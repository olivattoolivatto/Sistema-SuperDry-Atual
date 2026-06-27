# Parceiros de Tapetes/Cortinas — Como funciona

> Lido por: qualquer assistente/sessão futura que precise entender o fluxo de tapetes
> de parceiros (Leonardo Dry Clean, Vinicius/Higia, Maika/FormaClean, Wesley
> Higienização, João/Felipe). Documentado em 23/06/2026 após análise de uma planilha
> de cobrança real + log de WhatsApp de medições de junho/2026.

## O que é um "parceiro" nesse contexto

Parceiro = empresa terceira (outra lavanderia/dry clean, ou intermediário) que entrega
tapetes/cortinas para a SuperDry lavar, e que **paga a SuperDry pelo serviço de
lavagem** — não é o dono final do tapete, é quem terceiriza a lavagem. A SuperDry não
lida com o cliente final do parceiro, só fatura o parceiro periodicamente (hoje:
mensal, controlado numa planilha Google Sheets fora do sistema).

## Identificação física dos itens — etiqueta cor + número

Cada parceiro usa seu motorista/técnico para entregar os tapetes já etiquetados com
**cor + número sequencial** (ex.: `Azul 581`, `Roxo 366`, `Cinza 373`). Essa etiqueta
NÃO é um campo estruturado no sistema hoje — aparece só como texto livre em
mensagens de WhatsApp e na agenda. Mesma cor é reaproveitada por vários parceiros
(ex.: "Cinza", "Roxo", "Azul" não são exclusivos de um parceiro só), então cor+número
sozinho não basta para saber de qual parceiro é — precisa de contexto (quem entregou,
em que rota, e o histórico de faturamento).

**Importante:** números de etiqueta SÃO reaproveitados ao longo do tempo (etiqueta
física é reciclada). Se o mesmo "Azul 601" aparecer de novo com dimensão diferente da
última vez cobrada, NÃO é duplicata — é uma etiqueta nova reaproveitando o número
antigo. A regra de decisão (confirmada pelo dono em 23/06/2026): código repetido +
dimensão igual à já cobrada = duplicata (eliminar); código repetido + dimensão
diferente = item novo.

## Como os itens chegam até nós (regras de identificação no log/WhatsApp)

Indícios de que um item do log é de parceiro (e não de cliente final):
1. Marcado **"sem nome"** ou **"sem número"/"sem etiqueta"** — quase sempre parceiro.
2. Menção explícita ao nome do parceiro ou apelido: **"Leonardo"**, **"Higia"**
   (= Vinicius), **"Forma clean"/"Formaclean"** (= Maika), **"Parceiro Leonardo"**.
3. Padrão **cor + número** (ex. `Roxo 366`, `Cinza 373`) sem nome de pessoa associado.

Cuidado: o motorista do parceiro Leonardo também se chama **Dhiego** — não confundir
com Diego Olivatto (dono da SuperDry, que também lança itens no WhatsApp). O nome
"Diego"/"Dhiego" sozinho NÃO é confiável para identificar parceiro; usar sempre o
padrão cor+número ou marcação explícita.

Nomes próprios no log (ex. "Silvia", "Vanessa", "Dra Sandra Silvestre") são clientes
finais comuns, não parceiros — mesmo que apareçam misturados na mesma mensagem.

**Regras adicionais confirmadas pelo dono em 24/06/2026 (reconciliação de junho/2026):**

1. **"Sem nome" / "sem número" / "sem etiqueta" = sempre item do parceiro Leonardo.**
   Não é mais um caso ambíguo — o motorista dele tem o hábito de entregar peças sem
   etiqueta nenhuma. Tratar como Leonardo confirmado, sem precisar de confirmação
   adicional, mesmo sem cor nem número.
