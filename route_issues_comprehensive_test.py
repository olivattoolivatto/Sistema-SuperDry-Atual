#!/usr/bin/env python3
"""
Comprehensive Route Issues Investigation for SuperDry Lavanderia Management System
Focus: All critical route optimization problems reported by user

CRITICAL ISSUES IDENTIFIED:
1. ❌ deliveryOrder field: MISSING from RouteStop model - only order_sequence exists
2. ❌ alias field: MISSING from Route model - not implemented in backend
3. ❌ Route UPDATE endpoint: MISSING - no PUT /api/routes/{id} endpoint
4. ⚠️  Route optimization logic: Needs investigation for geographic logic

BACKEND CODE ANALYSIS:
- RouteStop model only has order_sequence field (line 321)
- Route model has no alias field (lines 324-338)
- No PUT endpoint for route updates (only PUT /routes/{id}/stops exists)
- Optimization algorithm in lines 404-496 may have geographic logic issues
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://laundry-agenda-1.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class RouteIssuesComprehensiveTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.test_results = []
        self.issues_found = []
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
    
    def log_issue(self, issue_type: str, description: str, severity: str = "HIGH"):
        """Log critical issues found"""
        issue = {
            'type': issue_type,
            'description': description,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        }
        self.issues_found.append(issue)
        print(f"🐛 {severity} ISSUE - {issue_type}: {description}")
    
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
    
    def test_delivery_order_vs_order_sequence_issue(self):
        """CRITICAL TEST: Investigate deliveryOrder vs orderSequence issue"""
        print("\n=== TESTING deliveryOrder vs orderSequence ISSUE ===")
        
        # Get the specific route RTE-0000001 mentioned by user
        response = self.make_request('GET', '/routes/RTE-0000001')
        if not response['success']:
            self.log_test("Get Route RTE-0000001", False, "Route RTE-0000001 not found")
            return False
        
        route = response['data']
        stops = route.get('stops', [])
        
        if not stops:
            self.log_test("Route Stops Analysis", False, "No stops found in route")
            return False
        
        # Analyze the fields in stops
        first_stop = stops[0]
        available_fields = list(first_stop.keys())
        
        print(f"📋 Available fields in RouteStop: {available_fields}")
        
        # Check for deliveryOrder field
        has_delivery_order = any('delivery' in field.lower() for field in available_fields)
        has_order_sequence = 'order_sequence' in available_fields
        
        if not has_delivery_order:
            self.log_issue("MISSING_FIELD", 
                         "deliveryOrder field is MISSING from RouteStop model. Only order_sequence exists.",
                         "CRITICAL")
            self.log_test("DeliveryOrder Field Check", False, 
                        "❌ CRITICAL: deliveryOrder field missing from backend model")
        
        if has_order_sequence:
            self.log_test("OrderSequence Field Check", True, 
                        "✅ order_sequence field exists")
            
            # Show the values to demonstrate they're the same as position
            print(f"\n📊 ORDER SEQUENCE ANALYSIS:")
            for i, stop in enumerate(stops):
                client_name = stop.get('client_name', 'N/A')
                order_seq = stop.get('order_sequence', 'N/A')
                print(f"   Stop {i+1}: {client_name} - order_sequence: {order_seq}")
                
                # The issue: order_sequence is just the position (i+1)
                if order_seq == i + 1:
                    print(f"     ⚠️  order_sequence equals position - no separate delivery logic")
        
        # CONCLUSION: The user expects TWO different fields:
        # - order_sequence: The optimized route order
        # - deliveryOrder: The actual delivery sequence (which might be different)
        # But the backend only has order_sequence
        
        self.log_issue("DESIGN_FLAW", 
                     "Backend only has order_sequence field. User expects separate deliveryOrder field for different delivery logic.",
                     "HIGH")
        
        return True
    
    def test_alias_field_missing(self):
        """CRITICAL TEST: Investigate missing alias field"""
        print("\n=== TESTING ALIAS FIELD MISSING ISSUE ===")
        
        # Test 1: Try to create route with alias
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2024-12-20",
            "planned_start_time": "08:00",
            "alias": "Rota Personalizada Teste"
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if response['success']:
            route = response['data']
            route_id = route['id']
            self.created_resources['routes'].append(route_id)
            
            # Check if alias was saved
            saved_alias = route.get('alias')
            if saved_alias:
                self.log_test("Alias Field Creation", True, f"✅ Alias saved: {saved_alias}")
            else:
                self.log_issue("MISSING_FIELD", 
                             "alias field is MISSING from Route model in backend",
                             "HIGH")
                self.log_test("Alias Field Creation", False, 
                            "❌ alias field not saved - missing from backend model")
        else:
            self.log_test("Route Creation with Alias", False, 
                        "Failed to create route", response['data'])
        
        # Test 2: Check if route update endpoint exists
        if self.created_resources['routes']:
            route_id = self.created_resources['routes'][0]
            update_data = {
                "vehicle_type": "CARRO",
                "planned_date": "2024-12-20",
                "planned_start_time": "08:00",
                "alias": "Rota Atualizada"
            }
            
            response = self.make_request('PUT', f'/routes/{route_id}', update_data)
            if response['status_code'] == 405:  # Method Not Allowed
                self.log_issue("MISSING_ENDPOINT", 
                             "PUT /api/routes/{id} endpoint is MISSING - cannot update routes",
                             "HIGH")
                self.log_test("Route Update Endpoint", False, 
                            "❌ PUT /api/routes/{id} endpoint missing")
            elif response['success']:
                self.log_test("Route Update Endpoint", True, 
                            "✅ Route update endpoint works")
            else:
                self.log_test("Route Update Endpoint", False, 
                            f"Route update failed: {response['data']}")
        
        return True
    
    def test_route_optimization_geographic_logic(self):
        """CRITICAL TEST: Investigate route optimization geographic logic"""
        print("\n=== TESTING ROUTE OPTIMIZATION GEOGRAPHIC LOGIC ===")
        
        # Analyze the specific route RTE-0000001 for geographic logic issues
        response = self.make_request('GET', '/routes/RTE-0000001')
        if not response['success']:
            self.log_test("Get Route for Geographic Analysis", False, "Route not found")
            return False
        
        route = response['data']
        stops = route.get('stops', [])
        company_address = route.get('company_address', {})
        
        company_lat = company_address.get('latitude')
        company_lng = company_address.get('longitude')
        
        if not company_lat or not company_lng:
            self.log_test("Company Coordinates", False, "Company coordinates missing")
            return False
        
        print(f"🏢 Company Location: {company_lat}, {company_lng}")
        
        # Analyze each stop's distance from company
        stop_analysis = []
        for i, stop in enumerate(stops):
            client_name = stop.get('client_name', 'N/A')
            priority = stop.get('priority', 'N/A')
            address = stop.get('address', {})
            stop_lat = address.get('latitude')
            stop_lng = address.get('longitude')
            
            if stop_lat and stop_lng:
                # Calculate rough distance from company
                distance = ((company_lat - stop_lat)**2 + (company_lng - stop_lng)**2)**0.5
                
                stop_info = {
                    'position': i + 1,
                    'name': client_name,
                    'priority': priority,
                    'distance': distance,
                    'coordinates': (stop_lat, stop_lng)
                }
                stop_analysis.append(stop_info)
                
                print(f"📍 Stop {i+1}: {client_name}")
                print(f"   Priority: {priority}")
                print(f"   Distance from company: {distance:.6f}")
                
                # Check for specific clients mentioned by user
                if 'nilda' in client_name.lower():
                    print(f"   🎯 NILDA: Position {i+1}, Should be FIRST (PRIMEIRA)")
                elif 'daiana' in client_name.lower():
                    print(f"   🎯 DAIANA: Position {i+1}, Should be LAST (closest to company)")
        
        # Analyze optimization logic issues
        if len(stop_analysis) >= 2:
            # Find closest and farthest stops among AUTOMATICA priority
            automatica_stops = [s for s in stop_analysis if s['priority'] == 'AUTOMATICA']
            
            if len(automatica_stops) >= 2:
                closest_stop = min(automatica_stops, key=lambda x: x['distance'])
                farthest_stop = max(automatica_stops, key=lambda x: x['distance'])
                
                print(f"\n🔍 GEOGRAPHIC LOGIC ANALYSIS:")
                print(f"   Closest to company: {closest_stop['name']} (pos: {closest_stop['position']}, dist: {closest_stop['distance']:.6f})")
                print(f"   Farthest from company: {farthest_stop['name']} (pos: {farthest_stop['position']}, dist: {farthest_stop['distance']:.6f})")
                
                # Check if closest is last (optimal for return to company)
                automatica_positions = [s['position'] for s in automatica_stops]
                max_position = max(automatica_positions)
                
                if closest_stop['position'] == max_position:
                    self.log_test("Geographic Optimization", True, 
                                "✅ Closest stop is last - optimal for return")
                else:
                    self.log_issue("OPTIMIZATION_LOGIC", 
                                 f"Closest stop ({closest_stop['name']}) is not last. Should be last for efficient return to company.",
                                 "MEDIUM")
                    self.log_test("Geographic Optimization", False, 
                                f"❌ Closest stop ({closest_stop['name']}) should be last")
                
                # Check if Daiana (mentioned by user) is the closest
                daiana_stop = next((s for s in automatica_stops if 'daiana' in s['name'].lower()), None)
                if daiana_stop:
                    if daiana_stop == closest_stop:
                        print(f"   ✅ Daiana is closest to company (should be last)")
                        if daiana_stop['position'] != max_position:
                            self.log_issue("USER_REPORTED_BUG", 
                                         "Daiana is closest to company but not in last position. User reported this specific issue.",
                                         "HIGH")
                    else:
                        print(f"   ℹ️  Daiana is not the closest stop")
        
        return True
    
    def test_osrm_integration_issues(self):
        """TEST: Check OSRM integration for potential issues"""
        print("\n=== TESTING OSRM INTEGRATION ISSUES ===")
        
        # Create a test route to check OSRM behavior
        if not self.setup_test_data():
            return False
        
        # Get available items
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Get Available Items", False, "Failed to get available items")
            return False
        
        available_items = response['data'].get('available_items', [])
        if len(available_items) < 2:
            self.log_test("OSRM Test Setup", False, "Need at least 2 items for OSRM test")
            return False
        
        # Create route
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2024-12-20",
            "planned_start_time": "08:00"
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if not response['success']:
            self.log_test("Create OSRM Test Route", False, "Failed to create route")
            return False
        
        route_id = response['data']['id']
        self.created_resources['routes'].append(route_id)
        
        # Add stops
        stops_data = [
            {"budget_item_id": available_items[0]['budget_item_id'], "priority": "AUTOMATICA"},
            {"budget_item_id": available_items[1]['budget_item_id'], "priority": "AUTOMATICA"}
        ]
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', stops_data)
        if not response['success']:
            self.log_test("Add Stops for OSRM", False, "Failed to add stops")
            return False
        
        # Test OSRM optimization
        response = self.make_request('POST', f'/routes/{route_id}/optimize?route_type=EFICIENTE')
        if response['success']:
            result = response['data']
            distance_km = result.get('total_distance_km', 0)
            
            # Check for unrealistic distances (user mentioned 3072km for local routes)
            if distance_km > 1000:  # More than 1000km for local routes is suspicious
                self.log_issue("OSRM_DISTANCE", 
                             f"OSRM returned unrealistic distance: {distance_km}km for local route",
                             "MEDIUM")
                self.log_test("OSRM Distance Check", False, 
                            f"❌ Unrealistic distance: {distance_km}km")
            else:
                self.log_test("OSRM Distance Check", True, 
                            f"✅ Reasonable distance: {distance_km}km")
            
            self.log_test("OSRM Integration", True, "✅ OSRM optimization working")
        else:
            self.log_test("OSRM Integration", False, "❌ OSRM optimization failed", response['data'])
        
        return True
    
    def setup_test_data(self):
        """Setup minimal test data"""
        # Create client
        client_data = {
            "name": "Teste Cliente",
            "phone_primary": "11999999999",
            "address": {
                "full_address": "Rua Teste, 100",
                "neighborhood": "Centro",
                "city": "São Paulo",
                "state": "SP",
                "latitude": -23.5505,
                "longitude": -46.6333
            }
        }
        
        response = self.make_request('POST', '/clients', client_data)
        if response['success']:
            self.created_resources['clients'].append(response['data']['id'])
        else:
            return False
        
        # Create service
        service_data = {
            "name": "Teste Serviço",
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
        else:
            return False
        
        # Create budget
        budget_data = {
            "client_id": self.created_resources['clients'][0],
            "payment_method": "PIX_CNPJ_25995295000104",
            "salesperson": "Gabriela Alcântara",
            "items": [{
                "service_id": service_id,
                "service_name": "Teste Serviço",
                "service_code": service_id,
                "quantity": 1.0,
                "unit_price": 100.0,
                "total_value": 100.0,
                "status": "RETIRAR",
                "execution_location": "RETIRADA"
            }]
        }
        
        response = self.make_request('POST', '/budgets', budget_data)
        if response['success']:
            self.created_resources['budgets'].append(response['data']['id'])
            return True
        
        return False
    
    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n=== CLEANING UP TEST DATA ===")
        
        for route_id in self.created_resources['routes']:
            self.make_request('DELETE', f'/routes/{route_id}')
        
        for budget_id in self.created_resources['budgets']:
            self.make_request('DELETE', f'/budgets/{budget_id}')
        
        for client_id in self.created_resources['clients']:
            self.make_request('DELETE', f'/clients/{client_id}')
    
    def print_comprehensive_summary(self):
        """Print comprehensive summary of all issues found"""
        print("\n" + "=" * 80)
        print("🔍 COMPREHENSIVE ROUTE ISSUES INVESTIGATION SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        
        print(f"\n🐛 CRITICAL ISSUES IDENTIFIED: {len(self.issues_found)}")
        
        if self.issues_found:
            for issue in self.issues_found:
                severity_icon = "🔴" if issue['severity'] == "CRITICAL" else "🟡" if issue['severity'] == "HIGH" else "🟠"
                print(f"  {severity_icon} {issue['severity']} - {issue['type']}: {issue['description']}")
        
        print(f"\n📋 BACKEND CODE FIXES NEEDED:")
        print(f"  1. Add 'delivery_order' field to RouteStop model (server.py line 321)")
        print(f"  2. Add 'alias' field to Route model (server.py line 324-338)")
        print(f"  3. Implement PUT /api/routes/{{id}} endpoint for route updates")
        print(f"  4. Review OSRM optimization logic for geographic efficiency")
        
        print("\n" + "=" * 80)
    
    def run_comprehensive_investigation(self):
        """Run complete investigation of all route issues"""
        print("🔍 STARTING COMPREHENSIVE ROUTE ISSUES INVESTIGATION")
        print(f"🔗 Testing against: {self.base_url}")
        print("🎯 Focus: All critical route optimization problems reported by user")
        print("=" * 80)
        
        # Investigation 1: deliveryOrder vs orderSequence issue
        print("\n1️⃣ INVESTIGATING deliveryOrder vs orderSequence ISSUE:")
        self.test_delivery_order_vs_order_sequence_issue()
        
        # Investigation 2: Missing alias field
        print("\n2️⃣ INVESTIGATING MISSING ALIAS FIELD:")
        self.test_alias_field_missing()
        
        # Investigation 3: Route optimization geographic logic
        print("\n3️⃣ INVESTIGATING ROUTE OPTIMIZATION GEOGRAPHIC LOGIC:")
        self.test_route_optimization_geographic_logic()
        
        # Investigation 4: OSRM integration issues
        print("\n4️⃣ INVESTIGATING OSRM INTEGRATION ISSUES:")
        self.test_osrm_integration_issues()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Comprehensive summary
        self.print_comprehensive_summary()
        
        return True

if __name__ == "__main__":
    tester = RouteIssuesComprehensiveTester()
    tester.run_comprehensive_investigation()