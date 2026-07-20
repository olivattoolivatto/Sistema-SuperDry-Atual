#!/usr/bin/env python3
"""
SuperDry — Diagnóstico da coleção budgets + relatório de inadimplência filtrado.

Rode na Oracle VM:
    /usr/bin/python3.11 diagnostico_budget.py

Saída: /tmp/diagnostico_budget.json
Copiar: scp opc@148.116.108.43:/tmp/diagnostico_budget.json .
"""

import json
import os
import sys
from datetime import datetime, timezone

MONGO_URL   = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME     = os.environ.get("DB_NAME",   "superdry")
OUTPUT      = "/tmp/diagnostico_budget.json"

# Janela de análise
DATE_FROM = datetime(2026, 6, 1,  tzinfo=timezone.utc)
DATE_TO   = datetime(2026, 7, 19, 23, 59, 59, tzinfo=timezone.utc)

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def all_keys(doc, prefix=""):
    """Retorna todos os caminhos de chaves de um documento (recursivo 1 nível)."""
    keys = []
    for k, v in doc.items():
        if k == "_id":
            continue
        full = f"{prefix}{k}"
        keys.append(full)
        if isinstance(v, dict) and v:
            for sk in v.keys():
                keys.append(f"{full}.{sk}")
    return keys

def safe_str(v):
    """Converte valor para string serializável."""
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v) if v is not None else None

