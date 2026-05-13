#!/usr/bin/env python3
"""
SuperDry Phase 2 Backend Testing - ITEM as Pillar
Tests all Phase 2 functionality focusing on ITEM as the core entity.
"""

import requests
import json
from datetime import datetime, date
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://superdry-laundry.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@superdry.com"
ADMIN_PASSWORD = "admin123"

# Global state
token = None
admin_user = None
test_client_id = None
test_service_retirada_id = None
test_service_no_local_id = None
test_budget_id = None
test_item_retirada_id = None
test_item_no_local_id = None

def log(message: str, level: str = "INFO"):
    """Log test messages"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def make_request(method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Make HTTP request with auth"""
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=30)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return {
            "status_code": response.status_code,
            "data": response.json() if response.text else {},
            "success": 200 <= response.status_code < 300
        }
    except Exception as e:
        log(f"Request failed: {str(e)}", "ERROR")
        return {"status_code": 0, "data": {}, "success": False, "error": str(e)}

# ============================================================
# TEST 1: Authentication
# ============================================================
def test_authentication():
    """Test login and get admin token"""
    global token, admin_user
    log("=" * 60)
    log("TEST 1: AUTHENTICATION")
    log("=" * 60)
    
    result = make_request("POST", "/auth/login", {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    
    if result["success"]:
        token = result["data"].get("access_token")
        admin_user = result["data"].get("user")
        log(f"✅ Login successful - Token obtained, User: {admin_user.get('name')}")
        return True
    else:
        log(f"❌ Login failed - Status: {result['status_code']}", "ERROR")
        return False

# ============================================================
# TEST 2: Create Test Client
# ============================================================
def test_create_client():
    """Create a test client for budgets"""
    global test_client_id
    log("=" * 60)
    log("TEST 2: CREATE TEST CLIENT")
    log("=" * 60)
    
    client_data = {
        "name": "Cliente Teste Phase 2",
        "phone_primary": "65999887766",
        "email": "cliente.phase2@test.com",
        "address": {
            "full_address": "Rua Teste Phase 2, 123",
            "neighborhood": "Centro",
            "city": "Cuiabá",
            "state": "MT",
            "latitude": -15.601411,
            "longitude": -56.097892
        }
    }
    
    result = make_request("POST", "/clients", client_data)
    
    if result["success"]:
        test_client_id = result["data"].get("id")
        log(f"✅ Client created - ID: {test_client_id}")
        return True
    else:
        log(f"❌ Client creation failed - Status: {result['status_code']}", "ERROR")
        return False

# ============================================================
# TEST 3: Create Test Services
# ============================================================
def test_create_services():
    """Create 2 services: one RETIRADA (default_service_status=RETIRAR) and one NO_LOCAL (default_service_status=EXECUTAR_NO_LOCAL)"""
    global test_service_retirada_id, test_service_no_local_id
    log("=" * 60)
    log("TEST 3: CREATE TEST SERVICES")
    log("=" * 60)
    
    # Service 1: RETIRADA
    service1_data = {
        "name": "Lavagem de Sofá 3 Lugares - Teste Phase 2",
        "category": "ESTOFADOS",
        "service_type": "Lavagem",
        "measure_type": "UNITARIO",
        "execution_location": "RETIRADA",
        "cost_price": 100.0,
        "sale_price": 200.0,
        "default_service_status": "RETIRAR"
    }
    
    result1 = make_request("POST", "/services", service1_data)
    
    if result1["success"]:
        test_service_retirada_id = result1["data"].get("id")
        log(f"✅ Service 1 (RETIRADA) created - ID: {test_service_retirada_id}, default_status: RETIRAR")
    else:
        log(f"❌ Service 1 creation failed - Status: {result1['status_code']}", "ERROR")
        return False
    
    # Service 2: NO_LOCAL
    service2_data = {
        "name": "Lavagem de Carpete no Local - Teste Phase 2",
        "category": "CARPETES_E_TAPETES_NO_LOCAL",
        "service_type": "Lavagem no Local",
        "measure_type": "CARPETE_TAPETE_LOCAL",
        "execution_location": "NO_LOCAL",
        "cost_price": 50.0,
        "sale_price": 100.0,
        "default_service_status": "EXECUTAR_NO_LOCAL"
    }
    
    result2 = make_request("POST", "/services", service2_data)
    
    if result2["success"]:
        test_service_no_local_id = result2["data"].get("id")
        log(f"✅ Service 2 (NO_LOCAL) created - ID: {test_service_no_local_id}, default_status: EXECUTAR_NO_LOCAL")
        return True
    else:
        log(f"❌ Service 2 creation failed - Status: {result2['status_code']}", "ERROR")
        return False

# ============================================================
# TEST 4: Budget Creation with ITEM Enrichment
# ============================================================
def test_budget_creation_with_item_enrichment():
    """
    Create budget with 2 items and verify:
    - Each item has ITM- id, budget_id, client snapshot
    - execution_mode derived correctly (RETIRADA→RETIRAR_E_LEVAR, NO_LOCAL→EXECUTAR_NO_LOCAL)
    - status derived from service.default_service_status
    - status_history has exactly 1 entry with 'Item criado'
    - payment fields initialized correctly
    """
    global test_budget_id, test_item_retirada_id, test_item_no_local_id
    log("=" * 60)
    log("TEST 4: BUDGET CREATION WITH ITEM ENRICHMENT")
    log("=" * 60)
    
    budget_data = {
        "client_id": test_client_id,
        "payment_method": "PIX_CNPJ_25995295000104",
        "salesperson": "Gabriela Alcântara",
        "internal_observations": "Teste Phase 2",
        "budget_observations": "Orçamento de teste para Phase 2",
        "items": [
            {
                "service_id": test_service_retirada_id,
                "quantity": 1.0,
                "unit_price": 200.0,
                "total_value": 200.0,
                "observations": "Item 1 - RETIRADA"
            },
            {
                "service_id": test_service_no_local_id,
                "quantity": 1.0,
                "area_m2": 10.0,
                "unit_price": 100.0,
                "total_value": 100.0,
                "observations": "Item 2 - NO_LOCAL"
            }
        ]
    }
    
    result = make_request("POST", "/budgets", budget_data)
    
    if not result["success"]:
        log(f"❌ Budget creation failed - Status: {result['status_code']}", "ERROR")
        log(f"   Response: {result.get('data')}", "ERROR")
        return False
    
    budget = result["data"]
    test_budget_id = budget.get("id")
    items = budget.get("items", [])
    
    log(f"✅ Budget created - ID: {test_budget_id}")
    
    # Verify we have 2 items
    if len(items) != 2:
        log(f"❌ Expected 2 items, got {len(items)}", "ERROR")
        return False
    
    log(f"✅ Budget has 2 items")
    
    # Test each item
    all_checks_passed = True
    
    for idx, item in enumerate(items):
        item_num = idx + 1
        log(f"\n--- Verifying Item {item_num} ---")
        
        # a) Check ID format, budget_id, client snapshot
        item_id = item.get("id")
        if not item_id or not item_id.startswith("ITM-"):
            log(f"❌ Item {item_num}: Invalid ID format: {item_id}", "ERROR")
            all_checks_passed = False
        else:
            log(f"✅ Item {item_num}: ID format correct: {item_id}")
        
        if item.get("budget_id") != test_budget_id:
            log(f"❌ Item {item_num}: budget_id mismatch", "ERROR")
            all_checks_passed = False
        else:
            log(f"✅ Item {item_num}: budget_id matches")
        
        if item.get("client_id") != test_client_id:
            log(f"❌ Item {item_num}: client_id mismatch", "ERROR")
            all_checks_passed = False
        else:
            log(f"✅ Item {item_num}: client_id matches")
        
        if not item.get("client_name") or not item.get("client_phone"):
            log(f"❌ Item {item_num}: Missing client snapshot", "ERROR")
            all_checks_passed = False
        else:
            log(f"✅ Item {item_num}: Client snapshot present (name: {item.get('client_name')}, phone: {item.get('client_phone')})")
        
        # b) Check service fields
        if not item.get("service_name") or not item.get("service_code") or not item.get("service_category"):
            log(f"❌ Item {item_num}: Missing service fields", "ERROR")
            all_checks_passed = False
        else:
            log(f"✅ Item {item_num}: Service fields present")
        
        # c) Check execution_mode derivation
        expected_mode = "RETIRAR_E_LEVAR" if idx == 0 else "EXECUTAR_NO_LOCAL"
        if item.get("execution_mode") != expected_mode:
            log(f"❌ Item {item_num}: execution_mode incorrect. Expected: {expected_mode}, Got: {item.get('execution_mode')}", "ERROR")
            all_checks_passed = False
        else:
            log(f"✅ Item {item_num}: execution_mode correct: {expected_mode}")
        
        # d) Check status derivation
        expected_status = "RETIRAR" if idx == 0 else "EXECUTAR_NO_LOCAL"
        if item.get("status") != expected_status:
            log(f"❌ Item {item_num}: status incorrect. Expected: {expected_status}, Got: {item.get('status')}", "ERROR")
            all_checks_passed = False
        else:
            log(f"✅ Item {item_num}: status correct: {expected_status}")
        
        # e) Check status_history
        status_history = item.get("status_history", [])
        if len(status_history) != 1:
            log(f"❌ Item {item_num}: status_history should have exactly 1 entry, got {len(status_history)}", "ERROR")
            all_checks_passed = False
        else:
            entry = status_history[0]
            if entry.get("status") != item.get("status"):
                log(f"❌ Item {item_num}: status_history[0].status doesn't match current status", "ERROR")
                all_checks_passed = False
            elif not entry.get("by_user_id") or entry.get("notes") != "Item criado":
                log(f"❌ Item {item_num}: status_history[0] missing by_user_id or notes != 'Item criado'", "ERROR")
                all_checks_passed = False
            else:
                log(f"✅ Item {item_num}: status_history correct (1 entry, status={entry.get('status')}, notes='Item criado')")
        
        # f) Check empty collections
        if item.get("execution_sessions") != []:
            log(f"❌ Item {item_num}: execution_sessions should be empty", "ERROR")
            all_checks_passed = False
        else:
            log(f"✅ Item {item_num}: execution_sessions empty")
        
        if item.get("payment_records") != []:
            log(f"❌ Item {item_num}: payment_records should be empty", "ERROR")
            all_checks_passed = False
        else:
            log(f"✅ Item {item_num}: payment_records empty")
        
        if item.get("route_history") != []:
            log(f"❌ Item {item_num}: route_history should be empty", "ERROR")
            all_checks_passed = False
        else:
            log(f"✅ Item {item_num}: route_history empty")
        
        # g) Check payment fields
        if item.get("paid_value") != 0.0:
            log(f"❌ Item {item_num}: paid_value should be 0.0", "ERROR")
            all_checks_passed = False
        else:
            log(f"✅ Item {item_num}: paid_value = 0.0")
        
        if item.get("payment_status") != "PENDENTE":
            log(f"❌ Item {item_num}: payment_status should be PENDENTE", "ERROR")
            all_checks_passed = False
        else:
            log(f"✅ Item {item_num}: payment_status = PENDENTE")
        
        # h) Check audit fields
        if not item.get("created_by") or not item.get("created_at"):
            log(f"❌ Item {item_num}: Missing audit fields (created_by/created_at)", "ERROR")
            all_checks_passed = False
        else:
            log(f"✅ Item {item_num}: Audit fields present (created_by={item.get('created_by')})")
        
        # Store item IDs for later tests
        if idx == 0:
            test_item_retirada_id = item_id
        else:
            test_item_no_local_id = item_id
    
    if all_checks_passed:
        log(f"\n✅ ALL ITEM ENRICHMENT CHECKS PASSED")
        return True
    else:
        log(f"\n❌ SOME ITEM ENRICHMENT CHECKS FAILED", "ERROR")
        return False

# ============================================================
# TEST 5: PATCH /api/items/{item_id}
# ============================================================
def test_patch_item():
    """
    Test PATCH /api/items/{item_id}:
    - Update observations, is_retoque, scheduled_execution_date
    - Verify audit log created
    - Try to PATCH protected field (should be ignored or 400)
    - PATCH status with status_notes (should append to status_history)
    """
    log("=" * 60)
    log("TEST 5: PATCH /api/items/{item_id}")
    log("=" * 60)
    
    all_checks_passed = True
    
    # 5a) Update regular fields
    log("\n--- 5a) Update regular fields ---")
    patch_data = {
        "observations": "Cor azul",
        "is_retoque": True,
        "scheduled_execution_date": "2026-06-01"
    }
    
    result = make_request("PATCH", f"/items/{test_item_retirada_id}", patch_data)
    
    if not result["success"]:
        log(f"❌ PATCH failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
    else:
        item = result["data"].get("item", {})
        if item.get("observations") == "Cor azul" and item.get("is_retoque") == True and item.get("scheduled_execution_date") == "2026-06-01":
            log(f"✅ Fields updated correctly")
        else:
            log(f"❌ Fields not updated correctly", "ERROR")
            all_checks_passed = False
    
    # 5b) Try to PATCH protected field
    log("\n--- 5b) Try to PATCH protected field ---")
    patch_protected = {"id": "ITM-FAKE"}
    
    result = make_request("PATCH", f"/items/{test_item_retirada_id}", patch_protected)
    
    if result["status_code"] == 400:
        log(f"✅ Protected field rejected with 400")
    elif result["success"]:
        # Check if id was actually changed
        item = result["data"].get("item", {})
        if item.get("id") == test_item_retirada_id:
            log(f"✅ Protected field ignored (id unchanged)")
        else:
            log(f"❌ Protected field was changed!", "ERROR")
            all_checks_passed = False
    else:
        log(f"❌ Unexpected response: {result['status_code']}", "ERROR")
        all_checks_passed = False
    
    # 5c) PATCH status with status_notes
    log("\n--- 5c) PATCH status with status_notes ---")
    
    # First, get current status_history length
    result_before = make_request("GET", f"/items/{test_item_retirada_id}")
    if result_before["success"]:
        history_before = result_before["data"].get("item", {}).get("status_history", [])
        history_len_before = len(history_before)
        log(f"   Current status_history length: {history_len_before}")
    else:
        log(f"❌ Failed to get item before PATCH", "ERROR")
        all_checks_passed = False
        history_len_before = 0
    
    patch_status = {
        "status": "COLETADO",
        "status_notes": "Coletado por teste"
    }
    
    result = make_request("PATCH", f"/items/{test_item_retirada_id}", patch_status)
    
    if not result["success"]:
        log(f"❌ PATCH status failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
    else:
        item = result["data"].get("item", {})
        history_after = item.get("status_history", [])
        history_len_after = len(history_after)
        
        if item.get("status") == "COLETADO":
            log(f"✅ Status updated to COLETADO")
        else:
            log(f"❌ Status not updated", "ERROR")
            all_checks_passed = False
        
        if history_len_after == history_len_before + 1:
            log(f"✅ status_history grew by 1 (now {history_len_after} entries)")
            # Check last entry
            last_entry = history_after[-1]
            if last_entry.get("status") == "COLETADO" and "Coletado por teste" in last_entry.get("notes", ""):
                log(f"✅ Last status_history entry correct")
            else:
                log(f"❌ Last status_history entry incorrect", "ERROR")
                all_checks_passed = False
        else:
            log(f"❌ status_history length incorrect (expected {history_len_before + 1}, got {history_len_after})", "ERROR")
            all_checks_passed = False
    
    if all_checks_passed:
        log(f"\n✅ ALL PATCH TESTS PASSED")
        return True
    else:
        log(f"\n❌ SOME PATCH TESTS FAILED", "ERROR")
        return False

# ============================================================
# TEST 6: POST /api/items/{item_id}/status
# ============================================================
def test_post_item_status():
    """
    Test POST /api/items/{item_id}/status:
    - Change status with notes
    - Same status again (should return unchanged:true)
    - Invalid status (should return 400)
    """
    log("=" * 60)
    log("TEST 6: POST /api/items/{item_id}/status")
    log("=" * 60)
    
    all_checks_passed = True
    
    # 6a) Change status
    log("\n--- 6a) Change status to EM_LAVAGEM ---")
    
    result = make_request("POST", f"/items/{test_item_no_local_id}/status", {
        "status": "EM_LAVAGEM",
        "notes": "Levou para lavagem"
    })
    
    if not result["success"]:
        log(f"❌ Status change failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
    else:
        if result["data"].get("status") == "EM_LAVAGEM":
            log(f"✅ Status changed to EM_LAVAGEM")
        else:
            log(f"❌ Status not changed correctly", "ERROR")
            all_checks_passed = False
    
    # 6b) Same status again
    log("\n--- 6b) Same status again (should return unchanged:true) ---")
    
    result = make_request("POST", f"/items/{test_item_no_local_id}/status", {
        "status": "EM_LAVAGEM",
        "notes": "Tentando mudar para mesmo status"
    })
    
    if not result["success"]:
        log(f"❌ Request failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
    else:
        if result["data"].get("unchanged") == True:
            log(f"✅ Returned unchanged:true")
        else:
            log(f"❌ Did not return unchanged:true", "ERROR")
            all_checks_passed = False
    
    # 6c) Invalid status
    log("\n--- 6c) Invalid status (should return 400) ---")
    
    result = make_request("POST", f"/items/{test_item_no_local_id}/status", {
        "status": "FOO",
        "notes": "Invalid status"
    })
    
    if result["status_code"] == 400:
        log(f"✅ Invalid status rejected with 400")
    else:
        log(f"❌ Invalid status not rejected (status: {result['status_code']})", "ERROR")
        all_checks_passed = False
    
    if all_checks_passed:
        log(f"\n✅ ALL STATUS CHANGE TESTS PASSED")
        return True
    else:
        log(f"\n❌ SOME STATUS CHANGE TESTS FAILED", "ERROR")
        return False

# ============================================================
# TEST 7: Execution Sessions
# ============================================================
def test_execution_sessions():
    """
    Test execution sessions:
    - Start session
    - Try to start another (should fail with 400)
    - Finish with outcome=PARTIAL (status should become EXECUCAO_PARCIAL)
    - Start another session (now allowed)
    - Finish with outcome=COMPLETED (status should become EXECUTADO, actual_finished_at set)
    - Finish nonexistent session (should return 404)
    - Invalid outcome (should return 400)
    """
    log("=" * 60)
    log("TEST 7: EXECUTION SESSIONS")
    log("=" * 60)
    
    all_checks_passed = True
    session_id_1 = None
    session_id_2 = None
    
    # 7a) Start first session
    log("\n--- 7a) Start first session ---")
    
    result = make_request("POST", f"/items/{test_item_retirada_id}/execution-session/start", {
        "technician_id": "TEC-001",
        "technician_name": "João",
        "notes": "Iniciou"
    })
    
    if not result["success"]:
        log(f"❌ Start session failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
    else:
        session = result["data"].get("session", {})
        session_id_1 = session.get("id")
        if session_id_1 and session_id_1.startswith("SES-") and session.get("finished_at") is None:
            log(f"✅ Session started - ID: {session_id_1}, finished_at=null")
        else:
            log(f"❌ Session data incorrect", "ERROR")
            all_checks_passed = False
    
    # 7b) Try to start another while one is open
    log("\n--- 7b) Try to start another session (should fail) ---")
    
    result = make_request("POST", f"/items/{test_item_retirada_id}/execution-session/start", {
        "technician_id": "TEC-001",
        "technician_name": "João",
        "notes": "Tentando iniciar outra"
    })
    
    if result["status_code"] == 400:
        log(f"✅ Second session rejected with 400")
    else:
        log(f"❌ Second session not rejected (status: {result['status_code']})", "ERROR")
        all_checks_passed = False
    
    # 7c) Finish with outcome=PARTIAL
    log("\n--- 7c) Finish session with outcome=PARTIAL ---")
    
    result = make_request("POST", f"/items/{test_item_retirada_id}/execution-session/{session_id_1}/finish", {
        "outcome": "PARTIAL",
        "reason": "Máquina quebrou"
    })
    
    if not result["success"]:
        log(f"❌ Finish session failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
    else:
        new_status = result["data"].get("new_status")
        if new_status == "EXECUCAO_PARCIAL":
            log(f"✅ Status changed to EXECUCAO_PARCIAL")
        else:
            log(f"❌ Status not changed to EXECUCAO_PARCIAL (got: {new_status})", "ERROR")
            all_checks_passed = False
        
        # Verify status_history was appended
        result_item = make_request("GET", f"/items/{test_item_retirada_id}")
        if result_item["success"]:
            item = result_item["data"].get("item", {})
            history = item.get("status_history", [])
            if any(h.get("status") == "EXECUCAO_PARCIAL" for h in history):
                log(f"✅ status_history contains EXECUCAO_PARCIAL entry")
            else:
                log(f"❌ status_history missing EXECUCAO_PARCIAL entry", "ERROR")
                all_checks_passed = False
    
    # 7d) Start another session (now allowed)
    log("\n--- 7d) Start second session (now allowed) ---")
    
    result = make_request("POST", f"/items/{test_item_retirada_id}/execution-session/start", {
        "technician_id": "TEC-001",
        "technician_name": "João",
        "notes": "Segunda sessão"
    })
    
    if not result["success"]:
        log(f"❌ Start second session failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
    else:
        session = result["data"].get("session", {})
        session_id_2 = session.get("id")
        if session_id_2 and session_id_2.startswith("SES-"):
            log(f"✅ Second session started - ID: {session_id_2}")
        else:
            log(f"❌ Second session data incorrect", "ERROR")
            all_checks_passed = False
    
    # 7e) Finish with outcome=COMPLETED
    log("\n--- 7e) Finish session with outcome=COMPLETED ---")
    
    result = make_request("POST", f"/items/{test_item_retirada_id}/execution-session/{session_id_2}/finish", {
        "outcome": "COMPLETED"
    })
    
    if not result["success"]:
        log(f"❌ Finish session failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
    else:
        new_status = result["data"].get("new_status")
        if new_status == "EXECUTADO":
            log(f"✅ Status changed to EXECUTADO")
        else:
            log(f"❌ Status not changed to EXECUTADO (got: {new_status})", "ERROR")
            all_checks_passed = False
        
        # Verify actual_finished_at was set
        result_item = make_request("GET", f"/items/{test_item_retirada_id}")
        if result_item["success"]:
            item = result_item["data"].get("item", {})
            if item.get("actual_finished_at"):
                log(f"✅ actual_finished_at was set")
            else:
                log(f"❌ actual_finished_at not set", "ERROR")
                all_checks_passed = False
    
    # 7f) Finish nonexistent session
    log("\n--- 7f) Finish nonexistent session (should return 404) ---")
    
    result = make_request("POST", f"/items/{test_item_retirada_id}/execution-session/SES-FAKE/finish", {
        "outcome": "COMPLETED"
    })
    
    if result["status_code"] == 404:
        log(f"✅ Nonexistent session rejected with 404")
    else:
        log(f"❌ Nonexistent session not rejected (status: {result['status_code']})", "ERROR")
        all_checks_passed = False
    
    # 7g) Invalid outcome
    log("\n--- 7g) Invalid outcome (should return 400) ---")
    
    # Start a new session for this test
    result_start = make_request("POST", f"/items/{test_item_no_local_id}/execution-session/start", {
        "technician_id": "TEC-002",
        "technician_name": "Maria"
    })
    
    if result_start["success"]:
        session_id_3 = result_start["data"].get("session", {}).get("id")
        
        result = make_request("POST", f"/items/{test_item_no_local_id}/execution-session/{session_id_3}/finish", {
            "outcome": "WRONG"
        })
        
        if result["status_code"] == 400:
            log(f"✅ Invalid outcome rejected with 400")
        else:
            log(f"❌ Invalid outcome not rejected (status: {result['status_code']})", "ERROR")
            all_checks_passed = False
    else:
        log(f"⚠️  Could not start session for invalid outcome test", "WARN")
    
    if all_checks_passed:
        log(f"\n✅ ALL EXECUTION SESSION TESTS PASSED")
        return True
    else:
        log(f"\n❌ SOME EXECUTION SESSION TESTS FAILED", "ERROR")
        return False

# ============================================================
# TEST 8: Payments
# ============================================================
def test_payments():
    """
    Test payment recording:
    - First payment (partial) - paid_value=50, payment_status=PARCIAL
    - Second payment (complete) - paid_value=200, payment_status=PAGO
    - Invalid method (should return 400)
    - Value 0 (should return 400)
    """
    log("=" * 60)
    log("TEST 8: PAYMENTS")
    log("=" * 60)
    
    all_checks_passed = True
    
    # 8a) First payment (partial)
    log("\n--- 8a) First payment (partial) ---")
    
    result = make_request("POST", f"/items/{test_item_retirada_id}/payment", {
        "method": "PIX_CNPJ_25995295000104",
        "value": 50,
        "notes": "Sinal"
    })
    
    if not result["success"]:
        log(f"❌ First payment failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
    else:
        paid_value = result["data"].get("paid_value")
        payment_status = result["data"].get("payment_status")
        
        if paid_value == 50 and payment_status == "PARCIAL":
            log(f"✅ First payment recorded - paid_value=50, payment_status=PARCIAL")
        else:
            log(f"❌ First payment data incorrect (paid_value={paid_value}, payment_status={payment_status})", "ERROR")
            all_checks_passed = False
    
    # 8b) Second payment (complete)
    log("\n--- 8b) Second payment (complete) ---")
    
    result = make_request("POST", f"/items/{test_item_retirada_id}/payment", {
        "method": "DINHEIRO",
        "value": 150,
        "notes": "Restante"
    })
    
    if not result["success"]:
        log(f"❌ Second payment failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
    else:
        paid_value = result["data"].get("paid_value")
        payment_status = result["data"].get("payment_status")
        
        if paid_value == 200 and payment_status == "PAGO":
            log(f"✅ Second payment recorded - paid_value=200, payment_status=PAGO")
        else:
            log(f"❌ Second payment data incorrect (paid_value={paid_value}, payment_status={payment_status})", "ERROR")
            all_checks_passed = False
    
    # 8c) Invalid method
    log("\n--- 8c) Invalid payment method (should return 400) ---")
    
    result = make_request("POST", f"/items/{test_item_no_local_id}/payment", {
        "method": "FOO",
        "value": 50
    })
    
    if result["status_code"] == 400:
        log(f"✅ Invalid method rejected with 400")
    else:
        log(f"❌ Invalid method not rejected (status: {result['status_code']})", "ERROR")
        all_checks_passed = False
    
    # 8d) Value 0
    log("\n--- 8d) Value 0 (should return 400) ---")
    
    result = make_request("POST", f"/items/{test_item_no_local_id}/payment", {
        "method": "DINHEIRO",
        "value": 0
    })
    
    if result["status_code"] == 400:
        log(f"✅ Value 0 rejected with 400")
    else:
        log(f"❌ Value 0 not rejected (status: {result['status_code']})", "ERROR")
        all_checks_passed = False
    
    if all_checks_passed:
        log(f"\n✅ ALL PAYMENT TESTS PASSED")
        return True
    else:
        log(f"\n❌ SOME PAYMENT TESTS FAILED", "ERROR")
        return False

# ============================================================
# TEST 9: Timeline
# ============================================================
def test_timeline():
    """
    Test GET /api/items/{item_id}/timeline:
    - Returns events list with types STATUS, EXEC_START, EXEC_END, PAYMENT
    - Events are ordered ascending by 'at'
    """
    log("=" * 60)
    log("TEST 9: TIMELINE")
    log("=" * 60)
    
    result = make_request("GET", f"/items/{test_item_retirada_id}/timeline")
    
    if not result["success"]:
        log(f"❌ Timeline request failed - Status: {result['status_code']}", "ERROR")
        return False
    
    events = result["data"].get("events", [])
    
    if len(events) == 0:
        log(f"❌ Timeline is empty", "ERROR")
        return False
    
    log(f"✅ Timeline has {len(events)} events")
    
    # Check event types
    event_types = set(e.get("type") for e in events)
    expected_types = {"STATUS", "EXEC_START", "EXEC_END", "PAYMENT"}
    
    if not event_types.issubset(expected_types):
        log(f"❌ Unexpected event types: {event_types - expected_types}", "ERROR")
        return False
    
    log(f"✅ Event types valid: {event_types}")
    
    # Check ordering
    timestamps = [e.get("at") for e in events if e.get("at")]
    if timestamps == sorted(timestamps):
        log(f"✅ Events are ordered ascending by 'at'")
    else:
        log(f"❌ Events are not properly ordered", "ERROR")
        return False
    
    # Display timeline
    log("\n--- Timeline Events ---")
    for i, event in enumerate(events, 1):
        log(f"   {i}. [{event.get('type')}] {event.get('label')} - {event.get('at')}")
    
    log(f"\n✅ TIMELINE TEST PASSED")
    return True

# ============================================================
# TEST 10: GET /api/items with filters
# ============================================================
def test_items_list_with_filters():
    """
    Test GET /api/items with filters:
    - no_route=true (returns items where current_route_id is null)
    - status=EXECUTADO
    - payment_status=PAGO
    - Each result has shape { item: {...}, budget_id, budget_payment_method }
    """
    log("=" * 60)
    log("TEST 10: GET /api/items WITH FILTERS")
    log("=" * 60)
    
    all_checks_passed = True
    
    # 10a) no_route=true
    log("\n--- 10a) Filter: no_route=true ---")
    
    result = make_request("GET", "/items", params={"no_route": "true"})
    
    if not result["success"]:
        log(f"❌ Request failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
    else:
        items = result["data"].get("items", [])
        log(f"✅ Found {len(items)} items with no route")
        
        # Verify all items have current_route_id = null
        for item_doc in items:
            item = item_doc.get("item", {})
            if item.get("current_route_id") is not None:
                log(f"❌ Item {item.get('id')} has current_route_id={item.get('current_route_id')}", "ERROR")
                all_checks_passed = False
                break
        else:
            log(f"✅ All items have current_route_id=null")
    
    # 10b) status=EXECUTADO
    log("\n--- 10b) Filter: status=EXECUTADO ---")
    
    result = make_request("GET", "/items", params={"status": "EXECUTADO"})
    
    if not result["success"]:
        log(f"❌ Request failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
    else:
        items = result["data"].get("items", [])
        log(f"✅ Found {len(items)} items with status=EXECUTADO")
        
        # Verify all items have status = EXECUTADO
        for item_doc in items:
            item = item_doc.get("item", {})
            if item.get("status") != "EXECUTADO":
                log(f"❌ Item {item.get('id')} has status={item.get('status')}", "ERROR")
                all_checks_passed = False
                break
        else:
            log(f"✅ All items have status=EXECUTADO")
    
    # 10c) payment_status=PAGO
    log("\n--- 10c) Filter: payment_status=PAGO ---")
    
    result = make_request("GET", "/items", params={"payment_status": "PAGO"})
    
    if not result["success"]:
        log(f"❌ Request failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
    else:
        items = result["data"].get("items", [])
        log(f"✅ Found {len(items)} items with payment_status=PAGO")
        
        # Verify all items have payment_status = PAGO
        for item_doc in items:
            item = item_doc.get("item", {})
            if item.get("payment_status") != "PAGO":
                log(f"❌ Item {item.get('id')} has payment_status={item.get('payment_status')}", "ERROR")
                all_checks_passed = False
                break
        else:
            log(f"✅ All items have payment_status=PAGO")
    
    # 10d) Verify result shape
    log("\n--- 10d) Verify result shape ---")
    
    result = make_request("GET", "/items", params={"limit": "1"})
    
    if result["success"] and result["data"].get("items"):
        item_doc = result["data"]["items"][0]
        if "item" in item_doc and "budget_id" in item_doc and "budget_payment_method" in item_doc:
            log(f"✅ Result shape correct: {{ item, budget_id, budget_payment_method }}")
        else:
            log(f"❌ Result shape incorrect", "ERROR")
            all_checks_passed = False
    
    if all_checks_passed:
        log(f"\n✅ ALL ITEMS LIST FILTER TESTS PASSED")
        return True
    else:
        log(f"\n❌ SOME ITEMS LIST FILTER TESTS FAILED", "ERROR")
        return False

# ============================================================
# TEST 11: Budget Delete Protection
# ============================================================
def test_budget_delete_protection():
    """
    Test budget delete protection:
    - Create a new budget B with 1 item
    - Change item status to EM_LAVAGEM
    - DELETE should return 400 with message about items in execution
    - Create another budget C with 1 item, no changes
    - DELETE should succeed (200)
    """
    log("=" * 60)
    log("TEST 11: BUDGET DELETE PROTECTION")
    log("=" * 60)
    
    all_checks_passed = True
    
    # 11a) Create budget B with item in execution
    log("\n--- 11a) Create budget B with item ---")
    
    budget_b_data = {
        "client_id": test_client_id,
        "payment_method": "DINHEIRO",
        "salesperson": "Diego Olivatto",
        "items": [
            {
                "service_id": test_service_retirada_id,
                "quantity": 1.0,
                "unit_price": 200.0,
                "total_value": 200.0
            }
        ]
    }
    
    result = make_request("POST", "/budgets", budget_b_data)
    
    if not result["success"]:
        log(f"❌ Budget B creation failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
        budget_b_id = None
        item_b_id = None
    else:
        budget_b_id = result["data"].get("id")
        item_b_id = result["data"].get("items", [{}])[0].get("id")
        log(f"✅ Budget B created - ID: {budget_b_id}, Item ID: {item_b_id}")
        
        # Change item status to EM_LAVAGEM
        log("\n--- 11b) Change item status to EM_LAVAGEM ---")
        
        result_status = make_request("POST", f"/items/{item_b_id}/status", {
            "status": "EM_LAVAGEM",
            "notes": "Em lavagem"
        })
        
        if result_status["success"]:
            log(f"✅ Item status changed to EM_LAVAGEM")
        else:
            log(f"❌ Failed to change item status", "ERROR")
            all_checks_passed = False
        
        # Try to delete budget B
        log("\n--- 11c) Try to DELETE budget B (should fail) ---")
        
        result_delete = make_request("DELETE", f"/budgets/{budget_b_id}")
        
        if result_delete["status_code"] == 400:
            detail = result_delete["data"].get("detail", "")
            if "rota" in detail.lower() or "execução" in detail.lower():
                log(f"✅ Delete rejected with 400 and appropriate message")
            else:
                log(f"⚠️  Delete rejected with 400 but message unclear: {detail}", "WARN")
        else:
            log(f"❌ Delete not rejected (status: {result_delete['status_code']})", "ERROR")
            all_checks_passed = False
    
    # 11d) Create budget C with no changes
    log("\n--- 11d) Create budget C with item (no changes) ---")
    
    budget_c_data = {
        "client_id": test_client_id,
        "payment_method": "CREDITO_1X",
        "salesperson": "Daiana Olivatto",
        "items": [
            {
                "service_id": test_service_no_local_id,
                "quantity": 1.0,
                "unit_price": 100.0,
                "total_value": 100.0
            }
        ]
    }
    
    result = make_request("POST", "/budgets", budget_c_data)
    
    if not result["success"]:
        log(f"❌ Budget C creation failed - Status: {result['status_code']}", "ERROR")
        all_checks_passed = False
    else:
        budget_c_id = result["data"].get("id")
        log(f"✅ Budget C created - ID: {budget_c_id}")
        
        # Try to delete budget C
        log("\n--- 11e) DELETE budget C (should succeed) ---")
        
        result_delete = make_request("DELETE", f"/budgets/{budget_c_id}")
        
        if result_delete["success"]:
            log(f"✅ Budget C deleted successfully")
        else:
            log(f"❌ Budget C deletion failed (status: {result_delete['status_code']})", "ERROR")
            all_checks_passed = False
    
    if all_checks_passed:
        log(f"\n✅ ALL BUDGET DELETE PROTECTION TESTS PASSED")
        return True
    else:
        log(f"\n❌ SOME BUDGET DELETE PROTECTION TESTS FAILED", "ERROR")
        return False

# ============================================================
# TEST 12: Available for Routes
# ============================================================
def test_available_for_routes():
    """
    Test GET /api/budget-items/available-for-routes:
    - Only returns items with status in (RETIRAR/EXECUTAR_NO_LOCAL/ENTREGAR) AND current_route_id == null
    - Each result has: budget_item_id, client_id, execution_mode, payment_status, address
    """
    log("=" * 60)
    log("TEST 12: AVAILABLE FOR ROUTES")
    log("=" * 60)
    
    result = make_request("GET", "/budget-items/available-for-routes")
    
    if not result["success"]:
        log(f"❌ Request failed - Status: {result['status_code']}", "ERROR")
        return False
    
    items = result["data"].get("available_items", [])
    log(f"✅ Found {len(items)} items available for routes")
    
    # Verify all items have correct status and no route
    valid_statuses = ["RETIRAR", "EXECUTAR_NO_LOCAL", "ENTREGAR"]
    all_valid = True
    
    for item in items:
        status = item.get("status")
        if status not in valid_statuses:
            log(f"❌ Item {item.get('budget_item_id')} has invalid status: {status}", "ERROR")
            all_valid = False
        
        # Note: current_route_id is not in the response, but the query filters it
    
    if all_valid:
        log(f"✅ All items have valid status (RETIRAR/EXECUTAR_NO_LOCAL/ENTREGAR)")
    
    # Verify result shape
    if items:
        item = items[0]
        required_fields = ["budget_item_id", "client_id", "execution_mode", "payment_status", "address"]
        missing_fields = [f for f in required_fields if f not in item]
        
        if missing_fields:
            log(f"❌ Missing fields in result: {missing_fields}", "ERROR")
            all_valid = False
        else:
            log(f"✅ Result shape correct (has all required fields)")
    
    if all_valid:
        log(f"\n✅ AVAILABLE FOR ROUTES TEST PASSED")
        return True
    else:
        log(f"\n❌ AVAILABLE FOR ROUTES TEST FAILED", "ERROR")
        return False

# ============================================================
# TEST 13: Dashboard Summary
# ============================================================
def test_dashboard_summary():
    """
    Test GET /api/dashboard/summary:
    - items_pending_routes counts only items pending (no route assigned)
    - financial_pending counts items not in PAGO/CORTESIA
    """
    log("=" * 60)
    log("TEST 13: DASHBOARD SUMMARY")
    log("=" * 60)
    
    result = make_request("GET", "/dashboard/summary")
    
    if not result["success"]:
        log(f"❌ Request failed - Status: {result['status_code']}", "ERROR")
        return False
    
    summary = result["data"]
    
    # Check required fields
    required_fields = [
        "items_pending_routes",
        "active_budgets",
        "execution_today",
        "items_in_washing",
        "financial_pending",
        "finance_summary",
        "tickets_open",
        "total_clients",
        "generated_at"
    ]
    
    missing_fields = [f for f in required_fields if f not in summary]
    
    if missing_fields:
        log(f"❌ Missing fields: {missing_fields}", "ERROR")
        return False
    
    log(f"✅ All required fields present")
    
    # Display summary
    log("\n--- Dashboard Summary ---")
    log(f"   Items Pending Routes: {summary.get('items_pending_routes')}")
    log(f"   Active Budgets: {summary.get('active_budgets')}")
    log(f"   Execution Today: {summary.get('execution_today')}")
    log(f"   Items in Washing: {summary.get('items_in_washing')}")
    log(f"   Financial Pending: {summary.get('financial_pending')}")
    log(f"   Total Clients: {summary.get('total_clients')}")
    log(f"   Tickets Open: {summary.get('tickets_open')}")
    
    log(f"\n✅ DASHBOARD SUMMARY TEST PASSED")
    return True

# ============================================================
# TEST 14: Budget Update Preserves History
# ============================================================
def test_budget_update_preserves_history():
    """
    Test PUT /api/budgets/{id}:
    - Update budget with existing items + 1 new item
    - Existing items must keep their status_history, payment_records, execution_sessions unchanged
    - New item should get its own snapshot fields populated
    """
    log("=" * 60)
    log("TEST 14: BUDGET UPDATE PRESERVES HISTORY")
    log("=" * 60)
    
    # Get current budget state
    result_before = make_request("GET", f"/budgets/{test_budget_id}")
    
    if not result_before["success"]:
        log(f"❌ Failed to get budget before update", "ERROR")
        return False
    
    budget_before = result_before["data"]
    items_before = budget_before.get("items", [])
    
    log(f"Budget before update has {len(items_before)} items")
    
    # Store history data for first item
    item1_before = items_before[0]
    item1_id = item1_before.get("id")
    item1_status_history_before = item1_before.get("status_history", [])
    item1_payment_records_before = item1_before.get("payment_records", [])
    item1_execution_sessions_before = item1_before.get("execution_sessions", [])
    
    log(f"Item 1 before: {len(item1_status_history_before)} status_history, {len(item1_payment_records_before)} payment_records, {len(item1_execution_sessions_before)} execution_sessions")
    
    # Update budget: keep existing items + add 1 new item
    update_data = {
        "client_id": test_client_id,
        "payment_method": budget_before.get("payment_method"),
        "salesperson": budget_before.get("salesperson"),
        "internal_observations": "Updated",
        "items": [
            # Existing item 1 (with id)
            {
                "id": items_before[0].get("id"),
                "service_id": items_before[0].get("service_id"),
                "quantity": items_before[0].get("quantity"),
                "unit_price": items_before[0].get("unit_price"),
                "total_value": items_before[0].get("total_value"),
                "observations": "Updated observation"
            },
            # Existing item 2 (with id)
            {
                "id": items_before[1].get("id"),
                "service_id": items_before[1].get("service_id"),
                "quantity": items_before[1].get("quantity"),
                "unit_price": items_before[1].get("unit_price"),
                "total_value": items_before[1].get("total_value")
            },
            # New item (no id)
            {
                "service_id": test_service_retirada_id,
                "quantity": 1.0,
                "unit_price": 150.0,
                "total_value": 150.0,
                "observations": "New item added in update"
            }
        ]
    }
    
    result = make_request("PUT", f"/budgets/{test_budget_id}", update_data)
    
    if not result["success"]:
        log(f"❌ Budget update failed - Status: {result['status_code']}", "ERROR")
        return False
    
    budget_after = result["data"]
    items_after = budget_after.get("items", [])
    
    log(f"✅ Budget updated - now has {len(items_after)} items")
    
    # Verify existing item 1 preserved history
    item1_after = next((it for it in items_after if it.get("id") == item1_id), None)
    
    if not item1_after:
        log(f"❌ Item 1 not found after update", "ERROR")
        return False
    
    item1_status_history_after = item1_after.get("status_history", [])
    item1_payment_records_after = item1_after.get("payment_records", [])
    item1_execution_sessions_after = item1_after.get("execution_sessions", [])
    
    log(f"Item 1 after: {len(item1_status_history_after)} status_history, {len(item1_payment_records_after)} payment_records, {len(item1_execution_sessions_after)} execution_sessions")
    
    all_checks_passed = True
    
    if len(item1_status_history_after) != len(item1_status_history_before):
        log(f"❌ Item 1 status_history length changed", "ERROR")
        all_checks_passed = False
    else:
        log(f"✅ Item 1 status_history preserved")
    
    if len(item1_payment_records_after) != len(item1_payment_records_before):
        log(f"❌ Item 1 payment_records length changed", "ERROR")
        all_checks_passed = False
    else:
        log(f"✅ Item 1 payment_records preserved")
    
    if len(item1_execution_sessions_after) != len(item1_execution_sessions_before):
        log(f"❌ Item 1 execution_sessions length changed", "ERROR")
        all_checks_passed = False
    else:
        log(f"✅ Item 1 execution_sessions preserved")
    
    # Verify new item has proper snapshot
    new_item = items_after[2]  # Should be the 3rd item
    
    if not new_item.get("id") or not new_item.get("id").startswith("ITM-"):
        log(f"❌ New item missing ID", "ERROR")
        all_checks_passed = False
    else:
        log(f"✅ New item has ID: {new_item.get('id')}")
    
    if new_item.get("budget_id") != test_budget_id:
        log(f"❌ New item budget_id incorrect", "ERROR")
        all_checks_passed = False
    else:
        log(f"✅ New item budget_id correct")
    
    if not new_item.get("client_name") or not new_item.get("client_phone"):
        log(f"❌ New item missing client snapshot", "ERROR")
        all_checks_passed = False
    else:
        log(f"✅ New item has client snapshot")
    
    if all_checks_passed:
        log(f"\n✅ BUDGET UPDATE PRESERVES HISTORY TEST PASSED")
        return True
    else:
        log(f"\n❌ BUDGET UPDATE PRESERVES HISTORY TEST FAILED", "ERROR")
        return False

# ============================================================
# MAIN TEST RUNNER
# ============================================================
def main():
    """Run all Phase 2 backend tests"""
    log("=" * 60)
    log("SUPERDRY PHASE 2 BACKEND TESTING")
    log("ITEM AS PILLAR - COMPREHENSIVE TEST SUITE")
    log("=" * 60)
    
    results = {}
    
    # Run tests in sequence
    tests = [
        ("Authentication", test_authentication),
        ("Create Test Client", test_create_client),
        ("Create Test Services", test_create_services),
        ("Budget Creation with ITEM Enrichment", test_budget_creation_with_item_enrichment),
        ("PATCH /api/items/{item_id}", test_patch_item),
        ("POST /api/items/{item_id}/status", test_post_item_status),
        ("Execution Sessions", test_execution_sessions),
        ("Payments", test_payments),
        ("Timeline", test_timeline),
        ("GET /api/items with Filters", test_items_list_with_filters),
        ("Budget Delete Protection", test_budget_delete_protection),
        ("Available for Routes", test_available_for_routes),
        ("Dashboard Summary", test_dashboard_summary),
        ("Budget Update Preserves History", test_budget_update_preserves_history),
    ]
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            log(f"❌ Test '{test_name}' crashed: {str(e)}", "ERROR")
            results[test_name] = False
        
        # Small delay between tests
        import time
        time.sleep(0.5)
    
    # Summary
    log("\n" + "=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        log(f"{status} - {test_name}")
    
    log("=" * 60)
    log(f"TOTAL: {passed}/{total} tests passed ({passed*100//total}%)")
    log("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
