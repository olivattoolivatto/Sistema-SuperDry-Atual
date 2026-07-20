# SuperDry — Padrões de Mensagem para IA

> Documento de referência para implementação da Camada B (IA) de automação.
> Criado em 19/07/2026 a partir de exemplos reais de WhatsApp e análise do código existente.
> Leia junto: `PARCEIROS_TAPETES.md`, `FLUXO_TRABALHO_E_AUTOMACAO.md`, `CLAUDE.md`.

---

## 1. O que já existe no sistema (não reimplementar)

### Backend (`server.py`)

| Função / Endpoint | O que faz | Estado |
|---|---|---|
| `_parse_measures_text(text)` | Parser completo de listas de medidas de tapetes: cabeçalho WhatsApp, emoji+código, cor+código, parceiros, cm/m heurística, redondo | ✅ Produção |
| `_classify_partner(identifier)` | Identifica se identificador é parceiro (por nome/emoji/cor+num) e qual parceiro | ✅ Produção |
| `_normalize_dims(w, h)` | Heurística cm→m: se `> 10`, divide por 100 | ✅ Produção |
| `_smart_parse_budget(text, services)` | Parser de orçamento por conteúdo (nome, telefone, items, endereço, obs:) com match no catálogo | ✅ Produção |
| `match_service_in_catalog(query, services)` | Fuzzy match query → serviço do catálogo (token score + vieses de domínio) | ✅ Produção |
| `_resolve_client_fuzzy(name)` | Busca cliente no banco por exato / prefixo / primeiro token | ✅ Produção |
| `_PARTNER_SERVICE_MAP` | CLI-ID → (SRV quadrado, SRV redondo) por parceiro | ✅ Produção |
| `suggest_credit_installments(total)` | Sugere parcelas de crédito pelo valor total | ✅ Produção |
| `POST /automation/preview-budget` | Retorna preview do orçamento parseado (itens enriquecidos com catálogo) | ✅ Produção |
| `POST /automation/execute-budget` | Cria cliente + orçamento + itens a partir do preview confirmado | ✅ Produção |
| `POST /automation/preview-measures` | Preview do lançamento de medidas de tapetes | ✅ Produção |
| `POST /automation/execute-measures` | Preenche medidas em itens existentes ou cria novos por parceiro | ✅ Produção |

### Frontend

| Componente | O que faz |
|---|---|
| `Automations.js` — aba Orçamento | Cola texto do WhatsApp → preview → confirma → cria orçamento |
| `Automations.js` — aba Medidas | Cola lista de medidas → preview → preenche itens existentes ou cria por parceiro |
| `BatchModal` em `BudgetEditor.js` | Lança N itens do mesmo serviço de uma vez num orçamento; auto-seleciona `CLIENTE_TROUXE` para serviços com "parceiro" no nome |
| `AddressAutocomplete` | Autocomplete Google Places em Clientes, BudgetEditor, Automations |

### Parceiros já mapeados no banco e no código

| Cliente (banco) | ID | Aliases reconhecidos pelo parser |
|---|---|---|
| Leonardo - Dry Clean USA | CLI-0006 | sem nome, s/n, dry, dry2, dry clean, dhiego, diego, parceiro diego, emoji+código, cor+código (Azul 581, etc.) |
| Forma Clean | CLI-0009 | forma clean, forma clan, maika, renan |
| Higia Service | CLI-0010 | higia, lucas (vinicius = ambíguo) |
| Wesley Higienização | CLI-0011 | parceiro wesley, ^wesley$ |
| Felipe Gonçalves / João Farias | CLI-0016 | parceiro joao, parceiro felipe, domus, domus decor |

**Lacunas existentes no parser atual (a adicionar):**
- `Parceiro Diego` / `Dhiego` / `Dry 2` → **não estão mapeados** para nenhum parceiro (Diego Olivatto é o dono, não um parceiro; mas "Parceiro Diego" nos exemplos é um parceiro diferente). Precisa de CLI-XXXX próprio e inclusão em `_PARTNER_SERVICE_MAP`.
- Variações de grafia de clientes comuns (`José lito` → `Joselito`, `Boa Ventura` → `Boaventura`) — `_classify_partner` faz só Title Case, não corrige essas fusões.

---

## 2. Tipos de mensagem identificados

### TIPO A — Lista de medidas de tapetes (WhatsApp de técnico)

**Descrição:** Mensagem enviada pelo técnico ao grupo, com uma medida por linha. Cada linha = um tapete. Pode conter cabeçalho de data do WhatsApp.

**Exemplo canônico:**
```
[06/07/2026] Marcos Técnico - Santa Isabel:
Higia 1.80 redondo 
💛059 1.60 redondo 
🩷567 1X1.50
Hellen 80X3.10
Nádia 2X3
Sem nome 2.50X3.40
Parceiro Diego 2X2.90
```

**Campos extraíveis por linha:**
- `identifier` — tudo antes da medida: nome do cliente, nome do parceiro, emoji+código, cor+código, "Sem nome"
- `width` / `height` — para tapetes retangulares (formato NxM)
- `diameter` — para tapetes redondos (keyword "redondo" ou símbolo Ø)
- `area_m2` — calculado: `w × h` ou `π × (d/2)²`
- `reference_date` — data extraída do cabeçalho WhatsApp `[DD/MM/AAAA, HH:MM:SS]`
- `is_partner` — booleano
- `partner_label` — `{type: "COLOR_NUM", color: "AMARELO", number: "059"}` ou `{type: "TEXT", text: "Higia Service"}`

**O que dispara no sistema:** `POST /automation/preview-measures` → `execute-measures`

---

### TIPO B — Orçamento formal (texto do atendimento)

**Descrição:** Texto colado do atendimento, com nome + telefone + itens + valores. Gerado manualmente ou pelo agente IA da Meta (WhatsApp Business).

