"""
SuperDry — Gestor Financeiro — Importador de extrato (OFX/CSV)
================================================================

Caminho "gratuito" de conciliação bancária, alternativo ao Open Finance pago
(Pluggy/Belvo) — ver memory/GESTOR_FINANCEIRO.md §18. Em vez de webhook em
tempo real, o sistema lê arquivos de extrato (formato OFX, padrão usado por
todo internet banking brasileiro na opção "exportar para contabilidade", ou
CSV exportado pelo banco/InfinitePay) e cria os `financial_entries`
automaticamente, com dedupe.

Duas portas de entrada usam este módulo:
  1. POST /api/finance/entries/import-statement — upload manual (fallback).
  2. email_statement_poller.py — caixa de e-mail dedicada, fluxo automático.

Import tardio de `server` (mesmo padrão de finance_routes.py) para evitar
import circular.
"""
import csv
import hashlib
import io
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from finance_manager import EntryKind, EntrySource, EntryStatus

# ofxparse é opcional — só é necessário se algum extrato OFX for importado.
try:
    from ofxparse import OfxParser
except ImportError:  # pragma: no cover
    OfxParser = None

# pdfplumber é opcional — só necessário pros bancos "dinossauro" que só mandam
# PDF (Caixa, C6, MercadoPago, 99Pay — ver memory/GESTOR_FINANCEIRO.md §19/§20).
try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

# pytesseract é opcional — só necessário para o extrato da Caixa, que é PDF
# escaneado (imagem, sem texto real). Ver §23 do GESTOR_FINANCEIRO.md. Exige
# também o binário `tesseract-ocr` (+ idioma `tesseract-ocr-por`) instalado no
# sistema operacional da VM — não é instalável via pip.
try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None


# Termos que identificam uma linha de SALDO (não é uma transação real, é um
# instantâneo de saldo que alguns bancos intercalam no meio do extrato — ver
# achado em memory/GESTOR_FINANCEIRO.md §22.2.1/§22.5). Comparar sempre contra
# texto sem acento e em minúsculas (ver `_strip_accents`/`_normalize_header`).
BALANCE_LINE_TERMS = ("saldo anterior", "saldo do dia", "saldo dia", "saldo bloqueado")


def _is_balance_line(description: Optional[str]) -> bool:
    norm = _strip_accents((description or "")).strip().lower()
    return any(term in norm for term in BALANCE_LINE_TERMS)


# ── Parsers ───────────────────────────────────────────────────────────────────
def parse_ofx_bytes(data: bytes) -> List[Dict[str, Any]]:
    """Extrai transações de um arquivo OFX/QFX. Formato padrão e estável —
    todo banco brasileiro oferece essa exportação no internet banking."""
    if OfxParser is None:
        raise RuntimeError(
            "Biblioteca 'ofxparse' não instalada. Rode: pip install ofxparse"
        )
    ofx = OfxParser.parse(io.BytesIO(data))
    out = []
    for account in ofx.accounts:
        statement = getattr(account, "statement", None)
        if not statement:
            continue
        for tx in statement.transactions:
            # NAME (payee) e MEMO são concatenados, não escolhidos com "ou" —
            # achado real (memory/GESTOR_FINANCEIRO.md §22.2.3): no Banco do
            # Brasil o NAME traz um resumo curto ("Pix - Recebido") e é o MEMO
            # que carrega o CPF/CNPJ da contraparte ("...25995295000104...").
            # Usar só o NAME (como antes) descartava o MEMO sempre que o NAME
            # existia, quebrando a detecção de transferência entre contas
            # próprias (_extract_match_keys, que varre a descrição por
            # documento) para extratos BB.
            payee = (getattr(tx, "payee", None) or "").strip()
            memo = (getattr(tx, "memo", None) or "").strip()
            description = " - ".join(p for p in (payee, memo) if p and p != payee) if memo != payee else payee
            description = description or payee or memo
            if _is_balance_line(payee) or _is_balance_line(description):
                # "Saldo Anterior"/"Saldo do dia" (BB) — não são transações
                # reais, são instantâneos de saldo intercalados no extrato.
                continue
            out.append({
                "tx_id": getattr(tx, "id", None),  # FITID — único por transação, estável
                "date": tx.date.date().isoformat() if hasattr(tx.date, "date") else str(tx.date),
                "amount": float(tx.amount),
                "description": description,
            })
    return out


# Nomes de coluna aceitos (minúsculo, sem acento) por campo — cobre os layouts
# mais comuns de exportação de banco/InfinitePay/Nubank PJ/PicPay.
_CSV_FIELD_ALIASES = {
    "date": ["data", "date", "data lancamento", "data da transacao"],
    "amount": ["valor", "amount", "value", "valor (r$)"],
    "description": ["descricao", "description", "historico", "title", "identificador", "detalhes", "origem / destino", "origem/destino"],
    "tx_id": ["identificador", "id", "fitid", "codigo"],
    # PicPay separa "tipo" (Pix recebido/Pagamento realizado/Compra realizada) da
    # "origem / destino" (contraparte) em duas colunas — concatenadas na descrição
    # final do mesmo jeito que NAME+MEMO no OFX do BB (ver parse_ofx_bytes).
    "type": ["tipo", "type"],
}


