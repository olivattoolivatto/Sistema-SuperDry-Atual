# Integração Agenda (cores) ↔ Sistema

Documento de análise + design para resolver o maior bloqueio da implantação: o sistema
foi projetado para o fluxo **completo e futuro** (Cliente → Orçamento → Item → Rota →
Agenda), mas o uso real do dono hoje é **Agenda-primeiro** — cola dados soltos do
WhatsApp direto num evento do Google Calendar e manda print pro técnico. Cadastro
estruturado e roteirização são exceção, não regra, no dia a dia atual.

> Leia junto: [FLUXO_TRABALHO_E_AUTOMACAO.md](FLUXO_TRABALHO_E_AUTOMACAO.md) (visão geral),
> [PARCEIROS_TAPETES.md](PARCEIROS_TAPETES.md) (tapetes de parceiro).

---

## 1. Diagnóstico técnico (código, não suposição)

**Cores do Google Calendar já mapeadas no frontend** (`Agenda.js:1286-1352`), batendo
exatamente com a convenção do dono:

| colorId | Nome Google | Uso do dono |
|---|---|---|
| `9` | Azul Cobalto | Estofado, 1 deslocamento |
| `3` | Roxo Uva | Múltiplos deslocamentos (tapete/cortina/imper. em 2 etapas) |
| `5` | Amarelo Banana | Reservado / não confirmado |
| `11` | Vermelho Tomate | Não pago |

**Mas o backend nunca usa essa tabela.** Toda criação de evento grava `colorId` fixo
em `'5'` (`server.py:1770` e `2162`) — automática ou manual, sempre amarelo. Não existe
nenhuma lógica que decida a cor pelo status/pagamento do item.

**Leitura é só de exibição, nunca persistida.** `GET /calendar/events` e
`GET /calendar/events/detail/{id}` (`server.py:2203-2260`, `2285-2324`) leem ao vivo da
API do Google e devolvem `color_id` pro frontend pintar a tela — mas isso nunca é
gravado no MongoDB. Se o dono muda a cor manualmente no Google, o sistema nunca fica
sabendo. **Não existe webhook nem polling do Google Calendar** — confirmado por busca
no código inteiro; as únicas menções a "webhook" são do InfinitePay (pagamento).

**Vínculo evento↔item passa por Rota.** `CalendarEvent` guarda `route_id` + `stop_id`
(`server.py:894-906`); é o `RouteStop` dentro da rota que carrega o `budget_item_id`
(`server.py:500-502`). Ou seja: hoje, pra um evento "saber" a qual item ele pertence,
formalmente precisaria existir uma Rota — o que reforça a rigidez do fluxo completo.

**Mas já existe uma porta dos fundos que bate com o hábito real:**
`POST /calendar/events/direct` (`server.py:2133-2191`) cria evento **sem** rota nem
item (`route_id=None, stop_id=None`) — é essencialmente "colar texto solto e salvar",
só que hoje ainda sai pintado de amarelo fixo e sem nenhuma ponte de volta pro sistema.

**Cadastro estruturado tem fricção real.** Cliente exige nome + telefone (≥10 dígitos)
+ endereço completo (`Clients.js:586-592`, `server.py:270-300`); `Address` no Pydantic
exige `neighborhood/city/state` como string obrigatória — se o endereço for digitado à
mão (sem o autocomplete do Google preencher), pode dar erro 422 sem aviso claro.
Orçamento exige cliente + ao menos 1 item com serviço do catálogo + preço
(`BudgetEditor.js:965-972`, `server.py:1005-1011`). Isso é razoável para o fluxo
completo, mas é exatamente o "burocracia chata" quando tudo que se quer é anotar
"João, 99999-9999, Rua X, sofá 3 lugares R$150" e seguir em frente.

---

## 2. Descoberta importante: a lista de recolhimento de parceiro **já é suportada**

O parser `_parse_measures_text` (`server.py:3587-3813`), usado por
`POST /automation/preview-measures` / `execute-measures`, já interpreta linha a linha
exatamente o formato que você colou (`Verde 576 60x90`, `Nádia 2x3`, com ou sem emoji
de cor). Testei os dois padrões:

