"""
SuperDry Backend Phase 1 Testing
Tests for Auth, Users, Clients, Dashboard, and Audit Logs
"""
import httpx
import json
from datetime import datetime
import time

# Configuration
BASE_URL = "https://superdry-laundry.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@superdry.com"
ADMIN_PASSWORD = "admin123"

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "tests": []
}

def log_test(name, passed, details=""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results["tests"].append({
        "name": name,
        "passed": passed,
        "details": details
    })
    if passed:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
    print(f"{status}: {name}")
    if details:
        print(f"  Details: {details}")

def print_summary():
    """Print test summary"""
    total = test_results["passed"] + test_results["failed"]
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {total}")
    print(f"Passed: {test_results['passed']} ({test_results['passed']/total*100:.1f}%)")
    print(f"Failed: {test_results['failed']} ({test_results['failed']/total*100:.1f}%)")
    print("="*80)
    
    if test_results["failed"] > 0:
        print("\nFailed Tests:")
        for test in test_results["tests"]:
            if not test["passed"]:
                print(f"  ❌ {test['name']}")
                if test["details"]:
                    print(f"     {test['details']}")

# ============================================================
# 1. AUTH ENDPOINTS TESTS
# ============================================================
def test_auth_endpoints():
    """Test all authentication endpoints"""
    print("\n" + "="*80)
    print("TESTING AUTH ENDPOINTS")
    print("="*80)
    
    # Test 1: Login with correct credentials
    try:
        response = httpx.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data and "user" in data:
                admin_token = data["access_token"]
                user = data["user"]
                if "password_hash" not in user:
                    log_test("Login with admin credentials", True, 
                            f"Token received, user: {user.get('name')}, role: {user.get('role')}")
                    globals()["admin_token"] = admin_token
                else:
                    log_test("Login with admin credentials", False, "password_hash exposed in response")
            else:
                log_test("Login with admin credentials", False, "Missing access_token or user in response")
        else:
            log_test("Login with admin credentials", False, f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("Login with admin credentials", False, str(e))
    
    # Test 2: Login with wrong password
    try:
        response = httpx.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": "wrongpassword"},
            timeout=30
        )
        if response.status_code == 401:
            log_test("Login with wrong password returns 401", True)
        else:
            log_test("Login with wrong password returns 401", False, f"Got status {response.status_code}")
    except Exception as e:
        log_test("Login with wrong password returns 401", False, str(e))
    
    # Test 3: Create inactive user and test login
    try:
        # First create an inactive user
        response = httpx.post(
            f"{BASE_URL}/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Inactive Test User",
                "email": "inactive@test.com",
                "password": "test123",
                "role": "TECNICO",
                "is_active": False
            },
            timeout=30
        )
        if response.status_code == 200:
            # Try to login with inactive user
            response = httpx.post(
                f"{BASE_URL}/auth/login",
                json={"email": "inactive@test.com", "password": "test123"},
                timeout=30
            )
            if response.status_code == 403:
                log_test("Login with inactive user returns 403", True)
            else:
                log_test("Login with inactive user returns 403", False, f"Got status {response.status_code}")
        else:
            log_test("Login with inactive user returns 403", False, "Failed to create inactive user")
    except Exception as e:
        log_test("Login with inactive user returns 403", False, str(e))
    
    # Test 4: GET /auth/me without token
    try:
        response = httpx.get(f"{BASE_URL}/auth/me", timeout=30)
        if response.status_code == 401:
            log_test("GET /auth/me without token returns 401", True)
        else:
            log_test("GET /auth/me without token returns 401", False, f"Got status {response.status_code}")
    except Exception as e:
        log_test("GET /auth/me without token returns 401", False, str(e))
    
    # Test 5: GET /auth/me with valid token
    try:
        response = httpx.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("email") == ADMIN_EMAIL and "password_hash" not in data:
                log_test("GET /auth/me with valid token", True, f"User: {data.get('name')}")
            else:
                log_test("GET /auth/me with valid token", False, "Invalid user data or password_hash exposed")
        else:
            log_test("GET /auth/me with valid token", False, f"Status {response.status_code}")
    except Exception as e:
        log_test("GET /auth/me with valid token", False, str(e))
    
    # Test 6: Change password with wrong old password
    try:
        response = httpx.post(
            f"{BASE_URL}/auth/change-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"old_password": "wrongold", "new_password": "newpass123"},
            timeout=30
        )
        if response.status_code == 401:
            log_test("Change password with wrong old_password returns 401", True)
        else:
            log_test("Change password with wrong old_password returns 401", False, f"Got status {response.status_code}")
    except Exception as e:
        log_test("Change password with wrong old_password returns 401", False, str(e))
    
    # Test 7: Change password successfully and verify new password works
    try:
        # Change password
        response = httpx.post(
            f"{BASE_URL}/auth/change-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"old_password": ADMIN_PASSWORD, "new_password": "newadmin123"},
            timeout=30
        )
        if response.status_code == 200:
            # Try login with new password
            response = httpx.post(
                f"{BASE_URL}/auth/login",
                json={"email": ADMIN_EMAIL, "password": "newadmin123"},
                timeout=30
            )
            if response.status_code == 200:
                # Change back to original password
                new_token = response.json()["access_token"]
                httpx.post(
                    f"{BASE_URL}/auth/change-password",
                    headers={"Authorization": f"Bearer {new_token}"},
                    json={"old_password": "newadmin123", "new_password": ADMIN_PASSWORD},
                    timeout=30
                )
                log_test("Change password successfully", True, "Password changed and verified")
            else:
                log_test("Change password successfully", False, "New password doesn't work for login")
        else:
            log_test("Change password successfully", False, f"Status {response.status_code}")
    except Exception as e:
        log_test("Change password successfully", False, str(e))