def _strip_accents(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _normalize_header(h: str) -> str:
    return _strip_accents(h or "").strip().lower()


def parse_csv_bytes(data: bytes) -> List[Dict[str, Any]]:
    """Parser genérico por nome de coluna (não por posição) — funciona com o
    CSV de extrato do Nubank PJ, InfinitePay ou qualquer banco que exporte
    Data/Valor/Descrição, em qualquer ordem de coluna."""
    text = data.decode("utf-8-sig", errors="replace")
    # Detecta separador (; é comum em export de banco BR, , é o padrão internacional)
    sample = text[:2000]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("CSV sem cabeçalho reconhecível.")

    norm_to_original = {_normalize_header(f): f for f in reader.fieldnames}

    def find_col(field: str) -> Optional[str]:
        for alias in _CSV_FIELD_ALIASES[field]:
            if alias in norm_to_original:
                return norm_to_original[alias]
        return None

    col_date = find_col("date")
    col_amount = find_col("amount")
    col_desc = find_col("description")
    col_id = find_col("tx_id")
    col_type = find_col("type")
    if not col_date or not col_amount:
        raise ValueError(
            f"Não encontrei colunas de Data/Valor no CSV. Cabeçalho recebido: {reader.fieldnames}"
        )

    out = []
    for row in reader:
        amount = _parse_csv_amount(row.get(col_amount))
        if amount is None:
            continue
        date_raw = (row.get(col_date) or "").strip()
        date_iso = _normalize_date(date_raw)
        tipo = (row.get(col_type) or "").strip() if col_type else ""
        contraparte = (row.get(col_desc) or "").strip()
        # Concatena "tipo" + "origem/destino" do PicPay (mesmo padrão NAME+MEMO do
        # BB em parse_ofx_bytes) — sozinho, "origem/destino" às vezes é só um nome
        # genérico ("Fatura PicPay Card") sem dizer que é um pagamento de fatura.
        description = " - ".join(dict.fromkeys(p for p in (tipo, contraparte) if p))
        out.append({
            "tx_id": (row.get(col_id) or "").strip() or None,
            "date": date_iso,
            "amount": amount,
            "description": description,
        })
    return out


def _parse_csv_amount(raw: Optional[str]) -> Optional[float]:
    """Converte valor de coluna CSV pra float, tolerando os formatos reais vistos:
    '1234.56' (internacional), '1.234,56' (BR), 'R$ 1.234,56', '-R$ 1.234,56' e
    '−R$ 1.234,56' (achado real — PicPay usa o caractere MINUS SIGN Unicode U+2212
    antes do "R$", em vez do hífen comum "-" U+002D, que o float() do Python não
    aceita; e deixa um espaço entre o sinal/R$ e o número, que também quebra o
    float() se não for removido). Por isso a limpeza é: normaliza o sinal Unicode,
    remove "R$", remove TODO espaço interno (não só as bordas) e só então resolve
    o separador decimal BR."""
    raw_amount = (raw or "0").strip()
    if not raw_amount:
        return 0.0
    raw_amount = raw_amount.replace("−", "-")  # MINUS SIGN -> hífen comum
    raw_amount = raw_amount.replace("R$", "")
    raw_amount = re.sub(r"\s+", "", raw_amount)  # remove espaço entre sinal/R$ e o número
    if "," in raw_amount and raw_amount.count(",") == 1:
        raw_amount = raw_amount.replace(".", "").replace(",", ".")
    try:
        return float(raw_amount)
    except ValueError:
        return None


def _normalize_date(raw: str) -> str:
    """Aceita DD/MM/AAAA, AAAA-MM-DD, etc. Mantém a string original se não reconhecer."""
    raw = raw.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return raw


# ── PDF (Caixa, C6, MercadoPago, 99Pay — bancos que só mandam PDF) ────────────
# Extrato em PDF não tem um formato estruturado como OFX/CSV — cada banco usa
# um layout de texto diferente. Por isso o parser é "por linha": cada linha do
# texto extraído é testada contra um padrão genérico de
# "data ... descrição ... valor", o que cobre razoavelmente bem os extratos
# brasileiros mais comuns. Se um banco específico tiver um layout que o
# genérico não capture bem, dá pra registrar um parser dedicado em
# PDF_LINE_PARSERS (chave = nome da instituição, igual ao campo `institution`
# da conta) sem afetar os demais.
_RE_PDF_DATE = re.compile(r"^\s*(\d{2}/\d{2}/\d{2,4})\b")
_RE_PDF_VALUE = re.compile(r"(-?\d{1,3}(?:\.\d{3})*,\d{2})\s*([CD]?)\s*$")

# Vários extratos brasileiros de fintech (C6, MercadoPago, 99Pay) mostram o
# sinal ANTES do "R$" ("-R$ 8,00", "+R$175,92"), não colado no número como o
# `_RE_PDF_VALUE` genérico espera ("8,00 D"). Achado real testando os PDFs de
# amostra (memory/GESTOR_FINANCEIRO.md §23): nesse formato o "-" nunca chegava
# a ser capturado (ficava antes do "R$", fora do grupo), e todo valor virava
# positivo — quebrando a classificação RECEITA/DESPESA. Este regex cobre as
# duas posições possíveis do sinal.
_RE_SIGNED_RS = re.compile(r"([+-])?\s*R\$\s*(-?\d{1,3}(?:\.\d{3})*,\d{2})")


def _parse_signed_rs(sign: Optional[str], raw: str) -> Optional[float]:
    try:
        value = float(raw.replace(".", "").replace(",", "."))
    except ValueError:
        return None
    if sign == "-" and value > 0:
        value = -value
    return value


def _parse_pdf_amount(raw: str, suffix: str) -> Optional[float]:
    """Converte '1.234,56' (decimal BR) pra float. suffix 'D' força negativo,
    'C' força positivo (alguns extratos marcam débito/crédito por letra em vez
    de sinal — ex.: Caixa)."""
    try:
        value = float(raw.replace(".", "").replace(",", "."))
    except ValueError:
        return None
    if suffix == "D" and value > 0:
        value = -value
    elif suffix == "C" and value < 0:
        value = -value
    return value


def _parse_pdf_lines_generic(text: str) -> List[Dict[str, Any]]:
    """Parser heurístico: linhas que começam com data DD/MM/AAAA (ou AA) e
    terminam com um valor em decimal BR (opcionalmente seguido de C/D) são
    tratadas como transação; o meio da linha é a descrição. Lançamentos
    extraídos assim entram com source=EXTRATO_IMPORT e ficam A_CATEGORIZAR
    como qualquer outro — revisão manual cobre eventuais erros de leitura."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        date_m = _RE_PDF_DATE.match(line)
        if not date_m:
            continue
        # Tenta primeiro o formato "R$ valor" com sinal antes do "R$" (comum
        # em extratos de fintech); se a linha não tiver "R$", cai no formato
        # genérico "1.234,56 D/C" ancorado no final da linha.
        rs_m = _RE_SIGNED_RS.search(line)
        if rs_m:
            amount = _parse_signed_rs(rs_m.group(1), rs_m.group(2))
            desc_end = rs_m.start()
        else:
            value_m = _RE_PDF_VALUE.search(line)
            if not value_m:
                continue
            amount = _parse_pdf_amount(value_m.group(1), value_m.group(2))
            desc_end = value_m.start()
        if amount is None:
            continue
        description = line[date_m.end():desc_end].strip(" -|\t")
        if _is_balance_line(description):
            continue
        out.append({
            "tx_id": None,  # PDF não traz ID estável -> dedupe cai no hash (data+valor+descrição)
            "date": _normalize_date(date_m.group(1)),
            "amount": amount,
            "description": description,
        })
    return out


# ── Parsers dedicados por banco (PDF) ─────────────────────────────────────────
# O genérico acima cobre extratos com 1 data + 1 valor por linha. Os 4 bancos
# que só mandam PDF (Caixa, C6, MercadoPago, 99Pay) têm layouts próprios
# incompatíveis com esse padrão — cada um ganhou um parser dedicado abaixo,
# validado contra amostras reais (memory/GESTOR_FINANCEIRO.md §23).

def _normalize_institution(institution: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]", "", _strip_accents((institution or "")).lower())


# C6 Bank: cada linha de transação tem DUAS datas sem ano ("DD/MM DD/MM"
# — data de lançamento e data contábil), seguidas do tipo+descrição e do
# valor com sinal colado no "R$" ("-R$ 8,00"). O ano não aparece na linha —
# só no cabeçalho do período ("Junho 2026 ( 01/06/2026 - 27/06/2026 )"),
# então é extraído uma vez do texto inteiro e aplicado a todas as linhas.
_RE_C6_PERIOD = re.compile(r"\((\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})\)")
_RE_C6_ROW = re.compile(
    r"^(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+" + _RE_SIGNED_RS.pattern + r"\s*$"
)


def _c6_year_for(month: int, start_month: int, start_year: int, end_year: int) -> int:
    if start_year == end_year:
        return start_year
    return start_year if month >= start_month else end_year


def _parse_pdf_c6(text: str) -> List[Dict[str, Any]]:
    period_m = _RE_C6_PERIOD.search(text)
    if period_m:
        start_month, start_year = int(period_m.group(2)), int(period_m.group(3))
        end_year = int(period_m.group(6))
    else:
        # Sem o cabeçalho de período não há como saber o ano — assume o ano
        # corrente como melhor esforço (extrato deveria sempre trazer o
        # período; isso é só uma rede de segurança).
        start_month, start_year, end_year = 1, datetime.utcnow().year, datetime.utcnow().year

    out = []
    for line in text.splitlines():
        line = line.strip()
        m = _RE_C6_ROW.match(line)
        if not m:
            continue
        day, month = line[:2], line[3:5]
        amount = _parse_signed_rs(m.group(4), m.group(5))
        if amount is None:
            continue
        description = m.group(3).strip()
        if _is_balance_line(description):
            continue
        year = _c6_year_for(int(month), start_month, start_year, end_year)
        out.append({
            "tx_id": None,
            "date": f"{year:04d}-{month}-{day}",
            "amount": amount,
            "description": description,
        })
    return out


# MercadoPago: "DD-MM-YYYY Descrição ID-da-operação R$ valor R$ saldo" — data
# já com ano e separada por hífen (não barra); CADA linha termina com DOIS
# valores em R$ (valor da transação e saldo resultante) — pegar o primeiro
# (valor), não o último (que seria o saldo, achado real de §23).
_RE_MP_ROW = re.compile(
    r"^(\d{2})-(\d{2})-(\d{4})\s+(.+?)\s+(\d{6,})\s+"
    r"([+-]?)\s*R\$\s*(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+"
    r"[+-]?\s*R\$\s*-?\d{1,3}(?:\.\d{3})*,\d{2}\s*$"
)


def _parse_pdf_mercadopago(text: str) -> List[Dict[str, Any]]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        m = _RE_MP_ROW.match(line)
        if not m:
            continue
        day, month, year, description, _op_id, sign, raw_value = m.groups()
        amount = _parse_signed_rs(sign or None, raw_value)
        if amount is None or _is_balance_line(description):
            continue
        out.append({
            "tx_id": None,
            "date": f"{year}-{month}-{day}",
            "amount": amount,
            "description": description.strip(),
        })
    return out


# 99Pay: o ID da transação (numérico longo ou GUID) é mais largo que a coluna
# e "vaza" pra uma linha solta logo abaixo — a linha real da transação é a que
# contém data+hora+valor; a linha órfã seguinte (só dígitos/GUID, sem
# data/hora) é naturalmente ignorada porque não casa com o regex. O início da
# linha real ainda carrega um pedaço do ID antes do tipo de transação — é
# removido da descrição por heurística (prefixo numérico/hex longo).
_RE_99PAY_ROW = re.compile(
    r"^(.*?)(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}:\d{2}\s+" + _RE_SIGNED_RS.pattern + r"\s*$"
)
_RE_99PAY_ID_PREFIX = re.compile(r"^[0-9A-Fa-f-]{8,}\s*")


def _parse_pdf_99pay(text: str) -> List[Dict[str, Any]]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        m = _RE_99PAY_ROW.match(line)
        if not m:
            continue
        lead, date_raw, sign, raw_value = m.groups()
        amount = _parse_signed_rs(sign, raw_value)
        if amount is None:
            continue
        description = _RE_99PAY_ID_PREFIX.sub("", lead).strip(" -|\t")
        if _is_balance_line(description):
            continue
        out.append({
            "tx_id": None,
            "date": _normalize_date(date_raw),
            "amount": amount,
            "description": description,
        })
    return out


# Caixa: o PDF exportado pelo internet banking da Caixa é uma IMAGEM
# (escaneado/print), sem nenhum texto real embutido (confirmado: 0 chars, 1
# imagem por página) — `extract_text()` sempre devolve vazio. É o único dos 4
# "dinossauros" que exige OCR. O texto reconhecido por OCR sai linearizado por
# COLUNA (todas as datas juntas, depois todos os documentos, etc.), não por
# linha de transação — por isso não basta rodar `image_to_string` e tratar
# como texto comum; é necessário reconstruir as linhas a partir da posição
# (x, y) de cada palavra reconhecida (`image_to_data`), agrupando por
# proximidade vertical e ordenando por posição horizontal dentro do grupo.
def _ocr_reconstruct_rows(page, lang: str = "por") -> List[str]:
    if pytesseract is None:
        raise RuntimeError(
            "Biblioteca 'pytesseract' não instalada (rode: pip install pytesseract) "
            "e o binário 'tesseract-ocr' precisa estar instalado no sistema "
            "(+ pacote de idioma 'tesseract-ocr-por' para melhor precisão em PT-BR)."
        )
    image = page.to_image(resolution=300).original
    try:
        data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
    except Exception:
        # Idioma 'por' pode não estar instalado no ambiente (só acontece fora
        # da VM de produção, se Diego instalar o pacote certo) — cai pro
        # inglês, que ainda lê números/datas corretamente.
        data = pytesseract.image_to_data(image, lang="eng", output_type=pytesseract.Output.DICT)

    words = [
        {"text": data["text"][i].strip(), "left": data["left"][i], "top": data["top"][i]}
        for i in range(len(data["text"]))
        if data["text"][i].strip()
    ]
    words.sort(key=lambda w: (w["top"], w["left"]))

    rows: List[List[Dict[str, Any]]] = []
    row_top: Optional[int] = None
    tolerance = 8  # px a 300dpi — tolerância de alinhamento vertical de uma mesma linha
    for w in words:
        if row_top is None or abs(w["top"] - row_top) > tolerance:
            rows.append([w])
            row_top = w["top"]
        else:
            rows[-1].append(w)
            row_top = w["top"]  # acompanha deslocamento gradual da linha

    return [" ".join(w["text"] for w in sorted(row, key=lambda w: w["left"])) for row in rows]


# Linha de transação real da Caixa: "DD/MM/AAAA - HH:MM:SS NrDoc Descrição
# Favorecido CPF/CNPJ Valor C/D Saldo C/D" — pega o PRIMEIRO valor com C/D
# (a transação), não o segundo (o saldo resultante, achado real de §22.5).
_RE_CAIXA_ROW = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s*-?\s*(\d{2}:\d{2}:\d{2})\s+\d+\s+(.+?)\s+"
    r"(-?\d{1,3}(?:\.\d{3})*,\d{2})\s*([CD])\s+"
    r"-?\d{1,3}(?:\.\d{3})*,\d{2}\s*[CD]\s*$"
)


def _parse_pdf_caixa_rows(rows: List[str]) -> List[Dict[str, Any]]:
    out = []
    for row in rows:
        m = _RE_CAIXA_ROW.match(row.strip())
        if not m:
            continue
        date_raw, _time, description, raw_value, suffix = m.groups()
        amount = _parse_pdf_amount(raw_value, suffix)
        if amount is None or _is_balance_line(description):
            continue
        out.append({
            "tx_id": None,
            "date": _normalize_date(date_raw),
            "amount": amount,
            "description": description.strip(),
        })
    return out


def _parse_pdf_caixa(pdf) -> List[Dict[str, Any]]:
    out = []
    for page in pdf.pages:
        rows = _ocr_reconstruct_rows(page)
        out.extend(_parse_pdf_caixa_rows(rows))
    return out


# Chave = forma normalizada (sem acento/espaço/maiúscula) do `institution`
# cadastrado na conta — busca por substring, então "C6 Bank", "C6" ou "c6"
# casam igual. Caixa não entra aqui porque precisa do objeto `pdf` (imagens),
# não só do texto — é tratada antes, direto em `parse_pdf_bytes`.
PDF_LINE_PARSERS: Dict[str, Any] = {
    "c6": _parse_pdf_c6,
    "mercadopago": _parse_pdf_mercadopago,
    "99pay": _parse_pdf_99pay,
}


def _pick_pdf_parser(institution: Optional[str]):
    norm = _normalize_institution(institution)
    for key, parser in PDF_LINE_PARSERS.items():
        if key in norm:
            return parser
    return _parse_pdf_lines_generic


def parse_pdf_bytes(data: bytes, password: Optional[str] = None, institution: Optional[str] = None) -> List[Dict[str, Any]]:
    if pdfplumber is None:
        raise RuntimeError(
            "Biblioteca 'pdfplumber' não instalada. Rode: pip install pdfplumber"
        )
    try:
        pdf = pdfplumber.open(io.BytesIO(data), password=password)
    except Exception as e:
        raise ValueError(
            f"Não consegui abrir o PDF (senha incorreta ou ausente?): {e}"
        )
    with pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        # Caixa exporta um PDF escaneado (sem texto real) — se o texto vier
        # vazio (ou se a conta for explicitamente identificada como Caixa),
        # usa o caminho de OCR com reconstrução de linhas por coordenada.
        if "caixa" in _normalize_institution(institution) or not text.strip():
            return _parse_pdf_caixa(pdf)

        parser = _pick_pdf_parser(institution)
        return parser(text)


def parse_statement_bytes(
    filename: str,
    data: bytes,
    password: Optional[str] = None,
    institution: Optional[str] = None,
) -> List[Dict[str, Any]]:
    ext = (filename or "").lower().rsplit(".", 1)[-1] if "." in (filename or "") else ""
    if ext in ("ofx", "qfx"):
        return parse_ofx_bytes(data)
    if ext == "csv":
        return parse_csv_bytes(data)
    if ext == "pdf":
        return parse_pdf_bytes(data, password=password, institution=institution)
    raise ValueError(f"Extensão não suportada: .{ext} (use .ofx, .qfx, .csv ou .pdf)")


# ── Dedupe + gravação ─────────────────────────────────────────────────────────
def _dedupe_key(account_id: str, tx: Dict[str, Any]) -> str:
    if tx.get("tx_id"):
        # Inclui o valor na chave mesmo quando há FITID — achado real
        # (memory/GESTOR_FINANCEIRO.md §22.2.2): o Banco do Brasil reusa o
        # mesmo FITID para uma transação e sua reversão/estorno (ex.:
        # "Pagamento de Impostos" -87,05 e "Estorno de Débito" +87,05, ambos
        # com FITID=1.024). Sem o valor na chave, o segundo lançamento do par
        # colidia com o primeiro e era descartado como "duplicado", perdendo
        # a baixa do estorno e deixando o saldo da conta errado.
        amount = round(float(tx.get("amount") or 0), 2)
        return f"{account_id}:{tx['tx_id']}:{amount}"
    raw = f"{account_id}|{tx.get('date')}|{tx.get('amount')}|{tx.get('description')}"
    return f"{account_id}:hash:" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


# ── Detecção de transferência entre contas próprias ───────────────────────────
# Extratos brasileiros (Nubank, InfinitePay etc.) descrevem o contraparte do Pix
# incluindo o CNPJ completo ("25.995.295/0001-04") ou o CPF mascarado
# ("•••.152.691-••", só os 6 dígitos do meio ficam visíveis por privacidade) —
# ou, no caso de transferência pra si mesmo dentro de uma conta-pagamento tipo
# InfinitePay, o CPF aparece completo e sem máscara ("01615269185"). Cadastrando
# o documento do titular em cada conta (`holder_document`), conseguimos casar a
# descrição da transação com outra conta já cadastrada no sistema e marcar o
# lançamento com is_internal_transfer=True. O kind continua RECEITA/DESPESA
# (pelo sinal do valor) — isso é necessário pra não quebrar o cálculo de saldo
# em _compute_account_balance (finance_routes.py), que só soma kind == RECEITA
# ou DESPESA. A flag serve pra excluir esses lançamentos de relatórios futuros
# de receita/despesa "real" sem afetar o saldo da conta.
#
# Nem todo banco fornece documento na descrição — o BB, por exemplo, manda o
# CNPJ/CPF completo no "Pix recebido" mas só um nome truncado, sem documento
# nenhum, no "Pix enviado" (ver memory/GESTOR_FINANCEIRO.md §22.2.3/§25). Por
# isso a detecção tem 3 níveis de confiança, do mais ao menos confiável:
#   1. "documento" — CNPJ/CPF na descrição bate com holder_document de outra conta.
#   2. "nome"      — nome normalizado na descrição bate com holder_name de outra
#                    conta (fallback quando não há documento — caso BB).
#   3. "valor_data"— nenhuma das duas achou nada NA hora do import; outra rotina
#                    (_suggest_value_date_transfers, chamada depois do import)
#                    casa por valor absoluto + data próxima entre contas próprias
#                    e marca como SUGESTÃO (transfer_suggested=True), sem
#                    confirmar automaticamente — exige confirmação manual via
#                    POST /api/finance/entries/{id}/confirm-transfer.
_RE_CNPJ = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")
_RE_CPF_MASKED = re.compile(r"[•*]{2,3}\.?(\d{3})\.?(\d{3})-?[•*]{2,3}")
_RE_CPF_FULL = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_RE_CPF_BARE = re.compile(r"\b\d{11}\b")  # CPF sem máscara nem pontuação (ex: InfinitePay)


def _extract_match_keys(description: str) -> List[str]:
    """Retorna possíveis chaves de comparação extraídas da descrição: CNPJ completo
    (14 dígitos) ou os 6 dígitos centrais de um CPF (mascarado, completo ou solto)."""
    if not description:
        return []
    keys = []
    for m in _RE_CNPJ.finditer(description):
        digits = re.sub(r"\D", "", m.group())
        if len(digits) == 14:
            keys.append(digits)
    for m in _RE_CPF_MASKED.finditer(description):
        keys.append(m.group(1) + m.group(2))  # 6 dígitos centrais
    for m in _RE_CPF_FULL.finditer(description):
        digits = re.sub(r"\D", "", m.group())
        if len(digits) == 11:
            keys.append(digits[3:9])
    for m in _RE_CPF_BARE.finditer(description):
        keys.append(m.group()[3:9])
    return keys


def _account_match_keys(holder_document: Optional[str]) -> List[str]:
    """Mesma lógica do lado da conta cadastrada: se for CNPJ (14 dígitos), a chave é o
    documento inteiro; se for CPF (11 dígitos), a chave são os 6 dígitos centrais
    (porque é só isso que aparece mascarado na maioria dos extratos)."""
    if not holder_document:
        return []
    digits = re.sub(r"\D", "", holder_document)
    if len(digits) == 14:
        return [digits]
    if len(digits) == 11:
        return [digits[3:9]]
    return []


def _normalize_name(name: Optional[str]) -> str:
    """Remove acentos, baixa pra maiúsculo e colapsa espaços — pra comparar
    "Diego Cesar Gonçalves Olivatto" com "DIEGO CESAR GONCALVES OLIVATTO 01615269185"
    (o CPF solto no fim não afeta a comparação por substring, ver _name_in_description)."""
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_only.upper()).strip()


def _name_in_description(holder_name: Optional[str], description: str) -> bool:
    """True se o nome normalizado do titular aparecer (como substring) na descrição
    normalizada da transação. Limiar mínimo de 2 palavras pra evitar falso-positivo
    com nomes muito curtos/genéricos (ex.: um holder_name vazio ou só "JOSE")."""
    norm_name = _normalize_name(holder_name)
    if not norm_name or len(norm_name.split()) < 2:
        return False
    norm_desc = _normalize_name(description)
    return norm_name in norm_desc


async def _detect_transfer(description: str, current_account_id: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Tenta achar, entre as outras contas próprias já cadastradas, a contraparte de
    uma transferência interna. Tenta primeiro por documento (mais confiável) e cai
    pra nome (fallback) se não achar nada — ver bloco de comentário acima.
    Retorna (nome_da_conta, account_id, confidence) ou (None, None, None)."""
    import server  # import tardio — mesmo padrão do resto do módulo

    other_accounts = await server.db.financial_accounts.find(
        {"id": {"$ne": current_account_id}},
        {"_id": 0, "id": 1, "name": 1, "holder_document": 1, "holder_name": 1},
    ).to_list(1000)
    if not other_accounts:
        return None, None, None

    # 1) Documento — mais confiável, casa por CNPJ/CPF na descrição.
    tx_keys = set(_extract_match_keys(description))
    if tx_keys:
        for acc in other_accounts:
            acc_keys = set(_account_match_keys(acc.get("holder_document")))
            if tx_keys & acc_keys:
                return acc.get("name") or acc.get("id"), acc.get("id"), "documento"

    # 2) Nome — fallback quando o extrato não traz documento (ex.: BB "Pix enviado").
    for acc in other_accounts:
        if _name_in_description(acc.get("holder_name"), description):
            return acc.get("name") or acc.get("id"), acc.get("id"), "nome"

    return None, None, None


async def import_transactions(
    account_id: str,
    transactions: List[Dict[str, Any]],
    source_filename: str = "",
) -> Dict[str, Any]:
    """Cria 1 financial_entries por transação nova (dedupe por openfinance_tx_id),
    status A_CATEGORIZAR, source=EXTRATO_IMPORT. Usado tanto pelo upload manual
    quanto pelo poller de e-mail."""
    import server  # import tardio — evita ciclo (mesmo padrão de finance_routes.py)

    account = await server.db.financial_accounts.find_one({"id": account_id})
    if not account:
        raise ValueError(f"Conta não encontrada: {account_id}")

    imported, duplicated, skipped, transfers = 0, 0, 0, 0
    for tx in transactions:
        if tx.get("amount") in (None, 0) or not tx.get("date"):
            skipped += 1
            continue
        key = _dedupe_key(account_id, tx)
        existing = await server.db.financial_entries.find_one({"openfinance_tx_id": key})
        if existing:
            duplicated += 1
            continue

        amount = float(tx["amount"])
        description = tx.get("description") or ""
        # kind segue o sinal real do valor — isso é o que mantém o saldo da conta
        # correto (ver _compute_account_balance em finance_routes.py, que soma por
        # RECEITA/DESPESA). Transferência entre contas próprias não muda o kind,
        # só marca is_internal_transfer=True pra ser excluída de relatórios de
        # receita/despesa "de verdade" no futuro.
        kind = EntryKind.RECEITA.value if amount > 0 else EntryKind.DESPESA.value
        transfer_name, transfer_acc_id, confidence = await _detect_transfer(description, account_id)

        if transfer_name:
            status = EntryStatus.PAGO.value  # não precisa de categoria — já é resolvido
            label = "documento" if confidence == "documento" else "nome (sem documento no extrato)"
            notes = (
                f"Transferência entre contas próprias (detectada automaticamente por {label} "
                f"— conta: {transfer_name})"
            )
        else:
            status = EntryStatus.A_CATEGORIZAR.value
            notes = f"Importado de {source_filename}" if source_filename else "Importado de extrato"

        entry_id = await server._next_id(server.db.financial_entries, "LCT-", 4)
        doc = {
            "id": entry_id,
            "kind": kind,
            "scope": account.get("scope", "EMPRESA"),
            "account_id": account_id,
            "date": tx["date"],
            "paid_date": tx["date"],
            "establishment": description or None,
            "total_value": round(abs(amount), 2),
            "payment_method": None,
            "installments": {"n": 1, "total": 1},
            "status": status,
            "splits": [],
            "is_internal_transfer": bool(transfer_name),
            "transfer_match_confidence": confidence,
            "transfer_with_account_id": transfer_acc_id,
            "transfer_with_entry_id": None,
            "transfer_suggested": False,
            "source": EntrySource.EXTRATO_IMPORT.value,
            "openfinance_tx_id": key,
            "reconciled": False,
            "invoice_id": None,
            "attachments": [source_filename] if source_filename else [],
            "recurring_id": None,
            "notes": notes,
            "created_at": datetime.utcnow().isoformat(),
        }
        await server.db.financial_entries.insert_one(doc)
        imported += 1
        if transfer_name:
            transfers += 1

    # Terceira camada de detecção — valor+data entre contas próprias (baixa
    # confiança, fica só como SUGESTÃO pro usuário confirmar). Roda depois do
    # loop principal porque precisa olhar lançamentos já existentes (de outras
    # contas, importadas em outra sessão) e os que acabaram de entrar agora.
    suggestions = await _suggest_value_date_transfers(account_id)

    return {
        "account_id": account_id,
        "total_parsed": len(transactions),
        "imported": imported,
        "duplicated": duplicated,
        "skipped": skipped,
        "transfers_detected": transfers,
        "transfers_suggested": suggestions,
    }


# ── Camada 3: sugestão de transferência por valor+data ────────────────────────
# Quando nem documento nem nome batem (ex.: BB "Pix enviado" pra uma conta cujo
# nome no extrato não foi cadastrado, ou veio escrito de um jeito muito diferente
# do holder_name), ainda dá pra suspeitar de transferência interna olhando o
# padrão: uma SAÍDA numa conta própria e uma ENTRADA de mesmo valor absoluto em
# outra conta própria, em data igual ou muito próxima (±1 dia, pra cobrir
# processamento overnight). Isso NÃO confirma sozinho — fica marcado como
# sugestão (transfer_suggested=True) até o usuário confirmar via endpoint
# (ver finance_routes.py: POST /entries/{id}/confirm-transfer).
_VALUE_DATE_WINDOW_DAYS = 1


def _date_window(date_iso: str) -> Tuple[str, str]:
    d = datetime.strptime(date_iso, "%Y-%m-%d")
    lo = (d - timedelta(days=_VALUE_DATE_WINDOW_DAYS)).strftime("%Y-%m-%d")
    hi = (d + timedelta(days=_VALUE_DATE_WINDOW_DAYS)).strftime("%Y-%m-%d")
    return lo, hi


async def _suggest_value_date_transfers(account_id: str) -> int:
    """Para lançamentos de `account_id` ainda sem transferência confirmada
    (is_internal_transfer=False) nem sugestão anterior (transfer_suggested=False),
    procura em OUTRAS contas próprias um lançamento de sinal oposto, mesmo valor
    absoluto e data dentro da janela. Se achar, marca os DOIS lados como sugestão
    (não confirma — só sinaliza pra revisão manual). Retorna quantos pares novos
    foram sugeridos."""
    import server

    candidates = await server.db.financial_entries.find(
        {
            "account_id": account_id,
            "is_internal_transfer": False,
            "transfer_suggested": False,
        },
        {"_id": 0},
    ).to_list(5000)

    suggested = 0
    for entry in candidates:
        value = round(float(entry.get("total_value") or 0), 2)
        if not value:
            continue
        opposite_kind = EntryKind.DESPESA.value if entry.get("kind") == EntryKind.RECEITA.value else EntryKind.RECEITA.value
        lo, hi = _date_window(entry.get("date") or "")

        match = await server.db.financial_entries.find_one({
            "id": {"$ne": entry["id"]},
            "account_id": {"$ne": account_id},
            "kind": opposite_kind,
            "total_value": value,
            "date": {"$gte": lo, "$lte": hi},
            "is_internal_transfer": False,
            "transfer_suggested": False,
        })
        if not match:
            continue

        await server.db.financial_entries.update_one(
            {"id": entry["id"]},
            {"$set": {
                "transfer_suggested": True,
                "transfer_match_confidence": "valor_data",
                "transfer_with_account_id": match["account_id"],
                "transfer_with_entry_id": match["id"],
                "notes": (entry.get("notes") or "") + " [Possível transferência interna — confirme em Financeiro]",
            }},
        )
        await server.db.financial_entries.update_one(
            {"id": match["id"]},
            {"$set": {
                "transfer_suggested": True,
                "transfer_match_confidence": "valor_data",
                "transfer_with_account_id": account_id,
                "transfer_with_entry_id": entry["id"],
                "notes": (match.get("notes") or "") + " [Possível transferência interna — confirme em Financeiro]",
            }},
        )
        suggested += 1

    return suggested
