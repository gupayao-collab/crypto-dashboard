"""
Backend web do Crypto Dashboard.

Reusa binance_data.py — o MESMO modulo usado pelos collectors locais (PC).
Qualquer ajuste de logica de coleta vale para PC e iPhone simultaneamente.

Endpoints:
  GET /dados.json     — snapshot do mercado (publico)
  GET /portfolio.json — snapshot do portfolio (privado, exige BINANCE_API_KEY/SECRET)
  GET /health         — healthcheck para o Render

Cache: cada chamada a Binance demora ~3s (mercado) ou ~10s (portfolio).
Para evitar martelar a API, cacheamos por 30s em memoria.

Credenciais sao lidas de variaveis de ambiente (configurar no painel do Render):
  BINANCE_API_KEY, BINANCE_SECRET, DEPOSITO_INICIAL (opcional, padrao 3000),
  ALLOWED_ORIGIN (opcional, padrao *).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# Carrega .env local (so em dev — no Render as env vars vem do painel)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# Importa o modulo da pasta pai (Dashboard/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import binance_data  # noqa: E402

CACHE_TTL_SEC = 30
_cache: dict[str, tuple[float, dict]] = {}

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": os.environ.get("ALLOWED_ORIGIN", "*")}})


def _cached(chave: str, ttl: int, gerador):
    agora = time.time()
    if chave in _cache:
        ts, dados = _cache[chave]
        if agora - ts < ttl:
            return dados
    dados = gerador()
    _cache[chave] = (agora, dados)
    return dados


@app.route("/dados.json")
def dados():
    try:
        payload = _cached("mercado", CACHE_TTL_SEC, binance_data.obter_mercado)
        return jsonify(payload)
    except Exception as e:
        return jsonify({"erro": "Falha ao buscar dados de mercado", "detalhe": str(e)}), 502


@app.route("/portfolio.json")
def portfolio():
    try:
        deposito = float(os.environ.get("DEPOSITO_INICIAL", "3000"))
        payload = _cached(
            "portfolio",
            CACHE_TTL_SEC,
            lambda: binance_data.obter_portfolio(deposito_inicial_brl=deposito),
        )
        return jsonify(payload)
    except FileNotFoundError as e:
        return jsonify({"erro": "Credenciais nao configuradas", "detalhe": str(e)}), 500
    except Exception as e:
        return jsonify({"erro": "Falha ao buscar portfolio", "detalhe": str(e)}), 502


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# ──────────────────────────────────────────────────────────────────────────
# Rotas para servir o HTML em DEV LOCAL (em producao, GitHub Pages faz isso).
# Permite abrir http://localhost:5000/ e ver o dashboard completo.
# ──────────────────────────────────────────────────────────────────────────
DASHBOARD_DIR = str(Path(__file__).resolve().parent.parent)


@app.route("/")
def index():
    return send_from_directory(DASHBOARD_DIR, "crypto_dashboard.html")


@app.route("/crypto_dashboard.html")
def dashboard_html():
    return send_from_directory(DASHBOARD_DIR, "crypto_dashboard.html")


@app.route("/manifest.json")
def manifest():
    return send_from_directory(DASHBOARD_DIR, "manifest.json")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
