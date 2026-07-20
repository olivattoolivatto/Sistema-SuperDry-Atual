# Relatório de Inadimplência — SuperDry Lavanderia
**Período analisado:** 01/06/2026 a 19/07/2026  
**Gerado em:** 19/07/2026  
**Fontes:** Google Calendar (eventos colorId=11/Vermelho) + MongoDB produção (Oracle VM)

---

## Campos reais encontrados no MongoDB (diagnóstico)

A coleta anterior usou nomes de campo errados. Os nomes reais na coleção `budgets` são:

| Campo buscado antes | Campo real no banco | Observação |
|---|---|---|
| `total_price` | **`total_value`** | Valor numérico correto |
| `status` | *não existe* no nível de budget | Sem campo de status no documento pai |
| `payment_status` | **`payment_status`** | Existe, mas com valores `"PENDENTE"` / `None` / `"PAGO"` |
| — | **`payment_received`** | Booleano como string: `"False"` ou `"True"` |

A coleção **`budget_items`** está **vazia** em produção — os itens ficam embutidos em `budgets.items` (array dentro do documento pai). O script `fetch_calendar_report.py` precisa ser corrigido para usar `total_value` e `payment_received`.

**Distribuição de `payment_status` no banco (todos os orçamentos):**
- `"PENDENTE"`: 107 documentos
- `null` (campo ausente): 43 documentos
- `"PAGO"`: 1 documento

---

## Resumo Executivo — Período 01/06–19/07/2026

| Indicador | Valor |
|---|---|
| Orçamentos não pagos no sistema (período) | **146 de 147** |
| Clientes únicos com ORC em aberto | **62** |
| **Total em aberto no sistema (período)** | **R$ 42.203,94** |
| Eventos vermelhos no Calendar (período) | 22 |
| → Clientes/serviços (excl. administrativos) | **21** |
| Cruzamento confirmado (vermelho + ORC) | **14 clientes** |
| Clientes com ORC mas sem evento vermelho | **48 clientes** ← atenção |
| Clientes no Calendar sem ORC no sistema | **6 casos** |

> **Atenção:** Há R$ 32.000+ em ORCs sem nenhuma marcação vermelha no Calendar — o Calendar reflete apenas o que o usuário marcou manualmente. O sistema ERP é a fonte completa.

---

## 1. Dupla Confirmação — Evento Vermelho + ORC em Aberto

Clientes que aparecem **tanto** marcados de vermelho no Calendar **quanto** com orçamento não pago no sistema. Ordenados por valor total no sistema.

### 🔴 Edifício Felicitá
- **Evento Calendar:** 09/06/2026 — "Pediu retoque"
- **Serviços:** 2 poltronas + 2 sofás de canto
- **Contato:** Síndico Rubens Tomio +55 65 99968-1222 | Zelador Cristiano
- **No sistema:** ORC-0000101 (R$780) + ORC-0000144 (R$780) = **R$ 1.560,00**
- **Observação:** Dois orçamentos com o mesmo valor — provavelmente um é duplicata ou registro de retoque. Verificar antes de cobrar.
- **Ação:** Combinar pagamento + retoque simultaneamente.

### 🔴 Higia Service (Vinícius/Lucas)
- **Evento Calendar:** 11/06/2026 — "NAO FOI PAGO AINDA" (confirmação explícita)
- **Período coberto:** 13/05 a 08/06/2026 (15 lotes de tapetes)
- **Último acerto:** R$810 em 15/05/2026
- **No sistema:** 8 ORCs — ORC-0000040 ao ORC-0000087 = **R$ 960,64**
- **Observação:** O Calendar registra total de R$2.181,80 (dh) / R$2.399,98 (pix) para o período completo após o último acerto, mas o sistema só mostra R$960,64. A diferença pode ser de ORCs não lançados ou valores calculados de forma diferente (m² × tarifa vs. preço fixo por ORC).
- **Ação:** Conciliar total Calendar vs. sistema antes do acerto. Verificar se todos os lotes estão cadastrados.

