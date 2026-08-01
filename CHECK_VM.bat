@echo off
title SuperDry — Check + Fix VM
echo Verificando e restaurando servico na VM...
"C:\Program Files\Git\bin\bash.exe" -c "ssh -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no opc@148.116.108.43 'sudo journalctl -u superdry -n 20 --no-pager 2>&1; echo ---; sudo systemctl status superdry --no-pager 2>&1' 2>&1 | tee ~/OneDrive/SuperDry-Atual-MIGRACAO/vm_status.txt"
echo.
echo Status salvo em vm_status.txt
pause
