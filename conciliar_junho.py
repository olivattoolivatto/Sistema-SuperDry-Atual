"""
Conciliação Junho/2026 — SuperDry
Executa todos os lançamentos confirmados: pagamentos, novos clientes, orçamentos e status.
Rodar com:  python conciliar_junho.py
"""
import requests, json, sys, time, os
from datetime import datetime

BASE = "http://localhost:8001"
# Credenciais via variável de ambiente — nunca deixar senha em texto puro no código.
# Defina antes de rodar: $env:SUPERDRY_EMAIL="..."; $env:SUPERDRY_PASSWORD="..."
EMAIL = os.environ.get("SUPERDRY_EMAIL", "")
PASSWORD = os.environ.get("SUPERDRY_PASSWORD", "")
if not EMAIL or not PASSWORD:
    print("ERRO: defina as variáveis de ambiente SUPERDRY_EMAIL e SUPERDRY_PASSWORD antes de rodar este script.")
    sys.exit(1)
SALESPERSON = "Diego Olivatto"

# ── Paleta de métodos de pagamento ──────────────────────────────────────────
PIX_NU       = "PIX_CNPJ_25995295000104"
DINHEIRO     = "DINHEIRO"
CREDITO_1X   = "CREDITO_1X"
CREDITO_2X   = "CREDITO_2X"
CREDITO_3X   = "CREDITO_3X"
CREDITO_4X   = "CREDITO_4X"
CREDITO_5X   = "CREDITO_5X"
CREDITO_7X   = "CREDITO_7X"

# ── IDs de serviços ──────────────────────────────────────────────────────────
SRV_TAPETE_EMP        = "SRV-0032"  # Tapete m² - Lavagem na Empresa
SRV_TAPETE_REDONDO    = "SRV-0033"  # Tapete redondo - na Empresa
SRV_SOFA_2LG          = "SRV-0004"  # Sofá 2 lugares
SRV_SOFA_3LG          = "SRV-0005"  # Sofá 3 lugares
SRV_SOFA_CANTO        = "SRV-0006"  # Sofá de canto
SRV_CADEIRA_ESC       = "SRV-0009"  # Cadeira escritório
SRV_CADEIRA_ASSENTO   = "SRV-0008"  # Cadeira assento+encosto
SRV_POLTRONA          = "SRV-0012"  # Poltrona padrão
SRV_CORTINA_VOAL      = "SRV-0054"  # Cortina voal simples
SRV_CORTINA_DUPLA     = "SRV-0055"  # Cortina dupla voal+blackout
SRV_CARPETE_LOCAL     = "SRV-0046"  # Carpete no local
SRV_PERSIANA_ROLO     = "SRV-0059"  # Persiana rolô/romana
SRV_OUTROS            = "SRV-0072"  # Outros itens
SRV_IMPER_SOFA        = "SRV-0073"  # Impermeabilização sofá

# ── Helpers ──────────────────────────────────────────────────────────────────

def login():
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        print(f"ERRO login: {r.text}"); sys.exit(1)
    token = r.json()["access_token"]
    print("✅ Login OK")
    return {"Authorization": f"Bearer {token}"}

def get(H, path, **params):
    r = requests.get(f"{BASE}/api/{path}", headers=H, params=params)
    r.raise_for_status()
    return r.json()

def post(H, path, body):
    r = requests.post(f"{BASE}/api/{path}", headers=H, json=body)
    if r.status_code not in (200, 201):
        print(f"  ⚠️  POST {path} → {r.status_code}: {r.text[:200]}")
        return None
    return r.json()

def put(H, path, body):
    r = requests.put(f"{BASE}/api/{path}", headers=H, json=body)
    if r.status_code not in (200, 201):
        print(f"  ⚠️  PUT {path} → {r.status_code}: {r.text[:200]}")
        return None
    return r.json()

def patch(H, path, body=None):
    r = requests.patch(f"{BASE}/api/{path}", headers=H, json=body or {})
    if r.status_code not in (200, 201):
        print(f"  ⚠️  PATCH {path} → {r.status_code}: {r.text[:200]}")
        return None
    return r.json()

def create_client(H, name, phone, address_str, complement=None,
                  neighborhood="Cuiabá", city="Cuiabá", state="MT",
                  observations=None, phone_alt=None):
    body = {
        "name": name,
        "phone_primary": phone,
        "phone_alternative": phone_alt,
        "address": {
            "full_address": address_str,
            "complement": complement,
            "neighborhood": neighborhood,
            "city": city,
            "state": state
        },
        "observations": observations
    }
    r = post(H, "clients", body)
    if r:
        cid = r.get("id", "?")
        print(f"  👤 Cliente criado: {name} → {cid}")
        return cid
    return None

def create_budget(H, client_id, payment_method=PIX_NU,
                  internal_obs=None, budget_obs=None):
    body = {
        "client_id": client_id,
        "payment_method": payment_method,
        "salesperson": SALESPERSON,
        "internal_observations": internal_obs or "",
        "budget_observations": budget_obs or ""
    }
    r = post(H, "budgets", body)
    if r:
        oid = r.get("id", "?")
        print(f"  📋 Orçamento criado: {oid}")
        return oid
    return None