### 🔴 Sandra Castaldelli (Clínica Vitalle)
- **Evento Calendar:** 23/06/2026 — "esse cliente está cadastrado"
- **Serviço:** Tapete 12m² (3×4m) — R$420,00
- **No sistema:** ORC-0000089 (R$210) + ORC-0000148 (R$420) = **R$ 630,00**
- **Observação:** Dois ORCs. O mais antigo (ORC-0000089, criado 08/06) tem valor menor, possivelmente para um item diferente do mesmo cliente.
- **Ação:** Confirmar quais itens foram entregues e cobrar.

### 🔴 Mariana Ferreira Paschoal
- **Evento Calendar:** 22/06/2026
- **Serviço:** Sofá 2 lugares — R$280,00
- **No sistema:** ORC-0000065 (R$239,99 — CREDITO_3X) + ORC-0000147 (R$280,00) = **R$ 519,99**
- **Contato:** +55 65 99232-3032 | Cond. Florais do Parque, qd 04 lt 19
- **Ação:** Verificar qual ORC é o serviço atual e cobrar.

### 🔴 Mônica Rodrigues de Sousa
- **Evento Calendar:** 11/06/2026 — "NAO FOI PAGO" (nota explícita no evento)
- **Serviço:** Sofá 3 módulos retrátil — R$300,00
- **No sistema:** ORC-0000102 (R$320) + ORC-0000146 (R$300) = **R$ 620,00**
- **Contato:** +55 65 99982-9423 | Ed. Bravie, Av. Cássio Caberlin, 138, apt 1504
- **Ação:** Cobrança — confirmada pelo usuário na nota do evento.

### 🔴 Ellen Guedes Tambelini
- **Evento Calendar:** 02/07/2026 — 3 tapetes grandes (37,92m²)
- **Valor Calendar:** R$1.420,00 (pix) / R$1.280,00 (dinheiro)
- **No sistema:** ORC-0000156 = **R$ 1.427,20** (CREDITO_6X)
- **Contato:** +55 65 98112-0456 | Alameda Jatobá, qd 17, casa 17
- **Observação:** Valor sistema (R$1.427,20) confere com Calendar (R$1.420 + pequena diferença de cálculo). Escolheu 6x no cartão — verificar se houve cobrança na InfinitePay.
- **Ação:** Verificar lançamento no cartão ou enviar link de cobrança.

### 🔴 Sandra Silvestre da Silva Torres (Dra. Sandra)
- **Evento Calendar:** 23/06/2026 — 5 tapetes pequenos — R$140,00
- **Contatos:** Zelma (secretária): 65 99230-8137 | Carol Torres: 65 99251-8721 | Dra. Sandra: 65 99224-7828
- **Endereço:** Rua E, qd 15, casa 11, Jd. Village Flamboyant/Barra do Pari
- **No sistema:** ORC-0000097 (R$140) + ORC-0000150 (R$140) = **R$ 280,00**
- **Ação:** Cobrar — dois ORCs para o mesmo cliente (possível duplicata de cadastro ou dois serviços distintos).

### 🔴 Forma Clean / Maika (Renan)
- **Evento Calendar:** 11/06/2026 — acerto pós 15/05/2026
- **Saldo calculado no Calendar:** R$645,70 (dh) / R$710,27 (pix)
- **No sistema:** ORC-0000034 = **R$ 120,00**
- **Observação:** Divergência grande entre Calendar (R$645) e sistema (R$120). O sistema registrou apenas um ORC de R$120, mas o Calendar detalha múltiplos lotes. Boa parte dos tapetes do Maika pode estar sendo registrada apenas no Calendar, sem ORC.
- **Ação:** Usar o valor do Calendar (R$645,70) para o acerto, não o sistema.

### 🔴 Alessandra Paz (Várzea Grande)
- **Evento Calendar:** 23/06/2026 — tapete 5m² — R$175,00
- **No sistema:** ORC-0000151 = **R$ 175,00**
- **Contato:** Cond. Terra Nova, casa 407, Vg. Grande — CEP 78110-903