def main():
    from pymongo import MongoClient

    log("Conectando ao MongoDB...")
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[DB_NAME]
    log(f"MongoDB OK — banco '{DB_NAME}'")

    result = {}

    # ------------------------------------------------------------------ #
    # 1. Estrutura de 3 documentos da coleção budgets
    # ------------------------------------------------------------------ #
    log("Inspecionando estrutura da coleção budgets...")
    sample_budgets = list(db.budgets.find({}, limit=3))
    budget_field_sets = []
    for doc in sample_budgets:
        keys = all_keys(doc)
        budget_field_sets.append({
            "id":     doc.get("id", str(doc["_id"])),
            "campos": sorted(keys),
        })

    # União de todos os campos encontrados nos 3 docs
    all_budget_keys = sorted(set(
        k for b in budget_field_sets for k in b["campos"]
    ))
    log(f"  Campos encontrados em budgets: {all_budget_keys}")

    result["budgets_schema"] = {
        "amostras": budget_field_sets,
        "todos_campos_unicos": all_budget_keys,
    }

    # Valores de exemplo dos campos mais relevantes (do 1º doc)
    if sample_budgets:
        first = sample_budgets[0]
        relevantes = [
            "id", "status", "payment_status", "total_price", "total",
            "valor_total", "client_name", "client_id",
            "created_at", "updated_at", "date", "scheduled_date",
            "items", "budget_items",
        ]
        result["budgets_schema"]["valores_exemplo_primeiro_doc"] = {
            k: safe_str(first.get(k)) for k in relevantes if k in first
        }
        # Também mostra qualquer campo com "date", "price", "total", "status", "pay" no nome
        extras = {k: safe_str(first.get(k)) for k in first
                  if k != "_id" and any(x in k.lower() for x in
                     ["date","price","total","status","pay","valor","criado","data","pagam"])}
        result["budgets_schema"]["campos_financeiros_e_datas"] = extras

    # ------------------------------------------------------------------ #
    # 2. Estrutura de 3 documentos da coleção budget_items
    # ------------------------------------------------------------------ #
    log("Inspecionando estrutura da coleção budget_items...")
    sample_items = list(db.budget_items.find({}, limit=3))
    item_field_sets = []
    for doc in sample_items:
        keys = all_keys(doc)
        item_field_sets.append({
            "id":     doc.get("id", str(doc["_id"])),
            "campos": sorted(keys),
        })

    all_item_keys = sorted(set(
        k for b in item_field_sets for k in b["campos"]
    ))
    log(f"  Campos encontrados em budget_items: {all_item_keys}")

    result["budget_items_schema"] = {
        "amostras": item_field_sets,
        "todos_campos_unicos": all_item_keys,
    }

    if sample_items:
        first_item = sample_items[0]
        extras_item = {k: safe_str(first_item.get(k)) for k in first_item
                       if k != "_id" and any(x in k.lower() for x in
                          ["date","price","total","status","pay","valor","criado","data","pagam","execu","entrega"])}
        result["budget_items_schema"]["campos_financeiros_e_datas"] = extras_item

    # ------------------------------------------------------------------ #
    # 3. Contagens gerais para calibrar os filtros
    # ------------------------------------------------------------------ #
    log("Calculando contagens gerais...")
    total_budgets = db.budgets.count_documents({})
    total_items   = db.budget_items.count_documents({})

    # Distribuição de valores de status e payment_status (se existirem)
    def count_field_values(collection, field, limit=20):
        pipeline = [
            {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ]
        try:
            return [{"value": safe_str(r["_id"]), "count": r["count"]}
                    for r in collection.aggregate(pipeline)]
        except Exception as e:
            return [{"error": str(e)}]

    result["contagens"] = {
        "total_budgets": total_budgets,
        "total_budget_items": total_items,
        "budget_status_distribution":         count_field_values(db.budgets,      "status"),
        "budget_payment_status_distribution": count_field_values(db.budgets,      "payment_status"),
        "item_status_distribution":           count_field_values(db.budget_items, "status"),
        "item_payment_status_distribution":   count_field_values(db.budget_items, "payment_status"),
    }
    log(f"  Total budgets: {total_budgets} | Total items: {total_items}")

    # ------------------------------------------------------------------ #
    # 4. Orçamentos do período 01/06/2026–19/07/2026
    #    Tenta vários nomes de campo de data possíveis
    # ------------------------------------------------------------------ #
    log(f"Buscando orçamentos entre {DATE_FROM.date()} e {DATE_TO.date()}...")

    date_fields_to_try = ["created_at", "date", "scheduled_date", "updated_at", "data"]
    period_budgets_by_field = {}

    for df in date_fields_to_try:
        try:
            # Tenta com objetos datetime nativos (Motor/pymongo aceita)
            docs = list(db.budgets.find(
                {df: {"$gte": DATE_FROM, "$lte": DATE_TO}},
                {"_id": 0}
            ))
            if docs:
                log(f"  Campo '{df}': {len(docs)} orçamentos encontrados")
                period_budgets_by_field[df] = len(docs)
            else:
                # Tenta com string ISO
                docs_str = list(db.budgets.find(
                    {df: {"$gte": DATE_FROM.isoformat(), "$lte": DATE_TO.isoformat()}},
                    {"_id": 0}
                ))
                log(f"  Campo '{df}' (str): {len(docs_str)} orçamentos")
                period_budgets_by_field[df] = len(docs_str) if docs_str else 0
        except Exception as e:
            period_budgets_by_field[df] = f"ERRO: {e}"

    result["periodo_01jun_19jul"] = {"contagens_por_campo_data": period_budgets_by_field}

    # Usa o campo de data com mais resultados como candidato principal
    best_field = max(
        [f for f in date_fields_to_try if isinstance(period_budgets_by_field.get(f), int)],
        key=lambda f: period_budgets_by_field.get(f, 0),
        default=None
    )
    log(f"  Melhor campo de data: '{best_field}' ({period_budgets_by_field.get(best_field, 0)} docs)")

    if best_field:
        period_docs = list(db.budgets.find(
            {best_field: {"$gte": DATE_FROM, "$lte": DATE_TO}},
            {"_id": 0}
        ))
        if not period_docs:
            period_docs = list(db.budgets.find(
                {best_field: {"$gte": DATE_FROM.isoformat(), "$lte": DATE_TO.isoformat()}},
                {"_id": 0}
            ))

        # Serializa todos os valores (datetime → string)
        def serialize_doc(doc):
            return {k: safe_str(v) if isinstance(v, datetime) else v
                    for k, v in doc.items() if k != "_id"}

        serialized = [serialize_doc(d) for d in period_docs]

        result["periodo_01jun_19jul"]["campo_data_usado"] = best_field
        result["periodo_01jun_19jul"]["total"] = len(serialized)
        result["periodo_01jun_19jul"]["documentos"] = serialized
        log(f"  {len(serialized)} orçamentos incluídos no resultado")
    else:
        result["periodo_01jun_19jul"]["erro"] = "Nenhum campo de data retornou resultados"

    # ------------------------------------------------------------------ #
    # 5. Budget_items do período (para cruzar com pagamentos)
    # ------------------------------------------------------------------ #
    log("Buscando budget_items do período...")
    item_date_fields = ["created_at", "execution_date", "delivery_date", "scheduled_date", "updated_at"]
    period_items_by_field = {}

    for df in item_date_fields:
        try:
            n = db.budget_items.count_documents(
                {df: {"$gte": DATE_FROM, "$lte": DATE_TO}}
            )
            period_items_by_field[df] = n
        except Exception as e:
            period_items_by_field[df] = f"ERRO: {e}"

    result["periodo_01jun_19jul"]["items_contagens_por_campo_data"] = period_items_by_field
    log(f"  Items por campo de data: {period_items_by_field}")

    best_item_field = max(
        [f for f in item_date_fields if isinstance(period_items_by_field.get(f), int)],
        key=lambda f: period_items_by_field.get(f, 0),
        default=None
    )

    if best_item_field and period_items_by_field.get(best_item_field, 0) > 0:
        period_items = list(db.budget_items.find(
            {best_item_field: {"$gte": DATE_FROM, "$lte": DATE_TO}},
            {"_id": 0,
             "id": 1, "budget_id": 1, "client_name": 1,
             "service_name": 1, "status": 1, "payment_status": 1,
             "final_price": 1, "total_price": 1, "price": 1,
             best_item_field: 1}
        ))
        result["periodo_01jun_19jul"]["items_campo_data_usado"] = best_item_field
        result["periodo_01jun_19jul"]["items_total"] = len(period_items)

        def serialize_item(doc):
            return {k: safe_str(v) if isinstance(v, datetime) else v
                    for k, v in doc.items()}
        result["periodo_01jun_19jul"]["items"] = [serialize_item(i) for i in period_items]
        log(f"  {len(period_items)} items do período incluídos")

    # ------------------------------------------------------------------ #
    # 6. Salva resultado
    # ------------------------------------------------------------------ #
    log(f"Salvando em {OUTPUT}...")
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    log(f"Arquivo salvo: {OUTPUT}")
    log("Pronto! Copie com:")
    log(f"  scp opc@148.116.108.43:{OUTPUT} .")

if __name__ == "__main__":
    main()
