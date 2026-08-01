#!/bin/bash
set -e

ARCHIVE=~/deploy_superdry.tar.gz
BASE=/home/opc/superdry
TMP=/tmp/deploy_extract

echo "=== SuperDry Deploy Script ==="
echo ""

# Extract
echo "[1/6] Extraindo arquivos..."
rm -rf $TMP
mkdir -p $TMP
tar xzf $ARCHIVE -C $TMP
echo "OK"

# Copy files
echo "[2/6] Copiando arquivos para $BASE..."
cp $TMP/deploy_pkg/backend/server.py $BASE/backend/server.py
cp $TMP/deploy_pkg/frontend/src/pages/budgets/BudgetEditor.js $BASE/frontend/src/pages/budgets/BudgetEditor.js
cp $TMP/deploy_pkg/frontend/src/pages/ComunicacaoWhatsApp.js $BASE/frontend/src/pages/ComunicacaoWhatsApp.js
cp $TMP/deploy_pkg/frontend/src/App.js $BASE/frontend/src/App.js
cp $TMP/deploy_pkg/frontend/src/components/Layout.js $BASE/frontend/src/components/Layout.js
cp $TMP/deploy_pkg/frontend/src/services/api.js $BASE/frontend/src/services/api.js
echo "OK"

# Validate Python
echo "[3/6] Validando server.py..."
python3 -m py_compile $BASE/backend/server.py && echo "OK" || { echo "ERRO no server.py!"; exit 1; }

# Build frontend
echo "[4/6] Compilando frontend (aguarde ~2 min)..."
cd $BASE/frontend
npm run build 2>&1 | tail -5
echo "OK"

# Restart
echo "[5/6] Reiniciando serviço..."
sudo systemctl restart superdry
sleep 2

# Check status
echo "[6/6] Status do serviço:"
sudo systemctl is-active superdry && echo "superdry está RODANDO" || echo "ERRO ao iniciar o serviço"

echo ""
echo "=== Deploy concluído! ==="
echo "Acesse: http://sistema.lavesuperdry.com.br/"