- `Verde 576 60x90` → reconhece etiqueta cor+número (`_classify_partner`,
  `server.py:3631-3679`) + dimensão → cria `BudgetItem` de parceiro com status
  `AGUARDANDO_BUSCAR`, já com dedupe contra o banco (60 dias) e dentro da própria
  colagem (`server.py:4208-4309`).
- `Nádia 2x3` → sem etiqueta de cor → vira item de cliente comum com status
  `CLIENTE_TROUXE`.

**Ou seja: você já pode colar a mensagem do grupo de recolhimento direto na tela
Automações → Medidas, hoje, sem nenhum código novo, e ela gera os itens sozinha.**
O gargalo não é falta de feature — é que esse caminho não virou hábito ainda porque
ninguém te mostrou que ele já resolve exatamente essa lista.

**Verificação rodada de fato (não só leitura de código) contra as duas mensagens reais
enviadas (a sua, formato "Cor NNN medida", e a do Marcos Técnico, formato emoji):**

| Mensagem | Linhas reconhecidas | Perdidas | Erros de atribuição parceiro↔cliente |
|---|---|---|---|
| Sua (24 tapetes Leonardo + 4 clientes comuns) | 28/29 | 1 | 0 |
| Marcos Técnico (formato emoji) | 27/27 | 0 | **8** |

- **1 linha perdida na sua mensagem:** `Amarelo dry2 2,2x` — medida incompleta (falta o
  segundo número depois do "x"), a linha inteira é silenciosamente descartada. Isso é
  fidelidade a como você realmente digita quando está com pressa/errou — o parser não
  avisa que perdeu a linha, só ignora.
- **8 erros na mensagem do Marcos Técnico:** ele identifica os tapetes do Leonardo com
  emoji de cor (💛059, 🩷567, 🩶870, 🩶871, 🩶892, 🧡608, 🩶893, 🧡966) em vez da palavra
  escrita (`Verde`, `Cinza` etc). O regex de etiqueta só reconhece as palavras
  (`server.py:3646-3649`), não os emojis — então cada um desses 8 vira um "cliente novo"
  com nome literal `💛059` etc, em vez de ser atribuído ao parceiro Leonardo com a
  etiqueta certa. Isso quebraria o fechamento de cobrança do parceiro se fosse rodado
  sem ajuste: seria preciso mapear os emojis (💛=amarelo, 🩷=rosa, 🩶=cinza, 🧡=laranja)
  no `_classify_partner` antes de confiar nessa mensagem específica.
- Fora isso, nomes repetidos sem etiqueta (ex: "Hellen" 4x com medidas diferentes,
  "Higia" 3x) **não se atropelam** — a dedup só age sobre itens com etiqueta cor+número
  (`server.py:4209-4226`), então tapetes de cliente comum do mesmo tamanho continuam
  todos entrando, corretamente tratados como peças distintas.

**Conclusão honesta:** funcional e correto pro seu próprio jeito de escrever (97%,
só a linha incompleta perde). Para o formato do Marcos Técnico (emoji), hoje **não**
está pronto — precisa de um ajuste pequeno e localizado (mapear emoji→cor em
`_classify_partner`) antes de confiar cegamente nessa fonte.

**✅ Implementado (13/07/2026):** `_classify_partner` (`server.py`) agora traduz os
emojis de cor (💛🟡→amarelo, 🩷💗💖→rosa, 🩶⚪🤍→cinza, 🧡🟠→laranja, 💙🔵→azul, 💜🟣→roxo,
💚🟢→verde) pro mesmo fluxo do texto — os 8 tapetes do Leonardo na mensagem do Marcos
Técnico agora são atribuídos corretamente (antes viravam "clientes" falsos). Também
passou a reconhecer `dry`/`dry2`/`dry3` como identificação Leonardo sem etiqueta
numérica, igual "sem nome" — mas isso **não resgata** a linha `Amarelo dry2 2,2x` do
seu exemplo real: essa continua perdida porque a *medida* está incompleta (falta o
segundo número depois do "x"), não porque a tag não era reconhecida. Testado com
`Amarelo dry2 1,2x1,5` (medida completa) e funciona. Revalidado com script isolado
reproduzindo a função real linha a linha — 0 erros de atribuição nas duas mensagens.

---

## 2.1. Por que amarelo é o padrão hoje (confirmado pelo dono)

