@echo off
title SuperDry — Deploy VM Oracle
echo ========================================
echo  SuperDry — Deploy para VM Oracle
echo ========================================
echo.
echo Copiando arquivos para a VM...
cd /d "%USERPROFILE%\OneDrive\SuperDry-Atual-MIGRACAO"

"C:\Program Files\Git\bin\bash.exe" -c "cd ~/OneDrive/SuperDry-Atual-MIGRACAO && scp -i oracle-vm-key.key -o StrictHostKeyChecking=no deploy_superdry.tar.gz run_deploy.sh opc@148.116.108.43:~/ && ssh -i oracle-vm-key.key -o StrictHostKeyChecking=no opc@148.116.108.43 'bash ~/run_deploy.sh'"

echo.
if %ERRORLEVEL% EQU 0 (
    echo Deploy concluido com sucesso!
    echo Acesse: http://sistema.lavesuperdry.com.br/
) else (
    echo ERRO no deploy. Verifique a conexao.
)
echo.
pause
