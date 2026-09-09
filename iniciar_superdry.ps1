# SuperDry — Inicialização completa (requer admin)
# Sobe: MongoDB + Backend + Frontend
# v2 — 31/08/2026: root agora se auto-localiza (nao quebra mais quando a pasta OneDrive mudar de lugar/letra),
# checagens explicitas de cada dependencia antes de tentar subir, e logs de execucao gravados em arquivo
# para diagnostico remoto (backend em logs\backend_run.log, frontend em frontend_run.log).

# --- 0. Localizacao automatica da raiz do projeto -----------------------------------------
# Antes o caminho ficava fixo (ex: "E:\OneDrive\SuperDry\SuperDry-Atual-MIGRACAO") e quebrava
# toda vez que a pasta do OneDrive mudava de letra de unidade ou de posicao. Agora a raiz e
# sempre "a pasta onde este .ps1 esta", entao o script acompanha a pasta se ela for movida de novo.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logFile = Join-Path $root "iniciar_superdry_log.txt"

function Log($msg, $color = "Gray") {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Add-Content -Path $logFile -Value $line
    Write-Host $line -ForegroundColor $color
}

"=== Nova execução: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Add-Content -Path $logFile

Write-Host "=== SuperDry Iniciando ===" -ForegroundColor Cyan
Log "Raiz do projeto detectada: $root"

# --- 0b. Checagens de sanidade antes de tentar subir qualquer coisa -----------------------
$erro = $false

if (-not (Test-Path (Join-Path $root "backend\server.py"))) {
    Log "ERRO: nao encontrei '$root\backend\server.py'. A pasta do projeto mudou de estrutura?" "Red"
    $erro = $true
}
if (-not (Test-Path (Join-Path $root "frontend\package.json"))) {
    Log "ERRO: nao encontrei '$root\frontend\package.json'." "Red"
    $erro = $true
}

# Localiza o uvicorn: tenta o caminho conhecido primeiro, depois cai para o PATH.
$uvicornCandidato = "C:\Users\USUARIO\AppData\Local\Python\pythoncore-3.14-64\Scripts\uvicorn.exe"
$uvicorn = $null
if (Test-Path $uvicornCandidato) {
    $uvicorn = $uvicornCandidato
} else {
    $cmd = Get-Command uvicorn.exe -ErrorAction SilentlyContinue
    if ($cmd) { $uvicorn = $cmd.Source }
}
if (-not $uvicorn) {
    Log "ERRO: uvicorn.exe nao encontrado em '$uvicornCandidato' nem no PATH. Python/venv mudou de lugar (reinstalou o Python? trocou de versao?). Rode 'where.exe uvicorn' num PowerShell normal e ajuste o caminho no script." "Red"
    $erro = $true
} else {
    Log "uvicorn encontrado em: $uvicorn"
}

# Localiza o npm (necessario para o frontend)
$npmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npmCmd) { $npmCmd = Get-Command npm -ErrorAction SilentlyContinue }
if (-not $npmCmd) {
    Log "ERRO: npm nao encontrado no PATH. Node.js instalado?" "Red"
    $erro = $true
}

if ($erro) {
    Log "Abortando por erro(s) de pre-requisito acima." "Red"
    Write-Host ""
    Write-Host "Corrija o(s) erro(s) acima (log completo em: $logFile) e rode de novo." -ForegroundColor Red
    Write-Host "Pressione qualquer tecla para fechar..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# --- 1. MongoDB -----------------------------------------------------------------------------
Write-Host "[1/3] Iniciando MongoDB..." -ForegroundColor Yellow
$svc = Get-Service -Name MongoDB -ErrorAction SilentlyContinue
if ($svc) {
    Start-Service MongoDB -ErrorAction SilentlyContinue
} else {
    Log "AVISO: servico Windows 'MongoDB' nao existe nesta maquina (verifique com 'Get-Service *mongo*'). Tentando seguir assumindo que o Mongo ja esta rodando de outra forma." "Yellow"
}
Start-Sleep 3
$mongo = Get-NetTCPConnection -LocalPort 27017 -State Listen -ErrorAction SilentlyContinue
if ($mongo) { Log "      MongoDB OK" "Green" }
else        { Log "      MongoDB FALHOU (porta 27017 nao respondeu)" "Red" }

# --- 2. Backend (loop reinício automático, janela minimizada) -------------------------------
Write-Host "[2/3] Iniciando Backend..." -ForegroundColor Yellow
$backendLog = Join-Path $root "backend\logs\backend_run.log"
New-Item -ItemType Directory -Force -Path (Join-Path $root "backend\logs") | Out-Null

$backendCmd = @"
`$u = '$uvicorn'
`$dir = '$root\backend'
`$log = '$backendLog'
while (`$true) {
    Set-Location `$dir
    & `$u server:app --host 0.0.0.0 --port 8001 2>&1 | Tee-Object -FilePath `$log -Append
    Start-Sleep 3
}
"@
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Minimized

Start-Sleep 10
$back = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
if ($back) { Log "      Backend OK" "Green" }
else {
    Log "      Backend FALHOU (porta 8001 nao respondeu). Veja $backendLog para o erro real." "Red"
}

# --- 3. Frontend (janela minimizada) ---------------------------------------------------------
Write-Host "[3/3] Iniciando Frontend..." -ForegroundColor Yellow
$frontendLog = Join-Path $root "frontend_run.log"
$frontendCmd = @"
Set-Location '$root\frontend'
npm start 2>&1 | Tee-Object -FilePath '$frontendLog' -Append
"@
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Minimized

Write-Host ""
Write-Host "Sistema iniciando!" -ForegroundColor Green
Write-Host "  Local:   http://localhost:3000" -ForegroundColor Cyan
Write-Host "  Celular: http://100.77.51.88:3000" -ForegroundColor Cyan
Write-Host "  Webhook: https://superdry.tail287b6c.ts.net" -ForegroundColor Cyan
Write-Host ""
Write-Host "Frontend demora ~30s para compilar." -ForegroundColor Gray
Write-Host "Log desta execucao: $logFile" -ForegroundColor Gray
Write-Host "Log do backend:     $backendLog" -ForegroundColor Gray
Write-Host "Log do frontend:    $frontendLog" -ForegroundColor Gray
Write-Host "Pressione qualquer tecla para fechar esta janela..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