O `colorId` fixo em `'5'` não é falha de implementação — é intencional. O desenho
original do sistema pressupõe que todo agendamento nasce **provisório**: vai pra
Agenda primeiro (amarelo), e só é "confirmado" depois. Não existe, na arquitetura
atual, a hipótese de mandar direto pra Agenda algo que já nasce como serviço
definido/confirmado (que seria o caso comum do dono: azul/roxo direto, sem passar por
amarelo). Isso é raiz do mesmo problema da seção 3: o sistema modela a burocracia
completa como caminho único, não como uma opção entre outras.

## 2.2. A obrigatoriedade de Rota — confirmada, e como evitá-la

Verificado em código: hoje, **para um item existir na Agenda pelo caminho oficial**,
uma `Route` precisa existir antes. `POST /calendar/events` (`server.py:1715-1726`)
recebe `route_id`, busca a rota no banco e retorna 404 se não existir — os eventos são
sempre criados a partir de `route.stops`. E `POST /routes` (`server.py:5003-5019`)
exige `vehicle_type` + `planned_date` + `planned_start_time`, mesmo para um único
compromisso avulso (ex: um estofado azul, 1 endereço, sem necessidade real de
otimização). Isso confirma a queixa: hoje, formalmente, **não dá pra colocar um item
no sistema vinculado à Agenda sem primeiro montar uma Rota**, mesmo quando rota não
faz sentido nenhum pro caso (a maioria dos seus atendimentos, pelo seu relato).

**Isso é evitável, e o caminho já existe parcialmente:** `POST /calendar/events/direct`
(seção 1) já cria evento sem rota — só que hoje ele não vincula a nenhum item, perdendo
o rastro financeiro. A correção é dar a esse endpoint (ou a um novo endpoint irmão) a
capacidade de vincular o evento **direto a um ou mais `budget_item_id`**, sem criar
Rota nenhuma — bastaria adicionar um campo opcional `budget_item_ids` no modelo
`CalendarEvent` (hoje só tem `route_id`/`stop_id`, `server.py:894-906`). Rota continua
existindo, mas vira **opcional**, usada só quando você realmente quer otimizar
deslocamento de múltiplas paradas (tapetes/imper., como você já faz eventualmente)
— exatamente a distinção que a cor azul/roxo já representa na sua cabeça: azul = 1
parada, não precisa de rota; roxo = múltiplas paradas, aí sim vale a pena rotear.

**✅ Implementado (13/07/2026):** `CalendarEvent` ganhou `budget_item_ids` e `color_id`
persistidos no Mongo (antes a cor só ia pro Google, nunca ficava salva localmente —
importante pra Fase 2 comparar depois). `DirectEventCreate` aceita `budget_item_ids`
(opcional, validado contra `db.budgets` — 404 se algum ID não existir, pra pegar erro
de digitação na hora) e `color_id` (opcional, valida contra os 11 ids do Google,
default `'5'` mantém o comportamento antigo se omitido). `GET /calendar/events` e
`GET /calendar/events/detail/{id}` agora devolvem `budget_item_ids` junto (busca em
lote na coleção local, sem N+1 query). **Frontend ainda não foi tocado** — o botão de
criação rápida de evento na Agenda continua sem campo pra escolher item/cor; isso é o
próximo passo de UI se você quiser usar isso na prática (ver seção "Próximos passos").

## 3. O problema real: ordem invertida, não falta de feature

O sistema pressupõe **estrutura primeiro, depois registro** (Cliente → Orçamento →
Item → só então algo pode ir pra Agenda). Sua rotina de 10 anos é **registro primeiro,
estrutura se sobrar tempo** (WhatsApp → Agenda → print pro técnico; rota e cadastro
completo são exceção). Forçar a ordem do sistema é forçar uma rotina nova sobre um
cérebro que já tem uma rotina automática e eficiente — é fricção desnecessária, não
disciplina.

**Princípio de design proposto: a Agenda continua sendo o ponto de captura. O sistema
estrutura por trás, de forma assíncrona e opcional, nunca como bloqueio.**

---

## 4. Design proposto (fases independentes, você escolhe onde parar)

### Fase 0 — sem código, só uso (disponível hoje)
Adotar `Automações → Medidas` para colar a lista de recolhimento de parceiros direto
do grupo do WhatsApp. Resolve o "não tem jeito formal de entrar no sistema" sem
nenhuma mudança técnica.

### Fase 1 — cor certa desde a criação + evento direto como caminho padrão

