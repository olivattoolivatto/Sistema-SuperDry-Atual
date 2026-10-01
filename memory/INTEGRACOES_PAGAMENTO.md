# Integrações de Pagamento — Plano Técnico

Documento de referência para ativar pagamentos automáticos (link/PIX) e
conciliação bancária no SuperDry. **Atualizado em 24/06/2026** após investigação real em produção
(VM Oracle) — ver "Estado real verificado em 24/06/2026" logo abaixo. O resto do documento (§2-§7)
descreve o plano original, anterior à migração para a VM, e contém trechos desatualizados (Proxmox,
Cloudflare Tunnel, Tailscale) — mantido como histórico, mas não confiar nele sem checar a seção atualizada.

> ⚠️ **`PAYMENT_PROVIDER=INFINITEPAY` já está ATIVO** em produção (VM) e local — não é MANUAL como
> a versão antiga deste doc dizia. `create_charge` funciona e já gerou 3 links reais. Mas a
> **confirmação automática (webhook) nunca funcionou de fato em produção** até hoje. Isso ficou
> obsoleto porque o trabalho foi feito quando o sistema ainda rodava local (PC do dono); depois da
> migração para a VM Oracle (sempre ligada, IP fixo) em 12/06/2026, ninguém testou/ajustou de novo.

## Estado real verificado em 24/06/2026 (Mongo de produção, via SSH)

Consulta a `consolidated_payments` na VM encontrou 3 cobranças reais via InfinitePay:

| CPG | Pagador / Valor | Status | Como confirmou | Datas |
|---|---|---|---|---|
| CPG-0002 | — | **PENDENTE** | nunca confirmado | criado 04/06/2026 |
| CPG-0003 | — | **PENDENTE** | nunca confirmado | criado 04/06/2026 |
| CPG-0004 | Eduardo Ficagna, R$450 | PAGO | **manual** (`provider_event: "manual-eduardo"`) — confirmado fora do fluxo oficial, não via webhook nem redirect | criado 09/06, pago 10/06 |

**Conclusões:**
- `create_charge` (`POST /links`) funciona de verdade — os 3 links são reais (`checkout.infinitepay.io/superdry?lenc=...`).
- A baixa automática (`_apply_cp_paid`) só é chamada pelo webhook (`POST /api/webhooks/payment`) ou
  pelo redirect de retorno (`GET /payments/infinitepay/return`) — **nenhum dos dois nunca disparou em
  produção**: não existe nenhuma linha em `webhook_recebidos.log` (arquivo nem existe ainda, nem local
  nem na VM).
- Não está confirmado se CPG-0002/0003 foram realmente pagas pelo cliente e o webhook não chegou, ou
  se o cliente simplesmente nunca pagou — **precisa ser checado direto no painel da InfinitePay**.
- `INFINITEPAY_API_KEY` está vazia em produção e local — se a conta exigir Bearer token para
  `/payment_check`, isso pode estar fazendo `confirm_payment` falhar silenciosamente (a função trata
  exceção e retorna `False`).
- Havia uma linha duplicada de `INFINITEPAY_REDIRECT_URL` em `/etc/superdry.env` na VM (cosmético,
  sem efeito prático, mas deve ser limpa).

### Mitigação implementada em 24/06/2026 (enquanto o webhook não é validado)

Para dar visibilidade e controle dentro do próprio sistema (em vez de depender só do webhook ou de
consulta direta ao banco), foi adicionado:
- `GET /api/payments/consolidated/pending` — lista cobranças com link gerado ainda PENDENTE.
- `POST /api/payments/consolidated/{cpid}/confirm-manual` — confirma manualmente (ADMIN/FINANCEIRO),
  chamando o mesmo `_apply_cp_paid` usado pelo webhook (idempotente, dá baixa nos itens).
- Painel "Cobranças com link aguardando pagamento" em **Financeiro** (`Financial.js`) com botões de
  copiar link, reenviar por WhatsApp e "Marcar como pago".

Fluxo recomendado enquanto o webhook não está validado:
1. Gerar a cobrança normalmente (cria o link real via InfinitePay).
2. Enviar o link ao cliente (WhatsApp).
3. Conferir o recebimento no painel da própria InfinitePay.
4. Se confirmado fora do sistema, usar "Marcar como pago" no painel de Financeiro.
5. Quando/se o webhook passar a funcionar de fato, a confirmação volta a ser automática — o painel
   manual continua útil como rede de segurança.

