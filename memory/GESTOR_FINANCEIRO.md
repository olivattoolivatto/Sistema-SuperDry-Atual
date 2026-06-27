# Gestor Financeiro (estilo Organizze) — Arquitetura

Documento de referência para o **Gerenciador Financeiro** do SuperDry: controle de
contas bancárias, cartões de crédito e lançamentos de despesas/receitas para a
**empresa (PJ)** e para o **pessoal (PF)** do dono.

Estado atual: **tela "Gerenciador Financeiro" existe como placeholder** (sem página
`FinanceManager.js` ainda; `dashboard/summary` devolve `finance_summary.available=false`,
`server.py:5462`). Este doc define o que será construído, incrementalmente.

> Complementa [INTEGRACOES_PAGAMENTO.md](INTEGRACOES_PAGAMENTO.md) (lado **contas a receber** /
> cobrança de clientes via InfinitePay). Este doc trata do lado **gestão/contas a pagar** e
> conciliação Open Finance (Nubank Empresarial + InfinitePay).

---

## 0. Handoff para nova sessão (25/06/2026)

Esta seção existe para uma sessão **nova** (contexto zerado) começar a implementar sem
precisar repesquisar nada do que já foi decidido. Leia isto primeiro, depois o resto do
doc conforme precisar de detalhe.

### Onde começar
Implementar a **Fase 0** do roadmap (§12): coleções `financial_accounts`,
`financial_categories`, `financial_entries` (com `splits[]`) + seed de categorias + CRUD
backend/frontend. Nada de Open Finance/Pluggy/NF-e nesta fase — isso é fase 4/5, fica
para depois.

### O que já existe (não recriar)
- **`backend/finance_manager.py`** — scaffold completo: enums (`AccountType`, `Scope`,
  `CategoryKind`, `EntryKind`, `EntryStatus`, `EntrySource`), modelos Pydantic
  (`FinancialAccount`, `FinancialCategory`, `EntrySplit`, `FinancialEntry`), helpers de
  validação (`splits_total`, `splits_balanced`, `derive_status`) e
  `DEFAULT_CATEGORIES` (lista pronta para seed PF/PJ). **Falta apenas**: importar isso no
  `server.py`, criar os endpoints REST (§5) e ligar no Mongo (`db.financial_accounts`,
  `db.financial_categories`, `db.financial_entries` — Motor async, mesmo padrão de
  `db.clients`/`db.budgets` já usados em todo o `server.py`).
- **Nenhum endpoint `/api/finance/*` existe ainda** e **nenhuma tela** existe
  (`pages/finance/FinanceManager.js` não foi criada). O item "Gerenciador Financeiro" no
  menu (`Layout.js`) hoje é placeholder puro.
- `dashboard/summary` (`server.py`, buscar por `finance_summary`) já devolve um dict
  fixo `{cash_balance: 0, bank_balance: 0, month_revenue: 0, available: False}` — é só
  preencher de verdade quando os lançamentos existirem.

### Padrões do código a reaproveitar (evita reinventar)
- **Geração de ID sequencial**: já existe `async def _next_id(collection, prefix, zfill)`
  em `server.py` (buscar por `_next_id`) — usa aggregation pipeline pra achar o maior
  número existente. Reusar exatamente assim para `ACC-`, `CAT-`, `LCT-` (zfill=4),
  igual já é feito para `CLI-` e outros.
- **Auth/permissão de rota**: todo endpoint usa
  `current_user: UserPublic = Depends(get_current_user)` (import já no topo do
  `server.py`, vem de `auth.py`). Seguir o mesmo em `/api/finance/*`.
- **Router**: tudo pendura em `api_router = APIRouter(prefix="/api")` (linha ~158),
  registrado no `app` mais abaixo. Não criar um `FastAPI()` novo — só adicionar mais
  `@api_router.get/post/put/delete("/finance/...")` no mesmo arquivo (ou, se quiser
  organizar melhor, criar um `APIRouter` separado em outro arquivo e fazer
  `app.include_router()` dele — `server.py` já está em 5.700+ linhas, então isolar o
  módulo financeiro em arquivo próprio desde o início é uma boa ideia, mas não
  obrigatória; ninguém fez isso ainda no projeto, então não há padrão a seguir aqui).
- **UI do "split por categoria"**: usar `frontend/src/pages/budgets/ItemDetailDrawer.js`
  como referência de layout de drawer lateral — é o equivalente direto do que vai ser
  o drawer de divisão de lançamento por categoria.
- **Menu**: novo item entra em `frontend/src/components/Layout.js` (mesmo array de
  navegação por role dos outros módulos).
- **Chamadas HTTP do frontend**: centralizar em `frontend/src/services/api.js`, igual
  todo o resto (não fazer fetch solto nas páginas).

### Credenciais / acessos — o que falta e o que NÃO falta
- **Fase 0 (CRUD local) não depende de nenhuma credencial nova.** Não esperar nada do
  Diego para começar — é só modelo + endpoint + tela, com o Mongo que já está rodando.
- **`.env` atual** (`backend/.env`, não commitado) já tem: `MONGO_URL`, `DB_NAME`,
  `JWT_SECRET_KEY`, `GEOAPIFY_API_KEY`, credenciais Google Calendar,
  `PAYMENT_PROVIDER=INFINITEPAY`, `INFINITEPAY_HANDLE`, `INFINITEPAY_API_BASE`,
  `INFINITEPAY_API_KEY` (vazio), `PUBLIC_WEBHOOK_URL`, `INFINITEPAY_REDIRECT_URL`.
  **Não existe nenhuma variável `PLUGGY_*` ainda** — só vai ser necessária na Fase 5
  (Open Finance), bem mais adiante. Quando chegar lá, ver checklist em §7 (CLIENT_ID +
  CLIENT_SECRET do Pluggy, cobertura de Nubank PJ + InfinitePay).
- InfinitePay (lado AR, módulo separado) já está ativo em produção — não precisa de
  nada novo para o Gestor Financeiro.

### Fluxo de deploy (sem mudanças — mesma rotina já validada)
1. Eu edito local (pasta sincronizada via OneDrive).
2. **Diego** roda `git add <arquivos específicos>`, `git commit`, `git push` do Windows
   dele (o sandbox não tem rede pra GitHub — 403 confirmado em sessão anterior). Eu nunca
   commito/pusho por ele.
3. Eu entro na **Oracle Cloud Shell** (Chrome MCP) e faço `git pull` + rebuild do
   frontend (`npm run build`) + `chcon` (SELinux) + `systemctl restart superdry` na VM.
   Detalhes completos em `memory/INFRAESTRUTURA.md`.
4. Esse módulo, enquanto em desenvolvimento puro de modelagem/CRUD, **não precisa tocar
   a VM a cada passo** — só implantar quando tiver algo testável localmente primeiro.

### Cuidado conhecido deste ambiente
O mount do bash (`mcp__workspace__bash`) sincronizado via OneDrive pode ficar
**desatualizado por algum tempo** depois de uma edição via ferramenta de arquivo
(Edit/Write), chegando a truncar o final de arquivos grandes recém-editados em
`cat`/`tail`/`wc -l`/`git diff` no bash. **As ferramentas `Read`/`Grep` sempre refletem o
estado real e atual do arquivo** — usar elas (não o bash) pra verificar o resultado de
uma edição antes de confiar no diff.

---

## 1. Os dois lados do dinheiro

| Lado | O que é | Onde mora hoje | Integração |
|------|---------|----------------|-----------|
| **Receber (AR)** | Clientes pagam serviços | `consolidated_payments`, `payment_records` nos itens | InfinitePay (cobrança/link/PIX) + webhook |
| **Gerir (este doc)** | Contas, cartões, despesas/receitas PF e PJ | **novo** (coleções abaixo) | Open Finance (Pluggy/Belvo) lê Nubank PJ + InfinitePay |

Ponte entre os dois: toda cobrança recebida (AR) **também** vira um **Lançamento de
RECEITA** já conciliado no gestor, para o saldo refletir a entrada sem digitação dupla.

---

## 2. A ideia central — Lançamento como agregador de categorias

Hoje o sistema já tem um padrão consagrado: **Orçamento (agrupador) → Itens (linhas)**.

O gestor financeiro **reusa o mesmo padrão**:

```
Orçamento  →  Itens                    (já existe)
Lançamento →  Entradas por categoria   (novo, mesma mecânica)
```

Uma **compra** não é lançada como um valor único. É um **agrupador** que se desdobra em
linhas por categoria, e a soma das linhas fecha o valor da compra (o valor que passou no
cartão/PIX):

```
Lançamento LCT-0001  —  "Mercado Pantanal"  —  R$ 258,09  —  Cartão Nubank PJ
├── Produtos de limpeza ........ R$  23,30
├── Comida ...................... R$ 123,43
├── Itens para casa ............. R$  93,32
└── Higiene ..................... R$  18,04
                          soma =  R$ 258,09   ✅ bate com o valor da compra
```

Validação: `|soma(entradas.valor) − total_value| ≤ 0,01`. Enquanto não fecha, o
lançamento fica `A_CATEGORIZAR`. É o **diferencial sobre o Organizze**, que só permite
categoria única por lançamento.

Quando a compra vem do Open Finance (extrato), ela entra automaticamente como **um único
lançamento de R$ 258,09 com uma entrada "Não categorizado"**; o usuário abre e **divide
em categorias** (drawer igual ao `ItemDetailDrawer` dos orçamentos).

---

## 3. Modelo de dados (novas coleções MongoDB)

### `financial_accounts` — Contas e cartões (ACC-XXXX)
```
id              ACC-XXXX
name            "Nubank PJ", "Cartão Nubank", "Dinheiro", "InfinitePay"
type            CONTA_CORRENTE | CARTAO_CREDITO | DINHEIRO | POUPANCA | CONTA_PAGAMENTO
scope           EMPRESA | PESSOAL          # separa PJ de PF
institution     "Nubank", "InfinitePay", ...
opening_balance float                      # saldo inicial informado
current_balance float                      # calculado (opening + lançamentos conciliados)
# Só para CARTAO_CREDITO:
credit_limit    float
closing_day     int    # dia de fechamento da fatura
due_day         int    # dia de vencimento
# Open Finance:
openfinance     { connected, provider, item_id, account_id, last_sync }
color, icon, archived
```

### `financial_categories` — Árvore de categorias (CAT-XXXX)
```
id          CAT-XXXX
name        "Mercado", "Produtos de limpeza", "Combustível", "Folha", "Impostos"...
kind        DESPESA | RECEITA
parent_id   CAT-XXXX | null            # hierarquia (Casa > Limpeza)
scope       EMPRESA | PESSOAL | AMBOS
color, icon, archived
```
Seed inicial sugerido (ajustável):
- **DESPESA PJ:** Insumos/Produtos de lavagem, Combustível/Veículo, Folha/Comissões,
  Impostos/Taxas, Marketing, Manutenção/Equipamentos, Aluguel, Energia/Água, Software.
- **DESPESA PF:** Mercado, Produtos de limpeza, Comida, Itens para casa, Higiene,
  Saúde, Educação, Lazer, Transporte, Moradia.
- **RECEITA:** Serviços (ponte AR), Outras receitas, Aportes.