**✅ Implementado (13/07/2026):**
- `CalendarEvent.budget_item_ids` + `color_id` persistidos no Mongo (seção 2.2).
- `POST /calendar/events/direct` valida `budget_item_ids` contra o banco (404 se
  ID errado) e aceita `color_id` explícito (default `'5'`, mantém compat).
- Vínculo reverso: `BudgetItem.agenda_event_ids` (campo que já existia no modelo,
  nunca era preenchido — `server.py:383`) agora recebe o `CAL-XXXXXXX` de cada
  evento criado com vínculo. É a base pra Fase 1 status→cor e pro polling da Fase 2.
- **Frontend (`Agenda.js`):** o modal "Criar Evento" ganhou seletor de 4 cores
  (cobalto/uva/banana/tomate) e um campo opcional "Vincular a um item" (ID do ITM,
  com botão "Verificar" que mostra cliente+serviço antes de salvar, via
  `itemsApi.get`). Continua sem exigir Rota.
- **Cor automática por status/pagamento (status→cor, mão única):**
  `_expected_color_id_for_item()` decide a cor certa (vermelho tomate se
  finalizado sem pagamento completo; senão azul cobalto ou roxo uva conforme a
  categoria do serviço — tapetes/cortinas/impermeabilização = roxo). Acionado em
  `POST /items/{id}/status`, `PUT /budget-items/{id}/status` (legado),
  fim de sessão de execução, e `POST /items/{id}/payment` — sempre via
  `_sync_linked_events_color()`, que só mexe em eventos já vinculados
  (`agenda_event_ids`) e nunca derruba o fluxo principal se o Google falhar.
  **Amarelo continua manual** — não há sinal confiável pra inferir "reservado/não
  confirmado" a partir do status do item.
- Ainda **não implementado**: a sugestão silenciosa de estruturação via
  `_smart_parse_budget` ao salvar um evento direto sem item vinculado — o campo
  "vincular a um item" hoje exige que o item já exista antes (criado via
  Automações ou Orçamento manual). Colar texto solto e o sistema estruturar
  sozinho por trás continua como próximo passo, não feito ainda.

### Fase 2 — sincronia mão-dupla cor↔status

**✅ Implementado (13/07/2026), com uma decisão tomada por mim (a confirmar com
você):** em vez de cron/intervalo fixo, o "polling" acontece **toda vez que
`GET /calendar/events` é chamado** — ou seja, toda vez que a Agenda é aberta ou
atualizada. Vantagem: zero infra nova, sem gasto de cota do Google fora do que já
era consumido. Desvantagem: se você não abrir a Agenda, não há verificação (não é
um vigia em segundo plano). Se isso não for suficiente, dá pra evoluir pra um
intervalo fixo depois.

- **Status → Cor:** feito (ver Fase 1 acima).
- **Cor → Status (detecção):** `GET /calendar/events` agora compara, pra cada
  evento vinculado a item, o `color_id` salvo no Mongo contra a cor ao vivo do
  Google — devolve `color_diverged: true` + `stored_color_id` quando diferem.
  **Não grava pagamento nem status sozinho** — exatamente a regra combinada,
  porque você mesmo relatou que a regra do vermelho falha às vezes.
- **Confirmação:** `POST /calendar/events/{google_event_id}/acknowledge-color`
  só atualiza a baseline local (pra parar de sinalizar) — pagamento continua
  sendo lançado por você no Financeiro, sempre.
- **Frontend:** bolinha âmbar no canto do evento na grade quando há divergência;
  ao abrir o evento (duplo clique), aparece um aviso com botão "Confirmar".

### Fase 3 — painel "resolver hoje" pra cobrir o que você esquece
Como o próprio vermelho falha às vezes, um painel simples (já previsto na visão
"assistente pessoal" do `FLUXO_TRABALHO_E_AUTOMACAO.md`) que cruza *itens
executados/entregues sem pagamento registrado E sem cor vermelha* — pega exatamente o
buraco que a memória sozinha não cobre.

---

## 5. Decisões pendentes do dono

- ~~Ok pra Fase 1 alterar `/calendar/events/direct`?~~ Feito — endpoint estendido,
  compatível com quem já chamava sem os campos novos.
