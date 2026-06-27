"""
Lança no sistema (produção) os 23 itens do parceiro Leonardo - Dry Clean USA já
reconciliados para o período de 02/06 a 22/06/2026 (ver memory/PARCEIROS_TAPETES.md),
usando o mesmo motor de automação que a tela "Automações" usa
(POST /api/automation/execute-measures) — cria um orçamento (ORC-XXXXXXX) com os
itens (ITM-XXXXXXX) já no status AGUARDANDO_BUSCAR, vinculados ao cliente CLI-0006.

Depois de rodar, o relatório em /reports → "Fechamento de Parceiro" vai mostrar
esses itens de verdade.

Uso (no terminal, dentro da pasta do projeto):
  $env:SUPERDRY_EMAIL="seu-email@exemplo.com"
  $env:SUPERDRY_PASSWORD="sua-senha"
  python lancar_parceiro_leonardo_junho.py

Por padrão aponta para a produção (Oracle). Para testar contra o backend local
primeiro, defina:
  $env:SUPERDRY_BASE_URL="http://localhost:8001"
"""
import json
import math
import os
import sys

import requests

BASE = os.environ.get("SUPERDRY_BASE_URL", "https://sistema.lavesuperdry.com.br")

EMAIL = os.environ.get("SUPERDRY_EMAIL", "")
PASSWORD = os.environ.get("SUPERDRY_PASSWORD", "")
if not EMAIL or not PASSWORD:
    print("ERRO: defina as variáveis de ambiente SUPERDRY_EMAIL e SUPERDRY_PASSWORD antes de rodar este script.")
    sys.exit(1)

CLIENT_NAME = "Leonardo - Dry Clean USA"  # nome canônico no banco (CLI-0006)

# ── Os 23 itens reconciliados (ver memory/PARCEIROS_TAPETES.md) ────────────────
# categoria: TAPETE | CORTINA — informativo apenas (o catálogo de parceiro hoje
# não distingue cortina, todos entram como "Tapete Parceiro" no preço unificado
# de R$20/m²; ver aviso no final do script)
# tipo: RETANGULAR | REDONDO
ITENS = [
    {"data": "2026-06-08", "categoria": "CORTINA", "tipo": "RETANGULAR", "cor": None, "etiqueta": None, "largura": 2.8, "comprimento": 2.5},
    {"data": "2026-06-08", "categoria": "CORTINA", "tipo": "RETANGULAR", "cor": None, "etiqueta": None, "largura": 2.8, "comprimento": 2.75},
    {"data": "2026-06-08", "categoria": "CORTINA", "tipo": "RETANGULAR", "cor": None, "etiqueta": None, "largura": 2.8, "comprimento": 2.1},
    {"data": "2026-06-12", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Roxo", "etiqueta": None, "largura": 2.0, "comprimento": 3.0},
    {"data": "2026-06-12", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Roxo", "etiqueta": None, "largura": 2.0, "comprimento": 3.0},
    {"data": "2026-06-12", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Roxo", "etiqueta": None, "largura": 2.9, "comprimento": 3.4},
    {"data": "2026-06-12", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Roxo", "etiqueta": "367", "largura": 2.5, "comprimento": 3.0},
    {"data": "2026-06-12", "categoria": "TAPETE", "tipo": "REDONDO", "cor": "Verde", "etiqueta": "147", "largura": 2.0, "comprimento": None},
    {"data": "2026-06-12", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Roxo", "etiqueta": None, "largura": 2.5, "comprimento": 3.5},
    {"data": "2026-06-12", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": None, "etiqueta": None, "largura": 2.5, "comprimento": 2.0},
    {"data": "2026-06-18", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Cinza", "etiqueta": "374", "largura": 0.7, "comprimento": 1.55},
    {"data": "2026-06-18", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Cinza", "etiqueta": "349", "largura": 1.1, "comprimento": 1.8},
    {"data": "2026-06-18", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Cinza", "etiqueta": "312", "largura": 1.2, "comprimento": 1.6},
    {"data": "2026-06-18", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Rosa", "etiqueta": "198", "largura": 1.0, "comprimento": 1.5},
    {"data": "2026-06-18", "categoria": "TAPETE", "tipo": "REDONDO", "cor": "Azul", "etiqueta": "149", "largura": 1.4, "comprimento": None},
    {"data": "2026-06-22", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Roxo", "etiqueta": "366", "largura": 2.5, "comprimento": 2.9},
    {"data": "2026-06-22", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Verde", "etiqueta": "320", "largura": 1.9, "comprimento": 3.0},
    {"data": "2026-06-22", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Cinza", "etiqueta": "511", "largura": 1.2, "comprimento": 1.7},
    {"data": "2026-06-22", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Rosa", "etiqueta": "214", "largura": 2.4, "comprimento": 2.8},
    {"data": "2026-06-22", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Cinza", "etiqueta": "558", "largura": 2.7, "comprimento": 2.9},
    {"data": "2026-06-22", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Azul", "etiqueta": "041", "largura": 0.9, "comprimento": 1.5},
    {"data": "2026-06-22", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Cinza", "etiqueta": "373", "largura": 0.7, "comprimento": 1.5},
    {"data": "2026-06-22", "categoria": "TAPETE", "tipo": "RETANGULAR", "cor": "Rosa", "etiqueta": "199", "largura": 0.6, "comprimento": 1.0},
]


def build_payload_item(it):
    payload = {
        "client_name": CLIENT_NAME,
        "service_name": "Tapete",
        "reference_date": f"{it['data']}T12:00:00",
    }
    if it["tipo"] == "REDONDO":
        d = it["largura"]
        payload["diameter"] = d
        payload["area_m2"] = round(math.pi * (d / 2) ** 2, 4)
    else:
        w, h = it["largura"], it["comprimento"]
        payload["width"] = w
        payload["height"] = h
        payload["area_m2"] = round(w * h, 4)

    if it["cor"] and it["etiqueta"]:
        payload["partner_label"] = {"type": "COLOR_NUM", "color": it["cor"].upper(), "number": it["etiqueta"]}
    elif it["cor"]:
        payload["partner_label"] = {"type": "TEXT", "text": it["cor"]}
    # sem cor e sem etiqueta -> sem partner_label (fica "sem nome" no relatório)
    return payload


def main():
    print(f"Base URL: {BASE}")
    print("Fazendo login...")
    r = requests.post(f"{BASE}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        print(f"ERRO no login: {r.status_code} {r.text}")
        sys.exit(1)
    token = r.json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}
    print("OK\n")

    items_payload = [build_payload_item(it) for it in ITENS]

    print(f"Enviando {len(items_payload)} itens para /api/automation/execute-measures...")
    r = requests.post(f"{BASE}/api/automation/execute-measures", json={"items": items_payload}, headers=H)
    if r.status_code != 200:
        print(f"ERRO: {r.status_code} {r.text}")
        sys.exit(1)

    data = r.json()
    results = data.get("results", [])
    created = sum(1 for x in results if x.get("status") in ("created", "updated"))
    dupes = sum(1 for x in results if x.get("status") == "duplicate")
    skipped = sum(1 for x in results if x.get("status") == "skipped")
    print(f"\nResultado: {created} criados/atualizados, {dupes} duplicados, {skipped} ignorados")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