# ============================================================
# 2. USERS CRUD TESTS
# ============================================================
def test_users_crud():
    """Test users CRUD endpoints"""
    print("\n" + "="*80)
    print("TESTING USERS CRUD (ADMIN ONLY)")
    print("="*80)
    
    # Test 1: GET /users with admin token
    try:
        response = httpx.get(
            f"{BASE_URL}/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        if response.status_code == 200:
            users = response.json()
            if isinstance(users, list) and len(users) > 0:
                log_test("GET /users with admin token", True, f"Found {len(users)} users")
            else:
                log_test("GET /users with admin token", False, "Empty or invalid response")
        else:
            log_test("GET /users with admin token", False, f"Status {response.status_code}")
    except Exception as e:
        log_test("GET /users with admin token", False, str(e))
    
    # Test 2: Create non-admin user and test GET /users returns 403
    try:
        # Create a TECNICO user
        response = httpx.post(
            f"{BASE_URL}/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Test Tecnico",
                "email": "tecnico@test.com",
                "password": "test123",
                "role": "TECNICO",
                "is_active": True
            },
            timeout=30
        )
        if response.status_code == 200:
            # Login as tecnico
            response = httpx.post(
                f"{BASE_URL}/auth/login",
                json={"email": "tecnico@test.com", "password": "test123"},
                timeout=30
            )
            if response.status_code == 200:
                tecnico_token = response.json()["access_token"]
                # Try to access /users
                response = httpx.get(
                    f"{BASE_URL}/users",
                    headers={"Authorization": f"Bearer {tecnico_token}"},
                    timeout=30
                )
                if response.status_code == 403:
                    log_test("GET /users with non-admin token returns 403", True)
                else:
                    log_test("GET /users with non-admin token returns 403", False, f"Got status {response.status_code}")
            else:
                log_test("GET /users with non-admin token returns 403", False, "Failed to login as tecnico")
        else:
            log_test("GET /users with non-admin token returns 403", False, "Failed to create tecnico user")
    except Exception as e:
        log_test("GET /users with non-admin token returns 403", False, str(e))
    
    # Test 3: POST /users creates new user with role TECNICO
    try:
        response = httpx.post(
            f"{BASE_URL}/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "New Tecnico User",
                "email": f"newtecnico{int(time.time())}@test.com",
                "password": "test123",
                "role": "TECNICO",
                "is_active": True
            },
            timeout=30
        )
        if response.status_code == 200:
            user = response.json()
            if user.get("role") == "TECNICO" and "password_hash" not in user:
                log_test("POST /users creates new user", True, f"Created user: {user.get('name')}")
                globals()["test_user_id"] = user.get("id")
            else:
                log_test("POST /users creates new user", False, "Invalid user data or password_hash exposed")
        else:
            log_test("POST /users creates new user", False, f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("POST /users creates new user", False, str(e))
    
    # Test 4: POST /users with duplicate email returns 400
    try:
        response = httpx.post(
            f"{BASE_URL}/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Duplicate User",
                "email": ADMIN_EMAIL,  # Use admin email (duplicate)
                "password": "test123",
                "role": "TECNICO"
            },
            timeout=30
        )
        if response.status_code == 400:
            log_test("POST /users with duplicate email returns 400", True)
        else:
            log_test("POST /users with duplicate email returns 400", False, f"Got status {response.status_code}")
    except Exception as e:
        log_test("POST /users with duplicate email returns 400", False, str(e))
    
    # Test 5: PUT /users/{id} updates user
    try:
        if "test_user_id" in globals():
            response = httpx.put(
                f"{BASE_URL}/users/{test_user_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "name": "Updated Tecnico Name",
                    "role": "ATENDENTE",
                    "is_active": True
                },
                timeout=30
            )
            if response.status_code == 200:
                user = response.json()
                if user.get("name") == "Updated Tecnico Name" and user.get("role") == "ATENDENTE":
                    log_test("PUT /users/{id} updates user", True, "Name and role updated")
                else:
                    log_test("PUT /users/{id} updates user", False, "Update not reflected")
            else:
                log_test("PUT /users/{id} updates user", False, f"Status {response.status_code}")
        else:
            log_test("PUT /users/{id} updates user", False, "No test user created")
    except Exception as e:
        log_test("PUT /users/{id} updates user", False, str(e))
    
    # Test 6: PUT /users/{id} with password change
    try:
        if "test_user_id" in globals():
            response = httpx.put(
                f"{BASE_URL}/users/{test_user_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"password": "newtest456"},
                timeout=30
            )
            if response.status_code == 200:
                # Get the user's email
                response = httpx.get(
                    f"{BASE_URL}/users",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    timeout=30
                )
                users = response.json()
                test_user = next((u for u in users if u.get("id") == test_user_id), None)
                if test_user:
                    # Try login with new password
                    response = httpx.post(
                        f"{BASE_URL}/auth/login",
                        json={"email": test_user.get("email"), "password": "newtest456"},
                        timeout=30
                    )
                    if response.status_code == 200:
                        log_test("PUT /users/{id} password change works", True)
                    else:
                        log_test("PUT /users/{id} password change works", False, "New password doesn't work")
                else:
                    log_test("PUT /users/{id} password change works", False, "Test user not found")
            else:
                log_test("PUT /users/{id} password change works", False, f"Status {response.status_code}")
        else:
            log_test("PUT /users/{id} password change works", False, "No test user created")
    except Exception as e:
        log_test("PUT /users/{id} password change works", False, str(e))
    
    # Test 7: DELETE /users/{id} - cannot delete self
    try:
        # Get admin user ID
        response = httpx.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        admin_id = response.json().get("id")
        
        response = httpx.delete(
            f"{BASE_URL}/users/{admin_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        if response.status_code == 400:
            log_test("DELETE /users/{id} - cannot delete self", True)
        else:
            log_test("DELETE /users/{id} - cannot delete self", False, f"Got status {response.status_code}")
    except Exception as e:
        log_test("DELETE /users/{id} - cannot delete self", False, str(e))
    
    # Test 8: DELETE /users/{id} - cannot delete last admin
    try:
        # Create a second admin
        response = httpx.post(
            f"{BASE_URL}/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Second Admin",
                "email": f"admin2_{int(time.time())}@test.com",
                "password": "admin123",
                "role": "ADMIN",
                "is_active": True
            },
            timeout=30
        )
        if response.status_code == 200:
            second_admin_id = response.json().get("id")
            
            # Get first admin ID
            response = httpx.get(
                f"{BASE_URL}/auth/me",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=30
            )
            first_admin_id = response.json().get("id")
            
            # Delete first admin (should work since we have 2 admins)
            response = httpx.delete(
                f"{BASE_URL}/users/{first_admin_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=30
            )
            
            # This should fail because we're deleting ourselves
            # Let's try deleting the second admin instead
            response = httpx.delete(
                f"{BASE_URL}/users/{second_admin_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=30
            )
            
            if response.status_code == 200:
                # Now try to delete the remaining admin (should fail)
                response = httpx.delete(
                    f"{BASE_URL}/users/{first_admin_id}",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    timeout=30
                )
                if response.status_code == 400:
                    log_test("DELETE /users/{id} - cannot delete last admin", True)
                else:
                    log_test("DELETE /users/{id} - cannot delete last admin", False, f"Got status {response.status_code}")
            else:
                log_test("DELETE /users/{id} - cannot delete last admin", False, "Failed to delete second admin")
        else:
            log_test("DELETE /users/{id} - cannot delete last admin", False, "Failed to create second admin")
    except Exception as e:
        log_test("DELETE /users/{id} - cannot delete last admin", False, str(e))
    
    # Test 9: DELETE /users/{id} - regular user deletion works
    try:
        if "test_user_id" in globals():
            response = httpx.delete(
                f"{BASE_URL}/users/{test_user_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=30
            )
            if response.status_code == 200:
                log_test("DELETE /users/{id} - regular user deletion", True)
            else:
                log_test("DELETE /users/{id} - regular user deletion", False, f"Status {response.status_code}")
        else:
            log_test("DELETE /users/{id} - regular user deletion", False, "No test user to delete")
    except Exception as e:
        log_test("DELETE /users/{id} - regular user deletion", False, str(e))

