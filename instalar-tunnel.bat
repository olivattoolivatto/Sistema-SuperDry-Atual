@echo off
echo ================================================
echo  SuperDry - Instalacao do Cloudflare Tunnel
echo ================================================
echo.

echo [1/3] Baixando cloudflared...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'C:\cloudflared.exe'"

if not exist C:\cloudflared.exe (
    echo ERRO: Falha no download. Verifique a internet e tente novamente.
    pause
    exit /b 1
)
echo OK: cloudflared.exe baixado em C:\

echo.
echo [2/3] Instalando como servico do Windows...
C:\cloudflared.exe service install eyJhIjoiZTdmZGFiYTYxMTA0MTAzYzJjN2MxZDVmODNhMTViN2MiLCJ0IjoiMDhlNWRhMzAtNTA3OS00ZjE3LWJhOTgtYTM5YTA4ODIyNDQzIiwicyI6IlpHUXpNbVl3TlRZdE1tWm1aQzAwWVRVM0xUaGlaV1V0TWpaalpESmlaVGcyWVRFeSJ9

echo.
echo [3/3] Iniciando servico...
net start cloudflared

echo.
echo ================================================
echo  Tunnel instalado! Verifique no painel Cloudflare
echo  em Zero Trust - Tunnels - supersystem
echo ================================================
pause
