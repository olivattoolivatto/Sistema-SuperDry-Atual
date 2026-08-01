"""
SuperDry — Gestor Financeiro — Conciliação com a Agenda (Google Calendar)
===========================================================================

Pedido do dono (23/06/26): cruzar lançamentos financeiros com eventos da
Agenda para confirmar a que serviço cada pagamento se refere — ver
memory/AGENDA_PADRAO_EVENTOS.md §3 "Registro de pagamento" e §4c "Formas de
pagamento (registro na agenda)" para o formato usado no corpo dos eventos:

    [código] [valor] [data]
    ex.: "PixNuSuperDry 1937,00 23/6/26"

Essa linha, quando presente na descrição de um evento, registra que aquele
serviço foi pago via [código] no valor X na data Y — geralmente uns dias
diferente da data do próprio agendamento (o evento marca quando o técnico vai
lá; o pagamento pode ter sido feito antes ou depois). Conciliamos casando esse
valor+data contra os `financial_entries` já importados do extrato bancário.

Exemplo real (dono, 23/06/26): lançamento bancário "Transferência recebida
pelo Pix - FERNANDO EUGENIO MEYER ... R$ 1.937,00" em 23/06, evento da agenda
"🪑 Fernando Eugênio Meyer" (25/06) com a linha "PixNuSuperDry 1937,00 23/6/26"
no corpo → o pagamento foi feito em 23/06 (data do lançamento bancário), mesmo
o evento estando agendado pra 25/06.

Este módulo só SUGERE casamentos (não grava nada sozinho) — a confirmação é
manual via endpoint em finance_routes.py, no mesmo espírito da camada 3 de
detecção de transferência em finance_import.py (_suggest_value_date_transfers).
"""
import re
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional

# Linha de registro de pagamento no corpo do evento: "<código> <valor> <data>"
# (às vezes com um token extra de parcelas entre código e valor, ex.:
# "Cartão 2x 340,00 10/6/26" — ver AGENDA_PADRAO_EVENTOS.md §4c).
_PAYMENT_LINE_RE = re.compile(
    r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9]*(?:\s+\d+x)?)\s+"
    r"(\d{1,3}(?:\.\d{3})*,\d{2})\s+"
    r"(\d{1,2}/\d{1,2}/\d{2,4})"
)


def _parse_brl_value(raw: str) -> Optional[float]:
    try:
        return float(raw.replace(".", "").replace(",", "."))
    except (ValueError, AttributeError):
        return None


def _parse_br_date(raw: str) -> Optional[str]:
    """'23/6/26' ou '23/06/2026' → '2026-06-23'."""
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", raw)
    if not m:
        return None
    day, month, year = m.groups()
    year_i = int(year)
    if year_i < 100:
        year_i += 2000
    try:
        return datetime(year_i, int(month), int(day)).strftime("%Y-%m-%d")
    except ValueError:
        return None


def extract_payment_registration(description: Optional[str]) -> Optional[Dict[str, Any]]:
    """Acha a ÚLTIMA ocorrência no formato '<código> <valor> <data>' na
    descrição do evento (o registro de pagamento aparece no final do corpo,
    depois das anotações de serviço — ver AGENDA_PADRAO_EVENTOS.md §3)."""
    if not description:
        return None
    matches = list(_PAYMENT_LINE_RE.finditer(description))
    if not matches:
        return None
    m = matches[-1]
    method_label, value_raw, date_raw = m.groups()
    value = _parse_brl_value(value_raw)
    date_iso = _parse_br_date(date_raw)
    if value is None or not date_iso:
        return None
    return {"method_label": method_label.strip(), "value": value, "date": date_iso, "raw": m.group(0)}


def _strip_emojis_and_actions(summary: str) -> str:
    """Remove emojis/pontuação e palavras de ação ('retirar', 'entregar' etc.)
    do título, deixando só o nome do cliente (ver AGENDA_PADRAO_EVENTOS.md §2)."""
    text = re.sub(r"[^\w\sÀ-ÿ/]", " ", summary or "")
    for action in ("retirar", "retirada", "entregar", "entrega"):
        text = re.sub(rf"\b{action}\b", " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_name(name: Optional[str]) -> str:
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_only.upper()).strip()


def _names_overlap(a: str, b: str) -> bool:
    """True se houver ao menos uma palavra significativa (>=4 letras) em comum
    entre os dois nomes normalizados. Só reforça a confiança de um match já
    encontrado por valor+data — nomes em extrato bancário costumam vir
    truncados/diferentes do nome usado na agenda, então não decide sozinho."""
    wa = {w for w in _normalize_name(a).split() if len(w) >= 4}
    wb = {w for w in _normalize_name(b).split() if len(w) >= 4}
    return bool(wa & wb)


_VALUE_TOLERANCE = 0.01
_DATE_WINDOW_DAYS = 5


def suggest_matches(entries: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Para cada lançamento ainda sem conciliação de agenda (`agenda_event_id`
    vazio), procura o evento cujo registro de pagamento (valor+data) bate.
    Não grava nada — devolve sugestões pra confirmação manual via
    POST /entries/{id}/apply-agenda-match (finance_routes.py)."""
    registrations = []
    for ev in events:
        reg = extract_payment_registration(ev.get("description"))
        if reg:
            registrations.append({
                **reg,
                "event_id": ev.get("google_event_id") or ev.get("id"),
                "event_title": ev.get("summary"),
            })

    suggestions: List[Dict[str, Any]] = []
    for entry in entries:
        if entry.get("agenda_event_id"):
            continue  # já conciliado manualmente antes

        entry_value = round(abs(float(entry.get("total_value") or 0)), 2)
        if entry_value == 0:
            continue
        entry_date = entry.get("paid_date") or entry.get("date")
        if not entry_date:
            continue
        try:
            entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
        except ValueError:
            continue

        best = None
        for reg in registrations:
            if abs(reg["value"] - entry_value) > _VALUE_TOLERANCE:
                continue
            reg_dt = datetime.strptime(reg["date"], "%Y-%m-%d")
            diff_days = abs((reg_dt - entry_dt).days)
            if diff_days > _DATE_WINDOW_DAYS:
                continue

            name_match = _names_overlap(
                entry.get("establishment") or "",
                _strip_emojis_and_actions(reg.get("event_title") or ""),
            )
            confidence = "valor_data_exato" if diff_days == 0 else "valor_data_proximo"
            if name_match:
                confidence += "_nome"
            score = (0 if diff_days == 0 else 1, 0 if name_match else 1, diff_days)

            if best is None or score < best["_score"]:
                best = {
                    "entry_id": entry["id"],
                    "entry_establishment": entry.get("establishment"),
                    "entry_value": entry_value,
                    "entry_date": entry_date,
                    "event_id": reg["event_id"],
                    "event_title": reg["event_title"],
                    "payment_value": reg["value"],
                    "payment_date": reg["date"],
                    "date_diff_days": diff_days,
                    "name_match": name_match,
                    "confidence": confidence,
                    "_score": score,
                }
        if best:
            best.pop("_score", None)
            suggestions.append(best)

    return suggestions