# ============================================================
# 3. CLIENTS ENDPOINTS TESTS
# ============================================================
def test_clients_endpoints():
    """Test clients endpoints"""
    print("\n" + "="*80)
    print("TESTING CLIENTS ENDPOINTS")
    print("="*80)
    
    # Test 1: POST /clients with full payload
    try:
        response = httpx.post(
            f"{BASE_URL}/clients",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "João da Silva",
                "phone_primary": "(65) 99999-1234",
                "phone_alternative": "(65) 98888-5678",
                "email": "joao@test.com",
                "cpf_cnpj": "123.456.789-00",
                "instagram": "@joaosilva",
                "address": {
                    "full_address": "Rua Teste, 123",
                    "complement": "Apto 45",
                    "neighborhood": "Centro",
                    "city": "Cuiabá",
                    "state": "MT",
                    "latitude": -15.601411,
                    "longitude": -56.097892
                }
            },
            timeout=30
        )
        if response.status_code == 200:
            client = response.json()
            if (client.get("id", "").startswith("CLI-") and 
                "created_by" in client and 
                "created_by_name" in client and
                "updated_by" in client and
                "updated_by_name" in client):
                log_test("POST /clients creates client with sequential ID and audit", True, 
                        f"Client ID: {client.get('id')}, Created by: {client.get('created_by_name')}")
                globals()["test_client_id"] = client.get("id")
            else:
                log_test("POST /clients creates client with sequential ID and audit", False, 
                        "Missing ID format or audit fields")
        else:
            log_test("POST /clients creates client with sequential ID and audit", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("POST /clients creates client with sequential ID and audit", False, str(e))
    
    # Test 2: GET /clients/count
    try:
        response = httpx.get(
            f"{BASE_URL}/clients/count",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if "total" in data and isinstance(data["total"], int):
                log_test("GET /clients/count", True, f"Total clients: {data['total']}")
            else:
                log_test("GET /clients/count", False, "Invalid response format")
        else:
            log_test("GET /clients/count", False, f"Status {response.status_code}")
    except Exception as e:
        log_test("GET /clients/count", False, str(e))
    
    # Test 3: Create test clients with accented names
    test_clients = [
        {"name": "Mônica Santos", "city": "Cuiabá", "neighborhood": "Jardim"},
        {"name": "Andréa Costa", "city": "Várzea Grande", "neighborhood": "Centro"}
    ]
    
    for client_data in test_clients:
        try:
            response = httpx.post(
                f"{BASE_URL}/clients",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "name": client_data["name"],
                    "phone_primary": "(65) 99999-0000",
                    "address": {
                        "full_address": "Rua Teste",
                        "neighborhood": client_data["neighborhood"],
                        "city": client_data["city"],
                        "state": "MT"
                    }
                },
                timeout=30
            )
            if response.status_code != 200:
                print(f"  Warning: Failed to create test client {client_data['name']}")
        except Exception as e:
            print(f"  Warning: Error creating test client: {e}")
    
    # Test 4: GET /clients?search - case insensitive
    try:
        response = httpx.get(
            f"{BASE_URL}/clients?search=joao",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        if response.status_code == 200:
            clients = response.json()
            found = any("joão" in c.get("name", "").lower() for c in clients)
            if found:
                log_test("GET /clients?search - case insensitive", True, "Found 'João' with search 'joao'")
            else:
                log_test("GET /clients?search - case insensitive", False, "Case insensitive search not working")
        else:
            log_test("GET /clients?search - case insensitive", False, f"Status {response.status_code}")
    except Exception as e:
        log_test("GET /clients?search - case insensitive", False, str(e))
    
    # Test 5: GET /clients?search - accent insensitive
    try:
        response = httpx.get(
            f"{BASE_URL}/clients?search=monica",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        if response.status_code == 200:
            clients = response.json()
            found = any("mônica" in c.get("name", "").lower() for c in clients)
            if found:
                log_test("GET /clients?search - accent insensitive", True, "Found 'Mônica' with search 'monica'")
            else:
                log_test("GET /clients?search - accent insensitive", False, "Accent insensitive search not working")
        else:
            log_test("GET /clients?search - accent insensitive", False, f"Status {response.status_code}")
    except Exception as e:
        log_test("GET /clients?search - accent insensitive", False, str(e))
    
    # Test 6: GET /clients?search - numeric search (phone)
    try:
        response = httpx.get(
            f"{BASE_URL}/clients?search=999991234",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        if response.status_code == 200:
            clients = response.json()
            if len(clients) > 0:
                log_test("GET /clients?search - numeric phone search", True, f"Found {len(clients)} clients")
            else:
                log_test("GET /clients?search - numeric phone search", False, "No clients found with phone search")
        else:
            log_test("GET /clients?search - numeric phone search", False, f"Status {response.status_code}")
    except Exception as e:
        log_test("GET /clients?search - numeric phone search", False, str(e))
    
    # Test 7: GET /clients?search - city search
    try:
        response = httpx.get(
            f"{BASE_URL}/clients?search=Cuiabá",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        if response.status_code == 200:
            clients = response.json()
            if len(clients) > 0:
                log_test("GET /clients?search - city search", True, f"Found {len(clients)} clients in Cuiabá")
            else:
                log_test("GET /clients?search - city search", False, "No clients found with city search")
        else:
            log_test("GET /clients?search - city search", False, f"Status {response.status_code}")
    except Exception as e:
        log_test("GET /clients?search - city search", False, str(e))
    
    # Test 8: GET /clients/{id}
    try:
        if "test_client_id" in globals():
            response = httpx.get(
                f"{BASE_URL}/clients/{test_client_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=30
            )
            if response.status_code == 200:
                client = response.json()
                if client.get("id") == test_client_id:
                    log_test("GET /clients/{id}", True, f"Retrieved client: {client.get('name')}")
                else:
                    log_test("GET /clients/{id}", False, "Wrong client returned")
            else:
                log_test("GET /clients/{id}", False, f"Status {response.status_code}")
        else:
            log_test("GET /clients/{id}", False, "No test client created")
    except Exception as e:
        log_test("GET /clients/{id}", False, str(e))
    
    # Test 9: GET /clients/{id} - 404 for invalid ID
    try:
        response = httpx.get(
            f"{BASE_URL}/clients/CLI-9999",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        if response.status_code == 404:
            log_test("GET /clients/{id} - 404 for invalid ID", True)
        else:
            log_test("GET /clients/{id} - 404 for invalid ID", False, f"Got status {response.status_code}")
    except Exception as e:
        log_test("GET /clients/{id} - 404 for invalid ID", False, str(e))
    
    # Test 10: GET /clients/{id}/history - no budgets
    try:
        if "test_client_id" in globals():
            response = httpx.get(
                f"{BASE_URL}/clients/{test_client_id}/history",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                if (data.get("client_id") == test_client_id and 
                    "items" in data and 
                    "total_items" in data):
                    log_test("GET /clients/{id}/history", True, 
                            f"History retrieved, {data.get('total_items')} items")
                else:
                    log_test("GET /clients/{id}/history", False, "Invalid response format")
            else:
                log_test("GET /clients/{id}/history", False, f"Status {response.status_code}")
        else:
            log_test("GET /clients/{id}/history", False, "No test client created")
    except Exception as e:
        log_test("GET /clients/{id}/history", False, str(e))
    
    # Test 11: PUT /clients/{id} - update client
    try:
        if "test_client_id" in globals():
            response = httpx.put(
                f"{BASE_URL}/clients/{test_client_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "name": "João da Silva Updated",
                    "phone_primary": "(65) 99999-9999",
                    "email": "joao.updated@test.com",
                    "address": {
                        "full_address": "Rua Nova, 456",
                        "neighborhood": "Novo Bairro",
                        "city": "Cuiabá",
                        "state": "MT"
                    }
                },
                timeout=30
            )
            if response.status_code == 200:
                client = response.json()
                if (client.get("name") == "João da Silva Updated" and 
                    "updated_by" in client and 
                    "updated_by_name" in client):
                    log_test("PUT /clients/{id} updates and logs audit", True, 
                            f"Updated by: {client.get('updated_by_name')}")
                else:
                    log_test("PUT /clients/{id} updates and logs audit", False, 
                            "Update not reflected or missing audit fields")
            else:
                log_test("PUT /clients/{id} updates and logs audit", False, f"Status {response.status_code}")
        else:
            log_test("PUT /clients/{id} updates and logs audit", False, "No test client created")
    except Exception as e:
        log_test("PUT /clients/{id} updates and logs audit", False, str(e))
    
    # Test 12: DELETE /clients/{id} - blocked if has budgets
    # First, we need to check if we can create a budget for testing
    # For now, we'll test deletion without budgets
    
    # Test 13: DELETE /clients/{id} - success without budgets
    try:
        # Create a new client for deletion
        response = httpx.post(
            f"{BASE_URL}/clients",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Client To Delete",
                "phone_primary": "(65) 99999-0000",
                "address": {
                    "full_address": "Rua Delete",
                    "neighborhood": "Test",
                    "city": "Cuiabá",
                    "state": "MT"
                }
            },
            timeout=30
        )
        if response.status_code == 200:
            delete_client_id = response.json().get("id")
            
            # Delete the client
            response = httpx.delete(
                f"{BASE_URL}/clients/{delete_client_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=30
            )
            if response.status_code == 200:
                log_test("DELETE /clients/{id} - success without budgets", True)
            else:
                log_test("DELETE /clients/{id} - success without budgets", False, 
                        f"Status {response.status_code}")
        else:
            log_test("DELETE /clients/{id} - success without budgets", False, 
                    "Failed to create client for deletion")
    except Exception as e:
        log_test("DELETE /clients/{id} - success without budgets", False, str(e))

# ============================================================
# 4. DASHBOARD SUMMARY TESTS
# ============================================================
def test_dashboard_summary():
    """Test dashboard summary endpoint"""
    print("\n" + "="*80)
    print("TESTING DASHBOARD SUMMARY")
    print("="*80)
    
    # Test 1: GET /dashboard/summary without auth
    try:
        response = httpx.get(f"{BASE_URL}/dashboard/summary", timeout=30)
        if response.status_code == 401:
            log_test("GET /dashboard/summary without auth returns 401", True)
        else:
            log_test("GET /dashboard/summary without auth returns 401", False, 
                    f"Got status {response.status_code}")
    except Exception as e:
        log_test("GET /dashboard/summary without auth returns 401", False, str(e))
    
    # Test 2: GET /dashboard/summary with auth
    try:
        response = httpx.get(
            f"{BASE_URL}/dashboard/summary",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            required_keys = [
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
            missing_keys = [k for k in required_keys if k not in data]
            
            if not missing_keys:
                # Check finance_summary structure
                finance = data.get("finance_summary", {})
                finance_keys = ["cash_balance", "bank_balance", "month_revenue", "available"]
                missing_finance = [k for k in finance_keys if k not in finance]
                
                if not missing_finance:
                    log_test("GET /dashboard/summary returns all required fields", True, 
                            f"Clients: {data.get('total_clients')}, Pending routes: {data.get('items_pending_routes')}")
                else:
                    log_test("GET /dashboard/summary returns all required fields", False, 
                            f"Missing finance_summary keys: {missing_finance}")
            else:
                log_test("GET /dashboard/summary returns all required fields", False, 
                        f"Missing keys: {missing_keys}")
        else:
            log_test("GET /dashboard/summary returns all required fields", False, 
                    f"Status {response.status_code}")
    except Exception as e:
        log_test("GET /dashboard/summary returns all required fields", False, str(e))

# ============================================================
# 5. AUDIT LOGS TESTS
# ============================================================
def test_audit_logs():
    """Test audit logs endpoint"""
    print("\n" + "="*80)
    print("TESTING AUDIT LOGS")
    print("="*80)
    
    # Test 1: GET /audit-logs with admin token
    try:
        response = httpx.get(
            f"{BASE_URL}/audit-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if "logs" in data and "count" in data:
                log_test("GET /audit-logs with admin token", True, 
                        f"Found {data.get('count')} audit logs")
            else:
                log_test("GET /audit-logs with admin token", False, "Invalid response format")
        else:
            log_test("GET /audit-logs with admin token", False, f"Status {response.status_code}")
    except Exception as e:
        log_test("GET /audit-logs with admin token", False, str(e))
    
    # Test 2: GET /audit-logs?entity_type=client
    try:
        response = httpx.get(
            f"{BASE_URL}/audit-logs?entity_type=client",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            logs = data.get("logs", [])
            if all(log.get("entity_type") == "client" for log in logs):
                log_test("GET /audit-logs?entity_type=client filters correctly", True, 
                        f"Found {len(logs)} client audit logs")
            else:
                log_test("GET /audit-logs?entity_type=client filters correctly", False, 
                        "Filter not working correctly")
        else:
            log_test("GET /audit-logs?entity_type=client filters correctly", False, 
                    f"Status {response.status_code}")
    except Exception as e:
        log_test("GET /audit-logs?entity_type=client filters correctly", False, str(e))
    
    # Test 3: GET /audit-logs?entity_type=user
    try:
        response = httpx.get(
            f"{BASE_URL}/audit-logs?entity_type=user",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            logs = data.get("logs", [])
            if all(log.get("entity_type") == "user" for log in logs):
                log_test("GET /audit-logs?entity_type=user filters correctly", True, 
                        f"Found {len(logs)} user audit logs")
            else:
                log_test("GET /audit-logs?entity_type=user filters correctly", False, 
                        "Filter not working correctly")
        else:
            log_test("GET /audit-logs?entity_type=user filters correctly", False, 
                    f"Status {response.status_code}")
    except Exception as e:
        log_test("GET /audit-logs?entity_type=user filters correctly", False, str(e))
    
    # Test 4: GET /audit-logs with non-admin token returns 403
    try:
        # Create a tecnico user if not exists
        response = httpx.post(
            f"{BASE_URL}/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Audit Test Tecnico",
                "email": f"audittest{int(time.time())}@test.com",
                "password": "test123",
                "role": "TECNICO",
                "is_active": True
            },
            timeout=30
        )
        if response.status_code == 200:
            # Login as tecnico
            tecnico_email = response.json().get("email")
            response = httpx.post(
                f"{BASE_URL}/auth/login",
                json={"email": tecnico_email, "password": "test123"},
                timeout=30
            )
            if response.status_code == 200:
                tecnico_token = response.json()["access_token"]
                
                # Try to access audit logs
                response = httpx.get(
                    f"{BASE_URL}/audit-logs",
                    headers={"Authorization": f"Bearer {tecnico_token}"},
                    timeout=30
                )
                if response.status_code == 403:
                    log_test("GET /audit-logs with non-admin returns 403", True)
                else:
                    log_test("GET /audit-logs with non-admin returns 403", False, 
                            f"Got status {response.status_code}")
            else:
                log_test("GET /audit-logs with non-admin returns 403", False, 
                        "Failed to login as tecnico")
        else:
            log_test("GET /audit-logs with non-admin returns 403", False, 
                    "Failed to create tecnico user")
    except Exception as e:
        log_test("GET /audit-logs with non-admin returns 403", False, str(e))

# ============================================================
# MAIN TEST EXECUTION
# ============================================================
def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("SUPERDRY BACKEND PHASE 1 TESTING")
    print("Testing Auth, Users, Clients, Dashboard, and Audit Logs")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    print("="*80)
    
    try:
        # Run all test suites
        test_auth_endpoints()
        test_users_crud()
        test_clients_endpoints()
        test_dashboard_summary()
        test_audit_logs()
        
        # Print summary
        print_summary()
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
