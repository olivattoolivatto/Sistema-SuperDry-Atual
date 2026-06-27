$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$uvicorn = "C:\Users\USUARIO\AppData\Local\Python\pythoncore-3.14-64\Scripts\uvicorn.exe"

# Backend — loop de reinício automático (se cair, volta em 3s)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
  `$uvicorn = '$uvicorn';
  `$dir = '$root\backend';
  Write-Host '=== SuperDry Backend ===' -ForegroundColor Cyan;
  Write-Host 'Reinicio automatico ativo. Ctrl+C para parar.' -ForegroundColor Gray;
  while (`$true) {
    Write-Host \"[`$(Get-Date -Format 'HH:mm:ss')] Iniciando...\" -ForegroundColor Green;
    Set-Location `$dir;
    & `$uvicorn server:app --host 0.0.0.0 --reload --port 8001;
    Write-Host \"[`$(Get-Date -Format 'HH:mm:ss')] Caiu — reiniciando em 3s...\" -ForegroundColor Yellow;
    Start-Sleep 3;
  }
"

# Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
  Write-Host '=== SuperDry Frontend ===' -ForegroundColor Green;
  Set-Location '$root\frontend';
  npm start
"

Write-Host ""
Write-Host "Iniciando SuperDry..." -ForegroundColor Yellow
Write-Host "  Backend  -> http://localhost:8001" -ForegroundColor Cyan
Write-Host "  Frontend -> http://localhost:3000" -ForegroundColor Green
Write-Host ""
Write-Host "Backend com reinicio automatico. Feche as janelas para parar." -ForegroundColor Gray
