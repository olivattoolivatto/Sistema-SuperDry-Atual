# =============================================================================
# SuperDry — Rodar localmente para teste
# Uso: .\rodar-local.ps1
#
# Requisito: cria um tunel SSH para o MongoDB do Oracle (porta 27017)
# O backend local se conecta ao banco real via tunel, sem precisar de
# MongoDB instalado na sua maquina.
# =============================================================================

$KEY    = "$env:USERPROFILE\.ssh\oracle.key"
$ORACLE = "opc@148.116.108.43"
$REPO   = "C:\Users\USUARIO\OneDrive\SuperDry-Atual-MIGRACAO"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  SuperDry — Ambiente Local" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "O que vai subir:" -ForegroundColor White
Write-Host "  - Tunel SSH  : localhost:27017 -> Oracle MongoDB" -ForegroundColor Gray
Write-Host "  - Backend    : http://localhost:8001" -ForegroundColor Gray
Write-Host "  - Frontend   : http://localhost:3000" -ForegroundColor Gray
Write-Host ""
Write-Host "Pressione Ctrl+C em qualquer janela para parar." -ForegroundColor Yellow
Write-Host ""

# ── 1. Tunel SSH para o MongoDB ───────────────────────────────────────────────
Write-Host "Abrindo tunel SSH para o MongoDB..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "Write-Host 'TUNEL MongoDB (nao feche esta janela)' -ForegroundColor Yellow; " +
    "ssh -i `"$KEY`" -o StrictHostKeyChecking=no -N -L 27017:localhost:27017 $ORACLE"

Start-Sleep -Seconds 3

# ── 2. Backend FastAPI ────────────────────────────────────────────────────────
Write-Host "Iniciando backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "Write-Host 'BACKEND FastAPI' -ForegroundColor Cyan; " +
    "Set-Location '$REPO\backend'; " +
    "pip install -r requirements.txt -q; " +
    "uvicorn server:app --reload --port 8001"

Start-Sleep -Seconds 5

# ── 3. Frontend React ─────────────────────────────────────────────────────────
Write-Host "Iniciando frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "Write-Host 'FRONTEND React' -ForegroundColor Cyan; " +
    "Set-Location '$REPO\frontend'; " +
    "npm start"

Write-Host ""
Write-Host "Abrindo em 10 segundos: http://localhost:3000" -ForegroundColor Green
Start-Sleep -Seconds 10
Start-Process "http://localhost:3000"
