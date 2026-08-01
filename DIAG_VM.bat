@echo off
title SuperDry -- Diagnostico VM
echo Coletando diagnostico da VM...
"C:\Program Files\Git\bin\bash.exe" -c "ssh -i ~/OneDrive/SuperDry-Atual-MIGRACAO/oracle-vm-key.key -o StrictHostKeyChecking=no opc@148.116.108.43 'echo === SERVICO === && sudo systemctl status superdry --no-pager 2>&1 && echo === BUILD DIR === && ls -la /home/opc/superdry/frontend/build/ 2>&1 && echo === INDEX.HTML === && test -f /home/opc/superdry/frontend/build/index.html && echo EXISTS || echo MISSING && echo === ULTIMAS LINHAS DO BUILD LOG === && tail -30 /home/opc/superdry/frontend/npm_build.log 2>/dev/null || echo sem log && echo === JOURNAL === && sudo journalctl -u superdry -n 20 --no-pager 2>&1 && echo === NGINX ERRORS === && sudo tail -20 /var/log/nginx/error.log 2>&1' > ~/OneDrive/SuperDry-Atual-MIGRACAO/vm_diag.txt 2>&1"
echo.
echo Diagnostico salvo em vm_diag.txt
pause
