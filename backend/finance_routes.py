"""
SuperDry — Gestor Financeiro — Endpoints REST (Fase 0)
========================================================

Implementa o que está descrito em memory/GESTOR_FINANCEIRO.md §5/§12 Fase 0:
CRUD de `financial_accounts`, `financial_categories` e `financial_entries`
(o agregador com `splits[]` por categoria).

Import tardio e proposital de `server` (em vez de `from server import db, ...`)
para evitar import circular: este módulo é importado de dentro de `server.py`,
perto do final do arquivo — quando isso acontece, `db`, `get_current_user`,
`UserPublic` e `_next_id` já existem no namespace de `server`, então acessá-los
via `server.<nome>` dentro dos corpos das funções (avaliados em tempo de
requisição, não de import) funciona sem problema.
"""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

import server  # import tardio proposital — ver docstring acima
import finance_import
import finance_agenda_reconcile
from finance_manager import (
    AccountType,
    CATEGORY_TREE,
    CategoryKind,
    DEFAULT_CATEGORIES,
    EntryKind,
    EntrySource,
    EntryStatus,
    Scope,
    derive_status,
)

finance_router = APIRouter(prefix="/api/finance", tags=["finance"])


def _only_digits(s: Optional[str]) -> Optional[str]:
    """Normaliza CPF/CNPJ pra só dígitos (ou None). Usado em holder_document —
    ver finance_import.py para a detecção de transferência entre contas próprias."""
    if not s:
        return None
    digits = re.sub(r"\D", "", s)
    return digits or None


def _check_scope(scope: str):
    valid = {Scope.EMPRESA.value, Scope.PESSOAL.value, Scope.AMBOS.value}
    if scope not in valid:
        raise HTTPException(status_code=400, detail=f"Scope inválido: {scope}")


# Status "efetivados" (afetam o saldo real) vs "previstos" (só projeção/fluxo de caixa
# futuro) — mesma distinção que o Organizze chama de "Saldo" vs "Previsão de Saldo".
SETTLED_STATUSES = [EntryStatus.PAGO.value, EntryStatus.CONCILIADO.value]
PENDING_STATUSES = [EntryStatus.PENDENTE.value, EntryStatus.A_CATEGORIZAR.value]


def _today_iso() -> str:
    return datetime.utcnow().date().isoformat()


def _scope_filter(scope: Optional[str]) -> Dict[str, Any]:
    """Filtro de escopo para contas/lançamentos. `None` ou `AMBOS` = visão combinada
    PF+PJ (sem filtro, retorna tudo) — diferente do uso de AMBOS como valor de escopo
    *armazenado* numa categoria (que significa "aplica-se aos dois"). Aqui é o
    parâmetro de navegação do usuário MEI que quer ver as finanças misturadas."""
    if not scope or scope == Scope.AMBOS.value:
        return {}
    return {"scope": scope}


def _annotate_entry(e: Dict[str, Any]) -> Dict[str, Any]:
    """Anexa `is_overdue`: lançamento previsto (não efetivado/confirmado) cuja data já
    passou — não confundir com payment_method nem com o status em si; é só um indicador
    visual derivado para a UI (card vermelho/laranja na tela de lançamentos)."""
    status = e.get("status")
    e["is_overdue"] = bool(
        status in PENDING_STATUSES and (e.get("date") or "") < _today_iso()
    )
    return e


async def _compute_account_balance(account: Dict[str, Any]) -> Dict[str, Any]:
    """Saldo real (lançamentos PAGO/CONCILIADO) + previsão (inclui PENDENTE/
    A_CATEGORIZAR) — espelha a Barra de Resultados do modo "Fluxo de caixa" do
    Organizze (Saldo vs Previsão de Saldo)."""
    opening = float(account.get("opening_balance") or 0)
    income = expense = 0.0
    forecast_income = forecast_expense = 0.0
    cursor = server.db.financial_entries.find(
        {"account_id": account["id"]}, {"_id": 0, "kind": 1, "total_value": 1, "status": 1}
    )
    async for e in cursor:
        v = float(e.get("total_value") or 0)
        st = e.get("status")
        is_income = e.get("kind") == EntryKind.RECEITA.value
        is_expense = e.get("kind") == EntryKind.DESPESA.value
        if st in SETTLED_STATUSES:
            if is_income:
                income += v
            elif is_expense:
                expense += v
        elif st in PENDING_STATUSES:
            if is_income:
                forecast_income += v
            elif is_expense:
                forecast_expense += v
    current_balance = opening + income - expense
    forecast_balance = current_balance + forecast_income - forecast_expense
    return {
        "opening_balance": round(opening, 2),
        "settled_income": round(income, 2),
        "settled_expense": round(expense, 2),
        "current_balance": round(current_balance, 2),
        "forecast_income": round(forecast_income, 2),
        "forecast_expense": round(forecast_expense, 2),
        "forecast_balance": round(forecast_balance, 2),
    }


