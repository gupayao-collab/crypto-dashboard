@echo off
title Crypto Dashboard

echo.
echo ============================================
echo    CRYPTO DASHBOARD - INICIANDO
echo ============================================
echo.

REM Verificar Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado.
    echo        Instale em: https://python.org
    echo.
    pause
    exit /b 1
)

REM Ir para a pasta do script
cd /d "%~dp0"

REM Instalar dependencias do backend
echo [1/3] Verificando dependencias...
pip install -r backend\requirements.txt -q --disable-pip-version-check
echo       OK

REM Verificar porta disponivel
set PORTA=8080
netstat -an | find ":8080" | find "LISTENING" > nul 2>&1
if not errorlevel 1 (
    set PORTA=8181
    echo [2/3] Porta 8080 ocupada, usando 8181...
) else (
    echo [2/3] Iniciando servidor na porta 8080...
)

REM Iniciar backend Flask (dados ao vivo da Binance)
start "Crypto Dashboard Backend" cmd /k "set PORT=%PORTA% && python backend\app.py"
timeout /t 3 /nobreak > nul

REM Abrir navegador
echo [3/3] Abrindo dashboard no navegador...
start http://localhost:%PORTA%/crypto_dashboard.html

echo.
echo ============================================
echo    DASHBOARD INICIADO!
echo    Endereco: http://localhost:%PORTA%/
echo    Feche a janela "Crypto Dashboard Backend"
echo    para encerrar o servidor.
echo ============================================
echo.