### 🔴 Ana Paula Martins Pinheiro Santos (Primor das Torres)
- **Evento Calendar:** 29/06/2026 — 10 cadeiras — R$250,00
- **No sistema:** ORC-0000032 = **R$ 175,00**
- **Observação:** Valor diverge (Calendar R$250 vs. sistema R$175). Verificar se o valor foi alterado.
- **Contato:** +55 65 99683-2195 | Cond. Primor das Torres, Qd 2 Lt 24

### 🔴 Mara Carvalho
- **Evento Calendar:** 24/06/2026 — remoção de mancha em sofá de linho — R$50,00
- **No sistema:** ORC-0000142 = **R$ 50,00**
- **Contato:** +55 69 98486-7230 | Rua Ministro João Alberto, 49, Araés

### 🔴 Joselito Pinheiro de Abreu
- **Evento Calendar:** 26/06/2026 — tapete 2,8m² — R$100,00
- **No sistema:** ORC-0000095 = **R$ 42,00**
- **Observação:** Valor diverge (Calendar R$100 vs. sistema R$42). O sistema pode ter apenas um item; o Calendar pode incluir outro.
- **Contato:** +55 66 99651-2778 | Torre 4, Apt 706

### 🔴 Juliana Assunção Oliveira (portal do parque)
- **Evento Calendar:** 23/06/2026 — tapete redondo — R$100,00
- **No sistema:** ORC-0000149 = **R$ 100,00**
- **Contato:** 065 99661-0198 | Ed. Portal do Parque, Apt 1004

### 🔴 Leonardo (Cond. Minas Cuiabá)
- **Evento Calendar:** 24/06/2026 — tapete 2m² — R$90,00
- **No sistema:** ORC-0000099 (R$58,80) + ORC-0000152 (R$90,00) = **R$ 148,80**
- **Contato:** +55 65 99243-1689 | Bl 31, Apt 3113, Cond. Villa das Minas
- **Atenção:** Este é um **cliente pessoa física** chamado Leonardo, diferente do parceiro "Leonardo - Dry Clean USA".

---

## 2. Apenas no Calendar (sem ORC no sistema)

Eventos vermelhos no período sem orçamento correspondente encontrado no banco.

| Data | Cliente | Valor (Calendar) | Observação |
|---|---|---|---|
| 29/06/2026 | Bruno Inova | R$ 150,00 | Sofá pequeno · dono da loja · sem ORC cadastrado |
| 09/07/2026 | Thiago R Oliveira | R$ 630,00 | 2 tapetes (15m² + 2,94m²) · Vaga 99, T1 apt 102 · sem ORC |
| 13/07/2026 | Silvia Luz Serio | R$ 869,25 | Sofá 3L + 2 tapetes · "Cartão 2x" escolhido · Ed. Modigliani, apt 702 |
| 14/07/2026 | Andressa Fantim Giroldo | R$ 55,00 | Tapete 1,5m² · Bl A10, Apt 102 |
| 14/07/2026 | Antônio / Magda (Belvedere I) | R$ 220,00 | Tapete 6,2m² · Rua do Beija Flor, qd 26, casa 27 |
| 17/07/2026 | Mônica Zuffo | R$ 730,00 | 2 tapetes (8,8m² + 12m²) · Apto 21, 2º andar |

**Soma:** R$ 2.654,25 sem ORC no sistema.  
**Ação:** Lançar esses serviços no sistema imediatamente para não perder o rastro.

---

## 3. Apenas no Sistema — Sem Evento Vermelho no Calendar

Os clientes abaixo têm orçamentos em aberto (período 01/06–19/07/2026) mas **nenhuma marcação vermelha** no Calendar. Podem estar em processo, ainda aguardando pagamento no prazo, ou simplesmente não foram marcados.

Ordenados por valor:

| Cliente | Total no Sistema | ORCs | Método |
|---|---|---|---|
| **Regus** | **R$ 7.053,93** | ORC-0000103 | CREDITO_7X |
| **Hotel Slaviero Slim** | **R$ 2.970,00** | ORC-0000155 | CREDITO_6X |
| **Fource Gestão de Recursos** | **R$ 2.294,28** | ORC-0000104 | PIX |
| **Fernando Ed Superia** | **R$ 1.937,00** | ORC-0000106 | PIX |
| **Carpete Advanced (RSA Capital)** | **R$ 1.420,00** | ORC-0000110 | PIX |
| **Ciça Zanca** | **R$ 1.360,70** | ORC-0000088 | PIX |
| **Taynara** | **R$ 1.335,40** | ORC-0000154 | CREDITO_6X |
| **Sadora Xavier** | **R$ 1.257,40** | ORC-0000094 | PIX |
| Mercia Cristina Antunes | R$ 897,75 | 6 ORCs (0015–0076) | PIX |
| Daniella Amorim | R$ 852,60 | ORC-0000082 | PIX |
| Lindamar | R$ 710,00 | ORC-0000105 | PIX |
| Silvia Cassia Nunes Rosa | R$ 586,00 | ORC-0000117 | PIX |
| Sônia Maria | R$ 570,00 | ORC-0000115 | PIX |
| Célia Cristina Maggi Scheffer | R$ 529,99 | ORC-0000062 | CREDITO_4X |
| Mariana Ferreira Paschoal | R$ 519,99 | ORC-0000065+0147 | PIX/CREDITO |
| Rosani Maria Epping | R$ 525,00 | ORC-0000107 | PIX |
| Vanessa Tonhá | R$ 473,68 | ORC-0000098 | PIX |
| Ronimar Cruz | R$ 456,75 | 3 ORCs (0037–0039) | PIX |
| Eduardo Ficagna | R$ 449,99 | ORC-0000078+0083 | CREDITO |
| Pietra | R$ 350,00 | ORC-0000084 | DINHEIRO |
| Bianca Azoia Bezerra | R$ 332,50 | ORC-0000111 | PIX |
| Wandrecha Machado | R$ 315,00 | ORC-0000051 | PIX |
| Paulinha Freiberger | R$ 280,00 | ORC-0000093 | CREDITO_1X |
| Dayane Araújo | R$ 262,50 | ORC-0000109 | PIX |
| Ilana Santiago Arquitetura | R$ 250,00 | ORC-0000114 | PIX |
| Maristela Balles | R$ 242,00 | ORC-0000108 | PIX |
| Beni Melatte | R$ 220,00 | ORC-0000112 | PIX |
| Ana Paula Bonadio | R$ 210,00 | ORC-0000080+0145 | PIX/CREDITO |
| Michelle Ficagna Silva | R$ 200,00 | ORC-0000079 | PIX |
| Felipe (Anjos Colchões) | R$ 200,00 | ORC-0000113 | PIX |
| Sandra Silva | R$ 198,00 | ORC-0000096 | PIX |
| Marluce Barros | R$ 175,00 | ORC-0000090 | PIX |
| Dayanne Martins | R$ 175,00 | ORC-0000116 | PIX |
| Aline Bernardes | R$ 160,00 | ORC-0000081+0100 | PIX |
| Isa Toledo | R$ 157,50 | ORC-0000011+0012 | PIX |
| Leonardo (Cond. Minas) | R$ 148,80 | ORC-0000099+0152 | PIX |
| Franciely | R$ 144,20 | ORC-0000035+0036 | PIX |
| Ana Livia | R$ 110,25 | ORC-0000045 | PIX |
| Juliana Machado | R$ 105,00 | ORC-0000049+0077 | PIX |
| Parceiro João / Felipe | R$ 60,00 | ORC-0000092 | PIX |
| Joselito Pinheiro de Abreu | R$ 42,00 | ORC-0000095 | PIX |
| Bia (Beatriz Santana - LB Modas) | R$ 42,00 | ORC-0000013 | PIX |
| Luis Eduardo Hugueney Queiroz | R$ 36,00 | ORC-0000071 | PIX |
| Daiana S. M. Olivatto | R$ 4,00 | ORC-0000141+0143 | PIX |
| Daiana | R$ 1,00 | ORC-0000085 | PIX |

> ⚠️ **Regus (R$7.053,93) e Hotel Slaviero Slim (R$2.970) e Fource Gestão (R$2.294) são os maiores valores sem nenhuma sinalização no Calendar.** Verificar se estão em prazo normal de pagamento ou já vencidos.

---