# ════════════════════════════════════════════════════════════════════════════
# Contas e cartões (ACC-XXXX)
# ════════════════════════════════════════════════════════════════════════════
@finance_router.get("/accounts")
async def list_accounts(
    scope: Optional[str] = None,
    include_archived: bool = False,
    with_balance: bool = False,
    current_user=Depends(server.get_current_user),
):
    q: Dict[str, Any] = {**_scope_filter(scope)}
    if not include_archived:
        q["archived"] = {"$ne": True}
    accounts = await server.db.financial_accounts.find(q, {"_id": 0}).sort("name", 1).to_list(1000)
    if with_balance:
        for acc in accounts:
            acc["balance"] = await _compute_account_balance(acc)
    return accounts


@finance_router.post("/accounts")
async def create_account(payload: Dict[str, Any], current_user=Depends(server.get_current_user)):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome da conta é obrigatório.")
    try:
        acc_type = AccountType(payload.get("type"))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Tipo de conta inválido: {payload.get('type')}")
    scope = payload.get("scope", Scope.EMPRESA.value)
    _check_scope(scope)

    opening = float(payload.get("opening_balance") or 0)
    acc_id = await server._next_id(server.db.financial_accounts, "ACC-", 4)
    doc = {
        "id": acc_id,
        "name": name,
        "type": acc_type.value,
        "scope": scope,
        "institution": payload.get("institution"),
        "holder_document": _only_digits(payload.get("holder_document")),
        "statement_pdf_password": (payload.get("statement_pdf_password") or "").strip() or None,
        "opening_balance": opening,
        "current_balance": opening,
        "credit_limit": payload.get("credit_limit"),
        "closing_day": payload.get("closing_day"),
        "due_day": payload.get("due_day"),
        "openfinance": {
            "connected": False, "provider": None, "item_id": None,
            "account_id": None, "last_sync": None,
        },
        "color": payload.get("color"),
        "icon": payload.get("icon"),
        "archived": False,
        "created_at": datetime.utcnow().isoformat(),
    }
    await server.db.financial_accounts.insert_one(doc)
    doc.pop("_id", None)
    return doc