---

> Este doc cobre o lado **contas a receber** (cobrar clientes). O lado **gestão/contas a
> pagar** (gestor estilo Organizze, contas, cartões, despesas PF/PJ, Nubank Empresarial via
> Open Finance) está em [GESTOR_FINANCEIRO.md](GESTOR_FINANCEIRO.md). Os dois compartilham
> o agregador Open Finance (Pluggy/Belvo) da §5.

---

## 1. Visão geral

| Camada | Hoje | Quando ativar |
|--------|------|---------------|
| Cobrança consolidada | ✅ Funcional (registro manual) | — |
| Geração de link/PIX | Manual (cola link no campo) | InfinitePay via API |
| Confirmação automática | — | Webhook `/api/webhooks/payment` |
| Conciliação bancária | — | Agregador Open Finance (Pluggy/Belvo) |

Arquivos já criados:
- `backend/payment_providers.py` — abstração de provedores + esqueletos InfinitePay/Pluggy
- `backend/server.py` → endpoint `POST /api/webhooks/payment` (inerte até configurar)
- Coleção `consolidated_payments` com campos `provider`, `external_charge_id`, `payment_link`, `txid`, `status`

---

## 2. Hospedagem (HISTÓRICO — superado pela migração de 12/06/2026)

> Esta seção descrevia o plano original (Proxmox + Cloudflare Tunnel). **Não é o que está em
> produção.** Ver [`INFRAESTRUTURA.md`](INFRAESTRUTURA.md) para o estado real: o sistema roda na
> **Oracle Cloud VM** (`148.116.108.43`, IP público fixo), com `sistema.lavesuperdry.com.br`
> **proxyado pelo Cloudflare** (modo proxy DNS, não Tunnel) → HTTP simples na origem (porta 80,
> Nginx). Webhook do provedor chega em `https://sistema.lavesuperdry.com.br/api/webhooks/payment`
> — URL pública real, sem depender de PC ligado nem Tailscale.

---

## 3. Variáveis de ambiente (.env do backend) — valores reais em produção (24/06/2026)

```env
# Provedor de cobrança (MANUAL | INFINITEPAY) — JÁ ATIVO: INFINITEPAY
PAYMENT_PROVIDER=INFINITEPAY

# InfinitePay Checkout — api.checkout.infinitepay.io
INFINITEPAY_HANDLE=superdry
INFINITEPAY_API_KEY=                # ainda vazia — checar se a conta exige Bearer
INFINITEPAY_API_BASE=https://api.checkout.infinitepay.io
INFINITEPAY_REDIRECT_URL=https://sistema.lavesuperdry.com.br
PUBLIC_WEBHOOK_URL=https://sistema.lavesuperdry.com.br/api/webhooks/payment

# Conciliação Open Finance (quando ativar) — PLUGGY | BELVO
OPENFINANCE_PROVIDER=
PLUGGY_CLIENT_ID=
PLUGGY_CLIENT_SECRET=
```

Idêntico em `backend/.env` (local) e `/etc/superdry.env` (VM), exceto que a VM tinha uma linha
duplicada de `INFINITEPAY_REDIRECT_URL` (cosmético, corrigido em 24/06/2026).

---

## 3b. API real InfinitePay Checkout (confirmado em jun/2026)

Base: `https://api.checkout.infinitepay.io` · handle do lojista: **`superdry`** · **preços em CENTAVOS**.
Docs: https://www.infinitepay.io/checkout · credenciais: ecommerce@infinitepay.io

- **Criar link:** `POST /links` `{handle, order_nsu, items[{quantity,price,description}], webhook_url, redirect_url}` → `{ "url": "<link>" }`
- **Webhook (sem HMAC!):** `POST {webhook_url}` `{invoice_slug, amount, paid_amount, installments, capture_method, transaction_nsu, order_nsu, receipt_url, items}` → responder **200**
- **Confirmar (fonte da verdade):** `POST /payment_check` `{handle, order_nsu, transaction_nsu, slug}`

**Implementado (jun/2026)** em `payment_providers.py::InfinitePayProvider`:
`create_charge` (POST /links), `parse_webhook` (lê order_nsu=CPG, paid_amount), `confirm_payment` (payment_check). O endpoint `/api/webhooks/payment` chama `confirm_payment` antes de aplicar. `order_nsu` = nosso `CPG-XXXX`.

