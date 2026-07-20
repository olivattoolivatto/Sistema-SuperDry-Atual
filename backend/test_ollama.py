#!/usr/bin/env python3
"""
test_ollama.py — Testa se o Ollama está rodando e faz uma extração
de teste com a mensagem da Mariane de Oliveira (caso real B5).

Uso:
    python3 test_ollama.py

Requer: requests (pip install requests)
        Ollama rodando em localhost:11434 com modelo llama3.2:3b
"""

import json
import sys
import requests

OLLAMA_BASE = "http://localhost:11434"
MODEL = "llama3.2:3b"

MARIANE_MSG = """Mariane de Oliveira
+55 65 99973-1235
Edifício Amadeo Modigliani Cuiabá
Apartamento 2402
Horário 20/7 9:00

🔶 Orçamento - Estofado e Tapete 🔶

💧Lavagem a seco - Sofá 2 lugares - R$290,00
💧Lavagem a seco - Cadeira Tipo Poltrona - R$50,00un (2un = R$100,00)
💧Lavagem a seco - Cadeira Tipo Poltrona - R$60,00un (2un = R$120,00)

📍💳 Total dos serviços: R$ 510,00 à vista no pix ou em até 5x sem juros no cartão de crédito ou
📌💵 Pagamento em dinheiro R$ 460,00.

📍 🛋 Estofados: 🛋
▪O atendimento é em domicílio.
▪Os serviços são realizados por profissionais especializados.
▪Responsabilidade pelos itens durante o serviço."""

EXPECTED = {
    "client_name": "Mariane de Oliveira",
    "phone": "65 99973-1235",
    "address": "Edifício Amadeo Modigliani",
    "complement": "Apartamento 2402",
    "scheduled_date": "2026-07-20",
    "scheduled_time": "09:00",
    "items": [
        {"service_name": "Lavagem a seco - Sofá 2 lugares", "qty": 1, "unit_value": 290.0, "total": 290.0},
        {"service_name": "Lavagem a seco - Cadeira Tipo Poltrona", "qty": 2, "unit_value": 50.0, "total": 100.0},
        {"service_name": "Lavagem a seco - Cadeira Tipo Poltrona", "qty": 2, "unit_value": 60.0, "total": 120.0},
    ],
    "total_pix": 510.0,
    "total_cash": 460.0,
}

PROMPT = f"""Você é o parser de mensagens WhatsApp da SuperDry Lavanderia.
Extraia dados estruturados da mensagem abaixo.

REGRAS:
- Linhas "Horário DD/M HH:MM" = data/hora do agendamento, NÃO é item
- "Edifício X" = endereço; "Apartamento N" = complemento
- Tudo após o bloco de pagamento (▪, 📍🛋) = IGNORAR
- Dois itens com mesmo nome mas preços diferentes = dois itens distintos
- "R$X,XXun (Nun = R$Y,YY)" = preço unitário + quantidade + total

MENSAGEM:
{MARIANE_MSG}

Responda SOMENTE com JSON válido (sem markdown, sem explicações):
{{
  "client_name": "...",
  "phone": "...",
  "address": "...",
  "complement": "...",
  "scheduled_date": "YYYY-MM-DD",
  "scheduled_time": "HH:MM",
  "total_pix": 0.0,
  "total_cash": 0.0,
  "items": [
    {{"service_name": "...", "qty": 1, "unit_value": 0.0, "total": 0.0}}
  ]
}}"""


def check_ollama():
    """Verifica se o Ollama está disponível."""
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=3)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            print(f"✅ Ollama disponível. Modelos instalados: {models}")
            return True
        else:
            print(f"❌ Ollama respondeu com status {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama não disponível em {OLLAMA_BASE}: {e}")
        return False


def run_extraction():
    """Envia a mensagem para o Ollama e verifica o resultado."""
    print("\n=== Enviando mensagem da Mariane para extração ===\n")
    try:
        r = requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json={"model": MODEL, "prompt": PROMPT, "stream": False},
            timeout=60,
        )
        r.raise_for_status()
        raw = r.json().get("response", "")
        print(f"Resposta bruta do modelo:\n{raw}\n")
    except Exception as e:
        print(f"❌ Erro ao chamar modelo: {e}")
        return

    # Tentar parsear o JSON da resposta
    import re
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not json_match:
        print("❌ JSON não encontrado na resposta do modelo.")
        return

    try:
        result = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao parsear JSON: {e}")
        return

    print("=== JSON extraído ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # Verificar campos esperados
    print("\n=== Verificação de campos ===")
    ok = True
    checks = [
        ("client_name", EXPECTED["client_name"]),
        ("scheduled_date", EXPECTED["scheduled_date"]),
        ("scheduled_time", EXPECTED["scheduled_time"]),
        ("total_pix", EXPECTED["total_pix"]),
        ("total_cash", EXPECTED["total_cash"]),
    ]
    for key, expected in checks:
        got = result.get(key)
        match = str(got) == str(expected) or got == expected
        status = "✅" if match else "⚠️"
        if not match:
            ok = False
        print(f"  {status} {key}: esperado={expected!r}, got={got!r}")

    # Verificar itens
    items = result.get("items", [])
    print(f"\n  Itens extraídos: {len(items)} (esperado: {len(EXPECTED['items'])})")
    for i, it in enumerate(items):
        print(f"    [{i+1}] {it.get('service_name', '?')} · qty={it.get('qty', '?')} · unit={it.get('unit_value', '?')} · total={it.get('total', '?')}")
    if len(items) != len(EXPECTED["items"]):
        print("  ⚠️  Número de itens diferente do esperado")
        ok = False

    print(f"\n{'✅ Extração OK' if ok else '⚠️  Extração com divergências (verificar acima)'}")


def test_python_parser():
    """Testa o parser Python local sem Ollama (importa server.py)."""
    print("\n=== Teste do parser Python local (sem Ollama) ===")
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(__file__))
        # Import dinâmico para não exigir toda a stack FastAPI
        import importlib.util
        spec = importlib.util.spec_from_file_location("server", os.path.join(os.path.dirname(__file__), "server.py"))
        # Só importar funções utilitárias, não inicializar o app inteiro
        print("  (teste do parser Python requer o servidor rodando — use o endpoint /api/automation/interpret-message)")
    except Exception as e:
        print(f"  (aviso: {e})")


if __name__ == "__main__":
    print("SuperDry Lavanderia — Teste Ollama")
    print("=" * 50)

    available = check_ollama()
    if not available:
        print("\nInstale o Ollama primeiro:")
        print("  bash install_ollama.sh")
        sys.exit(1)

    run_extraction()
    test_python_parser()