**Subtipo B1 — com emojis e formatação rica:**
```
Monica Natany Zuffo Ribeiro
+55 65 99660-2405
Edifício campo D'ourique
Apto 21 - 2 andar.

🔶 Orçamento - Tapetes 🔶

💧Lavagem - Tapete 2.5 x 3.5 = 8.8m² = R$310,00
💧Lavagem - Tapete 3 x 4 = 12m² = R$420,00

💳 Total dos serviços: R$ 730,00 à vista no pix, em até 6x sem juros no cartão de crédito
💵 Pagamento em DINHEIRO: R$ 660,00.
```

**Subtipo B2 — texto corrido do bot IA Meta:**
```
Thiago Lucena 
65 99629-2289

Alameda Jatobá Qd 17 LT 13 - condomínio Florias dos lagos - Cuiabá 

sofá de 1,70m, o valor da higienização é de R$ 260,00 (pagamento via Pix ou cartão em até 3x sem juros). Se preferir pagar em dinheiro, oferecemos 10% de desconto, ficando R$ 234,00.
```

**Subtipo B3 — estofados / item por unidade / desconto global (confirmado 19/07/2026):**
```
Loise Perroni
+55 65 99901-4488

Florais dos Lagos
Rua Alameda paineira 
Quadra 20 casa 18 

🔶 Orçamento - Estofados e colchões 🔶

💧Lavagem a seco - Sofá 2 lugares - R$280,00 
💧Lavagem a seco - Sofá 4 lugares com cheise grande e almofadas soltas - R$230,00 (valor promocional)
💧Lavagem a seco - Poltrona - R$60,00un (2un = R$120,00)
💧 Lavagem à seco (higienização) colchão solteiro - R$90,00

📍💳 Total dos serviços: R$ 720,00 à vista no pix ou em até 6x sem juros no cartão de crédito ou
📌💵 Pagamento em dinheiro R$ 630,00.
```

**Subtipo B4 — misto (tapete + estofados + cortinas + persiana) com desconto global (confirmado 19/07/2026):**
```
Taynara Zuhl
65 99977-2713

Avenida F, n 277, apt 501. Edifício Solar do Bosque.
CEP: 78.050-242
Bairro Jardim Aclimacao 
Cuiabá - MT

🔶 Orçamento - Tapetes 🔶

💧Lavagem - Tapete 2,5 X 2 = 5m = R$175,00
💧Higienização - Sofá Retratil 2 módulos R$280,00 
💧Higienização - Cadeira de jantar estofada - R$40,00un (4un R$160,00)
💧Higienização - Poltrona colorida - R$60,00un (2un R$120,00)
💧Lavagem - Cortina sala (aproximadamente 10m lineares) R$280,00
💧Lavagem - Cortina quarto (aproximadamente 6,8m lineares) R$190,40
💧Lavagem - Persiana Romana 1,2 X 1,8 aproximadamente R$130,00

Total dos serviços R$1.335,40

Fechando todos os itens do orçamento R$1.200,00 em até 6x sem juros no cartão de crédito ou
📌 À vista em dinheiro / transferência bancária / pix R$1.100,00.
```

**Campos extraíveis (todos os subtipos B):**
- `client_name` — 1ª linha de texto não-numérica
- `client_phone` — linha com 8–13 dígitos e ≤2 chars não-numéricos (já tratado com Unicode invisíveis do WhatsApp)
- `client_address` — linha(s) com palavras de logradouro (rua, av, qd, lt, condomínio, apto, etc.) — ver seção 6 para variações não detectadas
- `complement` — apto, bloco, número de apartamento, CEP, bairro
- `items[]` — cada item com `service_name`, `unit_price`, `quantity`, `total_value`, `width`/`height`/`diameter`/`area_m2`, `linear_meters`, `is_promotional`
- `budget_total` — valor total do orçamento (linha "Total dos serviços")
- `payment_options[]` — PIX, cartão (Nx), dinheiro, cada um com valor e condições
- `global_discount_value` — valor do "Fechando todos os itens" (desconto por fechar pacote)
- `notes` — linha iniciada com `obs:`

**O que dispara no sistema:** `POST /automation/preview-budget` → `execute-budget`

**Estado atual:** `_smart_parse_budget` extrai nome e telefone corretamente. **Ver seção 10 para inventário completo de bugs verificados com saída real.** Os subtipos B3/B4 requerem IA (Camada B) para extração correta.

---

### Subtipo B5 — Agendamento embutido + termos longos ao final (confirmado 19/07/2026)

```
Mariane de Oliveira
+55 65 99973-1235
Edifício Amadeo Modigliani Cuiabá
Apartamento 2402
Horário 20/7 9:00

🔶 Orçamento - Estofado e Tapete 🔶

💧Lavagem a seco - Sofá 2 lugares - R$290,00 
💧Lavagem a seco - Cadeira Tipo Poltrona - R$50,00un (2un = R$100,00)
💧Lavagem a seco - Cadeira Tipo Poltrona - R$60,00un (2un = R$120,00)

📍💳 Total dos serviços: R$ 510,00 à vista no pix ou em até 5x sem juros no cartão de crédito ou
📌💵 Pagamento em dinheiro R$ 460,00.

📍 🛋 Estofados: 🛋
▪O atendimento é em domicílio.
[...texto longo de termos e condições — IGNORAR/CORTAR...]
```

**Regras específicas B5 (além das já documentadas em B1–B4):**

1. **Linha "Horário DD/M HH:MM"** é o agendamento na agenda — não faz parte do endereço nem dos itens.
   - Formato: `Horário 20/7 9:00` → `scheduled_date = "2026-07-20"`, `scheduled_time = "09:00"` (ano = corrente quando omitido).
   - Regex: `^Hor[aá]rio\s+(\d{1,2}/\d{1,2})(?:/\d{2,4})?\s+(\d{1,2}:\d{2})`
   - Aparece entre o bloco de endereço e os itens — o parser precisa reconhecer ANTES de tentar match no catálogo.

2. **Endereço = nome do prédio sem logradouro explícito.** "Edifício Amadeo Modigliani Cuiabá" é o endereço completo disponível.
   - Complemento na linha seguinte: "Apartamento 2402" = `client_complement`.
   - Para geolocalização: buscar no Maps/Geoapify pelo nome do prédio + cidade ("Edifício Amadeo Modigliani Cuiabá") e apresentar opções ao usuário.

