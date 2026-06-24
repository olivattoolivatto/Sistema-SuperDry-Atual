"""
Script auxiliar: busca eventos do Google Calendar e clientes/orçamentos do sistema
e salva em arquivos JSON para a conciliação pelo Claude.
"""
import requests, json, sys, os
from datetime import datetime

BASE = "http://localhost:8001"

# 1. Login
# Credenciais via variável de ambiente — nunca deixar senha em texto puro no código.
# Defina antes de rodar: $env:SUPERDRY_EMAIL="..."; $env:SUPERDRY_PASSWORD="..."
EMAIL = os.environ.get("SUPERDRY_EMAIL", "")
PASSWORD = os.environ.get("SUPERDRY_PASSWORD", "")
if not EMAIL or not PASSWORD:
    print("ERRO: defina as variáveis de ambiente SUPERDRY_EMAIL e SUPERDRY_PASSWORD antes de rodar este script.")
    sys.exit(1)

print("Fazendo login...")
r = requests.post(f"{BASE}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
if r.status_code != 200:
    print(f"ERRO no login: {r.text}"); sys.exit(1)
token = r.json()["access_token"]
H = {"Authorization": f"Bearer {token}"}
print("OK")

# 2. Eventos do Calendar (junho/2026)
print("Buscando eventos do Google Calendar...")
r = requests.get(f"{BASE}/api/calendar/events",
    params={"start_date":"2026-06-01", "end_date":"2026-06-30"},
    headers=H)
if r.status_code != 200:
    print(f"ERRO calendar: {r.status_code} {r.text[:300]}")
    eventos = []
else:
    data = r.json()
    eventos = data if isinstance(data, list) else data.get("events", data.get("items", []))
    print(f"  {len(eventos)} eventos encontrados")

with open("eventos_junho.json","w",encoding="utf-8") as f:
    json.dump(eventos, f, ensure_ascii=False, indent=2, default=str)
print("  Salvo em eventos_junho.json")

# 3. Clientes existentes
print("Buscando clientes...")
r = requests.get(f"{BASE}/api/clients?limit=500", headers=H)
raw = r.json() if r.status_code == 200 else []
clientes = raw if isinstance(raw, list) else raw.get("clients", raw.get("items", []))
with open("clientes.json","w",encoding="utf-8") as f:
    json.dump(clientes, f, ensure_ascii=False, indent=2, default=str)
print(f"  {len(clientes)} clientes — salvo em clientes.json")

# 4. Orçamentos existentes (junho)
print("Buscando orçamentos...")
r = requests.get(f"{BASE}/api/budgets?limit=200", headers=H)
raw2 = r.json() if r.status_code == 200 else []
orcamentos = raw2 if isinstance(raw2, list) else raw2.get("budgets", raw2.get("items", []))
with open("orcamentos.json","w",encoding="utf-8") as f:
    json.dump(orcamentos, f, ensure_ascii=False, indent=2, default=str)
print(f"  {len(orcamentos)} orçamentos — salvo em orcamentos.json")

print("\nPronto! Compartilhe os 3 arquivos JSON com o Claude para a conciliação.")