## 4. Parceiro Leonardo — Dry Clean USA

Situação especial: 57 orçamentos em aberto no sistema, todos com `payment_status=PENDENTE`, criados em dois lotes (02/06/2026 e 24/06/2026).

| Lote | Data | Qtd ORCs | Total |
|---|---|---|---|
| Lote 1 | 02/06/2026 | 32 ORCs (ORC-0000010–0086) | R$ 2.043,51 |
| Lote 2 | 24/06/2026 | 23 ORCs (ORC-0000118–0140) | R$ 2.008,61 |
| **Total** | | **55 ORCs** | **R$ 4.052,12** |

Estes ORCs representam tapetes individuais lavados para o parceiro. O acerto é feito em bloco periodicamente (como os parceiros Maika e Higia). Não há evento vermelho para Leonardo Dry Clean no período — pode estar em processo de acerto normal.

---

## 5. Totais Consolidados

| Grupo | Valor |
|---|---|
| Dupla confirmação (vermelho + ORC) — clientes | R$ 6.030,63 |
| Dupla confirmação (vermelho + ORC) — parceiros (Higia + Maika) | R$ 1.080,64 |
| Só no Calendar, sem ORC (6 clientes) | R$ 2.654,25 |
| Só no sistema, sem vermelho no Calendar | R$ 32.223,43 |
| **TOTAL GERAL EM ABERTO (sistema, período)** | **R$ 42.203,94** |

---

## 6. Ações Prioritárias

### Urgente — Esta Semana

1. **Regus** — R$7.053,93 (CREDITO_7X) — maior devedor, sem sinalização no Calendar. Verificar prazo da fatura.
2. **Hotel Slaviero Slim** — R$2.970,00 — prazo vencido? Verificar.
3. **Higia/Vinícius** — R$960,64 no sistema / R$2.181,80 no Calendar — "NAO FOI PAGO". Combinar acerto.
4. **Ellen Guedes** — R$1.427,20 — 17 dias. Verificar se cartão (CREDITO_6X) foi cobrado.
5. **Mônica Rodrigues de Sousa** — R$620 — "NAO FOI PAGO" confirmado.

### Esta Quinzena

6. **Edifício Felicitá** — R$1.560 (dois ORCs + retoque pendente).
7. **Fource Gestão de Recursos** — R$2.294,28 — sem sinalização no Calendar.
8. **Fernando Ed Superia** — R$1.937,00 — sem sinalização.
9. **Taynara** — R$1.335,40 — verificar prazo do cartão.
10. **Cadastrar no sistema os 6 sem ORC** (Bruno, Thiago, Silvia Serio, Andressa, Antônio, Mônica Zuffo) — total R$2.654 não rastreado.

### Conciliar Divergências

- **Higia/Vinícius:** sistema diz R$960, Calendar diz R$2.181 → verificar ORCs faltantes.
- **Forma Clean/Maika:** sistema diz R$120, Calendar diz R$645 → mesmo problema.
- **Edifício Felicitá:** dois ORCs com mesmo valor (R$780 cada) → verificar se é duplicata.

---

## 7. Correções a Fazer no Script `fetch_calendar_report.py`

Para a próxima execução, substituir:

```python
# ANTES (errado):
paid_cursor = db.budget_items.find({"payment_status": "PAGO"}, ...)
unpaid_cursor = db.budget_items.find({"status": {"$in": terminal_statuses}, ...})

# DEPOIS (correto):
# Buscar em budgets (não budget_items — coleção vazia em produção)
paid_cursor = db.budgets.find({"payment_received": "True"}, {"_id": 0, "id": 1})
unpaid_cursor = db.budgets.find(
    {
        "payment_received": {"$ne": "True"},
        "payment_status": {"$ne": "PAGO"},
        "created_at": {"$gte": date_from, "$lte": date_to}
    },
    {"_id": 0, "id": 1, "client_name": 1, "total_value": 1,
     "payment_status": 1, "payment_received": 1, "payment_method": 1, "created_at": 1}
)
```

---

*Relatório gerado pelo Claude em 19/07/2026 com dados reais do MongoDB de produção (Oracle VM) e Google Calendar.*
