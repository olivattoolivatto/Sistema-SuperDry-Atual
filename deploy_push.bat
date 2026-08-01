@echo off
echo === SuperDry Deploy Push === > deploy_log.txt 2>&1
cd /d "C:\Users\USUARIO\OneDrive\SuperDry-Atual-MIGRACAO" >> deploy_log.txt 2>&1

if exist ".git\index.lock" ( del /f ".git\index.lock" >> deploy_log.txt 2>&1 )
if exist ".git\HEAD.lock" ( del /f ".git\HEAD.lock" >> deploy_log.txt 2>&1 )

git add backend/server.py >> deploy_log.txt 2>&1
git commit -m "fix: ollama timeout 150s + warmup no startup + skip claude api apos 400" >> deploy_log.txt 2>&1
git push origin main >> deploy_log.txt 2>&1
echo === Concluido === >> deploy_log.txt 2>&1
echo Done!
pause
