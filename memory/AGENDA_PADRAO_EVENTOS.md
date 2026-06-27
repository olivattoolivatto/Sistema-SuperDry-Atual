# Padrão de Eventos do Google Agenda — SuperDry

Documento de referência para interpretação dos eventos da Google Agenda do dono,
usada como sistema primário de controle operacional. Base para conciliação periódica
com o sistema SuperDry.

---

## 1. Legenda de Emojis

### Tipos de item/serviço
| Emoji | Significado |
|-------|-------------|
| 🗞️ | Tapete |
| 📜 | Persiana ou Cortina de tecido |
| 🪟 | Persiana (distinção mais recente de 📜) |
| 🪜 | Acompanha 📜 — indica cortina de pé direito alto/duplo que exige escada especial → serviço só pode ir de **carro** (não moto) |
| 🧹 ou 📰 | Carpete (sem padrão fixo, podem aparecer juntos ou separados) |
| 🛏️ | Itens de quarto: cabeceiras, colchões, box |
| 🛋️ | Sofás em geral |
| 🪑 | Cadeiras (jantar ou escritório) |
| 💺 | Poltronas (todos os tipos) |
| 🛒 | Carrinho de bebê ou acessório infantil |
| 🧺 | Edredons, roupas de cama ou similares (terceirizados para lavanderia parceira) |
| 🚗 ou 🚘 | Serviços automotivos (limpeza de interiores, carpetes veiculares, bancos) |

### Tipos de serviço/ação
| Emoji | Significado |
|-------|-------------|
| 💧 | Limpeza / Lavagem |
| 💦 | Impermeabilização *(obs: quando acompanhado de 🐈‍⬛ indica urina de animal)* |
| 💦🐈‍⬛ | Tratamento de urina de gato/animal doméstico |
| 📐 | Ir fazer orçamento |
| 💳 | Levar máquina de cartão / receber pessoalmente via cartão |
| 🏷️ | *Legado/desuso* — cliente não atendido pelo celular da empresa, sem comissão para vendedor |

### Tipo de veículo / logística
| Emoji | Significado |
|-------|-------------|
| 🏍️ | Técnico vai de moto (economia de combustível, serviços menores/locais) |
| 🪜 | Exige carro (escada grande para pé direito duplo) |
| 🚗 / 🚘 | Serviço automotivo (não indica veículo do técnico) |

---

## 2. Formato do Título

```
[emojis de veículo] [emojis de item] [ação] [Nome do Cliente]
```

**Ações comuns no título:**
- `Retirar` / `Retirada` — ir buscar o item na casa do cliente
- `Entregar` / `Entrega` — levar o item de volta ao cliente após lavagem
- `Retirar e Entregar` — buscar e entregar no mesmo evento (ex: tapetes que são lavados no local)
- Sem ação explícita — execução no local (ex: `🛋💺 Edifício Felicitá`)

**Exemplos reais:**
- `🏍️🗞 entregar Marluce Barros` → entregar tapete, técnico de moto
- `📜 Retirada Bianca Azoia Bezerra` → retirar cortina
- `🪜📜 entregar Daniella Amorim / CDA Atacado` → entregar cortina, exige escada/carro
- `🛋💺 Edifício Felicitá` → limpeza de sofá e poltrona no local
- `💦🛋️Pietra` → impermeabilização de sofá
- `🗞️ retirar e 🛏️🪑Silvia Cassia` → retirar tapete E cabeceira/cadeiras

---

## 3. Formato do Corpo (Descrição do Evento)

```
[Endereço complementar (quadra, lote, apto, bloco, etc.)]

*🔶 Orçamento - [Categoria] 🔶*

[💧/💦] [Nome do serviço] - R$[valor]
...

📍 Total dos serviços: R$[valor] [condições de parcelamento]
*📌 À vista: R$[valor_desconto]*

[Registro de pagamento recebido, se houver]
[Anotações especiais: instruções, medidas, informações do cliente]
```

### Registro de pagamento
Aparece no final do corpo. Formatos observados:
- `PixNuSuperDry [valor] [data]` → PIX recebido no Nubank da empresa
- `PixInter [valor] [data]` → PIX recebido no Inter
- `Cartão [parcelas]x [valor] [data]` → pagamento no cartão
- `Dinheiro [valor] [data]` → pagamento em espécie
- Ausência de registro → pagamento ainda não recebido (PENDENTE)

### Anotações especiais
- Medidas dos itens (ex: quantidades de ganchos de cortina, dimensões de tapete)
- Preços especiais para clientes recorrentes
- Instruções de procedimento específicas

---

## 4. Regras de negócio implícitas

- **Impermeabilização (💦):** pode ser dividida em dois eventos — preparação (neutralizante) e execução (aplicação do impermeabilizante)
- **Retirada:** pagamento geralmente só após entrega, não na retirada
- **Tapetes:** retirados, lavados na sede, depois entregues
- **Estofados / limpeza no local:** executado na casa do cliente
- **Parceiro (🧺):** item terceirizado para outra lavanderia; não é serviço executado pela SuperDry
- **🪜 (escada):** sempre de carro, nunca de moto

