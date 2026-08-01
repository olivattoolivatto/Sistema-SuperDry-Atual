@echo off
title SuperDry — Deploy direto (SCP)
echo ============================================
echo  SuperDry — Copiando arquivos para VM
echo ============================================
echo.
echo [1/5] Copiando BudgetEditor.js...
"C:\Program Files\Git\bin\bash.exe" -c "scp -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no ~/OneDrive/SuperDry-Atual-MIGRACAO/frontend/src/pages/budgets/BudgetEditor.js opc@148.116.108.43:/home/opc/superdry/frontend/src/pages/budgets/BudgetEditor.js && echo SCP_BEDITOR_OK"
if %ERRORLEVEL% NEQ 0 ( echo ERRO SCP BudgetEditor && pause && exit /b 1 )

echo [2/5] Copiando server.py + modulos auxiliares...
"C:\Program Files\Git\bin\bash.exe" -c "scp -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no ~/OneDrive/SuperDry-Atual-MIGRACAO/backend/server.py ~/OneDrive/SuperDry-Atual-MIGRACAO/backend/payment_providers.py ~/OneDrive/SuperDry-Atual-MIGRACAO/backend/finance_manager.py ~/OneDrive/SuperDry-Atual-MIGRACAO/backend/auth.py opc@148.116.108.43:/home/opc/superdry/backend/ && echo SCP_BACKEND_OK"
if %ERRORLEVEL% NEQ 0 ( echo ERRO SCP backend && pause && exit /b 1 )

echo [3/5] Convertendo CRLF nos arquivos Python e JS...
"C:\Program Files\Git\bin\bash.exe" -c "ssh -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no opc@148.116.108.43 'sed -i s/\r// /home/opc/superdry/frontend/src/pages/budgets/BudgetEditor.js /home/opc/superdry/backend/server.py /home/opc/superdry/backend/payment_providers.py /home/opc/superdry/backend/finance_manager.py /home/opc/superdry/backend/auth.py && echo CRLF_OK'"

echo [4/5] Build frontend + restart...
"C:\Program Files\Git\bin\bash.exe" -c "ssh -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no opc@148.116.108.43 'cd /home/opc/superdry/frontend && npm run build 2>&1 | tail -8 && sudo systemctl restart superdry && echo DEPLOY_DONE'"

echo.
echo [5/5] Verificando servico (aguarde 10s)...
timeout /t 10 /nobreak > nul
"C:\Program Files\Git\bin\bash.exe" -c "ssh -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no opc@148.116.108.43 'curl -s -o /dev/null -w HTTP_%{http_code} http://localhost:8001/api/auth/me'"

echo.
echo ============================================
echo  Acesse: http://sistema.lavesuperdry.com.br/
echo ============================================
pause
