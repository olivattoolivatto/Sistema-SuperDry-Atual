# SuperDry Lavanderia — Guia do Projeto

Sistema ERP para lavanderias de serviços (estofados, tapetes, cortinas, veículos, etc).
Localização operacional: Cuiabá, MT.

## Ciclo central do negócio

```
Cliente → Orçamento (com Itens) → Rota → Agenda Google Calendar → Técnico executa → Pagamento
```

O **BudgetItem (ITM-XXXX)** é o pilar do sistema. Tudo orbita em torno do seu ciclo de vida.

> **Infraestrutura decidida:** ver [`memory/INFRAESTRUTURA.md`](memory/INFRAESTRUTURA.md). Resumo: SuperDry + Home Assistant → **Oracle Cloud Free** (ARM 24GB, IP fixo, sempre ligado, R$0); Nextcloud → **Proxmox local** (Core 2 Duo, HDs físicos para grande armazenagem sem custo). **Migração Oracle concluída em 12/06/2026 — sistema em produção na VM.** Pendência real atual: equalizar o código (local está ~1.700 linhas adiante do que foi deployado pela última vez na VM) — ver checklist em `memory/INFRAESTRUTURA.md`.

> **Forma de trabalho do dono + visão de automação ("assistente pessoal"):** ver
> [`memory/FLUXO_TRABALHO_E_AUTOMACAO.md`](memory/FLUXO_TRABALHO_E_AUTOMACAO.md). Resumo do fluxo real:
> atendimento WhatsApp (nome+telefone+fotos) → orçamento → confirmação → endereço → roteirização
> (tapetes=CARRO, limpezas/imperm.=MOTO, agrupados por região) → agenda → técnico → cobrança (raramente no local).
> O sistema deve automatizar ao máximo e apontar prioridades (cobranças, compras, estoque).

> **Parceiros de tapetes/cortinas (Leonardo Dry Clean, Vinicius/Higia, Maika/FormaClean,
> Wesley Higienização, João/Felipe):** ver [`memory/PARCEIROS_TAPETES.md`](memory/PARCEIROS_TAPETES.md).
> Resumo: cada parceiro já tem 2 itens próprios no catálogo (tapete quadrado/redondo,
> R$20/m², `service_type: "Tapete Parceiro"`); identificação física é por etiqueta
> cor+número em texto livre (sem campo estruturado ainda); falta construir a automação
> que gera os orçamentos/itens de parceiro a partir do log de medições e o fechamento
> mensal de cobrança dentro do sistema.

> **Integração Agenda (cores) ↔ Sistema — diagnóstico e design:** ver
> [`memory/INTEGRACAO_AGENDA_CORES.md`](memory/INTEGRACAO_AGENDA_CORES.md). Resumo: o
> uso real do dono é Agenda-primeiro (cola texto solto do WhatsApp direto num evento do
> Google Calendar), enquanto o sistema pressupõe cadastro estruturado antes. `colorId`
> hoje é sempre fixo em amarelo na criação (`server.py:1770`/`2162`), sem nenhuma
> leitura/gravação da cor real (azul/roxo/amarelo/vermelho) de volta pro Mongo — não
> existe webhook nem polling do Google Calendar. `POST /calendar/events/direct` já
> permite evento sem orçamento/rota, e o parser de medidas de parceiro
> (`_parse_measures_text`) já processa a lista de recolhimento do grupo do WhatsApp sem
> precisar de código novo. Design faseado: cor automática na criação → evento direto
> como caminho de primeira classe com sugestão silenciosa de estruturação → sincronia
> mão-dupla cor↔status via polling (sinalizando divergência, não gravando pagamento
> sozinha) → painel "resolver hoje".

---

## Stack técnica

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11, FastAPI 0.110.1, Uvicorn |
| Banco de dados | MongoDB via Motor 3.3.1 (async) |
| Autenticação | JWT (python-jose), roles por papel |
| PDFs | ReportLab + WeasyPrint |
| Frontend | React 19, React Router DOM 7.5.1 |
| Estilos | Tailwind CSS 3.4.17 |
| UI Components | Radix UI (25+ libs), Shadcn/ui pattern |
| Mapa | Leaflet 1.9.4 + React Leaflet 5.0.0 |
| Formulários | React Hook Form 7.56.2 + Zod 3.24.4 |
| HTTP client | Axios 1.8.4 com interceptadores JWT |
| Build | Craco (Create React App override) |
| Notificações | Sonner 2.0.3 |

### APIs externas