**Pendente — itens (3) e (4) abaixo já foram feitos, (1) e (2) ainda não:**
1. Credenciais/`INFINITEPAY_API_KEY` se a conta exigir Bearer — **ainda vazia, não confirmado se é necessária.**
2. Confirmar o **shape real da resposta** do `payment_check` — **nunca validado contra uma chamada real** (o código aceita várias chaves de status na expectativa, sem confirmação).
3. ~~`INFINITEPAY_REDIRECT_URL`~~ ✅ definido: `https://sistema.lavesuperdry.com.br`.
4. ~~trocar `PAYMENT_PROVIDER=INFINITEPAY`~~ ✅ já está `INFINITEPAY` em produção e local.

Webhook URL real em produção: `https://sistema.lavesuperdry.com.br/api/webhooks/payment` (não mais Tailscale).

## 4. Fluxo InfinitePay (quando ativar)

```
Financeiro → "Cobrar selecionados" → cria CPG-XXXX (status PENDENTE)
   ↓
provider.create_charge(amount, txid=CPG-XXXX, payer) → link + PIX QR
   ↓
Sistema mostra/envia o link e o PIX copia-e-cola por WhatsApp
   ↓
Cliente paga
   ↓
InfinitePay → POST /api/webhooks/payment
   ↓
verify_webhook() valida assinatura HMAC
parse_webhook() → (txid=CPG-XXXX, status=PAGO, valor)
   ↓
Sistema marca CPG-XXXX = PAGO e distribui pagamento nos itens
```

### Tarefas de código para ativar InfinitePay
1. Em `payment_providers.py::InfinitePayProvider.create_charge` — implementar a
   chamada HTTP real (shape já comentado no arquivo).
2. Conferir o **header de assinatura** real do webhook e ajustar `verify_webhook`.
3. Conferir os **campos do payload** e ajustar `parse_webhook`.
4. ✅ **FEITO (2026-06-03).** `create_consolidated_payment` já é provider-aware: em modo
   gateway cria a cobrança, guarda link/PIX/charge_id e marca `PENDENTE`; o webhook aplica.
   Caminho MANUAL inalterado.
5. Definir `PAYMENT_PROVIDER=INFINITEPAY` + credenciais no `.env`.

---

## 5. Conciliação bancária (Open Finance via Pluggy/Belvo)

Para "valores atualizados em tempo real" e bater PIX recebido com cobranças:

1. Contratar agregador regulado (**Pluggy** ou **Belvo**) — eles já são participantes
   Open Finance e conectam no Nubank, InfinitePay, etc.
2. Conectar as contas (Nubank, InfinitePay) via fluxo do agregador.
3. Implementar `PluggyReconciliation.fetch_recent_transactions` (esqueleto pronto).
4. Job periódico: puxa transações → casa por `valor` + `txid`/descrição com
   `consolidated_payments` PENDENTES → marca PAGO.

> **Nubank direto não tem API** — só via Open Finance/agregador. Confirmado.

---

## 6. Segurança

- Backend exposto **só** via Cloudflare Tunnel (TLS). Mongo nunca exposto.
- Webhook valida assinatura HMAC (`verify_webhook`) — rejeita não assinados.
- JWT já protege o resto da API.
- `JWT_SECRET_KEY` forte (mín. 32 bytes) no `.env` de produção.
- Backups da VM (snapshot Proxmox) + dump periódico do Mongo.

---

## 7. Checklist de ativação (atualizado 24/06/2026)

- [x] VM provisionada — Oracle Cloud (não Proxmox), sempre ligada, IP fixo
- [x] HTTPS público — Cloudflare proxy DNS (não Tunnel) em `sistema.lavesuperdry.com.br`
- [ ] Conta lojista InfinitePay — handle `superdry` já configurado; **API key/webhook secret ainda
      não confirmados** (campo vazio)
- [x] Implementar `create_charge` / `verify_webhook` / `parse_webhook` reais — feito, `create_charge`
      confirmado funcionando com 3 links reais gerados
- [x] Ajustar `create_consolidated_payment` para modo PENDENTE quando provider≠MANUAL — feito
- [x] `.env` com `PAYMENT_PROVIDER=INFINITEPAY` — já ativo em produção e local
- [ ] **Testar com pagamento real de valor baixo e confirmar que o webhook chega** — ainda não feito;
      é o item crítico que falta para validar o ciclo completo (as 3 cobranças reais existentes nunca
      foram confirmadas pelo fluxo automático)