---

## 4b. CNPJs da empresa

| Nome | CNPJ | Uso |
|------|------|-----|
| **SuperDry** | 25.995.295/0001-04 | CNPJ principal — maquininhas, contas, cobrança |
| **SuperDAY** | 30.369.419/0001-86 | CNPJ secundário — em desuso para pagamentos novos |

---

## 4c. Formas de pagamento (registro na agenda)

| Código na agenda | Significado |
|-----------------|-------------|
| `PixNuSuperDry` | PIX recebido no Nubank — CNPJ SuperDry |
| `PixInterSuperDAY` | PIX no Inter — CNPJ SuperDAY *(em desuso)* |
| `BolNuSD` | Boleto Nubank — CNPJ SuperDry |
| `InfCrd[N]x` | InfinitePay crédito em N parcelas (ex: `InfCrd2x` = 2×) |
| `InfDeb` | InfinitePay débito |
| `Link` (ou variação) | Link de pagamento / crédito InfinitePay |
| `Dinheiro` | Pagamento em espécie |

Formato geral: `[código] [valor] [data]` — ex: `PixNuSuperDry 340,00 10/6/26`

---

## 4d. Cores dos eventos no Google Calendar

| Cor | Nome Google | Significado operacional |
|-----|-------------|------------------------|
| Azul pavão (padrão) | Peacock | Execução normal — itens confirmados e agendados |
| Amarelo | Banana | Item não confirmado / aguardando confirmação do cliente |
| Vermelho | Tomato | Pagamento não localizado / cobrar / investigar |
| Verde claro | Sage | Trabalho na empresa (ex: lavagem de tapetes ou persianas na sede) |
| Azul escuro | Blueberry | Item de parceiro — trazido e retirado pelo próprio parceiro *(exceto Leonardo: alto fluxo, registrado só em planilha mensal com totalização de medidas)* |
| Roxo | Grape | Itens com múltiplos deslocamentos (retiradas, entregas, retoques, etc.) |
| Cinza | Graphite | Feriado municipal marcado manualmente para evitar agendamentos |

**Mapeamento para o sistema:**
- Amarelo → `budget.status = PENDENTE` / item não confirmado
- Vermelho → alerta financeiro, `payment_status = PENDENTE` com flag de cobrança urgente
- Verde claro → `execution_mode = CLIENTE_TROUXE` (trabalho na sede)
- Azul escuro → cliente parceiro, sem comissão de vendedor
- Roxo → item com `execution_mode = RETIRAR_E_LEVAR` (múltiplas etapas)
- Cinza → ignorar na conciliação (não é atendimento)

---

## 5. Mapeamento para o sistema SuperDry

| Dado da Agenda | Campo no sistema |
|----------------|-----------------|
| Nome no título | `client.name` |
| Endereço do evento (Google) + complemento no corpo | `budget.pickup_address` / `budget.delivery_address` |
| Emoji de item (🗞️ 🛋️ etc.) | `budget_item.service_category` |
| Emoji de ação (retirar/entregar) | `budget_item.execution_mode` |
| Valor no orçamento por linha | `budget_item.price` |
| Total à vista | `budget.total_value` |
| Registro de pagamento no corpo | `budget_item.payment_status` + `budget_item.paid_value` |
| Data/hora do evento | `budget_item.scheduled_date` |
| 🏍️ no título | `route.vehicle_type = MOTO` |
| 🪜 no título | `route.vehicle_type = CARRO` |

---

## 6. Pendências de melhoria no módulo Agenda

*(Anotado para implementação futura)*

- **Layout da tela Agenda** — exibição atual não agrada ao dono; precisa redesenho
- ~~**Cores dos eventos** — o sistema não replica as cores definidas no Google Calendar original.~~
  **Resolvido (verificado em 2026-06-24):** já estava implementado tanto no backend
  (`GET /api/calendar/events` devolve `color_id` = `colorId` do Google, em
  `backend/server.py`) quanto no frontend (`getGoogleCalendarColor()` em
  `frontend/src/pages/Agenda.js`, mapeando os 11 IDs oficiais do Google para as cores
  reais e aplicando no estilo do evento). Confirmado em produção (VM): a tela `/agenda`
  já exibe a legenda "Cores do Google Calendar" e o aviso "as cores dos eventos
  correspondem às configurações definidas no seu Google Calendar". Esta pendência
  estava desatualizada no documento — nenhuma mudança de código foi necessária.

---

## 7. Processo de conciliação periódica

Executado sob demanda via Cowork (Claude com acesso ao sistema):

1. Chamar `GET /api/calendar/events` com token admin
2. Para cada evento: extrair cliente, itens, valores, pagamento usando este guia
3. Buscar cliente correspondente no MongoDB (`clients` collection) por nome aproximado
4. Verificar se existe orçamento correspondente (`budgets` collection) com itens e valores similares
5. Reportar gaps: eventos na agenda sem orçamento no sistema, pagamentos anotados na agenda sem registro financeiro
6. Aguardar confirmação do dono para criar/atualizar registros
