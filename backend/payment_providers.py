"""
SuperDry — Abstração de Provedores de Pagamento (integration-ready)
====================================================================

Este módulo isola a lógica de geração de cobrança (link/PIX) e de
conciliação via webhook, para que o restante do sistema não precise
conhecer detalhes de cada provedor.

Estado atual: provider MANUAL ativo (sem chamada externa).
Para ativar um provedor real, defina as variáveis de ambiente no .env
e troque PAYMENT_PROVIDER. Nenhuma outra parte do sistema precisa mudar.

Provedores previstos:
  - MANUAL       : sem integração (registro manual de pagamento) — padrão
  - INFINITEPAY  : geração de link/PIX + webhook de confirmação
  - (conciliação) PLUGGY / BELVO : leitura de transações via Open Finance

Fluxo de integração (quando ativado):
  1. Cobrança consolidada chama provider.create_charge(...) → link/PIX + txid
  2. Cliente paga
  3. Provedor chama POST /api/webhooks/payment
  4. provider.verify_webhook() valida assinatura
  5. provider.parse_webhook() devolve (txid/charge_id, status, valor)
  6. Sistema marca o consolidated_payment como PAGO e atualiza os itens
"""
import os
import hmac
import hashlib
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


# ============================================================
# Contrato
# ============================================================
class ChargeResult:
    def __init__(self, charge_id: Optional[str], payment_link: Optional[str],
                 pix_qr: Optional[str], txid: Optional[str], status: str = "PENDENTE"):
        self.charge_id = charge_id
        self.payment_link = payment_link
        self.pix_qr = pix_qr            # payload "copia e cola" do PIX
        self.txid = txid
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "external_charge_id": self.charge_id,
            "payment_link": self.payment_link,
            "pix_qr": self.pix_qr,
            "txid": self.txid,
            "status": self.status,
        }


class WebhookEvent:
    def __init__(self, txid: Optional[str], charge_id: Optional[str],
                 status: str, paid_value: Optional[float] = None):
        self.txid = txid
        self.charge_id = charge_id
        self.status = status           # "PAGO" | "PENDENTE" | "CANCELADO"
        self.paid_value = paid_value


