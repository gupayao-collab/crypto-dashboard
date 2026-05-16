#!/usr/bin/env python3
"""
Dashboard Collector — coleta precos publicos da Binance e salva em dados.json.

Toda a logica de fetching esta em binance_data.py (modulo compartilhado
com o backend web). Este script adiciona:
  - Acumulacao de historico de atualizacoes por coin (ultimas 100)
  - Acumulacao de historico de coletas (ultimas 500)
  - Persistencia em dados.json
  - Modo continuo a cada 30 minutos
  - Menu interativo
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import binance_data

COINS                = binance_data.COINS_DEFAULT
COLLECT_INTERVAL_MIN = 30
VARIATION_THRESHOLD  = 3.0
DATA_FILE            = Path(__file__).parent / "dados.json"


class DashboardCollector:
    def __init__(self) -> None:
        self.coins = COINS
        self.data  = self._carregar_dados()

    def _estrutura_vazia(self) -> dict:
        return {
            "coins": {
                coin: {
                    "preco_atual":    0.0,
                    "media_24h":      0.0,
                    "desvio_percent": 0.0,
                    "historico_24h":  [],
                    "atualizacoes":   [],
                }
                for coin in self.coins
            },
            "ultima_atualizacao": None,
            "historico_coletas":  [],
        }

    def _carregar_dados(self) -> dict:
        if DATA_FILE.exists():
            try:
                return json.loads(DATA_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return self._estrutura_vazia()

    def _salvar_dados(self) -> bool:
        try:
            DATA_FILE.write_text(
                json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            return True
        except OSError as e:
            print(f"  [ERRO] Falha ao salvar dados: {e}")
            return False

    def coletar(self) -> bool:
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print(f"\n{'='*55}")
        print(f"  Coletando dados — {ts}")
        print(f"{'='*55}")

        coletados = 0
        agora = datetime.now().isoformat()

        for coin in self.coins:
            snapshot = binance_data.obter_mercado_coin(coin)
            if snapshot is None:
                print(f"  {coin:<6} [ERRO] Sem dados")
                continue

            # Garante que o coin existe na estrutura (caso seja novo)
            entry = self.data["coins"].setdefault(coin, {
                "preco_atual": 0.0, "media_24h": 0.0, "desvio_percent": 0.0,
                "historico_24h": [], "atualizacoes": [],
            })

            entry["preco_atual"]    = snapshot["preco_atual"]
            entry["media_24h"]      = snapshot["media_24h"]
            entry["desvio_percent"] = snapshot["desvio_percent"]
            entry["historico_24h"]  = snapshot["historico_24h"]

            entry["atualizacoes"].append({
                "timestamp": agora,
                "preco":     snapshot["preco_atual"],
                "desvio":    snapshot["desvio_percent"],
            })
            entry["atualizacoes"] = entry["atualizacoes"][-100:]

            coletados += 1
            status = "[!] ALERTA" if abs(snapshot["desvio_percent"]) >= VARIATION_THRESHOLD else "[OK] Estavel"
            print(
                f"  {coin:<6} {status} | ${snapshot['preco_atual']:>12,.2f} | "
                f"{snapshot['desvio_percent']:+.2f}%"
            )

        self.data["ultima_atualizacao"] = agora
        self.data["historico_coletas"].append({
            "timestamp":  agora,
            "coletados":  coletados,
            "total":      len(self.coins),
        })
        self.data["historico_coletas"] = self.data["historico_coletas"][-500:]

        print(f"{'='*55}")
        if self._salvar_dados():
            print(f"  [OK] {coletados}/{len(self.coins)} coins salvas em dados.json")
        print(f"{'='*55}\n")
        return coletados > 0

    def executar_continuo(self, intervalo_min: int = COLLECT_INTERVAL_MIN) -> None:
        print(f"\n  Modo continuo — atualizando a cada {intervalo_min} minuto(s)")
        print(f"  Arquivo: {DATA_FILE}")
        print(f"  Pressione Ctrl+C para parar\n")
        try:
            while True:
                self.coletar()
                print(f"  Proxima coleta em {intervalo_min} minuto(s)...")
                time.sleep(intervalo_min * 60)
        except KeyboardInterrupt:
            print("\n  Coleta encerrada.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dashboard Collector")
    parser.add_argument(
        "--modo", choices=["unico", "continuo"], default=None,
        help="unico = coleta uma vez | continuo = coleta a cada 30min",
    )
    parser.add_argument(
        "--intervalo", type=int, default=COLLECT_INTERVAL_MIN,
        help=f"Intervalo em minutos (padrao: {COLLECT_INTERVAL_MIN})",
    )
    args = parser.parse_args()

    collector = DashboardCollector()

    if args.modo == "continuo":
        collector.executar_continuo(args.intervalo)
        return

    if args.modo == "unico":
        collector.coletar()
        return

    print(f"\n{'='*55}")
    print("  Dashboard Collector")
    print(f"{'='*55}")
    print(f"  Arquivo: {DATA_FILE}\n")
    print("  [1] Coletar dados agora (unica vez)")
    print("  [2] Coleta continua (a cada 30 minutos)")
    opcao = input("\n  Escolha (1/2): ").strip()

    if opcao == "1":
        collector.coletar()
    elif opcao == "2":
        collector.executar_continuo()
    else:
        print("  Opcao invalida.")


if __name__ == "__main__":
    main()