3. **Dois itens com o mesmo nome de serviço e preços DIFERENTES = dois serviços distintos** — não é duplicata. `R$50,00un` e `R$60,00un` para "Cadeira Tipo Poltrona" indicam modelos diferentes (ex.: cadeiras de tamanhos/tipos distintos). A IA deve criar um item para cada linha, preservando os preços unitários diferentes.

4. **Tudo após o bloco de pagamento (💳/💵) deve ser IGNORADO.** Os termos e condições padrão começam com marcadores como `📍 🛋`, `▪`, ou palavras como "O atendimento é em domicílio" / "TERMOS". Gatilho de corte: primeira linha não-vazia após o bloco de pagamento que começa com `📍`, `▪`, `•`, `–`, ou contém frases como "atendimento", "domicílio", "responsabilidade", "garantia", "termos".

5. **Data sem ano ("20/7") = 20/07 do ano corrente.** Hora "9:00" = "09:00" (zero-pad).

**Campos extraíveis (além dos comuns de B):**

| Campo | Valor no exemplo |
|---|---|
| `client_name` | "Mariane de Oliveira" |
| `client_phone` | "+55 65 99973-1235" |
| `client_address` | "Edifício Amadeo Modigliani Cuiabá" |
| `client_complement` | "Apartamento 2402" |
| `scheduled_date` | "2026-07-20" |
| `scheduled_time` | "09:00" |
| `items[0]` | Lavagem a seco - Sofá 2 lugares, unit_price=290.00, qty=1 |
| `items[1]` | Lavagem a seco - Cadeira Tipo Poltrona, unit_price=50.00, qty=2, total=100.00 |
| `items[2]` | Lavagem a seco - Cadeira Tipo Poltrona, unit_price=60.00, qty=2, total=120.00 |
| `budget_total` | 510.00 (PIX/cartão), `payment_installments_max` = 5 |
| `payment_cash_value` | 460.00 |
| `terms_block_cut` | true — tudo após "📌💵 Pagamento em dinheiro R$ 460,00." descartado |

---

### TIPO C — Lista de medidas lançadas pelo dono (sem cabeçalho de técnico)

**Descrição:** O próprio dono (Diego Olivatto) cola uma lista de medidas no grupo ou digita direto na tela de Automações. Mesma estrutura do Tipo A, mas sem cabeçalho de data.

**Exemplo:**
```
Mônica 2,5x3,5
Mônica 3x4
Maria Auxiliadora 2,5x4,5
Laranja 779 1,3x2
```

**Diferença do Tipo A:** sem cabeçalho, mas o parser atual já lida com isso (`reference_date` fica nulo). "Laranja 779" = cor+código → Leonardo. Rota: igual ao Tipo A.

---

## 3. Regras de parsing de medidas

### 3.1 Separadores aceitos

| Separador | Exemplo | Interpretado como |
|---|---|---|
| `X` ou `x` | `2X3`, `2x3` | dimensões LxA |
| `×` (unicode) | `2×3` | dimensões LxA |
| `,` (vírgula decimal) | `2,5x3,5` | 2.5 × 3.5 |
| `.` (ponto decimal) | `2.5x3.5` | 2.5 × 3.5 |
| Espaço antes/depois do `x` | `2 x 3`, `2 X 3` | ok |

### 3.2 Heurística cm → m

```
se w > 10 E h > 10  → ambos em cm: w/100, h/100
se só w > 10        → w está em cm: w/100
se só h > 10        → h está em cm: h/100
se nenhum > 10      → já em metros
```

Exemplos:
- `80X3.10` → w=0.80, h=3.10 (só 80 > 10)
- `60X1.80` → w=0.60, h=1.80 (só 60 > 10)
- `60X70`   → w=0.60, h=0.70 (ambos > 10)
- `2X3`     → w=2.0, h=3.0 (nenhum > 10)
- `1.50X2`  → w=1.50, h=2.0 ✓

### 3.3 Tapetes redondos

Três formatos reconhecidos, em ordem de prioridade:

| Formato | Exemplo | Regex |
|---|---|---|
| A: diâmetro APÓS "redondo" | `Azul 599 redondo 0,8` | `redondo\s+([\d.,]+)` |
| B: diâmetro ANTES de "redondo" | `1.60 redondo` | `([\d.,]+)\s+redondo` |
| C: símbolo Ø | `Ø1.5` | `[ØDd]\s*([\d.,]+)` |

Área calculada: `π × (d/2)²` (usa `3.14159`).

Heurística cm/m igual à retangular: se `d > 10`, divide por 100.

### 3.4 Número único (sem "x" e sem "redondo")

Ex: `FormaClean Thais 2,4` → diâmetro 2.4m

Regra: se a linha tem um número decimal mas sem `xX×` → trata como diâmetro de redondo.
**Exceção:** inteiro de 1 a 9 sem decimal é ignorado (trata como contagem de tapetes prontos, não medida).

---

## 4. Regras de identificação de parceiros

### 4.1 Algoritmo de `_classify_partner(identifier)` (já implementado)

Ordem de prioridade no código:

1. **Vazio / "sem nome" / dry / dry2 / dry clean** → Leonardo (sem etiqueta)
   - Padrão: `sem nome`, `s/n`, `sem identificação`, `não identificado`, `desconhecido`, `dry`, `dry2`, `dry 2`, `dry clean`

2. **Dhiego / Parceiro Diego / Diego** → Leonardo (sem etiqueta)
   - `Dhiego` é o **motorista** da empresa Leonardo Dry Clean USA — não um parceiro separado.
   - No contexto de listas de medidas de tapetes, qualquer referência a `dhiego`, `parceiro diego` ou `diego` identifica esse motorista.
   - **NÃO confundir** com Diego Olivatto (dono da SuperDry). A função `_classify_partner` é chamada apenas dentro de `_parse_measures_text`, que processa exclusivamente mensagens de medida — portanto, "Diego" nesse contexto é sempre o motorista.
   - Regex implementada: `r'\bdhiego\b|parceiro\s+diego|\bdiego\b'` (confirmado em 19/07/2026)

