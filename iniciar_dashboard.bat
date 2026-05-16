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

REM Instalar dependencias
echo [1/5] Verificando dependencias...
pip install requests -q --disable-pip-version-check
echo       OK

REM Iniciar coletor de mercado em modo continuo
echo [2/5] Iniciando coletor de mercado...
start "Crypto Coletor Mercado" cmd /c "python dashboard_collector.py --modo continuo"

REM Iniciar coletor de portfolio em modo continuo
echo [3/5] Iniciando coletor de portfolio...
start "Crypto Coletor Portfolio" cmd /c "python portfolio_collector.py --modo continuo"

REM Aguardar primeira coleta
echo       Coletando dados, aguarde 12 segundos...
timeout /t 12 /nobreak > nul

REM Verificar porta disponivel
set PORTA=8080
netstat -an | find ":8080" | find "LISTENING" > nul 2>&1
if not errorlevel 1 (
    set PORTA=8181
    echo [4/5] Porta 8080 ocupada, usando 8181...
) else (
    echo [4/5] Iniciando servidor local na porta 8080...
)

REM Iniciar servidor HTTP local (com monitoramento de fechamento)
start "Crypto Servidor" cmd /c "python servidor.py %PORTA%"
timeout /t 2 /nobreak > nul

REM Abrir navegador e fechar esta janela
echo [5/5] Abrindo dashboard no navegador...
start http://localhost:%PORTA%/crypto_dashboard.html

echo.
echo ============================================
echo    DASHBOARD INICIADO!
echo    Endereco: http://localhost:%PORTA%/
echo    Feche o dashboard no browser para encerrar.
echo ============================================
echo.
