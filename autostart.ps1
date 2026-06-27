# SuperDry — Inicialização automática completa
# Executado automaticamente no login do Windows via Agendador de Tarefas
# Sobe: Tailscale Funnel + Backend + Frontend

$uvicorn  = "C:\Users\USUARIO\AppData\Local\Python\pythoncore-3.14-64\Scripts\uvicorn.exe"
$root     = "C:\Users\USUARIO\OneDrive\SuperDry-Atual-MIGRACAO"
$tailscale = "C:\Program Files\Tailscale\tailscale.exe"
$logFile  = "$root\autostart.log"

function Log($msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Add-Content -Path $logFile -Value $line
    Write-Host $line
}

Log "=== SuperDry Autostart ==="

# 1. Aguarda o Tailscale conectar (máx 30s)
Log "Aguardando Tailscale conectar..."
$tries = 0
while ($tries -lt 15) {
    $st = & $tailscale status 2>&1
    if ($st -match "100\.\d+\.\d+\.\d+") { break }
    Start-Sleep -Seconds 2
    $tries++
}

# 2. Ativa o Funnel
Log "Ativando Tailscale Funnel na porta 8001..."
& $tailscale funnel --bg 8001 2>&1 | ForEach-Object { Log $_ }

# 3. Sobe o backend (loop de reinício automático em janela separada)
Log "Subindo backend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
    `$uvicorn = '$uvicorn';
    `$dir = '$root\backend';
    while (`$true) {
        Write-Host '[Backend] Iniciando...' -ForegroundColor Green;
        Set-Location `$dir;
        & `$uvicorn server:app --host 0.0.0.0 --reload --port 8001;
        Write-Host '[Backend] Caiu — reiniciando em 3s...' -ForegroundColor Yellow;
        Start-Sleep 3;
    }
" -WindowStyle Minimized

# 4. Aguarda backend subir para então iniciar o frontend
Log "Aguardando backend subir..."
$tries = 0
while ($tries -lt 20) {
    $conn = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
    if ($conn) { break }
    Start-Sleep -Seconds 2
    $tries++
}

# 5. Sobe o frontend
Log "Subindo frontend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
    Write-Host '[Frontend] Iniciando...' -ForegroundColor Cyan;
    Set-Location '$root\frontend';
    npm start;
" -WindowStyle Minimized

Log "=== Autostart concluído ==="
Log "Backend  -> http://localhost:8001"
Log "Frontend -> http://localhost:3000"
Log "Externo  -> https://superdry.tail287b6c.ts.net"