3. **Emoji de coração + código 2-3 dígitos** → Leonardo com `{type: "COLOR_NUM"}`
   - `EMOJI_CODE_RE = r'^(emoji)\s*(\d{2,3})$'`
   - Ex: `💛059` → `{color: "AMARELO", number: "059"}`
   - Mapa completo de emojis → cor:

   | Emoji | Cor |
   |---|---|
   | 💛 🟡 | AMARELO |
   | 🩷 💗 💖 | ROSA |
   | 🩶 ⚪ 🤍 | CINZA |
   | 🧡 🟠 | LARANJA |
   | 💙 🔵 | AZUL |
   | 💜 🟣 | ROXO |
   | 💚 🟢 | VERDE |

3. **Cor em texto + código 2-3 dígitos** → Leonardo com `{type: "COLOR_NUM"}`
   - Cores aceitas: `azul`, `amarelo`, `cinza`, `laranja`, `roxo`, `rosa`, `verde`
   - Com ou sem espaço entre cor e número: `Rosa856` ou `Rosa 856`

4. **`higia`, `lucas`** → Higia Service (CLI-0010)

5. **`vinicius` / `vinícius`** → Higia Service (ambíguo, `is_ambiguous=True`)

6. **`forma clean`, `forma clan`, `maika`, `renan`** → Forma Clean (CLI-0009)

7. **`parceiro wesley` ou exatamente `wesley`** → Wesley Higienização (CLI-0011)

8. **`parceiro felipe`, `parceiro joao`, `domus`, `domus decor`** → Felipe/João (CLI-0016)

9. **Qualquer outra coisa** → cliente comum (Title Case normalizado)

### 4.2 Lacunas que precisam ser adicionadas ao parser

| Identificador no WhatsApp | Deve mapear para | Estado |
|---|---|---|
| ~~`Parceiro Diego`~~ | ~~novo parceiro~~ → **Leonardo** (motorista Dhiego) | ✅ Corrigido em 19/07/2026 |
| ~~`Dhiego`~~ | → **Leonardo** (motorista) | ✅ Corrigido em 19/07/2026 |
| `Dry 2` | Leonardo (sem etiqueta) | ✅ Coberto: regex `\bdry\s*\d*\b` captura "Dry 2" (espaço antes do número) |

### 4.3 Regras de grafia de nomes de clientes comuns

O parser faz `Title Case` mas **não corrige fusões de palavras**. Aliases conhecidos a normalizar:

| No WhatsApp | Nome canônico | Regra |
|---|---|---|
| `José lito`, `joselito` | `Joselito` (ou nome completo) | fusão de nome composto |
| `Boa Ventura`, `boaventura` | `Boaventura` | fusão de sobrenome |
| `Ana Livia` | `Ana Lívia` | acentuação opcional |
| `Rhafaely Medeiros` | `Rhafaely Medeiros` | grafia incomum — não "corrigir" |
| `Érika basto` | `Érika Basto` | Title Case (já tratado) |
| `Maria auxiliadora` | `Maria Auxiliadora` | Title Case (já tratado) |

**Decisão de design:** normalização de grafia de clientes deve ser **sugestão** (fuzzy match via `_resolve_client_fuzzy`), não correção automática silenciosa. Se ambíguo, apresentar candidatos para o usuário confirmar.

---

## 5. Estrutura de dados: o que cada tipo de mensagem produz no sistema

### Tipo A / C → Lançamento de medidas

```
POST /automation/execute-measures
{
  items: [
    {
      client_name: "Higia Service",        // nome canônico do parceiro ou cliente
      is_partner: true,
      partner_label: {type: "TEXT", text: "Higia Service"},
      width: null,
      height: null,
      diameter: 1.80,                      // redondo
      area_m2: 2.5447,
      reference_date: "2026-07-06T...",
      service_name: "Tapete"
    },
    {
      client_name: "Leonardo - Dry Clean USA",
      is_partner: true,
      partner_label: {type: "COLOR_NUM", color: "AMARELO", number: "059"},
      diameter: 1.60,
      area_m2: 2.0106,
      reference_date: "2026-07-06T..."
    },
    {
      client_name: "Hellen",               // cliente comum
      is_partner: false,
      width: 0.80, height: 3.10,
      area_m2: 2.48
    }
  ]
}
```

**O que cria no sistema:** preenche `width`/`height`/`diameter`/`area_m2` em itens existentes (se o cliente tem item ativo sem medida), ou cria novo orçamento+item para o parceiro com `status=AGUARDANDO_BUSCAR`, `execution_location=CLIENTE_TROUXE`, `source=AUTOMATION_MEASURES`.

### Tipo B → Orçamento com cliente

```
POST /automation/execute-budget
{
  client_name: "Monica Natany Zuffo Ribeiro",
  client_phone: "+55 65 99660-2405",
  client_address: "Edifício campo D'ourique",
  complement: "Apto 21 - 2 andar",
  items: [
    {service_name: "Lavagem Tapete", width: 2.5, height: 3.5, area_m2: 8.75, value: 310.00},
    {service_name: "Lavagem Tapete", width: 3.0, height: 4.0, area_m2: 12.0, value: 420.00}
  ],
  payment_method: "PIX_CNPJ_25995295000104",
  notes: ""
}
```

---

## 6. Padrões que a IA (Camada B) precisará interpretar

Esses padrões **não estão implementados** e requerem LLM para extração confiável.

### 6.1 Linha de item com emoji decorativo

```
💧Lavagem - Tapete 2.5 x 3.5 = 8.8m² = R$310,00
```

- Emoji `💧` = decorativo, ignorar
- `Lavagem - Tapete` = serviço (match catálogo)
- `2.5 x 3.5` = medidas
- `= 8.8m²` = m² calculado (pode confirmar ou ignorar se houver discrepância)
- `= R$310,00` = valor já calculado

### 6.2 Linha de total / condições de pagamento

```
💳 Total dos serviços: R$ 730,00 à vista no pix, em até 6x sem juros no cartão de crédito
💵 Pagamento em DINHEIRO: R$ 660,00.
```

