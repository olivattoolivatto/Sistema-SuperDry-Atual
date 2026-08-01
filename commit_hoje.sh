#!/bin/bash
# ── Commit das alterações de 20/07/2026 ──────────────────────────────────────
# Execute este script via Git Bash dentro da pasta SuperDry-Atual-MIGRACAO
# Ou cole os comandos um a um no terminal.

cd "$(dirname "$0")"

# 1. Remover index.lock travado (deixado por processo anterior)
rm -f .git/index.lock

# 2. Resetar stage e re-adicionar só os arquivos de hoje
git reset HEAD 2>/dev/null || true

git add \
  backend/server.py \
  backend/install_ollama.sh \
  backend/test_ollama.py \
  frontend/src/App.js \
  frontend/src/components/Layout.js \
  "frontend/src/pages/automation/AutomationPage.jsx" \
  memory/AI_PATTERNS.md

# 3. Confirmar o que está staged
echo ""
echo "=== Arquivos no stage ==="
git diff --cached --name-only

# 4. Fazer o commit
git commit \
  --author="Diego (SuperDry) <superdrylavagemaseco@gmail.com>" \
  -m "Automacao com IA: parser fixes B5, endpoint interpret-message, AutomationPage

PARTE 1 — Fixes urgentes no backend (server.py):

Fix 1: INFINITEPAY_REDIRECT_URL corrigida no .env local para apontar ao
  endpoint /api/payments/infinitepay/return (atualizar tambem na VM).

Fix 2: payment_received propagado ao budget pai apos cada pagamento.
  - POST /items/{id}/payment: atualiza budget.payment_received=True + payment_status
  - _apply_cp_paid(): idem, uma vez por budget distinto no loop

Fix 3: Bugs 10, 11, 12 do _smart_parse_budget corrigidos (caso Mariane B5):
  - Bug 10: _SCHEDULE_RE detecta 'Horario DD/M HH:MM' -> scheduled_date/time
  - Bug 11: _TERMS_BLOCK_RE corta parsing ao encontrar triangulo/ponto/balao/atendimento
  - Bug 12: 'edificio' adicionado ao _ADDR_KW; _COMPLEMENT_KW trata 'Apartamento/Apto'
    como client_complement em vez de criar item falso
  - Adicionado _smart_extract_value (Bug 2+3+4): extrai valor correto mesmo quando
    a descricao tem numeros; le ultimo R\$ na linha em vez de concatenar digitos
  - Adicionado _smart_extract_unit_qty: extrai unit_price/qty/total do padrao
    R\$X,XXun (Nun = R\$Y,YY)
  - Adicionado campos scheduled_date, scheduled_time, client_complement, total_pix,
    total_cash ao modelo AutoBudgetLine

PARTE 2 — Novo endpoint POST /api/automation/interpret-message:
  - Recebe {text}, roda _smart_parse_budget com todos os fixes
  - Se Ollama disponivel em localhost:11434: enriquece com llama3.2:3b
  - Se nao (VM sem modelo ainda): usa so o parser Python
  - Retorna JSON: client_name, phone, address, complement,
    scheduled_date, scheduled_time, items[], total_pix, total_cash, notes,
    client_exists, existing_client_id, source

PARTE 2 — Nova tela frontend: AutomationPage.jsx (/automation-ai):
  - Painel esquerdo: textarea para colar mensagem WhatsApp + botao Interpretar
  - Painel direito: formulario completo editavel (cliente, endereco Geoapify,
    complemento, data/hora, itens com ItemRow expansivel, totais, observacoes)
  - Botao 'Salvar + Criar Orcamento + Lancar na Agenda' e 'So salvar rascunho'
  - Registrada em App.js (/automation-ai) e Layout.js (icone Wand2)

PARTE 3 — Scripts Ollama para VM Oracle ARM:
  - backend/install_ollama.sh: instala Ollama + baixa llama3.2:3b (~2GB)
  - backend/test_ollama.py: testa disponibilidade + extracao com msg da Mariane

Teste: parser extrai corretamente 9/9 campos da mensagem Mariane de Oliveira (B5):
nome, tel, edificio, complemento, agendamento 2026-07-20 09:00, 3 itens distintos
com unit_price corretos, total PIX 510, dinheiro 460. OK"

# 5. Push
echo ""
echo "=== Fazendo push para origin/main ==="
git push origin main

echo ""
echo "=== Pronto! ==="
git log --oneline -3
