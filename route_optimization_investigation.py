#!/usr/bin/env python3
"""
Route Optimization Investigation for SuperDry Lavanderia Management System
Focus: Investigating critical route optimization problems reported by user

PROBLEMS TO INVESTIGATE:
1. deliveryOrder vs orderSequence: Always appear with equal values but should be different
2. Route optimization logic: Route RTE-0000001 issues:
   - Cliente Nilda defined as PRIMEIRA (priority) 
   - Cliente Daiana (next to company) became 2nd position
   - Should be: Company → Nilda (1st) → Alex → ... → Daiana (last, close to company)
3. ALIAS not saving: User defines custom name but doesn't appear in saved route
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://superdry-routes.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class RouteOptimizationInvestigator:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.test_results = []
        self.created_resources = {
            'clients': [],
            'services': [],
            'budgets': [],
            'routes': []
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
    
    def investigate_route_rte_0000001(self):
        """Investigate the specific route RTE-0000001 mentioned by user"""
        print("\n=== INVESTIGATING ROUTE RTE-0000001 ===")
        
        # Try to find the specific route mentioned by user
        response = self.make_request('GET', '/routes/RTE-0000001')
        if response['success']:
            route = response['data']
            self.log_test("Find Route RTE-0000001", True, "✅ Found route RTE-0000001")
            
            # Analyze the route structure
            print(f"\n📋 ROUTE RTE-0000001 ANALYSIS:")
            print(f"   Vehicle Type: {route.get('vehicle_type')}")
            print(f"   Planned Date: {route.get('planned_date')}")
            print(f"   Status: {route.get('status')}")
            print(f"   Total Stops: {len(route.get('stops', []))}")
            
            # Analyze stops and their sequence
            stops = route.get('stops', [])
            if stops:
                print(f"\n🛑 STOPS ANALYSIS:")
                for i, stop in enumerate(stops):
                    client_name = stop.get('client_name', 'N/A')
                    priority = stop.get('priority', 'N/A')
                    order_sequence = stop.get('order_sequence', 'N/A')
                    delivery_order = stop.get('delivery_order', 'N/A')  # Check if this field exists
                    
                    print(f"   Stop {i+1}: {client_name}")
                    print(f"     Priority: {priority}")
                    print(f"     Order Sequence: {order_sequence}")
                    print(f"     Delivery Order: {delivery_order}")
                    
                    # Check for the specific clients mentioned
                    if 'nilda' in client_name.lower():
                        print(f"     🎯 FOUND NILDA: Position {i+1}, Priority: {priority}")
                    elif 'daiana' in client_name.lower():
                        print(f"     🎯 FOUND DAIANA: Position {i+1}, Priority: {priority}")
                    elif 'alex' in client_name.lower():
                        print(f"     🎯 FOUND ALEX: Position {i+1}, Priority: {priority}")
                
                # Check for deliveryOrder vs orderSequence issue
                self.analyze_delivery_vs_order_sequence(stops)
            
            # Check for alias field
            alias = route.get('alias') or route.get('route_alias') or route.get('custom_name')
            if alias:
                print(f"\n📝 ALIAS FOUND: {alias}")
                self.log_test("Route Alias Check", True, f"✅ Route has alias: {alias}")
            else:
                print(f"\n📝 NO ALIAS FOUND")
                self.log_test("Route Alias Check", False, "❌ Route has no alias field")
            
            return route
        else:
            self.log_test("Find Route RTE-0000001", False, "❌ Route RTE-0000001 not found", response['data'])
            return None
    
    def analyze_delivery_vs_order_sequence(self, stops: List[Dict]):
        """Analyze deliveryOrder vs orderSequence values"""
        print(f"\n🔍 ANALYZING deliveryOrder vs orderSequence:")
        
        delivery_orders = []
        order_sequences = []
        
        for stop in stops:
            delivery_order = stop.get('delivery_order')
            order_sequence = stop.get('order_sequence')
            
            if delivery_order is not None:
                delivery_orders.append(delivery_order)
            if order_sequence is not None:
                order_sequences.append(order_sequence)
        
        print(f"   Delivery Orders found: {delivery_orders}")
        print(f"   Order Sequences found: {order_sequences}")
        
        # Check if they are always equal (the reported problem)
        if delivery_orders and order_sequences:
            if len(delivery_orders) == len(order_sequences):
                are_equal = all(d == o for d, o in zip(delivery_orders, order_sequences))
                if are_equal:
                    self.log_test("DeliveryOrder vs OrderSequence", False, 
                                "❌ PROBLEM CONFIRMED: deliveryOrder and orderSequence have identical values")
                else:
                    self.log_test("DeliveryOrder vs OrderSequence", True, 
                                "✅ deliveryOrder and orderSequence have different values")
            else:
                self.log_test("DeliveryOrder vs OrderSequence", False, 
                            f"❌ Different number of delivery_order ({len(delivery_orders)}) vs order_sequence ({len(order_sequences)}) fields")
        else:
            if not delivery_orders:
                self.log_test("DeliveryOrder vs OrderSequence", False, 
                            "❌ No delivery_order field found in stops")
            if not order_sequences:
                self.log_test("DeliveryOrder vs OrderSequence", False, 
                            "❌ No order_sequence field found in stops")
    
    def test_route_optimization_algorithm(self):
        """Test the route optimization algorithm with specific scenario"""
        print("\n=== TESTING ROUTE OPTIMIZATION ALGORITHM ===")
        
        # Setup test data that mimics the user's scenario
        if not self.setup_optimization_test_data():
            return False
        
        # Get available items
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Get Available Items", False, "Failed to get available items", response['data'])
            return False
        
        available_items = response['data'].get('available_items', [])
        if len(available_items) < 3:
            self.log_test("Get Available Items", False, f"Need at least 3 items, got {len(available_items)}")
            return False
        
        # Create route
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2024-12-20",
            "planned_start_time": "08:00"
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if not response['success']:
            self.log_test("Create Test Route", False, "Failed to create route", response['data'])
            return False
        
        route_id = response['data']['id']
        self.created_resources['routes'].append(route_id)
        
        # Add stops with specific priorities to test the scenario
        stops_data = [
            {
                "budget_item_id": available_items[0]['budget_item_id'],
                "priority": "PRIMEIRA"  # This should be Nilda (first)
            },
            {
                "budget_item_id": available_items[1]['budget_item_id'], 
                "priority": "AUTOMATICA"  # This should be Alex (middle)
            },
            {
                "budget_item_id": available_items[2]['budget_item_id'],
                "priority": "AUTOMATICA"  # This should be Daiana (close to company, should be last)
            }
        ]
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', stops_data)
        if not response['success']:
            self.log_test("Add Stops to Route", False, "Failed to add stops", response['data'])
            return False
        
        # Optimize route and analyze results
        response = self.make_request('POST', f'/routes/{route_id}/optimize?route_type=EFICIENTE')
        if not response['success']:
            self.log_test("Optimize Route", False, "Failed to optimize route", response['data'])
            return False
        
        # Get optimized route details
        response = self.make_request('GET', f'/routes/{route_id}')
        if not response['success']:
            self.log_test("Get Optimized Route", False, "Failed to get route details", response['data'])
            return False
        
        optimized_route = response['data']
        self.analyze_optimization_results(optimized_route)
        
        return True
    
    def analyze_optimization_results(self, route: Dict):
        """Analyze the optimization results for logical issues"""
        print(f"\n🧠 ANALYZING OPTIMIZATION LOGIC:")
        
        stops = route.get('stops', [])
        company_address = route.get('company_address', {})
        company_lat = company_address.get('latitude')
        company_lng = company_address.get('longitude')
        
        print(f"   Company Location: {company_lat}, {company_lng}")
        print(f"   Total Stops: {len(stops)}")
        
        # Analyze stop order and priorities
        primeira_stops = []
        automatica_stops = []
        ultima_stops = []
        
        for i, stop in enumerate(stops):
            client_name = stop.get('client_name')
            priority = stop.get('priority')
            order_sequence = stop.get('order_sequence', i+1)
            address = stop.get('address', {})
            stop_lat = address.get('latitude')
            stop_lng = address.get('longitude')
            
            print(f"\n   Stop {order_sequence}: {client_name}")
            print(f"     Priority: {priority}")
            print(f"     Location: {stop_lat}, {stop_lng}")
            
            # Calculate distance from company (rough estimate)
            if company_lat and company_lng and stop_lat and stop_lng:
                distance = ((company_lat - stop_lat)**2 + (company_lng - stop_lng)**2)**0.5
                print(f"     Distance from company: {distance:.6f} (rough)")
                
                # Store for analysis
                stop_info = {
                    'name': client_name,
                    'priority': priority,
                    'order': order_sequence,
                    'distance': distance,
                    'position_in_route': i+1
                }
                
                if priority == 'PRIMEIRA':
                    primeira_stops.append(stop_info)
                elif priority == 'AUTOMATICA':
                    automatica_stops.append(stop_info)
                elif priority == 'ULTIMA':
                    ultima_stops.append(stop_info)
        
        # Analyze if optimization makes sense
        print(f"\n📊 OPTIMIZATION ANALYSIS:")
        print(f"   PRIMEIRA stops: {len(primeira_stops)}")
        print(f"   AUTOMATICA stops: {len(automatica_stops)}")
        print(f"   ULTIMA stops: {len(ultima_stops)}")
        
        # Check if PRIMEIRA stops are actually first
        if primeira_stops:
            for stop in primeira_stops:
                if stop['position_in_route'] == 1:
                    self.log_test("Priority PRIMEIRA Position", True, 
                                f"✅ {stop['name']} with PRIMEIRA priority is in position 1")
                else:
                    self.log_test("Priority PRIMEIRA Position", False, 
                                f"❌ {stop['name']} with PRIMEIRA priority is in position {stop['position_in_route']}, not 1")
        
        # Check if closest to company is last (for AUTOMATICA stops)
        if len(automatica_stops) >= 2:
            # Find closest to company among AUTOMATICA stops
            closest_stop = min(automatica_stops, key=lambda x: x['distance'])
            farthest_stop = max(automatica_stops, key=lambda x: x['distance'])
            
            print(f"   Closest to company: {closest_stop['name']} (distance: {closest_stop['distance']:.6f})")
            print(f"   Farthest from company: {farthest_stop['name']} (distance: {farthest_stop['distance']:.6f})")
            
            # Check if closest is last among AUTOMATICA stops
            automatica_positions = [stop['position_in_route'] for stop in automatica_stops]
            max_automatica_position = max(automatica_positions)
            
            if closest_stop['position_in_route'] == max_automatica_position:
                self.log_test("Closest Stop Last", True, 
                            f"✅ {closest_stop['name']} (closest to company) is last among AUTOMATICA stops")
            else:
                self.log_test("Closest Stop Last", False, 
                            f"❌ {closest_stop['name']} (closest to company) is in position {closest_stop['position_in_route']}, not last")
                
                # This might be the bug the user reported
                print(f"   🐛 POTENTIAL BUG: Closest stop should be last for efficient return to company")
    
    def test_alias_field_saving(self):
        """Test if alias field is properly saved in routes"""
        print("\n=== TESTING ALIAS FIELD SAVING ===")
        
        # Create route with alias
        route_data = {
            "vehicle_type": "MOTO",
            "planned_date": "2024-12-21",
            "planned_start_time": "09:00",
            "alias": "Rota Teste Personalizada"  # Test if this field is accepted
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if not response['success']:
            self.log_test("Create Route with Alias", False, "Failed to create route with alias", response['data'])
            return False
        
        route = response['data']
        route_id = route['id']
        self.created_resources['routes'].append(route_id)
        
        # Check if alias was saved
        saved_alias = route.get('alias')
        if saved_alias == "Rota Teste Personalizada":
            self.log_test("Alias Field Saving", True, f"✅ Alias saved correctly: {saved_alias}")
        else:
            self.log_test("Alias Field Saving", False, f"❌ Alias not saved. Expected: 'Rota Teste Personalizada', Got: {saved_alias}")
        
        # Try to update route with alias
        update_data = {
            "vehicle_type": "MOTO",
            "planned_date": "2024-12-21", 
            "planned_start_time": "09:00",
            "alias": "Rota Atualizada com Nome"
        }
        
        response = self.make_request('PUT', f'/routes/{route_id}', update_data)
        if response['success']:
            # Get updated route
            response = self.make_request('GET', f'/routes/{route_id}')
            if response['success']:
                updated_route = response['data']
                updated_alias = updated_route.get('alias')
                
                if updated_alias == "Rota Atualizada com Nome":
                    self.log_test("Alias Field Update", True, f"✅ Alias updated correctly: {updated_alias}")
                else:
                    self.log_test("Alias Field Update", False, f"❌ Alias not updated. Expected: 'Rota Atualizada com Nome', Got: {updated_alias}")
            else:
                self.log_test("Alias Field Update", False, "Failed to get updated route")
        else:
            self.log_test("Alias Field Update", False, "Failed to update route with alias", response['data'])
        
        return True
    
    def setup_optimization_test_data(self):
        """Setup test data for optimization testing"""
        print("\n=== SETTING UP OPTIMIZATION TEST DATA ===")
        
        # Setup system config with company coordinates
        system_config_data = {
            "company_name": "SuperDry Lavanderia de Tapetes & Estofados",
            "address_full": "Rua Central, 100",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP",
            "latitude": -23.5505,  # Company location
            "longitude": -46.6333,
            "phone": "11999999999",
            "email": "contato@superdry.com"
        }
        
        response = self.make_request('PUT', '/system-config', system_config_data)
        if not response['success']:
            self.log_test("Setup System Config", False, "Failed to setup system config", response['data'])
            return False
        
        # Create test clients with strategic locations
        clients_data = [
            {
                "name": "Nilda Silva",  # Should be PRIMEIRA
                "phone_primary": "11987654321",
                "email": "nilda@email.com",
                "address": {
                    "full_address": "Rua Distante, 500",
                    "neighborhood": "Bairro Longe",
                    "city": "São Paulo",
                    "state": "SP",
                    "latitude": -23.6000,  # Far from company
                    "longitude": -46.7000
                }
            },
            {
                "name": "Alex Santos",  # Should be middle
                "phone_primary": "11876543210",
                "email": "alex@email.com",
                "address": {
                    "full_address": "Rua Média, 200",
                    "neighborhood": "Bairro Médio",
                    "city": "São Paulo",
                    "state": "SP",
                    "latitude": -23.5700,  # Medium distance
                    "longitude": -46.6500
                }
            },
            {
                "name": "Daiana Olivatto",  # Should be last (close to company)
                "phone_primary": "11765432109",
                "email": "daiana@email.com",
                "address": {
                    "full_address": "Rua Próxima, 50",
                    "neighborhood": "Centro",
                    "city": "São Paulo",
                    "state": "SP",
                    "latitude": -23.5510,  # Very close to company
                    "longitude": -46.6340
                }
            }
        ]
        
        for client_data in clients_data:
            response = self.make_request('POST', '/clients', client_data)
            if response['success']:
                self.created_resources['clients'].append(response['data']['id'])
                self.log_test("Setup Client", True, f"Created client: {client_data['name']}")
            else:
                self.log_test("Setup Client", False, f"Failed to create client: {client_data['name']}", response['data'])
                return False
        
        # Create services
        service_data = {
            "name": "Limpeza de Tapete Teste",
            "category": "TAPETES",
            "service_type": "Limpeza",
            "measure_type": "AREA_DE_TAPETE",
            "execution_location": "RETIRADA",
            "cost_price": 50.0,
            "sale_price": 100.0,
            "default_service_status": "RETIRAR"
        }
        
        response = self.make_request('POST', '/services', service_data)
        if response['success']:
            service_id = response['data']['id']
            self.created_resources['services'].append(service_id)
            self.log_test("Setup Service", True, f"Created service: {service_id}")
        else:
            self.log_test("Setup Service", False, "Failed to create service", response['data'])
            return False
        
        # Create budgets for each client
        for i, client_id in enumerate(self.created_resources['clients']):
            budget_data = {
                "client_id": client_id,
                "payment_method": "PIX_CNPJ_25995295000104",
                "salesperson": "Gabriela Alcântara",
                "internal_observations": f"Orçamento para teste de otimização - Cliente {i+1}",
                "items": [
                    {
                        "service_id": service_id,
                        "service_name": "Limpeza de Tapete Teste",
                        "service_code": service_id,
                        "quantity": 1.0,
                        "unit_price": 100.0,
                        "total_value": 100.0,
                        "status": "RETIRAR",
                        "execution_location": "RETIRADA",
                        "area_m2": 2.0
                    }
                ]
            }
            
            response = self.make_request('POST', '/budgets', budget_data)
            if response['success']:
                self.created_resources['budgets'].append(response['data']['id'])
                self.log_test("Setup Budget", True, f"Created budget for client {i+1}")
            else:
                self.log_test("Setup Budget", False, f"Failed to create budget for client {i+1}", response['data'])
                return False
        
        return True
    
    def cleanup_test_data(self):
        """Clean up created test data"""
        print("\n=== CLEANING UP TEST DATA ===")
        
        # Delete routes
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
        
        # Delete clients
        for client_id in self.created_resources['clients']:
            response = self.make_request('DELETE', f'/clients/{client_id}')
            if response['success']:
                print(f"✅ Deleted client: {client_id}")
    
    def print_summary(self):
        """Print investigation results summary"""
        print("\n" + "=" * 80)
        print("📊 ROUTE OPTIMIZATION INVESTIGATION SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Investigations: {total_tests}")
        print(f"✅ Confirmed Working: {passed_tests}")
        print(f"❌ Issues Found: {failed_tests}")
        
        if failed_tests > 0:
            print(f"\n🐛 ISSUES IDENTIFIED:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print("\n" + "=" * 80)
    
    def run_investigation(self):
        """Run the complete route optimization investigation"""
        print("🔍 STARTING ROUTE OPTIMIZATION INVESTIGATION")
        print(f"🔗 Testing against: {self.base_url}")
        print("🎯 Focus: Critical route optimization problems reported by user")
        print("=" * 80)
        
        # Investigation 1: Look for the specific route RTE-0000001
        print("\n1️⃣ INVESTIGATING SPECIFIC ROUTE RTE-0000001:")
        self.investigate_route_rte_0000001()
        
        # Investigation 2: Test route optimization algorithm
        print("\n2️⃣ TESTING ROUTE OPTIMIZATION ALGORITHM:")
        self.test_route_optimization_algorithm()
        
        # Investigation 3: Test alias field saving
        print("\n3️⃣ TESTING ALIAS FIELD SAVING:")
        self.test_alias_field_saving()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        self.print_summary()
        
        return True

if __name__ == "__main__":
    investigator = RouteOptimizationInvestigator()
    investigator.run_investigation()