Campos a extrair:
- `total_value` = 730.00
- `payment_options[]`:
  - `{method: "PIX", value: 730.00}`
  - `{method: "CREDITO", installments: 6, value: 730.00, note: "sem juros"}`
  - `{method: "DINHEIRO", value: 660.00, discount_pct: ~9.6}`

### 6.3 Texto corrido do bot IA Meta (Subtipo B2)

```
sofá de 1,70m, o valor da higienização é de R$ 260,00 (pagamento via Pix ou cartão em até 3x sem juros). Se preferir pagar em dinheiro, oferecemos 10% de desconto, ficando R$ 234,00.
```

Campos a extrair:
- `service_name` = "Higienização Sofá" (tamanho "1,70m" → atributo do sofá, não tapete)
- `value_pix` = 260.00
- `value_credito` = 260.00, max_installments = 3
- `value_dinheiro` = 234.00 (desconto 10%)

### 6.4 Variações de nomes de parceiros não cobertas pelo parser atual

| Input | Esperado |
|---|---|
| ~~`Parceiro Diego`~~ | → **Leonardo** (motorista Dhiego) — ✅ corrigido 19/07/2026 |
| `Higia Beatriz` | → Higia Service + nome da cliente final ("Beatriz") para etiqueta |
| `FormaClean Ana` | → Forma Clean + nome do cliente final |
| `Boa Ventura` | → `_resolve_client_fuzzy("Boa Ventura")` → candidatos |
| `José lito` | → `_resolve_client_fuzzy("Joselito")` (fusão antes da busca) |

### 6.5 Padrões de preço por unidade (B3/B4)

**Formato:** `R$X,XXun (Nun = R$Y,YY)` — preço unitário + quantidade + subtotal

```
💧Lavagem a seco - Poltrona - R$60,00un (2un = R$120,00)
💧Higienização - Cadeira de jantar estofada - R$40,00un (4un R$160,00)
💧Higienização - Poltrona colorida - R$60,00un (2un R$120,00)
```

Campos a extrair:
- `unit_price` = 60.00
- `quantity` = 2
- `total_value` = 120.00 (ou calcular: unit_price × quantity)

Regex sugerida para unit price: `R\$\s*([\d.,]+)\s*un`
Regex sugerida para quantidade: `\((\d+)\s*un`

**Variações observadas:**
- `(2un = R$120,00)` — com `=` e valor total explícito
- `(4un R$160,00)` — sem `=`, valor direto após espaço

### 6.6 Flag "valor promocional"

```
💧Lavagem a seco - Sofá 4 lugares com cheise grande e almofadas soltas - R$230,00 (valor promocional)
```

- `(valor promocional)` em parênteses após o valor = flag de desconto especial no item
- **Não é** uma quantidade — é um indicador de preço abaixo da tabela
- Campo a extrair: `is_promotional: true`
- A IA deve identificar esse padrão e não tentar extrair número de unidades dele

### 6.7 Linhas de total / desconto global

Quatro variações confirmadas nos exemplos:

| Variação | Exemplo | Campo |
|---|---|---|
| Com emoji e `:` | `📍💳 Total dos serviços: R$ 720,00 à vista no pix ou em até 6x sem juros` | `budget_total` + `payment_options` |
| Sem emoji, sem separador | `Total dos serviços R$1.335,40` | `budget_total` |
| Desconto global | `Fechando todos os itens do orçamento R$1.200,00 em até 6x sem juros no cartão` | `global_discount_value` + `installments` |
| Dinheiro com emoji | `📌💵 Pagamento em dinheiro R$ 630,00.` | `payment_cash_value` |
| Dinheiro múltiplos métodos | `📌 À vista em dinheiro / transferência bancária / pix R$1.100,00.` | `payment_cash_value` (engloba dinheiro/pix/ted) |

**Regra:** a IA deve reconhecer essas linhas como metadados do orçamento e **não** incluí-las na lista de `items[]`.

Gatilhos para identificar como linha de total/pagamento:
- Contém "total dos serviços"
- Contém "fechando todos os itens" ou "fechando o orçamento"
- Contém "pagamento em dinheiro" + valor
- Contém "à vista em dinheiro" ou "pix" + valor sem item associado

### 6.8 Medidas de cortinas (metros lineares)

```
💧Lavagem - Cortina sala (aproximadamente 10m lineares) R$280,00
💧Lavagem - Cortina quarto (aproximadamente 6,8m lineares) R$190,40
```

- Tipo de medida: `METRAGEM_LINEAR` (já existe no sistema como `MeasureType`)
- Campo: `linear_meters: 10.0` / `linear_meters: 6.8`
- Regex sugerida: `(\d+[,.]?\d*)\s*m\s*(linear|lineares)`
- "aproximadamente" = estimativa; o valor real será confirmado após execução
- **Diferente de tapete/persiana:** não é `width × height`, é metragem corrida

### 6.9 Variações de endereço não detectadas pelo parser atual

O `_ADDR_KW` do `_smart_parse_budget` detecta endereço por palavras-chave de logradouro. Casos que **escapam** e vão para `items[]` incorretamente:

| Linha | Problema | Solução para IA |
|---|---|---|
| `Florais dos Lagos` | nome de condomínio sem "condomínio" antes | tratar como address se estiver entre telefone e rua, ou usar posição |
| `Cuiabá - MT` | cidade - estado sem keyword | detectar pelo padrão `<cidade> - <sigla_estado>` |
| `CEP: 78.050-242` | CEP é detectado (keyword "CEP") mas descartado se já tem endereço | armazenar CEP separado de `client_address` |
| `Bairro Jardim Aclimacao` | detectado mas descartado (só primeiro endereço é salvo) | armazenar todos os componentes separados |

**Decisão de design para IA:** montar objeto de endereço completo com campos separados:
```json
{
  "address": {
    "logradouro": "Avenida F, n 277",
    "complemento": "apt 501, Edifício Solar do Bosque",
    "bairro": "Jardim Aclimacao",
    "cidade": "Cuiabá",
    "estado": "MT",
    "cep": "78050-242",
    "condominio": "Florais dos Lagos",
    "full_text": "Avenida F, n 277, apt 501. Edifício Solar do Bosque. CEP: 78.050-242, Bairro Jardim Aclimacao, Cuiabá - MT"
  }
}
```