| API | Uso |
|-----|-----|
| Google Maps Places API | Autocomplete e geocodificação de endereços |
| Google Calendar OAuth2 | Criação e sincronização de eventos |
| OSRM | Otimização de rotas (modo legado) |
| Geoapify Route Planner v1 | Otimização de rotas (modo atual, desde fev/2026) |

---

## Estrutura de arquivos

```
SuperDry-Atual-MIGRACAO/
├── CLAUDE.md                        # Este arquivo
├── README.md
├── .gitignore
├── importar.py                      # Script de migração/seed
├── meus_servicos.json               # Seed de 85 serviços completos
│
├── backend/
│   ├── server.py                    # Core FastAPI — 5700+ linhas, 100+ endpoints
│   ├── auth.py                      # JWT, roles, hashing, auditoria
│   ├── requirements.txt             # Dependências Python
│   ├── uploads/
│   │   └── logo.png
│   └── tests/
│       └── test_geoapify_routes.py
│
├── frontend/
│   ├── package.json
│   ├── craco.config.js
│   ├── tailwind.config.js
│   ├── jsconfig.json                # Alias @/ → src/
│   ├── components.json              # Shadcn/ui config
│   └── src/
│       ├── App.js                   # Root component + ProtectedRoute + rotas React
│       ├── index.js
│       ├── contexts/
│       │   └── AuthContext.js       # Login, logout, JWT storage, user state
│       ├── services/
│       │   └── api.js               # Todos os endpoints do frontend (Axios)
│       ├── hooks/
│       │   └── use-toast.js
│       ├── lib/
│       │   └── utils.js             # cn() e utilitários Tailwind
│       ├── components/
│       │   ├── Layout.js            # Menu lateral + navegação por role
│       │   ├── MiniMap.js           # Mapa Leaflet reutilizável
│       │   └── ui/                  # 45+ componentes Radix UI/Shadcn
│       └── pages/
│           ├── Login.js
│           ├── Dashboard.js
│           ├── Clients.js
│           ├── Catalog.js
│           ├── Budgets.js
│           ├── BudgetConfig.js      # Textos e condições dos orçamentos
│           ├── Routes.js            # Rotas OSRM (legado)
│           ├── RoutesGeoapify.js    # Rotas Geoapify (atual)
│           ├── Agenda.js            # Google Calendar
│           ├── Financial.js
│           ├── SystemConfig.js
│           ├── TechnicianMode.js
│           ├── Automations.js
│           └── budgets/
│               ├── _constants.js
│               ├── BudgetEditor.js
│               └── ItemDetailDrawer.js
│
├── uploads/
│   └── photos/                      # Fotos antes/depois dos itens
│
├── memory/
│   └── PRD.md                       # Product Requirements Document
│
└── tests/
    └── __init__.py
```

---

## Funcionalidades implementadas

### Autenticação e controle de acesso
- Login com JWT (expiração 30 dias)
- Papéis: `ADMIN`, `TECNICO`, `ATENDENTE`, `FINANCEIRO`, `MANUTENCAO`
- Permissões de módulos por usuário
- Auditoria completa de ações (AUD-XXXX)
- Troca de senha

### Clientes
- CRUD completo (ID padrão: CLI-XXXX)
- Autocomplete de endereço via Google Places API
- Armazenamento de coordenadas geográficas
- Histórico de alterações por cliente

### Catálogo de serviços
- 85 serviços pré-carregados (`meus_servicos.json`)
- Categorias: ESTOFADOS, COLCHOES, BOX, TAPETES, CORTINAS, PERSIANAS, ITENS_INFANTIS, VEICULOS, IMPERMEABILIZACAO, OUTROS
- Tipos de medição: UNITARIO, AREA_DE_TAPETE, METRAGEM_LINEAR, DIAMETRO, AREA_PERSIANA
- Locais de execução: RETIRADA, NO_LOCAL, CLIENTE_TROUXE
- Preço de custo e preço de venda separados
- Ativação/desativação de serviços

