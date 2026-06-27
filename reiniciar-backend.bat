@echo off
echo Parando uvicorn...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM uvicorn.exe /T 2>nul
timeout /t 2 /nobreak >nul

echo Iniciando backend SuperDry...
cd /d "%~dp0backend"
start "SuperDry Backend" cmd /k "uvicorn server:app --host 0.0.0.0 --port 8001"
echo Backend iniciado na porta 8001.