2. **A palavra "Leonardo" pura (sem o prefixo "PARCEIRO") NÃO é um indício confiável**
   de que o item é do parceiro. Só conta como item de parceiro Leonardo confirmado se
   aparecer **uma das três coisas**: (a) o texto explícito **"PARCEIRO Leonardo"**,
   (b) etiqueta no padrão **cor + número**, ou (c) marcação de **"sem nome"/"sem
   número"** (regra 1). "Leonardo" sozinho pode ser outra coisa — cliente final
   homônimo, confusão com o motorista "Dhiego", ou menção a "parceiro Diego". Itens
   assim devem ficar **fora** do fechamento do parceiro até confirmação manual.
3. **Etiqueta repetida com 2 medições diferentes no mesmo período (mesmo código, sem
   nenhuma já cobrada antes) = erro de medição, não item duplicado nem item novo
   duplicado.** Ficar só com a maior medição (a menor é descartada como erro do
   técnico ao medir). Isso é diferente da regra de duplicata entre períodos (código +
   dimensão igual a uma já cobrada antes = duplicata real, ver acima) — aqui é o
   mesmo período, duas medições do mesmo tapete físico.
4. **Cortinas do parceiro Leonardo passam a usar o mesmo preço de tapete: R$20,00/m².**
   Não existe mais diferenciação de preço por tipo de item dentro do Leonardo — tudo
   é R$20/m² (tapete, cortina, redondo, etc.). A categoria (tapete/cortina/...)
   continua existindo só para granularidade do relatório, não para precificação. Isso
   corrige o SRV-0062 (cortina Leonardo, documentado abaixo a R$18) — **deve ser
   atualizado para R$20,00/m²** tanto no seed local quanto em produção (ainda
   pendente de execução).

## Itens de catálogo exclusivos por parceiro (já existem no sistema)

Cada parceiro tem 2 serviços próprios no catálogo (`service_type: "Tapete Parceiro"`,
`execution_location: "CLIENTE_TROUXE"`, `cost_price: R$8,00/m²`), um para tapete
quadrado/retangular (`measure_type: AREA_DE_TAPETE`) e um para redondo
(`measure_type: TAPETE_REDONDO_DIAMETRO`):

| Parceiro | SRV quadrado | SRV redondo | Preço venda (atualizado 23/06/2026) |
|---|---|---|---|
| Leonardo Dry Clean | SRV-0036 | SRV-0037 | R$ 20,00/m² |
| Vinicius (Higia) | SRV-0038 | SRV-0039 | R$ 20,00/m² |
| Maika (FormaClean) | SRV-0040 | SRV-0041 | R$ 20,00/m² |
| Wesley Higienização | SRV-0042 | SRV-0043 | R$ 20,00/m² (já estava) |
| João / Felipe | SRV-0044 | SRV-0045 | R$ 20,00/m² |

Todos `is_active: true`. Preços padronizados em R$20,00/m² para todos os parceiros em
23/06/2026 (antes: Leonardo R$18, Higia R$19, João/Felipe R$17, FormaClean/Wesley já
R$20). Atualizado tanto em produção (Oracle, via API) quanto no seed local
`meus_servicos.json`.

Cortinas do Leonardo: havia 2 itens no catálogo para cortina. Decisão do dono
(23/06/2026): **usar sempre o item de área**, ignorar o linear. Por isso o item
linear foi **desativado** (`is_active: false`) tanto em produção quanto no seed:
- `SRV-0058` — "Lavagem de Cortinas/Blackouts Parceiro Leonardo Dry Clean" (linear,
  R$18) — **DESATIVADO, não usar.**
- `SRV-0062` — "Lavagem de Cortinas Parceiro Leonardo Dry Clean" (categoria Persianas,
  área) — **item correto a usar** para qualquer cortina do Leonardo. Preço
  **atualizado em 24/06/2026 para R$20,00/m²** (regra 4 acima — unificado com tapete;
  estava documentado em R$18 até então). **Pendente:** aplicar essa correção de preço
  em produção/seed (só foi corrigida na documentação até o momento).

## Fechamento de junho/2026 — primeiro relatório de teste