- ~~Polling a cada quanto tempo?~~ Decidido por mim como "a cada abertura da Agenda"
  em vez de intervalo fixo — **valide se isso é suficiente pro seu uso real** ou se
  prefere um intervalo fixo em segundo plano mesmo sem abrir a tela.
- ~~Divergência cor↔pagamento: painel dedicado ou aviso na própria Agenda?~~ Fiz
  aviso na própria Agenda (bolinha + banner ao abrir o evento) por ser mais rápido
  de implementar e não exigir tela nova — **o painel "resolver hoje" (Fase 3)
  continua em aberto** se você quiser algo mais consolidado depois.
- Novo: a UI de "vincular a um item" no evento direto só aceita **um item por
  evento** por enquanto (o backend aceita vários). Suficiente pro seu caso mais
  comum (azul/1 item)? Tapetes/múltiplos itens no mesmo evento ainda precisam do
  fluxo de Rota, ou vale ampliar a UI pra aceitar mais de um ID?

## 6. Roadmap sequenciado

1. ~~Fase 0~~ — disponível, sem código (usar Automações/Medidas pra parceiros).
2. ~~Fase 1~~ — ✅ cor automática por status/pagamento + evento direto com cor e
   item vinculado, sem Rota. Falta só a sugestão silenciosa de estruturação
   automática (colar texto solto → sistema cria Cliente/Orçamento sozinho).
3. ~~Fase 2~~ — ✅ sincronia mão-dupla cor↔status (polling ao abrir a Agenda,
   sinalização sem gravar pagamento).
4. Fase 3 — painel "resolver hoje" (ainda não feito).
5. **Deploy:** essas mudanças estão só no código local — para ir pra VM Oracle,
   seguir o checklist de equalização em `memory/INFRAESTRUTURA.md` (build do
   frontend + restart do backend).

## 7. Teste de lógica (13/07/2026) — 18/18 passaram

Rodei o backend de verdade (importando `server.py` real, não uma reimplementação)
num MongoDB compatível (`mongomock`) num ambiente isolado, com o Google Calendar
simulado (nenhuma chamada tocou sua conta real) e autenticação sobreposta pra não
precisar de login. Exercitei via `TestClient` (HTTP de verdade contra a app real):

1. Criar evento vinculado a um item sem Rota, com cor explícita — item recebeu
   `agenda_event_ids`, evento nasceu com a cor pedida. ✅
2. Vincular item inexistente → rejeitado com 404 e mensagem clara. ✅
3. Status → `ENTREGUE` sem pagamento → cor virou vermelho tomate sozinha. ✅
4. Pagamento completo → cor voltou pra azul cobalto (categoria ESTOFADOS) sozinha. ✅
5. Cor mudada manualmente "no Google" (simulado) → sistema detectou a divergência
   na listagem (`color_diverged`), sem mexer em pagamento/status. ✅
6. Confirmar a divergência → baseline local atualizada, aviso some. ✅
7. Item de categoria TAPETES → cor calculada foi roxo uva (não azul), confirmando
   a distinção 1 deslocamento vs. múltiplos. ✅

**O que isso prova:** a lógica nova (decisão de cor, vínculo sem rota, detecção
de divergência, validação de item) está correta e funciona ponta a ponta dentro
do FastAPI real. **O que isso NÃO prova:** o comportamento real da API do Google
Calendar (autenticação OAuth, limites de cota, nuances de fuso horário) — isso só
um teste manual seu, com sua conta logada, cobre. Duas ressalvas técnicas do
ambiente de teste (não são bugs do seu sistema): o `mongomock` usado aqui não
suporta projeção posicional (`{"items.$": 1}`) nem `$push` posicional em array de
subdocumento — precisei de dois contornos só no arnês de teste; o MongoDB real
da VM não tem essa limitação, então o código roda como está, sem ajuste. Também
descobri no processo que o ambiente de sandbox que uso pra rodar comandos shell
ficou com uma cópia desatualizada do `server.py` por boa parte da sessão (sem
refletir os últimos trechos do arquivo) — o arquivo real, que você vê no seu
OneDrive, sempre esteve correto (as edições foram todas gravadas nele
diretamente); só minha verificação via shell precisou contornar isso reconstruindo
o arquivo a partir do que eu tinha lido. Vale um `python -m py_compile server.py`
seu, local, como último gate antes do deploy — é rápido e fecha essa lacuna.
