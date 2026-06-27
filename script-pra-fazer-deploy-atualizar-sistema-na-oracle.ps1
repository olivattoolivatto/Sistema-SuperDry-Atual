# =============================================================================
# SuperDry — Script de Deploy
# Uso: .\deploy.ps1
# Faz: git add -A → commit → push → SSH Oracle → pull → build → restart
# =============================================================================

$KEY     = "$env:USERPROFILE\.ssh\oracle.key"
$ORACLE  = "opc@148.116.108.43"
$REPO    = "C:\Users\USUARIO\OneDrive\SuperDry-Atual-MIGRACAO"

Set-Location $REPO

# ── 1. Mostrar o que vai ser enviado ─────────────────────────────────────────
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  SuperDry Deploy" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

$status = git status --short
if (-not $status) {
    Write-Host "Nenhuma alteracao local encontrada." -ForegroundColor Yellow
    Write-Host "O Oracle ja esta atualizado. Nada a fazer." -ForegroundColor Yellow
    exit 0
}

Write-Host "Arquivos alterados:" -ForegroundColor White
git status --short
Write-Host ""

# ── 2. Mensagem do commit ─────────────────────────────────────────────────────
$msg = Read-Host "Descricao do que foi alterado (Enter para 'Atualizacao')"
if (-not $msg) { $msg = "Atualizacao" }

# ── 3. Confirmar ─────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Resumo do deploy:" -ForegroundColor White
Write-Host "  Commit : $msg" -ForegroundColor Gray
Write-Host "  Destino: sistema.lavesuperdry.com.br (Oracle)" -ForegroundColor Gray
Write-Host ""
$confirm = Read-Host "Confirma? (s/n)"
if ($confirm -ne "s") {
    Write-Host "Deploy cancelado." -ForegroundColor Yellow
    exit 0
}

# ── 4. Git add + commit + push ────────────────────────────────────────────────
Write-Host ""
Write-Host "[1/3] Enviando para o GitHub..." -ForegroundColor Cyan
git add -A
git commit -m $msg
if ($LASTEXITCODE -ne 0) {
    Write-Host "Erro no commit. Verifique os arquivos." -ForegroundColor Red
    exit 1
}
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "Erro no push. Verifique a conexao com o GitHub." -ForegroundColor Red
    exit 1
}
Write-Host "GitHub atualizado." -ForegroundColor Green

# ── 5. Deploy no Oracle ───────────────────────────────────────────────────────
Write-Host ""
Write-Host "[2/3] Conectando ao Oracle e fazendo pull..." -ForegroundColor Cyan

$remoteCmd = @"
set -e
cd /home/opc/superdry
echo '[Oracle] Pull...'
git pull origin main
echo '[Oracle] Reiniciando backend...'
sudo systemctl restart superdry
echo '[Oracle] Backend OK'
"@

ssh -i $KEY -o StrictHostKeyChecking=no $ORACLE $remoteCmd
if ($LASTEXITCODE -ne 0) {
    Write-Host "Erro ao conectar/atualizar o Oracle." -ForegroundColor Red
    exit 1
}

# ── 6. Build do frontend ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "[3/3] Compilando frontend no Oracle (~3 min)..." -ForegroundColor Cyan

$buildCmd = @"
set -e
cd /home/opc/superdry/frontend
npm run build
echo 'BUILD_CONCLUIDO'
"@

$output = ssh -i $KEY -o StrictHostKeyChecking=no $ORACLE $buildCmd
Write-Host $output

if ($output -match "BUILD_CONCLUIDO") {
    Write-Host ""
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host "  Deploy concluido com sucesso!" -ForegroundColor Green
    Write-Host "  https://sistema.lavesuperdry.com.br" -ForegroundColor Green
    Write-Host "=====================================" -ForegroundColor Green
} else {
    Write-Host "Build pode ter falhado. Verifique o output acima." -ForegroundColor Yellow
}
