#!/bin/bash
# ============================================================
# SuperDry — Ativa InfinitePay Checkout no .env da VM
# Rodar UMA VEZ na Oracle VM:
#   chmod +x setup_infinitepay.sh && bash setup_infinitepay.sh
# ============================================================

ENV_FILE="/home/opc/superdry/backend/.env"

# ── Preencha antes de rodar ──────────────────────────────────
INFINITEPAY_HANDLE="superdry"  # InfiniteTag sem o $
PUBLIC_WEBHOOK_URL="https://superdry.tail287b6c.ts.net/api/webhooks/payment"
INFINITEPAY_REDIRECT_URL="https://superdry.tail287b6c.ts.net/api/payments/infinitepay/return"
# ────────────────────────────────────────────────────────────

if [ -z "$INFINITEPAY_HANDLE" ]; then
  echo "ERRO: preencha INFINITEPAY_HANDLE neste script antes de rodar."
  exit 1
fi

echo "→ Fazendo backup do .env..."
cp "$ENV_FILE" "${ENV_FILE}.bak_$(date +%Y%m%d_%H%M%S)"

# Remove entradas antigas (se existirem) e adiciona as novas
grep -v "^PAYMENT_PROVIDER\|^INFINITEPAY_HANDLE\|^INFINITEPAY_API_BASE\|^PUBLIC_WEBHOOK_URL\|^INFINITEPAY_REDIRECT_URL" "$ENV_FILE" > /tmp/env_tmp

cat >> /tmp/env_tmp << EOF

# ── InfinitePay Checkout ──────────────────────────────────
PAYMENT_PROVIDER=INFINITEPAY
INFINITEPAY_HANDLE=${INFINITEPAY_HANDLE}
INFINITEPAY_API_BASE=https://api.checkout.infinitepay.io
PUBLIC_WEBHOOK_URL=${PUBLIC_WEBHOOK_URL}
INFINITEPAY_REDIRECT_URL=${INFINITEPAY_REDIRECT_URL}
EOF

mv /tmp/env_tmp "$ENV_FILE"

echo "→ .env atualizado. Reiniciando superdry..."
sudo systemctl restart superdry
sleep 3
sudo systemctl status superdry --no-pager | head -20
echo ""
echo "✅ Pronto. Teste criando uma cobrança consolidada no sistema."
echo "   URL do webhook configurada: ${PUBLIC_WEBHOOK_URL}"
echo "   Para verificar o log de webhooks recebidos:"
echo "   tail -f /home/opc/superdry/backend/webhook_recebidos.log"
