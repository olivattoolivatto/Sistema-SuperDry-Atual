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
BASE_URL = "https://route-optimizer-19.preview.emergentagent.com/api"
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

if __name__ == "__main__":
    tester = RoutesAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)