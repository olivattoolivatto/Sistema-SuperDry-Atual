# Forma de Trabalho do Dono & Visão de Automação

Documento-mestre que descreve **como o dono opera** e **como o sistema deve se
adequar** a ele. Objetivo declarado pelo dono: que o sistema seja "mais que um ERP
— quase um assistente pessoal automatizado", que execute o máximo de funções e
aponte prioridades (cobranças, compras, estoque, o que resolver primeiro).

> Leia junto: [CLAUDE.md](../CLAUDE.md) (arquitetura), [GESTOR_FINANCEIRO.md](GESTOR_FINANCEIRO.md),
> [INTEGRACOES_PAGAMENTO.md](INTEGRACOES_PAGAMENTO.md).

---

## 1. Fluxo operacional real (como o dono trabalha)

```
1. ATENDIMENTO (WhatsApp Business)
   - Maioria dos contatos chega pelo WhatsApp.
   - Novos clientes hoje são atendidos pela IA da Meta (atendente automático).
   - Dados disponíveis no início: PRIMEIRO NOME + TELEFONE + fotos/descrição dos itens
     (tapete, sofá, etc). Endereço NÃO é pedido ainda.

2. ORÇAMENTO
   - A partir das fotos/descrições, monta o orçamento (itens + valores).
   - Envia ao cliente (hoje manual; meta: automático pelo sistema).

3. CONFIRMAÇÃO → ENDEREÇO
   - Só pede o endereço quando o serviço é confirmado.
   - Endereço serve para roteirização (não antes).

4. ROTEIRIZAÇÃO (agrupamento inteligente)
   - Agrupa serviços por REGIÃO da cidade (bairros próximos juntos).
   - Separa por VEÍCULO:
       • TAPETES  → CARRO (consome mais, mas comporta volume de tapetes)
       • LIMPEZAS / IMPERMEABILIZAÇÕES → MOTO (leva o equipamento, consome menos)
   - Por isso o sistema calcula rotas para CARRO e MOTO (Geoapify/OSRM).
   - Critério: eficiência econômica + deslocamento.

5. AGENDA
   - Após roteirizar, joga tudo na Agenda (Google Calendar) p/ organização visual.

6. EXECUÇÃO (técnico)
   - Repassa a agenda ao técnico, que segue endereços e executa.
   - Técnico RARAMENTE recebe no local → cobrança fica para depois.

7. FINANCEIRO
   - Controle de recebíveis é crítico: parte dos clientes "enrola" para pagar.
   - Precisa de cobrança automatizada + vigilância de inadimplência.
```

### Mapeamento fluxo → sistema (entidades já existentes)
| Etapa do dono | No sistema |
|---|---|
| Atendimento/itens | Cliente (CLI) + Orçamento (ORC) + Itens (ITM) |
| Orçamento | `BudgetItem` com `total_value`, modos de execução |
| Endereço na confirmação | `client.address` / endereços por etapa do item |
| Roteirização carro/moto | Rotas Geoapify/OSRM (`vehicle_type` CARRO/MOTO) |
| Agenda | `calendar_events` (Google Calendar OAuth) |
| Execução | Modo Técnico + status do item |
| Financeiro | `payment_records`, cobrança consolidada (CPG), taxas/líquido |

---

## 2. O que o dono quer agora: "comando → orçamento pronto"

Na seção **Automações**, dar uma entrada (texto do WhatsApp, eventualmente fotos)
e o sistema **devolver um orçamento pronto** (cliente + itens + valores sugeridos).

### Estado atual da automação de orçamento (já existe, mas básico)
- `POST /api/automation/preview-budget` + `/execute-budget` (server.py).
- Parser `_parse_budget_text`: **rígido e posicional** —
  linha1=nome, linha2=telefone, linha3=endereço, linha4+=`serviço - valor`, `obs:`.
- Limitação: não casa itens com o **catálogo** (85 serviços), não calcula preço,
  não entende texto livre de WhatsApp, não lê fotos.
- Já existe um parser SOFISTICADO de medidas de tapete (`_parse_measures_text`)
  com classificação de parceiros e heurística cm/m — bom modelo de referência.

### Design proposto (camadas, do simples ao avançado)
**Camada A — Casamento com catálogo (sem IA) — ✅ IMPLEMENTADA (jun/2026):**
- Parser por CONTEÚDO (não posicional): `_smart_parse_budget(text, services)` classifica
  cada linha — nome (1ª linha), telefone (dígitos), item (casa no catálogo), endereço
  (palavras-chave; opcional, pode vir depois), `obs:`. Adequado ao fluxo do dono
  (nome+telefone+itens, sem endereço no início).
- Matcher `match_service_in_catalog` / `_svc_score`: fuzzy match por tokens, remove medidas
  (NxM), vieses de domínio (sem "imperme"→prioriza lavagem; prefere variante "na empresa").
  Traz `service_id`, `service_name`, `sale_price`, `measure_type`, `match_score`, `low_confidence`.
