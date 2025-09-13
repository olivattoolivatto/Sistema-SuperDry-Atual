#!/usr/bin/env python3
"""
Specific Test for Technician Mode Improvements
Testing the exact endpoints and data mentioned in the review request
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://tecnico-mode.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class TechnicianModeSpecificTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.test_results = []
    
    def log_test(self, test_name: str, success: bool, message: str, details=None):
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
    
    def make_request(self, method: str, endpoint: str, data=None):
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=self.headers, json=data)
            
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
    
    def test_technician_assign_events_specific(self):
        """Test POST /api/technician/assign-events with specific data from review"""
        print("\n=== TESTING TECHNICIAN ASSIGNMENT WITH SPECIFIC DATA ===")
        
        # Create assignment with data from review request
        assignment_data = {
            "route_id": "RTE-TEST001",
            "event_ids": ["CAL-EVENT01", "CAL-EVENT02"],
            "technician_id": "TECH-001",
            "assigned_date": "2025-09-13",  # Data específica da review
            "assignment_type": "AGENDA"
        }
        
        response = self.make_request('POST', '/technician/assign-events', assignment_data)
        if response['success']:
            result = response['data']
            
            # Verify response structure matches expected format
            if (result.get('success') == True and
                result.get('assignment_id') and
                result.get('events_assigned') == 2 and
                result.get('technician_id') == 'TECH-001'):
                
                assignment_id = result.get('assignment_id')
                self.log_test("POST /api/technician/assign-events", True, 
                            f"✅ Assignment created successfully: {assignment_id}")
                return assignment_id
            else:
                self.log_test("POST /api/technician/assign-events", False, 
                            f"❌ Invalid response structure: {result}")
                return None
        else:
            self.log_test("POST /api/technician/assign-events", False, 
                        f"❌ Request failed with status {response['status_code']}", response['data'])
            return None
    
    def test_technician_daily_tasks_specific(self):
        """Test GET /api/technician/TECH-001/daily-tasks with specific data from review"""
        print("\n=== TESTING TECHNICIAN DAILY TASKS WITH SPECIFIC DATA ===")
        
        # Test with exact parameters from review request
        technician_id = "TECH-001"
        date = "2025-09-13"  # Data específica da review
        
        response = self.make_request('GET', f'/technician/{technician_id}/daily-tasks?date={date}')
        if response['success']:
            result = response['data']
            
            # Verify hybrid structure as mentioned in review
            required_sections = ['agenda_events', 'status_items', 'assignments']
            missing_sections = [section for section in required_sections if section not in result]
            
            if not missing_sections:
                agenda_events = result.get('agenda_events', [])
                status_items = result.get('status_items', [])
                assignments = result.get('assignments', [])
                
                print(f"   📊 Estrutura híbrida retornada:")
                print(f"   📋 agenda_events: {len(agenda_events)} items")
                print(f"   📊 status_items: {len(status_items)} items")
                print(f"   📝 assignments: {len(assignments)} items")
                
                # Verify deduplication (sistema híbrido combina assignments da agenda + itens por status)
                assigned_event_ids = set()
                for assignment in assignments:
                    assigned_event_ids.update(assignment.get('event_ids', []))
                
                status_item_ids = set(item.get('id') for item in status_items if item.get('id'))
                overlap = assigned_event_ids.intersection(status_item_ids)
                
                if len(overlap) == 0:
                    self.log_test("GET /api/technician/TECH-001/daily-tasks", True, 
                                f"✅ Hybrid structure working correctly - assignments + status_items with no overlap")
                    
                    # Verify assignment structure
                    if assignments:
                        first_assignment = assignments[0]
                        assignment_fields = ['id', 'technician_id', 'assigned_date', 'assignment_type', 'status']
                        missing_fields = [field for field in assignment_fields if field not in first_assignment]
                        
                        if not missing_fields:
                            self.log_test("Assignment Structure", True, 
                                        f"✅ Assignment contains all required fields")
                        else:
                            self.log_test("Assignment Structure", False, 
                                        f"❌ Missing assignment fields: {missing_fields}")
                    
                    # Verify status_items structure
                    if status_items:
                        first_status_item = status_items[0]
                        status_fields = ['id', 'client_name', 'service_name', 'status']
                        missing_fields = [field for field in status_fields if field not in first_status_item]
                        
                        if not missing_fields:
                            self.log_test("Status Items Structure", True, 
                                        f"✅ Status items contain required fields")
                        else:
                            self.log_test("Status Items Structure", False, 
                                        f"❌ Missing status item fields: {missing_fields}")
                    
                    return result
                else:
                    self.log_test("GET /api/technician/TECH-001/daily-tasks", False, 
                                f"❌ Deduplication failed - {len(overlap)} items appear in both lists")
                    return result
            else:
                self.log_test("GET /api/technician/TECH-001/daily-tasks", False, 
                            f"❌ Missing required sections: {missing_sections}")
                return None
        else:
            self.log_test("GET /api/technician/TECH-001/daily-tasks", False, 
                        f"❌ Request failed with status {response['status_code']}", response['data'])
            return None
    
    def test_update_assignment_status_specific(self, assignment_id: str):
        """Test PUT /api/technician/assignment/{id}/status with specific transitions"""
        print("\n=== TESTING ASSIGNMENT STATUS UPDATE WITH SPECIFIC TRANSITIONS ===")
        
        if not assignment_id:
            self.log_test("PUT /api/technician/assignment/{id}/status", False, 
                        "❌ No assignment ID available for testing")
            return False
        
        # Test status transitions as mentioned in review
        status_transitions = [
            ("ASSIGNED", "IN_PROGRESS"),
            ("IN_PROGRESS", "COMPLETED")
        ]
        
        success_count = 0
        
        for current_status, new_status in status_transitions:
            response = self.make_request('PUT', f'/technician/assignment/{assignment_id}/status?status={new_status}')
            if response['success']:
                result = response['data']
                
                if (result.get('success') == True and
                    result.get('assignment_id') == assignment_id and
                    result.get('new_status') == new_status):
                    
                    self.log_test(f"Status Update {current_status}→{new_status}", True, 
                                f"✅ Successfully updated assignment status to {new_status}")
                    success_count += 1
                else:
                    self.log_test(f"Status Update {current_status}→{new_status}", False, 
                                f"❌ Invalid response format: {result}")
            else:
                self.log_test(f"Status Update {current_status}→{new_status}", False, 
                            f"❌ Request failed with status {response['status_code']}", response['data'])
        
        # Test error handling with invalid assignment ID
        fake_assignment_id = "TASS-INVALID123"
        response = self.make_request('PUT', f'/technician/assignment/{fake_assignment_id}/status?status=COMPLETED')
        if not response['success'] and response['status_code'] == 404:
            self.log_test("Error Handling - Invalid Assignment", True, 
                        f"✅ Correctly returned 404 for invalid assignment ID")
            success_count += 1
        else:
            self.log_test("Error Handling - Invalid Assignment", False, 
                        f"❌ Should return 404 for invalid assignment ID")
        
        overall_success = success_count == 3  # 2 transitions + 1 error test
        self.log_test("PUT /api/technician/assignment/{id}/status", overall_success, 
                    f"✅ All status update tests passed" if overall_success else f"❌ {success_count}/3 tests passed")
        
        return overall_success
    
    def test_complete_flow(self):
        """Test the complete flow as described in review request"""
        print("\n=== TESTING COMPLETE FLOW: CREATE ASSIGNMENT → GET DAILY TASKS → UPDATE STATUS ===")
        
        # Step 1: Create assignment
        print("\n🔄 STEP 1: Creating assignment...")
        assignment_id = self.test_technician_assign_events_specific()
        
        # Step 2: Get daily tasks and verify hybrid structure
        print("\n🔄 STEP 2: Getting daily tasks and verifying hybrid structure...")
        daily_tasks = self.test_technician_daily_tasks_specific()
        
        # Step 3: Update assignment status
        print("\n🔄 STEP 3: Updating assignment status...")
        if assignment_id:
            status_update_success = self.test_update_assignment_status_specific(assignment_id)
        else:
            status_update_success = False
            self.log_test("Complete Flow", False, "❌ Cannot test status update without assignment ID")
        
        # Verify complete flow success
        flow_success = (assignment_id is not None and 
                       daily_tasks is not None and 
                       status_update_success)
        
        if flow_success:
            self.log_test("Complete Flow Test", True, 
                        "✅ Complete flow working: assignment creation → daily tasks → status update")
        else:
            self.log_test("Complete Flow Test", False, 
                        "❌ Complete flow failed at one or more steps")
        
        return flow_success
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 80)
        print("📊 TECHNICIAN MODE SPECIFIC TEST RESULTS SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   - {result['test']}: {result['message']}")
        
        print("=" * 80)
    
    def run_specific_tests(self):
        """Run the specific tests mentioned in the review request"""
        print("🔧 TESTING TECHNICIAN MODE IMPROVEMENTS - SPECIFIC REVIEW REQUEST")
        print(f"🔗 Testing against: {self.base_url}")
        print("🎯 Focus: Test specific endpoints with exact data from review")
        print("📋 Context: Agenda improvements with 'Enviar para Técnico' and hybrid system")
        print("=" * 80)
        
        print("\n📝 REVIEW REQUEST DETAILS:")
        print("- Técnico ID: TECH-001")
        print("- Data: 2025-09-13 (hoje)")
        print("- Assignment type: AGENDA")
        print("- Test complete flow: create assignment → get daily tasks → verify hybrid structure → update status")
        
        # Run the complete flow test
        success = self.test_complete_flow()
        
        # Print summary
        self.print_summary()
        
        return success

if __name__ == "__main__":
    tester = TechnicianModeSpecificTester()
    success = tester.run_specific_tests()
    sys.exit(0 if success else 1)