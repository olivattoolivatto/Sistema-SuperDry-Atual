#!/usr/bin/env python3
"""
SuperDry — Coleta de eventos do Google Calendar + dados de pagamento pendente.

Rode na Oracle VM (ou localmente onde o MongoDB esteja rodando):
    cd /caminho/do/backend
    python3 fetch_calendar_report.py

Saída: /tmp/superdry_calendar_report.json
       (copie esse arquivo para a pasta OneDrive do projeto para análise)

Dependências (já instaladas na VM via requirements.txt):
    pymongo, google-api-python-client, google-auth, google-auth-oauthlib
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

# --------------------------------------------------------------------------- #
# CONFIGURAÇÃO — ajuste se necessário
# --------------------------------------------------------------------------- #
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME   = os.environ.get("DB_NAME",   "superdry")
OUTPUT    = os.environ.get("OUTPUT",    "/tmp/superdry_calendar_report.json")
# Janela de eventos: 12 meses atrás até 6 meses à frente
MONTHS_BACK    = 12
MONTHS_FORWARD = 6
# --------------------------------------------------------------------------- #

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def get_mongo_db():
    from pymongo import MongoClient
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")   # lança exceção se não conectar
    return client[DB_NAME]


def get_calendar_service(creds_dict):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    import google.auth.transport.requests

    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    creds = Credentials(
        token=creds_dict.get("token"),
        refresh_token=creds_dict.get("refresh_token"),
        token_uri=creds_dict.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=creds_dict.get("client_id"),
        client_secret=creds_dict.get("client_secret"),
        scopes=creds_dict.get("scopes", SCOPES),
    )
    # Renova o access token se expirado
    if creds.expired and creds.refresh_token:
        log("Token expirado — renovando...")
        request = google.auth.transport.requests.Request()
        creds.refresh(request)
        log("Token renovado.")
    return build("calendar", "v3", credentials=creds)


def fetch_all_events(service, time_min: datetime, time_max: datetime):
    """Busca todos os eventos com paginação."""
    events = []
    page_token = None
    time_min_iso = time_min.isoformat()
    time_max_iso = time_max.isoformat()

    while True:
        kwargs = dict(
            calendarId="primary",
            timeMin=time_min_iso,
            timeMax=time_max_iso,
            maxResults=250,
            singleEvents=True,
            orderBy="startTime",
        )
        if page_token:
            kwargs["pageToken"] = page_token

        result = service.events().list(**kwargs).execute()
        batch = result.get("items", [])
        events.extend(batch)
        log(f"  Página recebida: {len(batch)} eventos (total até agora: {len(events)})")

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return events


def normalize_event(ev):
    """Extrai apenas os campos relevantes de um evento bruto."""
    start = ev.get("start", {})
    end   = ev.get("end",   {})
    return {
        "id":          ev.get("id"),
        "summary":     ev.get("summary", "(sem título)"),
        "description": ev.get("description", ""),
        "location":    ev.get("location", ""),
        "colorId":     ev.get("colorId"),      # None = cor padrão do calendário
        "status":      ev.get("status"),
        "start_dt":    start.get("dateTime") or start.get("date"),
        "end_dt":      end.get("dateTime")   or end.get("date"),
        "html_link":   ev.get("htmlLink"),
        "attendees":   [a.get("email") for a in ev.get("attendees", [])],
        "extended":    ev.get("extendedProperties", {}).get("private", {}),
    }


def fetch_payment_data(db):
    """
    Retorna dois dicionários:
        paid_item_ids   → set de IDs de budget_items com pagamento confirmado
        pending_items   → lista de itens entregues/executados sem pagamento
    """
    # Itens com payment_status = PAGO
    paid_cursor = db.budget_items.find(
        {"payment_status": "PAGO"},
        {"_id": 0, "id": 1}
    )
    paid_ids = {doc["id"] for doc in paid_cursor}

    # Itens que terminaram (ENTREGUE, EXECUTADO, BUSCOU) mas não estão pagos
    terminal_statuses = ["ENTREGUE", "EXECUTADO", "BUSCOU"]
    unpaid_cursor = db.budget_items.find(
        {
            "status": {"$in": terminal_statuses},
            "payment_status": {"$nin": ["PAGO", "CORTESIA"]},
        },
        {
            "_id": 0,
            "id": 1,
            "budget_id": 1,
            "service_name": 1,
            "status": 1,
            "payment_status": 1,
            "final_price": 1,
            "execution_date": 1,
            "client_name": 1,
        }
    )
    pending = list(unpaid_cursor)

    # Orçamentos pendentes de pagamento (status != PAGO/CORTESIA) com valor total
    unpaid_budgets_cursor = db.budgets.find(
        {"payment_status": {"$nin": ["PAGO", "CORTESIA"]}},
        {
            "_id": 0,
            "id": 1,
            "client_name": 1,
            "total_price": 1,
            "payment_status": 1,
            "created_at": 1,
        }
    )
    unpaid_budgets = list(unpaid_budgets_cursor)

    return paid_ids, pending, unpaid_budgets


def main():
    # 1. Conecta ao MongoDB
    log("Conectando ao MongoDB...")
    try:
        db = get_mongo_db()
        log(f"MongoDB OK — banco '{DB_NAME}'")
    except Exception as e:
        log(f"ERRO ao conectar ao MongoDB: {e}")
        sys.exit(1)

    # 2. Recupera credenciais do Google Calendar
    log("Buscando credenciais do Google Calendar...")
    creds_doc = db.calendar_credentials.find_one({})
    if not creds_doc:
        log("ERRO: nenhuma credencial encontrada em calendar_credentials.")
        log("Acesse o sistema → Agenda → 'Conectar Google Calendar' e refaça a autenticação.")
        sys.exit(1)

    creds_dict = creds_doc.get("credentials") or creds_doc
    log("Credenciais encontradas. Construindo serviço do Calendar...")

    # 3. Constrói o serviço do Google Calendar
    try:
        service = get_calendar_service(creds_dict)
        log("Serviço do Google Calendar pronto.")
    except Exception as e:
        log(f"ERRO ao construir serviço Calendar: {e}")
        sys.exit(1)

    # 4. Busca eventos
    now   = datetime.now(timezone.utc)
    t_min = now - timedelta(days=30 * MONTHS_BACK)
    t_max = now + timedelta(days=30 * MONTHS_FORWARD)
    log(f"Buscando eventos de {t_min.date()} a {t_max.date()}...")

    try:
        raw_events = fetch_all_events(service, t_min, t_max)
        log(f"Total de eventos recebidos: {len(raw_events)}")
    except Exception as e:
        log(f"ERRO ao buscar eventos: {e}")
        sys.exit(1)

    events = [normalize_event(ev) for ev in raw_events]

    # 5. Dados de pagamento do MongoDB
    log("Consultando dados de pagamento no MongoDB...")
    paid_ids, pending_items, unpaid_budgets = fetch_payment_data(db)
    log(f"  IDs pagos: {len(paid_ids)}")
    log(f"  Itens pendentes de pagamento: {len(pending_items)}")
    log(f"  Orçamentos não quitados: {len(unpaid_budgets)}")

    # 6. Estatísticas rápidas
    red_events   = [e for e in events if e["colorId"] == "11"]
    no_color     = [e for e in events if e["colorId"] is None]
    other_colors = [e for e in events if e["colorId"] not in (None, "11")]

    log(f"  Eventos vermelhos (colorId=11/Tomato): {len(red_events)}")
    log(f"  Eventos sem cor explícita (padrão): {len(no_color)}")
    log(f"  Eventos com outra cor: {len(other_colors)}")

    # 7. Monta saída
    report = {
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "window_start":     t_min.isoformat(),
        "window_end":       t_max.isoformat(),
        "total_events":     len(events),
        "events":           events,
        "pending_payment_items":   pending_items,
        "unpaid_budgets":          unpaid_budgets,
        "color_legend": {
            "null": "Cor padrão do calendário (amarelo no SuperDry = colorId 5)",
            "5":    "Banana/Amarelo — agendamento padrão",
            "11":   "Tomate/Vermelho — marcado como inadimplente manualmente",
            "9":    "Mirtilo/Azul",
            "1":    "Lavanda",
            "2":    "Sálvia",
            "3":    "Uva/Roxo",
            "4":    "Flamingo/Rosa",
            "6":    "Tangerina/Laranja",
            "7":    "Pavão/Ciano",
            "8":    "Grafite/Cinza",
            "10":   "Manjericão/Verde escuro",
        },
    }

    # 8. Salva JSON
    log(f"Salvando relatório em {OUTPUT}...")
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    log(f"Arquivo salvo: {OUTPUT}")
    log("Pronto! Copie o arquivo para a pasta do projeto e avise o Claude.")
    log(f"  scp opc@148.116.108.43:{OUTPUT} .")


if __name__ == "__main__":
    main()