- [x] Mitigação manual enquanto isso — painel "Cobranças com link aguardando pagamento" em Financeiro
      (`GET /payments/consolidated/pending` + `POST .../confirm-manual`), adicionado 24/06/2026
- [ ] (Opcional) Agregador Open Finance para conciliação

---

## 8. Template de mensagem de cobrança via WhatsApp — decidido em 25/06/2026

Testado e aprovado pelo dono (opção "link do PDF do orçamento" em vez de descrever o serviço por
extenso na mensagem). Formato final, para uso no futuro disparo automático (WhatsApp Business API /
Evolution API — ver tarefa de implantação):

```
Olá {nome_cliente}! Segue o link para pagamento de R${valor} referentes ao último serviço prestado.
Detalhes do serviço podem ser vistos em: {link_pdf_orcamento}

{link_pagamento_infinitepay}
```

- `{nome_cliente}` — primeiro nome do cliente (`client.name`).
- `{valor}` — valor total da cobrança, formatado `R$XXX,XX`.
- `{link_pdf_orcamento}` — usa o link já gerado pelo backend em `GET /budgets/{id}/whatsapp`
  (campo derivado de `PUBLIC_WEBHOOK_URL` sem o `/api/webhooks/payment`): 
  `{PUBLIC_WEBHOOK_URL sem sufixo}/api/budgets/{budget_id}/pdf`. Depende de `PUBLIC_WEBHOOK_URL`
  estar correto em produção (ver §3) — checar ao equalizar o deploy.
- `{link_pagamento_infinitepay}` — link gerado por `create_charge` (mesmo fluxo da Cobrança
  Consolidada / CPG-XXXX).
- Texto fixo "referentes ao último serviço prestado" — genérico de propósito, não cita o serviço
  específico (decisão explícita do dono para manter a mensagem curta).

---

## Atualização 01/10/2026 — confirmado: InfinitePay segue ativa, ninguém testou de novo desde jun/2026

Reconfirmado contra o servidor em produção (`sistema.lavesuperdry.com.br`, via chamada direta ao
endpoint, sem precisar de SSH): `PAYMENT_PROVIDER=INFINITEPAY` continua ativo (webhook não retorna
503/MANUAL). `.env` local confirma os mesmos valores de jun/2026 (`INFINITEPAY_HANDLE=superdry`,
`INFINITEPAY_API_KEY` ainda vazia, `INFINITEPAY_REDIRECT_URL` agora aponta para
`/api/payments/infinitepay/return`).

**Pesquisa na documentação oficial da InfinitePay (out/2026)**: continua sendo só a API de
"Checkout Integrado" (`POST /links`), igual ao que já está implementado — não existe parâmetro pra
controlar parcelamento por transação/valor. O limite de parcelas (ex.: 6x) é configuração única da
conta, vale pra toda venda igual, independente do valor. Não há API alternativa mais nova que
resolva isso — é uma limitação de produto da InfinitePay, não do nosso código.

**Diagnóstico adicionado (commit 68e9b84)**: `confirm_payment` (payment_check) agora grava a
resposta crua da InfinitePay em `backend/payment_check_log.txt` — nunca foi confirmado contra uma
chamada real, o parsing de status era só uma suposição. Ler esse arquivo depois do próximo teste
real pra confirmar/ajustar o parsing.

**Teste pendente, nunca refeito desde as 3 cobranças de jun/2026** (CPG-0002/0003 nunca confirmadas,
CPG-0004 do Eduardo foi paga de verdade mas só confirmada manualmente — nem webhook nem redirect
dispararam nem para essa). Próximo teste real deve conferir, nessa ordem:
1. `webhook_recebidos.log` recebeu alguma linha depois do pagamento? Se não, o problema é a
   InfinitePay não estar chamando nosso webhook/redirect de volta (checar painel da própria
   InfinitePay, ou abrir chamado com o suporte deles perguntando se o Checkout Integrado realmente
   dispara webhook pra todo link gerado via API, e se há algo a habilitar do lado da conta).
2. Se a linha chegou no webhook_recebidos.log, olhar `payment_check_log.txt` pra ver a resposta real
   do `payment_check` e ajustar o parsing em `InfinitePayProvider.confirm_payment` se necessário.
