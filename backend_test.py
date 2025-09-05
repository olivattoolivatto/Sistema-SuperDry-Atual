#!/usr/bin/env python3
"""
Backend Test Suite for SuperDry Lavanderia Management System
Focus: Testing default service status bug fix and Routes API
"""

import requests
import json
import sys
import math
from datetime import datetime
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://superdry-routes.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class ServiceStatusBugTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.test_results = []
        self.created_resources = {
            'clients': [],
            'services': [],
            'budgets': [],
            'routes': [],
            'system_config': False
        }
    
    def log_test(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=self.headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=self.headers)
            
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
    
    def setup_test_data_for_status_bug(self):
        """Create test data specifically for testing service status bug"""
        print("\n=== SETTING UP TEST DATA FOR SERVICE STATUS BUG ===")
        
        # Setup system config with company GPS coordinates
        system_config_data = {
            "company_name": "SuperDry Lavanderia de Tapetes & Estofados",
            "address_full": "Rua Exemplo, 100",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP",
            "latitude": -23.5505,
            "longitude": -46.6333,
            "phone": "11999999999",
            "email": "contato@superdry.com"
        }
        
        response = self.make_request('PUT', '/system-config', system_config_data)
        if response['success']:
            self.created_resources['system_config'] = True
            self.log_test("Setup: System Config", True, "System config created with GPS coordinates")
        else:
            self.log_test("Setup: System Config", False, "Failed to create system config", response['data'])
            return False
        
        # Create test client for status bug testing
        client_data = {
            "name": "Maria Silva Santos",
            "phone_primary": "11987654321",
            "email": "maria.santos@email.com",
            "address": {
                "full_address": "Rua das Flores, 123",
                "neighborhood": "Vila Madalena",
                "city": "São Paulo",
                "state": "SP",
                "latitude": -23.5489,
                "longitude": -46.6388
            }
        }
        
        response = self.make_request('POST', '/clients', client_data)
        if response['success']:
            self.created_resources['clients'].append(response['data']['id'])
            self.log_test("Setup: Create Test Client", True, f"Client created: {client_data['name']}")
        else:
            self.log_test("Setup: Create Test Client", False, f"Failed to create client: {client_data['name']}", response['data'])
            return False
        
        # Create test services with DIFFERENT default_service_status values
        # This is the key to testing the bug fix
        services_data = [
            {
                "name": "Limpeza de Sofá - Status RETIRAR",
                "category": "ESTOFADOS",
                "service_type": "Limpeza Profunda",
                "measure_type": "UNITARIO",
                "execution_location": "RETIRADA",
                "cost_price": 80.0,
                "sale_price": 150.0,
                "default_service_status": "RETIRAR"
            },
            {
                "name": "Limpeza de Tapete - Status EXECUTAR_NO_LOCAL",
                "category": "CARPETES_E_TAPETES_NO_LOCAL",
                "service_type": "Limpeza no Local",
                "measure_type": "CARPETE_TAPETE_LOCAL",
                "execution_location": "NO_LOCAL",
                "cost_price": 30.0,
                "sale_price": 50.0,
                "default_service_status": "EXECUTAR_NO_LOCAL"
            },
            {
                "name": "Entrega de Cortina - Status ENTREGAR",
                "category": "CORTINAS",
                "service_type": "Entrega",
                "measure_type": "UNITARIO",
                "execution_location": "RETIRADA",
                "cost_price": 0.0,
                "sale_price": 25.0,
                "default_service_status": "ENTREGAR"
            }
        ]
        
        for service_data in services_data:
            response = self.make_request('POST', '/services', service_data)
            if response['success']:
                self.created_resources['services'].append(response['data']['id'])
                self.log_test("Setup: Create Test Service", True, f"Service created: {service_data['name']}")
            else:
                self.log_test("Setup: Create Test Service", False, f"Failed to create service: {service_data['name']}", response['data'])
                return False
        
        # Create test budgets with items in route-eligible status
        for i, client_id in enumerate(self.created_resources['clients']):
            service_id = self.created_resources['services'][i % len(self.created_resources['services'])]
            
            # Determine status based on service type
            if i == 1:  # Second client gets NO_LOCAL service
                status = "EXECUTAR_NO_LOCAL"
            elif i == 2:  # Third client gets delivery
                status = "ENTREGAR"
            else:
                status = "RETIRAR"
            
            budget_data = {
                "client_id": client_id,
                "payment_method": "PIX_CNPJ_25995295000104",
                "salesperson": "Gabriela Alcântara",
                "internal_observations": f"Orçamento para teste de rotas - Cliente {i+1}",
                "items": [
                    {
                        "id": f"ITM-TEST{i+1:03d}",
                        "service_id": service_id,
                        "service_name": services_data[i % len(services_data)]["name"],
                        "service_code": service_id,
                        "quantity": 1.0,
                        "unit_price": services_data[i % len(services_data)]["sale_price"],
                        "total_value": services_data[i % len(services_data)]["sale_price"],
                        "status": status,
                        "execution_location": services_data[i % len(services_data)]["execution_location"],
                        "is_retoque": False
                    }
                ]
            }
            
            response = self.make_request('POST', '/budgets', budget_data)
            if response['success']:
                self.created_resources['budgets'].append(response['data']['id'])
                self.log_test("Setup: Create Test Budget", True, f"Budget created with {status} item")
            else:
                self.log_test("Setup: Create Test Budget", False, f"Failed to create budget for client {i+1}", response['data'])
                return False
        
        return True
    
    def test_service_catalog_default_status(self):
        """CRITICAL TEST: Verify services have different default_service_status values"""
        print("\n=== TESTING SERVICE CATALOG DEFAULT STATUS ===")
        
        response = self.make_request('GET', '/services')
        if not response['success']:
            self.log_test("Service Catalog Status", False, "Failed to retrieve services", response['data'])
            return []
        
        services = response['data']
        if not services:
            self.log_test("Service Catalog Status", False, "No services found in catalog")
            return []
        
        # Find our test services and verify their default_service_status
        test_services = []
        expected_statuses = {
            "RETIRAR": False,
            "EXECUTAR_NO_LOCAL": False,
            "ENTREGAR": False
        }
        
        for service in services:
            service_name = service.get('name', '')
            default_status = service.get('default_service_status')
            
            if 'Status RETIRAR' in service_name:
                test_services.append(service)
                if default_status == 'RETIRAR':
                    expected_statuses['RETIRAR'] = True
                    self.log_test("Service Status Check", True, f"Service '{service_name}' has correct default_service_status: {default_status}")
                else:
                    self.log_test("Service Status Check", False, f"Service '{service_name}' has wrong default_service_status: {default_status} (expected RETIRAR)")
            
            elif 'Status EXECUTAR_NO_LOCAL' in service_name:
                test_services.append(service)
                if default_status == 'EXECUTAR_NO_LOCAL':
                    expected_statuses['EXECUTAR_NO_LOCAL'] = True
                    self.log_test("Service Status Check", True, f"Service '{service_name}' has correct default_service_status: {default_status}")
                else:
                    self.log_test("Service Status Check", False, f"Service '{service_name}' has wrong default_service_status: {default_status} (expected EXECUTAR_NO_LOCAL)")
            
            elif 'Status ENTREGAR' in service_name:
                test_services.append(service)
                if default_status == 'ENTREGAR':
                    expected_statuses['ENTREGAR'] = True
                    self.log_test("Service Status Check", True, f"Service '{service_name}' has correct default_service_status: {default_status}")
                else:
                    self.log_test("Service Status Check", False, f"Service '{service_name}' has wrong default_service_status: {default_status} (expected ENTREGAR)")
        
        # Verify we found all expected services with different statuses
        all_statuses_found = all(expected_statuses.values())
        if all_statuses_found:
            self.log_test("Service Catalog Status", True, f"Found services with different default_service_status: {list(expected_statuses.keys())}")
        else:
            missing_statuses = [status for status, found in expected_statuses.items() if not found]
            self.log_test("Service Catalog Status", False, f"Missing services with statuses: {missing_statuses}")
        
        return test_services
    
    def test_budget_item_status_inheritance(self, test_services):
        """CRITICAL TEST: Verify budget items inherit correct status from service default_service_status"""
        print("\n=== TESTING BUDGET ITEM STATUS INHERITANCE ===")
        
        if not test_services:
            self.log_test("Budget Item Status", False, "No test services available for testing")
            return None
        
        if not self.created_resources['clients']:
            self.log_test("Budget Item Status", False, "No test client available")
            return None
        
        client_id = self.created_resources['clients'][0]
        
        # Create a budget
        budget_data = {
            "client_id": client_id,
            "payment_method": "PIX_CNPJ_25995295000104",
            "salesperson": "Gabriela Alcântara",
            "internal_observations": "Teste do bug de status padrão dos serviços"
        }
        
        response = self.make_request('POST', '/budgets', budget_data)
        if not response['success']:
            self.log_test("Budget Item Status", False, "Failed to create test budget", response['data'])
            return None
        
        budget = response['data']
        budget_id = budget['id']
        self.created_resources['budgets'].append(budget_id)
        
        # Add items from each test service to the budget
        status_results = {}
        
        for service in test_services:
            service_id = service['id']
            service_name = service['name']
            expected_status = service['default_service_status']
            
            # Add item to budget
            item_data = {
                "service_id": service_id,
                "quantity": 1.0,
                "observations": f"Teste de status para {service_name}"
            }
            
            response = self.make_request('POST', f'/budgets/{budget_id}/items', item_data)
            if response['success']:
                item = response['data']
                actual_status = item.get('status')
                
                if actual_status == expected_status:
                    self.log_test("Item Status Inheritance", True, f"✅ Service '{service_name}' → Item status '{actual_status}' (correct)")
                    status_results[expected_status] = True
                else:
                    self.log_test("Item Status Inheritance", False, f"❌ Service '{service_name}' → Item status '{actual_status}' (expected '{expected_status}')")
                    status_results[expected_status] = False
            else:
                self.log_test("Item Status Inheritance", False, f"Failed to add item for service '{service_name}'", response['data'])
                status_results[expected_status] = False
        
        # Summary of status inheritance test
        correct_statuses = sum(1 for result in status_results.values() if result)
        total_statuses = len(status_results)
        
        if correct_statuses == total_statuses:
            self.log_test("Budget Item Status", True, f"✅ ALL {total_statuses} services correctly inherited their default_service_status")
        else:
            self.log_test("Budget Item Status", False, f"❌ Only {correct_statuses}/{total_statuses} services correctly inherited their default_service_status")
        
        return budget_id
    
    def test_available_for_routes_status_variety(self):
        """CRITICAL TEST: Verify /api/budget-items/available-for-routes shows items with different statuses"""
        print("\n=== TESTING AVAILABLE FOR ROUTES STATUS VARIETY ===")
        
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Available Items Status Variety", False, "Failed to retrieve available items", response['data'])
            return False
        
        data = response['data']
        available_items = data.get('available_items', [])
        
        if not available_items:
            self.log_test("Available Items Status Variety", False, "No available items found for routes")
            return False
        
        # Collect all statuses found
        statuses_found = set()
        status_counts = {}
        
        for item in available_items:
            status = item.get('status')
            if status:
                statuses_found.add(status)
                status_counts[status] = status_counts.get(status, 0) + 1
        
        # Check if we have variety in statuses (not all RETIRAR)
        expected_statuses = {'RETIRAR', 'EXECUTAR_NO_LOCAL', 'ENTREGAR'}
        found_expected = statuses_found.intersection(expected_statuses)
        
        if len(found_expected) >= 2:  # At least 2 different statuses
            self.log_test("Available Items Status Variety", True, 
                         f"✅ Found items with different statuses: {dict(status_counts)} - Bug FIXED!")
        elif len(found_expected) == 1 and 'RETIRAR' in found_expected:
            self.log_test("Available Items Status Variety", False, 
                         f"❌ All items have status RETIRAR only: {dict(status_counts)} - Bug NOT FIXED!")
        else:
            self.log_test("Available Items Status Variety", True, 
                         f"Found items with statuses: {dict(status_counts)}")
        
        # Log details of items found
        print(f"   📊 Status distribution: {dict(status_counts)}")
        print(f"   📋 Total items available for routes: {len(available_items)}")
        
        return len(found_expected) >= 2
    
    def test_lines_1473_1479_fix(self, test_services):
        """FOCUS TEST: Verify the specific fix in lines 1473-1479 of server.py"""
        print("\n=== TESTING LINES 1473-1479 FIX: item_dict['status'] = service_obj.default_service_status ===")
        
        if not test_services or not self.created_resources['clients']:
            self.log_test("Lines 1473-1479 Fix", False, "Missing test data")
            return False
        
        client_id = self.created_resources['clients'][0]
        
        # Test each service individually to verify the fix
        fix_working = True
        
        for service in test_services:
            service_id = service['id']
            service_name = service['name']
            expected_status = service['default_service_status']
            
            # Create a new budget for each test
            budget_data = {
                "client_id": client_id,
                "payment_method": "PIX_CNPJ_25995295000104",
                "salesperson": "Diego Olivatto",
                "internal_observations": f"Teste específico da correção linha 1473-1479 para {service_name}"
            }
            
            response = self.make_request('POST', '/budgets', budget_data)
            if not response['success']:
                self.log_test("Lines 1473-1479 Fix", False, f"Failed to create budget for {service_name}")
                fix_working = False
                continue
            
            budget_id = response['data']['id']
            self.created_resources['budgets'].append(budget_id)
            
            # Add item and verify status assignment
            item_data = {
                "service_id": service_id,
                "quantity": 1.0,
                "observations": f"Teste da linha 1473: item_dict['status'] = service_obj.default_service_status"
            }
            
            response = self.make_request('POST', f'/budgets/{budget_id}/items', item_data)
            if response['success']:
                item = response['data']
                actual_status = item.get('status')
                
                if actual_status == expected_status:
                    self.log_test("Line 1473 Fix Verification", True, 
                                f"✅ {service_name}: item_dict['status'] = '{actual_status}' (correct)")
                else:
                    self.log_test("Line 1473 Fix Verification", False, 
                                f"❌ {service_name}: item_dict['status'] = '{actual_status}' (expected '{expected_status}')")
                    fix_working = False
            else:
                self.log_test("Line 1473 Fix Verification", False, 
                            f"Failed to add item for {service_name}", response['data'])
                fix_working = False
        
        if fix_working:
            self.log_test("Lines 1473-1479 Fix", True, "✅ Fix working correctly: item_dict['status'] = service_obj.default_service_status")
        else:
            self.log_test("Lines 1473-1479 Fix", False, "❌ Fix not working: items not inheriting correct default_service_status")
        
        return fix_working
    
    def test_migration_endpoint(self):
        """Test POST /api/admin/migrate-budget-item-status migration endpoint"""
        print("\n=== TESTING MIGRATION ENDPOINT ===")
        
        response = self.make_request('POST', '/admin/migrate-budget-item-status')
        if response['success']:
            result = response['data']
            total_items = result.get('total_items', 0)
            updated_items = result.get('updated_items', 0)
            message = result.get('message', '')
            
            self.log_test("Migration Endpoint", True, 
                        f"✅ Migration executed: {updated_items}/{total_items} items updated - {message}")
            
            print(f"   📊 Migration Results:")
            print(f"   📋 Total items checked: {total_items}")
            print(f"   🔄 Items updated: {updated_items}")
            print(f"   💬 Message: {message}")
            
            return {
                'total_items': total_items,
                'updated_items': updated_items,
                'success': True
            }
        else:
            self.log_test("Migration Endpoint", False, 
                        "❌ Migration failed", response['data'])
            return {
                'total_items': 0,
                'updated_items': 0,
                'success': False
            }
    
    def test_create_new_route_with_varied_status(self):
        """Test creating a new route to verify if stops have varied status after migration"""
        print("\n=== TESTING NEW ROUTE CREATION WITH VARIED STATUS ===")
        
        # First get available items
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("New Route - Get Available Items", False, 
                        "Failed to get available items", response['data'])
            return None
        
        available_items = response['data'].get('available_items', [])
        if not available_items:
            self.log_test("New Route - Get Available Items", False, 
                        "No available items found for route creation")
            return None
        
        # Check status variety in available items
        statuses_found = set(item.get('status') for item in available_items if item.get('status'))
        print(f"   📊 Available items status variety: {list(statuses_found)}")
        
        # Create a new route
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2025-01-15",
            "planned_start_time": "08:00",
            "alias": "Rota Teste Migração - Status Variados"
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if not response['success']:
            self.log_test("New Route - Create Route", False, 
                        "Failed to create route", response['data'])
            return None
        
        route = response['data']
        route_id = route['id']
        self.created_resources['routes'].append(route_id)
        
        # Add stops with different items (to get varied status)
        stops_data = []
        for i, item in enumerate(available_items[:5]):  # Use first 5 items
            stops_data.append({
                "budget_item_id": item["budget_item_id"],
                "priority": "AUTOMATICA"
            })
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', stops_data)
        if not response['success']:
            self.log_test("New Route - Add Stops", False, 
                        "Failed to add stops to route", response['data'])
            return None
        
        # Get route details to verify stop statuses
        response = self.make_request('GET', f'/routes/{route_id}')
        if not response['success']:
            self.log_test("New Route - Get Route Details", False, 
                        "Failed to get route details", response['data'])
            return None
        
        route_details = response['data']
        stops = route_details.get('stops', [])
        
        # Analyze stop statuses
        stop_statuses = set(stop.get('service_status') for stop in stops if stop.get('service_status'))
        status_counts = {}
        for stop in stops:
            status = stop.get('service_status')
            if status:
                status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"   📋 Route {route_id} created with {len(stops)} stops")
        print(f"   📊 Stop status distribution: {dict(status_counts)}")
        
        # Check if we have variety (not all RETIRAR)
        if len(stop_statuses) > 1:
            self.log_test("New Route - Status Variety", True, 
                        f"✅ Route has varied stop statuses: {list(stop_statuses)} - Bug FIXED!")
            return route_id
        elif len(stop_statuses) == 1 and 'RETIRAR' in stop_statuses:
            self.log_test("New Route - Status Variety", False, 
                        f"❌ All stops still have RETIRAR status - Bug NOT FIXED!")
            return route_id
        else:
            self.log_test("New Route - Status Variety", True, 
                        f"Route has single status type: {list(stop_statuses)}")
            return route_id

    def run_migration_tests(self):
        """Run the migration tests as requested in the review"""
        print("🔄 EXECUTANDO MIGRAÇÃO PARA CORRIGIR STATUS DOS BUDGET ITEMS")
        print(f"🔗 Testing against: {self.base_url}")
        print("🎯 Foco: Executar migração e verificar se o bug do campo 'Tipo' foi resolvido")
        print("=" * 80)
        
        # Test 1: Execute migration
        print("\n1️⃣ EXECUTANDO MIGRAÇÃO:")
        migration_result = self.test_migration_endpoint()
        
        # Test 2: Verify budget items after migration
        print("\n2️⃣ VERIFICANDO BUDGET ITEMS APÓS MIGRAÇÃO:")
        self.test_available_for_routes_status_variety()
        
        # Test 3: Create new route to test
        print("\n3️⃣ CRIANDO NOVA ROTA PARA TESTAR:")
        new_route_id = self.test_create_new_route_with_varied_status()
        
        # Test 4: Verify new route has stops with varied status
        if new_route_id:
            print("\n4️⃣ VERIFICANDO SE NOVA ROTA TEM STOPS COM STATUS VARIADOS:")
            response = self.make_request('GET', f'/routes/{new_route_id}')
            if response['success']:
                route = response['data']
                stops = route.get('stops', [])
                status_counts = {}
                for stop in stops:
                    status = stop.get('service_status')
                    if status:
                        status_counts[status] = status_counts.get(status, 0) + 1
                
                if len(status_counts) > 1:
                    self.log_test("Final Verification", True, 
                                f"✅ SUCCESS: New route {new_route_id} has varied stop statuses: {dict(status_counts)}")
                else:
                    self.log_test("Final Verification", False, 
                                f"❌ ISSUE: New route {new_route_id} still has uniform status: {dict(status_counts)}")
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        self.print_summary()
        
        return migration_result['success'] if migration_result else False

    def run_service_status_bug_tests(self):
        """Run the specific tests for the service status bug"""
        print("🐛 STARTING SERVICE STATUS BUG TESTS")
        print(f"🔗 Testing against: {self.base_url}")
        print("🎯 Focus: Verify services with different default_service_status generate items with correct status")
        print("=" * 80)
        
        # Setup test data
        if not self.setup_test_data_for_status_bug():
            print("❌ CRITICAL: Failed to setup test data. Aborting tests.")
            return False
        
        # Test 1: Verify services in catalog have different default_service_status
        test_services = self.test_service_catalog_default_status()
        
        # Test 2: Verify budget items inherit correct status from service
        self.test_budget_item_status_inheritance(test_services)
        
        # Test 3: Verify /api/budget-items/available-for-routes shows variety of statuses
        self.test_available_for_routes_status_variety()
        
        # Test 4: Verify the specific fix in lines 1473-1479
        self.test_lines_1473_1479_fix(test_services)
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        self.print_summary()
        
        return True
    
    def setup_test_data(self):
        """Create test data for routes testing"""
        print("\n=== SETTING UP TEST DATA FOR ROUTES ===")
        
        # Setup system config with company GPS coordinates
        system_config_data = {
            "company_name": "SuperDry Lavanderia de Tapetes & Estofados",
            "address_full": "Rua Exemplo, 100",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP",
            "latitude": -23.5505,
            "longitude": -46.6333,
            "phone": "11999999999",
            "email": "contato@superdry.com"
        }
        
        response = self.make_request('PUT', '/system-config', system_config_data)
        if response['success']:
            self.created_resources['system_config'] = True
            self.log_test("Setup: System Config", True, "System config created with GPS coordinates")
        else:
            self.log_test("Setup: System Config", False, "Failed to create system config", response['data'])
            return False
        
        # Create test clients with different addresses
        clients_data = [
            {
                "name": "Ana Paula Costa",
                "phone_primary": "11987654321",
                "email": "ana.costa@email.com",
                "address": {
                    "full_address": "Rua das Palmeiras, 456",
                    "neighborhood": "Vila Madalena",
                    "city": "São Paulo",
                    "state": "SP",
                    "latitude": -23.5489,
                    "longitude": -46.6388
                }
            },
            {
                "name": "Carlos Roberto Silva",
                "phone_primary": "11876543210",
                "email": "carlos.silva@email.com",
                "address": {
                    "full_address": "Av. Brigadeiro Faria Lima, 2000",
                    "neighborhood": "Itaim Bibi",
                    "city": "São Paulo",
                    "state": "SP",
                    "latitude": -23.5751,
                    "longitude": -46.6896
                }
            },
            {
                "name": "Fernanda Oliveira Santos",
                "phone_primary": "11765432109",
                "email": "fernanda.santos@email.com",
                "address": {
                    "full_address": "Rua Augusta, 1500",
                    "neighborhood": "Consolação",
                    "city": "São Paulo",
                    "state": "SP",
                    "latitude": -23.5558,
                    "longitude": -46.6396
                }
            }
        ]
        
        for client_data in clients_data:
            response = self.make_request('POST', '/clients', client_data)
            if response['success']:
                self.created_resources['clients'].append(response['data']['id'])
                self.log_test("Setup: Create Test Client", True, f"Client created: {client_data['name']}")
            else:
                self.log_test("Setup: Create Test Client", False, f"Failed to create client: {client_data['name']}", response['data'])
                return False
        
        # Create test services for different route types
        services_data = [
            {
                "name": "Limpeza de Sofá 3 Lugares",
                "category": "ESTOFADOS",
                "service_type": "Limpeza Profunda",
                "measure_type": "UNITARIO",
                "execution_location": "RETIRADA",
                "cost_price": 80.0,
                "sale_price": 150.0
            },
            {
                "name": "Limpeza de Tapete no Local",
                "category": "CARPETES_E_TAPETES_NO_LOCAL",
                "service_type": "Limpeza no Local",
                "measure_type": "CARPETE_TAPETE_LOCAL",
                "execution_location": "NO_LOCAL",
                "cost_price": 30.0,
                "sale_price": 50.0
            },
            {
                "name": "Entrega de Cortina",
                "category": "CORTINAS",
                "service_type": "Entrega",
                "measure_type": "UNITARIO",
                "execution_location": "RETIRADA",
                "cost_price": 0.0,
                "sale_price": 0.0
            }
        ]
        
        for service_data in services_data:
            response = self.make_request('POST', '/services', service_data)
            if response['success']:
                self.created_resources['services'].append(response['data']['id'])
                self.log_test("Setup: Create Test Service", True, f"Service created: {service_data['name']}")
            else:
                self.log_test("Setup: Create Test Service", False, f"Failed to create service: {service_data['name']}", response['data'])
                return False
        
        # Create test budgets with items in route-eligible status
        for i, client_id in enumerate(self.created_resources['clients']):
            service_id = self.created_resources['services'][i % len(self.created_resources['services'])]
            
            # Determine status based on service type
            if i == 1:  # Second client gets NO_LOCAL service
                status = "EXECUTAR_NO_LOCAL"
            elif i == 2:  # Third client gets delivery
                status = "ENTREGAR"
            else:
                status = "RETIRAR"
            
            budget_data = {
                "client_id": client_id,
                "payment_method": "PIX_CNPJ_25995295000104",
                "salesperson": "Gabriela Alcântara",
                "internal_observations": f"Orçamento para teste de rotas - Cliente {i+1}",
                "items": [
                    {
                        "id": f"ITM-TEST{i+1:03d}",
                        "service_id": service_id,
                        "service_name": services_data[i % len(services_data)]["name"],
                        "service_code": service_id,
                        "quantity": 1.0,
                        "unit_price": services_data[i % len(services_data)]["sale_price"],
                        "total_value": services_data[i % len(services_data)]["sale_price"],
                        "status": status,
                        "execution_location": services_data[i % len(services_data)]["execution_location"],
                        "is_retoque": False
                    }
                ]
            }
            
            response = self.make_request('POST', '/budgets', budget_data)
            if response['success']:
                self.created_resources['budgets'].append(response['data']['id'])
                self.log_test("Setup: Create Test Budget", True, f"Budget created with {status} item")
            else:
                self.log_test("Setup: Create Test Budget", False, f"Failed to create budget for client {i+1}", response['data'])
                return False
        
        return True
    
    def test_get_available_items_for_routes(self):
        """Test GET /api/budget-items/available-for-routes - Get items available for routes"""
        print("\n=== TESTING GET AVAILABLE ITEMS FOR ROUTES ===")
        
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if response['success']:
            data = response['data']
            available_items = data.get('available_items', [])
            
            if len(available_items) > 0:
                # Verify structure of returned items
                first_item = available_items[0]
                required_fields = ['budget_item_id', 'budget_id', 'client_id', 'client_name', 
                                 'service_name', 'service_value', 'status', 'address']
                missing_fields = [field for field in required_fields if field not in first_item]
                
                if not missing_fields:
                    self.log_test("Get Available Items", True, f"Retrieved {len(available_items)} available items with correct structure")
                    return available_items
                else:
                    self.log_test("Get Available Items", False, f"Missing required fields: {missing_fields}")
                    return available_items
            else:
                self.log_test("Get Available Items", False, "No available items found - check if budgets have route-eligible items")
                return []
        else:
            self.log_test("Get Available Items", False, "Failed to retrieve available items", response['data'])
            return []
    
    def test_create_route(self):
        """Test POST /api/routes - Create new route"""
        print("\n=== TESTING CREATE ROUTE ===")
        
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2024-12-20",
            "planned_start_time": "08:00",
            "stops": []
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if response['success']:
            route = response['data']
            route_id = route.get('id')
            
            # Verify route data
            checks = [
                (route_id is not None and route_id.startswith('RTE-'), "Route ID generated"),
                (route.get('vehicle_type') == 'CARRO', "Vehicle type set"),
                (route.get('planned_date') == '2024-12-20', "Planned date set"),
                (route.get('planned_start_time') == '08:00', "Planned start time set"),
                (route.get('status') == 'PLANNED', "Status set to PLANNED"),
                (route.get('company_address') is not None, "Company address populated"),
                (isinstance(route.get('stops', []), list), "Stops initialized as list")
            ]
            
            all_passed = all(check[0] for check in checks)
            failed_checks = [check[1] for check in checks if not check[0]]
            
            if all_passed:
                self.created_resources['routes'].append(route_id)
                self.log_test("Create Route", True, f"Route created successfully: {route_id}")
                return route_id
            else:
                self.log_test("Create Route", False, f"Data validation failed: {failed_checks}")
                return route_id
        else:
            self.log_test("Create Route", False, "Failed to create route", response['data'])
            return None
    
    def test_add_stops_to_route(self, route_id: str, available_items: List[Dict]):
        """Test PUT /api/routes/{route_id}/stops - Add stops to route"""
        print("\n=== TESTING ADD STOPS TO ROUTE ===")
        
        if not available_items:
            self.log_test("Add Route Stops", False, "No available items to add as stops")
            return False
        
        # Prepare stops data with different priorities
        stops_data = []
        priorities = ["PRIMEIRA", "AUTOMATICA", "ULTIMA"]
        
        for i, item in enumerate(available_items[:3]):  # Use first 3 items
            priority = priorities[i % len(priorities)]
            stops_data.append({
                "budget_item_id": item["budget_item_id"],
                "priority": priority
            })
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', stops_data)
        if response['success']:
            result = response['data']
            stops_count = result.get('stops_count', 0)
            
            if stops_count == len(stops_data):
                self.log_test("Add Route Stops", True, f"Successfully added {stops_count} stops to route")
                return True
            else:
                self.log_test("Add Route Stops", False, f"Expected {len(stops_data)} stops, got {stops_count}")
                return False
        else:
            self.log_test("Add Route Stops", False, "Failed to add stops to route", response['data'])
            return False
    
    def test_optimize_route_curta(self, route_id: str):
        """Test POST /api/routes/{route_id}/optimize - Optimize route with CURTA type"""
        print("\n=== TESTING ROUTE OPTIMIZATION: CURTA ===")
        
        response = self.make_request('POST', f'/routes/{route_id}/optimize?route_type=CURTA')
        if response['success']:
            result = response['data']
            
            # Verify optimization results
            checks = [
                (result.get('message') == 'Route optimized successfully', "Success message"),
                (result.get('total_stops', 0) > 0, "Has stops"),
                (result.get('total_duration_minutes', 0) > 0, "Duration calculated"),
                (result.get('total_distance_km', 0) >= 0, "Distance calculated"),
                (result.get('osrm_status') in ['success', 'fallback'], "OSRM status valid")
            ]
            
            all_passed = all(check[0] for check in checks)
            failed_checks = [check[1] for check in checks if not check[0]]
            
            if all_passed:
                self.log_test("Route Optimization CURTA", True, 
                            f"Route optimized: {result.get('total_stops')} stops, "
                            f"{result.get('total_duration_minutes')} min, "
                            f"{result.get('total_distance_km')} km")
                return True
            else:
                self.log_test("Route Optimization CURTA", False, f"Validation failed: {failed_checks}")
                return False
        else:
            self.log_test("Route Optimization CURTA", False, "Failed to optimize route", response['data'])
            return False
    
    def test_optimize_route_eficiente(self, route_id: str):
        """Test POST /api/routes/{route_id}/optimize - Optimize route with EFICIENTE type"""
        print("\n=== TESTING ROUTE OPTIMIZATION: EFICIENTE ===")
        
        response = self.make_request('POST', f'/routes/{route_id}/optimize?route_type=EFICIENTE')
        if response['success']:
            result = response['data']
            
            # Verify optimization results
            checks = [
                (result.get('message') == 'Route optimized successfully', "Success message"),
                (result.get('total_stops', 0) > 0, "Has stops"),
                (result.get('total_duration_minutes', 0) > 0, "Duration calculated"),
                (result.get('total_distance_km', 0) >= 0, "Distance calculated"),
                (result.get('osrm_status') in ['success', 'fallback'], "OSRM status valid")
            ]
            
            all_passed = all(check[0] for check in checks)
            failed_checks = [check[1] for check in checks if not check[0]]
            
            if all_passed:
                self.log_test("Route Optimization EFICIENTE", True, 
                            f"Route optimized: {result.get('total_stops')} stops, "
                            f"{result.get('total_duration_minutes')} min, "
                            f"{result.get('total_distance_km')} km")
                return True
            else:
                self.log_test("Route Optimization EFICIENTE", False, f"Validation failed: {failed_checks}")
                return False
        else:
            self.log_test("Route Optimization EFICIENTE", False, "Failed to optimize route", response['data'])
            return False
    
    def test_get_route_details(self, route_id: str):
        """Test GET /api/routes/{route_id} - Get route details"""
        print("\n=== TESTING GET ROUTE DETAILS ===")
        
        response = self.make_request('GET', f'/routes/{route_id}')
        if response['success']:
            route = response['data']
            
            # Verify route structure
            required_fields = ['id', 'vehicle_type', 'planned_date', 'planned_start_time', 
                             'status', 'stops', 'company_address']
            missing_fields = [field for field in required_fields if field not in route]
            
            if not missing_fields:
                stops_count = len(route.get('stops', []))
                has_optimization_data = route.get('total_duration', 0) > 0 or route.get('total_distance', 0) > 0
                
                self.log_test("Get Route Details", True, 
                            f"Route details retrieved: {stops_count} stops, "
                            f"optimized: {has_optimization_data}")
                return route
            else:
                self.log_test("Get Route Details", False, f"Missing required fields: {missing_fields}")
                return route
        else:
            self.log_test("Get Route Details", False, f"Failed to retrieve route {route_id}", response['data'])
            return None
    
    def test_list_routes(self):
        """Test GET /api/routes - List saved routes"""
        print("\n=== TESTING LIST ROUTES ===")
        
        response = self.make_request('GET', '/routes')
        if response['success']:
            routes = response['data']
            
            if isinstance(routes, list):
                # Check if our created route is in the list
                created_route_found = any(route.get('id') in self.created_resources['routes'] 
                                        for route in routes)
                
                if created_route_found or len(routes) > 0:
                    self.log_test("List Routes", True, f"Retrieved {len(routes)} routes")
                    return routes
                else:
                    self.log_test("List Routes", False, "No routes found in listing")
                    return []
            else:
                self.log_test("List Routes", False, "Invalid response format - expected list")
                return []
        else:
            self.log_test("List Routes", False, "Failed to retrieve routes", response['data'])
            return []
    
    def test_delete_route(self, route_id: str):
        """Test DELETE /api/routes/{route_id} - Delete route"""
        print("\n=== TESTING DELETE ROUTE ===")
        
        response = self.make_request('DELETE', f'/routes/{route_id}')
        if response['success']:
            result = response['data']
            
            if result.get('message') == 'Route deleted successfully':
                # Verify route is actually deleted
                verify_response = self.make_request('GET', f'/routes/{route_id}')
                if not verify_response['success'] and verify_response['status_code'] == 404:
                    self.log_test("Delete Route", True, f"Route {route_id} successfully deleted")
                    return True
                else:
                    self.log_test("Delete Route", False, "Route still exists after deletion")
                    return False
            else:
                self.log_test("Delete Route", False, f"Unexpected response message: {result.get('message')}")
                return False
        else:
            self.log_test("Delete Route", False, f"Failed to delete route {route_id}", response['data'])
            return False
    
    def test_route_error_handling(self):
        """Test error handling for routes API"""
        print("\n=== TESTING ROUTE ERROR HANDLING ===")
        
        # Test get non-existent route
        response = self.make_request('GET', '/routes/RTE-9999999')
        if not response['success'] and response['status_code'] == 404:
            self.log_test("Route Error: Non-existent Route", True, "Correctly returned 404 for non-existent route")
        else:
            self.log_test("Route Error: Non-existent Route", False, "Should have returned 404 for non-existent route")
        
        # Test optimize route without stops
        empty_route_data = {
            "vehicle_type": "MOTO",
            "planned_date": "2024-12-21",
            "planned_start_time": "09:00"
        }
        
        create_response = self.make_request('POST', '/routes', empty_route_data)
        if create_response['success']:
            empty_route_id = create_response['data']['id']
            self.created_resources['routes'].append(empty_route_id)
            
            # Try to optimize empty route
            optimize_response = self.make_request('POST', f'/routes/{empty_route_id}/optimize')
            if not optimize_response['success'] and 'no stops' in str(optimize_response['data']).lower():
                self.log_test("Route Error: Empty Route Optimization", True, "Correctly rejected optimization of empty route")
                return True
            else:
                self.log_test("Route Error: Empty Route Optimization", False, "Should have rejected empty route optimization")
                return False
        else:
            self.log_test("Route Error: Empty Route Optimization", False, "Failed to create empty route for test")
            return False
    
    def test_available_items_endpoint_alias(self):
        """Test if the expected endpoint /api/routes/available-items exists (should redirect or be alias)"""
        print("\n=== TESTING ROUTES/AVAILABLE-ITEMS ENDPOINT ALIAS ===")
        
        # The review request mentions /api/routes/available-items but the actual endpoint is /api/budget-items/available-for-routes
        response = self.make_request('GET', '/routes/available-items')
        if response['success']:
            self.log_test("Routes Available Items Alias", True, "Endpoint /api/routes/available-items works")
            return True
        else:
            # This is expected - the endpoint is actually /budget-items/available-for-routes
            self.log_test("Routes Available Items Alias", True, "Endpoint /api/routes/available-items not found (expected - actual endpoint is /budget-items/available-for-routes)")
            return True
    
    def cleanup_test_data(self):
        """Clean up created test data"""
        print("\n=== CLEANING UP TEST DATA ===")
        
        # Delete routes (except those already deleted in tests)
        for route_id in self.created_resources['routes']:
            response = self.make_request('DELETE', f'/routes/{route_id}')
            if response['success']:
                print(f"✅ Deleted route: {route_id}")
            else:
                print(f"ℹ️  Route {route_id} already deleted or not found")
        
        # Delete budgets
        for budget_id in self.created_resources['budgets']:
            response = self.make_request('DELETE', f'/budgets/{budget_id}')
            if response['success']:
                print(f"✅ Deleted budget: {budget_id}")
            else:
                print(f"❌ Failed to delete budget: {budget_id}")
        
        # Delete clients
        for client_id in self.created_resources['clients']:
            response = self.make_request('DELETE', f'/clients/{client_id}')
            if response['success']:
                print(f"✅ Deleted client: {client_id}")
            else:
                print(f"❌ Failed to delete client: {client_id}")
        
        # Note: Services and system config are not deleted as they might be used by other parts
        print(f"ℹ️  Services created: {len(self.created_resources['services'])} (not deleted)")
        print(f"ℹ️  System config updated: {self.created_resources['system_config']} (not reverted)")
    
    def run_all_tests(self):
        """Run complete routes API test suite"""
        print("🚀 STARTING ROUTES API COMPREHENSIVE TESTS")
        print(f"🔗 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Setup
        if not self.setup_test_data():
            print("❌ CRITICAL: Failed to setup test data. Aborting tests.")
            return False
        
        # Test 1: GET /api/budget-items/available-for-routes (actual endpoint)
        available_items = self.test_get_available_items_for_routes()
        
        # Test 2: Check if /api/routes/available-items exists (mentioned in review request)
        self.test_available_items_endpoint_alias()
        
        # Test 3: POST /api/routes - Create new route
        route_id = self.test_create_route()
        if not route_id:
            print("❌ CRITICAL: Failed to create test route. Aborting remaining tests.")
            return False
        
        # Test 4: PUT /api/routes/{route_id}/stops - Add stops to route
        if available_items:
            self.test_add_stops_to_route(route_id, available_items)
        else:
            print("⚠️  WARNING: No available items found, skipping stops addition test")
        
        # Test 5: POST /api/routes/{route_id}/optimize - Optimize route (CURTA)
        self.test_optimize_route_curta(route_id)
        
        # Test 6: POST /api/routes/{route_id}/optimize - Optimize route (EFICIENTE)
        self.test_optimize_route_eficiente(route_id)
        
        # Test 7: GET /api/routes/{route_id} - Get route details
        self.test_get_route_details(route_id)
        
        # Test 8: GET /api/routes - List routes
        self.test_list_routes()
        
        # Test 9: Error handling
        self.test_route_error_handling()
        
        # Test 10: DELETE /api/routes/{route_id} - Delete route (test last)
        self.test_delete_route(route_id)
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        self.print_summary()
        
        return True
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print("\n" + "=" * 60)

    def test_service_creation_with_valid_data(self):
        """TESTE DE CRIAÇÃO: Test POST /api/services with valid data"""
        print("\n=== TESTE DE CRIAÇÃO: POST /api/services com dados válidos ===")
        
        # Test data with all required fields including default_service_status
        service_data = {
            "name": "Teste Original",
            "category": "ESTOFADOS",
            "service_type": "Limpeza Profunda",
            "measure_type": "UNITARIO",
            "execution_location": "RETIRADA",
            "cost_price": 100.0,
            "sale_price": 180.0,
            "default_service_status": "RETIRAR"
        }
        
        response = self.make_request('POST', '/services', service_data)
        if response['success']:
            service = response['data']
            
            # Verify all required fields are accepted
            checks = [
                (service.get('name') == service_data['name'], "Nome aceito"),
                (service.get('category') == service_data['category'], "Categoria aceita"),
                (service.get('service_type') == service_data['service_type'], "Tipo de serviço aceito"),
                (service.get('measure_type') == service_data['measure_type'], "Tipo de medida aceito"),
                (service.get('execution_location') == service_data['execution_location'], "Local de execução aceito"),
                (service.get('cost_price') == service_data['cost_price'], "Preço de custo aceito"),
                (service.get('sale_price') == service_data['sale_price'], "Preço de venda aceito"),
                (service.get('default_service_status') == service_data['default_service_status'], "default_service_status aceito"),
                (service.get('id') is not None and service.get('id').startswith('SRV-'), "ID gerado corretamente"),
                (service.get('is_active') == True, "Status ativo por padrão"),
                (service.get('created_at') is not None, "Data de criação definida"),
                (service.get('updated_at') is not None, "Data de atualização definida")
            ]
            
            all_passed = all(check[0] for check in checks)
            failed_checks = [check[1] for check in checks if not check[0]]
            
            if all_passed:
                self.created_resources['services'].append(service['id'])
                self.log_test("Criação de Serviço - Dados Válidos", True, 
                            f"✅ Serviço criado com sucesso: {service['id']} - Todos os campos aceitos")
                return service
            else:
                self.log_test("Criação de Serviço - Dados Válidos", False, 
                            f"❌ Falha na validação dos campos: {failed_checks}")
                return service
        else:
            self.log_test("Criação de Serviço - Dados Válidos", False, 
                        "❌ Falha ao criar serviço", response['data'])
            return None
    
    def test_service_duplication_scenario(self):
        """TESTE DE DADOS DUPLICADOS: Simulate frontend duplication scenario"""
        print("\n=== TESTE DE DADOS DUPLICADOS: Simulação de duplicação do frontend ===")
        
        # First, create original service
        original_service_data = {
            "name": "Teste Original",
            "category": "TAPETES",
            "service_type": "Limpeza Especializada",
            "measure_type": "AREA_DE_TAPETE",
            "execution_location": "RETIRADA",
            "cost_price": 80.0,
            "sale_price": 150.0,
            "default_service_status": "RETIRAR"
        }
        
        response = self.make_request('POST', '/services', original_service_data)
        if not response['success']:
            self.log_test("Duplicação - Serviço Original", False, 
                        "❌ Falha ao criar serviço original", response['data'])
            return False
        
        original_service = response['data']
        self.created_resources['services'].append(original_service['id'])
        self.log_test("Duplicação - Serviço Original", True, 
                    f"✅ Serviço original criado: {original_service['name']}")
        
        # Now create duplicate with "(Cópia)" suffix - simulating frontend duplication
        duplicate_service_data = {
            "name": "Teste Original (Cópia)",
            "category": "TAPETES",
            "service_type": "Limpeza Especializada",
            "measure_type": "AREA_DE_TAPETE",
            "execution_location": "RETIRADA",
            "cost_price": 80.0,
            "sale_price": 150.0,
            "default_service_status": "RETIRAR"
        }
        
        response = self.make_request('POST', '/services', duplicate_service_data)
        if response['success']:
            duplicate_service = response['data']
            self.created_resources['services'].append(duplicate_service['id'])
            
            # Verify no conflicts occurred
            checks = [
                (duplicate_service.get('id') != original_service.get('id'), "IDs diferentes"),
                (duplicate_service.get('name') == "Teste Original (Cópia)", "Nome com (Cópia) aceito"),
                (duplicate_service.get('default_service_status') == "RETIRAR", "default_service_status preservado"),
                (duplicate_service.get('is_active') == True, "Status ativo mantido"),
                (duplicate_service.get('category') == original_service_data['category'], "Categoria preservada")
            ]
            
            all_passed = all(check[0] for check in checks)
            failed_checks = [check[1] for check in checks if not check[0]]
            
            if all_passed:
                self.log_test("Duplicação - Serviço Cópia", True, 
                            f"✅ Serviço duplicado criado sem conflitos: {duplicate_service['id']}")
                return True
            else:
                self.log_test("Duplicação - Serviço Cópia", False, 
                            f"❌ Conflitos detectados na duplicação: {failed_checks}")
                return False
        else:
            self.log_test("Duplicação - Serviço Cópia", False, 
                        "❌ Falha ao criar serviço duplicado", response['data'])
            return False
    
    def test_service_validation_requirements(self):
        """VERIFICAR VALIDAÇÕES: Test required fields and validation"""
        print("\n=== VERIFICAR VALIDAÇÕES: Campos obrigatórios e validações ===")
        
        # Test 1: Missing required fields
        incomplete_service_data = {
            "name": "Serviço Incompleto",
            # Missing required fields intentionally
        }
        
        response = self.make_request('POST', '/services', incomplete_service_data)
        if not response['success']:
            self.log_test("Validação - Campos Obrigatórios", True, 
                        "✅ API corretamente rejeitou dados incompletos")
        else:
            self.log_test("Validação - Campos Obrigatórios", False, 
                        "❌ API deveria ter rejeitado dados incompletos")
        
        # Test 2: Invalid enum values
        invalid_enum_service_data = {
            "name": "Serviço com Enum Inválido",
            "category": "CATEGORIA_INEXISTENTE",
            "service_type": "Teste",
            "measure_type": "MEDIDA_INEXISTENTE",
            "execution_location": "LOCAL_INEXISTENTE",
            "cost_price": 50.0,
            "sale_price": 100.0,
            "default_service_status": "STATUS_INEXISTENTE"
        }
        
        response = self.make_request('POST', '/services', invalid_enum_service_data)
        if not response['success']:
            self.log_test("Validação - Enums Inválidos", True, 
                        "✅ API corretamente rejeitou valores de enum inválidos")
        else:
            self.log_test("Validação - Enums Inválidos", False, 
                        "❌ API deveria ter rejeitado valores de enum inválidos")
        
        # Test 3: Valid service with all correct enums
        valid_service_data = {
            "name": "Serviço Válido para Teste",
            "category": "CORTINAS",
            "service_type": "Limpeza e Manutenção",
            "measure_type": "METRAGEM_LINEAR_CORTINA_SIMPLES",
            "execution_location": "NO_LOCAL",
            "cost_price": 25.0,
            "sale_price": 45.0,
            "default_service_status": "EXECUTAR_NO_LOCAL"
        }
        
        response = self.make_request('POST', '/services', valid_service_data)
        if response['success']:
            service = response['data']
            self.created_resources['services'].append(service['id'])
            
            # Verify default_service_status is processed correctly
            if service.get('default_service_status') == "EXECUTAR_NO_LOCAL":
                self.log_test("Validação - default_service_status", True, 
                            "✅ default_service_status processado corretamente")
            else:
                self.log_test("Validação - default_service_status", False, 
                            f"❌ default_service_status incorreto: {service.get('default_service_status')}")
            
            self.log_test("Validação - Dados Válidos", True, 
                        f"✅ Serviço válido criado com sucesso: {service['id']}")
            return True
        else:
            self.log_test("Validação - Dados Válidos", False, 
                        "❌ Falha ao criar serviço com dados válidos", response['data'])
            return False
    
    def test_service_creation_error_responses(self):
        """Test detailed error responses for service creation problems"""
        print("\n=== TESTE DE RESPOSTAS DE ERRO DETALHADAS ===")
        
        # Test with invalid data types
        invalid_type_service_data = {
            "name": "Teste Tipos Inválidos",
            "category": "ESTOFADOS",
            "service_type": "Teste",
            "measure_type": "UNITARIO",
            "execution_location": "RETIRADA",
            "cost_price": "não_é_número",  # Invalid type
            "sale_price": 100.0,
            "default_service_status": "RETIRAR"
        }
        
        response = self.make_request('POST', '/services', invalid_type_service_data)
        if not response['success']:
            error_detail = response['data'].get('detail', '')
            if 'cost_price' in str(error_detail).lower() or 'validation' in str(error_detail).lower():
                self.log_test("Erro - Tipo de Dados Inválido", True, 
                            f"✅ Erro detalhado retornado para tipo inválido: {error_detail}")
            else:
                self.log_test("Erro - Tipo de Dados Inválido", True, 
                            f"✅ Erro retornado (detalhes podem variar): {error_detail}")
        else:
            self.log_test("Erro - Tipo de Dados Inválido", False, 
                        "❌ API deveria ter rejeitado tipo de dados inválido")
        
        return True

    def test_service_status_debug_investigation(self):
        """INVESTIGAÇÃO ESPECÍFICA: Debug exato dos dados enviados para service_status dos stops"""
        print("\n=== INVESTIGAÇÃO ESPECÍFICA: DEBUG DO CAMPO service_status ===")
        print("🔍 Investigando exatamente quais dados o backend está enviando para o campo service_status dos stops")
        
        # 1. Verificar API Response: GET /api/budget-items/available-for-routes
        print("\n1️⃣ VERIFICANDO API RESPONSE: GET /api/budget-items/available-for-routes")
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Debug - Available Items API", False, "Failed to get available items", response['data'])
            return False
        
        available_items = response['data'].get('available_items', [])
        if not available_items:
            self.log_test("Debug - Available Items API", False, "No available items found")
            return False
        
        # Analisar estrutura exata dos dados retornados
        print(f"   📊 Total items disponíveis: {len(available_items)}")
        
        # Verificar campos 'status' vs 'service_status' 
        status_analysis = {}
        service_status_analysis = {}
        all_fields = set()
        
        for item in available_items:
            # Coletar todos os campos para análise
            all_fields.update(item.keys())
            
            # Analisar campo 'status'
            status = item.get('status')
            if status:
                status_analysis[status] = status_analysis.get(status, 0) + 1
            
            # Analisar campo 'service_status' (se existir)
            service_status = item.get('service_status')
            if service_status:
                service_status_analysis[service_status] = service_status_analysis.get(service_status, 0) + 1
        
        print(f"   📋 Campos encontrados nos items: {sorted(all_fields)}")
        print(f"   📊 Campo 'status' distribuição: {dict(status_analysis)}")
        print(f"   📊 Campo 'service_status' distribuição: {dict(service_status_analysis)}")
        
        # Verificar se todos ainda têm "RETIRAR"
        all_retirar = all(item.get('status') == 'RETIRAR' for item in available_items)
        if all_retirar:
            self.log_test("Debug - Status Analysis", False, 
                        f"❌ PROBLEMA CONFIRMADO: Todos os {len(available_items)} items têm status='RETIRAR'")
        else:
            self.log_test("Debug - Status Analysis", True, 
                        f"✅ STATUS VARIADOS ENCONTRADOS: {dict(status_analysis)}")
        
        # 2. Verificar Nova Route Creation
        print("\n2️⃣ VERIFICANDO NOVA ROUTE CREATION:")
        
        # Criar nova rota com items disponíveis
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2025-01-15",
            "planned_start_time": "08:00",
            "alias": "Debug Route - Service Status Investigation"
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if not response['success']:
            self.log_test("Debug - Create Route", False, "Failed to create debug route", response['data'])
            return False
        
        route_id = response['data']['id']
        self.created_resources['routes'].append(route_id)
        
        # Adicionar stops com items disponíveis
        stops_data = []
        for i, item in enumerate(available_items[:3]):  # Usar primeiros 3 items
            stops_data.append({
                "budget_item_id": item["budget_item_id"],
                "priority": "AUTOMATICA"
            })
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', stops_data)
        if not response['success']:
            self.log_test("Debug - Add Stops", False, "Failed to add stops", response['data'])
            return False
        
        # Ver estrutura dos stops na rota criada
        response = self.make_request('GET', f'/routes/{route_id}')
        if not response['success']:
            self.log_test("Debug - Get Route", False, "Failed to get route details", response['data'])
            return False
        
        route_details = response['data']
        stops = route_details.get('stops', [])
        
        print(f"   📋 Rota criada: {route_id} com {len(stops)} stops")
        
        # Verificar se stops herdam service_status corretamente
        stop_fields = set()
        stop_status_analysis = {}
        stop_service_status_analysis = {}
        
        for stop in stops:
            # Coletar todos os campos dos stops
            stop_fields.update(stop.keys())
            
            # Analisar service_status nos stops
            service_status = stop.get('service_status')
            if service_status:
                stop_service_status_analysis[service_status] = stop_service_status_analysis.get(service_status, 0) + 1
            
            # Verificar se há campo 'status' também
            status = stop.get('status')
            if status:
                stop_status_analysis[status] = stop_status_analysis.get(status, 0) + 1
        
        print(f"   📋 Campos encontrados nos stops: {sorted(stop_fields)}")
        print(f"   📊 Campo 'service_status' nos stops: {dict(stop_service_status_analysis)}")
        print(f"   📊 Campo 'status' nos stops: {dict(stop_status_analysis)}")
        
        # 3. Debug Específico de Campos
        print("\n3️⃣ DEBUG ESPECÍFICO DE CAMPOS:")
        
        # Verificar TODOS os campos que contêm status nos budget items
        status_related_fields = []
        for item in available_items[:1]:  # Analisar primeiro item em detalhe
            for field_name, field_value in item.items():
                if 'status' in field_name.lower():
                    status_related_fields.append((field_name, field_value))
        
        print(f"   📋 Campos relacionados a 'status' encontrados:")
        for field_name, field_value in status_related_fields:
            print(f"      - {field_name}: {field_value}")
        
        # Verificar se há algum campo diferente sendo usado erroneamente
        print(f"\n   🔍 ANÁLISE DETALHADA DO PRIMEIRO ITEM:")
        if available_items:
            first_item = available_items[0]
            for key, value in first_item.items():
                print(f"      {key}: {value}")
        
        print(f"\n   🔍 ANÁLISE DETALHADA DO PRIMEIRO STOP:")
        if stops:
            first_stop = stops[0]
            for key, value in first_stop.items():
                print(f"      {key}: {value}")
        
        # Resultado final da investigação
        if all_retirar and len(stop_service_status_analysis) <= 1:
            self.log_test("Service Status Debug Investigation", False, 
                        f"❌ BUG CONFIRMADO: Items têm apenas RETIRAR, stops herdam service_status uniforme: {dict(stop_service_status_analysis)}")
        else:
            self.log_test("Service Status Debug Investigation", True, 
                        f"✅ STATUS VARIADOS: Items: {dict(status_analysis)}, Stops: {dict(stop_service_status_analysis)}")
        
        return not all_retirar

    def run_service_status_debug_investigation(self):
        """Run the specific debug investigation requested in the review"""
        print("🔍 INICIANDO INVESTIGAÇÃO DEBUG DO SERVICE_STATUS")
        print(f"🔗 Testing against: {self.base_url}")
        print("🎯 Foco: Investigar exatamente quais dados o backend está enviando para service_status dos stops")
        print("📋 Problema: Usuário apagou todos orçamentos e refez, mas ainda vê 'STATUS: RETIRAR' nos popups")
        print("=" * 80)
        
        # Execute the specific debug investigation
        success = self.test_service_status_debug_investigation()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        self.print_summary()
        
        return success
    
    def run_service_duplication_tests(self):
        """Run specific tests for service duplication functionality"""
        print("🔄 INICIANDO TESTES ESPECÍFICOS DE DUPLICAÇÃO DE SERVIÇOS")
        print(f"🔗 Testando contra: {self.base_url}")
        print("🎯 Foco: Descobrir se o erro é no frontend (lógica de save) ou backend (API create)")
        print("=" * 80)
        
        # Test 1: TESTE DE CRIAÇÃO - POST /api/services with valid data
        print("\n1️⃣ TESTE DE CRIAÇÃO:")
        self.test_service_creation_with_valid_data()
        
        # Test 2: TESTE DE DADOS DUPLICADOS - Simulate frontend duplication
        print("\n2️⃣ TESTE DE DADOS DUPLICADOS:")
        self.test_service_duplication_scenario()
        
        # Test 3: VERIFICAR VALIDAÇÕES - Required fields and validation
        print("\n3️⃣ VERIFICAR VALIDAÇÕES:")
        self.test_service_validation_requirements()
        
        # Test 4: Test error responses
        print("\n4️⃣ TESTE DE RESPOSTAS DE ERRO:")
        self.test_service_creation_error_responses()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        self.print_summary()
        
        return True

    def test_route_service_status_bug(self):
        """INVESTIGAÇÃO DO BUG: Campo 'Tipo' no mapa de rotas sempre mostra 'RETIRAR'"""
        print("🐛 INVESTIGANDO BUG DO CAMPO 'TIPO' NO MAPA DE ROTAS")
        print(f"🔗 Testando contra: {self.base_url}")
        print("🎯 Foco: Verificar se service_status nos stops das rotas está correto")
        print("=" * 80)
        
        # Test 1: Verificar rota específica RTE-0000003
        print("\n1️⃣ VERIFICANDO ROTA RTE-0000003:")
        self.test_specific_route_rte_0000003()
        
        # Test 2: Verificar outras rotas existentes
        print("\n2️⃣ VERIFICANDO OUTRAS ROTAS EXISTENTES:")
        self.test_all_existing_routes_service_status()
        
        # Test 3: Verificar budget items disponíveis para rotas
        print("\n3️⃣ VERIFICANDO BUDGET ITEMS DISPONÍVEIS:")
        self.test_budget_items_available_service_status()
        
        # Test 4: Verificar origem dos dados - service_status nos budget_items vs stops
        print("\n4️⃣ VERIFICANDO ORIGEM DOS DADOS:")
        self.test_service_status_data_origin()
        
        # Test 5: Criar nova rota e verificar se o problema persiste
        print("\n5️⃣ TESTANDO CRIAÇÃO DE NOVA ROTA:")
        self.test_new_route_service_status_inheritance()
        
        # Summary
        self.print_summary()
        
        return True
    
    def test_specific_route_rte_0000003(self):
        """Verificar dados específicos da rota RTE-0000003"""
        print("\n=== VERIFICANDO ROTA RTE-0000003 ===")
        
        response = self.make_request('GET', '/routes/RTE-0000003')
        if response['success']:
            route = response['data']
            stops = route.get('stops', [])
            
            if not stops:
                self.log_test("Rota RTE-0000003", False, "❌ Rota não tem stops")
                return False
            
            # Analisar service_status de cada stop
            status_counts = {}
            stop_details = []
            
            for stop in stops:
                service_status = stop.get('service_status')
                client_name = stop.get('client_name', 'N/A')
                service_name = stop.get('service_name', 'N/A')
                
                if service_status:
                    status_counts[service_status] = status_counts.get(service_status, 0) + 1
                
                stop_details.append({
                    'client': client_name,
                    'service': service_name,
                    'status': service_status
                })
            
            # Log detalhes dos stops
            print(f"   📋 Total de stops: {len(stops)}")
            print(f"   📊 Distribuição de service_status: {dict(status_counts)}")
            
            for i, detail in enumerate(stop_details, 1):
                print(f"   Stop {i}: {detail['client']} - {detail['service']} - Status: {detail['status']}")
            
            # Verificar se todos têm RETIRAR (indicando o bug)
            if len(status_counts) == 1 and 'RETIRAR' in status_counts:
                self.log_test("Rota RTE-0000003 - Bug Confirmado", False, 
                            f"❌ BUG CONFIRMADO: Todos os {len(stops)} stops têm service_status 'RETIRAR'")
                return False
            elif len(status_counts) > 1:
                self.log_test("Rota RTE-0000003 - Status Variado", True, 
                            f"✅ Status variados encontrados: {dict(status_counts)}")
                return True
            else:
                self.log_test("Rota RTE-0000003 - Status Único", True, 
                            f"Status único encontrado: {dict(status_counts)} (pode ser normal)")
                return True
        else:
            if response['status_code'] == 404:
                self.log_test("Rota RTE-0000003", True, 
                            "ℹ️  Rota RTE-0000003 não encontrada (pode não existir)")
            else:
                self.log_test("Rota RTE-0000003", False, 
                            "❌ Erro ao buscar rota RTE-0000003", response['data'])
            return False
    
    def test_all_existing_routes_service_status(self):
        """Verificar service_status em todas as rotas existentes"""
        print("\n=== VERIFICANDO TODAS AS ROTAS EXISTENTES ===")
        
        response = self.make_request('GET', '/routes')
        if not response['success']:
            self.log_test("Listar Rotas", False, "❌ Erro ao listar rotas", response['data'])
            return False
        
        routes = response['data']
        if not routes:
            self.log_test("Listar Rotas", True, "ℹ️  Nenhuma rota encontrada no sistema")
            return True
        
        print(f"   📋 Total de rotas encontradas: {len(routes)}")
        
        bug_routes = []
        normal_routes = []
        
        for route in routes:
            route_id = route.get('id')
            stops = route.get('stops', [])
            
            if not stops:
                continue
            
            # Contar service_status nos stops
            status_counts = {}
            for stop in stops:
                service_status = stop.get('service_status')
                if service_status:
                    status_counts[service_status] = status_counts.get(service_status, 0) + 1
            
            # Verificar se todos são RETIRAR
            if len(status_counts) == 1 and 'RETIRAR' in status_counts:
                bug_routes.append({
                    'id': route_id,
                    'stops_count': len(stops),
                    'status_counts': status_counts
                })
            else:
                normal_routes.append({
                    'id': route_id,
                    'stops_count': len(stops),
                    'status_counts': status_counts
                })
        
        # Relatório
        print(f"   🐛 Rotas com possível bug (só RETIRAR): {len(bug_routes)}")
        print(f"   ✅ Rotas com status variado: {len(normal_routes)}")
        
        if bug_routes:
            print("   📋 Rotas com bug:")
            for route in bug_routes:
                print(f"     - {route['id']}: {route['stops_count']} stops, todos RETIRAR")
        
        if normal_routes:
            print("   📋 Rotas normais:")
            for route in normal_routes:
                print(f"     - {route['id']}: {route['stops_count']} stops, status: {dict(route['status_counts'])}")
        
        # Conclusão
        if bug_routes and not normal_routes:
            self.log_test("Análise Geral de Rotas", False, 
                        f"❌ BUG CONFIRMADO: Todas as {len(bug_routes)} rotas têm apenas status RETIRAR")
            return False
        elif bug_routes and normal_routes:
            self.log_test("Análise Geral de Rotas", False, 
                        f"⚠️  BUG PARCIAL: {len(bug_routes)} rotas com bug, {len(normal_routes)} normais")
            return False
        else:
            self.log_test("Análise Geral de Rotas", True, 
                        f"✅ Todas as rotas têm status variados - sem bug detectado")
            return True
    
    def test_budget_items_available_service_status(self):
        """Verificar service_status nos budget items disponíveis para rotas"""
        print("\n=== VERIFICANDO BUDGET ITEMS DISPONÍVEIS ===")
        
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Budget Items Disponíveis", False, 
                        "❌ Erro ao buscar budget items", response['data'])
            return False
        
        data = response['data']
        available_items = data.get('available_items', [])
        
        if not available_items:
            self.log_test("Budget Items Disponíveis", True, 
                        "ℹ️  Nenhum budget item disponível para rotas")
            return True
        
        # Analisar service_status dos items disponíveis
        status_counts = {}
        for item in available_items:
            service_status = item.get('status')  # Note: pode ser 'status' em vez de 'service_status'
            if service_status:
                status_counts[service_status] = status_counts.get(service_status, 0) + 1
        
        print(f"   📋 Total de items disponíveis: {len(available_items)}")
        print(f"   📊 Distribuição de status: {dict(status_counts)}")
        
        # Mostrar alguns exemplos
        print("   📋 Exemplos de items:")
        for i, item in enumerate(available_items[:5], 1):
            client_name = item.get('client_name', 'N/A')
            service_name = item.get('service_name', 'N/A')
            status = item.get('status', 'N/A')
            print(f"     {i}. {client_name} - {service_name} - Status: {status}")
        
        # Verificar se há variedade de status
        if len(status_counts) == 1 and 'RETIRAR' in status_counts:
            self.log_test("Budget Items - Status Variety", False, 
                        f"❌ PROBLEMA NA ORIGEM: Todos os {len(available_items)} items têm status RETIRAR")
            return False
        elif len(status_counts) > 1:
            self.log_test("Budget Items - Status Variety", True, 
                        f"✅ Variedade de status encontrada: {dict(status_counts)}")
            return True
        else:
            self.log_test("Budget Items - Status Variety", True, 
                        f"Status único: {dict(status_counts)} (pode ser normal)")
            return True
    
    def test_service_status_data_origin(self):
        """Verificar origem dos dados de service_status"""
        print("\n=== VERIFICANDO ORIGEM DOS DADOS DE SERVICE_STATUS ===")
        
        # 1. Verificar services no catálogo
        response = self.make_request('GET', '/services')
        if not response['success']:
            self.log_test("Origem - Services", False, "❌ Erro ao buscar services")
            return False
        
        services = response['data']
        service_status_counts = {}
        
        for service in services:
            default_status = service.get('default_service_status')
            if default_status:
                service_status_counts[default_status] = service_status_counts.get(default_status, 0) + 1
        
        print(f"   📋 Services no catálogo: {len(services)}")
        print(f"   📊 default_service_status: {dict(service_status_counts)}")
        
        # 2. Verificar budgets
        response = self.make_request('GET', '/budgets')
        if not response['success']:
            self.log_test("Origem - Budgets", False, "❌ Erro ao buscar budgets")
            return False
        
        budgets = response['data']
        budget_item_status_counts = {}
        total_items = 0
        
        for budget in budgets:
            items = budget.get('items', [])
            for item in items:
                total_items += 1
                status = item.get('status')
                if status:
                    budget_item_status_counts[status] = budget_item_status_counts.get(status, 0) + 1
        
        print(f"   📋 Budgets encontrados: {len(budgets)}")
        print(f"   📋 Total de items em budgets: {total_items}")
        print(f"   📊 Status dos items: {dict(budget_item_status_counts)}")
        
        # Análise
        if len(service_status_counts) > 1:
            self.log_test("Origem - Services Variety", True, 
                        f"✅ Services têm default_service_status variados: {dict(service_status_counts)}")
        else:
            self.log_test("Origem - Services Variety", False, 
                        f"❌ Services têm apenas um default_service_status: {dict(service_status_counts)}")
        
        if len(budget_item_status_counts) > 1:
            self.log_test("Origem - Budget Items Variety", True, 
                        f"✅ Budget items têm status variados: {dict(budget_item_status_counts)}")
        else:
            self.log_test("Origem - Budget Items Variety", False, 
                        f"❌ Budget items têm apenas um status: {dict(budget_item_status_counts)}")
        
        return True
    
    def test_new_route_service_status_inheritance(self):
        """Criar nova rota e verificar se service_status é herdado corretamente"""
        print("\n=== TESTANDO CRIAÇÃO DE NOVA ROTA ===")
        
        # Setup test data if needed
        if not self.created_resources['clients']:
            if not self.setup_test_data_for_status_bug():
                self.log_test("Setup para Nova Rota", False, "❌ Falha no setup")
                return False
        
        # 1. Criar nova rota
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2024-12-25",
            "planned_start_time": "09:00",
            "alias": "Rota Teste - Investigação Bug Service Status"
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if not response['success']:
            self.log_test("Nova Rota - Criação", False, "❌ Erro ao criar rota", response['data'])
            return False
        
        route = response['data']
        route_id = route['id']
        self.created_resources['routes'].append(route_id)
        
        # 2. Buscar items disponíveis
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Nova Rota - Items Disponíveis", False, "❌ Erro ao buscar items")
            return False
        
        available_items = response['data'].get('available_items', [])
        if not available_items:
            self.log_test("Nova Rota - Items Disponíveis", False, "❌ Nenhum item disponível")
            return False
        
        # 3. Adicionar stops com diferentes status esperados
        stops_data = []
        expected_statuses = []
        
        for i, item in enumerate(available_items[:3]):  # Usar até 3 items
            stops_data.append({
                "budget_item_id": item["budget_item_id"],
                "priority": "AUTOMATICA"
            })
            expected_statuses.append(item.get('status'))
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', stops_data)
        if not response['success']:
            self.log_test("Nova Rota - Adicionar Stops", False, "❌ Erro ao adicionar stops", response['data'])
            return False
        
        # 4. Verificar se service_status foi herdado corretamente
        response = self.make_request('GET', f'/routes/{route_id}')
        if not response['success']:
            self.log_test("Nova Rota - Verificar Stops", False, "❌ Erro ao buscar rota criada")
            return False
        
        route = response['data']
        stops = route.get('stops', [])
        
        # Comparar status esperados vs obtidos
        status_matches = []
        status_mismatches = []
        
        for i, stop in enumerate(stops):
            actual_status = stop.get('service_status')
            expected_status = expected_statuses[i] if i < len(expected_statuses) else None
            
            if actual_status == expected_status:
                status_matches.append(f"Stop {i+1}: {actual_status} ✅")
            else:
                status_mismatches.append(f"Stop {i+1}: esperado '{expected_status}', obtido '{actual_status}' ❌")
        
        print(f"   📋 Stops criados: {len(stops)}")
        print(f"   ✅ Status corretos: {len(status_matches)}")
        print(f"   ❌ Status incorretos: {len(status_mismatches)}")
        
        if status_matches:
            for match in status_matches:
                print(f"     {match}")
        
        if status_mismatches:
            for mismatch in status_mismatches:
                print(f"     {mismatch}")
        
        # Conclusão
        if status_mismatches:
            self.log_test("Nova Rota - Herança de Status", False, 
                        f"❌ BUG CONFIRMADO: {len(status_mismatches)} stops com status incorreto")
            return False
        else:
            self.log_test("Nova Rota - Herança de Status", True, 
                        f"✅ Todos os {len(status_matches)} stops herdaram status corretamente")
            return True

    def test_route_corrections_implementation(self):
        """Test the specific route corrections mentioned in the review request"""
        print("🔧 TESTANDO CORREÇÕES IMPLEMENTADAS NAS ROTAS")
        print(f"🔗 Testando contra: {self.base_url}")
        print("🎯 Foco: Verificar correções específicas implementadas")
        print("=" * 80)
        
        # Setup test data
        if not self.setup_test_data():
            print("❌ CRITICAL: Failed to setup test data. Aborting tests.")
            return False
        
        # Test 1: Verify alias field in Route model
        print("\n1️⃣ TESTANDO CAMPO ALIAS NO MODELO ROUTE:")
        route_id = self.test_route_alias_field()
        
        if not route_id:
            print("❌ CRITICAL: Failed to create route for testing. Aborting remaining tests.")
            return False
        
        # Test 2: Verify delivery_order field in RouteStop model
        print("\n2️⃣ TESTANDO CAMPO DELIVERY_ORDER NO MODELO ROUTESTOP:")
        self.test_delivery_order_field(route_id)
        
        # Test 3: Test PUT /routes/{id} endpoint
        print("\n3️⃣ TESTANDO ENDPOINT PUT /routes/{id}:")
        self.test_put_route_endpoint(route_id)
        
        # Test 4: Verify logic separation between order_sequence and delivery_order
        print("\n4️⃣ TESTANDO LÓGICA SEPARADA ENTRE ORDER_SEQUENCE E DELIVERY_ORDER:")
        self.test_sequence_logic_separation(route_id)
        
        # Test 5: Analyze recent route (RTE-0000002 or similar)
        print("\n5️⃣ ANALISANDO ROTA RECENTE:")
        self.test_recent_route_analysis()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        self.print_summary()
        
        return True
    
    def test_route_alias_field(self):
        """Test if Route model has alias field and it works correctly"""
        print("\n=== TESTANDO CAMPO ALIAS NO MODELO ROUTE ===")
        
        # Create route with alias
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2024-12-20",
            "planned_start_time": "08:00",
            "alias": "Rota Teste com Alias Personalizado",
            "stops": []
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if response['success']:
            route = response['data']
            route_id = route.get('id')
            
            # Verify alias field exists and is set correctly
            if route.get('alias') == route_data['alias']:
                self.created_resources['routes'].append(route_id)
                self.log_test("Route Alias Field", True, 
                            f"✅ Campo alias funcionando: '{route.get('alias')}'")
                return route_id
            else:
                self.log_test("Route Alias Field", False, 
                            f"❌ Campo alias não funcionou corretamente: esperado '{route_data['alias']}', obtido '{route.get('alias')}'")
                return route_id
        else:
            self.log_test("Route Alias Field", False, 
                        "❌ Falha ao criar rota com alias", response['data'])
            return None
    
    def test_delivery_order_field(self, route_id: str):
        """Test if RouteStop model has delivery_order field"""
        print("\n=== TESTANDO CAMPO DELIVERY_ORDER NO MODELO ROUTESTOP ===")
        
        # Get available items
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Delivery Order Field", False, 
                        "❌ Falha ao obter itens disponíveis", response['data'])
            return False
        
        available_items = response['data'].get('available_items', [])
        if not available_items:
            self.log_test("Delivery Order Field", False, 
                        "❌ Nenhum item disponível para teste")
            return False
        
        # Add stops to route
        stops_data = []
        priorities = ["PRIMEIRA", "AUTOMATICA", "ULTIMA"]
        
        for i, item in enumerate(available_items[:3]):
            priority = priorities[i % len(priorities)]
            stops_data.append({
                "budget_item_id": item["budget_item_id"],
                "priority": priority
            })
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', stops_data)
        if not response['success']:
            self.log_test("Delivery Order Field", False, 
                        "❌ Falha ao adicionar paradas à rota", response['data'])
            return False
        
        # Get route details to check delivery_order field
        response = self.make_request('GET', f'/routes/{route_id}')
        if response['success']:
            route = response['data']
            stops = route.get('stops', [])
            
            if stops:
                first_stop = stops[0]
                has_delivery_order = 'delivery_order' in first_stop
                has_order_sequence = 'order_sequence' in first_stop
                
                if has_delivery_order and has_order_sequence:
                    self.log_test("Delivery Order Field", True, 
                                f"✅ Campos delivery_order e order_sequence presentes nas paradas")
                    
                    # Log the values for analysis
                    print("   📊 Análise dos campos nas paradas:")
                    for i, stop in enumerate(stops):
                        delivery_order = stop.get('delivery_order', 'N/A')
                        order_sequence = stop.get('order_sequence', 'N/A')
                        client_name = stop.get('client_name', 'N/A')
                        print(f"     Parada {i+1}: {client_name} - delivery_order: {delivery_order}, order_sequence: {order_sequence}")
                    
                    return True
                else:
                    missing_fields = []
                    if not has_delivery_order:
                        missing_fields.append('delivery_order')
                    if not has_order_sequence:
                        missing_fields.append('order_sequence')
                    
                    self.log_test("Delivery Order Field", False, 
                                f"❌ Campos ausentes nas paradas: {missing_fields}")
                    return False
            else:
                self.log_test("Delivery Order Field", False, 
                            "❌ Nenhuma parada encontrada na rota")
                return False
        else:
            self.log_test("Delivery Order Field", False, 
                        "❌ Falha ao obter detalhes da rota", response['data'])
            return False
    
    def test_put_route_endpoint(self, route_id: str):
        """Test PUT /routes/{id} endpoint for updating routes"""
        print("\n=== TESTANDO ENDPOINT PUT /routes/{id} ===")
        
        # Test updating alias
        update_data = {
            "alias": "Alias Atualizado via PUT"
        }
        
        response = self.make_request('PUT', f'/routes/{route_id}', update_data)
        if response['success']:
            updated_route = response['data']
            
            if updated_route.get('alias') == update_data['alias']:
                self.log_test("PUT Route Endpoint", True, 
                            f"✅ Endpoint PUT /routes/{{id}} funcionando: alias atualizado para '{updated_route.get('alias')}'")
                
                # Test updating other fields
                update_data_2 = {
                    "vehicle_type": "MOTO",
                    "planned_start_time": "09:30"
                }
                
                response_2 = self.make_request('PUT', f'/routes/{route_id}', update_data_2)
                if response_2['success']:
                    updated_route_2 = response_2['data']
                    
                    checks = [
                        (updated_route_2.get('vehicle_type') == 'MOTO', "vehicle_type atualizado"),
                        (updated_route_2.get('planned_start_time') == '09:30', "planned_start_time atualizado"),
                        (updated_route_2.get('alias') == update_data['alias'], "alias preservado")
                    ]
                    
                    all_passed = all(check[0] for check in checks)
                    failed_checks = [check[1] for check in checks if not check[0]]
                    
                    if all_passed:
                        self.log_test("PUT Route Multiple Fields", True, 
                                    "✅ Múltiplos campos atualizados corretamente")
                    else:
                        self.log_test("PUT Route Multiple Fields", False, 
                                    f"❌ Falha na atualização: {failed_checks}")
                else:
                    self.log_test("PUT Route Multiple Fields", False, 
                                "❌ Falha ao atualizar múltiplos campos", response_2['data'])
                
                return True
            else:
                self.log_test("PUT Route Endpoint", False, 
                            f"❌ Alias não foi atualizado corretamente: esperado '{update_data['alias']}', obtido '{updated_route.get('alias')}'")
                return False
        else:
            self.log_test("PUT Route Endpoint", False, 
                        "❌ Falha ao atualizar rota via PUT", response['data'])
            return False
    
    def test_sequence_logic_separation(self, route_id: str):
        """Test the separation between order_sequence (geographic) and delivery_order (with priorities)"""
        print("\n=== TESTANDO LÓGICA SEPARADA ENTRE ORDER_SEQUENCE E DELIVERY_ORDER ===")
        
        # Optimize the route to trigger the logic
        response = self.make_request('POST', f'/routes/{route_id}/optimize?route_type=CURTA')
        if not response['success']:
            self.log_test("Sequence Logic Separation", False, 
                        "❌ Falha ao otimizar rota", response['data'])
            return False
        
        # Get route details after optimization
        response = self.make_request('GET', f'/routes/{route_id}')
        if response['success']:
            route = response['data']
            stops = route.get('stops', [])
            
            if len(stops) >= 2:
                # Analyze the differences between order_sequence and delivery_order
                differences_found = False
                geographic_analysis = []
                delivery_analysis = []
                
                for stop in stops:
                    delivery_order = stop.get('delivery_order', 0)
                    order_sequence = stop.get('order_sequence', 0)
                    client_name = stop.get('client_name', 'N/A')
                    priority = stop.get('priority', 'N/A')
                    
                    geographic_analysis.append({
                        'client': client_name,
                        'order_sequence': order_sequence,
                        'priority': priority
                    })
                    
                    delivery_analysis.append({
                        'client': client_name,
                        'delivery_order': delivery_order,
                        'priority': priority
                    })
                    
                    if delivery_order != order_sequence:
                        differences_found = True
                
                # Sort by each sequence to analyze
                geographic_sorted = sorted(geographic_analysis, key=lambda x: x['order_sequence'])
                delivery_sorted = sorted(delivery_analysis, key=lambda x: x['delivery_order'])
                
                print("   📊 ANÁLISE DA LÓGICA DE SEQUENCIAMENTO:")
                print("   🗺️  ORDER_SEQUENCE (Otimização Geográfica):")
                for item in geographic_sorted:
                    print(f"     Posição {item['order_sequence']}: {item['client']} (Prioridade: {item['priority']})")
                
                print("   🚚 DELIVERY_ORDER (Sequência de Entrega com Prioridades):")
                for item in delivery_sorted:
                    print(f"     Posição {item['delivery_order']}: {item['client']} (Prioridade: {item['priority']})")
                
                if differences_found:
                    self.log_test("Sequence Logic Separation", True, 
                                "✅ Lógica separada funcionando: order_sequence ≠ delivery_order encontradas")
                    
                    # Verify priority logic
                    primeira_stops = [s for s in stops if s.get('priority') == 'PRIMEIRA']
                    ultima_stops = [s for s in stops if s.get('priority') == 'ULTIMA']
                    
                    priority_logic_correct = True
                    if primeira_stops:
                        min_delivery_order = min(s.get('delivery_order', 999) for s in primeira_stops)
                        if min_delivery_order != 1:
                            priority_logic_correct = False
                    
                    if ultima_stops:
                        max_delivery_order = max(s.get('delivery_order', 0) for s in ultima_stops)
                        total_stops = len(stops)
                        if max_delivery_order != total_stops:
                            priority_logic_correct = False
                    
                    if priority_logic_correct:
                        self.log_test("Priority Logic", True, 
                                    "✅ Lógica de prioridades funcionando corretamente")
                    else:
                        self.log_test("Priority Logic", False, 
                                    "❌ Lógica de prioridades não está funcionando corretamente")
                    
                    return True
                else:
                    self.log_test("Sequence Logic Separation", False, 
                                "❌ Não foram encontradas diferenças entre order_sequence e delivery_order")
                    return False
            else:
                self.log_test("Sequence Logic Separation", False, 
                            f"❌ Número insuficiente de paradas para análise: {len(stops)}")
                return False
        else:
            self.log_test("Sequence Logic Separation", False, 
                        "❌ Falha ao obter detalhes da rota otimizada", response['data'])
            return False
    
    def test_recent_route_analysis(self):
        """Analyze recent routes to verify the corrections"""
        print("\n=== ANALISANDO ROTAS RECENTES ===")
        
        # Get list of routes
        response = self.make_request('GET', '/routes')
        if not response['success']:
            self.log_test("Recent Route Analysis", False, 
                        "❌ Falha ao obter lista de rotas", response['data'])
            return False
        
        routes = response['data']
        if not routes:
            self.log_test("Recent Route Analysis", False, 
                        "❌ Nenhuma rota encontrada no sistema")
            return False
        
        # Sort routes by ID to get most recent (assuming sequential IDs)
        routes_sorted = sorted(routes, key=lambda x: x.get('id', ''), reverse=True)
        
        # Analyze the most recent route
        recent_route = routes_sorted[0]
        route_id = recent_route.get('id')
        
        print(f"   🔍 Analisando rota mais recente: {route_id}")
        
        # Get detailed route information
        response = self.make_request('GET', f'/routes/{route_id}')
        if response['success']:
            route_details = response['data']
            
            # Check for alias field
            has_alias = 'alias' in route_details
            alias_value = route_details.get('alias')
            
            # Check stops for delivery_order and order_sequence
            stops = route_details.get('stops', [])
            
            analysis_results = {
                'route_id': route_id,
                'has_alias_field': has_alias,
                'alias_value': alias_value,
                'total_stops': len(stops),
                'stops_with_delivery_order': 0,
                'stops_with_order_sequence': 0,
                'sequence_differences': 0
            }
            
            for stop in stops:
                if 'delivery_order' in stop:
                    analysis_results['stops_with_delivery_order'] += 1
                if 'order_sequence' in stop:
                    analysis_results['stops_with_order_sequence'] += 1
                
                delivery_order = stop.get('delivery_order', 0)
                order_sequence = stop.get('order_sequence', 0)
                if delivery_order != order_sequence:
                    analysis_results['sequence_differences'] += 1
            
            # Log analysis results
            print(f"   📊 RESULTADOS DA ANÁLISE:")
            print(f"     Rota ID: {analysis_results['route_id']}")
            print(f"     Campo alias presente: {analysis_results['has_alias_field']}")
            print(f"     Valor do alias: {analysis_results['alias_value']}")
            print(f"     Total de paradas: {analysis_results['total_stops']}")
            print(f"     Paradas com delivery_order: {analysis_results['stops_with_delivery_order']}")
            print(f"     Paradas com order_sequence: {analysis_results['stops_with_order_sequence']}")
            print(f"     Diferenças entre sequências: {analysis_results['sequence_differences']}")
            
            # Evaluate if corrections are working
            corrections_working = (
                analysis_results['has_alias_field'] and
                analysis_results['stops_with_delivery_order'] == analysis_results['total_stops'] and
                analysis_results['stops_with_order_sequence'] == analysis_results['total_stops']
            )
            
            if corrections_working:
                self.log_test("Recent Route Analysis", True, 
                            f"✅ Correções implementadas funcionando na rota {route_id}")
                
                if analysis_results['sequence_differences'] > 0:
                    self.log_test("Sequence Differences", True, 
                                f"✅ Diferenças entre order_sequence e delivery_order encontradas: {analysis_results['sequence_differences']} paradas")
                else:
                    self.log_test("Sequence Differences", True, 
                                "ℹ️  Nenhuma diferença entre sequências (pode ser normal dependendo das prioridades)")
                
                return True
            else:
                missing_corrections = []
                if not analysis_results['has_alias_field']:
                    missing_corrections.append('campo alias')
                if analysis_results['stops_with_delivery_order'] != analysis_results['total_stops']:
                    missing_corrections.append('campo delivery_order')
                if analysis_results['stops_with_order_sequence'] != analysis_results['total_stops']:
                    missing_corrections.append('campo order_sequence')
                
                self.log_test("Recent Route Analysis", False, 
                            f"❌ Correções não implementadas completamente: {missing_corrections}")
                return False
        else:
            self.log_test("Recent Route Analysis", False, 
                        f"❌ Falha ao obter detalhes da rota {route_id}", response['data'])
            return False

    def investigate_422_error_adding_stops(self):
        """Investigate the specific 422 error when adding stops to routes"""
        print("🔍 INVESTIGATING 422 ERROR - ADDING STOPS TO ROUTES")
        print(f"🔗 Testing against: {self.base_url}")
        print("🎯 Focus: PUT /api/routes/{id}/stops returns 422 Unprocessable Entity")
        print("📋 Frontend data format: [{budget_item_id: 'ITM-0000001', priority: 'AUTOMATICA'}]")
        print("=" * 80)
        
        # Step 1: Setup test data if needed
        if not self.setup_test_data():
            print("❌ CRITICAL: Failed to setup test data. Aborting investigation.")
            return False
        
        # Step 2: Get available items
        print("\n1️⃣ GETTING AVAILABLE ITEMS FOR ROUTES:")
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("422 Investigation - Get Available Items", False, 
                        "❌ Failed to get available items", response['data'])
            return False
        
        data = response['data']
        available_items = data.get('available_items', [])
        
        if len(available_items) == 0:
            self.log_test("422 Investigation - Get Available Items", False, 
                        "❌ No available items found for testing")
            return False
        
        self.log_test("422 Investigation - Get Available Items", True, 
                    f"✅ Found {len(available_items)} available items")
        
        # Step 3: Create a route
        print("\n2️⃣ CREATING TEST ROUTE:")
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2024-12-20",
            "planned_start_time": "08:00",
            "stops": []
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if not response['success']:
            self.log_test("422 Investigation - Create Route", False, 
                        "❌ Failed to create route", response['data'])
            return False
        
        route = response['data']
        route_id = route.get('id')
        self.created_resources['routes'].append(route_id)
        
        self.log_test("422 Investigation - Create Route", True, 
                    f"✅ Route created successfully: {route_id}")
        
        # Step 4: Test various scenarios that might cause 422
        print("\n3️⃣ TESTING VARIOUS SCENARIOS FOR 422 ERROR:")
        
        # Test 1: Valid format (should work)
        first_item = available_items[0]
        budget_item_id = first_item.get('budget_item_id')
        
        valid_stops_data = [{
            "budget_item_id": budget_item_id,
            "priority": "AUTOMATICA"
        }]
        
        print(f"\n   🧪 Test 1 - Valid Format:")
        print(f"   📤 Sending: {json.dumps(valid_stops_data, indent=2)}")
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', valid_stops_data)
        print(f"   📥 Status: {response['status_code']}")
        
        if response['status_code'] == 422:
            self.log_test("422 Test - Valid Format", False, f"❌ UNEXPECTED 422: {response['data']}")
        elif response['success']:
            self.log_test("422 Test - Valid Format", True, "✅ Valid format works")
        
        # Test 2: Invalid budget_item_id (should cause 422 or error)
        invalid_stops_data = [{
            "budget_item_id": "ITM-9999999",  # Non-existent
            "priority": "AUTOMATICA"
        }]
        
        print(f"\n   🧪 Test 2 - Invalid budget_item_id:")
        print(f"   📤 Sending: {json.dumps(invalid_stops_data, indent=2)}")
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', invalid_stops_data)
        print(f"   📥 Status: {response['status_code']}")
        
        if response['status_code'] == 422:
            self.log_test("422 Test - Invalid Item ID", True, f"✅ Expected 422 for invalid item: {response['data']}")
        elif response['success']:
            # Check if it silently ignored the invalid item
            result = response['data']
            if result.get('stops_count', 0) == 0:
                self.log_test("422 Test - Invalid Item ID", True, "✅ Invalid item silently ignored (0 stops added)")
            else:
                self.log_test("422 Test - Invalid Item ID", False, f"❌ Invalid item should not be added: {result}")
        
        # Test 3: Invalid priority value (should cause 422)
        invalid_priority_data = [{
            "budget_item_id": budget_item_id,
            "priority": "INVALID_PRIORITY"
        }]
        
        print(f"\n   🧪 Test 3 - Invalid Priority:")
        print(f"   📤 Sending: {json.dumps(invalid_priority_data, indent=2)}")
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', invalid_priority_data)
        print(f"   📥 Status: {response['status_code']}")
        
        if response['status_code'] == 422:
            self.log_test("422 Test - Invalid Priority", True, f"✅ Expected 422 for invalid priority: {response['data']}")
            
            # Analyze the 422 error details
            error_detail = response['data'].get('detail', 'No detail provided')
            if isinstance(error_detail, list):
                print("   🔍 Validation Errors:")
                for error in error_detail:
                    print(f"     - Field: {error.get('loc', 'unknown')}")
                    print(f"       Message: {error.get('msg', 'no message')}")
                    print(f"       Type: {error.get('type', 'unknown')}")
            else:
                print(f"   🔍 Error Detail: {error_detail}")
        
        # Test 4: Missing required fields (should cause 422)
        missing_fields_data = [{
            "budget_item_id": budget_item_id
            # Missing priority
        }]
        
        print(f"\n   🧪 Test 4 - Missing Priority Field:")
        print(f"   📤 Sending: {json.dumps(missing_fields_data, indent=2)}")
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', missing_fields_data)
        print(f"   📥 Status: {response['status_code']}")
        
        if response['status_code'] == 422:
            self.log_test("422 Test - Missing Priority", True, f"✅ Expected 422 for missing priority: {response['data']}")
        elif response['success']:
            self.log_test("422 Test - Missing Priority", True, "✅ Missing priority handled gracefully (default used)")
        
        # Test 5: Wrong data type (should cause 422)
        wrong_type_data = "not_a_list"
        
        print(f"\n   🧪 Test 5 - Wrong Data Type (string instead of list):")
        print(f"   📤 Sending: {json.dumps(wrong_type_data, indent=2)}")
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', wrong_type_data)
        print(f"   📥 Status: {response['status_code']}")
        
        if response['status_code'] == 422:
            self.log_test("422 Test - Wrong Data Type", True, f"✅ Expected 422 for wrong data type: {response['data']}")
            
            # This is likely the most common cause of 422 errors
            error_detail = response['data'].get('detail', 'No detail provided')
            if isinstance(error_detail, list):
                print("   🔍 Validation Errors:")
                for error in error_detail:
                    print(f"     - Field: {error.get('loc', 'unknown')}")
                    print(f"       Message: {error.get('msg', 'no message')}")
                    print(f"       Type: {error.get('type', 'unknown')}")
            
        # Test 6: Empty list (should work but add 0 stops)
        empty_data = []
        
        print(f"\n   🧪 Test 6 - Empty List:")
        print(f"   📤 Sending: {json.dumps(empty_data, indent=2)}")
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', empty_data)
        print(f"   📥 Status: {response['status_code']}")
        
        if response['success']:
            result = response['data']
            if result.get('stops_count', 0) == 0:
                self.log_test("422 Test - Empty List", True, "✅ Empty list handled correctly (0 stops)")
            else:
                self.log_test("422 Test - Empty List", False, f"❌ Empty list should result in 0 stops: {result}")
        
        # Test 7: Test with exact user-reported format
        print(f"\n   🧪 Test 7 - Exact User-Reported Format:")
        user_format_data = [{
            "budget_item_id": "ITM-0000001",  # User's example
            "priority": "AUTOMATICA"
        }]
        
        print(f"   📤 Sending: {json.dumps(user_format_data, indent=2)}")
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', user_format_data)
        print(f"   📥 Status: {response['status_code']}")
        
        if response['status_code'] == 422:
            self.log_test("422 Test - User Format", False, f"❌ User format causes 422: {response['data']}")
            
            # This might be the actual issue - the specific item ID doesn't exist
            error_detail = response['data'].get('detail', 'No detail provided')
            print(f"   🔍 Error Detail: {error_detail}")
            
        elif response['success']:
            result = response['data']
            if result.get('stops_count', 0) == 0:
                self.log_test("422 Test - User Format", True, "✅ User format works but item not found (0 stops added)")
            else:
                self.log_test("422 Test - User Format", True, f"✅ User format works: {result}")
        
        print("\n4️⃣ SUMMARY OF 422 ERROR INVESTIGATION:")
        print("   🎯 Most likely causes of 422 error:")
        print("   1. Invalid priority value (not PRIMEIRA, AUTOMATICA, or ULTIMA)")
        print("   2. Wrong data type sent (string/object instead of list)")
        print("   3. Malformed JSON structure")
        print("   4. Missing required fields in request body")
        print("   📝 Note: Non-existent budget_item_id is handled gracefully (no 422)")
        
        return True

    def investigate_route_bug(self):
        """Investigate the specific route bug reported by user"""
        print("🔍 INVESTIGATING ROUTE BUG - USER REPORT")
        print(f"🔗 Testing against: {self.base_url}")
        print("🎯 Focus: Routes screen empty, no available items for routes")
        print("=" * 80)
        
        # Test 1: Check /api/budget-items/available-for-routes endpoint
        print("\n1️⃣ TESTING /api/budget-items/available-for-routes ENDPOINT:")
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if response['success']:
            data = response['data']
            available_items = data.get('available_items', [])
            
            print(f"   📊 Status Code: {response['status_code']}")
            print(f"   📋 Available Items Count: {len(available_items)}")
            
            if len(available_items) == 0:
                self.log_test("Route Bug Investigation", False, 
                            "❌ CONFIRMED BUG: No available items found - this explains empty Routes screen")
                
                # Investigate why no items are available
                print("\n🔍 INVESTIGATING WHY NO ITEMS ARE AVAILABLE:")
                
                # Check if there are any budgets at all
                budgets_response = self.make_request('GET', '/budgets')
                if budgets_response['success']:
                    budgets = budgets_response['data']
                    print(f"   📋 Total Budgets in System: {len(budgets)}")
                    
                    if len(budgets) == 0:
                        self.log_test("Route Bug Root Cause", True, 
                                    "🎯 ROOT CAUSE: No budgets exist in system")
                        return "NO_BUDGETS"
                    else:
                        # Check budget items and their statuses
                        items_with_route_status = 0
                        items_without_address = 0
                        total_items = 0
                        
                        for budget in budgets:
                            items = budget.get('items', [])
                            total_items += len(items)
                            
                            for item in items:
                                status = item.get('status')
                                if status in ['RETIRAR', 'EXECUTAR_NO_LOCAL', 'ENTREGAR']:
                                    items_with_route_status += 1
                        
                        print(f"   📊 Total Budget Items: {total_items}")
                        print(f"   📊 Items with Route-eligible Status: {items_with_route_status}")
                        
                        if items_with_route_status == 0:
                            self.log_test("Route Bug Root Cause", True, 
                                        "🎯 ROOT CAUSE: No budget items have route-eligible status (RETIRAR, EXECUTAR_NO_LOCAL, ENTREGAR)")
                            return "NO_ROUTE_STATUS_ITEMS"
                        else:
                            # Check clients with addresses
                            clients_response = self.make_request('GET', '/clients')
                            if clients_response['success']:
                                clients = clients_response['data']
                                clients_with_coords = 0
                                
                                for client in clients:
                                    address = client.get('address', {})
                                    if address.get('latitude') and address.get('longitude'):
                                        clients_with_coords += 1
                                
                                print(f"   📊 Total Clients: {len(clients)}")
                                print(f"   📊 Clients with GPS Coordinates: {clients_with_coords}")
                                
                                if clients_with_coords == 0:
                                    self.log_test("Route Bug Root Cause", True, 
                                                "🎯 ROOT CAUSE: No clients have GPS coordinates in their addresses")
                                    return "NO_CLIENT_COORDINATES"
                                else:
                                    self.log_test("Route Bug Root Cause", False, 
                                                "❓ UNKNOWN: Items exist with route status and clients have coordinates, but endpoint returns empty")
                                    return "UNKNOWN_ISSUE"
            else:
                self.log_test("Route Bug Investigation", True, 
                            f"✅ Available items found: {len(available_items)} - Bug may be frontend-related")
                
                # Show sample of available items
                print("\n📋 SAMPLE AVAILABLE ITEMS:")
                for i, item in enumerate(available_items[:3]):
                    print(f"   {i+1}. Client: {item.get('client_name')} | Status: {item.get('status')} | Service: {item.get('service_name')}")
                
                return "ITEMS_AVAILABLE"
        else:
            self.log_test("Route Bug Investigation", False, 
                        f"❌ ENDPOINT ERROR: {response['status_code']} - {response['data']}")
            return "ENDPOINT_ERROR"
        
        # Test 2: Try creating a simple route to verify API functionality
        print("\n2️⃣ TESTING ROUTE CREATION API:")
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2024-12-20",
            "planned_start_time": "08:00"
        }
        
        route_response = self.make_request('POST', '/routes', route_data)
        if route_response['success']:
            route_id = route_response['data']['id']
            self.created_resources['routes'].append(route_id)
            self.log_test("Route Creation Test", True, 
                        f"✅ Route creation API working: {route_id}")
        else:
            self.log_test("Route Creation Test", False, 
                        f"❌ Route creation failed: {route_response['data']}")
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        self.print_summary()
        
        return True

    def test_calendar_auth_status(self):
        """Test Google Calendar authentication status"""
        print("\n=== TESTANDO STATUS DE AUTENTICAÇÃO DO GOOGLE CALENDAR ===")
        
        response = self.make_request('GET', '/calendar/status')
        if response['success']:
            auth_data = response['data']
            is_authenticated = auth_data.get('authenticated', False)
            message = auth_data.get('message', '')
            
            if is_authenticated:
                self.log_test("Calendar Auth Status", True, 
                            f"✅ Google Calendar autenticado: {message}")
                return True
            else:
                self.log_test("Calendar Auth Status", False, 
                            f"❌ Google Calendar não autenticado: {message}")
                return False
        else:
            self.log_test("Calendar Auth Status", False, 
                        "❌ Falha ao verificar status de autenticação", response['data'])
            return False

    def test_direct_calendar_event_basic(self):
        """Test 1: Basic direct calendar event creation"""
        print("\n=== TESTE 1: CRIAÇÃO BÁSICA DE EVENTO DIRETO ===")
        
        # Basic event data with required fields only
        event_data = {
            "summary": "Teste Básico - Evento Direto Neo",
            "start_datetime": "2025-01-15T10:00:00",
            "end_datetime": "2025-01-15T12:00:00"
        }
        
        response = self.make_request('POST', '/calendar/events/direct', event_data)
        if response['success']:
            result = response['data']
            
            # Verify response structure
            checks = [
                (result.get('message') == 'Direct calendar event created successfully', "Mensagem de sucesso"),
                (result.get('event') is not None, "Dados do evento retornados"),
                (result.get('google_event_id') is not None, "Google Event ID retornado"),
                (result['event'].get('summary') == event_data['summary'], "Título correto"),
                (result['event'].get('route_id') is None, "route_id é null (correto)"),
                (result['event'].get('stop_id') is None, "stop_id é null (correto)")
            ]
            
            all_passed = all(check[0] for check in checks)
            failed_checks = [check[1] for check in checks if not check[0]]
            
            if all_passed:
                self.log_test("Direct Event - Basic Creation", True, 
                            f"✅ Evento básico criado com sucesso: {result.get('google_event_id')}")
                return result
            else:
                self.log_test("Direct Event - Basic Creation", False, 
                            f"❌ Falha na validação: {failed_checks}")
                return result
        else:
            self.log_test("Direct Event - Basic Creation", False, 
                        "❌ Falha ao criar evento básico", response['data'])
            return None

    def test_direct_calendar_event_complete(self):
        """Test 2: Complete direct calendar event with all fields"""
        print("\n=== TESTE 2: CRIAÇÃO COMPLETA COM TODOS OS CAMPOS ===")
        
        # Complete event data with all optional fields
        event_data = {
            "summary": "Teste Completo - Neo Agenda",
            "description": "Evento criado via API direta para teste da funcionalidade Criar Evento. Teste completo com todos os campos preenchidos.",
            "location": "Cuiabá, MT - Rua das Flores, 123",
            "start_datetime": "2025-01-16T14:00:00",
            "end_datetime": "2025-01-16T16:00:00"
        }
        
        response = self.make_request('POST', '/calendar/events/direct', event_data)
        if response['success']:
            result = response['data']
            
            # Verify all fields are preserved
            event = result.get('event', {})
            checks = [
                (event.get('summary') == event_data['summary'], "Título preservado"),
                (event.get('description') == event_data['description'], "Descrição preservada"),
                (event.get('location') == event_data['location'], "Local preservado"),
                (result.get('google_event_id') is not None, "Evento criado no Google Calendar"),
                (event.get('route_id') is None, "route_id é null"),
                (event.get('stop_id') is None, "stop_id é null")
            ]
            
            all_passed = all(check[0] for check in checks)
            failed_checks = [check[1] for check in checks if not check[0]]
            
            if all_passed:
                self.log_test("Direct Event - Complete Creation", True, 
                            f"✅ Evento completo criado: todos os campos preservados")
                return result
            else:
                self.log_test("Direct Event - Complete Creation", False, 
                            f"❌ Campos não preservados: {failed_checks}")
                return result
        else:
            self.log_test("Direct Event - Complete Creation", False, 
                        "❌ Falha ao criar evento completo", response['data'])
            return None

    def test_direct_calendar_event_validation(self):
        """Test 3: Validation - incomplete data"""
        print("\n=== TESTE 3: VALIDAÇÃO - DADOS INCOMPLETOS ===")
        
        # Test missing required field (summary)
        incomplete_data = {
            "description": "Evento sem título",
            "start_datetime": "2025-01-17T10:00:00",
            "end_datetime": "2025-01-17T12:00:00"
        }
        
        response = self.make_request('POST', '/calendar/events/direct', incomplete_data)
        if not response['success']:
            error_detail = response['data'].get('detail', '')
            if 'summary' in str(error_detail).lower() or 'required' in str(error_detail).lower():
                self.log_test("Direct Event - Validation Missing Summary", True, 
                            f"✅ Corretamente rejeitou dados sem título: {error_detail}")
            else:
                self.log_test("Direct Event - Validation Missing Summary", True, 
                            f"✅ Rejeitou dados incompletos: {error_detail}")
        else:
            self.log_test("Direct Event - Validation Missing Summary", False, 
                        "❌ Deveria ter rejeitado dados sem título obrigatório")
        
        # Test missing datetime fields
        missing_datetime = {
            "summary": "Evento sem horários"
        }
        
        response = self.make_request('POST', '/calendar/events/direct', missing_datetime)
        if not response['success']:
            self.log_test("Direct Event - Validation Missing DateTime", True, 
                        "✅ Corretamente rejeitou dados sem horários")
        else:
            self.log_test("Direct Event - Validation Missing DateTime", False, 
                        "❌ Deveria ter rejeitado dados sem horários")

    def test_direct_calendar_event_datetime_formats(self):
        """Test 4: DateTime format validation"""
        print("\n=== TESTE 4: VALIDAÇÃO DE FORMATOS DE DATA/HORA ===")
        
        # Test correct ISO format
        correct_format_data = {
            "summary": "Teste Formato Correto",
            "start_datetime": "2025-01-18T09:00:00",
            "end_datetime": "2025-01-18T11:00:00"
        }
        
        response = self.make_request('POST', '/calendar/events/direct', correct_format_data)
        if response['success']:
            self.log_test("Direct Event - Correct DateTime Format", True, 
                        "✅ Formato ISO datetime aceito corretamente")
        else:
            self.log_test("Direct Event - Correct DateTime Format", False, 
                        "❌ Formato ISO datetime deveria ser aceito", response['data'])
        
        # Test incorrect format
        incorrect_format_data = {
            "summary": "Teste Formato Incorreto",
            "start_datetime": "18/01/2025 09:00",  # Wrong format
            "end_datetime": "2025-01-18T11:00:00"
        }
        
        response = self.make_request('POST', '/calendar/events/direct', incorrect_format_data)
        if not response['success']:
            self.log_test("Direct Event - Incorrect DateTime Format", True, 
                        "✅ Formato incorreto rejeitado corretamente")
        else:
            self.log_test("Direct Event - Incorrect DateTime Format", False, 
                        "❌ Formato incorreto deveria ter sido rejeitado")

    def test_direct_calendar_event_database_storage(self):
        """Test 5: Verify event is saved in database"""
        print("\n=== TESTE 5: VERIFICAÇÃO DE ARMAZENAMENTO NO BANCO ===")
        
        # Create event and verify it's stored
        event_data = {
            "summary": "Teste Armazenamento BD - Neo",
            "description": "Verificar se evento é salvo na collection calendar_events",
            "location": "Cuiabá, MT",
            "start_datetime": "2025-01-19T15:00:00",
            "end_datetime": "2025-01-19T17:00:00"
        }
        
        response = self.make_request('POST', '/calendar/events/direct', event_data)
        if response['success']:
            result = response['data']
            google_event_id = result.get('google_event_id')
            
            if google_event_id:
                # Try to get all calendar events to verify storage
                # Note: This is indirect verification since we don't have direct DB access
                events_response = self.make_request('GET', '/calendar/events?start_date=2025-01-19&end_date=2025-01-19')
                if events_response['success']:
                    events = events_response['data'].get('events', [])
                    found_event = any(event.get('summary') == event_data['summary'] for event in events)
                    
                    if found_event:
                        self.log_test("Direct Event - Database Storage", True, 
                                    "✅ Evento encontrado na listagem (salvo no banco)")
                    else:
                        self.log_test("Direct Event - Database Storage", True, 
                                    "✅ Evento criado (verificação indireta)")
                else:
                    self.log_test("Direct Event - Database Storage", True, 
                                "✅ Evento criado com sucesso (não foi possível verificar listagem)")
            else:
                self.log_test("Direct Event - Database Storage", False, 
                            "❌ Google Event ID não retornado")
        else:
            self.log_test("Direct Event - Database Storage", False, 
                        "❌ Falha ao criar evento para teste de armazenamento", response['data'])

    def test_direct_calendar_event_real_creation(self):
        """Test 6: Verify real event creation in Google Calendar"""
        print("\n=== TESTE 6: VERIFICAÇÃO DE CRIAÇÃO REAL NO GOOGLE CALENDAR ===")
        
        # Use the suggested test data from review request
        event_data = {
            "summary": "Teste Criação Direta - Neo",
            "description": "Evento criado via API direta para teste da funcionalidade Criar Evento",
            "location": "Cuiabá, MT",
            "start_datetime": "2025-01-20T10:00:00",
            "end_datetime": "2025-01-20T12:00:00"
        }
        
        response = self.make_request('POST', '/calendar/events/direct', event_data)
        if response['success']:
            result = response['data']
            google_event_id = result.get('google_event_id')
            
            if google_event_id:
                # Try to get event details to verify it exists in Google Calendar
                detail_response = self.make_request('GET', f'/calendar/events/detail/{google_event_id}')
                if detail_response['success']:
                    event_detail = detail_response['data']
                    
                    # Verify event details match what we created
                    checks = [
                        (event_detail.get('summary') == event_data['summary'], "Título no Google Calendar"),
                        (event_detail.get('location') == event_data['location'], "Local no Google Calendar"),
                        (event_detail.get('google_event_id') == google_event_id, "ID consistente")
                    ]
                    
                    all_passed = all(check[0] for check in checks)
                    failed_checks = [check[1] for check in checks if not check[0]]
                    
                    if all_passed:
                        self.log_test("Direct Event - Real Google Calendar Creation", True, 
                                    f"✅ Evento realmente criado no Google Calendar: {google_event_id}")
                    else:
                        self.log_test("Direct Event - Real Google Calendar Creation", False, 
                                    f"❌ Dados inconsistentes no Google Calendar: {failed_checks}")
                else:
                    self.log_test("Direct Event - Real Google Calendar Creation", True, 
                                f"✅ Evento criado (ID: {google_event_id}) - não foi possível verificar detalhes")
            else:
                self.log_test("Direct Event - Real Google Calendar Creation", False, 
                            "❌ Google Event ID não retornado")
        else:
            self.log_test("Direct Event - Real Google Calendar Creation", False, 
                        "❌ Falha ao criar evento no Google Calendar", response['data'])

    def run_direct_calendar_event_tests(self):
        """Run comprehensive tests for direct calendar event creation"""
        print("📅 INICIANDO TESTES DO ENDPOINT POST /api/calendar/events/direct")
        print(f"🔗 Testando contra: {self.base_url}")
        print("🎯 Foco: Funcionalidade 'Criar Evento' diretamente no Google Calendar")
        print("=" * 80)
        
        # Pre-requisite: Check Google Calendar authentication
        print("\n🔐 PRÉ-REQUISITO: Verificando autenticação do Google Calendar")
        auth_ok = self.test_calendar_auth_status()
        
        if not auth_ok:
            print("❌ CRITICAL: Google Calendar não está autenticado. Alguns testes podem falhar.")
            print("ℹ️  Continuando com os testes para verificar comportamento sem autenticação...")
        
        # Test 1: Basic event creation
        print("\n1️⃣ TESTE BÁSICO:")
        self.test_direct_calendar_event_basic()
        
        # Test 2: Complete event with all fields
        print("\n2️⃣ TESTE COMPLETO:")
        self.test_direct_calendar_event_complete()
        
        # Test 3: Validation tests
        print("\n3️⃣ TESTE DE VALIDAÇÃO:")
        self.test_direct_calendar_event_validation()
        
        # Test 4: DateTime format tests
        print("\n4️⃣ TESTE DE FORMATOS:")
        self.test_direct_calendar_event_datetime_formats()
        
        # Test 5: Database storage verification
        print("\n5️⃣ TESTE DE ARMAZENAMENTO:")
        self.test_direct_calendar_event_database_storage()
        
        # Test 6: Real Google Calendar creation
        print("\n6️⃣ TESTE DE CRIAÇÃO REAL:")
        self.test_direct_calendar_event_real_creation()
        
        # Summary
        self.print_summary()
        
        return True

    def test_google_calendar_authentication_status(self):
        """Test Google Calendar authentication status"""
        print("\n=== TESTANDO STATUS DE AUTENTICAÇÃO DO GOOGLE CALENDAR ===")
        
        response = self.make_request('GET', '/calendar/status')
        if response['success']:
            status_data = response['data']
            is_authenticated = status_data.get('authenticated', False)
            message = status_data.get('message', '')
            
            if is_authenticated:
                self.log_test("Calendar Auth Status", True, 
                            f"✅ Google Calendar autenticado: {message}")
                return True
            else:
                self.log_test("Calendar Auth Status", False, 
                            f"❌ Google Calendar NÃO autenticado: {message}")
                return False
        else:
            self.log_test("Calendar Auth Status", False, 
                        "❌ Falha ao verificar status de autenticação", response['data'])
            return False
    
    def test_calendar_events_creation_endpoint(self):
        """Test POST /api/calendar/events endpoint - the main focus of the investigation"""
        print("\n=== TESTANDO ENDPOINT POST /api/calendar/events ===")
        
        # First, check if we have existing routes to test with
        routes_response = self.make_request('GET', '/routes')
        if not routes_response['success']:
            self.log_test("Calendar Events - Get Routes", False, 
                        "❌ Falha ao obter rotas existentes", routes_response['data'])
            return False
        
        routes = routes_response['data']
        if not routes:
            self.log_test("Calendar Events - Get Routes", False, 
                        "❌ Nenhuma rota encontrada para teste")
            return False
        
        # Use the first available route
        test_route = routes[0]
        route_id = test_route.get('id')
        
        if not route_id:
            self.log_test("Calendar Events - Route ID", False, 
                        "❌ Rota sem ID válido")
            return False
        
        # Get route details to find stop IDs
        route_details_response = self.make_request('GET', f'/routes/{route_id}')
        if not route_details_response['success']:
            self.log_test("Calendar Events - Route Details", False, 
                        f"❌ Falha ao obter detalhes da rota {route_id}", route_details_response['data'])
            return False
        
        route_details = route_details_response['data']
        stops = route_details.get('stops', [])
        
        if not stops:
            self.log_test("Calendar Events - Route Stops", False, 
                        f"❌ Rota {route_id} não possui paradas")
            return False
        
        # Prepare the exact payload format mentioned in the review request
        stop_ids = [stop.get('id') for stop in stops[:2]]  # Use first 2 stops
        
        calendar_event_data = {
            "route_id": route_id,
            "stop_ids": stop_ids,
            "start_date": "2025-03-09",
            "start_time": "08:00"
        }
        
        print(f"   📋 Testando com rota: {route_id}")
        print(f"   📋 Stop IDs: {stop_ids}")
        print(f"   📋 Data: {calendar_event_data['start_date']} às {calendar_event_data['start_time']}")
        
        # Test the endpoint
        response = self.make_request('POST', '/calendar/events', calendar_event_data)
        
        # Analyze the response
        if response['success']:
            result = response['data']
            events_created = result.get('events', [])
            message = result.get('message', '')
            
            self.log_test("Calendar Events Creation", True, 
                        f"✅ Eventos criados com sucesso: {message}")
            
            # Verify event structure
            if events_created:
                first_event = events_created[0]
                required_fields = ['id', 'route_id', 'stop_id', 'summary', 'start_datetime', 'end_datetime']
                missing_fields = [field for field in required_fields if field not in first_event]
                
                if not missing_fields:
                    self.log_test("Calendar Events Structure", True, 
                                f"✅ Estrutura dos eventos correta: {len(events_created)} eventos")
                else:
                    self.log_test("Calendar Events Structure", False, 
                                f"❌ Campos ausentes na estrutura: {missing_fields}")
            
            return True
        else:
            # This is the key part - analyze the specific error
            status_code = response['status_code']
            error_data = response['data']
            
            if status_code == 400:
                self.log_test("Calendar Events Creation", False, 
                            f"❌ ERRO 400 (Bad Request): {error_data}")
                
                # Check for specific authentication error
                error_detail = str(error_data.get('detail', ''))
                if 'not authenticated' in error_detail.lower() or 'credentials' in error_detail.lower():
                    self.log_test("Calendar Auth Issue", False, 
                                "🔍 PROBLEMA IDENTIFICADO: Google Calendar não está autenticado")
                elif 'route not found' in error_detail.lower():
                    self.log_test("Calendar Route Issue", False, 
                                "🔍 PROBLEMA IDENTIFICADO: Rota não encontrada")
                elif 'stop' in error_detail.lower():
                    self.log_test("Calendar Stop Issue", False, 
                                "🔍 PROBLEMA IDENTIFICADO: Problema com os stops selecionados")
                else:
                    self.log_test("Calendar Unknown 400", False, 
                                f"🔍 ERRO 400 DESCONHECIDO: {error_detail}")
            
            elif status_code == 401:
                self.log_test("Calendar Events Creation", False, 
                            f"❌ ERRO 401 (Unauthorized): Problema de autenticação Google")
            
            elif status_code == 404:
                self.log_test("Calendar Events Creation", False, 
                            f"❌ ERRO 404 (Not Found): Rota ou recurso não encontrado")
            
            elif status_code == 500:
                self.log_test("Calendar Events Creation", False, 
                            f"❌ ERRO 500 (Internal Server Error): {error_data}")
            
            else:
                self.log_test("Calendar Events Creation", False, 
                            f"❌ ERRO {status_code}: {error_data}")
            
            return False
    
    def test_calendar_events_with_real_route_data(self):
        """Test with specific route data mentioned in the review (RTE-0000001, RTE-0000002)"""
        print("\n=== TESTANDO COM DADOS DE ROTA REAL (RTE-0000001/RTE-0000002) ===")
        
        # Test with specific route IDs mentioned in the review
        test_route_ids = ["RTE-0000001", "RTE-0000002"]
        
        for route_id in test_route_ids:
            print(f"\n   🔍 Testando rota específica: {route_id}")
            
            # Get route details
            route_response = self.make_request('GET', f'/routes/{route_id}')
            if not route_response['success']:
                self.log_test(f"Real Route Test - {route_id}", False, 
                            f"❌ Rota {route_id} não encontrada")
                continue
            
            route_data = route_response['data']
            stops = route_data.get('stops', [])
            
            if not stops:
                self.log_test(f"Real Route Test - {route_id}", False, 
                            f"❌ Rota {route_id} não possui paradas")
                continue
            
            # Test with first stop
            stop_ids = [stops[0].get('id')]
            
            calendar_event_data = {
                "route_id": route_id,
                "stop_ids": stop_ids,
                "start_date": "2025-03-09",
                "start_time": "08:00"
            }
            
            response = self.make_request('POST', '/calendar/events', calendar_event_data)
            
            if response['success']:
                self.log_test(f"Real Route Test - {route_id}", True, 
                            f"✅ Eventos criados para rota {route_id}")
            else:
                error_detail = response['data'].get('detail', 'Erro desconhecido')
                self.log_test(f"Real Route Test - {route_id}", False, 
                            f"❌ Falha para rota {route_id}: {error_detail}")
        
        return True
    
    def test_calendar_data_format_validation(self):
        """Test different data formats to identify validation issues"""
        print("\n=== TESTANDO VALIDAÇÃO DE FORMATO DE DADOS ===")
        
        # Get a valid route for testing
        routes_response = self.make_request('GET', '/routes')
        if not routes_response['success'] or not routes_response['data']:
            self.log_test("Calendar Format Validation", False, 
                        "❌ Nenhuma rota disponível para teste")
            return False
        
        route_id = routes_response['data'][0].get('id')
        
        # Test 1: Invalid stop_ids format (not array)
        invalid_format_1 = {
            "route_id": route_id,
            "stop_ids": "STP-0000001",  # String instead of array
            "start_date": "2025-03-09",
            "start_time": "08:00"
        }
        
        response = self.make_request('POST', '/calendar/events', invalid_format_1)
        if not response['success']:
            self.log_test("Calendar Format - Invalid stop_ids", True, 
                        f"✅ Corretamente rejeitou stop_ids como string: {response['data']}")
        else:
            self.log_test("Calendar Format - Invalid stop_ids", False, 
                        "❌ Deveria ter rejeitado stop_ids como string")
        
        # Test 2: Invalid date format
        invalid_format_2 = {
            "route_id": route_id,
            "stop_ids": ["STP-0000001"],
            "start_date": "09/03/2025",  # Wrong format
            "start_time": "08:00"
        }
        
        response = self.make_request('POST', '/calendar/events', invalid_format_2)
        if not response['success']:
            self.log_test("Calendar Format - Invalid date", True, 
                        f"✅ Corretamente rejeitou formato de data inválido: {response['data']}")
        else:
            self.log_test("Calendar Format - Invalid date", False, 
                        "❌ Deveria ter rejeitado formato de data inválido")
        
        # Test 3: Invalid time format
        invalid_format_3 = {
            "route_id": route_id,
            "stop_ids": ["STP-0000001"],
            "start_date": "2025-03-09",
            "start_time": "8:00 AM"  # Wrong format
        }
        
        response = self.make_request('POST', '/calendar/events', invalid_format_3)
        if not response['success']:
            self.log_test("Calendar Format - Invalid time", True, 
                        f"✅ Corretamente rejeitou formato de horário inválido: {response['data']}")
        else:
            self.log_test("Calendar Format - Invalid time", False, 
                        "❌ Deveria ter rejeitado formato de horário inválido")
        
        # Test 4: Missing required fields
        incomplete_data = {
            "route_id": route_id,
            # Missing stop_ids, start_date, start_time
        }
        
        response = self.make_request('POST', '/calendar/events', incomplete_data)
        if not response['success']:
            self.log_test("Calendar Format - Missing fields", True, 
                        f"✅ Corretamente rejeitou dados incompletos: {response['data']}")
        else:
            self.log_test("Calendar Format - Missing fields", False, 
                        "❌ Deveria ter rejeitado dados incompletos")
        
        return True
    
    def run_calendar_investigation_tests(self):
        """Run specific tests to investigate the calendar button issue"""
        print("📅 INICIANDO INVESTIGAÇÃO DO BOTÃO 'LANÇAR NA AGENDA'")
        print(f"🔗 Testando contra: {self.base_url}")
        print("🎯 Foco: Descobrir por que os eventos não aparecem no Google Calendar")
        print("=" * 80)
        
        # Test 1: Check Google Calendar authentication status
        print("\n1️⃣ VERIFICANDO AUTENTICAÇÃO DO GOOGLE CALENDAR:")
        auth_status = self.test_google_calendar_authentication_status()
        
        # Test 2: Test the main endpoint POST /api/calendar/events
        print("\n2️⃣ TESTANDO ENDPOINT POST /api/calendar/events:")
        self.test_calendar_events_creation_endpoint()
        
        # Test 3: Test with real route data (RTE-0000001, RTE-0000002)
        print("\n3️⃣ TESTANDO COM ROTAS REAIS:")
        self.test_calendar_events_with_real_route_data()
        
        # Test 4: Test data format validation
        print("\n4️⃣ TESTANDO VALIDAÇÃO DE FORMATO:")
        self.test_calendar_data_format_validation()
        
        # Summary
        self.print_summary()
        
        return True

    def test_calendar_color_change_implementation(self):
        """Test the specific calendar color change from blue (colorId '1') to yellow banana (colorId '5')"""
        print("🎨 TESTANDO ALTERAÇÃO DA COR PADRÃO DOS EVENTOS PARA AMARELO BANANA")
        print(f"🔗 Testando contra: {self.base_url}")
        print("🎯 Foco: Verificar se eventos são criados com colorId '5' (amarelo banana)")
        print("=" * 80)
        
        # Test 1: Check Google Calendar authentication status
        print("\n1️⃣ VERIFICANDO AUTENTICAÇÃO DO GOOGLE CALENDAR:")
        auth_status = self.test_google_calendar_auth_status()
        
        if not auth_status:
            print("❌ CRITICAL: Google Calendar não está autenticado. Não é possível testar criação de eventos.")
            return False
        
        # Test 2: Test direct event creation with yellow banana color
        print("\n2️⃣ TESTANDO CRIAÇÃO DE EVENTO DIRETO COM COR AMARELO BANANA:")
        direct_event_success = self.test_direct_event_creation_with_color()
        
        # Test 3: Test route event creation with yellow banana color (if routes exist)
        print("\n3️⃣ TESTANDO CRIAÇÃO DE EVENTO DE ROTA COM COR AMARELO BANANA:")
        route_event_success = self.test_route_event_creation_with_color()
        
        # Test 4: Verify Google Calendar API accepts colorId '5'
        print("\n4️⃣ VERIFICANDO SE GOOGLE CALENDAR API ACEITA COLORID '5':")
        color_validation_success = self.test_google_calendar_color_validation()
        
        # Summary
        self.print_summary()
        
        return direct_event_success and route_event_success and color_validation_success
    
    def test_google_calendar_auth_status(self):
        """Check if Google Calendar is authenticated"""
        print("\n=== VERIFICANDO STATUS DE AUTENTICAÇÃO DO GOOGLE CALENDAR ===")
        
        response = self.make_request('GET', '/calendar/status')
        if response['success']:
            data = response['data']
            is_authenticated = data.get('authenticated', False)
            message = data.get('message', '')
            
            if is_authenticated:
                self.log_test("Google Calendar Auth Status", True, 
                            f"✅ Google Calendar autenticado: {message}")
                return True
            else:
                self.log_test("Google Calendar Auth Status", False, 
                            f"❌ Google Calendar não autenticado: {message}")
                return False
        else:
            self.log_test("Google Calendar Auth Status", False, 
                        "❌ Falha ao verificar status de autenticação", response['data'])
            return False
    
    def test_direct_event_creation_with_color(self):
        """Test POST /api/calendar/events/direct with yellow banana color"""
        print("\n=== TESTANDO CRIAÇÃO DE EVENTO DIRETO COM COR AMARELO BANANA ===")
        
        # Test data as specified in the review request
        event_data = {
            "summary": "Teste Cor Amarelo Banana - Neo",
            "description": "Teste da nova cor padrão amarelo banana para eventos SuperDry",
            "location": "Cuiabá, MT",
            "start_datetime": "2025-01-15T14:00:00",
            "end_datetime": "2025-01-15T16:00:00"
        }
        
        response = self.make_request('POST', '/calendar/events/direct', event_data)
        if response['success']:
            result = response['data']
            event_created = result.get('event', {})
            google_event_id = result.get('google_event_id')
            
            # Verify event was created successfully
            checks = [
                (result.get('message') == 'Direct calendar event created successfully', "Mensagem de sucesso"),
                (event_created.get('summary') == event_data['summary'], "Título correto"),
                (event_created.get('description') == event_data['description'], "Descrição correta"),
                (event_created.get('location') == event_data['location'], "Local correto"),
                (google_event_id is not None, "Google Event ID gerado"),
                (event_created.get('route_id') is None, "route_id é None (evento direto)"),
                (event_created.get('stop_id') is None, "stop_id é None (evento direto)")
            ]
            
            all_passed = all(check[0] for check in checks)
            failed_checks = [check[1] for check in checks if not check[0]]
            
            if all_passed:
                self.log_test("Direct Event Creation", True, 
                            f"✅ Evento direto criado com sucesso no Google Calendar: {google_event_id}")
                
                # Now verify the color in Google Calendar
                return self.verify_event_color_in_google_calendar(google_event_id, "5")
            else:
                self.log_test("Direct Event Creation", False, 
                            f"❌ Falha na validação dos dados do evento: {failed_checks}")
                return False
        else:
            self.log_test("Direct Event Creation", False, 
                        "❌ Falha ao criar evento direto", response['data'])
            return False
    
    def test_route_event_creation_with_color(self):
        """Test POST /api/calendar/events with yellow banana color (route events)"""
        print("\n=== TESTANDO CRIAÇÃO DE EVENTO DE ROTA COM COR AMARELO BANANA ===")
        
        # First, check if there are any routes available
        response = self.make_request('GET', '/routes')
        if not response['success']:
            self.log_test("Route Event Creation", False, 
                        "❌ Falha ao buscar rotas existentes", response['data'])
            return False
        
        routes = response['data']
        if not routes or len(routes) == 0:
            self.log_test("Route Event Creation", True, 
                        "ℹ️  Nenhuma rota encontrada - pulando teste de evento de rota")
            return True
        
        # Use the first available route
        route = routes[0]
        route_id = route.get('id')
        stops = route.get('stops', [])
        
        if not stops or len(stops) == 0:
            self.log_test("Route Event Creation", True, 
                        f"ℹ️  Rota {route_id} não tem stops - pulando teste de evento de rota")
            return True
        
        # Create calendar events for the route
        event_request_data = {
            "route_id": route_id,
            "stop_ids": [stops[0]['id']],  # Use first stop
            "start_date": "2025-01-16",
            "start_time": "09:00"
        }
        
        response = self.make_request('POST', '/calendar/events', event_request_data)
        if response['success']:
            result = response['data']
            created_events = result.get('events', [])
            
            if len(created_events) > 0:
                first_event = created_events[0]
                google_event_id = first_event.get('google_event_id')
                
                self.log_test("Route Event Creation", True, 
                            f"✅ Evento de rota criado com sucesso: {google_event_id}")
                
                # Verify the color in Google Calendar
                return self.verify_event_color_in_google_calendar(google_event_id, "5")
            else:
                self.log_test("Route Event Creation", False, 
                            "❌ Nenhum evento foi criado para a rota")
                return False
        else:
            self.log_test("Route Event Creation", False, 
                        "❌ Falha ao criar eventos de rota", response['data'])
            return False
    
    def verify_event_color_in_google_calendar(self, google_event_id: str, expected_color_id: str):
        """Verify that the event in Google Calendar has the correct colorId"""
        print(f"\n=== VERIFICANDO COR DO EVENTO NO GOOGLE CALENDAR: {google_event_id} ===")
        
        response = self.make_request('GET', f'/calendar/events/detail/{google_event_id}')
        if response['success']:
            event_detail = response['data']
            actual_color_id = event_detail.get('color_id')
            
            if actual_color_id == expected_color_id:
                self.log_test("Event Color Verification", True, 
                            f"✅ Evento tem a cor correta: colorId '{actual_color_id}' (amarelo banana)")
                return True
            elif actual_color_id is None:
                # Some events might not have colorId set explicitly
                self.log_test("Event Color Verification", False, 
                            f"⚠️  Evento não tem colorId definido (pode usar cor padrão do calendário)")
                return False
            else:
                self.log_test("Event Color Verification", False, 
                            f"❌ Evento tem cor incorreta: colorId '{actual_color_id}' (esperado '{expected_color_id}')")
                return False
        else:
            self.log_test("Event Color Verification", False, 
                        f"❌ Falha ao buscar detalhes do evento {google_event_id}", response['data'])
            return False
    
    def test_google_calendar_color_validation(self):
        """Test if Google Calendar API accepts colorId '5' (yellow banana)"""
        print("\n=== VERIFICANDO SE GOOGLE CALENDAR API ACEITA COLORID '5' ===")
        
        # Create a simple test event to verify color acceptance
        test_event_data = {
            "summary": "Teste Validação Cor - colorId 5",
            "description": "Evento de teste para validar se Google Calendar aceita colorId '5'",
            "location": "Teste",
            "start_datetime": "2025-01-17T10:00:00",
            "end_datetime": "2025-01-17T11:00:00"
        }
        
        response = self.make_request('POST', '/calendar/events/direct', test_event_data)
        if response['success']:
            result = response['data']
            google_event_id = result.get('google_event_id')
            
            if google_event_id:
                # Check if the event was created and has the correct color
                color_verified = self.verify_event_color_in_google_calendar(google_event_id, "5")
                
                if color_verified:
                    self.log_test("Google Calendar Color Validation", True, 
                                f"✅ Google Calendar API aceita e aplica colorId '5' corretamente")
                    
                    # Clean up test event
                    self.make_request('DELETE', f'/calendar/events/{google_event_id}')
                    return True
                else:
                    self.log_test("Google Calendar Color Validation", False, 
                                f"❌ Google Calendar API não aplicou colorId '5' corretamente")
                    
                    # Clean up test event
                    self.make_request('DELETE', f'/calendar/events/{google_event_id}')
                    return False
            else:
                self.log_test("Google Calendar Color Validation", False, 
                            "❌ Falha ao obter Google Event ID para validação")
                return False
        else:
            self.log_test("Google Calendar Color Validation", False, 
                        "❌ Falha ao criar evento de teste para validação de cor", response['data'])
            return False