- `POST /automation/preview-budget` enriquece itens (valor do catálogo p/ UNITARIO; flag
  `needs_measure` p/ tapetes/m²). `execute-budget` grava `service_id`/`measure_type`/categoria.
- Frontend `Automations.js`: preview mostra serviço casado, preço, ⚠️ baixa confiança e
  "precisa medida". Itens editáveis antes de criar.
- **Pendente da Camada A:** medidas de tapete no fluxo de orçamento (reusar `_parse_measures_text`)
  para calcular m² × preço; hoje tapete entra como "precisa medida" (valor definido depois).

**Camada B — Interpretação por IA (Claude API):**
- Texto livre do WhatsApp (e depois fotos) → Claude extrai {nome, telefone, lista de
  itens normalizados} e sugere o serviço do catálogo + medida. Resolve linguagem
  natural ("dois tapetes e um sofá de canto").
- Mantém o preview/confirmação antes de criar (humano no loop).
- Requer `ANTHROPIC_API_KEY`. Usar prompt caching (catálogo no cache).

**Camada C — Visão de fotos:**
- Fotos do item → Claude (multimodal) estima tipo/medidas aproximadas → sugere serviço.
- Sempre como SUGESTÃO confirmável (medidas reais confirmam no item).

> Regra de pagamento padrão (crédito Nx pelo valor) e taxas já se aplicam ao
> orçamento gerado — ver CLAUDE.md.

---

## 3. Pergunta do dono: integrar a IA da Meta (WhatsApp) ao sistema?

**Resposta honesta:** a "IA da Meta" que responde automaticamente **não expõe** um
jeito de chamar o seu sistema/enviar orçamentos elaborados por ele. O caminho real:

- **WhatsApp Business Cloud API (oficial da Meta):** seu sistema vira o cérebro do
  atendimento. Recebe mensagens via **webhook**, processa (gera orçamento) e
  **responde/Envia** (texto, PDF, link de pagamento). Substitui/complementa a IA
  genérica da Meta por um bot do SEU domínio (mais inteligente para lavanderia).
- Requisitos: número no WhatsApp Business Platform, App Meta, token, webhook público
  (já temos exposição via **Tailscale Funnel** — mesma infra do webhook InfinitePay).
- Fluxo alvo: cliente manda foto/descrição → Cloud API → sistema (Camada B/C) monta
  orçamento → envia de volta + opção de pagamento (InfinitePay) → confirma → endereço
  → entra na roteirização.

**Resumo:** sim, é possível enviar orçamentos elaborados pelo sistema via WhatsApp —
porém pela **Cloud API** (integração própria), não acoplando à IA nativa da Meta.

---

## 4. Visão "assistente pessoal" — vigilâncias automáticas (backlog)

O dono quer que o sistema aponte direções e prioridades. Módulos de vigilância:

| Vigilância | O que monitora | Ação/sinal |
|---|---|---|
| **Cobranças** | Itens ENTREGUE/EXECUTADO com `payment_status` PENDENTE/PARCIAL; dias em aberto | Lista priorizada de quem cobrar (e "enroladores" recorrentes) |
| **Compras/Estoque** | Insumos de lavagem (a criar: coleção `inventory`) | "Comprar X" quando abaixo do mínimo; prioridade |
| **Agenda/Execução** | Tarefas do dia, atrasos, itens parados em status | "Resolver hoje" |
| **Financeiro (gestor)** | Saldo, contas a pagar, faturas de cartão | Fluxo de caixa + alertas |
| **Operacional** | Itens órfãos/sem rota, medidas não confirmadas | Higiene de dados (ver bug de rota órfã já corrigido) |

Saída ideal: um **painel "Meu Dia"** (ou resumo no Dashboard) com prioridades
ordenadas, e/ou um digest no WhatsApp.

> **Estoque/Compras** se conecta ao [GESTOR_FINANCEIRO.md](GESTOR_FINANCEIRO.md):
> uma compra de insumo é um Lançamento (LCT) com entradas por categoria.

---

## 5. Roadmap de automação (proposto)

1. **Orçamento por comando — Camada A** (catálogo + fuzzy match) — entrega rápida.
2. **Camada B (Claude API)** — texto livre do WhatsApp → orçamento.
3. **WhatsApp Cloud API** — receber/enviar mensagens (webhook na infra Tailscale).
4. **Camada C (fotos)** — visão multimodal sugerindo itens.
5. **Painel "Meu Dia"** — vigilância de cobranças/compras/agenda/estoque.
6. **Estoque/Compras** — coleção `inventory` + alertas de reposição.

Decisões pendentes do dono: usar Claude API (sim/não, custo), adotar WhatsApp Cloud
API (migrar do atendimento atual), prioridade entre orçamento-IA e painel "Meu Dia".