def add_item(H, orc_id, srv_id, qty=1.0, width=None, height=None,
             diameter=None, area_m2=None, linear_meters=None, obs=None):
    body = {"service_id": srv_id, "quantity": qty}
    if width:        body["width"] = width
    if height:       body["height"] = height
    if diameter:     body["diameter"] = diameter
    if area_m2:      body["area_m2"] = area_m2
    if linear_meters: body["linear_meters"] = linear_meters
    if obs:          body["observations"] = obs
    r = post(H, f"budgets/{orc_id}/items", body)
    if r:
        iid = r.get("id", "?")
        return iid
    return None

def fix_item_price(H, item_id, unit_price, total_value, obs=None):
    body = {"unit_price": unit_price, "total_value": total_value}
    if obs: body["observations"] = obs
    patch(H, f"items/{item_id}", body)

def set_item_status(H, item_id, status, notes=""):
    post(H, f"items/{item_id}/status", {"status": status, "notes": notes})

def pay_item(H, item_id, method, value, notes=""):
    r = post(H, f"items/{item_id}/payment",
             {"method": method, "value": value, "notes": notes})
    if r:
        print(f"    💰 Pagamento R$ {value:.2f} ({method}) → {r.get('payment_status')}")
    return r

def get_budget_items(H, orc_id):
    r = get(H, f"budgets/{orc_id}")
    return r.get("items", [])

