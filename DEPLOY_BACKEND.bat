@echo off
title SuperDry -- Deploy Backend
echo [1/2] Copiando server.py...
"C:\Program Files\Git\bin\bash.exe" -c "scp -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no ~/OneDrive/SuperDry-Atual-MIGRACAO/backend/server.py opc@148.116.108.43:/home/opc/superdry/backend/server.py && echo SCP_OK"
echo.
echo [2/2] Reiniciando backend...
"C:\Program Files\Git\bin\bash.exe" -c "ssh -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no opc@148.116.108.43 'sudo systemctl restart superdry && sleep 4 && curl -s -o /dev/null -w HTTP_%%{http_code} http://localhost:8001/api/auth/me'"
echo.
pause
