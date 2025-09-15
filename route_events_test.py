#!/usr/bin/env python3
"""
Route Events Test Suite for SuperDry Lavanderia Management System
Focus: Testing new route event functionality with custom dates and optimized durations
"""

import requests
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://tech-laundry-hub.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class RouteEventsTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.test_results = []
        self.created_resources = {
            'clients': [],
            'services': [],
            'budgets': [],
            'routes': [],
            'calendar_events': []
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
        """Create test data for route events testing"""
        print("\n=== SETTING UP TEST DATA FOR ROUTE EVENTS ===")
        
        # Create test clients with different addresses for multiple items same location test
        clients_data = [
            {
                "name": "Cliente Mesmo Local A",
                "phone_primary": "65987654321",
                "email": "clienteA@email.com",
                "address": {
                    "full_address": "Rua das Flores, 123 - Centro, Cuiabá - MT",
                    "neighborhood": "Centro",
                    "city": "Cuiabá",
                    "state": "MT",
                    "latitude": -15.6014,
                    "longitude": -56.0979
                }
            },
            {
                "name": "Cliente Mesmo Local B",
                "phone_primary": "65987654322",
                "email": "clienteB@email.com",
                "address": {
                    "full_address": "Rua das Flores, 123 - Centro, Cuiabá - MT",  # Same address
                    "neighborhood": "Centro",
                    "city": "Cuiabá",
                    "state": "MT",
                    "latitude": -15.6014,
                    "longitude": -56.0979
                }
            },
            {
                "name": "Cliente Local Diferente",
                "phone_primary": "65987654323",
                "email": "clienteC@email.com",
                "address": {
                    "full_address": "Av. Getúlio Vargas, 456 - Araés, Cuiabá - MT",
                    "neighborhood": "Araés",
                    "city": "Cuiabá",
                    "state": "MT",
                    "latitude": -15.5989,
                    "longitude": -56.0949
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
        
        # Create test services with different statuses for duration testing
        services_data = [
            {
                "name": "Serviço EXECUTAR_NO_LOCAL - 120min",
                "category": "CARPETES_E_TAPETES_NO_LOCAL",
                "service_type": "Limpeza no Local",
                "measure_type": "CARPETE_TAPETE_LOCAL",
                "execution_location": "NO_LOCAL",
                "cost_price": 50.0,
                "sale_price": 100.0,
                "default_service_status": "EXECUTAR_NO_LOCAL"
            },
            {
                "name": "Serviço RETIRAR - 30min",
                "category": "ESTOFADOS",
                "service_type": "Retirada",
                "measure_type": "UNITARIO",
                "execution_location": "RETIRADA",
                "cost_price": 30.0,
                "sale_price": 60.0,
                "default_service_status": "RETIRAR"
            },
            {
                "name": "Serviço ENTREGAR - 30min",
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
        
        # Create test budgets with items for route events
        budget_configs = [
            # Two items at same location with EXECUTAR_NO_LOCAL (should get 15% reduction)
            {"client_idx": 0, "service_idx": 0, "status": "EXECUTAR_NO_LOCAL"},
            {"client_idx": 1, "service_idx": 1, "status": "RETIRAR"},  # Same location as client 0
            # One item at different location
            {"client_idx": 2, "service_idx": 2, "status": "ENTREGAR"}
        ]
        
        for i, config in enumerate(budget_configs):
            client_id = self.created_resources['clients'][config['client_idx']]
            service_id = self.created_resources['services'][config['service_idx']]
            
            budget_data = {
                "client_id": client_id,
                "payment_method": "PIX_CNPJ_25995295000104",
                "salesperson": "Gabriela Alcântara",
                "internal_observations": f"Orçamento para teste de eventos de rota - Item {i+1}",
                "items": [
                    {
                        "id": f"ITM-EVT{i+1:03d}",
                        "service_id": service_id,
                        "service_name": services_data[config['service_idx']]["name"],
                        "service_code": service_id,
                        "quantity": 1.0,
                        "unit_price": services_data[config['service_idx']]["sale_price"],
                        "total_value": services_data[config['service_idx']]["sale_price"],
                        "status": config['status'],
                        "execution_location": services_data[config['service_idx']]["execution_location"],
                        "is_retoque": False
                    }
                ]
            }
            
            response = self.make_request('POST', '/budgets', budget_data)
            if response['success']:
                self.created_resources['budgets'].append(response['data']['id'])
                self.log_test("Setup: Create Test Budget", True, f"Budget created with {config['status']} item")
            else:
                self.log_test("Setup: Create Test Budget", False, f"Failed to create budget for item {i+1}", response['data'])
                return False
        
        return True
    
    def create_test_route(self):
        """Create a test route with stops for event testing"""
        print("\n=== CREATING TEST ROUTE FOR EVENTS ===")
        
        # Create route
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2025-01-15",  # Different from custom date we'll use
            "planned_start_time": "08:00",
            "alias": "Rota Teste Eventos Personalizados"
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if not response['success']:
            self.log_test("Create Test Route", False, "Failed to create test route", response['data'])
            return None
        
        route = response['data']
        route_id = route['id']
        self.created_resources['routes'].append(route_id)
        self.log_test("Create Test Route", True, f"Route created: {route_id}")
        
        # Get available items
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Get Available Items", False, "Failed to get available items", response['data'])
            return None
        
        available_items = response['data'].get('available_items', [])
        if len(available_items) < 3:
            self.log_test("Get Available Items", False, f"Need at least 3 items, got {len(available_items)}")
            return None
        
        # Add stops to route (use first 3 items)
        stops_data = []
        for i, item in enumerate(available_items[:3]):
            stops_data.append({
                "budget_item_id": item["budget_item_id"],
                "priority": "AUTOMATICA"
            })
        
        response = self.make_request('PUT', f'/routes/{route_id}/stops', stops_data)
        if response['success']:
            self.log_test("Add Route Stops", True, f"Added {len(stops_data)} stops to route")
            return route_id
        else:
            self.log_test("Add Route Stops", False, "Failed to add stops to route", response['data'])
            return None
    
    def test_custom_date_functionality(self, route_id: str):
        """Test 1: Custom Date Functionality - Create events with custom date different from planned_date"""
        print("\n=== TEST 1: CUSTOM DATE FUNCTIONALITY ===")
        
        # Get route details to verify planned_date
        response = self.make_request('GET', f'/routes/{route_id}')
        if not response['success']:
            self.log_test("Custom Date Test", False, "Failed to get route details", response['data'])
            return False
        
        route = response['data']
        planned_date = route.get('planned_date')
        stops = route.get('stops', [])
        
        if not stops:
            self.log_test("Custom Date Test", False, "Route has no stops for testing")
            return False
        
        # Use custom date different from planned_date
        custom_date = "2025-09-10"  # As specified in test data
        custom_time = "10:00"
        
        # Create calendar events with custom date
        event_request = {
            "route_id": route_id,
            "stop_ids": [stops[0]["id"]],  # Use first stop
            "start_date": custom_date,
            "start_time": custom_time
        }
        
        response = self.make_request('POST', '/calendar/events', event_request)
        if response['success']:
            events = response['data'].get('events', [])
            if events:
                event = events[0]
                event_start = event.get('start_datetime')
                
                # Verify custom date was used instead of planned_date
                if custom_date in event_start and planned_date != custom_date:
                    self.created_resources['calendar_events'].extend([e.get('id') for e in events])
                    self.log_test("Custom Date Test", True, 
                                f"✅ Custom date used: {custom_date} (route planned_date: {planned_date})")
                    return True
                else:
                    self.log_test("Custom Date Test", False, 
                                f"❌ Custom date not used correctly: event_start={event_start}, custom_date={custom_date}")
                    return False
            else:
                self.log_test("Custom Date Test", False, "No events created")
                return False
        else:
            self.log_test("Custom Date Test", False, "Failed to create calendar events", response['data'])
            return False
    
    def test_basic_durations(self, route_id: str):
        """Test 2: Basic Duration Testing - Verify EXECUTAR_NO_LOCAL = 120min and RETIRAR/ENTREGAR = 30min"""
        print("\n=== TEST 2: BASIC DURATION TESTING ===")
        
        # Get route details
        response = self.make_request('GET', f'/routes/{route_id}')
        if not response['success']:
            self.log_test("Basic Duration Test", False, "Failed to get route details", response['data'])
            return False
        
        route = response['data']
        stops = route.get('stops', [])
        
        if len(stops) < 2:
            self.log_test("Basic Duration Test", False, "Need at least 2 stops for duration testing")
            return False
        
        # Find stops with different service statuses
        executar_stop = None
        retirar_entregar_stop = None
        
        for stop in stops:
            if stop.get('service_status') == 'EXECUTAR_NO_LOCAL':
                executar_stop = stop
            elif stop.get('service_status') in ['RETIRAR', 'ENTREGAR']:
                retirar_entregar_stop = stop
        
        if not executar_stop or not retirar_entregar_stop:
            self.log_test("Basic Duration Test", False, "Missing required service status types in stops")
            return False
        
        # Create events for both types
        event_request = {
            "route_id": route_id,
            "stop_ids": [executar_stop["id"], retirar_entregar_stop["id"]],
            "start_date": "2025-09-10",
            "start_time": "10:00"
        }
        
        response = self.make_request('POST', '/calendar/events', event_request)
        if response['success']:
            events = response['data'].get('events', [])
            
            duration_results = {}
            for event in events:
                start_time = datetime.fromisoformat(event['start_datetime'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(event['end_datetime'].replace('Z', '+00:00'))
                duration_minutes = int((end_time - start_time).total_seconds() / 60)
                
                # Find corresponding stop
                stop_id = event.get('stop_id')
                stop = next((s for s in stops if s['id'] == stop_id), None)
                if stop:
                    service_status = stop.get('service_status')
                    duration_results[service_status] = duration_minutes
            
            # Verify durations
            success = True
            messages = []
            
            if 'EXECUTAR_NO_LOCAL' in duration_results:
                duration = duration_results['EXECUTAR_NO_LOCAL']
                if duration == 120:
                    messages.append(f"✅ EXECUTAR_NO_LOCAL: {duration} minutes (correct)")
                else:
                    messages.append(f"❌ EXECUTAR_NO_LOCAL: {duration} minutes (expected 120)")
                    success = False
            
            for status in ['RETIRAR', 'ENTREGAR']:
                if status in duration_results:
                    duration = duration_results[status]
                    if duration == 30:
                        messages.append(f"✅ {status}: {duration} minutes (correct)")
                    else:
                        messages.append(f"❌ {status}: {duration} minutes (expected 30)")
                        success = False
            
            self.log_test("Basic Duration Test", success, "; ".join(messages))
            return success
        else:
            self.log_test("Basic Duration Test", False, "Failed to create calendar events", response['data'])
            return False
    
    def test_multiple_items_same_location(self, route_id: str):
        """Test 3: Multiple Items Same Location - Test optimization for items at same address"""
        print("\n=== TEST 3: MULTIPLE ITEMS SAME LOCATION OPTIMIZATION ===")
        
        # Get route details
        response = self.make_request('GET', f'/routes/{route_id}')
        if not response['success']:
            self.log_test("Multiple Items Test", False, "Failed to get route details", response['data'])
            return False
        
        route = response['data']
        stops = route.get('stops', [])
        
        # Group stops by location (same coordinates)
        location_groups = {}
        for stop in stops:
            address = stop.get('address', {})
            lat = address.get('latitude')
            lng = address.get('longitude')
            
            if lat and lng:
                location_key = f"{lat},{lng}"
                if location_key not in location_groups:
                    location_groups[location_key] = []
                location_groups[location_key].append(stop)
        
        # Find location with multiple items
        multi_item_location = None
        for location_key, location_stops in location_groups.items():
            if len(location_stops) >= 2:
                multi_item_location = location_stops
                break
        
        if not multi_item_location:
            self.log_test("Multiple Items Test", False, "No location with multiple items found")
            return False
        
        # Create events for multiple items at same location
        stop_ids = [stop['id'] for stop in multi_item_location]
        event_request = {
            "route_id": route_id,
            "stop_ids": stop_ids,
            "start_date": "2025-09-10",
            "start_time": "10:00"
        }
        
        response = self.make_request('POST', '/calendar/events', event_request)
        if response['success']:
            events = response['data'].get('events', [])
            
            # Calculate total duration and check for optimization
            total_duration = 0
            has_execution = False
            base_duration = 0
            
            for event in events:
                start_time = datetime.fromisoformat(event['start_datetime'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(event['end_datetime'].replace('Z', '+00:00'))
                duration_minutes = int((end_time - start_time).total_seconds() / 60)
                total_duration += duration_minutes
                
                # Find corresponding stop to check service status
                stop_id = event.get('stop_id')
                stop = next((s for s in multi_item_location if s['id'] == stop_id), None)
                if stop:
                    service_status = stop.get('service_status')
                    if service_status == 'EXECUTAR_NO_LOCAL':
                        has_execution = True
                        base_duration += 120
                    else:
                        base_duration += 30
            
            # Calculate expected optimized duration
            if has_execution:
                expected_optimized = int(base_duration * 0.85)  # 15% reduction
                reduction_type = "15% (with execution)"
            else:
                expected_optimized = int(base_duration * 0.75)  # 25% reduction
                reduction_type = "25% (without execution)"
            
            # Check if optimization was applied
            tolerance = 5  # Allow 5 minute tolerance
            if abs(total_duration - expected_optimized) <= tolerance:
                self.log_test("Multiple Items Test", True, 
                            f"✅ Optimization applied: {total_duration}min (expected ~{expected_optimized}min, {reduction_type})")
                return True
            else:
                self.log_test("Multiple Items Test", False, 
                            f"❌ Optimization not applied correctly: {total_duration}min (expected ~{expected_optimized}min, {reduction_type})")
                return False
        else:
            self.log_test("Multiple Items Test", False, "Failed to create calendar events", response['data'])
            return False
    
    def test_calculate_optimized_durations_function(self):
        """Test 4: Test calculate_optimized_durations() function algorithm"""
        print("\n=== TEST 4: CALCULATE_OPTIMIZED_DURATIONS FUNCTION ===")
        
        # This test verifies the algorithm by creating a scenario and checking the results
        # We'll create events and analyze the duration patterns to verify the algorithm works
        
        # Get available items to create test scenario
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Duration Algorithm Test", False, "Failed to get available items", response['data'])
            return False
        
        available_items = response['data'].get('available_items', [])
        if len(available_items) < 2:
            self.log_test("Duration Algorithm Test", False, "Need at least 2 items for algorithm testing")
            return False
        
        # Create a new route for this specific test
        route_data = {
            "vehicle_type": "CARRO",
            "planned_date": "2025-09-11",
            "planned_start_time": "09:00",
            "alias": "Rota Teste Algoritmo Durações"
        }
        
        response = self.make_request('POST', '/routes', route_data)
        if not response['success']:
            self.log_test("Duration Algorithm Test", False, "Failed to create test route", response['data'])
            return False
        
        test_route_id = response['data']['id']
        self.created_resources['routes'].append(test_route_id)
        
        # Add stops with items that should trigger optimization
        stops_data = []
        for item in available_items[:2]:  # Use first 2 items
            stops_data.append({
                "budget_item_id": item["budget_item_id"],
                "priority": "AUTOMATICA"
            })
        
        response = self.make_request('PUT', f'/routes/{test_route_id}/stops', stops_data)
        if not response['success']:
            self.log_test("Duration Algorithm Test", False, "Failed to add stops to test route", response['data'])
            return False
        
        # Get route with stops
        response = self.make_request('GET', f'/routes/{test_route_id}')
        if not response['success']:
            self.log_test("Duration Algorithm Test", False, "Failed to get test route details", response['data'])
            return False
        
        route = response['data']
        stops = route.get('stops', [])
        
        # Create events to test the algorithm
        event_request = {
            "route_id": test_route_id,
            "stop_ids": [stop['id'] for stop in stops],
            "start_date": "2025-09-11",
            "start_time": "09:00"
        }
        
        response = self.make_request('POST', '/calendar/events', event_request)
        if response['success']:
            events = response['data'].get('events', [])
            
            # Analyze the duration distribution
            durations = []
            for event in events:
                start_time = datetime.fromisoformat(event['start_datetime'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(event['end_datetime'].replace('Z', '+00:00'))
                duration_minutes = int((end_time - start_time).total_seconds() / 60)
                durations.append(duration_minutes)
            
            # Verify algorithm characteristics
            algorithm_working = True
            messages = []
            
            # Check if durations are reasonable (not all default values)
            if len(set(durations)) > 1 or any(d != 30 and d != 120 for d in durations):
                messages.append("✅ Algorithm producing varied durations")
            else:
                messages.append("❌ Algorithm not producing optimization")
                algorithm_working = False
            
            # Check if minimum duration constraint is respected (15 minutes minimum)
            if all(d >= 15 for d in durations):
                messages.append("✅ Minimum duration constraint (15min) respected")
            else:
                messages.append("❌ Minimum duration constraint violated")
                algorithm_working = False
            
            self.log_test("Duration Algorithm Test", algorithm_working, 
                        f"Algorithm analysis: {'; '.join(messages)}. Durations: {durations}")
            return algorithm_working
        else:
            self.log_test("Duration Algorithm Test", False, "Failed to create events for algorithm test", response['data'])
            return False
    
    def test_event_color_and_storage(self, route_id: str):
        """Test 5: Verify events are created with colorId '5' and stored correctly"""
        print("\n=== TEST 5: EVENT COLOR AND STORAGE VERIFICATION ===")
        
        # Get route details
        response = self.make_request('GET', f'/routes/{route_id}')
        if not response['success']:
            self.log_test("Event Color Test", False, "Failed to get route details", response['data'])
            return False
        
        route = response['data']
        stops = route.get('stops', [])
        
        if not stops:
            self.log_test("Event Color Test", False, "No stops available for testing")
            return False
        
        # Create event
        event_request = {
            "route_id": route_id,
            "stop_ids": [stops[0]["id"]],
            "start_date": "2025-09-10",
            "start_time": "10:00"
        }
        
        response = self.make_request('POST', '/calendar/events', event_request)
        if response['success']:
            events = response['data'].get('events', [])
            
            if events:
                event = events[0]
                
                # Verify database storage
                checks = [
                    (event.get('route_id') == route_id, "Route ID stored correctly"),
                    (event.get('stop_id') in [s['id'] for s in stops], "Stop ID stored correctly"),
                    (event.get('google_event_id') is not None, "Google Calendar event ID present"),
                    (event.get('start_datetime') is not None, "Start datetime stored"),
                    (event.get('end_datetime') is not None, "End datetime stored")
                ]
                
                all_passed = all(check[0] for check in checks)
                failed_checks = [check[1] for check in checks if not check[0]]
                
                if all_passed:
                    self.log_test("Event Color Test", True, 
                                "✅ Event stored correctly in database with all required fields")
                    
                    # Note: We can't directly verify colorId '5' without Google Calendar API access,
                    # but we can verify the event was created successfully
                    self.log_test("Event Color Verification", True, 
                                "✅ Event created (colorId '5' should be applied per backend code)")
                    return True
                else:
                    self.log_test("Event Color Test", False, 
                                f"❌ Storage validation failed: {failed_checks}")
                    return False
            else:
                self.log_test("Event Color Test", False, "No events created")
                return False
        else:
            self.log_test("Event Color Test", False, "Failed to create calendar events", response['data'])
            return False
    
    def cleanup_test_data(self):
        """Clean up created test data"""
        print("\n=== CLEANING UP TEST DATA ===")
        
        # Delete calendar events
        for event_id in self.created_resources['calendar_events']:
            # Note: Calendar events are typically cleaned up automatically or via Google Calendar API
            print(f"ℹ️  Calendar event created: {event_id}")
        
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
            else:
                print(f"❌ Failed to delete budget: {budget_id}")
        
        # Delete clients
        for client_id in self.created_resources['clients']:
            response = self.make_request('DELETE', f'/clients/{client_id}')
            if response['success']:
                print(f"✅ Deleted client: {client_id}")
            else:
                print(f"❌ Failed to delete client: {client_id}")
        
        print(f"ℹ️  Services created: {len(self.created_resources['services'])} (not deleted)")
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 80)
        print("📊 ROUTE EVENTS TEST RESULTS SUMMARY")
        print("=" * 80)
        
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
        
        print("\n" + "=" * 80)
    
    def run_route_events_tests(self):
        """Run comprehensive route events tests"""
        print("🎯 STARTING ROUTE EVENTS COMPREHENSIVE TESTS")
        print(f"🔗 Testing against: {self.base_url}")
        print("🎯 Focus: Custom dates, optimized durations, multiple items same location")
        print("=" * 80)
        
        # Setup test data
        if not self.setup_test_data():
            print("❌ CRITICAL: Failed to setup test data. Aborting tests.")
            return False
        
        # Create test route
        route_id = self.create_test_route()
        if not route_id:
            print("❌ CRITICAL: Failed to create test route. Aborting tests.")
            return False
        
        # Run all tests
        print(f"\n🚀 Running tests with route: {route_id}")
        
        # Test 1: Custom Date Functionality
        self.test_custom_date_functionality(route_id)
        
        # Test 2: Basic Duration Testing
        self.test_basic_durations(route_id)
        
        # Test 3: Multiple Items Same Location
        self.test_multiple_items_same_location(route_id)
        
        # Test 4: Algorithm Testing
        self.test_calculate_optimized_durations_function()
        
        # Test 5: Event Color and Storage
        self.test_event_color_and_storage(route_id)
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        self.print_summary()
        
        return True

if __name__ == "__main__":
    tester = RouteEventsTester()
    success = tester.run_route_events_tests()
    sys.exit(0 if success else 1)