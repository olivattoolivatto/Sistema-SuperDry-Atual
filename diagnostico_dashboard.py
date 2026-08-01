"""
Diagnóstico: quais orçamentos/itens estão aparecendo nos contadores do Dashboard.
Execute na pasta raiz do projeto:  python diagnostico_dashboard.py
"""
import asyncio
import json
import os
import sys

# Carrega .env
env = {}
env_path = os.path.join(os.path.dirname(__file__), "backend", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()

MONGO_URL = env.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME   = env.get("DB_NAME", "superdry")

ROUTE_STATUSES = {"RETIRAR", "EXECUTAR_NO_LOCAL", "ENTREGAR"}
WASH_STATUSES  = {"EM_LAVAGEM", "EM_LAVAGEM_PARCEIRO", "COLETADO", "AGUARDANDO_ENTREGA",
                  "AGUARDANDO_BUSCAR", "EXECUCAO_PARCIAL"}
DELIVERED      = {"ENTREGUE", "EXECUTADO", "BUSCOU"}
DEBT_PAY       = {"PENDENTE", "PARCIAL", "INADIMPLENTE"}


async def main():
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ImportError:
        print("motor não instalado. Rode:  pip install motor")
        sys.exit(1)

    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    sep = "─" * 60

    # ── 1. Itens pendentes de rota ─────────────────────────────────
    print(f"\n{sep}")
    print("1) ITENS PENDENTES DE ROTA  (card 'Itens Pendentes de Rota')")
    print(sep)
    count = 0
    async for b in db.budgets.find(
        {"budget_status": "APROVADO", "items.status": {"$in": list(ROUTE_STATUSES)}}
    ):
        for it in (b.get("items") or []):
            if (it.get("status") in ROUTE_STATUSES
                    and not it.get("current_route_id")
                    and it.get("execution_mode") not in ("CLIENTE_TROUXE", "CLIENTE_LEVARA")):
                count += 1
                print(f"  ORC {b.get('id')} | Cliente: {b.get('client_name')}")
                print(f"    Item: {it.get('id')} | Serviço: {it.get('service_name')}")
                print(f"    Status: {it.get('status')} | Modo: {it.get('execution_mode')}")
                print()
    print(f"  Total: {count}")

    # ── 2. Orçamentos ativos ───────────────────────────────────────
    print(f"\n{sep}")
    print("2) ORÇAMENTOS ATIVOS  (card 'Orçamentos Ativos')")
    print(sep)
    count = 0
    async for b in db.budgets.find({"budget_status": "APROVADO"}):
        items = b.get("items") or []
        has_pending = any(
            it.get("status") in ROUTE_STATUSES and not it.get("current_route_id")
            for it in items
        )
        if has_pending:
            count += 1
            print(f"  ORC {b.get('id')} | Cliente: {b.get('client_name')}")
            for it in items:
                if it.get("status") in ROUTE_STATUSES and not it.get("current_route_id"):
                    print(f"    → Item {it.get('id')}: {it.get('service_name')} [{it.get('status')}]")
            print()
    print(f"  Total: {count}")

    # ── 3. Em lavagem ──────────────────────────────────────────────
    print(f"\n{sep}")
    print("3) EM LAVAGEM / EXECUÇÃO  (card 'Em Lavagem')")
    print(sep)
    count = 0
    async for b in db.budgets.find({"items.status": {"$in": list(WASH_STATUSES)}}):
        for it in (b.get("items") or []):
            if it.get("status") in WASH_STATUSES:
                count += 1
                print(f"  ORC {b.get('id')} | {b.get('client_name')} | "
                      f"Item {it.get('id')}: {it.get('service_name')} [{it.get('status')}] | "
                      f"Budget: {b.get('budget_status')}")
    print(f"\n  Total: {count}")

    # ── 4. Pendências financeiras ──────────────────────────────────
    print(f"\n{sep}")
    print("4) PENDÊNCIAS FINANCEIRAS  (card 'Pendências Financeiras')")
    print(sep)
    count = 0
    async for b in db.budgets.find({"items.status": {"$in": list(DELIVERED)}}):
        for it in (b.get("items") or []):
            if it.get("status") in DELIVERED and it.get("payment_status") in DEBT_PAY:
                count += 1
                print(f"  ORC {b.get('id')} | {b.get('client_name')} | "
                      f"Item {it.get('id')}: {it.get('service_name')} | "
                      f"pay={it.get('payment_status')} | R${it.get('total_price', 0):.2f}")
    print(f"\n  Total: {count}")

    client.close()
    print(f"\n{sep}\nDiagnóstico concluído.\n")


asyncio.run(main())