class PaymentProvider(ABC):
    name = "ABSTRACT"

    @abstractmethod
    async def create_charge(self, *, amount: float, description: str,
                            txid: str, payer: Dict[str, Any],
                            items: Optional[list] = None) -> ChargeResult:
        """items (opcional): lista de detalhamento, um por serviço/ITM —
        [{"description": str, "quantity": int, "value": float}, ...].
        Se informado, o provedor deve usá-lo no lugar da `description` única
        para que o comprador veja o detalhamento real do que está pagando."""
        ...

    @abstractmethod
    def verify_webhook(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        ...

    @abstractmethod
    def parse_webhook(self, payload: Dict[str, Any]) -> WebhookEvent:
        ...


# ============================================================
# MANUAL (padrão) — nenhuma chamada externa
# ============================================================
class ManualProvider(PaymentProvider):
    name = "MANUAL"

    async def create_charge(self, *, amount, description, txid, payer, items=None) -> ChargeResult:
        # Sem provedor: o link é informado manualmente pelo operador.
        return ChargeResult(charge_id=None, payment_link=None, pix_qr=None,
                            txid=txid, status="PAGO")

    def verify_webhook(self, headers, raw_body) -> bool:
        return False  # MANUAL não recebe webhook

    def parse_webhook(self, payload) -> WebhookEvent:
        raise NotImplementedError


# ============================================================
# INFINITEPAY — Checkout API (links de pagamento)
# ============================================================
# Docs: https://www.infinitepay.io/checkout  | API base: api.checkout.infinitepay.io
#
# Fluxo:
#   create_charge → POST /links {handle, order_nsu, items[price em CENTAVOS], webhook_url, redirect_url}
#                   → resposta { "url": "<link de pagamento>" }
#   cliente paga → InfinitePay → POST webhook_url com {order_nsu, transaction_nsu, invoice_slug, paid_amount}
#   confirm_payment → POST /payment_check {handle, order_nsu, transaction_nsu, slug} (fonte da verdade)
#
# Observação: o Checkout NÃO assina o webhook com HMAC. A verificação é o
# payment_check (server-to-server). Por isso verify_webhook apenas aceita o
# recebimento e a confirmação real ocorre em confirm_payment.
#
# Env:
#   INFINITEPAY_HANDLE      (ex.: superdry)            [obrigatório]
#   INFINITEPAY_API_KEY     (Bearer, se a conta exigir) [opcional]
#   INFINITEPAY_API_BASE    (default api.checkout.infinitepay.io)
#   PUBLIC_WEBHOOK_URL      (URL pública do /api/webhooks/payment)
#   INFINITEPAY_REDIRECT_URL(para onde o cliente volta após pagar; default = webhook url)
class InfinitePayProvider(PaymentProvider):
    name = "INFINITEPAY"
    API_BASE = os.environ.get("INFINITEPAY_API_BASE", "https://api.checkout.infinitepay.io")

    def __init__(self):
        self.handle = os.environ.get("INFINITEPAY_HANDLE", "").strip()
        self.api_key = os.environ.get("INFINITEPAY_API_KEY", "").strip()
        self.webhook_url = os.environ.get("PUBLIC_WEBHOOK_URL", "").strip()
        self.redirect_url = os.environ.get("INFINITEPAY_REDIRECT_URL", "").strip() or self.webhook_url
        if not self.handle:
            raise RuntimeError("INFINITEPAY_HANDLE não configurado.")

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def create_charge(self, *, amount, description, txid, payer, items=None) -> ChargeResult:
        import httpx

        if items:
            # Um item por serviço/ITM — o comprador vê o detalhamento real
            # do que está pagando (em vez de uma descrição genérica única).
            line_items = []
            for it in items:
                price_cents = int(round(float(it.get("value") or 0) * 100))
                if price_cents <= 0:
                    continue
                line_items.append({
                    "quantity": int(it.get("quantity") or 1),
                    "price": price_cents,
                    "description": (it.get("description") or "Serviço SuperDry")[:255],
                })
            # Ajusta arredondamento: a soma dos itens precisa bater com `amount`.
            diff_cents = int(round(float(amount or 0) * 100)) - sum(li["price"] for li in line_items)
            if line_items and diff_cents:
                line_items[-1]["price"] += diff_cents
            if not line_items:
                line_items = [{
                    "quantity": 1,
                    "price": int(round(float(amount or 0) * 100)),
                    "description": (description or "Cobrança SuperDry")[:255],
                }]
        else:
            line_items = [{
                "quantity": 1,
                "price": int(round(float(amount or 0) * 100)),  # CENTAVOS
                "description": (description or "Cobrança SuperDry")[:255],
            }]

        body: Dict[str, Any] = {
            "handle": self.handle,
            "order_nsu": txid,                                  # nosso CPG-XXXX
            "items": line_items,
        }
        if self.webhook_url:
            body["webhook_url"] = self.webhook_url
        if self.redirect_url:
            body["redirect_url"] = self.redirect_url
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(f"{self.API_BASE}/links", headers=self._headers(), json=body)
            r.raise_for_status()
            d = r.json()
        return ChargeResult(charge_id=txid, payment_link=d.get("url"),
                            pix_qr=None, txid=txid, status="PENDENTE")

    def verify_webhook(self, headers, raw_body) -> bool:
        # Checkout InfinitePay não envia HMAC. A verificação real é o payment_check
        # (confirm_payment), feito no endpoint antes de marcar como pago.
        return True

    def parse_webhook(self, payload) -> WebhookEvent:
        cents = payload.get("paid_amount") or payload.get("amount") or 0
        return WebhookEvent(
            txid=payload.get("order_nsu"),                                   # = CPG-XXXX
            charge_id=payload.get("transaction_nsu") or payload.get("invoice_slug"),
            status="PAGO",   # o webhook do Checkout dispara na confirmação do pagamento
            paid_value=(float(cents) / 100.0) if cents else None,
        )

    async def confirm_payment(self, *, order_nsu, transaction_nsu, slug) -> bool:
        """Confirmação server-to-server (payment_check) — fonte da verdade.
        LOG DE DIAGNÓSTICO: grava a resposta crua em payment_check_log.txt (raiz do
        backend) pra conferir o formato real na primeira ativação — nunca testado
        contra a API de produção da InfinitePay até agora."""
        import httpx
        from pathlib import Path
        from datetime import datetime as _dt
        body = {"handle": self.handle, "order_nsu": order_nsu,
                "transaction_nsu": transaction_nsu, "slug": slug}
        log_path = Path(__file__).resolve().parent / "payment_check_log.txt"

        NL = chr(10)
        def _log(line: str):
            try:
                with open(log_path, "a", encoding="utf-8") as lf:
                    lf.write(NL + "[" + _dt.utcnow().isoformat() + "] " + line + NL)
            except Exception:
                pass

        try:
            async with httpx.AsyncClient(timeout=20) as c:
                r = await c.post(f"{self.API_BASE}/payment_check",
                                 headers=self._headers(), json=body)
            _log("REQUEST body=" + str(body) + NL + "RESPONSE status=" + str(r.status_code) + " body=" + r.text)
            if r.status_code != 200:
                return False
            d = r.json()
            # CONFIRMAR shape real ao ativar: aceita várias chaves comuns de status.
            if isinstance(d, dict):
                if d.get("paid") is True or d.get("success") is True:
                    return True
                if str(d.get("status", "")).lower() in ("paid", "approved", "success", "captured"):
                    return True
            return False
        except Exception as e:
            _log(f"EXCEPTION order_nsu={order_nsu} transaction_nsu={transaction_nsu} slug={slug} erro={e}")
            return False


# ============================================================
# Seletor — lê PAYMENT_PROVIDER do ambiente
# ============================================================
def get_provider() -> PaymentProvider:
    name = (os.environ.get("PAYMENT_PROVIDER") or "MANUAL").upper()
    if name == "INFINITEPAY":
        return InfinitePayProvider()
    return ManualProvider()


# ============================================================
# CONCILIAÇÃO via Open Finance (Pluggy / Belvo) — esqueleto
# ============================================================
# Para conciliação bancária em tempo real (Nubank/InfinitePay/etc.) use um
# agregador já regulado no Open Finance. Eles entregam um feed de transações.
#
# Requer: OPENFINANCE_PROVIDER (PLUGGY|BELVO), e credenciais do agregador.
# Fluxo: sync_transactions() puxa transações recentes → casa por valor/txid
# com consolidated_payments PENDENTES → marca PAGO.
class ReconciliationProvider(ABC):
    @abstractmethod
    async def fetch_recent_transactions(self, since_iso: str) -> list:
        """Retorna [{amount, date, description, counterparty, external_id?}]."""
        ...


class PluggyReconciliation(ReconciliationProvider):
    name = "PLUGGY"

    def __init__(self):
        self.client_id = os.environ.get("PLUGGY_CLIENT_ID", "")
        self.client_secret = os.environ.get("PLUGGY_CLIENT_SECRET", "")
        if not self.client_id:
            raise RuntimeError("PLUGGY_CLIENT_ID não configurada.")

    async def fetch_recent_transactions(self, since_iso: str) -> list:
        # TODO ao ativar: autenticar (apiKey) e GET /transactions via SDK/HTTP Pluggy.
        raise NotImplementedError("Implementar integração Pluggy ao ativar.")


def get_reconciliation_provider() -> Optional[ReconciliationProvider]:
    name = (os.environ.get("OPENFINANCE_PROVIDER") or "").upper()
    if name == "PLUGGY":
        return PluggyReconciliation()
    return None