@finance_router.put("/accounts/{account_id}")
async def update_account(account_id: str, payload: Dict[str, Any], current_user=Depends(server.get_current_user)):
    existing = await server.db.financial_accounts.find_one({"id": account_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")

    update: Dict[str, Any] = {}
    for f in ["name", "institution", "credit_limit", "closing_day", "due_day", "color", "icon", "archived"]:
        if f in payload:
            update[f] = payload[f]
    if "holder_document" in payload:
        update["holder_document"] = _only_digits(payload.get("holder_document"))
    if "statement_pdf_password" in payload:
        update["statement_pdf_password"] = (payload.get("statement_pdf_password") or "").strip() or None
    if "scope" in payload:
        _check_scope(payload["scope"])
        update["scope"] = payload["scope"]
    if "type" in payload:
        try:
            update["type"] = AccountType(payload["type"]).value
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Tipo de conta inválido: {payload['type']}")
    if "opening_balance" in payload:
        new_opening = float(payload["opening_balance"])
        delta = new_opening - float(existing.get("opening_balance") or 0)
        update["opening_balance"] = new_opening
        update["current_balance"] = float(existing.get("current_balance") or 0) + delta

    if update:
        await server.db.financial_accounts.update_one({"id": account_id}, {"$set": update})
    return await server.db.financial_accounts.find_one({"id": account_id}, {"_id": 0})


@finance_router.delete("/accounts/{account_id}")
async def delete_account(account_id: str, current_user=Depends(server.get_current_user)):
    in_use = await server.db.financial_entries.count_documents({"account_id": account_id})
    if in_use:
        raise HTTPException(
            status_code=400,
            detail=f"Conta possui {in_use} lançamento(s) vinculado(s); arquive em vez de excluir.",
        )
    res = await server.db.financial_accounts.delete_one({"id": account_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    return {"ok": True}


@finance_router.get("/accounts/{account_id}/balance")
async def get_account_balance(account_id: str, current_user=Depends(server.get_current_user)):
    acc = await server.db.financial_accounts.find_one({"id": account_id}, {"_id": 0})
    if not acc:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    return {"account_id": account_id, **(await _compute_account_balance(acc))}


@finance_router.get("/summary")
async def get_finance_summary(scope: Optional[str] = None, current_user=Depends(server.get_current_user)):
    """Saldo geral consolidado para a tela inicial do Gerenciador Financeiro (estilo
    "Saldo geral" do Organizze) — soma o saldo de todas as contas não arquivadas."""
    q: Dict[str, Any] = {"archived": {"$ne": True}, **_scope_filter(scope)}
    accounts = await server.db.financial_accounts.find(q, {"_id": 0}).sort("name", 1).to_list(1000)
    total_current = 0.0
    total_forecast = 0.0
    for acc in accounts:
        bal = await _compute_account_balance(acc)
        acc["balance"] = bal
        total_current += bal["current_balance"]
        total_forecast += bal["forecast_balance"]
    overdue_count = await server.db.financial_entries.count_documents({
        **_scope_filter(scope),
        "status": {"$in": PENDING_STATUSES},
        "date": {"$lt": _today_iso()},
    })
    to_categorize_count = await server.db.financial_entries.count_documents({
        **_scope_filter(scope),
        "status": EntryStatus.A_CATEGORIZAR.value,
    })
    return {
        "accounts": accounts,
        "total_current_balance": round(total_current, 2),
        "total_forecast_balance": round(total_forecast, 2),
        "overdue_count": overdue_count,
        "to_categorize_count": to_categorize_count,
    }


# ════════════════════════════════════════════════════════════════════════════
# Categorias (CAT-XXXX)
# ════════════════════════════════════════════════════════════════════════════
@finance_router.get("/categories")
async def list_categories(
    scope: Optional[str] = None,
    kind: Optional[str] = None,
    include_archived: bool = False,
    current_user=Depends(server.get_current_user),
):
    q: Dict[str, Any] = {}
    if scope and scope != Scope.AMBOS.value:
        # PJ ou PF isolado: traz as categorias daquele escopo + eventuais categorias
        # legadas com scope=AMBOS (criadas antes da correção de 2026-06-26, quando
        # "Ambos" ainda gravava uma única categoria compartilhada — ver
        # create_category). Categorias novas nunca são gravadas com scope=AMBOS.
        # scope == AMBOS (visão combinada) ou None = sem filtro, traz todas.
        q["scope"] = {"$in": [scope, Scope.AMBOS.value]}
    if kind:
        q["kind"] = kind
    if not include_archived:
        q["archived"] = {"$ne": True}
    return await server.db.financial_categories.find(q, {"_id": 0}).sort("name", 1).to_list(2000)


def _category_doc(cat_id: str, name: str, kind: str, parent_id: Optional[str], scope: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": cat_id,
        "name": name,
        "kind": kind,
        "parent_id": parent_id,
        "scope": scope,
        "color": payload.get("color"),
        "icon": payload.get("icon"),
        "archived": False,
    }


@finance_router.post("/categories")
async def create_category(payload: Dict[str, Any], current_user=Depends(server.get_current_user)):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome da categoria é obrigatório.")
    try:
        kind = CategoryKind(payload.get("kind"))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Kind inválido: {payload.get('kind')}")
    scope = payload.get("scope", Scope.EMPRESA.value)
    _check_scope(scope)

    parent_id = payload.get("parent_id")
    if parent_id:
        parent = await server.db.financial_categories.find_one({"id": parent_id})
        if not parent:
            raise HTTPException(status_code=400, detail="Categoria pai não encontrada.")

    # "Ambos PF/PJ" na criação é só um atalho de tela: cria DUAS categorias
    # independentes (uma EMPRESA, uma PESSOAL), nunca uma única categoria
    # compartilhada — senão editar/excluir uma afetaria as duas (bug reportado
    # pelo Diego em 2026-06-26). A partir da criação elas não têm mais nenhum
    # vínculo entre si.
    if scope == Scope.AMBOS.value:
        created = []
        for real_scope in (Scope.EMPRESA.value, Scope.PESSOAL.value):
            cat_id = await server._next_id(server.db.financial_categories, "CAT-", 4)
            doc = _category_doc(cat_id, name, kind.value, parent_id, real_scope, payload)
            await server.db.financial_categories.insert_one(doc)
            doc.pop("_id", None)
            created.append(doc)
        return created

    cat_id = await server._next_id(server.db.financial_categories, "CAT-", 4)
    doc = _category_doc(cat_id, name, kind.value, parent_id, scope, payload)
    await server.db.financial_categories.insert_one(doc)
    doc.pop("_id", None)
    return doc


@finance_router.put("/categories/{category_id}")
async def update_category(category_id: str, payload: Dict[str, Any], current_user=Depends(server.get_current_user)):
    existing = await server.db.financial_categories.find_one({"id": category_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")

    update: Dict[str, Any] = {}
    for f in ["name", "color", "icon", "archived"]:
        if f in payload:
            update[f] = payload[f]
    if "scope" in payload:
        new_scope = payload["scope"]
        if new_scope == Scope.AMBOS.value:
            # Categorias já criadas são entidades independentes (ver create_category) —
            # "Ambos" só existe como atalho no momento da criação, nunca como estado de
            # uma categoria já existente.
            raise HTTPException(
                status_code=400,
                detail="Esta categoria já é independente — escolha Empresa ou Pessoal (não é possível voltar a 'Ambos').",
            )
        _check_scope(new_scope)
        update["scope"] = new_scope
    if "kind" in payload:
        try:
            update["kind"] = CategoryKind(payload["kind"]).value
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Kind inválido: {payload['kind']}")
    if "parent_id" in payload:
        parent_id = payload["parent_id"]
        if parent_id == category_id:
            raise HTTPException(status_code=400, detail="Categoria não pode ser pai de si mesma.")
        if parent_id:
            parent = await server.db.financial_categories.find_one({"id": parent_id})
            if not parent:
                raise HTTPException(status_code=400, detail="Categoria pai não encontrada.")
        update["parent_id"] = parent_id

    if update:
        await server.db.financial_categories.update_one({"id": category_id}, {"$set": update})
    return await server.db.financial_categories.find_one({"id": category_id}, {"_id": 0})


@finance_router.delete("/categories/{category_id}")
async def delete_category(category_id: str, current_user=Depends(server.get_current_user)):
    children = await server.db.financial_categories.count_documents({"parent_id": category_id})
    if children:
        raise HTTPException(status_code=400, detail="Categoria possui subcategorias; remova-as primeiro.")
    in_use = await server.db.financial_entries.count_documents({"splits.category_id": category_id})
    if in_use:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria usada em {in_use} lançamento(s); arquive em vez de excluir.",
        )
    res = await server.db.financial_categories.delete_one({"id": category_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    return {"ok": True}


@finance_router.post("/categories/seed")
async def seed_categories(current_user=Depends(server.get_current_user)):
    """Semeia DEFAULT_CATEGORIES se a coleção ainda estiver vazia (idempotente).
    Entradas com scope=AMBOS (ex: "Outras receitas", "Aportes") são semeadas como
    DUAS categorias independentes (EMPRESA + PESSOAL) — mesma regra de
    create_category, para não recriar o bug de categoria compartilhada."""
    existing_count = await server.db.financial_categories.count_documents({})
    if existing_count > 0:
        return {"seeded": 0, "message": "Categorias já existem."}
    created = []
    for c in DEFAULT_CATEGORIES:
        scopes = (Scope.EMPRESA.value, Scope.PESSOAL.value) if c["scope"] == Scope.AMBOS.value else (c["scope"],)
        for sc in scopes:
            cat_id = await server._next_id(server.db.financial_categories, "CAT-", 4)
            await server.db.financial_categories.insert_one({
                "id": cat_id, "name": c["name"], "kind": c["kind"], "parent_id": None,
                "scope": sc, "color": None, "icon": None, "archived": False,
            })
            created.append(cat_id)
    return {"seeded": len(created)}


@finance_router.post("/categories/reset-import")
async def reset_import_categories(current_user=Depends(server.get_current_user)):
    """Apaga TODAS as categorias existentes e recria a árvore definitiva a
    partir de CATEGORY_TREE (ver finance_manager.py).

    Ação explicitamente solicitada por Diego em 2026-06-26: a estrutura de
    categorias mudou (PF/PJ × Receitas/Despesas com hierarquia de
    subcategorias) e o conjunto antigo deve ser substituído por completo, não
    mesclado. Por isso este endpoint ignora as proteções normais de
    `delete_category` (subcategorias e uso em lançamentos) — é uma operação
    de reset deliberada, não uma exclusão item a item.

    Lançamentos existentes que referenciem categorias antigas (via
    `splits[].category_id`) ficam com uma referência órfã após o reset; o
    endpoint reporta quantos lançamentos seriam afetados para que Diego saiba
    se precisa categorizá-los de novo.
    """
    orphaned_entries = await server.db.financial_entries.count_documents(
        {"splits.0": {"$exists": True}}
    )

    deleted = (await server.db.financial_categories.delete_many({})).deleted_count

    created = []
    for node in CATEGORY_TREE:
        parent_id = await server._next_id(server.db.financial_categories, "CAT-", 4)
        await server.db.financial_categories.insert_one({
            "id": parent_id, "name": node["name"], "kind": node["kind"], "parent_id": None,
            "scope": node["scope"], "color": None, "icon": None, "archived": False,
        })
        created.append(parent_id)
        for child_name in node["children"]:
            child_id = await server._next_id(server.db.financial_categories, "CAT-", 4)
            await server.db.financial_categories.insert_one({
                "id": child_id, "name": child_name, "kind": node["kind"], "parent_id": parent_id,
                "scope": node["scope"], "color": None, "icon": None, "archived": False,
            })
            created.append(child_id)

    return {
        "deleted": deleted,
        "created": len(created),
        "entries_with_splits": orphaned_entries,
        "message": (
            f"{deleted} categoria(s) antiga(s) apagada(s), {len(created)} nova(s) criada(s)."
            + (
                f" Atenção: {orphaned_entries} lançamento(s) com categorias já preenchidas"
                " referenciam IDs antigos — revise-os na aba Lançamentos."
                if orphaned_entries else ""
            )
        ),
    }


# ════════════════════════════════════════════════════════════════════════════
# Lançamentos — o AGREGADOR (LCT-XXXX)
# ════════════════════════════════════════════════════════════════════════════
async def _validate_splits(splits):
    for s in splits or []:
        if not s.get("category_id"):
            raise HTTPException(status_code=400, detail="Cada split precisa de category_id.")
        cat = await server.db.financial_categories.find_one({"id": s["category_id"]})
        if not cat:
            raise HTTPException(status_code=400, detail=f"Categoria não encontrada: {s['category_id']}")


@finance_router.get("/entries")
async def list_entries(
    scope: Optional[str] = None,
    status: Optional[str] = None,
    account_id: Optional[str] = None,
    kind: Optional[str] = None,
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    only_overdue: bool = False,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = "date",
    sort_dir: str = "desc",
    limit: int = 500,
    current_user=Depends(server.get_current_user),
):
    filt: Dict[str, Any] = {**_scope_filter(scope)}
    if status:
        filt["status"] = status
    if account_id:
        filt["account_id"] = account_id
    if kind:
        filt["kind"] = kind
    if category_id:
        filt["splits.category_id"] = category_id
    if date_from or date_to:
        rng: Dict[str, Any] = {}
        if date_from:
            rng["$gte"] = date_from
        if date_to:
            rng["$lte"] = date_to
        filt["date"] = rng
    if only_overdue:
        filt["status"] = {"$in": PENDING_STATUSES}
        rng = filt.get("date") if isinstance(filt.get("date"), dict) else {}
        rng["$lt"] = _today_iso()
        filt["date"] = rng
    if search:
        try:
            rx = re.compile(re.escape(search), re.IGNORECASE)
        except re.error:
            rx = None
        if rx:
            filt["$or"] = [
                {"establishment": rx},
                {"notes": rx},
                {"splits.description": rx},
            ]

    sort_field = sort_by if sort_by in ("date", "total_value", "establishment", "created_at") else "date"
    sort_order = 1 if sort_dir == "asc" else -1

    docs = await server.db.financial_entries.find(filt, {"_id": 0}) \
        .sort(sort_field, sort_order).limit(limit).to_list(limit)
    return [_annotate_entry(d) for d in docs]


@finance_router.get("/entries/{entry_id}")
async def get_entry(entry_id: str, current_user=Depends(server.get_current_user)):
    doc = await server.db.financial_entries.find_one({"id": entry_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    return _annotate_entry(doc)


@finance_router.post("/entries")
async def create_entry(payload: Dict[str, Any], current_user=Depends(server.get_current_user)):
    try:
        kind = EntryKind(payload.get("kind"))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Kind inválido: {payload.get('kind')}")
    scope = payload.get("scope", Scope.EMPRESA.value)
    _check_scope(scope)

    account_id = payload.get("account_id")
    if not account_id:
        raise HTTPException(status_code=400, detail="account_id é obrigatório.")
    account = await server.db.financial_accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=400, detail="Conta não encontrada.")

    date_ = payload.get("date")
    if not date_:
        raise HTTPException(status_code=400, detail="date é obrigatório.")

    total_value = float(payload.get("total_value") or 0)
    if total_value <= 0:
        raise HTTPException(status_code=400, detail="total_value deve ser maior que zero.")

    splits = payload.get("splits") or []
    await _validate_splits(splits)

    status = derive_status(total_value, splits, payload.get("status") or EntryStatus.PENDENTE.value)

    entry_id = await server._next_id(server.db.financial_entries, "LCT-", 4)
    doc = {
        "id": entry_id,
        "kind": kind.value,
        "scope": scope,
        "account_id": account_id,
        "date": date_,
        "paid_date": payload.get("paid_date"),
        "establishment": payload.get("establishment"),
        "total_value": round(total_value, 2),
        "payment_method": payload.get("payment_method"),
        "installments": payload.get("installments") or {"n": 1, "total": 1},
        "status": status,
        "splits": splits,
        "source": payload.get("source") or EntrySource.MANUAL.value,
        "openfinance_tx_id": payload.get("openfinance_tx_id"),
        "reconciled": False,
        "invoice_id": payload.get("invoice_id"),
        "attachments": payload.get("attachments") or [],
        "recurring_id": payload.get("recurring_id"),
        "notes": payload.get("notes"),
        "created_at": datetime.utcnow().isoformat(),
    }
    await server.db.financial_entries.insert_one(doc)
    doc.pop("_id", None)
    return doc


@finance_router.put("/entries/{entry_id}")
async def update_entry(entry_id: str, payload: Dict[str, Any], current_user=Depends(server.get_current_user)):
    existing = await server.db.financial_entries.find_one({"id": entry_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")

    update: Dict[str, Any] = {}
    for f in ["date", "paid_date", "establishment", "payment_method", "installments", "source",
              "openfinance_tx_id", "reconciled", "invoice_id", "attachments", "recurring_id", "notes"]:
        if f in payload:
            update[f] = payload[f]
    if "scope" in payload:
        _check_scope(payload["scope"])
        update["scope"] = payload["scope"]
    if "kind" in payload:
        try:
            update["kind"] = EntryKind(payload["kind"]).value
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Kind inválido: {payload['kind']}")
    if "account_id" in payload:
        acc = await server.db.financial_accounts.find_one({"id": payload["account_id"]})
        if not acc:
            raise HTTPException(status_code=400, detail="Conta não encontrada.")
        update["account_id"] = payload["account_id"]

    total_value = float(payload["total_value"]) if "total_value" in payload else float(existing.get("total_value") or 0)
    if "total_value" in payload:
        update["total_value"] = round(total_value, 2)

    splits = payload["splits"] if "splits" in payload else (existing.get("splits") or [])
    if "splits" in payload:
        await _validate_splits(splits)
        update["splits"] = splits

    desired_status = payload.get("status", existing.get("status"))
    update["status"] = derive_status(total_value, splits, desired_status)

    await server.db.financial_entries.update_one({"id": entry_id}, {"$set": update})
    return await server.db.financial_entries.find_one({"id": entry_id}, {"_id": 0})


@finance_router.put("/entries/{entry_id}/splits")
async def update_entry_splits(entry_id: str, payload: Dict[str, Any], current_user=Depends(server.get_current_user)):
    """Substitui as linhas por categoria do lançamento (drawer de divisão)."""
    existing = await server.db.financial_entries.find_one({"id": entry_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")

    splits = payload.get("splits") or []
    await _validate_splits(splits)

    total_value = float(existing.get("total_value") or 0)
    status = derive_status(total_value, splits, existing.get("status"))

    await server.db.financial_entries.update_one(
        {"id": entry_id}, {"$set": {"splits": splits, "status": status}}
    )
    return await server.db.financial_entries.find_one({"id": entry_id}, {"_id": 0})


@finance_router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: str, current_user=Depends(server.get_current_user)):
    res = await server.db.financial_entries.delete_one({"id": entry_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    return {"ok": True}


@finance_router.post("/entries/{entry_id}/confirm-transfer")
async def confirm_transfer(entry_id: str, current_user=Depends(server.get_current_user)):
    """Confirma uma transferência SUGERIDA (transfer_suggested=True, geralmente por
    casamento valor+data — confiança "valor_data", ver finance_import.py) como
    transferência interna de fato. Promove is_internal_transfer=True (passa a ser
    excluída de relatórios de receita/despesa) e PAGO, e — se houver um par
    espelho (transfer_with_entry_id) — confirma o outro lado também, já que os
    dois lançamentos representam a mesma transferência."""
    entry = await server.db.financial_entries.find_one({"id": entry_id})
    if not entry:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    if not entry.get("transfer_suggested") and not entry.get("transfer_with_account_id"):
        raise HTTPException(status_code=400, detail="Este lançamento não tem transferência sugerida/detectada para confirmar.")

    ids_to_confirm = [entry_id]
    mirror_id = entry.get("transfer_with_entry_id")
    if mirror_id:
        ids_to_confirm.append(mirror_id)

    await server.db.financial_entries.update_many(
        {"id": {"$in": ids_to_confirm}},
        {"$set": {"is_internal_transfer": True, "status": EntryStatus.PAGO.value, "transfer_suggested": False}},
    )
    return {"ok": True, "confirmed_entry_ids": ids_to_confirm}


@finance_router.post("/entries/{entry_id}/reject-transfer")
async def reject_transfer(entry_id: str, current_user=Depends(server.get_current_user)):
    """Rejeita uma sugestão de transferência (falso positivo do casamento por
    valor+data — ex.: duas compras coincidentemente do mesmo valor em contas
    diferentes). Volta o lançamento pro fluxo normal (A_CATEGORIZAR) e limpa os
    campos de sugestão, sem apagar o histórico de qual confiança gerou a sugestão
    (fica só em notes, pra auditoria)."""
    entry = await server.db.financial_entries.find_one({"id": entry_id})
    if not entry:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")

    ids_to_reject = [entry_id]
    mirror_id = entry.get("transfer_with_entry_id")
    if mirror_id and entry.get("transfer_suggested"):
        ids_to_reject.append(mirror_id)

    await server.db.financial_entries.update_many(
        {"id": {"$in": ids_to_reject}},
        {"$set": {
            "transfer_suggested": False,
            "is_internal_transfer": False,
            "status": EntryStatus.A_CATEGORIZAR.value,
            "transfer_with_account_id": None,
            "transfer_with_entry_id": None,
        }},
    )
    return {"ok": True, "rejected_entry_ids": ids_to_reject}


@finance_router.post("/entries/import-statement/preview")
async def import_statement_preview(
    account_id: str = Form(...),
    file: UploadFile = File(...),
    current_user=Depends(server.get_current_user),
):
    """Lê o extrato (OFX/QFX/CSV/PDF) e devolve a lista de transações detectadas
    para revisão na tela, SEM gravar nada no banco ainda — ver finance_import.
    preview_transactions(). O usuário revisa/edita cada linha no frontend e
    confirma via POST /entries/import-statement/commit."""
    account = await server.db.financial_accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=400, detail="Conta não encontrada.")

    raw = await file.read()
    try:
        transactions = finance_import.parse_statement_bytes(
            file.filename, raw,
            password=account.get("statement_pdf_password"),
            institution=account.get("institution"),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Falha ao ler o arquivo: {e}")

    result = await finance_import.preview_transactions(account_id, transactions)
    result["source_filename"] = file.filename
    return result


@finance_router.post("/entries/import-statement/commit")
async def import_statement_commit(payload: Dict[str, Any], current_user=Depends(server.get_current_user)):
    """Confirma a importação: recebe de volta as linhas retornadas pelo /preview
    (já revisadas/editadas pelo usuário na tela) e grava como financial_entries.
    Body esperado: { account_id, source_filename, rows: [...] }."""
    account_id = payload.get("account_id")
    rows: List[Dict[str, Any]] = payload.get("rows") or []
    source_filename = payload.get("source_filename") or ""
    if not account_id:
        raise HTTPException(status_code=400, detail="account_id é obrigatório.")
    account = await server.db.financial_accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=400, detail="Conta não encontrada.")

    result = await finance_import.commit_transactions(account_id, rows, source_filename)
    return result


# ── Conciliação com a Agenda (Google Calendar) ────────────────────────────────
# Ver finance_agenda_reconcile.py para o algoritmo de casamento (valor+data do
# "registro de pagamento" no corpo do evento — convenção documentada em
# memory/AGENDA_PADRAO_EVENTOS.md §3/§4c).
@finance_router.get("/entries/agenda-suggestions")
async def agenda_suggestions(
    start_date: str,
    end_date: str,
    scope: Optional[str] = None,
    current_user=Depends(server.get_current_user),
):
    """Sugestões de conciliação entre lançamentos e eventos da Agenda no
    período informado. Não grava nada — o usuário confirma cada sugestão via
    POST /entries/{id}/apply-agenda-match."""
    query: Dict[str, Any] = {"date": {"$gte": start_date, "$lte": end_date}}
    if scope:
        _check_scope(scope)
        query["scope"] = scope
    entries = await server.db.financial_entries.find(query, {"_id": 0}).to_list(2000)

    try:
        events_resp = await server.get_all_calendar_events(start_date, end_date)
    except HTTPException as e:
        # Google Calendar não autenticado, etc. — devolve a mensagem original
        # em vez de quebrar a tela do Gestor Financeiro.
        raise HTTPException(status_code=400, detail=f"Agenda indisponível: {e.detail}")
    events = events_resp.get("events", [])

    suggestions = finance_agenda_reconcile.suggest_matches(entries, events)
    return {"suggestions": suggestions, "entries_checked": len(entries), "events_checked": len(events)}


@finance_router.post("/entries/{entry_id}/apply-agenda-match")
async def apply_agenda_match(entry_id: str, payload: Dict[str, Any], current_user=Depends(server.get_current_user)):
    """Confirma manualmente uma sugestão de conciliação com a Agenda: grava o
    título do evento como referência no lançamento (`agenda_event_title`)."""
    event_title = payload.get("event_title")
    event_id = payload.get("event_id")
    if not event_title:
        raise HTTPException(status_code=400, detail="event_title é obrigatório.")
    existing = await server.db.financial_entries.find_one({"id": entry_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")

    await server.db.financial_entries.update_one(
        {"id": entry_id},
        {"$set": {"agenda_event_id": event_id, "agenda_event_title": event_title}},
    )
    return await server.db.financial_entries.find_one({"id": entry_id}, {"_id": 0})


@finance_router.post("/entries/{entry_id}/clear-agenda-match")
async def clear_agenda_match(entry_id: str, current_user=Depends(server.get_current_user)):
    """Desfaz uma conciliação de agenda confirmada por engano."""
    existing = await server.db.financial_entries.find_one({"id": entry_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")

    await server.db.financial_entries.update_one(
        {"id": entry_id},
        {"$set": {"agenda_event_id": None, "agenda_event_title": None}},
    )
    return await server.db.financial_entries.find_one({"id": entry_id}, {"_id": 0})