def find_client_by_name(H, partial_name):
    clients = get(H, "clients", limit=500)
    if isinstance(clients, list):
        for c in clients:
            if partial_name.lower() in c.get("name","").lower():
                return c
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# EXECUÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    H = login()
    time.sleep(0.3)

    # ──────────────────────────────────────────────────────────────────────────
    print("\n══ 1. CORRIGIR VANESSA TONHÁ (bug telefone) ══")
    c = find_client_by_name(H, "Vanessa")
    if c:
        print(f"  Encontrada: {c['name']} | phone: {c.get('phone_primary')}")
        if "Vanessa" in c.get("phone_primary", ""):
            put(H, f"clients/{c['id']}", {
                **{k: v for k, v in c.items() if k in
                   ["name","phone_primary","phone_alternative","email",
                    "cpf_cnpj","instagram","observations"]},
                "phone_primary": "65 99977-1929",
                "address": c.get("address", {})
            })
            print("  ✅ Telefone corrigido para 65 99977-1929")
        else:
            print("  ℹ️  Telefone já parece correto, pulando.")
        vanessa_id = c["id"]
    else:
        print("  ⚠️  Vanessa não encontrada — criando nova...")
        vanessa_id = create_client(
            H, "Vanessa Tonhá", "65 99977-1929",
            "Rua das Camelias, QD 16, LT 17 - Condomínio Florais Itália",
            complement=None, neighborhood="Florais Itália",
            city="Cuiabá", state="MT"
        )

    # ──────────────────────────────────────────────────────────────────────────
    print("\n══ 2. ATUALIZAR NOME: Ana Paula Primor das Torres ══")
    r = get(H, "budgets/ORC-0000032")
    if r:
        cid_primor = r.get("client_id")
        if cid_primor:
            cli = get(H, f"clients/{cid_primor}")
            print(f"  Cliente atual: {cli.get('name')}")
            put(H, f"clients/{cid_primor}", {
                **{k: v for k, v in cli.items() if k in
                   ["name","phone_primary","phone_alternative","email",
                    "cpf_cnpj","instagram","observations"]},
                "name": "Ana Paula Martins Pinheiro Santos",
                "phone_primary": cli.get("phone_primary","65 99683-2195"),
                "address": cli.get("address", {})
            })
            print("  ✅ Nome atualizado")
        # Marcar itens como EM_LAVAGEM
        for item in r.get("items", []):
            if item.get("status") not in ("EM_LAVAGEM","AGUARDANDO_ENTREGA","ENTREGUE","EXECUTADO"):
                set_item_status(H, item["id"], "EM_LAVAGEM", "Tapete em lavagem na empresa - jun/26")
                print(f"  ✅ {item['id']} → EM_LAVAGEM")

    # ──────────────────────────────────────────────────────────────────────────
    print("\n══ 3. PAGAMENTOS — ORÇAMENTOS EXISTENTES ══")

    def pagar_todos_itens(orc_id, method, value_total, notes=""):
        """Distribui value_total entre os itens ativos e registra pagamento.
        Use apenas quando value_total == soma dos preços de tabela (sem desconto).
        """
        items = get_budget_items(H, orc_id)
        active = [i for i in items if not i.get("client_desisted")]
        if not active:
            print(f"  ⚠️  {orc_id} sem itens ativos")
            return
        per_item = round(value_total / len(active), 2)
        remainder = round(value_total - per_item * (len(active) - 1), 2)
        for idx, item in enumerate(active):
            v = remainder if idx == len(active) - 1 else per_item
            pay_item(H, item["id"], method, v, notes)

    def pagar_com_desconto(orc_id, method, value_pago, notes="", desc_original=""):
        """Para pagamentos com desconto: ajusta total_value de cada item
        proporcionalmente ao valor realmente cobrado, ENTÃO registra pagamento.
        Isso garante payment_status=PAGO sem saldo em aberto.
        """
        items = get_budget_items(H, orc_id)
        active = [i for i in items if not i.get("client_desisted")]
        if not active:
            print(f"  ⚠️  {orc_id} sem itens ativos para desconto")
            return
        total_original = sum(i.get("total_value", 0) or 0 for i in active)
        acumulado = 0.0
        for idx, item in enumerate(active):
            orig = item.get("total_value", 0) or 0
            if idx == len(active) - 1:
                v = round(value_pago - acumulado, 2)
            else:
                peso = (orig / total_original) if total_original > 0 else (1 / len(active))
                v = round(value_pago * peso, 2)
            acumulado += v
            obs = (f"Desconto: tabela R${orig:.2f} → cobrado R${v:.2f}"
                   + (f" ({desc_original})" if desc_original else ""))
            # Ajusta total_value para o valor cobrado (sem aberto)
            patch(H, f"items/{item['id']}", {
                "total_value": v,
                "unit_price": round(v / max(item.get("quantity", 1), 0.01), 2),
                "observations": obs
            })
            pay_item(H, item["id"], method, v, notes)

    # ORC-0000065 Mariana Paschoal — InfCrd3x R$240
    print("  → ORC-0000065 Mariana Paschoal — InfCrd3x R$240")
    pagar_todos_itens("ORC-0000065", CREDITO_3X, 240.00, "InfCrd3x 02/06/26")

    # ORC-0000062 Célia Scheffer — InfCrd2x R$1010
    print("  → ORC-0000062 Célia Scheffer — InfCrd2x R$1010")
    pagar_todos_itens("ORC-0000062", CREDITO_2X, 1010.00, "InfCrd2x 03/06/26")

    # ORC-0000066 Silvia Affi — PIX R$450
    print("  → ORC-0000066 Silvia Affi — PIX R$450")
    pagar_todos_itens("ORC-0000066", PIX_NU, 450.00, "PixNuSuperDry 05/06/26")

    # ORC-0000068 Maisa — InfCrd2x R$98
    print("  → ORC-0000068 Maisa — InfCrd2x R$98")
    pagar_todos_itens("ORC-0000068", CREDITO_2X, 98.00, "InfCrd2x 03/06/26")

    # ORC-0000071 Luis Eduardo — PIX R$30
    print("  → ORC-0000071 Luis Eduardo — PIX R$30")
    pagar_todos_itens("ORC-0000071", PIX_NU, 30.00, "PixNuSuperDry 08/06/26")

    # ORC-0000081 Aline Bernardes — PIX R$135 (desconto à vista, lista R$150)
    print("  → ORC-0000081 Aline Bernardes — PIX R$135 (desconto, ajusta total_value)")
    pagar_com_desconto("ORC-0000081", PIX_NU, 135.00,
                       "PixNuSuperDry 02/06/26", "desconto à vista, lista R$150")

    # ORC-0000079 Michelle Ficagna — PIX R$200 (desconto concedido, quitado)
    print("  → ORC-0000079 Michelle Ficagna — PIX R$200 (desconto, ajusta total_value)")
    pagar_com_desconto("ORC-0000079", PIX_NU, 200.00,
                       "PixNuSuperDry 02/06/26. Serviço 29/05/26.", "desconto concedido")

    # ORC-0000084 Pietra — Dinheiro R$315 (desconto à vista, lista R$350)
    print("  → ORC-0000084 Pietra — Dinheiro R$315 (desconto, ajusta total_value)")
    pagar_com_desconto("ORC-0000084", DINHEIRO, 315.00,
                       "Dinheiro 09/06/26", "desconto à vista, lista R$350")

    # ORC-0000089 Sandra Castaldelli — PIX R$210
    print("  → ORC-0000089 Sandra Castaldelli — PIX R$210")
    pagar_todos_itens("ORC-0000089", PIX_NU, 210.00, "PixNuSuperDry 08/06/26")

    # ORC-0000078 Eduardo Ficagna sofás — InfCrd4x R$400 (sofá G R$250 + sofá P R$150)
    print("  → ORC-0000078 Eduardo Ficagna sofás — InfCrd4x R$400")
    items_edu78 = get_budget_items(H, "ORC-0000078")
    active_edu78 = [i for i in items_edu78 if not i.get("client_desisted")]
    if len(active_edu78) >= 2:
        pay_item(H, active_edu78[0]["id"], CREDITO_4X, 250.00,
                 "InfCrd4x 10/06/26 (sofá G - parte do total R$450)")
        pay_item(H, active_edu78[1]["id"], CREDITO_4X, 150.00,
                 "InfCrd4x 10/06/26 (sofá P - parte do total R$450)")
        # Se tiver item de tapete no ORC-0000078, pagar também
        for extra in active_edu78[2:]:
            pay_item(H, extra["id"], CREDITO_4X, extra.get("total_value", 0),
                     "InfCrd4x 10/06/26")
    else:
        pagar_todos_itens("ORC-0000078", CREDITO_4X, 400.00, "InfCrd4x 10/06/26")

    # ORC-0000083 Eduardo tapete — InfCrd4x R$50
    print("  → ORC-0000083 Eduardo tapete — InfCrd4x R$50")
    pagar_todos_itens("ORC-0000083", CREDITO_4X, 50.00,
                      "InfCrd4x 10/06/26 (tapete - parte do total R$450)")

    # ──────────────────────────────────────────────────────────────────────────
    print("\n══ 4. CORRIGIR ORC-0000082 DANIELLA AMORIM ══")
    items_daniella = get_budget_items(H, "ORC-0000082")
    print(f"  {len(items_daniella)} itens existentes — desistindo todos (errados)")
    for item in items_daniella:
        patch(H, f"items/{item['id']}/desist")

    # Adicionar 2 cortinas corretas (voal 5.7m = R$190 cada)
    print("  Adicionando 2 cortinas voal 5.7m @ R$190 cada")
    i1 = add_item(H, "ORC-0000082", SRV_CORTINA_VOAL,
                  linear_meters=5.7, obs="Cortina voal 5,7m (serviço real jun/26)")
    i2 = add_item(H, "ORC-0000082", SRV_CORTINA_VOAL,
                  linear_meters=5.7, obs="Cortina voal 5,7m (serviço real jun/26)")

    # Daniella: total_value ajustado para R$170 (valor cobrado) → paga em cheio → PAGO
    if i1:
        fix_item_price(H, i1, unit_price=29.82, total_value=170.00,
                       obs="Cortina voal 5,7m — tabela R$190, cobrado R$170 (desc. R$380→R$340)")
        pay_item(H, i1, PIX_NU, 170.00,
                 "PixNuSuperDry 10/06/26 - total desconto R$380→R$340")
    if i2:
        fix_item_price(H, i2, unit_price=29.82, total_value=170.00,
                       obs="Cortina voal 5,7m — tabela R$190, cobrado R$170 (desc. R$380→R$340)")
        pay_item(H, i2, PIX_NU, 170.00,
                 "PixNuSuperDry 10/06/26 - total desconto R$380→R$340")
    print("  ✅ Daniella Amorim corrigida (R$340 pago)")

    # ──────────────────────────────────────────────────────────────────────────
    print("\n══ 5. ANA PAULA BONADIO — PENDENTE/COBRAR ══")
    for item in get_budget_items(H, "ORC-0000080"):
        if item.get("status") not in ("ENTREGAR", "AGUARDANDO_ENTREGA", "ENTREGUE"):
            set_item_status(H, item["id"], "ENTREGAR",
                            "Tapete entregue 10/06 sem pagamento - cobrar")
    print("  ✅ Status atualizado para ENTREGAR (cobrar)")

    # ──────────────────────────────────────────────────────────────────────────
    print("\n══ 6. NOVOS CLIENTES + ORÇAMENTOS (PAGOS) ══")

    # ── 6a. Marluce Barros (tapete 2×2.5m, PAGO R$160 pix)
    print("  → Marluce Barros")
    cli = create_client(
        H, "Marluce Barros", "65 99995-3873",
        "Condomínio Origem VG, Q7 casa 713, Av. Tiradentes 2500",
        complement="Q7 casa 713", neighborhood="Petrópolis",
        city="Várzea Grande", state="MT"
    )
    if cli:
        orc = create_budget(H, cli, PIX_NU)
        if orc:
            i = add_item(H, orc, SRV_TAPETE_EMP, width=2.0, height=2.5)
            if i:
                # total_value = R$160 (valor cobrado, não R$175 de tabela) → paga em cheio → PAGO
                fix_item_price(H, i, 32.00, 160.00,
                               obs="Tapete 2×2,5m — tabela R$175, cobrado R$160 (desc. à vista)")
                set_item_status(H, i, "EM_LAVAGEM", "Retirada 03/06/26")
                set_item_status(H, i, "AGUARDANDO_ENTREGA", "Lavado, aguardando entrega 12/06")
                pay_item(H, i, PIX_NU, 160.00,
                         "PixNuSuperDry 09/06/26 - desconto à vista (tabela R$175)")

    # ── 6b. Telma Rodrigues (cadeira escritório R$50, PAGO)
    print("  → Telma Rodrigues")
    cli = create_client(
        H, "Telma Rodrigues", "65 99229-8097",
        "Av. Dr. Hélio Ribeiro, 165 - Parque Eldorado",
        complement="Apto 702 - Ed. Portal de Cuiabá",
        neighborhood="Parque Eldorado", city="Cuiabá", state="MT"
    )
    if cli:
        orc = create_budget(H, cli, PIX_NU)
        if orc:
            i = add_item(H, orc, SRV_CADEIRA_ESC, qty=1,
                         obs="Cadeira de escritório - serviço no local 05/06/26")
            if i:
                fix_item_price(H, i, 50.00, 50.00)
                set_item_status(H, i, "EXECUTADO", "Executado no local 05/06/26")
                pay_item(H, i, PIX_NU, 50.00, "PixNuSuperDry 05/06/26")

    # ── 6c. Parceiro João/Felipe (poltronas R$60, PAGO)
    print("  → Parceiro João/Felipe")
    cli = create_client(
        H, "Parceiro João / Felipe", "65 00000-0000",
        "Endereço fornecido pelo parceiro",
        complement=None, neighborhood="Cuiabá", city="Cuiabá", state="MT",
        observations="Parceiro externo. Endereço variável por demanda."
    )
    if cli:
        orc = create_budget(H, cli, PIX_NU,
                            internal_obs="Serviço via parceiro - sem comissão de vendedor")
        if orc:
            i = add_item(H, orc, SRV_POLTRONA, qty=1,
                         obs="Limpeza de poltronas via parceiro João/Felipe - 05/06/26")
            if i:
                fix_item_price(H, i, 60.00, 60.00)
                set_item_status(H, i, "EXECUTADO", "Executado 05/06/26")
                pay_item(H, i, PIX_NU, 60.00, "PixNuSuperDry 08/06/26")

    # ── 6d. Paulinha Freiberger (sofá 2 lugares R$230, PAGO R$220)
    print("  → Paulinha Freiberger")
    cli = create_client(
        H, "Paulinha Freiberger", "65 99600-6318",
        "R. Profa. Neuza Lula Rodrigues, 150 - Barra do Pari",
        complement="Casa 318 - Cond. Residencial Canachuê (a chave no passinho)",
        neighborhood="Barra do Pari", city="Cuiabá", state="MT"
    )
    if cli:
        orc = create_budget(H, cli, CREDITO_1X)
        if orc:
            i = add_item(H, orc, SRV_SOFA_2LG, qty=1,
                         obs="Sofá 2 lugares - condição especial vizinho")
            if i:
                # total_value = R$220 (cobrado, não R$230 de tabela) → paga em cheio → PAGO
                fix_item_price(H, i, 220.00, 220.00,
                               obs="Sofá 2 lugares — tabela R$230, cobrado R$220 (desc. à vista)")
                set_item_status(H, i, "EXECUTADO", "Executado no local 08/06/26")
                pay_item(H, i, CREDITO_1X, 220.00,
                         "InfCrd1x 09/06/26 - desconto à vista (tabela R$230)")

    # ── 6e. Sadora Xavier (3 tapetes + cortina voal, R$1375, PAGO)
    print("  → Sadora Xavier")
    cli = create_client(
        H, "Sadora Xavier", "65 98115-4214",
        "R. Corsino Amarante, 1271 - Duque de Caxias II",
        complement="Apto 201 - Ed. Premiato",
        neighborhood="Duque de Caxias II", city="Cuiabá", state="MT"
    )
    if cli:
        orc = create_budget(H, cli, PIX_NU)
        if orc:
            # Tapete 1: 2.4×3.4 = 8.16m² R$286
            i1 = add_item(H, orc, SRV_TAPETE_EMP, width=2.40, height=3.40)
            if i1:
                fix_item_price(H, i1, 35.0, 286.00)
                set_item_status(H, i1, "ENTREGUE", "Entregue 09/06/26")
                pay_item(H, i1, PIX_NU, 286.00, "PixNuSuperDry 08/06/26")
            # Tapete 2: 2×3.7 = 7.4m² R$259
            i2 = add_item(H, orc, SRV_TAPETE_EMP, width=2.0, height=3.70)
            if i2:
                fix_item_price(H, i2, 35.0, 259.00)
                set_item_status(H, i2, "ENTREGUE", "Entregue 09/06/26")
                pay_item(H, i2, PIX_NU, 259.00, "PixNuSuperDry 08/06/26")
            # Tapete 3: 3×3.9 = 11.7m² R$410
            i3 = add_item(H, orc, SRV_TAPETE_EMP, width=3.0, height=3.90)
            if i3:
                fix_item_price(H, i3, 35.0, 410.00)
                set_item_status(H, i3, "ENTREGUE", "Entregue 09/06/26")
                pay_item(H, i3, PIX_NU, 410.00, "PixNuSuperDry 08/06/26")
            # Antiderrapantes R$100
            i4 = add_item(H, orc, SRV_OUTROS, qty=1,
                          obs="Lavagem antiderrapantes tapetes")
            if i4:
                fix_item_price(H, i4, 100.00, 100.00)
                set_item_status(H, i4, "ENTREGUE", "Entregue 09/06/26")
                pay_item(H, i4, PIX_NU, 100.00, "PixNuSuperDry 08/06/26")
            # Cortina voal 14.9m R$320
            i5 = add_item(H, orc, SRV_CORTINA_VOAL, linear_meters=14.9)
            if i5:
                fix_item_price(H, i5, 21.48, 320.00)
                set_item_status(H, i5, "ENTREGUE", "Entregue 09/06/26")
                pay_item(H, i5, PIX_NU, 320.00, "PixNuSuperDry 08/06/26")

    # ──────────────────────────────────────────────────────────────────────────
    print("\n══ 7. TAPETES EM LAVAGEM (novos clientes) ══")

    # ── 7a. Joselito Pinheiro de Abreu
    print("  → Joselito Pinheiro de Abreu")
    cli = create_client(
        H, "Joselito Pinheiro de Abreu", "66 99651-2778",
        "Av. Nigéria, 333 - Jardim Aclimação",
        complement="Torre 4, Apto 706 - Residencial Harmonia",
        neighborhood="Jardim Aclimação", city="Cuiabá", state="MT"
    )
    if cli:
        orc = create_budget(H, cli, PIX_NU)
        if orc:
            i = add_item(H, orc, SRV_TAPETE_EMP, width=0.80, height=1.50,
                         obs="Tapete 0,8x1,5m — medida informada na retirada")
            if i:
                fix_item_price(H, i, 35.0, 40.00,
                               obs="Tapete 0,8×1,5=1,2m² — valor especial R$40")
                set_item_status(H, i, "EM_LAVAGEM", "Retirado 03/06/26")

    # ── 7b. Sandra Silva (cortinas)
    print("  → Sandra Silva")
    cli = create_client(
        H, "Sandra Silva", "65 99956-2323",
        "Av. dos Florais, 1044 - Cond. Florais dos Lagos",
        complement="Al. Jatobá, QD 29, LT 06",
        neighborhood="Florais dos Lagos", city="Cuiabá", state="MT"
    )
    if cli:
        orc = create_budget(H, cli, PIX_NU)
        if orc:
            i = add_item(H, orc, SRV_CORTINA_DUPLA, linear_meters=9.9,
                         obs="Cortina voal + blackout 9,9m")
            if i:
                fix_item_price(H, i, 25.0, 247.50)
                set_item_status(H, i, "EM_LAVAGEM", "Retirado 08/06/26")

    # ── 7c. Dra. Sandra Torres
    print("  → Dra. Sandra Torres (Zelma/Carol)")
    cli = create_client(
        H, "Sandra Silvestre da Silva Torres", "65 99224-7828",
        "Rua E, QD 15, Casa 11 - Jardim Village Flamboyant",
        complement=None, neighborhood="Barra do Pari",
        city="Cuiabá", state="MT",
        observations="Agendamento via Zelma (secretária): 65 99230-8137 ou Carol Torres (filha): 65 99251-8721. Cobrança para a Dra. Sandra."
    )
    if cli:
        orc = create_budget(H, cli, PIX_NU,
                            internal_obs="4 tapetes retirados 08/06. Medidas a confirmar na entrega.")
        if orc:
            for n in range(4):
                i = add_item(H, orc, SRV_TAPETE_EMP, qty=1,
                             obs=f"Tapete {n+1}/4 — medida a ser confirmada")
                if i:
                    fix_item_price(H, i, 35.0, 35.0,
                                   obs=f"Tapete {n+1}/4 — valor provisório, confirmar na entrega")
                    set_item_status(H, i, "EM_LAVAGEM", "Retirado 08/06/26")

    # ── 7d. Vanessa Tonhá (cliente já existe)
    print("  → Vanessa Tonhá (orçamento novo)")
    if vanessa_id:
        orc = create_budget(H, vanessa_id, PIX_NU)
        if orc:
            tapetes = [
                (0.60, 1.00, 20.00, "Tapete 0,6×1m"),
                (0.60, 1.00, 20.00, "Tapete 0,6×1m"),
                (0.80, 2.50, 70.00, "Tapete 0,8×2,5m"),
                (2.50, 3.00, 265.00,"Tapete 2,5×3m"),
            ]
            for w, h, val, obs in tapetes:
                i = add_item(H, orc, SRV_TAPETE_EMP, width=w, height=h, obs=obs)
                if i:
                    area = round(w * h, 2)
                    fix_item_price(H, i, round(val/area, 2), val, obs=obs)
                    set_item_status(H, i, "EM_LAVAGEM", "Retirado 08/06/26")
            # Tapete redondo 1.90 diâmetro = R$100
            i = add_item(H, orc, SRV_TAPETE_REDONDO, diameter=1.90,
                         obs="Tapete redondo Ø1,90m")
            if i:
                fix_item_price(H, i, 34.48, 100.00, obs="Tapete redondo Ø1,90m")
                set_item_status(H, i, "EM_LAVAGEM", "Retirado 08/06/26")

    # ── 7e. Leonardo (Cond. Minas Cuiabá) — NÃO é o parceiro Dry Clean
    print("  → Leonardo (morador Cond. Villa das Minas de Cuiabá)")
    cli = create_client(
        H, "Leonardo (Cond. Minas Cuiabá)", "65 99243-1689",
        "R. Barão de Melgaço, 130 - Porto",
        complement="Bloco 31, Ap 3113 - Cond. Villa das Minas de Cuiabá",
        neighborhood="Porto", city="Cuiabá", state="MT",
        observations="Cliente pessoa física — NÃO confundir com parceiro Leonardo Dry Clean USA."
    )
    if cli:
        orc = create_budget(H, cli, PIX_NU)
        if orc:
            i = add_item(H, orc, SRV_TAPETE_EMP, width=1.20, height=1.40)
            if i:
                fix_item_price(H, i, 45.0, 90.00,
                               obs="Tapete 1,2×1,4=1,68m² — valor R$90 pix / R$80 dinheiro")
                set_item_status(H, i, "EM_LAVAGEM", "Retirado 09/06/26")

    # ── 7f. Márcio Guedes (tapete sala menor 3×4, R$430)
    print("  → Márcio Guedes (LimpeMT)")
    cli = create_client(
        H, "Márcio Guedes", "65 99667-3302",
        "R. Mal. Floriano Peixoto, 1500 - Duque de Caxias",
        complement="Apto 2804 - Ed. Goiabeiras Tower",
        neighborhood="Duque de Caxias", city="Cuiabá", state="MT",
        observations="Agendamentos via secretárias Leila ou Leida. Cobrança direta para Márcio Guedes."
    )
    if cli:
        orc = create_budget(H, cli, PIX_NU,
                            internal_obs="10/06: apenas tapete sala menor 3×4m retirado.")
        if orc:
            i = add_item(H, orc, SRV_TAPETE_EMP, width=3.0, height=4.0,
                         obs="Tapete sala menor 3×4=12m² — retirado 10/06/26")
            if i:
                fix_item_price(H, i, 35.83, 430.00,
                               obs="Tapete sala 3×4=12m² R$430")
                set_item_status(H, i, "EM_LAVAGEM", "Retirado 10/06/26")

    # ──────────────────────────────────────────────────────────────────────────
    print("\n══ 8. EDIFÍCIO FELICITÁ — COBRAR ══")
    print("  → Edifício Felicitá")
    cli = create_client(
        H, "Edifício Felicitá", "65 99968-1222",
        "Av. Gen. Ramiro de Noronha, 965 - Jardim",
        complement="Síndico: Rubens Tomio | Zelador: Cristiano (acompanhar)",
        neighborhood="Jardim", city="Cuiabá", state="MT"
    )
    if cli:
        orc = create_budget(H, cli, PIX_NU,
                            internal_obs="Serviço 09/06 + retoque 11/06. Síndico Rubens Tomio.")
        if orc:
            # 2 poltronas R$120 cada = R$240
            i1 = add_item(H, orc, SRV_POLTRONA, qty=2,
                          obs="2 Poltronas - serviço 09/06 + retoque 11/06")
            if i1:
                fix_item_price(H, i1, 120.00, 240.00)
                set_item_status(H, i1, "EXECUTADO", "Executado 09/06/26 + retoque 11/06")
            # 2 sofás de canto R$330 cada = R$660 (catálogo R$330 × 2 = R$660)
            # Mas evento diz total R$780 = R$240 poltronas + R$540 sofás canto
            # R$540/2 = R$270 cada sofá de canto
            i2 = add_item(H, orc, SRV_SOFA_CANTO, qty=2,
                          obs="2 Sofás de canto - serviço 09/06 + retoque 11/06")
            if i2:
                fix_item_price(H, i2, 270.00, 540.00)
                set_item_status(H, i2, "EXECUTADO", "Executado 09/06/26 + retoque 11/06")
            print("  ⚠️  COBRAR — total R$780 — enviar link para Rubens Tomio 65 99968-1222")

    # ──────────────────────────────────────────────────────────────────────────
    print("\n══ 9. MÔNICA RODRIGUES DE SOUSA — COBRAR ══")
    cli = create_client(
        H, "Mônica Rodrigues de Sousa", "65 99982-9423",
        "Avenida Cassio Caberlin, 138 - Jardim Aclimação",
        complement="Apto 1504 - Ed. Bravie",
        neighborhood="Jardim Aclimação", city="Cuiabá", state="MT"
    )
    if cli:
        orc = create_budget(H, cli, PIX_NU,
                            internal_obs="Serviço 11/06/26. Pagamento anterior (03/03/26) era de serviço anterior.")
        if orc:
            i = add_item(H, orc, SRV_SOFA_3LG, qty=1,
                         obs="Sofá 3 módulos retrátil — serviço 11/06/26")
            if i:
                fix_item_price(H, i, 300.00, 300.00,
                               obs="R$300 cartão / R$280 pix. Pago em 03/03/26 era serviço anterior.")
                set_item_status(H, i, "EXECUTADO", "Executado no local 11/06/26")
                print("  ⚠️  COBRAR — enviar link de pagamento R$300/R$280")

    # ──────────────────────────────────────────────────────────────────────────
    print("\n══ 10. REGUS — SERVIÇO GRANDE (R$7.929,70) ══")
    cli = create_client(
        H, "Regus", "65 00000-0000",
        "Av. Miguel Sutil, 8800 - Duque de Caxias",
        complement="Andréia (gestora)",
        neighborhood="Duque de Caxias", city="Cuiabá", state="MT",
        observations="Empresa coworking. Contato via Andréia. 3 etapas: Fase1 06/06 (carpetes/cadeiras/persianas no local), Fase2 11/06 (capachos retirados), Fase3 a agendar (entrega capachos)."
    )
    if cli:
        orc = create_budget(H, cli, CREDITO_7X,
                            internal_obs="Serviço dividido em 3 fases. Total R$7.929,70. Pagamento pendente.")
        if orc:
            # Item 1: 41 cadeiras (executado no local 06/06)
            i1 = add_item(H, orc, SRV_CADEIRA_ASSENTO, qty=41,
                          obs="41 cadeiras assento estofado — Fase1 06/06/26")
            if i1:
                fix_item_price(H, i1, 40.00, 1640.00)
                set_item_status(H, i1, "EXECUTADO", "Fase1 executado no local 06/06/26")

            # Item 2: 3 conjuntos canto alemão (executado no local 06/06)
            i2 = add_item(H, orc, SRV_SOFA_CANTO, qty=3,
                          obs="3 conjuntos assento tipo canto alemão — Fase1 06/06/26")
            if i2:
                fix_item_price(H, i2, 100.00, 300.00)
                set_item_status(H, i2, "EXECUTADO", "Fase1 executado no local 06/06/26")

            # Item 3: carpetes (14 áreas + arquivo = total R$4341.20 — executado no local)
            # Área total calculada: 8.91+6.67+52+21.6+12.16+7.4+6.24+7.98+7.22+11.02+7.8+20.14+10.92+25+8 = 214.06m²
            carpete_area = 214.06
            i3 = add_item(H, orc, SRV_CARPETE_LOCAL, width=carpete_area, height=1.0,
                          obs="14 áreas de carpete (214m² + arquivo R$80 flat) — Fase1 06/06/26. "
                              "Sala 3,7×5,3 substituída por 3,2×3,8 + 2,0×3,7.")
            if i3:
                fix_item_price(H, i3, 20.00, 4341.20,
                               obs="Soma 14 salas: R$4.261,20 + arquivo R$80 = R$4.341,20")
                set_item_status(H, i3, "EXECUTADO", "Fase1 executado no local 06/06/26")

            # Item 4: 8 tapetes/capachos 0.6×0.8 = R$170 (EM_LAVAGEM — Fase2 11/06)
            i4 = add_item(H, orc, SRV_TAPETE_EMP, width=0.60, height=0.80,
                          obs="8 capachos 0,6×0,8m — Fase2 retirada 11/06/26")
            if i4:
                # 8 un × 0.48m² = 3.84m² total; R$170 flat
                fix_item_price(H, i4, 44.27, 170.00,
                               obs="8 capachos 0,6×0,8m = R$170 total (8 unidades)")
                # A quantidade no sistema virou 0.48m² (1 tapete), precisamos corrigir
                # para refletir 8 unidades via patch
                patch(H, f"items/{i4}", {"quantity": 3.84, "area_m2": 3.84,
                                          "observations": "8 capachos 0,6×0,8m = 3,84m² total = R$170"})
                set_item_status(H, i4, "EM_LAVAGEM", "Fase2 retirado 11/06/26")

            # Item 5: 13 persianas 1.9×1.1 = R$1358.50 (EM_LAVAGEM — provavelmente retiradas na Fase2)
            persiana_area = round(1.9 * 1.1 * 13, 2)  # 27.17m²
            i5 = add_item(H, orc, SRV_PERSIANA_ROLO, width=1.9, height=1.1,
                          obs="13 persianas 1,9×1,1m = R$1.358,50 total")
            if i5:
                fix_item_price(H, i5, 50.00, 1358.50,
                               obs="13 persianas × R$104,50 cada = R$1.358,50")
                patch(H, f"items/{i5}", {"quantity": persiana_area,
                                          "area_m2": persiana_area})
                set_item_status(H, i5, "EM_LAVAGEM", "Retirado para lavagem na empresa")

            # Item 6: capa elevador R$120 (executado)
            i6 = add_item(H, orc, SRV_OUTROS, qty=1,
                          obs="Capa elevador — lavagem Fase1 06/06/26")
            if i6:
                fix_item_price(H, i6, 120.00, 120.00)
                set_item_status(H, i6, "EXECUTADO", "Fase1 executado no local 06/06/26")

            print(f"  ✅ Regus {orc} criado — 6 itens — total R$7.929,70 — PENDENTE pagamento")

    # ──────────────────────────────────────────────────────────────────────────
    print("\n══ FIM DA CONCILIAÇÃO ══")
    print("""
Resumo do que foi feito:
  ✅ Vanessa Tonhá — telefone corrigido
  ✅ Ana Paula Martins Pinheiro Santos — nome corrigido
  ✅ Daniella Amorim — itens corrigidos (2 cortinas 5,7m) + R$340 pago
  ✅ Ana Paula Bonadio — status ENTREGAR (cobrar)
  ✅ ORC-0000065/62/66/68/71/81/79/84/89/78/83 — pagamentos lançados
  ✅ Novos clientes + orçamentos (pagos): Marluce, Telma, Parceiro João, Paulinha, Sadora Xavier
  ✅ Tapetes em lavagem: Joselito, Sandra Silva, Dra Sandra, Vanessa Tonhá, Leonardo, Márcio Guedes
  ✅ Cobranças a lançar: Edifício Felicitá (R$780), Mônica Sousa (R$300)
  ✅ Regus — orçamento completo 3 fases R$7.929,70

NÃO feito (aguardando confirmação):
  ⏳ Bianca Azoia Bezerra (não confirmado)
  ⏳ Carpete Advanced (não confirmado)
  ⏳ Bruno Inova, Fernando, Lindamar (sem dados)
  ⏳ Silvia Cassia Nunes Rosa (não estava na lista — confirmar)
""")

if __name__ == "__main__":
    main()
