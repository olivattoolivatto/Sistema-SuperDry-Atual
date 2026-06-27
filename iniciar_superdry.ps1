# SuperDry — Inicialização completa (requer admin)
# Sobe: MongoDB + Backend + Frontend

$uvicorn  = "C:\Users\USUARIO\AppData\Local\Python\pythoncore-3.14-64\Scripts\uvicorn.exe"
$root     = "C:\Users\USUARIO\OneDrive\SuperDry-Atual-MIGRACAO"

Write-Host "=== SuperDry Iniciando ===" -ForegroundColor Cyan

# 1. MongoDB
Write-Host "[1/3] Iniciando MongoDB..." -ForegroundColor Yellow
Start-Service MongoDB -ErrorAction SilentlyContinue
Start-Sleep 3
$mongo = Get-NetTCPConnection -LocalPort 27017 -State Listen -ErrorAction SilentlyContinue
if ($mongo) { Write-Host "      MongoDB OK" -ForegroundColor Green }
else         { Write-Host "      MongoDB FALHOU" -ForegroundColor Red }

# 2. Backend (loop reinício automático, janela minimizada)
Write-Host "[2/3] Iniciando Backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit","-Command","`
    `$u='$uvicorn';`
    while(`$true){`
        Set-Location '$root\backend';`
        & `$u server:app --host 0.0.0.0 --port 8001;`
        Start-Sleep 3`
    }" -WindowStyle Minimized
Start-Sleep 10
$back = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
if ($back) { Write-Host "      Backend OK" -ForegroundColor Green }
else        { Write-Host "      Backend FALHOU" -ForegroundColor Red }

# 3. Frontend (janela minimizada)
Write-Host "[3/3] Iniciando Frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit","-Command","`
    Set-Location '$root\frontend';`
    npm start" -WindowStyle Minimized

Write-Host ""
Write-Host "Sistema iniciando!" -ForegroundColor Green
Write-Host "  Local:   http://localhost:3000" -ForegroundColor Cyan
Write-Host "  Celular: http://100.77.51.88:3000" -ForegroundColor Cyan
Write-Host "  Webhook: https://superdry.tail287b6c.ts.net" -ForegroundColor Cyan
Write-Host ""
Write-Host "Frontend demora ~30s para compilar." -ForegroundColor Gray
Write-Host "Pressione qualquer tecla para fechar esta janela..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