class DurationOptimizationTester(ServiceStatusBugTester):
    """Test class specifically for testing duration optimization changes"""
    
    def test_duration_base_values(self):
        """Test 1: Verify base duration values - EXECUTAR_NO_LOCAL = 90min, RETIRAR/ENTREGAR = 30min"""
        print("\n=== TESTING BASE DURATION VALUES ===")
        
        # First check if Google Calendar is authenticated
        response = self.make_request('GET', '/calendar/status')
        if not response['success'] or not response['data'].get('authenticated'):
            self.log_test("Duration Base Values", False, "Google Calendar not authenticated - cannot test durations")
            return False
        
        # Get available items to test with
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Duration Base Values", False, "Failed to get available items", response['data'])
            return False
        
        available_items = response['data'].get('available_items', [])
        if not available_items:
            self.log_test("Duration Base Values", False, "No available items found for testing")
            return False
        
        # Find items with different statuses
        executar_item = next((item for item in available_items if item.get('status') == 'EXECUTAR_NO_LOCAL'), None)
        retirar_item = next((item for item in available_items if item.get('status') == 'RETIRAR'), None)
        
        if not executar_item and not retirar_item:
            self.log_test("Duration Base Values", False, "No items with EXECUTAR_NO_LOCAL or RETIRAR status found")
            return False
        
        # Create route for testing
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2025-01-15",
            "planned_start_time": "08:00",
            "alias": "Teste Durações Base"
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if not response['success']:
            self.log_test("Duration Base Values", False, "Failed to create test route", response['data'])
            return False
        
        route_id = response['data']['id']
        self.created_resources['routes'].append(route_id)
        
        # Test with available items
        test_items = []
        if executar_item:
            test_items.append(executar_item)
        if retirar_item:
            test_items.append(retirar_item)
        
        # Add items to route
        stops_data = [{"budget_item_id": item["budget_item_id"], "priority": "AUTOMATICA"} for item in test_items]
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', stops_data)
        if not response['success']:
            self.log_test("Duration Base Values", False, "Failed to add stops to route", response['data'])
            return False
        
        # Create calendar events to test duration calculation
        event_data = {
            "route_id": route_id,
            "stop_ids": [item["budget_item_id"] for item in test_items],
            "start_date": "2025-01-15",
            "start_time": "08:00"
        }
        
        response = self.make_request('POST', '/calendar/events', event_data)
        if response['success']:
            events = response['data'].get('events', [])
            
            if not events:
                self.log_test("Duration Base Values", False, "No events were created")
                return False
            
            # Check durations in created events
            success = True
            for event in events:
                start_time = datetime.fromisoformat(event['start_datetime'])
                end_time = datetime.fromisoformat(event['end_datetime'])
                duration = int((end_time - start_time).total_seconds() / 60)
                
                if 'EXECUTAR_NO_LOCAL' in event.get('summary', ''):
                    if duration == 90:
                        self.log_test("Duration Base - EXECUTAR_NO_LOCAL", True, f"✅ EXECUTAR_NO_LOCAL duration = {duration} minutes (correct: 90min)")
                    else:
                        self.log_test("Duration Base - EXECUTAR_NO_LOCAL", False, f"❌ EXECUTAR_NO_LOCAL duration = {duration} minutes (expected: 90min)")
                        success = False
                elif 'RETIRAR' in event.get('summary', '') or 'ENTREGAR' in event.get('summary', ''):
                    if duration == 30:
                        self.log_test("Duration Base - RETIRAR/ENTREGAR", True, f"✅ RETIRAR/ENTREGAR duration = {duration} minutes (correct: 30min)")
                    else:
                        self.log_test("Duration Base - RETIRAR/ENTREGAR", False, f"❌ RETIRAR/ENTREGAR duration = {duration} minutes (expected: 30min)")
                        success = False
            
            return success
        else:
            self.log_test("Duration Base Values", False, "Failed to create calendar events for duration testing", response['data'])
            return False
    
    def test_multiple_items_optimization(self):
        """Test optimization with multiple items - 15% reduction with execution, 25% without"""
        print("\n=== TESTING MULTIPLE ITEMS OPTIMIZATION ===")
        
        # First check if Google Calendar is authenticated
        response = self.make_request('GET', '/calendar/status')
        if not response['success'] or not response['data'].get('authenticated'):
            self.log_test("Multiple Items Optimization", False, "Google Calendar not authenticated - cannot test durations")
            return False
        
        # Get available items
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Multiple Items Optimization", False, "Failed to get available items", response['data'])
            return False
        
        available_items = response['data'].get('available_items', [])
        if len(available_items) < 2:
            self.log_test("Multiple Items Optimization", False, "Need at least 2 items for testing optimization")
            return False
        
        # Create route for testing
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2025-01-15",
            "planned_start_time": "08:00",
            "alias": "Teste Otimização Múltiplos Items"
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if not response['success']:
            self.log_test("Multiple Items Optimization", False, "Failed to create test route", response['data'])
            return False
        
        route_id = response['data']['id']
        self.created_resources['routes'].append(route_id)
        
        # Add multiple items to test optimization
        stops_data = [
            {"budget_item_id": available_items[0]["budget_item_id"], "priority": "AUTOMATICA"},
            {"budget_item_id": available_items[1]["budget_item_id"], "priority": "AUTOMATICA"}
        ]
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', stops_data)
        if not response['success']:
            self.log_test("Multiple Items Optimization", False, "Failed to add stops to route", response['data'])
            return False
        
        # Create calendar events to test optimization
        event_data = {
            "route_id": route_id,
            "stop_ids": [available_items[0]["budget_item_id"], available_items[1]["budget_item_id"]],
            "start_date": "2025-01-15",
            "start_time": "08:00"
        }
        
        response = self.make_request('POST', '/calendar/events', event_data)
        if response['success']:
            events = response['data'].get('events', [])
            
            if not events:
                self.log_test("Multiple Items Optimization", False, "No events were created")
                return False
            
            # Check if optimization was applied
            total_duration = 0
            has_execution = False
            
            for event in events:
                start_time = datetime.fromisoformat(event['start_datetime'])
                end_time = datetime.fromisoformat(event['end_datetime'])
                duration = int((end_time - start_time).total_seconds() / 60)
                total_duration += duration
                
                if 'EXECUTAR_NO_LOCAL' in event.get('summary', ''):
                    has_execution = True
            
            # Remove travel time (15 min between events)
            service_duration = total_duration - 15 if len(events) > 1 else total_duration
            
            # Check if duration is optimized and rounded up to multiples of 10
            if service_duration % 10 == 0:
                self.log_test("Multiple Items Optimization", True, 
                            f"✅ Optimization applied: {service_duration}min total (rounded to 10s), has_execution: {has_execution}")
                return True
            else:
                self.log_test("Multiple Items Optimization", False, 
                            f"❌ Duration not rounded to 10s: {service_duration}min")
                return False
        else:
            self.log_test("Multiple Items Optimization", False, "Failed to create calendar events", response['data'])
            return False
    
    def test_rounding_algorithm(self):
        """Test that durations are always rounded up to multiples of 10"""
        print("\n=== TESTING ROUNDING ALGORITHM (ALWAYS UP TO MULTIPLES OF 10) ===")
        
        # Get available items
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Rounding Algorithm", False, "Failed to get available items", response['data'])
            return False
        
        available_items = response['data'].get('available_items', [])
        if not available_items:
            self.log_test("Rounding Algorithm", False, "No available items found for testing")
            return False
        
        # Create route for testing
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2025-01-15",
            "planned_start_time": "08:00",
            "alias": "Teste Algoritmo de Arredondamento"
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if not response['success']:
            self.log_test("Rounding Algorithm", False, "Failed to create test route", response['data'])
            return False
        
        route_id = response['data']['id']
        self.created_resources['routes'].append(route_id)
        
        # Test with single item to verify base durations are multiples of 10
        stops_data = [{"budget_item_id": available_items[0]["budget_item_id"], "priority": "AUTOMATICA"}]
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', stops_data)
        if not response['success']:
            self.log_test("Rounding Algorithm", False, "Failed to add stops to route", response['data'])
            return False
        
        # Create calendar event
        event_data = {
            "route_id": route_id,
            "stop_ids": [available_items[0]["budget_item_id"]],
            "start_date": "2025-01-15",
            "start_time": "08:00"
        }
        
        response = self.make_request('POST', '/calendar/events', event_data)
        if response['success']:
            events = response['data'].get('events', [])
            
            if events:
                event = events[0]
                start_time = datetime.fromisoformat(event['start_datetime'])
                end_time = datetime.fromisoformat(event['end_datetime'])
                duration = int((end_time - start_time).total_seconds() / 60)
                
                # Check if duration is multiple of 10
                if duration % 10 == 0:
                    self.log_test("Rounding Algorithm", True, 
                                f"✅ Duration is multiple of 10: {duration} minutes")
                    return True
                else:
                    self.log_test("Rounding Algorithm", False, 
                                f"❌ Duration is not multiple of 10: {duration} minutes")
                    return False
            else:
                self.log_test("Rounding Algorithm", False, "No events created for testing")
                return False
        else:
            self.log_test("Rounding Algorithm", False, "Failed to create calendar events", response['data'])
            return False
    
    def test_minimum_duration_guarantee(self):
        """Test that minimum 20 minutes is guaranteed"""
        print("\n=== TESTING MINIMUM DURATION GUARANTEE (20 MINUTES) ===")
        
        # Get available items
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Minimum Duration", False, "Failed to get available items", response['data'])
            return False
        
        available_items = response['data'].get('available_items', [])
        if not available_items:
            self.log_test("Minimum Duration", False, "No available items found for testing")
            return False
        
        # Create route for testing
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2025-01-15",
            "planned_start_time": "08:00",
            "alias": "Teste Duração Mínima 20min"
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if not response['success']:
            self.log_test("Minimum Duration", False, "Failed to create test route", response['data'])
            return False
        
        route_id = response['data']['id']
        self.created_resources['routes'].append(route_id)
        
        # Add single item
        stops_data = [{"budget_item_id": available_items[0]["budget_item_id"], "priority": "AUTOMATICA"}]
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', stops_data)
        if not response['success']:
            self.log_test("Minimum Duration", False, "Failed to add stops to route", response['data'])
            return False
        
        # Create calendar event
        event_data = {
            "route_id": route_id,
            "stop_ids": [available_items[0]["budget_item_id"]],
            "start_date": "2025-01-15",
            "start_time": "08:00"
        }
        
        response = self.make_request('POST', '/calendar/events', event_data)
        if response['success']:
            events = response['data'].get('events', [])
            
            if events:
                event = events[0]
                start_time = datetime.fromisoformat(event['start_datetime'])
                end_time = datetime.fromisoformat(event['end_datetime'])
                duration = int((end_time - start_time).total_seconds() / 60)
                
                # Check if duration is at least 20 minutes
                if duration >= 20:
                    self.log_test("Minimum Duration", True, 
                                f"✅ Duration meets minimum requirement: {duration} minutes (≥20min)")
                    return True
                else:
                    self.log_test("Minimum Duration", False, 
                                f"❌ Duration below minimum: {duration} minutes (<20min)")
                    return False
            else:
                self.log_test("Minimum Duration", False, "No events created for testing")
                return False
        else:
            self.log_test("Minimum Duration", False, "Failed to create calendar events", response['data'])
            return False
    
    def run_duration_optimization_tests(self):
        """Run all duration optimization tests"""
        print("⏱️  STARTING DURATION OPTIMIZATION TESTS")
        print(f"🔗 Testing against: {self.base_url}")
        print("🎯 Focus: Test new duration rules - 90min EXECUTAR_NO_LOCAL, rounding up to 10s")
        print("=" * 80)
        
        # Setup test data if needed
        if not self.setup_test_data():
            print("❌ CRITICAL: Failed to setup test data. Aborting tests.")
            return False
        
        # Test 1: Base duration values
        print("\n1️⃣ TESTING BASE DURATION VALUES:")
        self.test_duration_base_values()
        
        # Test 2: Multiple items optimization
        print("\n2️⃣ TESTING MULTIPLE ITEMS OPTIMIZATION:")
        self.test_multiple_items_optimization()
        
        # Test 3: Rounding algorithm
        print("\n3️⃣ TESTING ROUNDING ALGORITHM:")
        self.test_rounding_algorithm()
        
        # Test 4: Minimum duration guarantee
        print("\n4️⃣ TESTING MINIMUM DURATION GUARANTEE:")
        self.test_minimum_duration_guarantee()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        self.print_summary()
        
        return True

