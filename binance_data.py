#!/usr/bin/env python3
"""
binance_data.py — Modulo compartilhado de coleta de dados da Binance.

Centraliza toda a logica que antes estava duplicada entre os collectors.
Usado tanto pelos scripts locais (dashboard_collector.py, portfolio_collector.py)
quanto pelo backend web (backend/app.py) — UMA fonte de verdade.

Credenciais:
- Primeiro tenta variaveis de ambiente BINANCE_API_KEY / BINANCE_SECRET (producao Render)
- Se nao achar, cai para ~/.crypto_monitor/ com Fernet (uso local no PC)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import datetime
from pathlib import Path

import requests

BINANCE_API = "https://api.binance.com"
CONFIG_DIR  = Path.home() / ".crypto_monitor"

# Stablecoins e tokens descontinuados ignorados no portfolio
IGNORAR = {"USDT", "BRL", "BUSD", "TUSD", "FDUSD", "ETHW"}

# Coins padrao monitoradas no dashboard de mercado
COINS_DEFAULT = ["BTC", "ETH", "AAVE", "ADA", "XRP", "SOL", "DOGE", "PEPE", "SUI"]

# Sleep entre chamadas (para nao estourar rate limit)
SLEEP_BETWEEN_CALLS = 0.15


# ---------------------------------------------------------------------------
# Credenciais
# ---------------------------------------------------------------------------

def carregar_credenciais() -> tuple[str, str]:
    """Carrega API Key + Secret. Env vars tem prioridade sobre arquivo local."""
    api_key = os.environ.get("BINANCE_API_KEY")
    secret  = os.environ.get("BINANCE_SECRET")
    if api_key and secret:
        return api_key, secret

    cipher_file = CONFIG_DIR / "cipher.key"
    creds_file  = CONFIG_DIR / "binance_credenciais.json"
    if not cipher_file.exists() or not creds_file.exists():
        raise FileNotFoundError(
            "Credenciais Binance nao encontradas.\n"
            "Local: execute setup_binance.py\n"
            "Producao: defina BINANCE_API_KEY e BINANCE_SECRET como variaveis de ambiente."
        )

    from cryptography.fernet import Fernet
    key   = cipher_file.read_bytes()
    dados = json.loads(Fernet(key).decrypt(creds_file.read_bytes()))
    return dados["api_key"], dados["secret_key"]


# ---------------------------------------------------------------------------
# Helpers HTTP
# ---------------------------------------------------------------------------

def _signed_get(endpoint: str, api_key: str, secret_key: str, params: dict | None = None) -> dict | list:
    p = {**(params or {}), "timestamp": int(time.time() * 1000)}
    qs  = "&".join(f"{k}={v}" for k, v in p.items())
    sig = hmac.new(secret_key.encode(), qs.encode(), hashlib.sha256).hexdigest()
    resp = requests.get(
        f"{BINANCE_API}{endpoint}",
        params={**p, "signature": sig},
        headers={"X-MBX-APIKEY": api_key},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _public_get(endpoint: str, params: dict | None = None):
    resp = requests.get(f"{BINANCE_API}{endpoint}", params=params or {}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _casas_decimais(preco: float) -> int:
    if preco >= 1:      return 2
    if preco >= 0.01:   return 4
    if preco >= 0.0001: return 6
    return 8


# ---------------------------------------------------------------------------
# Mercado (publico — nao precisa de credenciais)
# ---------------------------------------------------------------------------

def obter_mercado_coin(coin: str) -> dict | None:
    """Retorna snapshot 24h de uma coin: preco_atual, media_24h, desvio_percent, historico_24h.
    Mesma estrutura que dashboard_collector.py salva em dados.json -> coins[COIN].
    Retorna None se a coin nao tem par USDT ou houve erro."""
    try:
        klines = _public_get(
            "/api/v3/klines",
            {"symbol": f"{coin}USDT", "interval": "1h", "limit": 24},
        )
        closes = [float(k[4]) for k in klines]
        if not closes:
            return None

        preco  = closes[-1]
        media  = sum(closes) / len(closes)
        desvio = (preco - media) / media * 100  # com sinal: + alta, - baixa

        casas     = _casas_decimais(preco)
        return {
            "preco_atual":    round(preco,  casas),
            "media_24h":      round(media,  casas),
            "desvio_percent": round(desvio, 4),
            "historico_24h":  [round(p, casas) for p in closes],
        }
    except (requests.RequestException, ValueError, KeyError):
        return None


def obter_mercado(coins: list[str] | None = None) -> dict:
    """Snapshot completo do mercado para todas as coins.
    Mesma estrutura raiz que dados.json (sem historico_coletas/atualizacoes acumulado)."""
    coins = coins or COINS_DEFAULT
    resultado = {}
    for coin in coins:
        dados = obter_mercado_coin(coin)
        if dados is not None:
            resultado[coin] = dados
        time.sleep(SLEEP_BETWEEN_CALLS)

    return {
        "coins": resultado,
        "ultima_atualizacao": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Portfolio (privado — precisa de credenciais)
# ---------------------------------------------------------------------------

def _preco_atual_publico(coin: str) -> float | None:
    try:
        dados = _public_get("/api/v3/ticker/price", {"symbol": f"{coin}USDT"})
        return float(dados["price"])
    except (requests.RequestException, ValueError, KeyError):
        return None


def _calcular_posicao(coin: str, api_key: str, secret_key: str) -> dict:
    """Calcula preco medio e custo liquido baseado no historico de trades."""
    try:
        trades = _signed_get(
            "/api/v3/myTrades", api_key, secret_key,
            {"symbol": f"{coin}USDT", "limit": 1000},
        )
        if not isinstance(trades, list) or not trades:
            return {"preco_medio": 0.0, "custo_liquido": 0.0}

        compras = [t for t in trades if t["isBuyer"]]
        vendas  = [t for t in trades if not t["isBuyer"]]

        total_qty_comprado = sum(float(t["qty"])                     for t in compras)
        total_gasto        = sum(float(t["qty"]) * float(t["price"]) for t in compras)
        total_recebido     = sum(float(t["qty"]) * float(t["price"]) for t in vendas)

        preco_medio   = round(total_gasto / total_qty_comprado, 8) if total_qty_comprado > 0 else 0.0
        custo_liquido = max(0.0, total_gasto - total_recebido)

        return {
            "preco_medio":   preco_medio,
            "custo_liquido": round(custo_liquido, 4),
        }
    except (requests.RequestException, ValueError, KeyError):
        return {"preco_medio": 0.0, "custo_liquido": 0.0}


def obter_portfolio(deposito_inicial_brl: float = 3000.0) -> dict:
    """Snapshot completo do portfolio: saldo, preco medio, P&L por coin e totais.
    Mesma estrutura que portfolio.json."""
    api_key, secret_key = carregar_credenciais()
    conta = _signed_get("/api/v3/account", api_key, secret_key)

    saldos = {
        b["asset"]: float(b["free"]) + float(b["locked"])
        for b in conta["balances"]
        if (float(b["free"]) + float(b["locked"])) > 0 and b["asset"] not in IGNORAR
    }
    usdt_livre = next(
        (float(b["free"]) for b in conta["balances"] if b["asset"] == "USDT"), 0.0
    )

    coins = {}
    total_valor     = 0.0
    total_investido = 0.0

    for coin, qtd in saldos.items():
        preco = _preco_atual_publico(coin)
        if preco is None:
            continue

        posicao       = _calcular_posicao(coin, api_key, secret_key)
        preco_medio   = posicao["preco_medio"]
        custo_liquido = posicao["custo_liquido"]
        valor_atual   = qtd * preco
        pl_usd        = valor_atual - custo_liquido if custo_liquido > 0 else 0.0
        pl_pct        = (pl_usd / custo_liquido * 100) if custo_liquido > 0 else 0.0

        total_valor     += valor_atual
        total_investido += custo_liquido

        coins[coin] = {
            "quantidade":  round(qtd,           8),
            "preco_atual": preco,
            "preco_medio": preco_medio,
            "valor_atual": round(valor_atual,   4),
            "custo_base":  round(custo_liquido, 4),
            "pl_usd":      round(pl_usd,        4),
            "pl_pct":      round(pl_pct,        4),
        }
        time.sleep(SLEEP_BETWEEN_CALLS)

    pl_total_usd = total_valor - total_investido
    pl_total_pct = (pl_total_usd / total_investido * 100) if total_investido > 0 else 0.0

    return {
        "coins":                coins,
        "usdt_livre":           round(usdt_livre, 4),
        "total_valor_usd":      round(total_valor + usdt_livre, 4),
        "total_investido":      round(total_investido, 4),
        "pl_total_usd":         round(pl_total_usd, 4),
        "pl_total_pct":         round(pl_total_pct, 4),
        "deposito_inicial_brl": deposito_inicial_brl,
        "ultima_atualizacao":   datetime.now().isoformat(),
    }