### `financial_entries` — Lançamentos / o AGREGADOR (LCT-XXXX)
```
id             LCT-XXXX
kind           DESPESA | RECEITA | TRANSFERENCIA
scope          EMPRESA | PESSOAL
account_id     ACC-XXXX                  # conta/cartão usado
date           competência (quando ocorreu)
paid_date      caixa (quando saiu/entrou o dinheiro)
establishment  "Mercado Pantanal" / contraparte
total_value    float                     # valor da compra (bate com cartão/PIX)
payment_method PIX | CREDITO | DEBITO | DINHEIRO | BOLETO | TRANSFERENCIA
installments   { n: 1, total: 1 }        # parcelamento de cartão
status         A_CATEGORIZAR | PENDENTE | PAGO | CONCILIADO
splits         [ { category_id, description, value } ]   # << as linhas por categoria
source         MANUAL | OPENFINANCE | WEBHOOK
openfinance_tx_id   string | null        # dedupe da importação
reconciled     bool
invoice_id     FAT-XXXX | null           # se for compra no cartão, aponta p/ fatura
attachments    [urls de nota fiscal]
recurring_id   REC-XXXX | null
notes
```
Invariante: `sum(splits.value) == total_value` (tolerância 0,01) para sair de
`A_CATEGORIZAR`.

### (Fase 2) `credit_card_invoices` — Faturas (FAT-XXXX)
```
id, account_id (cartão), reference_month, closing_date, due_date,
total, status (ABERTA | FECHADA | PAGA), paid_with_account_id
```
Lançamentos de cartão entram na fatura do mês; pagar a fatura = transferência da conta
corrente que zera o ciclo.

### (Fase 3) `financial_recurring` — Recorrências (REC-XXXX)
Aluguel, salários, assinaturas → geram lançamentos automáticos previstos.

---

## 4. Conciliação via Open Finance (Nubank Empresarial + InfinitePay)

> **Nubank não tem API pública direta.** Acesso só via **agregador Open Finance**
> regulado (Pluggy ou Belvo), que conecta Nubank PJ, InfinitePay, etc. e entrega um feed
> de transações. Confirmado.

Fluxo:
```
Pluggy Connect (widget) → usuário linka Nubank PJ + InfinitePay
   ↓ (sync periódico / webhook do agregador)
fetch_recent_transactions()  → [ {amount, date, description, counterparty, tx_id} ]
   ↓ para cada transação nova (dedupe por openfinance_tx_id):
cria Lançamento  status=A_CATEGORIZAR, source=OPENFINANCE,
                 1 split "Não categorizado" = total
   ↓
usuário abre o drawer e divide em categorias  →  status=CONCILIADO
```
Esqueleto pronto: `payment_providers.py::PluggyReconciliation.fetch_recent_transactions`
(linha ~184). Falta implementar a chamada real ao ativar.

Conciliação AR ↔ extrato: PIX recebido de cliente casa por `valor` + `txid`/descrição
com `consolidated_payments` PENDENTES → marca PAGO (já previsto em
[INTEGRACOES_PAGAMENTO.md](INTEGRACOES_PAGAMENTO.md) §5).

---

## 5. Endpoints REST previstos (a criar)

```
# Contas
GET/POST/PUT/DELETE   /api/finance/accounts
GET                   /api/finance/accounts/{id}/balance

# Categorias
GET/POST/PUT/DELETE   /api/finance/categories          # árvore

# Lançamentos (o agregador)
GET/POST/PUT/DELETE   /api/finance/entries
PUT                   /api/finance/entries/{id}/splits  # editar linhas por categoria
GET                   /api/finance/entries?status=A_CATEGORIZAR   # fila p/ categorizar

# Open Finance
POST                  /api/finance/openfinance/connect-token   # token do widget Pluggy
POST                  /api/finance/sync                        # puxa transações → lançamentos
POST                  /api/webhooks/openfinance                # push do agregador

# Relatórios
GET                   /api/finance/reports/by-category?scope=&from=&to=
GET                   /api/finance/reports/cashflow            # fluxo de caixa mensal
```

Dashboard: preencher `finance_summary` real em `dashboard/summary` (`server.py:5462`):
`cash_balance`, `bank_balance`, `month_revenue`, `month_expense`, `available=true`.

---

## 6. Frontend previsto

- Nova página `pages/finance/FinanceManager.js` (rota `/financeiro/gestor`, item no Layout).
- Telas: **Contas** (cards estilo Organizze com saldo), **Categorias** (árvore),
  **Lançamentos** (lista + filtros), **Drawer de divisão por categoria** (reusa padrão do
  `ItemDetailDrawer.js`), **Relatórios** (pizza por categoria, fluxo de caixa).
- Separador **PF / PJ** (toggle de `scope`) no topo.

---

## 7. O que precisa ser provido (checklist do usuário)

### InfinitePay (cobrança automática de clientes — lado AR)
- [ ] Conta lojista InfinitePay ativa (CNPJ)
- [ ] **API Key** + **Webhook Secret** (painel → Desenvolvedores/API)
- [ ] Confirmar que o plano dá acesso à **API de cobranças** (link/PIX dinâmico), não só maquininha
- [ ] Documentação real da API vigente (endpoint de criar cobrança + formato do webhook)

### Open Finance (Nubank Empresarial + InfinitePay — lado gestão)
- [ ] Escolher agregador: **Pluggy (recomendado p/ BR/Nubank)** ou Belvo
- [ ] Cadastro no agregador → **CLIENT_ID + CLIENT_SECRET** (tem sandbox grátis)
- [ ] Confirmar no agregador que cobre **Nubank PJ** e **InfinitePay**
- [ ] CNPJ + acesso para conectar as contas pelo fluxo do agregador

### Infra (já em INTEGRACOES_PAGAMENTO.md §2)
- [ ] VM (Proxmox) com Python 3.11 / Node / MongoDB
- [ ] Cloudflare Tunnel + subdomínio `sistema.lavesuperdry.com.br` (p/ webhooks)

### Decisões de produto
- [ ] Separar PF e PJ no mesmo sistema? (default: **sim**, via `scope`)
- [ ] Importar histórico via OFX/CSV ou só daqui pra frente? (default: **só daqui pra frente** + import OFX como fase 2)

---

## 7b. Decisões tomadas (2026-06-03)

- **Ordem de implementação:** InfinitePay primeiro (cobrança de clientes), depois gestor local, depois Open Finance.
- **Agregador Open Finance:** **Pluggy** (já é o esqueleto padrão em `payment_providers.py`).
- **Feito sem credenciais:** `create_consolidated_payment` agora é *provider-aware* — em modo
  gateway (`PAYMENT_PROVIDER≠MANUAL`) cria a cobrança via `provider.create_charge`, guarda
  `external_charge_id`/`payment_link`/`pix_qr`, marca tudo `PENDENTE` e só aplica nos itens
  quando o webhook confirma. Caminho MANUAL inalterado. (server.py, tarefa §4 de INTEGRACOES.)
- **Bloqueado aguardando você:** API Key + Webhook Secret do InfinitePay e o **shape real**
  da API de cobrança/webhook para preencher `InfinitePayProvider.create_charge/parse_webhook`.

## 8. Roadmap incremental

1. **Modelos + coleções** (`finance_manager.py` scaffold) + seed de categorias.
2. **CRUD Contas e Categorias** (backend + telas).
3. **Lançamentos com divisão por categoria** (o agregador — coração do módulo).
4. **Dashboard `finance_summary` real** + relatório por categoria.
5. **Ativar InfinitePay** (cobrança real + webhook) — 5 tarefas em INTEGRACOES_PAGAMENTO.md §4.
6. **Open Finance / Pluggy** — sync de Nubank PJ + InfinitePay → fila A_CATEGORIZAR.
7. **Faturas de cartão + recorrências** (fases 2/3).

---

## 9. Estudo do Organizze (referência direta do produto)

Pesquisa feita em 2026-06-24 a pedido do Diego — o Organizze é o produto-referência
explícito para este módulo ("réplica dele com algumas melhorias"). Resumo do que ele
oferece hoje:

- **Conexão Bancária (Open Finance):** a partir do **Plano Conectado**; importa
  lançamentos de conta e cartão com 1 clique. Bancos cobertos: Nubank, Itaú, BB,
  Bradesco, Santander, Caixa, Inter, C6, Sicredi, Mercado Pago, XP, Sicoob, BTG, PicPay.
- **Planos:** Manual (~R$35/mês) vs Conectado (~R$45/mês) — confirma que Open Finance é
  feature paga/premium até para eles, ou seja, é aceitável fasear (manual primeiro).
- **Contas e cartões num só lugar:** corrente, poupança, investimento, cartão —
  exatamente o que já está modelado em `financial_accounts`.
- **Cartão/Fatura:** tela de fatura mostra limite total, limite disponível, fechamento,
  vencimento, situação (aberta/fechada/paga) e valor total — bate com a Fase 2
  `credit_card_invoices` já prevista (§3).
- **Categorias personalizadas + orçamento por categoria:** define teto de gastos por
  categoria/mês e alerta antes de estourar — equivalente ao que o esqueleto do Gemini
  chama de `Budgets` (`amount_limit`, `period`, `alert_percentage`). **Não tínhamos essa
  peça ainda — adicionar como nova coleção `financial_budgets` (§10 abaixo).**
- **Lançamento parcelado/recorrente:** campo "Repetir" cobre tanto recorrência fixa
  (aluguel) quanto parcelamento (cartão N de M) — confirma o design já previsto em
  `installments` + `financial_recurring` (Fase 3), mas mostra que vale unificar os dois
  num único campo "Repetir" na UI mesmo que sejam coleções diferentes no backend.