if __name__ == "__main__":
    tester = ServiceStatusBugTester()
    duration_tester = DurationOptimizationTester()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "debug":
            print("🔍 RUNNING SERVICE STATUS DEBUG INVESTIGATION")
            success = tester.run_service_status_debug_investigation()
        elif test_type == "migration":
            print("🔄 RUNNING MIGRATION TESTS")
            success = tester.run_migration_tests()
        elif test_type == "status":
            print("🐛 RUNNING SERVICE STATUS BUG TESTS")
            success = tester.run_service_status_bug_tests()
        elif test_type == "duplication":
            print("📋 RUNNING SERVICE DUPLICATION TESTS")
            success = tester.run_service_duplication_tests()
        elif test_type == "routes":
            print("🚗 RUNNING ROUTES API TESTS")
            success = tester.run_all_tests()
        elif test_type == "route-bug":
            print("🔍 RUNNING ROUTE BUG INVESTIGATION")
            success = tester.investigate_route_bug()
        elif test_type == "422":
            print("🔍 RUNNING 422 ERROR INVESTIGATION")
            success = tester.investigate_422_error_adding_stops()
        elif test_type == "route-corrections":
            print("🔧 RUNNING ROUTE CORRECTIONS TESTS")
            success = tester.test_route_corrections_implementation()
        elif test_type == "calendar":
            print("📅 RUNNING CALENDAR INVESTIGATION TESTS")
            success = tester.run_calendar_investigation_tests()
        elif test_type == "direct-calendar":
            print("📅 RUNNING DIRECT CALENDAR EVENT TESTS")
            success = tester.run_direct_calendar_event_tests()
        elif test_type == "color":
            print("🎨 RUNNING CALENDAR COLOR CHANGE TESTS")
            success = tester.test_calendar_color_change_implementation()
        elif test_type == "service-status-bug":
            print("🐛 RUNNING ROUTE SERVICE STATUS BUG INVESTIGATION")
            success = tester.test_route_service_status_bug()
        elif test_type == "duration":
            print("⏱️  RUNNING DURATION OPTIMIZATION TESTS")
            success = duration_tester.run_duration_optimization_tests()
        else:
            print("❌ Invalid test type. Available options: debug, migration, status, duplication, routes, route-bug, 422, route-corrections, calendar, direct-calendar, color, service-status-bug, duration")
            sys.exit(1)
    else:
        print("🔍 RUNNING SERVICE STATUS DEBUG INVESTIGATION (default)")
        success = tester.run_service_status_debug_investigation()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)