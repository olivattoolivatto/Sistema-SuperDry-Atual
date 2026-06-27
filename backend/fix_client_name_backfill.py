"""
Backfill: propaga client_id e client_name do budget pai para os
budget_items embutidos que estão com esses campos nulos.

Roda uma única vez. Seguro rodar novamente (idempotente).
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME   = os.getenv("DB_NAME", "superdry")


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # Busca todos os budgets que têm pelo menos um item sem client_name
    budgets = await db.budgets.find(
        {"items.client_name": None},
        {"id": 1, "client_id": 1, "client_name": 1, "items": 1}
    ).to_list(None)

    print(f"Budgets com itens sem client_name: {len(budgets)}")

    total_fixed = 0
    for bud in budgets:
        parent_name = bud.get("client_name")
        parent_id   = bud.get("client_id")
        if not parent_name:
            print(f"  SKIP {bud['id']} — o próprio budget não tem client_name")
            continue

        # Atualiza todos os items[] onde client_name é null
        result = await db.budgets.update_one(
            {"_id": bud["_id"]},
            [{
                "$set": {
                    "items": {
                        "$map": {
                            "input": "$items",
                            "as": "item",
                            "in": {
                                "$mergeObjects": [
                                    "$$item",
                                    {
                                        "client_name": {
                                            "$cond": [
                                                {"$or": [
                                                    {"$eq": ["$$item.client_name", None]},
                                                    {"$eq": ["$$item.client_name", ""]}
                                                ]},
                                                parent_name,
                                                "$$item.client_name"
                                            ]
                                        },
                                        "client_id": {
                                            "$cond": [
                                                {"$or": [
                                                    {"$eq": ["$$item.client_id", None]},
                                                    {"$eq": ["$$item.client_id", ""]}
                                                ]},
                                                parent_id,
                                                "$$item.client_id"
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            }]
        )
        if result.modified_count:
            n = sum(1 for it in bud["items"] if not it.get("client_name"))
            print(f"  FIXED {bud['id']} ({parent_name}) — {n} item(ns) corrigido(s)")
            total_fixed += n

    print(f"\nTotal de itens corrigidos: {total_fixed}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