- **Metas (Goals):** objetivo financeiro de longo prazo (ex: "viajar", "reserva de
  emergência") com valor-alvo e prazo — feature nova, não prevista no esqueleto atual.
  Vale anotar como Fase 4 (`financial_goals`), não é prioridade do MVP.
- **Transferência entre contas:** tipo de lançamento dedicado (não é despesa nem
  receita) — já cobrimos via `kind: TRANSFERENCIA` em `financial_entries`.
- **Contas compartilhadas (casal/sócios):** cada pessoa lança manualmente, ambos veem o
  mesmo extrato — relevante para o caso PF/PJ do Diego: dá pra tratar com `scope` +
  multiusuário (já existe sistema de roles), sem precisar de feature nova.
- **Limite:** o Organizze permite só **uma categoria por lançamento**. O split por
  múltiplas categorias num único lançamento (nosso `financial_entries.splits`) é
  diferencial real do SuperDry sobre o produto original — mantido como o coração do
  módulo.

---

## 10. Camada tributária e NF-e (a partir do esqueleto trazido pelo Diego/Gemini)

Peça nova, **não existe no Organizze** nem no scaffold atual — vem do brainstorm com
Gemini. Objetivo: ao escanear/importar uma nota fiscal (NF-e/NFC-e) de uma compra PF ou
PJ, o sistema já entra com o lançamento **pré-dividido por categoria com o imposto
embutido calculado por item**, em vez do usuário categorizar manualmente.

### 10.1 Nova coleção: `financial_invoices` (NFE-XXXX)
*(equivalente ao `InvoicesNF` do esqueleto, com nossa convenção de ID prefixado)*
```
id              NFE-XXXX
access_key      string (44 dígitos, chave da NF-e/NFC-e) — único
raw_xml_url     string  # XML bruto salvo (uploads/nfe/)
qr_code_url     string | null  # se capturado via QR Code do cupom
issuer_name     string  # razão social do emitente
total_value     float
total_taxes     float   # soma aproximada ICMS+ISS+PIS+COFINS via IBPT
tax_percentage  float   # total_taxes / total_value
items           [ {xProd, vProd, suggested_category_id, tax_amount} ]  # linhas brutas do XML
entry_id        LCT-XXXX | null   # lançamento gerado a partir desta nota
status          PENDENTE_REVISAO | PROCESSADA | FALHA
created_at
```

### 10.2 Pipeline de leitura (cron/sob demanda, backend FastAPI)
```
1. Captura: usuário cola o qr_code_url do cupom OU sobe o XML.
2. Parser baixa/lê o XML e extrai:
   - cabeçalho: emitente, data, valor total, <vTotTrib> (tributos aproximados)
   - itens: xProd (nome do produto), vProd (valor), proporção de imposto por linha
3. Categorização automática (motor de inteligência):
   a) Busca se aquele xProd exato já foi categorizado antes pelo usuário
      (tabela de aprendizado simples: {produto_normalizado → category_id}).
   b) Se não houver histórico, despacha o texto do item para a API do Claude
      (mesmo padrão usado no parser inteligente de Automações) pedindo a categoria
      mais provável dentre as cadastradas em financial_categories.
4. Monta o lançamento sugerido (ver payload §10.4) e devolve pra tela de revisão —
   o usuário confirma/ajusta antes de salvar definitivamente (nunca grava direto).
```
Observação: cálculo de tributo por item usa o percentual global da nota
(`tax_percentage`) aplicado proporcionalmente ao `vProd` de cada item, salvo quando o
XML já trouxer `vTotTrib` discriminado por item (raro fora de NFC-e detalhada).

### 10.3 Impacto no `financial_entries.splits`
Cada split ganha um campo novo: `tax_amount` (valor de imposto embutido naquele split
específico) — não existia antes. Isso alimenta um relatório novo: "quanto foi pago em
imposto por categoria/mês", que nem o Organizze tem.

### 10.4 Payload de sugestão (NF-e → tela de revisão)
```json
{
  "invoice_id": "NFE-0001",
  "access_key": "35260612345678901234567890123456789012345678",
  "total_taxes": 37.80,
  "tax_percentage": 21.00,
  "suggested_entry": {
    "date": "2026-06-24",
    "establishment": "Carrefour Comercio Ltda",
    "total_value": 180.00,
    "kind": "DESPESA",
    "scope": "PESSOAL",
    "account_id": null,
    "splits": [
      {"category_id": "CAT-0012", "value": 100.00, "tax_amount": 15.50, "description": "ARROZ TIO JOAO 5KG"},
      {"category_id": "CAT-0007", "value": 50.00, "tax_amount": 12.30, "description": "SABAO PO OMO 1KG"},
      {"category_id": "CAT-0009", "value": 30.00, "tax_amount": 10.00, "description": "CREME DENTAL COLGATE"}
    ]
  }
}
```
Payload de confirmação = o mesmo shape de `POST /api/finance/entries`, acrescido de
`invoice_id: "NFE-0001"` para amarrar o lançamento final à nota que o originou.

### 10.5 Endpoints novos
```
POST   /api/finance/invoices/parse        # recebe XML ou qr_code_url, devolve sugestão (não grava)
POST   /api/finance/invoices/{id}/confirm # grava o lançamento definitivo a partir da sugestão revisada
GET    /api/finance/invoices              # histórico de notas processadas
GET    /api/finance/reports/taxes?scope=&from=&to=   # total pago em imposto por categoria/mês
```

---

## 11. Diferenças entre o esqueleto do Gemini e nosso padrão — decisões a manter

O documento trazido por Diego usa `UUID` puro e nomes em inglês (`Transactions`,
`TransactionSplits`, `Accounts`). Para manter consistência com o resto do sistema
(`ORC-XXXXXXX`, `ITM-XXXXXXX`, `CLI-XXXX`), a tradução adotada é:

| Esqueleto (Gemini) | SuperDry (já decidido em §3, mantido) |
|---|---|
| `Accounts` | `financial_accounts` (ACC-XXXX) |
| `CreditCards` | mesma coleção `financial_accounts`, `type=CARTAO_CREDITO` |
| `Categories` | `financial_categories` (CAT-XXXX) |
| `Budgets` | **novo** `financial_budgets` (BGT-XXXX) — ver abaixo |
| `BankIntegrations` | embutido em `financial_accounts.openfinance{}` |
| `Transactions` | `financial_entries` (LCT-XXXX) |
| `TransactionSplits` | `financial_entries.splits[]` (embedded, não coleção própria — mesmo padrão Orçamento→Itens) |
| `InvoicesNF` | `financial_invoices` (NFE-XXXX) — §10 |

### Nova coleção `financial_budgets` (BGT-XXXX) — orçamento por categoria/mês
```
id               BGT-XXXX
category_id      CAT-XXXX
scope            EMPRESA | PESSOAL
amount_limit     float
period           "YYYY-MM"
alert_percentage int   # default 80
```
Regra: ao salvar um split em `financial_entries`, somar todos os splits daquela
`category_id` no `period` corrente e comparar com `amount_limit` — dispara alerta na UI
(toast/badge) ao cruzar `alert_percentage`, igual ao Organizze.

---

## 13. Pesquisa: lista de bancos, integração Open Finance/Pluggy e importador de NF-e (2026-06-25)

Pesquisa feita a pedido do Diego para validar com fontes reais o que estava especulado
em §4 (Open Finance) e §10 (NF-e), antes de implementar essas fases.

### 13.1 Lista de bancos com código + nome + ícone

Três fontes, propósitos diferentes — **nenhuma delas é "o sistema Open Finance"
sozinho**:

- **Bacen (oficial):** tabela de participantes do STR. Traz **ISPB** (8 dígitos,
  obrigatório e único para toda instituição no SPB) e **COMPE** (3 dígitos, legado, só
  para quem participa de compensação de cheque — várias fintechs/IPs não têm). PDF
  atualizado diariamente, sem ícone. Espelhos abertos em CSV/JSON existem no GitHub
  (`guibranco/BancosBrasileiros`).
- **Open Finance Brasil (diretório oficial):** lista as instituições certificadas no
  ecossistema regulatório, com API Explorer e CSV exportável. Metadado regulatório, sem
  ícone.
- **Pluggy `/connectors` (prático, o que resolve o ícone):** cada conector devolve `id`,
  `name`, `imageUrl` (logo em SVG/PNG), `primaryColor`, `institutionUrl`, tipo
  (PF/PJ/investimento) e país. **É essa a fonte a usar** quando chegarmos na Fase 5, para
  popular o seletor de instituição na tela de Contas com ícone real — não precisa cruzar
  com Bacen/diretório oficial para fins visuais.

Conclusão: o Open Finance (ecossistema regulatório) não entrega ícone por si só; quem
entrega é o agregador (Pluggy) que consome o Open Finance por debaixo.

### 13.2 Como funciona a integração Pluggy/Open Finance (fluxo real, documentado)

```
Pluggy Connect (widget) gera connectToken
   ↓ usuário autoriza login no banco dentro do widget
cria-se um Item (a "conexão" com aquela instituição)
   ↓ webhooks (configurar todos os 3):
   item/created, item/updated, item/error         → status da conexão
   transactions/created                            → vem com createdTransactionsLink
                                                      (paginar esse link pra buscar as
                                                      transações novas, página de 500)
   transactions/updated  { transactionIds: [...] } → rebuscar só esses IDs em /transactions
   transactions/deleted  { transactionIds: [...] } → apagar esses IDs localmente
```

Campos de cada transação relevantes para nós: `id` (usar como `openfinance_tx_id` para
dedupe — **pode mudar** se o banco corrigir data/descrição/valor depois, daí o evento
`transactions/updated`/`deleted` existir), `description`, `amount` (sinal diferente para
cartão de crédito: positivo = débito/gasto, negativo = pagamento da fatura), `date`,
`balance` (saldo pós-lançamento, só em parte das instituições), `category` (exige plano
**Pro** da Pluggy — não confiar nisso, manter nosso próprio motor de categorização),
`paymentData` (payer/receiver com nome, CPF/CNPJ, agência, conta, ISPB — preenchido em
PIX/TED/boleto, útil pra sugerir estabelecimento/categoria), `creditCardMetadata`
(parcelas).

Mapeamento direto pro nosso modelo: cada transação nova → 1 `financial_entries` com
`source=OPENFINANCE`, 1 split único `"Não categorizado"` = `total_value`,
`status=A_CATEGORIZAR`, gravando `openfinance_tx_id`. Confirma o desenho do §4; só
adicionar tratamento explícito do `transactions/deleted` (não estava no esqueleto
original).

**Ponto em aberto, não confirmado:** a tabela de cobertura por conector publicada pela
Pluggy (`/docs/connectors-coverage`) consultada agora **não trouxe "Nubank" na lista**
(nem PF nem PJ) entre os conectores Personal/Business exibidos. Pode ser recorte da
página/paginação, ou o Nubank PJ pode entrar por outro canal (ex.: conector regulado
Open Finance em vez de conector "direto"). **Antes de iniciar a Fase 5, conferir
diretamente no dashboard da Pluggy** (ou pedir confirmação ao suporte deles) se Nubank
Empresarial está coberto — não assumir.

### 13.3 Importador de NF-e/NFC-e com split por item — refinamento do §10

Confirma que o desenho do §10 é viável tecnicamente (o XML da nota traz exatamente os
dados necessários: `<det><prod><xProd>` = descrição do item, `<vProd>` = valor do item,
soma bate com o total da nota), mas duas coisas precisam ser ajustadas:

**(a) Duas trilhas de captação, não uma só:**
- **NF-e (modelo 55) contra o CNPJ da SuperDry** — compras de fornecedor. Existe o
  webservice oficial **NFeDistribuicaoDFe** (SEFAZ/Receita) que permite **buscar
  automaticamente e de forma recorrente** todas as notas emitidas contra um CNPJ — é o
  canal que sistemas de contabilidade usam para não depender do fornecedor mandar nada.
  Gratuito, mas exige **certificado digital A1 (e-CNPJ)** carregado no backend e
  comunicação SOAP/XML — complexidade real de implementar, porém é o único caminho
  verdadeiramente automático (sem o usuário escanear nada).
- **NFC-e (modelo 65) de compras avulsas (ex.: mercado pago com CPF)** — não tem
  distribuição automática para quem não é o emitente. O caminho é ler a chave de acesso
  (44 dígitos) ou o QR Code do cupom (foto ou digitação manual) e consultar via API de
  terceiros — **Focus NFe** ou **Webmania** — que devolvem o XML já estruturado por item.
  Sob demanda, não automático; depende do usuário capturar o QR/chave.

**(b) Regra fiscal nova que afeta diretamente a pergunta do Diego (NF-e vs cupom para
PJ):** desde **03/11/2025 (Ajuste SINIEF 11/2025)**, NFC-e (modelo 65) **não pode mais
ser emitida com CNPJ no destinatário** — passou a ser exclusiva para venda a pessoa
física (CPF). Antes dessa data, era possível pedir CNPJ no caixa e o cupom carregar
`<dest><CNPJ>`.

**Decisão de design corrigida (2026-06-25, a pedido do Diego):** o importador **não
decide PJ/PF nem pelo tipo de documento nem pelo `<dest>` do XML.** O `scope` do
lançamento é simplesmente **herdado da conta/cartão escolhido na importação**
(`financial_entries.account_id` → `financial_accounts.scope`), exatamente como já
funciona no lançamento manual — é o `account_id` que sempre define EMPRESA ou PESSOAL,
não a nota em si. Mais simples e mais correto: o que importa pra fechar o saldo é de qual
conta saiu o dinheiro, não o que está escrito no XML.

O `<dest><CPF|CNPJ>` do XML passa a servir só como **alerta de divergência fiscal**, não
como decisor: se a conta escolhida é PJ mas a nota saiu em CPF (porque não pediu CNPJ no
caixa — e desde 03/11/2025 o NFC-e nem pode mais sair em CNPJ), a tela de revisão mostra
um aviso ("nota em nome de pessoa física lançada em conta empresarial — pode não ser
dedutível/registrável como despesa PJ") e o usuário decide o que fazer (manter, tratar
como reembolso/retirada de sócio, etc.) — nunca bloqueia ou re-roteia automaticamente.

Isso não exige nenhum campo novo no modelo §10.1 (`financial_invoices`); só ajusta a
lógica do payload §10.4: `scope` no `suggested_entry` vem do `account_id` selecionado
(ou fica em branco até o usuário escolher a conta), e um novo campo opcional
`dest_mismatch_warning: string | null` é adicionado ao payload para carregar o aviso de
divergência quando aplicável.

---

## 12. Roadmap atualizado (substitui §8, mais granular)

1. **Fase 0 — Fundação:** coleções `financial_accounts`, `financial_categories`,
   `financial_entries` (com `splits[]`) + seed de categorias PF/PJ + CRUD básico
   backend/frontend (`FinanceManager.js`).
2. **Fase 1 — Orçamento por categoria:** `financial_budgets` + alerta de teto na UI.
3. **Fase 2 — Faturas de cartão:** `credit_card_invoices`, ciclo fechamento/vencimento.
4. **Fase 3 — Recorrência/parcelamento:** `financial_recurring` + campo unificado
   "Repetir" na UI (cobre fixo e parcelado).
5. **Fase 4 — NF-e e tributos:** `financial_invoices` + pipeline de parser/categorização
   via Claude + relatório de impostos por categoria (§10).
6. **Fase 5 — Open Finance:** Pluggy conectando Nubank PJ + InfinitePay → fila
   `A_CATEGORIZAR` (já detalhado em §4).
7. **Fase 6 — Metas (Goals):** `financial_goals`, opcional, baixa prioridade.

Importante: este módulo **não toca o banco de produção** durante o desenvolvimento —
só passa a interagir com a VM quando formos efetivamente implantar (conforme a regra
vigente de só alterar dados direto na VM). Toda a fase de modelagem/código pode ser
feita localmente e sincronizada depois.

---

## 14. Redesign Home/Lançamentos estilo Organizze + status pago/não-pago (2026-06-25)

Implementado em `backend/finance_routes.py` e `frontend/src/pages/finance/FinanceManager.js`.

- **Home ("Saldo geral")**: card de gradiente com saldo atual + previsão (quando
  diferem), badges de "atrasado(s)" e "a categorizar" clicáveis (levam para
  Lançamentos), lista de contas com saldo atual/previsto — espelha a tela inicial do
  Organizze.
- **Lançamentos ("Fluxo de caixa")**: lista agrupada por dia com total do dia, filtros
  por conta/tipo/categoria, busca por estabelecimento/descrição/observação, ordenação
  por data, linha lateral colorida para atrasado (vermelho) e pendente (âmbar).
- **Status pago/não-pago**: decisão deliberada de **não criar campo novo** — reusa o
  `EntryStatus` já existente (`A_CATEGORIZAR | PENDENTE | PAGO | CONCILIADO`).
  `SETTLED_STATUSES = [PAGO, CONCILIADO]` = "pago"; `PENDING_STATUSES = [PENDENTE,
  A_CATEGORIZAR]` = "não pago". "Atrasado" é um indicador derivado (`is_overdue`,
  calculado em `_annotate_entry`), não um status armazenado: lançamento com status em
  `PENDING_STATUSES` cuja `date` já passou. Botão "Marcar como pago" faz
  `PUT /entries/{id}` com `status=PAGO` + `paid_date=hoje`.
- **Backend**: `/api/finance/entries` ganhou filtros completos (`status`, `account_id`,
  `kind`, `category_id`, `search` via regex, `only_overdue`, `date_from`/`date_to`,
  `sort_by`/`sort_dir`, `limit`) e `/api/finance/summary` passou a devolver
  `total_current_balance`, `total_forecast_balance`, `overdue_count`,
  `to_categorize_count` junto da lista de contas com saldo.

---

## 15. Visão combinada PF+PJ ("Visão Geral") + cores por ambiente (2026-06-25)

Pedido do Diego: por ser **MEI**, ele mistura bastante as finanças PF/PJ na prática e
precisava de um terceiro modo que mostre tudo junto (além de PJ-only e PF-only), e de
**codificação por cor** para nunca perder de vista em qual ambiente está navegando.

### 15.1 Visão Geral (AMBOS como parâmetro de navegação)

O enum `Scope` (`backend/finance_manager.py`) já tinha três valores: `EMPRESA`,
`PESSOAL`, `AMBOS` — mas `AMBOS` só era usado como propriedade **armazenada** numa
categoria (`financial_categories.scope`), significando "essa categoria vale para os
dois ambientes". Em vez de criar um quarto valor ou um campo novo, **reaproveitamos o
mesmo `AMBOS`** com um segundo significado, dependente de contexto: como **parâmetro de
navegação/query** (`?scope=AMBOS` ou ausência de `scope`), ele significa "não filtrar,
mostrar PF+PJ combinados".

Os dois significados não colidem porque vivem em camadas diferentes (filtro de query vs
valor de campo gravado) e ficam documentados explicitamente no código:

```python
# backend/finance_routes.py
def _scope_filter(scope: Optional[str]) -> Dict[str, Any]:
    """`None` ou `AMBOS` = visão combinada (sem filtro, retorna tudo) — diferente do uso
    de AMBOS como valor de escopo *armazenado* numa categoria (que significa "aplica-se
    aos dois"). Aqui é o parâmetro de navegação do usuário MEI que quer ver as finanças
    misturadas."""
    if not scope or scope == Scope.AMBOS.value:
        return {}
    return {"scope": scope}
```

Usado em `list_accounts`, `get_finance_summary` (saldo geral + contadores de atrasado/a
categorizar) e `list_entries`. `list_categories` manteve lógica própria (porque lá
`AMBOS` já tinha o outro significado de "categoria compartilhada"):
`scope and scope != AMBOS` → filtra por `{scope, AMBOS}`; senão (incluindo
`scope=AMBOS`) devolve todas.

### 15.2 Frontend: terceira opção + separação navegação vs formulário

`SCOPES` (navegação/toggle de página, 3 opções: Empresa/Pessoal/Visão Geral) vs
`ENTRY_SCOPES = SCOPES.filter(s => s.value !== 'AMBOS')` (formulários de
conta/lançamento, só 2 opções) — uma conta ou lançamento individual sempre precisa de um
dono real (PJ ou PF); só a **navegação** pode estar em modo combinado. Ao abrir o drawer
de lançamento em modo combinado, `defaultScope='AMBOS'` é normalizado para `EMPRESA`
antes de virar o valor inicial do formulário.

Quando a página está em "Visão Geral" (`scope === 'AMBOS'`), cada conta/lançamento exibe
um badge **PJ**/**PF** individual (`scopeBadgeLabel(item.scope)`) para não perder a
identificação do ambiente de origem mesmo estando tudo junto na lista.

### 15.3 Cores por ambiente (azul PJ / verde PF / violeta Visão Geral)

Pedido explícito do Diego: azul para tudo relacionado a PJ (Empresa), verde para PF
(Pessoal), em botões, bordas, cabeçalhos e badges — para identificar visualmente o
ambiente sem precisar ler o texto.

```javascript
const BRAND_BLUE = '#1F4E8C';   // Empresa (PJ) — já era a cor de marca do sistema
const BRAND_GREEN = '#8CC63F';  // Pessoal (PF) — já era a cor de marca do sistema
const AMBOS_COLOR = '#6D5BD0';  // Visão Geral — cor própria, nem azul nem verde
const SCOPE_COLOR = { EMPRESA: BRAND_BLUE, PESSOAL: BRAND_GREEN, AMBOS: AMBOS_COLOR };
const scopeAccent = (s) => SCOPE_COLOR[s] || AMBOS_COLOR;
const scopeBadgeLabel = (s) => (s === 'EMPRESA' ? 'PJ' : s === 'PESSOAL' ? 'PF' : 'Geral');
```

Aplicado de forma consistente (tudo passa por `scopeAccent`, nada de cor hardcoded
espalhada): toggle de escopo no topo (cada opção tintada na sua própria cor, mesmo
inativa), pílula de badge do ambiente atual no cabeçalho, abas (borda/texto da aba ativa),
botões "Novo/Nova" em cada tela, borda lateral colorida nos cards de conta e nas linhas
de lançamento, ícone de tipo de conta, header do drawer de lançamento (borda + badge
PJ/PF conforme o escopo escolhido no formulário), card "Saldo geral" da Home (gradiente
de duas cores — azul→verde — no modo combinado, gradiente de uma cor mais escura da
mesma família no modo PJ-only/PF-only).

Cores reaproveitam a identidade visual já existente do sistema (`#1F4E8C`/`#8CC63F`, as
mesmas dos PDFs de orçamento) — não foram inventadas cores novas para PJ/PF, só
estendidas para este módulo.

---

## 16. Correção: categoria com escopo "Ambos" não pode mais ser uma entidade compartilhada (2026-06-26)

**Bug reportado pelo Diego:** ao criar uma categoria com escopo "Ambos PF/PJ", o sistema
gravava **um único documento** (`scope=AMBOS`) que aparecia tanto na visão PJ quanto na
visão PF — mas era a mesma entidade. Excluir (ou editar) essa categoria a partir de
qualquer uma das visões afetava a outra também, porque não eram duas categorias, era uma
só sendo exibida em dois lugares.

**Correção:** "Ambos" na criação passou a ser só um atalho de tela — o backend agora
**cria duas categorias de fato independentes** (uma `scope=EMPRESA`, uma
`scope=PESSOAL`), cada uma com seu próprio `CAT-XXXX`, sem nenhum vínculo entre si depois
de criadas. Editar ou excluir uma não afeta a outra.

- **`create_category`** (`finance_routes.py`): se `scope == AMBOS`, faz fan-out e insere
  dois documentos (`_category_doc` helper), retornando os dois; caso contrário,
  comportamento de sempre (um documento).
- **`update_category`**: passou a **rejeitar** `scope=AMBOS` (`400`) — uma categoria já
  criada nunca pode "voltar" a ser compartilhada; só pode ser `EMPRESA` ou `PESSOAL`.
  Isso também serve como correção manual para categorias legadas: editar uma categoria
  antiga com `scope=AMBOS` e escolher Empresa ou Pessoal a converte numa categoria
  independente real (criar manualmente o par do outro lado, se quiser as duas).
- **`seed_categories`**: as entradas de `DEFAULT_CATEGORIES` com `scope=AMBOS`
  ("Outras receitas", "Aportes") agora também são semeadas como duas categorias
  independentes, mesma regra.
- **Frontend (`CategoryModal`)**: a opção "Ambos (PF/PJ)" do seletor de escopo só
  aparece ao **criar** uma categoria nova; ao editar uma já existente, só
  Empresa/Pessoal ficam disponíveis (reforça que depois de criada ela é sempre de um
  lado só).
- **Dados legados:** qualquer categoria criada **antes** desta correção com
  `scope=AMBOS` continua existindo como um único documento compartilhado até ser
  editada manualmente (não houve migração automática/retroativa). `list_categories`
  ainda trata esse caso de forma compatível (mostra a categoria legada nas duas visões),
  mas categorias novas nunca mais são gravadas assim.

## 17. Substituição completa da árvore de categorias (2026-06-26)

**Pedido do Diego:** ele fez um levantamento completo das categorias que quer usar
(arquivo `lista de categorias para gerenciador financeiro SD.docx`) e pediu para apagar
**todas** as categorias existentes e recriar a partir desse documento — não mesclar, não
preservar nada do conjunto anterior.

**Estrutura do documento** (extraída via `pandoc`, conferida byte a byte contra o que foi
implementado): PF e PJ, cada um dividido em Receitas e Despesas; cada bloco de Receitas/
Despesas tem categorias-pai com uma lista de subcategorias — **exceto "PJ → Receitas"**,
que no documento original é uma lista plana, sem categoria-pai. Essa exceção foi
preservada de propósito: as 8 categorias de receita PJ entram como itens de **topo**
(`parent_id=None`), sem agrupamento, exatamente como Diego organizou.

**Implementação:**

- **`finance_manager.py` → `CATEGORY_TREE`**: nova constante, lista de nós
  `{scope, kind, name, children: [...]}`. Cada nó gera uma categoria-pai (ou de topo, se
  `children` vazio) mais uma categoria por item de `children`, com `parent_id` apontando
  para o pai. `DEFAULT_CATEGORIES` foi mantida no arquivo só por compatibilidade (nenhum
  código novo a usa) — `CATEGORY_TREE` é a fonte real a partir de agora.
- **`finance_routes.py` → `POST /api/finance/categories/reset-import`**: novo endpoint
  que (1) apaga **todos** os documentos de `financial_categories` sem aplicar as
  proteções normais de `delete_category` (subcategoria/uso em lançamento) — é reset
  deliberado, não exclusão item a item; (2) recria a árvore inteira a partir de
  `CATEGORY_TREE` em duas passadas (pais primeiro, depois filhos com o `parent_id` já
  resolvido); (3) conta quantos `financial_entries` têm `splits` preenchidos (que podem
  ficar com `category_id` órfão após o reset) e devolve esse número na resposta, para
  Diego saber se precisa revisar lançamentos já categorizados.
- **Frontend (`FinanceManager.js` → `CategoriesTab`)**: botão "Resetar e importar
  categorias" (aba Categorias), com `window.confirm` de aviso antes de chamar o endpoint,
  já que a ação é destrutiva. `api.js` ganhou `financeCategoriesApi.resetImport()`.
- **Por que um endpoint e não uma migração direta no banco:** o Mongo deste ambiente é
  local (`mongodb://localhost:27017`, ver `backend/.env`), inacessível pela sandbox onde
  o código é editado — qualquer alteração de dados reais só acontece rodando o backend
  de Diego. Por isso a operação foi exposta como endpoint clicável em vez de script
  aplicado diretamente.

## 18. Conciliação do `CATEGORY_TREE` com acréscimos ao docx (2026-06-26)

Diego acrescentou itens ao mesmo `lista de categorias para gerenciador financeiro SD.docx`
(não trocou o arquivo) e pediu para conciliar — manter o que já existia, só acrescentar o
que era novo ou tinha mudado. Comparado item a item contra o `CATEGORY_TREE` então vigente
(§17); diferenças encontradas e aplicadas direto no código (sem reset de categorias — isso
só é necessário quando Diego clica em "Resetar e importar"):

- Nova categoria PF/Despesa **"Atividades Física e Hobbys"** (14 itens) — inserida antes de
  "Alimentação".
- PF/Despesa "Lazer / Desfrute / Férias" — acrescentado **"Estacionamento Shopping /
  Eventos"**.
- Nova categoria PF/Despesa **"Vestuário e Aparência"** (16 itens) — inserida depois de
  "Celulares e Comunicação".
- PF/Despesa "Despesas da casa" — acrescentado **"Gás de Cozinha GLP"**.
- Nova categoria PF/Despesa **"Governo e Burocracia"** (Imposto de Renda Daiana/Diego,
  Taxas, Impostos em geral) — antes só existia a versão PJ desse nome.
- PJ/Despesa "Marketing / Redes Sociais" → renomeada para **"Marketing / Redes Sociais e
  Fortalecimento de Marca"**, com **"Uniforme Equipe"** acrescentado.
- PJ/Despesa "Despesas Fixas da Empresa" — acrescentado **"Recarga Crédito Celular
  Marcos"**.

Tudo o mais do levantamento batia exatamente com o que já estava implementado. Lembrando:
essas mudanças só valem em produção depois que Diego clicar de novo em "Resetar e importar
categorias" (apaga tudo e recria do `CATEGORY_TREE` atualizado) — reiniciar o backend antes,
senão o processo antigo continua servindo a versão anterior.

## 19. Importador de extrato (OFX/CSV) + poller de e-mail — alternativa gratuita ao Open Finance pago (2026-06-26)

**Contexto:** Diego perguntou sobre custo de Open Finance (Pluggy/Belvo cobram por conexão
ativa/mês) e se havia alternativa gratuita. Resposta documentada na conversa: sim — todo
banco brasileiro oferece exportação de extrato em **OFX** (Open Financial Exchange, formato
padrão, estável, com `FITID` único por transação — equivalente ao `openfinance_tx_id` que já
existia no modelo) na opção "extrato para contabilidade/conciliação" do internet banking;
CSV também é aceito como fallback quando o banco não oferece OFX. Diego escolheu, entre as
opções apresentadas, a via **e-mail dedicado**: uma caixa de e-mail vigiada automaticamente
pelo servidor, sem precisar abrir o sistema pra importar manualmente.

**Arquitetura implementada:**

- **`backend/finance_import.py`** (novo): `parse_ofx_bytes()` (via `ofxparse`, lê `FITID`,
  data, valor, descrição), `parse_csv_bytes()` (parser genérico por **nome** de coluna —
  não por posição — reconhecendo variações comuns de cabeçalho em PT-BR: Data/Date,
  Valor/Amount, Descrição/Histórico, Identificador/ID; detecta `;` vs `,` como separador e
  formato de decimal brasileiro `1.234,56`), e `import_transactions()` — a função central
  que recebe `account_id` + lista de transações parseadas e cria 1 `financial_entries` por
  transação **nova** (dedupe: usa o `FITID`/identificador do arquivo quando existe, senão
  gera hash de `conta+data+valor+descrição` — ambos gravados no campo já existente
  `openfinance_tx_id`). `kind` é derivado do sinal do valor (positivo=RECEITA,
  negativo=DESPESA); `scope` herdado da conta, igual ao padrão já usado no importador de
  NF-e (§13.3). Lançamento entra com `splits=[]` → `status=A_CATEGORIZAR` automaticamente
  (via `derive_status`, sem precisar de categoria "Não categorizado" sentinela).
- **Novo valor de enum `EntrySource.EXTRATO_IMPORT`** (`finance_manager.py`) — distingue
  esses lançamentos de `MANUAL`/`OPENFINANCE`/`WEBHOOK`.
- **`POST /api/finance/entries/import-statement`** (`finance_routes.py`): upload manual
  (multipart, `account_id` + `file`) — fallback caso o e-mail automático falhe ou para
  importar um extrato pontual. Botão de upload (ícone) em cada card de conta na aba Contas
  do `FinanceManager.js`; mostra resumo (importadas/duplicadas/ignoradas) em `window.alert`.
- **`backend/email_statement_poller.py`** (novo): loop assíncrono (`asyncio`, iniciado em
  `startup_bootstrap()` do `server.py` **só se** `STATEMENT_EMAIL_USER` estiver definido no
  `.env` — senão fica desativado, sem custo nenhum em CPU/dependência). A cada N minutos
  (`STATEMENT_IMPORT_INTERVAL_MINUTES`, default 30): conecta via IMAP (`imaplib`, roda em
  thread separada via `run_in_executor` porque `imaplib` é bloqueante) na pasta configurada
  (`STATEMENT_EMAIL_FOLDER`, default INBOX), busca e-mails não lidos, extrai anexos
  `.ofx`/`.qfx`/`.csv`, identifica a conta correspondente comparando remetente/assunto
  contra o campo `institution` de cada `financial_accounts` cadastrada (ex.: conta com
  `institution="Nubank"` casa com e-mails de `@nubank.com.br` ou que mencionem "Nubank" no
  assunto), importa via `finance_import.import_transactions()`, e marca o e-mail como lido
  — **só se** achou conta correspondente; se não achar, deixa não lido de propósito (fica
  pendente pra revisão manual, não se perde silenciosamente).
- **Variáveis de `.env` necessárias para ativar** (nenhuma preenchida ainda — feature fica
  inerte até Diego configurar):
  ```
  STATEMENT_EMAIL_HOST=imap.gmail.com
  STATEMENT_EMAIL_USER=<endereço dedicado ou alias +extrato do Gmail>
  STATEMENT_EMAIL_APP_PASSWORD=<senha de app do Gmail — exige 2FA ativado na conta>
  STATEMENT_EMAIL_FOLDER=Extratos     # opcional, default INBOX
  STATEMENT_IMPORT_INTERVAL_MINUTES=30 # opcional, default 30
  ```
- **`requirements.txt`**: adicionado `ofxparse>=0.21`.

**Pendência real, não resolvida ainda — depende de Diego confirmar:** se Nubank PJ e/ou
InfinitePay realmente enviam extrato por e-mail de forma recorrente/agendada (a maioria dos
bancos brasileiros não faz isso por segurança — geralmente só notificação de transação
isolada, não extrato consolidado). Caso não enviem, o caminho funciona do mesmo jeito, só
que com Diego baixando o OFX/CSV manualmente do internet banking e **encaminhando** o
e-mail com o anexo pra caixa dedicada — ainda mais rápido que abrir o sistema e usar o botão
de upload, e exatamente o fluxo que o poller espera. Cada conta cadastrada em
`financial_accounts` precisa ter o campo `institution` preenchido com um nome que apareça
no remetente/assunto do e-mail real (ex.: "Nubank"), senão o poller não vai saber casar o
anexo com a conta.

## 20. Detecção automática de transferências entre contas próprias (2026-06-26/27)

Contexto: Diego movimenta dinheiro entre as próprias contas (PF/PJ/InfinitePay/99Pay) — sem
tratamento, isso inflaria os totais de receita/despesa. Confirmado com dados reais (extratos
Nubank PF/PJ e InfinitePay) pelo menos 3 transferências internas e uma 4a carteira (99Pay)
ainda não mapeada. Diego escolheu detecção automática via CPF/CNPJ.

Como funciona: extratos brasileiros trazem o documento da contraparte do Pix — CNPJ completo,
CPF mascarado (so 6 dígitos do meio visíveis) ou, em transferência "pra si mesmo" dentro de
conta-pagamento, CPF completo sem máscara. Cada `financial_accounts` agora tem
`holder_document` (CPF/CNPJ do titular, só dígitos). Na importação (`finance_import.py`),
`_extract_match_keys` varre a descrição da transação por essas chaves; se baterem com o
`holder_document` de outra conta já cadastrada (`_detect_transfer`), o lançamento é marcado
como transferência interna.

Bug encontrado e corrigido antes de chegar a produção: a primeira versão usava
`kind = EntryKind.TRANSFERENCIA` pra esses lançamentos. Só que `_compute_account_balance()`
(`finance_routes.py`) só soma `kind == RECEITA` ou `DESPESA` no saldo da conta — um
lançamento TRANSFERENCIA ficaria invisível pro saldo, ou seja, dinheiro que realmente
entrou/saiu "desapareceria" do saldo calculado. Corrigido: `kind` sempre segue o sinal do
valor (preserva o saldo correto); a transferência detectada só liga a flag booleana
`is_internal_transfer`, que não afeta o saldo e serve pra excluir esses lançamentos de
relatórios futuros de receita/despesa "real" (relatório ainda não existe — flag é
infraestrutura preparada).

Pendência: cada conta cadastrada na VM precisa ter `holder_document` preenchido (campo no
formulário de conta, `FinanceManager.js`) pra detecção funcionar. PJ (Nubank) -> CNPJ
25.995.295/0001-04; contas pessoais de Diego (Nubank PF, 99Pay, InfinitePay) -> CPF
016.152.691-85.

## 21. Importador de extrato em PDF, com suporte a senha (2026-06-27)

Contexto: nem todo banco oferece OFX/CSV. Diego levantou 4 "dinossauros": Caixa só manda PDF;
C6 só manda PDF protegido por senha (6 primeiros dígitos do CPF do titular); MercadoPago só dá
link de download do PDF dentro da própria plataforma (exige login, não vem por e-mail); 99Pay
só manda PDF e só se solicitado ao atendimento.

Solução — extensão do importador, não troca de arquitetura:

- `backend/finance_import.py`: nova função `parse_pdf_bytes()` via `pdfplumber` (extrai texto
  de todas as páginas, com suporte a `password` quando o PDF é protegido). Como extrato em PDF
  não tem formato estruturado, o parser é heurístico por linha
  (`_parse_pdf_lines_generic`): considera transação toda linha que começa com data
  DD/MM/AAAA(AA) e termina com valor em decimal BR (opcionalmente seguido de C/D pra
  crédito/débito explícito); o texto entre data e valor é a descrição. Existe
  `PDF_LINE_PARSERS` (dict por `institution`) pra plugar parser específico depois se o
  genérico não capturar bem algum layout, sem afetar os demais. PDF não traz ID estável de
  transação — dedupe cai sempre no hash (conta+data+valor+descrição).
- Novo campo `statement_pdf_password` em `FinancialAccount` (`finance_manager.py`) — senha do
  PDF daquela conta especificamente (ex.: C6); campo correspondente no formulário de conta
  (`FinanceManager.js`); vazio/None pra contas sem proteção.
- `parse_statement_bytes()` passou a aceitar `password`/`institution` e rotear `.pdf` pra
  `parse_pdf_bytes()`; os dois pontos de entrada (upload manual e
  `email_statement_poller.py`) repassam `account["statement_pdf_password"]`/`institution`
  automaticamente — Diego só cadastra a senha uma vez na conta.
- `requirements.txt`: adicionado `pdfplumber>=0.11.0`.

Sobre MercadoPago: PDF fica atrás de login na própria plataforma — não chega por e-mail nem é
baixável via link direto sem sessão autenticada, então o poller automático não alcança; fica
só o caminho manual (Diego baixa logado, sobe pelo botão de upload).

Sobre 99Pay: mesma limitação — só é gerado a pedido do atendimento; o caminho é Diego
solicitar periodicamente e usar o upload manual quando chegar. Pode valer criar uma tarefa
agendada (skill `schedule`) só pra lembrar Diego de pedir o extrato com regularidade.

Limitação conhecida e aceita: o parser de PDF é heurístico — pode errar em layouts fora do
padrão. Tolerável porque todo lançamento importado já nasce A_CATEGORIZAR e passa por revisão
manual de qualquer forma; se um banco específico se mostrar problemático, dá pra escrever
parser dedicado em `PDF_LINE_PARSERS` sem tocar nos demais. Ainda não testado contra PDF real
de nenhum dos 4 bancos — Diego decidiu não rodar mais localmente (banco de dados só será
movimentado direto na VM); validação fica para o primeiro upload real lá.

---

## 22. Handoff para nova sessão — achados reais nos extratos da pasta `extratos/` (2026-06-27)

**Contexto:** Diego colocou amostras reais de extrato de cada instituição na pasta conectada
`E:\OneDrive\SuperDry\EMERGENT - Novo Sistema SD\extratos\`. Esta seção documenta o que foi
encontrado analisando esses arquivos, para uma sessão nova continuar sem precisar reabrir tudo.
**Nenhum código foi alterado ainda por causa destes achados** — são bugs/lacunas identificados
por leitura, ainda pendentes de correção.

### 22.1 Arquivos da pasta e status de análise

| Arquivo | Instituição | Status |
|---|---|---|
| `extrato-nubank-pj.ofx`, `nubank-pf.ofx`, `extrato-infinitepay.ofx` | Nubank PJ/PF, InfinitePay | Analisados em sessão anterior, OK |
| `BB-PF-Extrato conta corrente - 062026.ofx` | Banco do Brasil PF | Analisado nesta sessão — achados abaixo (§22.2) |
| `BB-PJ-Extrato conta corrente - 062026.ofx` | Banco do Brasil PJ | Analisado nesta sessão — achados abaixo (§22.2) |
| `PICPAY-PF-extrato-2026-05-28-2026-06-26.csv` | PicPay PF | Analisado — só tem a linha de cabeçalho, zero transações no período (§22.3) |
| `Extrato-C6-PF.png` | C6 Bank PF | Lido (é print do extrato real) — confirma layout visual, mas é imagem, não dá pra parsear automaticamente (§22.4) |
| `extrato-C6-PF-original-com-senha-016152.pdf` | C6 Bank PF | Tentei abrir com o Read tool e não consegui (ferramenta de leitura não decodifica PDF com senha) — **não é um problema do importador**: `parse_pdf_bytes()` já usa `pdfplumber.open(..., password=...)`, que deve abrir normalmente em produção. Só não dá pra eu inspecionar o conteúdo por aqui sem rodar código. Se quiser que eu valide de verdade, preciso rodar via bash/script, não só o Read tool |
| `Extrato-Caixa-PF.pdf` | Caixa PF | Analisado — achados abaixo (§22.5) |
| `Extrato-MercadoPago-PF.pdf`, `Extrato-99pay-PF.pdf` | MercadoPago, 99Pay | Lidos, mas ainda **não foram sintetizados** — próximo passo de uma sessão nova |

### 22.2 Banco do Brasil (OFX) — 3 achados, nenhum corrigido ainda

Arquivos: `BANKID=1`, `ORG=Banco do Brasil`, `BRANCHID=2764`; PF `ACCTID=134179`, PJ
`ACCTID=133968`.

1. **Linhas de saldo, não transações reais, vêm misturadas no OFX.** O BB inclui
   `<STMTTRN>` para "Saldo Anterior" (saldo de abertura, `TRNAMT=0.00`, `FITID` e `MEMO`
   vazios) e, na conta PJ, "Saldo do dia" repetido depois de cada transação real (saldo
   corrente, `TRNAMT` **diferente de zero** — ex.: `45.35` repetido várias vezes — também
   com `FITID`/`MEMO` vazios). O filtro atual em `import_transactions()`
   (`if tx.get("amount") in (None, 0) ...: pula`) só pega o "Saldo Anterior" (que é zero);
   o "Saldo do dia" tem valor != 0 e **seria importado como lançamento falso** se não for
   filtrado. **Correção sugerida:** no parser OFX, pular qualquer `STMTTRN` cujo `NAME`
   (payee) seja "Saldo Anterior" ou "Saldo do dia" (case-insensitive), antes de devolver a
   lista de transações.
2. **FITID duplicado entre um débito e seu estorno.** O BB reusa o mesmo `FITID` para a
   transação original e para a reversão dela. Exemplos do extrato PJ: "Pagamento de
   Impostos" `-87,05` e "Estorno de Débito" `+87,05`, ambos com `FITID = 1.024`; "Vivo
   Celular" `-151,19` e seu estorno `+151,19`, ambos com `FITID = 40.931`. A chave de
   dedupe atual usa `f"{account_id}:{tx_id}"` quando existe FITID — como os dois lançamentos
   do par compartilham o mesmo FITID, **o segundo a ser processado colide com o primeiro e
   é descartado como "duplicado"**, mesmo sendo um lançamento real e distinto (a reversão).
   Resultado prático: o sistema importaria só um dos dois (provavelmente o primeiro lido),
   perdendo a baixa do estorno e deixando o saldo da conta errado por esse valor.
   **Correção sugerida:** incluir o valor (`amount`) na chave de dedupe mesmo quando há
   FITID — ex.: `f"{account_id}:{tx_id}:{amount}"` — assim a chave só colide quando FITID
   *e* valor forem iguais (duplicata real de reimportação), não quando só o FITID repete
   com sinal trocado.
3. **Pix enviado pelo BB não traz CPF/CNPJ no MEMO.** Diferente do Nubank/InfinitePay, o
   MEMO de Pix *enviado* do BB só tem o próprio nome truncado do Diego (ex.: "27/06 10:11
   DIEGO CESAR GONCALVES OLI"), sem nenhum dígito de documento — então
   `_extract_match_keys()` (a detecção automática de transferência entre contas próprias,
   §20) **não consegue casar o lado "enviado" de uma transferência BB-PF ↔ BB-PJ**. O lado
   "recebido" funciona parcialmente: às vezes o MEMO de Pix recebido traz o CNPJ "cru", sem
   pontuação (ex.: "27/06 10:11 25995295000104 DIEGO C G O" → CNPJ
   `25.995.295/0001-04`), que o regex `_RE_CNPJ` já casa (pontuação é opcional no padrão).
   Ou seja: hoje a detecção fica **assimétrica** para BB — só pega quando o lado "recebido"
   tiver o documento no texto. Não há correção óbvia sem mais exemplos (precisaria ver se
   isso é consistente em todos os Pix enviados do BB ou só nesse caso).

### 22.3 PicPay (CSV) — possível extrato vazio, não investigado

`PICPAY-PF-extrato-2026-05-28-2026-06-26.csv` tem só a linha de cabeçalho
(`data,hora,tipo,"origem / destino",valor,"forma de pagamento"`) e nenhuma linha de dados
visível no período 28/05–26/06/2026. Não sei se é porque realmente não houve nenhuma
movimentação no PicPay nesse período ou se é um problema na exportação do arquivo pelo
Diego. **Perguntar ao Diego** antes de assumir que o parser de CSV está com problema — pode
ser simplesmente um extrato real vazio.

### 22.4 C6 Bank — PNG confirma layout, mas é só imagem

O `Extrato-C6-PF.png` é um print da tela do extrato (não o PDF) e mostra colunas: Data
lançamento, Data contábil, Tipo, Descrição, Valor (com cores verde/vermelho, sem sinal
explícito C/D em texto). Como é imagem, não tem como o `parse_pdf_bytes()` ler — serve só
de referência visual/redundância caso o PDF original (`extrato-C6-PF-original-com-senha-016152.pdf`,
senha `016152`) falhe ao abrir. Quando alguém puder validar o PDF de fato (via script/VM, não
pelo Read tool), checar se o layout de texto extraído bate com o que esse PNG mostra
(Data | Tipo | Descrição | Valor) e se precisa de um parser dedicado em `PDF_LINE_PARSERS["C6"]`
em vez do genérico.

### 22.5 Caixa (PDF) — achado importante: o parser genérico vai pegar a coluna errada

`Extrato-Caixa-PF.pdf` tem layout: `Data Mov. | Nr. Doc | Histórico/Complemento | Favorecido |
CPF/CNPJ | Valor | Saldo` — ou seja, **cada linha de transação termina com DOIS números
seguidos de C/D**: primeiro o Valor da transação, depois o Saldo resultante. Exemplo real:

```
27/06/2026 - 10:55:04   271055   PIX ENVIADO   Diego Cesar Goncal   ***.152.691***   57,57 D   0,00 C
```

O `_parse_pdf_lines_generic()` atual usa `_RE_PDF_VALUE` ancorado no **final da linha**
(`\s*$`) — como o último número da linha é o **Saldo** (`0,00 C`), não o Valor (`57,57 D`),
**o parser genérico vai importar o saldo da conta como se fosse o valor da transação**. Isso
é um bug real, não só um risco teórico — esse layout de "Valor + Saldo" na mesma linha é
exatamente o formato do extrato da Caixa. **Precisa de parser dedicado**
(`PDF_LINE_PARSERS["Caixa"]` ou pelo nome que for usado no campo `institution` da conta) que
capture o **primeiro** número C/D da linha (Valor), não o último, ou que use as posições das
colunas para diferenciar.

Outros pontos do extrato da Caixa:
- Também tem linhas de saldo puro, tipo "SALDO DIA" (com `Nr. Doc = 000000`, sem Favorecido/
  CPF), que precisam ser filtradas igual ao "Saldo Anterior"/"Saldo do dia" do BB (§22.2.1) —
  mesmo padrão, instituição diferente. Vale generalizar o filtro de nome (ex.: lista de termos
  bloqueados: "saldo anterior", "saldo dia", "saldo do dia") em vez de duplicar por banco.
- O CPF/CNPJ do favorecido vem **mascarado** (`***.152.691***`), formato diferente do que os
  regexes `_RE_CPF`/`_RE_CNPJ` esperam — a detecção automática de transferência (§20) não vai
  casar isso, mas como nesse caso o próprio "Favorecido" já é literalmente "Diego Cesar
  Goncal[ves]" (nome, não documento), talvez baste comparar pelo nome do titular da conta de
  destino como heurística alternativa pra esse banco especificamente — não implementado, é só
  uma ideia a avaliar.

### 22.6 Pendências concretas para a próxima sessão

1. **Decidir e implementar a correção do dedupe (BB, §22.2.2)** — risco de perda de dados
   real (importa só metade de pares débito/estorno). Prioridade alta.
2. **Filtrar linhas de saldo (BB + Caixa, §22.2.1 e §22.5)** — risco de lançamentos falsos
   sendo importados como receita/despesa real. Prioridade alta.
3. **Escrever parser dedicado para Caixa em `PDF_LINE_PARSERS`** (§22.5) — o genérico
   importaria o valor errado (saldo em vez de valor da transação) sempre que essa conta for
   usada. Prioridade alta, é o único dos 4 "dinossauros" cujo PDF já foi confirmado com esse
   problema.
4. **Investigar o CSV vazio do PicPay com o Diego** (§22.3) antes de assumir bug.
5. **Terminar de analisar `Extrato-MercadoPago-PF.pdf` e `Extrato-99pay-PF.pdf`** — foram
   lidos nesta sessão mas o conteúdo ainda não foi sintetizado/documentado.
6. **Validar de fato o PDF do C6 com senha** rodando `parse_pdf_bytes()` via script (o Read
   tool não decodifica PDF protegido por senha; isso não significa que o código de produção
   tenha problema, só que não foi possível inspecionar visualmente por aqui).
7. Nenhuma dessas correções foi codificada ainda — tudo isso é diagnóstico, não fix.
   Diego optou por não testar mais localmente (validação real será no primeiro upload na
   VM), então qualquer correção de código feita numa sessão futura deve ser revisada com
   cuidado redobrado por não haver mais o ciclo rápido de teste local→ajuste.

---

## 23. Todas as correções do §22 implementadas e validadas contra os extratos reais (2026-06-27)

**Contexto:** Diego pediu para corrigir tudo de uma vez nesta sessão (dedupe BB, filtro de
linhas de saldo, parser dedicado da Caixa, mais os parsers dedicados de C6/MercadoPago/99Pay
que ainda faltavam). Diferente da sessão anterior, **desta vez o código foi de fato executado**
contra os arquivos reais de `extratos/` (com Python via shell), não só lido — então os números
abaixo são resultado de teste real, não inspeção visual.

### 23.1 Correções em `backend/finance_import.py`

1. **Filtro de linha de saldo, por nome, genérico para qualquer banco** — nova constante
   `BALANCE_LINE_TERMS = ("saldo anterior", "saldo do dia", "saldo dia", "saldo bloqueado")`
   e helper `_is_balance_line(description)` (compara sem acento/maiúscula). Aplicado em
   `parse_ofx_bytes()` (testa `payee` e a descrição final) e em todo parser de PDF
   (genérico + os 4 dedicados). Resolve §22.2.1 (BB) e §22.5 (Caixa) com uma única
   implementação, sem duplicar por banco.
2. **Dedupe inclui o valor na chave mesmo quando há FITID** — `_dedupe_key()` agora monta
   `f"{account_id}:{tx_id}:{amount}"` em vez de só `f"{account_id}:{tx_id}"`. Resolve
   §22.2.2 (par débito/estorno do BB com FITID repetido).
3. **NAME + MEMO concatenados, não escolhidos com "ou"** — `parse_ofx_bytes()` antes pegava
   só o `payee` (NAME) quando existia, descartando o `memo` (MEMO); como no BB é o MEMO que
   carrega o CPF/CNPJ da contraparte, isso quebrava a detecção de transferência (§20) sempre
   que havia NAME preenchido. Agora concatena os dois (`"NAME - MEMO"`, sem duplicar se forem
   iguais), preservando o documento para `_extract_match_keys()`.
4. **Regex de valor com sinal antes do "R$"** (`_RE_SIGNED_RS`) — C6, MercadoPago e 99Pay
   mostram o sinal colado no "R$" (`-R$ 8,00`), não no número (`8,00 D`) como o regex
   genérico antigo esperava; sem isso todo valor virava positivo. Usado em todos os parsers
   de PDF novos, com fallback para o formato antigo (`_RE_PDF_VALUE`, número seguido de C/D)
   quando a linha não tem "R$".
5. **Quatro parsers dedicados em `PDF_LINE_PARSERS`** (chave = substring do `institution` da
   conta, case/acento-insensível via `_normalize_institution`):
   - `_parse_pdf_c6`: linhas `"DD/MM DD/MM Tipo+Descrição -R$/+R$ valor"` — duas datas sem
     ano (lançamento e contábil, usa a primeira); ano extraído uma vez do cabeçalho do
     período (`"( 01/06/2026 - 27/06/2026 )"`) e aplicado a todas as linhas.
   - `_parse_pdf_mercadopago`: linhas com data `DD-MM-YYYY`, ID de operação numérico, e
     **dois** valores em R$ no final (valor da transação + saldo) — pega o primeiro, não o
     último.
   - `_parse_pdf_99pay`: linhas `"... DD/MM/YYYY HH:MM:SS ±R$ valor"`; um prefixo
     numérico/hex (sobra do ID da transação, que "vaza" da coluna) é removido da descrição.
   - `_parse_pdf_caixa` (+ `_ocr_reconstruct_rows`, `_parse_pdf_caixa_rows`): a Caixa exporta
     PDF **escaneado** (0 caracteres de texto real) — exige OCR via `pytesseract`
     (`image_to_data`, não `image_to_string`, porque o texto OCR sai linearizado por coluna;
     as palavras são reagrupadas em linhas por proximidade vertical (`top`, tolerância 8px a
     300dpi) e ordenadas por posição horizontal (`left`) dentro do grupo). O regex de linha
     pega o **primeiro** valor com C/D (Valor), não o segundo (Saldo) — resolve §22.5.
   - `parse_pdf_bytes()` decide o caminho OCR automaticamente: se `institution` contém
     "caixa" OU se `extract_text()` vier vazio (rede de segurança pra qualquer outro banco
     que mande PDF escaneado sem avisar).

### 23.2 Validação real (rodado via Python no shell, não só lido)

A sessão anterior não conseguiu validar porque só tinha a ferramenta de leitura de arquivo
(que não decodifica PDF com senha nem executa código). Nesta sessão o código foi de fato
importado e rodado contra cada arquivo real de `extratos/`:

- **C6** (`extrato-C6-PF-original-com-senha-016152.pdf`, senha `016152`): abriu sem erro,
  **6 transações** extraídas corretamente (3 entradas Pix + 3 mensalidades C6Tag + 1 saída
  Pix), todas com data 27/06/2026 (confirmado contra o texto bruto do PDF — é mesmo o único
  dia com lançamento nesse extrato). "Saldo do dia" do cabeçalho foi corretamente ignorado
  (não é uma linha de transação no formato esperado pelo regex, então nem chega a precisar do
  filtro de nome aqui).
- **MercadoPago** (`Extrato-MercadoPago-PF.pdf`): **19 transações**, todas "Rendimentos"
  diários de R$0,04–0,06 (rendimento de CDB/conta remunerada) — valores e datas corretos,
  pegou o primeiro R$ (valor) e não o segundo (saldo) como esperado.
- **99Pay** (`Extrato-99pay-PF.pdf`): **387 transações** — Pix enviado/recebido, "Lucro"
  (rendimento diário), recarga de celular, todos com sinal correto (negativo pra saída,
  positivo pra entrada) e data/hora coerentes.
- **Caixa** (`Extrato-Caixa-PF.pdf`, via OCR): **4 transações reais** extraídas corretamente
  de 30 linhas OCR brutas — as 2 linhas "SALDO DIA" (intercaladas no meio do extrato, uma com
  valor zerado e outra não) foram corretamente excluídas pelo filtro de saldo; o valor
  capturado em cada linha foi sempre o primeiro número C/D (a transação), nunca o segundo (o
  saldo resultante) — confirma a correção do bug real de §22.5. OCR levou ~12s para 1 página
  em ambiente de teste (tesseract 4.1.1, só pacote de idioma inglês disponível — sem `por`,
  ainda assim leu números/datas/nomes corretamente).
- **BB OFX (PF e PJ)**: como a lib `ofxparse` não pôde ser instalada no sandbox (sem acesso
  de rede), a validação foi feita com um parser manual de `<STMTTRN>` (regex sobre o XML/SGML
  bruto) alimentando a mesma função `parse_ofx_bytes()` via um stub que imita a interface do
  `ofxparse` real (mesmos atributos: `.id`, `.date`, `.amount`, `.payee`, `.memo`) — testa a
  lógica de filtro/dedupe/concatenação do código real, não uma reimplementação paralela.
  Resultado:
  - PF: 3 lançamentos brutos → 2 retornados (a 1 "Saldo Anterior" zerada foi filtrada).
  - PJ: 11 lançamentos brutos → 7 retornados (4 linhas de saldo filtradas — confirmado no XML
    bruto que 3 das "Saldo do dia" tinham `TRNAMT=45.35`, valor **não-zero**, exatamente o
    risco apontado em §22.2.1: o filtro antigo por valor-zero não pegaria essas).
  - Os dois pares débito/estorno com FITID repetido (`1.024`: -87,05/+87,05; `40.931`:
    -151,19/+151,19) **ambos preservados**, zero colisões de chave de dedupe — confirma a
    correção de §22.2.2.
  - O MEMO com CNPJ cru (`25995295000104`) apareceu concatenado na descrição final,
    confirmando que a correção do NAME+MEMO (item 23.1.3) preserva o documento necessário
    para `_extract_match_keys()`.
  - **Achado §22.2.3 (Pix enviado do BB sem CPF/CNPJ no MEMO) confirmado, não corrigido** —
    segue sem solução nesta sessão por falta de mais exemplos; não é um bug de código, é uma
    limitação de informação que o próprio extrato do BB não fornece nesse caso.

### 23.3 PicPay (§22.3) e MercadoPago/99Pay (§22.6.5) — resolvidos

- PicPay: CSV realmente só tem cabeçalho, zero linhas de dados — comportamento esperado do
  parser genérico de CSV (retorna lista vazia, não erro). Não investigado mais a fundo com o
  Diego nesta sessão porque o foco foi a correção dos parsers de PDF/OFX; segue como possível
  pendência de confirmação ("o PicPay realmente não teve movimento no período, ou a
  exportação falhou?"), mas não há indício de bug no parser.
- MercadoPago e 99Pay: analisados e com parser dedicado funcionando (23.1.5/23.2).

### 23.4 Nota de ambiente — mount do bash ficou instável nesta sessão para arquivos grandes

Durante a validação, o mount usado pelas ferramentas de shell (`mcp__workspace__bash`) chegou
a mostrar **duas vezes** uma versão truncada de um arquivo grande recém-escrito
(`finance_manager.py`, parado em `SyntaxError` no meio de uma string; depois `finance_import.py`
parado em ~403 linhas de ~712 reais) — em ambos os casos o `Read`/`Write` (ferramenta de
arquivo, lado Windows) mostrava o conteúdo completo e correto, só o shell via uma cópia antiga/
incompleta, mesmo depois de esperar e tentar de novo. Contornado fazendo uma cópia do conteúdo
(via heredoc direto no próprio shell, sem depender do mount entre hosts) num diretório puramente
local ao sandbox (`/tmp`) para rodar os testes de verdade. **Para qualquer sessão futura:** se
`wc -l`/`cat`/`python3 -c "import ast..."` no shell apontar erro de sintaxe ou contagem de linha
estranha logo depois de uma edição grande, não assumir que o código está errado — comparar
primeiro com o que o `Read` tool mostra (fonte da verdade) antes de "corrigir" algo que já está
certo.

### 23.5 Pendências reais que continuam abertas

1. Confirmar com Diego se o PicPay realmente não teve movimento 28/05–26/06/2026 (§23.3).
2. BB "Pix enviado" sem documento no MEMO (§22.2.3) — sem solução, precisa de mais exemplos
   reais ou de uma heurística alternativa (ex.: casar pelo nome do titular, não só documento).
3. `ofxparse` nunca foi instalado/testado de fato neste sandbox (sem rede) — a validação do
   OFX foi por equivalência funcional (stub fiel à interface real), não pelo pacote oficial.
   Validação 100% real do caminho OFX só acontece no primeiro upload na VM (que tem rede).
4. Pacote de idioma `tesseract-ocr-por` não está instalado neste sandbox (só inglês) — o OCR
   da Caixa funcionou mesmo assim porque os campos relevantes são números/datas/nomes próprios,
   mas a precisão pode melhorar na VM se esse pacote for instalado lá
   (`apt install tesseract-ocr-por`).

---

## 24. PicPay — extrato CSV real recebido e bug de parsing corrigido (2026-06-27)

**Contexto:** o item 1 da pendência §23.5 ("PicPay não teve movimento no período?") era a
pergunta errada. Diego explicou: ele queria capturar hoje um Pix de ida-e-volta entre contas
próprias (conta A → PicPay → conta B) para servir de exemplo mais completo de transferência
interna, mas a exportação do PicPay só gera extrato até "ontem", nunca o dia atual — então não
deu pra capturar o exemplo same-day. Ele subiu em vez disso um extrato de período mais longo
(`PICPAY-PF-extrato-2026-04-28-2026-06-26.csv`) só para eu estudar como o PicPay formata os
dados — não necessariamente contendo o cenário de transferência simétrica.

### 24.1 O arquivo real não tinha linhas vazias — tinha um bug de parsing

Abrindo o CSV de verdade (9 transações, header
`data,hora,tipo,"origem / destino",valor,"forma de pagamento"`), rodar o parser genérico
antigo retornava **zero transações**, não por estar vazio, mas por dois bugs:

1. **Sinal Unicode MINUS SIGN (U+2212, "−") em vez de hífen ASCII (U+002D, "-")** antes do
   "R$" nos valores negativos — ex.: `"−R$ 468,34"`. Python's `float()` não reconhece esse
   caractere e levanta `ValueError`, que o código antigo engolia num `except: continue` —
   por isso a falha era silenciosa.
2. **Espaço interno entre o sinal/cifrão e o número** (`"−R$ 468,34"` tem espaço depois do
   R$) — mesmo corrigindo o sinal, esse espaço sozinho já quebra o `float()`.

Confirmado isolando o erro: `float('− 468.34')` → `ValueError: could not convert string to
float: '− 468.34'`. Esse não é só um caso do PicPay — qualquer exportador BR que use esse
caractere de menos "tipográfico" (comum em ferramentas que fazem auto-formatação de texto)
cairia na mesma armadilha.

Além disso, o header `"origem / destino"` do PicPay não estava na lista de aliases de
`description`, então mesmo corrigindo o valor a descrição sairia vazia.

### 24.2 Correção aplicada em `finance_import.py`

- Nova função `_parse_csv_amount()`: normaliza `−`→`-`, remove `"R$"`, remove **todo**
  espaço interno (`re.sub(r"\s+", "", raw_amount)` — não só as bordas), só depois resolve o
  separador decimal BR (`1.234,56` → `1234.56`) e chama `float()`.
- `_CSV_FIELD_ALIASES["description"]` ganhou `"origem / destino"` / `"origem/destino"`.
- Novo campo `_CSV_FIELD_ALIASES["type"]` (aliases `"tipo"`/`"type"`) — concatenado com a
  descrição (`"Pagamento realizado - Fatura PicPay Card"`, `"Pix recebido - DIEGO CESAR
  GONCALVES OLIVATTO 01615269185"`), no mesmo padrão de NAME+MEMO já usado para o OFX do BB,
  porque "origem/destino" sozinho às vezes é um rótulo genérico (`"Fatura PicPay Card"`) que
  não diz que é pagamento de fatura.
- *(Bug secundário corrigido durante a verificação: a primeira versão da concatenação tinha
  uma condição invertida que descartava o `tipo` em vez do `contraparte` duplicado — trocada
  por `" - ".join(dict.fromkeys(p for p in (tipo, contraparte) if p))`, que junta os dois e
  só remove duplicata exata.)*

**Validado de fato** rodando `parse_csv_bytes()` contra o arquivo real: as 9 linhas saem
corretas — 4 negativas (`Pagamento realizado`/`Compra realizada`) e 5 positivas (`Pix
recebido`), valores e sinais certos, descrição combinada, e o CPF `01615269185` preservado em
texto livre na descrição de uma das linhas (relevante pro pareamento de transferência interna,
ver §24.3).

### 24.3 Observação importante: este arquivo NÃO contém o exemplo de transferência simétrica

As 9 linhas são: pagamentos de fatura do cartão PicPay, uma compra (GOWD) e Pix recebidos —
**nenhuma linha é "Pix enviado"**. Ou seja, mesmo sendo um período mais longo, esse extrato não
demonstra o caso de ida-e-volta entre contas próprias que Diego queria estudar (isso só
aparecerá num extrato futuro que inclua um "Pix enviado" de saída). Vale capturar um novo
extrato no dia seguinte a uma transferência (já que a exportação do PicPay só fecha até
"ontem") se ele quiser validar esse cenário especificamente.

### 24.4 Pendências atualizadas

- ~~Item 1 de §23.5~~ — resolvido/superado: não era ausência de movimento, era bug de parsing
  (corrigido) + escolha de período sem "Pix enviado" (não é bug, é só o conteúdo do arquivo).
- Item 2 de §23.5 (BB "Pix enviado" sem CPF/CNPJ no MEMO) continua aberto — ver resposta dada
  ao Diego no chat em 2026-06-27 com as opções de solução apresentadas (heurística por nome,
  pedir mais exemplos reais, ou aceitar a assimetria com revisão manual como rede de segurança).
  **Resolvido nesta mesma sessão, ver §25** — Diego pediu pra combinar as hipóteses em vez de
  escolher uma só.

---

## 25. Detecção de transferência entre contas próprias — 3 camadas combinadas (2026-06-27)

**Contexto:** resposta ao "Qual é a situação do BB, me apresente soluções" (§24.4). Em vez de
escolher uma única heurística, Diego pediu pra combinar as hipóteses (documento + nome +
valor/data), com revisão manual como rede de segurança pra qualquer match de baixa confiança.

### 25.1 As 3 camadas, em ordem de confiança

1. **Documento** (já existia, ver §20) — CNPJ/CPF na descrição bate com `holder_document` de
   outra conta cadastrada. Confirma automático (`is_internal_transfer=True`, status `PAGO`).
2. **Nome** (novo) — quando não há documento na descrição (caso BB "Pix enviado"), tenta casar
   o `holder_name` da conta (novo campo em `FinancialAccount`, ex.: "Diego Cesar Gonçalves
   Olivatto") contra a descrição normalizada (sem acento, maiúsculo, espaços colapsados) por
   substring. Limiar de 2+ palavras no nome pra evitar falso-positivo com nome curto/genérico.
   Também confirma automático, mas o `notes` do lançamento deixa registrado que foi por nome
   ("sem documento no extrato"), pra eventual auditoria.
3. **Valor+data** (novo) — roda depois do loop principal de import (`_suggest_value_date_transfers`,
   chamada ao final de `import_transactions`). Pra cada lançamento ainda não confirmado, procura
   em OUTRAS contas próprias um lançamento de sinal oposto, mesmo valor absoluto, dentro de ±1
   dia. Se achar, marca os DOIS lados como **sugestão** (`transfer_suggested=True`,
   `transfer_match_confidence="valor_data"`, `transfer_with_entry_id` apontando um pro outro) —
   **não confirma sozinho**, fica pendente de revisão manual.

### 25.2 Schema novo

- `FinancialAccount.holder_name: Optional[str]` — nome do titular como aparece no extrato.
- `FinancialEntry.transfer_match_confidence: Optional[str]` — `"documento"|"nome"|"valor_data"`.
- `FinancialEntry.transfer_with_account_id: Optional[str]` — ACC-XXXX da outra ponta.
- `FinancialEntry.transfer_with_entry_id: Optional[str]` — LCT-XXXX do lançamento espelho (só
  preenchido no caso `valor_data`, pra confirmar/rejeitar o par exato).
- `FinancialEntry.transfer_suggested: bool` — True = sugestão de baixa confiança aguardando
  confirmação manual; `is_internal_transfer` só vira True de fato depois de confirmado.

### 25.3 Endpoints novos (`finance_routes.py`)

- `POST /api/finance/entries/{id}/confirm-transfer` — promove a sugestão a transferência
  confirmada (`is_internal_transfer=True`, `PAGO`) nos dois lados do par (via `transfer_with_entry_id`).
- `POST /api/finance/entries/{id}/reject-transfer` — reverte a sugestão (falso positivo — ex.:
  duas compras coincidentemente do mesmo valor em contas diferentes), volta pra
  `A_CATEGORIZAR` nos dois lados.

### 25.4 Validado de fato no sandbox

Sem acesso a MongoDB real aqui, foi construído um stub fiel da interface do Motor
(`find`/`find_one`/`insert_one`/`update_one`/`update_many`/`to_list`, suportando `$ne`/`$gte`/
`$lte`/`$in`) em `/tmp/fintest2/server.py`, e um stub de enums em `finance_manager.py` — o
`finance_import.py` testado é uma cópia EXATA do arquivo real (conferida linha a linha via
`Read` antes de copiar, por causa da instabilidade de mount documentada em §23.4). Cenário
testado:

- Conta PJ (CNPJ) + conta PF (CPF, holder_name "Diego Cesar Gonçalves Olivatto") + conta
  "Cofrinho" sem documento/nome cadastrados.
- Pix recebido na PF com CNPJ da PJ na descrição → confirmado por **documento**. ✅
- Pix enviado na PJ pra PF SEM CPF/CNPJ na descrição (só "Pix Enviado Diego Cesar Goncalves
  Olivatto", exatamente o caso real do BB) → confirmado por **nome**. ✅
- Saída na PF + entrada de mesmo valor 1 dia depois no Cofrinho (conta sem documento/nome) →
  nenhuma das 2 primeiras camadas achou nada, mas a 3ª (**valor_data**) marcou os dois lados
  como sugestão, apontando um pro outro via `transfer_with_entry_id`, SEM confirmar sozinho. ✅
- Simulação do endpoint `confirm-transfer`: confirmar um lado promoveu os dois lados pra
  `is_internal_transfer=True`/`PAGO` corretamente. ✅

### 25.5 Pendências / próximos passos

1. **Cadastrar `holder_name` nas contas reais do Diego** (BB PF, BB PJ, e demais) — sem isso a
   camada 2 (nome) não tem o que comparar. Tela de Configurações → Contas precisa ganhar esse
   campo (hoje só existe `holder_document` no formulário).
2. **UI de revisão de sugestões** — hoje a sugestão fica só no banco (`transfer_suggested=True`)
   e nos `notes`; falta uma tela/seção em Financeiro listando os pares sugeridos com botões
   Confirmar/Rejeitar (consumindo os 2 endpoints novos de §25.3). Sem isso o usuário não vê a
   sugestão.
3. A janela de ±1 dia em `_suggest_value_date_transfers` é um valor fixo (`_VALUE_DATE_WINDOW_DAYS`)
   — se aparecerem casos reais de transferência que demore mais de 1 dia pra processar entre
   bancos diferentes, esse número pode precisar aumentar (ao custo de mais falsos positivos).
4. Ainda não testado contra o MongoDB real (só contra o stub) — primeira validação de verdade
   será no primeiro upload de extrato na VM, junto com o resto do módulo (ver §23.5 item 3).