### 6.10 Linha de cabeçalho do orçamento (ignorar como item)

```
🔶 Orçamento - Estofados e colchões 🔶
🔶 Orçamento - Tapetes 🔶
```

- Linha puramente decorativa/organizacional — **não é um item de serviço**
- Atenção: o título pode **não refletir** todos os itens do orçamento (ex: "Tapetes" mas contém sofá, cortina, persiana)
- Gatilho para descartar: linha que começa e termina com `🔶` OU contém "orçamento -" precedido de emoji
- Regex: `[🔶]\s*Orçamento\s*-\s*.+[🔶]` (case-insensitive)

### 6.11 Typo "5m" no lugar de "5m²"

```
💧Lavagem - Tapete 2,5 X 2 = 5m = R$175,00
```

- `= 5m` aqui é o m² calculado (2,5 × 2 = 5), mas escrito com "m" em vez de "m²"
- O parser atual **extrai corretamente** a medida `2,5 X 2` → `area_m2: 5.0` via regex NxM
- O valor `5m` após o `=` pode ser ignorado (calculado das dimensões)
- Para a IA: quando houver `NxM` na linha, calcular área e não confiar no valor "Xm" intermediário

---

## 7. Regras de negócio críticas para a IA

1. **"Sem nome" é sempre Leonardo, nunca cliente sem cadastro.** O motorista do Leonardo tem hábito documentado de entregar sem etiqueta.

2. **Mesmo nome aparecendo N vezes = N tapetes diferentes** do mesmo dono. Não agrupar; criar um item por linha.

3. **"Parceiro Diego", "Dhiego" e "Diego" (em lista de medidas) = motorista do Leonardo Dry Clean USA — classificar como Leonardo.** Dhiego é o motorista da empresa parceira Leonardo Dry Clean USA. No contexto de mensagens de medida de tapetes (única situação em que `_classify_partner` é chamado), qualquer referência a esses nomes é esse motorista. Diego Olivatto (dono da SuperDry) não aparece como identificador de tapete em mensagens do técnico Marcos. Regra confirmada e implementada em 19/07/2026.

5. **Formato de medida: ordem = largura × comprimento** (não importa qual é maior). Não tentar inferir qual dimensão é qual.

6. **Etiqueta cor+número é reaproveitada ao longo do tempo.** Mesmo `Cinza 870` pode aparecer com dimensões diferentes em meses diferentes — não é duplicata, é tapete novo. Só é duplicata se mesma etiqueta + mesma dimensão já existir no mesmo ciclo de fechamento mensal.

7. **Referência de data do cabeçalho WhatsApp se propaga para todas as linhas seguintes** até o próximo cabeçalho. Se uma mensagem tem dois blocos de datas, os itens de cada bloco têm datas diferentes.

8. **Valor em dinheiro ≠ valor base.** Quando texto tem dois valores (pix/cartão e dinheiro), o valor de pix/cartão é o preço padrão; dinheiro tem desconto (normalmente 10%). Registrar como `payment_method` e `payment_discount`, não como dois itens diferentes.

9. **m² informado no texto pode diferir do calculado pelas dimensões** (arredondamentos). Usar dimensões brutas para cálculo interno; valor m² do texto é só confirmação visual.

10. **"Higia" sem complemento = tapete do acervo próprio da Higia**, não de cliente final. Se vier "Higia Beatriz 2x3", o parser atual ignora "Beatriz" — ⚠️ lacuna. A IA deve reconhecer o padrão `PARCEIRO NOME_CLIENTE MEDIDA` para parceiros como Higia/Forma Clean que identificam o cliente final.

---

## 8. Prompt de referência para Camada B (rascunho)

```
Você é o parser de mensagens WhatsApp da SuperDry Lavanderia.

TAREFA: extrair dados estruturados da mensagem abaixo.

CONTEXTO DO NEGÓCIO:
- Parceiros (não são clientes finais): Leonardo/Dry Clean USA, Higia Service, Forma Clean, Wesley Higienização, Felipe/João Farias
- Leonardo usa etiquetas cor+número: "💛059", "Azul 581", etc.
- "Sem nome" = sempre Leonardo
- Medidas: LARGURAxALTURA, separadores X/x/×/virgula/ponto, cm se > 10 (dividir por 100)
- "redondo" ou "Ø" = tapete circular com diâmetro (área = π×(d/2)²)

CATÁLOGO DISPONÍVEL (resumo): {catalog_summary}

MENSAGEM:
{message}

RETORNE JSON:
{
  "type": "MEASURES" | "BUDGET" | "UNKNOWN",
  "items": [...],
  "client_name": "...",
  "client_phone": "...",
  "client_address": "...",
  "notes": "..."
}
```

---

## 9. Pontos de integração: onde a IA se conecta ao sistema

| Ponto | Endpoint existente | O que muda com IA |
|---|---|---|
| Preview de medidas | `POST /automation/preview-measures` | IA pré-processa antes de enviar ao parser Python |
| Execução de medidas | `POST /automation/execute-measures` | sem mudança — IA já entrega payload limpo |
| Preview de orçamento | `POST /automation/preview-budget` | IA pré-processa B1/B2 antes do `_smart_parse_budget` |
| Execução de orçamento | `POST /automation/execute-budget` | sem mudança |
| Novo endpoint opcional | `POST /automation/ai-parse` | entrada crua → IA classifica tipo + extrai → redireciona ao endpoint correto |

---

---

## 10. Inventário de bugs do `_smart_parse_budget` (verificado com saída real — 19/07/2026)

> Rastreado executando os exemplos 3 (Loise Perroni) e 4 (Taynara Zuhl) contra a lógica atual (`_item_name_only`, `_extract_value`, `_parse_line_measures`). Nenhum desses bugs foi corrigido ainda — documentados aqui para guiar implementação da Camada B.

### BUG 1 — `_item_name_only` não strip emojis de prefixo

**Impacto: crítico para match no catálogo**

`_item_name_only` usa `re.split` no primeiro separador ` - ` / `: `, devolvendo tudo à esquerda. Para linhas com `💧` como prefixo antes do separador, retorna o emoji junto:

```python
_item_name_only("💧Lavagem a seco - Sofá 2 lugares - R$280,00")
→ "💧Lavagem a seco"   # emoji no nome degrada o fuzzy match no catálogo
```

O token `💧` não é removido e entra na tokenização de `_svc_score`. Resultado: o catálogo provavelmente não consegue match limpo em "💧Lavagem" vs. "Lavagem a Seco - Sofá".

**Solução para IA:** strip de emojis Unicode antes de qualquer processamento. Regex: `re.sub(r'[\U0001F300-\U0001FAFF\U00002600-\U000027FF]', '', line).strip()`

---

### BUG 2 — `_extract_value` sangra dígitos da descrição quando há múltiplos ` - `

**Impacto: crítico — valor errado por fator 10x**

`_extract_value` faz `re.split(..., maxsplit=1)` no primeiro ` - ` e tenta converter `parts[1]` para float, removendo tudo que não é dígito/vírgula/ponto. Quando a descrição entre o primeiro e o último ` - ` contém números (lugares do sofá, módulos, etc.), esses dígitos sangram para o valor:

```python
_extract_value("💧Lavagem a seco - Sofá 2 lugares - R$280,00")
# parts[1] = "Sofá 2 lugares - R$280,00"
# strip → "2280,00" → 2280.0  ← ERRADO (deu 2280 em vez de 280)

_extract_value("💧Higienização - Sofá Retratil 2 módulos R$280,00")
# parts[1] = "Sofá Retratil 2 módulos R$280,00"
# strip → "2280,00" → 2280.0  ← ERRADO
```

Mesma falha para cortinas com metros lineares:
```python
_extract_value("💧Lavagem - Cortina sala (aproximadamente 10m lineares) R$280,00")
# parts[1] = "Cortina sala (aproximadamente 10m lineares) R$280,00"
# strip → "10280,00" → 10280.0  ← ERRADO
```

---

### BUG 3 — `_extract_value` retorna 0 para o padrão `R$X,XXun (Nun = R$Y,YY)`

```python
_extract_value("💧Lavagem a seco - Poltrona - R$60,00un (2un = R$120,00)")
# parts[1] = "Poltrona - R$60,00un (2un = R$120,00)"
# strip → "60,002120,00" → duas vírgulas → replace fallback → ValueError → 0.0
```

Além de retornar 0, não extrai `unit_price`, `quantity` nem `total_value`.

---

### BUG 4 — Valor após `=` não é extraído (padrão `= R$VALUE`)

```python
_extract_value("💧Lavagem - Tapete 2,5 X 2 = 5m = R$175,00")
→ 0.0  # "=" não está nos separadores reconhecidos por _extract_value
```

O `_extract_value` usa apenas ` - ` e `: ` como separadores. Linhas de tapete com `= R$VALUE` ao final ficam sem valor.

---

### BUG 5 — Total/pagamento vão para `items[]` em vez de metadados

```
"Total dos serviços R$1.335,40"            → item? (name completo, val=0)
"Fechando todos os itens... R$1.200,00..." → item? (name completo, val=0)
"📌💵 Pagamento em dinheiro R$ 630,00."    → item? (val=0)
"📌 À vista em dinheiro / pix R$1.100,00." → item? (val=0)
```

Todas essas linhas chegam ao branch de item em `_smart_parse_budget` porque não têm palavras de logradouro e o score no catálogo é baixo. Nenhuma é reconhecida como metadado de pagamento.

Único caso parcialmente extraído (com `: ` como separador):
```python
_extract_value("📍💳 Total dos serviços: R$ 720,00 à vista no pix ou em até 6x sem juros...")
→ 720.006  # "6x" sangra: "720,006" → float 720.006 (errado em centavos)
```

---

### BUG 6 — Condomínio sem keyword vai para `items[]`

```python
# "Florais dos Lagos" — nenhum keyword de logradouro
→ item? (name="Florais dos Lagos", val=0)  # deveria ser parte do endereço
```

`_ADDR_KW` requer palavras explícitas (`rua`, `av`, `quadra`, `condomínio`, etc.). Nomes de condomínio/loteamento escritos diretamente (sem prefixo) não são detectados.

---

### BUG 7 — "Cuiabá - MT" vira item com nome "Cuiabá"

```python
_item_name_only("Cuiabá - MT")
→ "Cuiabá"   # split no " - ", name = "Cuiabá"
# sem keyword de endereço → vai para items[]
```

Padrão `<cidade> - <sigla_UF>` não está no `_ADDR_KW`.

---

### BUG 8 — CEP e bairro descartados (só primeiro match de endereço é salvo)

```
[03] ENDEREÇO ✅  "Avenida F, n 277, apt 501. Edifício Solar do Bosque."  # salvo
[04] ENDEREÇO2⚠️ "CEP: 78.050-242"         # descartado
[05] ENDEREÇO2⚠️ "Bairro Jardim Aclimacao" # descartado
```

`_smart_parse_budget` tem `if not res.client_address: res.client_address = line` — só a primeira linha de endereço é armazenada. CEP e bairro (que são detectados pelos keywords corretos) são silenciosamente descartados.

---

### BUG 9 — Linha de cabeçalho `🔶 Orçamento - ... 🔶` vai para `items[]`

```python
_item_name_only("🔶 Orçamento - Estofados e colchões 🔶")
→ "🔶 Orçamento"   # vai para items[] com score baixo no catálogo
```

Deveria ser descartada (linha puramente decorativa).

---

### Resumo: o que funciona vs. o que não funciona nos subtipos B3/B4

