"""
SuperDry — Gestor Financeiro — Poller de e-mail para extratos (OFX/CSV)
=========================================================================

Implementa a "Fase 5 alternativa" combinada com Diego em 2026-06-26 (ver
memory/GESTOR_FINANCEIRO.md §18): em vez de pagar por Open Finance
(Pluggy/Belvo), o sistema fica de olho numa caixa de e-mail dedicada. Sempre
que chega um e-mail com anexo de extrato (.ofx/.qfx/.csv) — seja porque o
banco manda automaticamente, seja porque alguém encaminhou manualmente o
arquivo baixado do internet banking — o anexo é baixado, identificado (de
qual conta é) e importado via finance_import.import_transactions().

Ativação: só roda se a variável STATEMENT_EMAIL_USER estiver definida no
.env. Sem isso, o loop nem inicia (ver server.py, startup_bootstrap).

Configuração necessária no .env:
    STATEMENT_EMAIL_HOST=imap.gmail.com
    STATEMENT_EMAIL_USER=algumacoisa@gmail.com
    STATEMENT_EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   (senha de app do Gmail, não a senha normal)
    STATEMENT_EMAIL_FOLDER=Extratos                     (label/pasta a vigiar; default INBOX)
    STATEMENT_IMPORT_INTERVAL_MINUTES=30                 (default 30)

Como o sistema decide de qual conta (financial_accounts) é o extrato:
    Casa o remetente OU o assunto do e-mail (case-insensitive, substring)
    contra o campo `institution` de cada conta cadastrada em
    financial_accounts. Ex.: conta com institution="Nubank" casa com
    e-mails de @nubank.com.br ou que mencionem "Nubank" no assunto.
    Se não achar nenhuma conta correspondente, o e-mail é pulado (fica
    marcado como não lido, pra não se perder) e um aviso é logado.
"""
import asyncio
import email
import imaplib
import logging
import os
import re
from email.message import Message
from typing import List, Optional, Tuple

import finance_import

logger = logging.getLogger("email_statement_poller")

ATTACHMENT_EXTENSIONS = (".ofx", ".qfx", ".csv")


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, default)


def is_configured() -> bool:
    return bool(_env("STATEMENT_EMAIL_USER") and _env("STATEMENT_EMAIL_APP_PASSWORD"))


def _decode_subject(raw_subject) -> str:
    parts = email.header.decode_header(raw_subject or "")
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _extract_attachments(msg: Message) -> List[Tuple[str, bytes]]:
    out = []
    for part in msg.walk():
        filename = part.get_filename()
        if not filename:
            continue
        if not filename.lower().endswith(ATTACHMENT_EXTENSIONS):
            continue
        payload = part.get_payload(decode=True)
        if payload:
            out.append((filename, payload))
    return out


async def _match_account(server_module, sender: str, subject: str) -> Optional[dict]:
    accounts = await server_module.db.financial_accounts.find(
        {"archived": {"$ne": True}}, {"_id": 0}
    ).to_list(1000)
    haystack = f"{sender} {subject}".lower()
    for acc in accounts:
        inst = (acc.get("institution") or "").strip().lower()
        if inst and inst in haystack:
            return acc
    return None


def _fetch_unseen_blocking(host: str, user: str, password: str, folder: str):
    """Parte bloqueante (imaplib não é async) — roda em thread separada via
    run_in_executor. Retorna lista de (msg_id, email.message.Message)."""
    conn = imaplib.IMAP4_SSL(host)
    conn.login(user, password)
    conn.select(folder)
    try:
        status, data = conn.search(None, "UNSEEN")
        if status != "OK":
            return conn, []
        ids = data[0].split()
        messages = []
        for msg_id in ids:
            status, msg_data = conn.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            raw = msg_data[0][1]
            messages.append((msg_id, email.message_from_bytes(raw)))
        return conn, messages
    except Exception:
        conn.logout()
        raise


def _mark_seen_blocking(conn, msg_id):
    conn.store(msg_id, "+FLAGS", "\\Seen")


async def poll_once() -> dict:
    """Uma passada: conecta, processa e-mails não lidos com anexo de extrato,
    importa o que reconhecer, marca como lido. Retorna um resumo pra log."""
    import server  # import tardio — mesmo padrão do resto do módulo financeiro

    host = _env("STATEMENT_EMAIL_HOST", "imap.gmail.com")
    user = _env("STATEMENT_EMAIL_USER")
    password = _env("STATEMENT_EMAIL_APP_PASSWORD")
    folder = _env("STATEMENT_EMAIL_FOLDER", "INBOX")

    loop = asyncio.get_event_loop()
    conn, messages = await loop.run_in_executor(
        None, _fetch_unseen_blocking, host, user, password, folder
    )

    summary = {"emails_vistos": len(messages), "anexos_importados": 0, "anexos_ignorados": 0, "erros": []}
    try:
        for msg_id, msg in messages:
            sender = msg.get("From", "")
            subject = _decode_subject(msg.get("Subject", ""))
            attachments = _extract_attachments(msg)
            if not attachments:
                # E-mail sem anexo de extrato — marca como lido e segue.
                await loop.run_in_executor(None, _mark_seen_blocking, conn, msg_id)
                continue

            account = await _match_account(server, sender, subject)
            if not account:
                logger.warning(
                    "Extrato recebido (assunto=%r, de=%r) mas nenhuma conta com institution "
                    "correspondente foi encontrada — e-mail deixado como não lido.",
                    subject, sender,
                )
                summary["anexos_ignorados"] += len(attachments)
                continue  # não marca como lido — fica pendente pra revisão manual

            ok_all = True
            for filename, content in attachments:
                try:
                    transactions = finance_import.parse_statement_bytes(
                        filename, content,
                        password=account.get("statement_pdf_password"),
                        institution=account.get("institution"),
                    )
                    result = await finance_import.import_transactions(
                        account["id"], transactions, filename
                    )
                    summary["anexos_importados"] += 1
                    logger.info(
                        "Importado %s para conta %s: %s", filename, account["id"], result
                    )
                except Exception as e:
                    ok_all = False
                    summary["erros"].append(f"{filename}: {e}")
                    logger.exception("Erro importando %s", filename)

            if ok_all:
                await loop.run_in_executor(None, _mark_seen_blocking, conn, msg_id)
    finally:
        conn.logout()

    return summary


async def poller_loop():
    """Loop infinito, iniciado em startup_bootstrap() do server.py só se
    is_configured() for True. Intervalo configurável via
    STATEMENT_IMPORT_INTERVAL_MINUTES (default 30 min)."""
    interval_minutes = float(_env("STATEMENT_IMPORT_INTERVAL_MINUTES", "30"))
    logger.info(
        "Poller de extrato por e-mail iniciado (caixa=%s, pasta=%s, intervalo=%smin).",
        _env("STATEMENT_EMAIL_USER"), _env("STATEMENT_EMAIL_FOLDER", "INBOX"), interval_minutes,
    )
    while True:
        try:
            summary = await poll_once()
            if summary["emails_vistos"]:
                logger.info("Poll de extrato concluído: %s", summary)
        except Exception:
            logger.exception("Erro no poll de extrato por e-mail.")
        await asyncio.sleep(interval_minutes * 60)