Em 24/06/2026, a partir da planilha de maio/2026 (referência, "planilha tapetes
leo.pdf") + log de WhatsApp de medições de 02/06 a 22/06/2026, foi feita a primeira
reconciliação aplicando todas as regras acima. Resultado: **23 itens novos
confirmados do parceiro Leonardo em junho** (20 tapetes + 3 cortinas), totalizando
**R$ 2.147,92** (R$1.736,32 tapetes + R$411,60 cortinas), depois de excluir 13 itens
que já constavam na planilha de maio (duplicatas reais), 1 item "Roxo 366" descartado
por erro de medição (regra 3), e 1 item "Leonardo 1,4x2" excluído por não ter
identificação confiável de parceiro (regra 2).

Esse fechamento gerou o primeiro esboço de um **relatório fixo dentro do sistema**
para cobrança de parceiros. Requisitos definidos pelo dono (24/06/2026): identificação
do parceiro, as medições detalhadas, as datas a que cada medição se refere (só
informativo, não é filtro), valores, dimensões, metragem total lavada no período, e
um resumo/total ao final.

**Implementado em 24/06/2026 (frontend):** menu "Relatórios" (`/reports`, antes só
placeholder) agora lista relatórios fixos do sistema — `frontend/src/pages/Reports.js`
(novo arquivo) + rota trocada em `frontend/src/App.js` (`<Placeholder title="Relatórios"/>`
→ `<Reports/>`). Primeiro relatório disponível: "Fechamento de Parceiro —
Tapetes/Cortinas", já com os dados de junho/2026 do Leonardo (23 itens, R$2.147,92,
metragem total lavada incluída no resumo). Os demais cards do menu (Comissões,
Inadimplência, Faturamento por Período) aparecem bloqueados ("Em breve").

**Limitação atual (importante para próxima sessão):** os dados desse relatório estão
**hardcoded** dentro do componente (`LEONARDO_JUNHO_2026` em `Reports.js`), não vêm do
banco — porque os itens de parceiro de junho nunca foram lançados como BudgetItems
reais no sistema (só existiram no WhatsApp/planilha). Não foi criado nenhum endpoint
novo no backend para isso ainda. **`backend/server.py` local continua corrompido/
truncado** (mesmo problema já diagnosticado antes — arquivo cortado no meio de uma
edição, não compila), então não foi possível nem tentar adicionar um endpoint real
agora. Quando o backend for restaurado, o próximo passo é: criar um
`GET /api/reports/partner-billing` (ou similar) que agregue BudgetItems de parceiro
por período/parceiro, e trocar os dados hardcoded do `Reports.js` por uma chamada a
esse endpoint.

## O que falta construir (não implementado ainda)

Hoje o controle de parceiros é só: agenda do Google Calendar + histórico de WhatsApp.
Não existe automação que pegue as medições do WhatsApp/agenda e crie os
orçamentos/itens no sistema automaticamente.

Direção definida pelo dono (23/06/2026): a "modelagem" não precisa ser um cadastro
novo de entidade Partner — o catálogo de serviços de parceiro já existe e já resolve
a parte de precificação. O que falta é **automação**: pegar as medições por parceiro
(do log/WhatsApp) e gerar automaticamente um Orçamento (ou item de orçamento) já no
status correto de retirada/coleta (ex. `RETIRAR` ou `COLETADO`), usando o
`service_id` certo do parceiro — só para depois conseguir cobrar o parceiro pelo
volume do período, sem precisar lançar manualmente cada tapete.

Pontos abertos para quando essa automação for desenhada:
- De onde vem o gatilho: cola do texto do WhatsApp (como o usuário já faz para
  clientes comuns) ou outra fonte?
- Quem é o "cliente" do orçamento — precisa existir um Client cadastrado representando
  cada parceiro (ex. CLI próprio para "Leonardo Dry Clean")?
- Etiqueta cor+número deveria virar um campo identificável no BudgetItem (ex.
  `partner_tag`) para rastreio e para detectar reaproveitamento de número vs duplicata
  real, em vez de ficar só na descrição em texto livre.
- Fechamento mensal: hoje é manual numa planilha Google Sheets por fora — não há
  ainda um relatório/consolidado dentro do SuperDry agregando os itens de parceiro
  por período pra gerar a cobrança.
