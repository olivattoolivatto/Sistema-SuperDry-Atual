@echo off
title SuperDry -- Redeploy Completo
echo ============================================
echo  SuperDry -- Redeploy Completo
echo ============================================
echo.

echo [1/6] Copiando arquivos frontend alterados...
"C:\Program Files\Git\bin\bash.exe" -c "scp -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no ~/OneDrive/SuperDry-Atual-MIGRACAO/frontend/src/pages/budgets/BudgetEditor.js opc@148.116.108.43:/home/opc/superdry/frontend/src/pages/budgets/BudgetEditor.js && scp -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no ~/OneDrive/SuperDry-Atual-MIGRACAO/frontend/src/pages/Budgets.js opc@148.116.108.43:/home/opc/superdry/frontend/src/pages/Budgets.js && scp -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no ~/OneDrive/SuperDry-Atual-MIGRACAO/frontend/src/pages/TechnicianMode.js opc@148.116.108.43:/home/opc/superdry/frontend/src/pages/TechnicianMode.js && scp -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no ~/OneDrive/SuperDry-Atual-MIGRACAO/frontend/src/pages/AcceptancePage.js opc@148.116.108.43:/home/opc/superdry/frontend/src/pages/AcceptancePage.js && scp -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no ~/OneDrive/SuperDry-Atual-MIGRACAO/frontend/src/pages/PhotoGalleryPage.js opc@148.116.108.43:/home/opc/superdry/frontend/src/pages/PhotoGalleryPage.js && scp -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no ~/OneDrive/SuperDry-Atual-MIGRACAO/frontend/src/App.js opc@148.116.108.43:/home/opc/superdry/frontend/src/App.js && scp -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no ~/OneDrive/SuperDry-Atual-MIGRACAO/frontend/src/pages/Catalog.js opc@148.116.108.43:/home/opc/superdry/frontend/src/pages/Catalog.js && scp -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no ~/OneDrive/SuperDry-Atual-MIGRACAO/frontend/src/components/MiniMap.js opc@148.116.108.43:/home/opc/superdry/frontend/src/components/MiniMap.js && echo SCP_JS_OK"
echo.

echo [2/6] Copiando backend (server.py + modulos)...
"C:\Program Files\Git\bin\bash.exe" -c "scp -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no ~/OneDrive/SuperDry-Atual-MIGRACAO/backend/server.py ~/OneDrive/SuperDry-Atual-MIGRACAO/backend/payment_providers.py ~/OneDrive/SuperDry-Atual-MIGRACAO/backend/finance_manager.py ~/OneDrive/SuperDry-Atual-MIGRACAO/backend/auth.py opc@148.116.108.43:/home/opc/superdry/backend/ && echo SCP_BACKEND_OK"
echo.

echo [3/6] Convertendo CRLF dos JS com dos2unix (instala se precisar)...
"C:\Program Files\Git\bin\bash.exe" -c "ssh -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no opc@148.116.108.43 'which dos2unix > /dev/null 2>&1 || sudo yum install -y dos2unix -q; dos2unix /home/opc/superdry/frontend/src/pages/budgets/BudgetEditor.js /home/opc/superdry/frontend/src/pages/Budgets.js /home/opc/superdry/frontend/src/pages/TechnicianMode.js /home/opc/superdry/frontend/src/pages/AcceptancePage.js /home/opc/superdry/frontend/src/pages/PhotoGalleryPage.js /home/opc/superdry/frontend/src/App.js /home/opc/superdry/frontend/src/pages/Catalog.js /home/opc/superdry/frontend/src/components/MiniMap.js 2>&1 && echo CRLF_OK'"
echo.

echo [4/6] Reiniciando backend (server.py restaurado)...
"C:\Program Files\Git\bin\bash.exe" -c "ssh -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no opc@148.116.108.43 'sudo systemctl restart superdry && sleep 3 && sudo systemctl status superdry --no-pager | head -6 && echo BACKEND_OK'"
echo.

echo [5/6] Build frontend -- aguarde 3 a 4 minutos...
"C:\Program Files\Git\bin\bash.exe" -c "ssh -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no -o ServerAliveInterval=30 opc@148.116.108.43 'cd /home/opc/superdry/frontend && npm run build > /tmp/build_superdry.log 2>&1; RC=$?; tail -20 /tmp/build_superdry.log; echo ---; echo BUILD_EXIT_CODE_$RC; if [ $RC -eq 0 ]; then sudo systemctl restart superdry && echo FRONTEND_DEPLOY_OK; else echo FRONTEND_BUILD_FALHOU; fi'"
echo.

echo [6/6] Verificacao final (aguarde 12s)...
timeout /t 12 /nobreak > nul
"C:\Program Files\Git\bin\bash.exe" -c "ssh -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no opc@148.116.108.43 'curl -s -o /dev/null -w HTTP_%%{http_code} http://localhost:8001/api/auth/me; echo; test -f /home/opc/superdry/frontend/build/index.html && echo FRONTEND_INDEX_OK || echo FRONTEND_INDEX_MISSING'"
echo.
echo ============================================
echo  Acesse: https://sistema.lavesuperdry.com.br/
echo ============================================
pause
