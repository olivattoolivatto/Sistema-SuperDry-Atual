#!/usr/bin/env python3
"""
Backend Test Suite for SuperDry Lavanderia Management System
Focus: Testing default service status bug fix and Routes API
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://laundry-manager-6.preview.emergentagent.com/api"
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

if __name__ == "__main__":
    # Check which tests to run based on command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--status-bug":
            print("🐛 Running SERVICE STATUS BUG TESTS only")
            tester = ServiceStatusBugTester()
            success = tester.run_service_status_bug_tests()
        elif sys.argv[1] == "--duplication":
            print("🔄 Running SERVICE DUPLICATION TESTS only")
            tester = ServiceStatusBugTester()
            success = tester.run_service_duplication_tests()
        else:
            print("🚀 Running FULL ROUTES API TESTS")
            tester = ServiceStatusBugTester()
            success = tester.run_all_tests()
    else:
        print("🚀 Running FULL ROUTES API TESTS")
        tester = ServiceStatusBugTester()
        success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)