| Campo | Estado | Detalhe |
|---|---|---|
| `client_name` | ✅ OK | 1ª linha extraída corretamente |
| `client_phone` | ✅ OK | regex de dígitos funciona |
| `client_address` (1ª linha com keyword) | ✅ OK | "Rua ...", "Avenida ..." detectados |
| Medidas NxM de tapete/persiana | ✅ OK | `_parse_line_measures` correto: `2,5 X 2` → `{width:2.5, height:2.0, area_m2:5.0}` e `1,2 X 1,8` → `{width:1.2, height:1.8, area_m2:2.16}` |
| Valor de colchão/item simples (`- R$90,00`) | ✅ OK | separador único ` - ` sem dígitos na descrição |
| Emoji prefixo `💧` stripped do nome | ❌ NÃO | retorna `"💧Lavagem a seco"` — degrada match catálogo |
| Valor extraído quando descrição tem número | ❌ BUG | "2 lugares" sangra: `280` → `2280` |
| Valor extraído no padrão `= R$175,00` | ❌ NÃO | retorna 0.0 |
| Preço unitário `R$X,XXun` | ❌ NÃO | retorna 0.0, sem `unit_price`/`quantity` |
| Flag `(valor promocional)` | ❌ NÃO | sem campo |
| Metros lineares de cortina | ❌ NÃO | sem campo |
| Linhas de total/pagamento | ❌ BUG | vão para `items[]` |
| Desconto global "Fechando todos os itens" | ❌ NÃO | sem campo |
| CEP, bairro, 2ª linha de endereço | ❌ DESCARTADO | só 1ª linha salva |
| Condomínio sem keyword | ❌ NÃO | vai para `items[]` |
| "Cuiabá - MT" | ❌ BUG | vira item com nome "Cuiabá" |
| Header `🔶 Orçamento - ... 🔶` | ❌ BUG | vai para `items[]` |

---

### Análise B5 × `_smart_parse_budget` (linha a linha)

Simulação do parser atual contra o exemplo Mariane de Oliveira:

| Linha | O que o parser faz | Correto? |
|---|---|---|
| `Mariane de Oliveira` | `client_name` (i=0) | ✅ |
| `+55 65 99973-1235` | `client_phone` (regex dígitos) | ✅ |
| `Edifício Amadeo Modigliani Cuiabá` | sc<0 + endereço ainda vazio → `client_address` (fallback `elif not res.client_address`) | ✅ (funciona por acidente — "edifício" **não** está em `_ADDR_KW`) |
| `Apartamento 2402` | `looks_addr=True` ("apartamento" está em `_ADDR_KW`), mas `client_address` já preenchido → cai no `else:` → vai para `items[]` | ❌ BUG 8 — complemento descartado/viralizado como item |
| `Horário 20/7 9:00` | sc<0 + `client_address` já preenchido → `else:` → `items[]` | ❌ BUG NOVO B5 — data de agendamento viralizada como item; campo inexistente no parser |
| `🔶 Orçamento - Estofado e Tapete 🔶` | BUG 9: vai para `items[]` como item de baixo score | ❌ |
| `💧Lavagem a seco - Sofá 2 lugares - R$290,00` | BUG 1 + BUG 2: emoji no nome; "2" de "2 lugares" sangra → `value=2290.0` | ❌ |
| `💧Lavagem a seco - Cadeira Tipo Poltrona - R$50,00un (2un = R$100,00)` | BUG 1 + BUG 3: emoji + padrão `un` → `value=0`, sem `unit_price`/`quantity` | ❌ |
| `💧Lavagem a seco - Cadeira Tipo Poltrona - R$60,00un (2un = R$120,00)` | Idem BUG 1 + BUG 3; gera item com mesmo nome do anterior (`value=0`) — não há como distinguir dos dois preços diferentes | ❌ |
| `📍💳 Total dos serviços: R$ 510,00 à vista...` | BUG 5: vai para `items[]` | ❌ |
| `📌💵 Pagamento em dinheiro R$ 460,00.` | BUG 5: vai para `items[]` | ❌ |
| `📍 🛋 Estofados: 🛋` e tudo depois | Sem cutoff: todas as linhas dos termos viram itens de score baixo | ❌ BUG NOVO B5 |

**Novos bugs específicos do B5 (não documentados nos B3/B4):**

**BUG 10 — Linha "Horário DD/M HH:MM" vai para `items[]`** *(novo)*

Não existe no parser nenhum padrão para reconhecer agendamento embutido. O resultado: um "item" com `service_name="Horário 20/7 9:00"` e `value=0.0` vai para o catálogo sem match.

**BUG 11 — Termos e condições após bloco de pagamento não são cortados** *(novo)*

O parser não detecta o fim do bloco de orçamento. Qualquer texto após `📌💵 Pagamento em dinheiro...` (termos padrão, políticas, garantias) vira uma sequência de itens com score=0. Em B5, isso pode gerar dezenas de "itens" falsos.

**BUG 12 — "edifício" ausente de `_ADDR_KW`** *(novo — funciona por acidente, frágil)*

"Edifício Amadeo Modigliani Cuiabá" é salvo como `client_address` porque sc<0 E endereço ainda vazio no momento em que a linha é processada. Mas se o parser processar outra linha antes (que também tenha sc<0 e endereço vazio), o endereço real seria perdido. Solução: adicionar `edif[ií]cio` a `_ADDR_KW`.

**Resumo: o que funciona vs. o que não funciona no subtipo B5**

| Campo | Estado | Detalhe |
|---|---|---|
| `client_name` | ✅ OK | |
| `client_phone` | ✅ OK | |
| `client_address` (nome do prédio) | ✅ OK por acidente | "edifício" não está em `_ADDR_KW`; funciona via fallback |
| `client_complement` ("Apartamento 2402") | ❌ BUG 8 | vai para `items[]` |
| `scheduled_date` / `scheduled_time` | ❌ BUG 10 | campo inexistente; linha vai para `items[]` |
| Header `🔶 Orçamento - ... 🔶` | ❌ BUG 9 | vai para `items[]` |
| Valor sofá (descrição com número) | ❌ BUG 2 | "2 lugares" → `2290.0` |
| Preço por unidade `R$50,00un` | ❌ BUG 3 | `value=0`, sem `unit_price`/`quantity` |
| Dois itens mesma desc + preços distintos | ❌ BUG 3 | ambos retornam 0; distinção de preço perdida |
| Linhas de total/pagamento | ❌ BUG 5 | vão para `items[]` |
| Termos após bloco pagamento | ❌ BUG 11 | sem cutoff; dezenas de itens falsos |

*Última atualização: 2026-07-19*
