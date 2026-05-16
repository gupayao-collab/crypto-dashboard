#!/usr/bin/env python3
"""
Servidor HTTP do Crypto Dashboard.
Substitui 'python -m http.server' e encerra todos os processos
automaticamente quando o browser fechar o dashboard.
"""

import http.server
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

HEARTBEAT_TIMEOUT = 4    # segundos sem ping = browser fechou

# Scripts dos coletores — usados para localizar e encerrar os processos
SCRIPTS_COLETORES = [
    "dashboard_collector.py",
    "portfolio_collector.py",
]

_inicio      = time.time()
_ultimo_ping = _inicio
_encerrado   = False


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global _ultimo_ping
        if self.path.startswith("/ping"):
            _ultimo_ping = time.time()
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        super().do_GET()

    def log_message(self, fmt, *args):
        if args and "/ping" in str(args[0]):
            return
        super().log_message(fmt, *args)


def _pids_por_cmdline(keyword: str) -> list[int]:
    """Retorna os PIDs de processos cujo CommandLine contém keyword."""
    result = subprocess.run(
        ["wmic", "process", "where", f'CommandLine like "%{keyword}%"',
         "get", "ProcessId", "/format:value"],
        capture_output=True, text=True
    )
    pids = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("ProcessId=") and line[10:].strip().isdigit():
            pid = int(line[10:].strip())
            if pid > 0:
                pids.append(pid)
    return pids


def _encerrar_tudo():
    global _encerrado
    if _encerrado:
        return
    _encerrado = True
    print("\n  Browser fechado — encerrando tudo...")

    for script in SCRIPTS_COLETORES:
        pids = _pids_por_cmdline(script)
        if pids:
            for pid in pids:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                               capture_output=True)
            print(f"  [OK] Encerrado: {script} (PID {pids})")
        else:
            print(f"  [--] Nao encontrado: {script}")

    time.sleep(0.5)
    print("  Servidor encerrado. Ate logo!\n")
    os._exit(0)


def _watchdog():
    print("  Aguardando conexao do browser...")
    while _ultimo_ping == _inicio:
        time.sleep(1)
    print("  Browser conectado. Monitorando heartbeat...\n")

    while True:
        time.sleep(3)
        if time.time() - _ultimo_ping > HEARTBEAT_TIMEOUT:
            _encerrar_tudo()
            break


if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    os.chdir(Path(__file__).parent)

    threading.Thread(target=_watchdog, daemon=True).start()

    print(f"\n  Servidor: http://localhost:{porta}/")
    print(f"  Encerra automaticamente ao fechar o dashboard no browser.\n")

    with http.server.HTTPServer(("", porta), Handler) as srv:
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            _encerrar_tudo()
