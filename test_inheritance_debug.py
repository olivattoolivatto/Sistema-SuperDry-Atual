#!/usr/bin/env python3
"""
Debug test for service status inheritance
Testing the specific lines 2140-2143 fix
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://superdry-routes.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

def make_request(method: str, endpoint: str, data: dict = None):
    """Make HTTP request with error handling"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=HEADERS)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=HEADERS, json=data)
        elif method.upper() == 'PUT':
            response = requests.put(url, headers=HEADERS, json=data)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=HEADERS)
        
        return {
            'status_code': response.status_code,
            'data': response.json() if response.content else {},
            'success': 200 <= response.status_code < 300
        }
    except Exception as e:
        return {
            'status_code': 0,
            'data': {'error': str(e)},
            'success': False
        }

def test_inheritance_debug():
    """Test the inheritance mechanism step by step"""
    print("🔍 DEBUGGING SERVICE STATUS INHERITANCE")
    print("=" * 60)
    
    # Step 1: Check services catalog
    print("\n1️⃣ CHECKING SERVICES CATALOG:")
    response = make_request('GET', '/services')
    if response['success']:
        services = response['data']
        status_counts = {}
        for service in services:
            status = service.get('default_service_status')
            if status:
                status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"   📊 Services found: {len(services)}")
        print(f"   📊 Status distribution: {status_counts}")
        
        # Find services with different statuses
        retirar_service = None
        executar_service = None
        entregar_service = None
        
        for service in services:
            if service.get('default_service_status') == 'RETIRAR' and not retirar_service:
                retirar_service = service
            elif service.get('default_service_status') == 'EXECUTAR_NO_LOCAL' and not executar_service:
                executar_service = service
            elif service.get('default_service_status') == 'ENTREGAR' and not entregar_service:
                entregar_service = service
        
        print(f"   ✅ Found RETIRAR service: {retirar_service['name'] if retirar_service else 'None'}")
        print(f"   ✅ Found EXECUTAR_NO_LOCAL service: {executar_service['name'] if executar_service else 'None'}")
        print(f"   ✅ Found ENTREGAR service: {entregar_service['name'] if entregar_service else 'None'}")
    else:
        print("   ❌ Failed to get services")
        return
    
    # Step 2: Get a test client
    print("\n2️⃣ GETTING TEST CLIENT:")
    response = make_request('GET', '/clients?limit=1')
    if response['success'] and response['data']:
        client = response['data'][0]
        client_id = client['id']
        print(f"   ✅ Using client: {client['name']} ({client_id})")
    else:
        print("   ❌ No clients found")
        return
    
    # Step 3: Create new budget and test inheritance
    print("\n3️⃣ TESTING INHERITANCE WITH NEW BUDGET:")
    
    # Create budget
    budget_data = {
        "client_id": client_id,
        "payment_method": "PIX_CNPJ_25995295000104",
        "salesperson": "Gabriela Alcântara",
        "internal_observations": "Teste de herança de status - Debug"
    }
    
    response = make_request('POST', '/budgets', budget_data)
    if not response['success']:
        print(f"   ❌ Failed to create budget: {response['data']}")
        return
    
    budget = response['data']
    budget_id = budget['id']
    print(f"   ✅ Created budget: {budget_id}")
    
    # Test each service type
    test_services = [
        (retirar_service, 'RETIRAR'),
        (executar_service, 'EXECUTAR_NO_LOCAL'),
        (entregar_service, 'ENTREGAR')
    ]
    
    inheritance_results = []
    
    for service, expected_status in test_services:
        if not service:
            print(f"   ⚠️  Skipping {expected_status} - no service found")
            continue
        
        print(f"\n   🧪 Testing service: {service['name']}")
        print(f"      Expected status: {expected_status}")
        print(f"      Service default_service_status: {service.get('default_service_status')}")
        
        # Add item to budget
        item_data = {
            "service_id": service['id'],
            "quantity": 1.0,
            "observations": f"Teste herança {expected_status}"
        }
        
        response = make_request('POST', f'/budgets/{budget_id}/items', item_data)
        if response['success']:
            item = response['data']
            actual_status = item.get('status')
            
            print(f"      ✅ Item created: {item['id']}")
            print(f"      📊 Actual status: {actual_status}")
            
            if actual_status == expected_status:
                print(f"      ✅ INHERITANCE WORKING: {expected_status}")
                inheritance_results.append(True)
            else:
                print(f"      ❌ INHERITANCE FAILED: Expected {expected_status}, got {actual_status}")
                inheritance_results.append(False)
        else:
            print(f"      ❌ Failed to add item: {response['data']}")
            inheritance_results.append(False)
    
    # Step 4: Check available items after creation
    print("\n4️⃣ CHECKING AVAILABLE ITEMS AFTER CREATION:")
    response = make_request('GET', '/budget-items/available-for-routes')
    if response['success']:
        available_items = response['data'].get('available_items', [])
        status_counts = {}
        for item in available_items:
            status = item.get('status')
            if status:
                status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"   📊 Available items: {len(available_items)}")
        print(f"   📊 Status distribution: {status_counts}")
        
        if len(status_counts) > 1:
            print("   ✅ VARIETY CONFIRMED: Multiple statuses found")
        else:
            print("   ❌ NO VARIETY: All items have same status")
    
    # Step 5: Summary
    print("\n5️⃣ INHERITANCE TEST SUMMARY:")
    successful_tests = sum(inheritance_results)
    total_tests = len(inheritance_results)
    
    if successful_tests == total_tests and total_tests > 0:
        print(f"   ✅ ALL TESTS PASSED: {successful_tests}/{total_tests}")
        print("   ✅ Lines 2140-2143 fix is working correctly")
    else:
        print(f"   ❌ SOME TESTS FAILED: {successful_tests}/{total_tests}")
        print("   ❌ Lines 2140-2143 fix needs investigation")
    
    # Cleanup
    print("\n6️⃣ CLEANUP:")
    response = make_request('DELETE', f'/budgets/{budget_id}')
    if response['success']:
        print(f"   ✅ Deleted test budget: {budget_id}")
    else:
        print(f"   ❌ Failed to delete budget: {budget_id}")

if __name__ == "__main__":
    test_inheritance_debug()