### Orçamentos
- Criação com itens individuais (ORC-XXXXXXX / ITM-XXXXXXX)
- Modos de execução por item: `RETIRAR_E_LEVAR`, `EXECUTAR_NO_LOCAL`, `CLIENTE_TROUXE`, `CLIENTE_LEVARA`
- Endereços por etapa (retirada, execução, entrega — podem diferir do cliente)
- Datas agendadas para cada etapa
- Medidas específicas por tipo (width, height, diameter, fabric folds)
- Fotos antes/depois por item
- Sessões de execução (lavagem em múltiplas etapas)
- Exportação em PDF (ReportLab) — **redesenhado com identidade visual SuperDry** (azul #1F4E8C + verde #8CC63F): cabeçalho com logo, card de cliente, tabela com cabeçalho azul/linhas alternadas/total verde, seções em barra colorida. Riscos por categoria usam o `service_category` real do item (corrigido: impermeabilização não cai mais em estofados). Logo lida de `ROOT_DIR/uploads/logo.png` (caminhos portáveis, não mais `/app/...`)
- Texto formatado para WhatsApp (`GET /budgets/{id}/whatsapp`)
- Textos de risco por categoria (configurável)
- **Condição de pagamento padrão sugerida:** Cartão de Crédito, com parcelas pelo valor — até R$200→2x, 300→3x, 400→4x, 500→5x, 600+→6x (teto). É só sugestão (auto-selecionada no editor até o usuário trocar); o pagamento real é definido no Financeiro. Regra em `suggest_credit_installments()` (backend) + `calc_budget_totals` grava `suggested_payment_method`/`suggested_installments`; espelhada no `BudgetEditor.js`.

**Ciclo de status do item:**
```
RETIRAR → COLETADO → EM_LAVAGEM → AGUARDANDO_ENTREGA → ENTREGAR → ENTREGUE
EXECUTAR_NO_LOCAL → EXECUTADO
CLIENTE_TROUXE → EM_LAVAGEM → ...
CANCELADO (a qualquer momento)
BUSCOU (cliente buscou na loja)
```

### Rotas e otimização (implementação dupla)

**OSRM (legado) — `Routes.js`**
- Endpoint: `POST /api/routes/{id}/optimize`
- Geometria OpenStreetMap local
- Mapa Leaflet integrado

**Geoapify Route Planner (atual) — `RoutesGeoapify.js`**
- Endpoint: `POST /api/routes/{id}/optimize-geoapify`
- API: `POST https://api.geoapify.com/v1/routeplanner`
- Prioridades por parada: `PRIMEIRA` (closer first), `AUTOMATICA` (otimizada), `ULTIMA` (farther first)
- Retorna: ordem otimizada, tempo total, distância, geometria MultiLineString
- Stop IDs com UUID para evitar duplicatas

**Ambos suportam:**
- Tipo de veículo: CARRO ou MOTO
- Tipo de rota: DISTANCE (mais curto) ou TIME (mais rápido)
- Parada obrigatória na sede da empresa
- Salvar rota com alias
- Exportar sequência de paradas

### Agenda
- Autenticação OAuth2 com Google Calendar
- Criação de eventos a partir de rotas (stops selecionáveis)
- Edição e exclusão de eventos
- Atribuição de tarefas a técnicos
- Filtro por período

### Modo técnico (execução em campo)
- Vista de tarefas diárias do técnico
- Câmera integrada para fotos antes/depois
- Registro de execução com sessões
- Registro de pagamento direto
- Timeline de eventos por item
- Recibos de retirada e entrega

### Financeiro
- Resumo de pendências por cliente
- Registro de pagamentos por item
- Métodos: PIX (2 CNPJs), DINHEIRO, CREDITO (1–8x), DEBITO, BOLETO, LINK_PAGAMENTO, TRANSFERENCIA, PERMUTA
- Status de adimplência: PENDENTE, PARCIAL, PAGO, CORTESIA, INADIMPLENTE
- Comissões de vendedores e técnicos
- Auditoria de pagamentos
- **Cobrança consolidada (CPG-XXXX):** quita vários itens num pagamento único, com responsável financeiro; pronta para InfinitePay (link/PIX + webhook `/api/webhooks/payment`)
- **Taxas por forma de pagamento → líquido estimado:** `SystemConfig.payment_fees` (% por método) pré-configurado com as taxas de crédito InfinitePay 1x–12x (4,20 / 6,09 / 7,01 / 7,91 / 8,80 / 9,67 / 12,59 / 13,42 / 14,25 / 15,06 / 15,87 / 16,66). Helpers `get_payment_fees()` + `compute_net()`; a cobrança consolidada grava `fee_pct`/`fee_amount`/`net_value` e o modal mostra **bruto/taxa/líquido** ao vivo. Demais métodos = 0% (ajustável). Estimativa; valor real virá da conciliação Open Finance. Editável em **Configurações → Formas de Pagamento** (campo % por método, em `SystemConfig.js`). Métodos de crédito disponíveis: 1x a 12x.

### Gestor Financeiro (estilo Organizze) — EM ESTRUTURAÇÃO
Módulo de gestão de contas/cartões e despesas PF e PJ. Ver [`memory/GESTOR_FINANCEIRO.md`](memory/GESTOR_FINANCEIRO.md).
- **Lançamento como agregador:** uma compra (LCT-XXXX) se desdobra em **entradas por categoria** cuja soma fecha o valor (mesmo padrão Orçamento→Itens). Diferencial sobre o Organizze.
- Contas/cartões (ACC-XXXX), árvore de categorias (CAT-XXXX), lançamentos com splits (LCT-XXXX)
- Conciliação via Open Finance (Pluggy/Belvo) lendo **Nubank Empresarial** + InfinitePay
- Scaffold de modelos: [`backend/finance_manager.py`](backend/finance_manager.py)
- Estado: placeholder na tela "Gerenciador Financeiro"; `finance_summary` ainda inerte (`server.py:5462`)

### Dashboard
- KPIs gerais (itens por status, clientes, receita)
- Endpoint legado `GET /dashboard` e novo `GET /dashboard/summary`

### Configurações do sistema
- Dados da empresa (nome, CNPJ, endereço, coordenadas, contatos)
- Upload e customização do logo
- Métodos de pagamento configuráveis
- Textos de orçamentos (riscos por categoria, condições gerais, rodapé)
- Política de retenção de dados (2 anos com anonimização)
- Permissões de módulos por usuário

### Automações
- Preview de automações em lote
- Execução em lote (budgets, medidas)
- Regras customizáveis (parcialmente implementado)

---

## Modelos de dados (MongoDB)

| Entidade | ID | Coleção |
|----------|----|---------|
| User | USR-XXXX | `users` |
| Client | CLI-XXXX | `clients` |
| Service | SRV-XXXX | `services` |
| Budget | ORC-XXXXXXX | `budgets` |
| BudgetItem | ITM-XXXXXXX | `budget_items` |
| Route | RTE-XXXX | `routes` (RouteStop embedded) |
| CalendarEvent | — | `calendar_events` |
| AuditLog | AUD-XXXX | `audit_logs` |
| SystemConfig | singleton | `system_config` |
| BudgetConfig | singleton | `budget_config` |
| ConsolidatedPayment | CPG-XXXX | `consolidated_payments` |
| FinancialAccount | ACC-XXXX | `financial_accounts` *(planejado)* |
| FinancialCategory | CAT-XXXX | `financial_categories` *(planejado)* |
| FinancialEntry | LCT-XXXX | `financial_entries` *(planejado)* |

---

## Endpoints REST principais

### Autenticação
```
POST   /api/auth/login
GET    /api/auth/me
POST   /api/auth/change-password
```

### Clientes
```
POST   /api/clients
GET    /api/clients
GET    /api/clients/{id}
PUT    /api/clients/{id}
DELETE /api/clients/{id}
GET    /api/clients/{id}/history
```

### Serviços
```
POST   /api/services
GET    /api/services
PUT    /api/services/{id}
PUT    /api/services/{id}/deactivate
```

### Orçamentos
```
POST   /api/budgets
GET    /api/budgets
GET    /api/budgets/{id}
PUT    /api/budgets/{id}
DELETE /api/budgets/{id}
POST   /api/budgets/{id}/items
GET    /api/budgets/{id}/whatsapp
GET    /api/budgets/{id}/pdf
```

### Itens
```
GET    /api/budget-items/available-for-routes
PUT    /api/budget-items/{id}/status?status=XXX
POST   /api/items/{id}/payment
```

### Rotas
```
POST   /api/routes
GET    /api/routes
PUT    /api/routes/{id}/stops
POST   /api/routes/{id}/optimize           # OSRM
POST   /api/routes/{id}/optimize-geoapify  # Geoapify
DELETE /api/routes/{id}
```

### Agenda
```
GET    /api/calendar/auth-url
POST   /api/calendar/auth
POST   /api/calendar/events
GET    /api/calendar/events
PUT    /api/calendar/events/{id}
DELETE /api/calendar/events/{id}
```

### Técnico
```
GET    /api/technician/{id}/daily-tasks
POST   /api/technician/upload-photos
GET    /api/technician/photos/{item_id}
```

### Financeiro
```
GET    /api/payment-methods
GET    /api/commissions/summary
```

### Endereços
```
GET    /api/places/search?query=XXX
GET    /api/places/details?place_id=XXX
```

### Usuários (admin)
```
GET    /api/users
POST   /api/users
PUT    /api/users/{id}
DELETE /api/users/{id}
```

### Sistema
```
GET    /api/system-config
PUT    /api/system-config
POST   /api/system-config/logo
GET    /api/dashboard/summary
GET    /api/audit-logs
```

---

## Variáveis de ambiente (`.env` — não commitado)

```
MONGO_URL=
DB_NAME=
JWT_SECRET_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
REDIRECT_URI=
GEOAPIFY_API_KEY=
REACT_APP_BACKEND_URL=
```

**Atenção:** A chave do Google Maps está hardcoded em `backend/server.py:55` — mover para `.env`.

---

## Dados de seed / teste

- **Admin:** `admin@superdry.com` / `admin123`
- **Clientes:** CLI-0001, CLI-0002, CLI-0003 (endereços em Cuiabá)
- **Orçamentos:** ORC-0000001, ORC-0000002, ORC-0000003
- **Serviços:** 85 em `meus_servicos.json`
- **Coordenadas da sede:** lat=-15.6014, lon=-56.0974 (Cuiabá)

---

## Incompleto / pendente

| Item | Situação |
|------|----------|
| WhatsApp | Entrada no menu existe, sem implementação |
| Relatórios | Placeholder sem implementação |
| Finance Manager detalhado | Estruturado em `memory/GESTOR_FINANCEIRO.md` + scaffold `finance_manager.py`; falta CRUD/telas |
| Tickets / Chamados | Placeholder |
| Automações | Camada A implementada (catálogo + parser inteligente). Pendentes abaixo. |
| Modo Moto no Geoapify | API não suporta `motorcycle`; ambos usam `drive` |
| `RoutesGeoapify.js` | Código pronto, aguarda validação visual com dados reais |
| Modularização do `server.py` | 5.700+ linhas em um único arquivo |
| Testes de integração | Apenas `test_geoapify_routes.py` existe |
| **[BACKLOG]** Tela de login — logo da empresa | ✅ Implementado: logo carregada dinamicamente via `/api/system-config/logo/file`. |
| **[BACKLOG]** Orçamento — "usar nome genérico (parceiro)" | ✅ Corrigido: checkbox auto-seleciona `CLIENTE_TROUXE`. Serviços com "parceiro" no nome também auto-selecionam `CLIENTE_TROUXE` em `ItemSubForm` e `BatchModal`. |
| **[BACKLOG]** Orçamento — botões no topo | ✅ "Adicionar Item" e "Lançar em Lote" movidos para o TOPO da lista de itens. |
| **[BACKLOG]** Automação de medidas — tapete redondo vs quadrado | ✅ Documentado: cada linha da mensagem é classificada individualmente ("redondo"/Ø → `TAPETE_REDONDO_DIAMETRO`, NxM → `AREA_DE_TAPETE`). Lançar tudo de uma vez na automação de medidas para classificar corretamente na criação. Não há retrofix de quadrado→redondo em item já criado. |
| **[BACKLOG]** Acesso externo completo (celular sem Tailscale) | Build do frontend servido pelo backend para acesso via `https://superdry.tail287b6c.ts.net` sem precisar do app Tailscale no celular. Definitivo só no Proxmox. |
| **[BACKLOG]** Orçamento — cadastro rápido de cliente inline | ✅ Implementado: painel expansível no Step 1 do BudgetEditor com cola do WhatsApp (auto-preenche nome+telefone), campos de nome/telefone/endereço/complemento e botão "Cadastrar e usar no orçamento". Também disponível via SmartSearchBar (QuickRegisterModal) na tela de Orçamentos. Bug corrigido: `AddressAutocomplete` recebia objeto em vez de string (`qcAddr?.full_address \|\| ''`). |

---

## Pontos de atenção

- **`server.py` é monolítico** (5.700+ linhas) — dividir em routers FastAPI separados reduz risco de conflitos em edições simultâneas
- **API key do Google Maps hardcoded** em `server.py:55` — risco de exposição no git
- **Frontend em `.js`** sem TypeScript — sem type safety em props e retornos de API
- **Sem versionamento de API** (`/api/v1/...`) — mudanças podem quebrar compatibilidade
- **Sem rate limiting** visível nas rotas públicas
- **Índices MongoDB** não definidos explicitamente — queries podem degradar com volume

---

## Como rodar localmente

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8001

# Frontend
cd frontend
npm install
npm start
```

O frontend acessa o backend via `REACT_APP_BACKEND_URL` (padrão `http://localhost:8001`).
