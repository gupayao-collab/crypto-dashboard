#!/usr/bin/env python3
"""
Portfolio Collector — busca saldo, preco medio e P&L da Binance.
Salva em portfolio.json para o dashboard local.

Toda a logica de coleta esta em binance_data.py (modulo compartilhado
com o backend web). Este script apenas chama, formata o log e salva o JSON.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import binance_data

PORTFOLIO_FILE      = Path(__file__).parent / "portfolio.json"
DEPOSITO_INICIAL_BRL = 3000.0


def _print_portfolio(p: dict) -> None:
    print(f"\n{'='*55}")
    print(f"  Buscando portfolio — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*55}")

    for coin, d in p["coins"].items():
        sinal = "+" if d["pl_pct"] >= 0 else ""
        print(
            f"  {coin:<8} ${d['preco_atual']:<14.6g}  "
            f"valor: ${d['valor_atual']:>10.2f}  "
            f"P&L: {sinal}{d['pl_pct']:.2f}%"
        )

    print(f"{'='*55}")
    sinal_total = '+' if p['pl_total_pct'] >= 0 else ''
    print(
        f"  Total: ${p['total_valor_usd']:.2f}  |  "
        f"P&L: {sinal_total}{p['pl_total_pct']:.2f}%  (${p['pl_total_usd']:.2f})"
    )
    print(f"  Deposito inicial: R${p['deposito_inicial_brl']:,.2f}")
    print(f"  Salvo em: {PORTFOLIO_FILE}")
    print(f"{'='*55}\n")


def coletar_portfolio() -> dict:
    portfolio = binance_data.obter_portfolio(deposito_inicial_brl=DEPOSITO_INICIAL_BRL)
    PORTFOLIO_FILE.write_text(
        json.dumps(portfolio, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    _print_portfolio(portfolio)
    return portfolio


def main() -> None:
    parser = argparse.ArgumentParser(description="Portfolio Collector")
    parser.add_argument("--modo", choices=["unico", "continuo"], default=None)
    parser.add_argument("--intervalo", type=int, default=30)
    args = parser.parse_args()

    if args.modo == "continuo":
        print(f"  Modo continuo — atualizando a cada {args.intervalo} minuto(s)")
        try:
            while True:
                coletar_portfolio()
                time.sleep(args.intervalo * 60)
        except KeyboardInterrupt:
            print("\n  Encerrado.")
        return

    if args.modo == "unico":
        coletar_portfolio()
        return

    print(f"\n{'='*55}")
    print("  Portfolio Collector")
    print(f"{'='*55}\n")
    print("  [1] Coletar agora (unica vez)")
    print("  [2] Coleta continua (a cada 30 minutos)")
    opcao = input("\n  Escolha (1/2): ").strip()
    if opcao == "1":
        coletar_portfolio()
    elif opcao == "2":
        args.modo = "continuo"
        main()
    else:
        print("  Opcao invalida.")


if __name__ == "__main__":
    main()
