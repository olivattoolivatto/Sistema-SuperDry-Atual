@echo off
title SuperDry — Status VM
"C:\Program Files\Git\bin\bash.exe" -c "ssh -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no opc@148.116.108.43 'sudo journalctl -u superdry -n 40 --no-pager && echo --- && sudo systemctl status superdry --no-pager' > ~/OneDrive/SuperDry-Atual-MIGRACAO/vm_log.txt 2>&1"
echo Pronto. Feche esta janela.
pause
