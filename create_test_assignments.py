#!/usr/bin/env python3
"""
Create test assignments to investigate the duplication issue
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://cleansync.preview.emergentagent.com/api"
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

def create_test_assignments():
    """Create test assignments to reproduce the duplication issue"""
    print("🔧 CREATING TEST ASSIGNMENTS TO REPRODUCE DUPLICATION ISSUE")
    print("=" * 60)
    
    today = datetime.now().strftime('%Y-%m-%d')
    technician_id = "TECH-001"
    
    # Get available items first
    print("1️⃣ Getting available items...")
    response = make_request('GET', '/budget-items/available-for-routes')
    if not response['success']:
        print(f"❌ Failed to get available items: {response['data']}")
        return False
    
    available_items = response['data'].get('available_items', [])
    print(f"   📦 Found {len(available_items)} available items")
    
    if len(available_items) < 3:
        print("⚠️  Not enough available items to create meaningful test assignments")
        return False
    
    # Create multiple assignments with different configurations to test duplication
    assignments_to_create = [
        {
            "route_id": "RTE-TEST001",
            "event_ids": [available_items[0]['budget_item_id']],  # Single event
            "technician_id": technician_id,
            "assigned_date": today,
            "assignment_type": "AGENDA",
            "status": "ASSIGNED"
        },
        {
            "route_id": "RTE-TEST002", 
            "event_ids": [available_items[0]['budget_item_id'], available_items[0]['budget_item_id']],  # Duplicate event_ids (potential issue)
            "technician_id": technician_id,
            "assigned_date": today,
            "assignment_type": "MANUAL",
            "status": "ASSIGNED"
        }
    ]
    
    # Add more assignments if we have enough items
    if len(available_items) >= 2:
        assignments_to_create.append({
            "route_id": "RTE-TEST003",
            "event_ids": [available_items[0]['budget_item_id'], available_items[1]['budget_item_id'] if len(available_items) > 1 else available_items[0]['budget_item_id']],  # Multiple different events
            "technician_id": technician_id,
            "assigned_date": today,
            "assignment_type": "STATUS_BASED",
            "status": "ASSIGNED"
        })
    
    print(f"\n2️⃣ Creating {len(assignments_to_create)} test assignments...")
    created_assignments = []
    
    for i, assignment_data in enumerate(assignments_to_create, 1):
        print(f"\n   Creating assignment {i}:")
        print(f"   📋 Route ID: {assignment_data['route_id']}")
        print(f"   🎯 Event IDs: {assignment_data['event_ids']} ({len(assignment_data['event_ids'])} events)")
        print(f"   📅 Date: {assignment_data['assigned_date']}")
        print(f"   🏷️  Type: {assignment_data['assignment_type']}")
        
        response = make_request('POST', '/technician/assign-events', assignment_data)
        if response['success']:
            result = response['data']
            assignment_id = result.get('assignment_id')
            created_assignments.append(assignment_id)
            print(f"   ✅ Created: {assignment_id}")
        else:
            print(f"   ❌ Failed: {response['data']}")
    
    print(f"\n3️⃣ Successfully created {len(created_assignments)} assignments:")
    for assignment_id in created_assignments:
        print(f"   - {assignment_id}")
    
    # Now test the daily-tasks endpoint to see if duplication occurs
    print(f"\n4️⃣ Testing daily-tasks endpoint after creating assignments...")
    response = make_request('GET', f'/technician/{technician_id}/daily-tasks?date={today}')
    if response['success']:
        daily_tasks = response['data']
        assignments = daily_tasks.get('assignments', [])
        status_items = daily_tasks.get('status_items', [])
        
        print(f"   📊 Results:")
        print(f"   📋 Assignments: {len(assignments)}")
        print(f"   📦 Status Items: {len(status_items)}")
        print(f"   🔢 Total status_items desencapsulados: {len(status_items)}")
        
        # Check for duplications
        status_item_ids = [item.get('id') for item in status_items if item.get('id')]
        assignment_ids_in_status_items = [item.get('assignment_id') for item in status_items if item.get('assignment_id')]
        
        duplicate_item_ids = []
        seen_ids = set()
        for item_id in status_item_ids:
            if item_id in seen_ids:
                duplicate_item_ids.append(item_id)
            seen_ids.add(item_id)
        
        duplicate_assignment_ids = []
        assignment_counts = {}
        for assignment_id in assignment_ids_in_status_items:
            assignment_counts[assignment_id] = assignment_counts.get(assignment_id, 0) + 1
        duplicate_assignment_ids = [aid for aid, count in assignment_counts.items() if count > 1]
        
        print(f"\n   🔍 Duplication Analysis:")
        print(f"   ❌ Duplicate item IDs: {duplicate_item_ids}")
        print(f"   ❌ Duplicate assignment IDs: {duplicate_assignment_ids}")
        
        if duplicate_item_ids or duplicate_assignment_ids:
            print(f"   🚨 DUPLICATION ISSUE REPRODUCED!")
            
            # Show detailed status_items
            print(f"\n   📦 Detailed status_items:")
            for i, item in enumerate(status_items, 1):
                print(f"      {i}. ID: {item.get('id')}")
                print(f"         Assignment ID: {item.get('assignment_id')}")
                print(f"         Cliente: {item.get('client_name', 'N/A')}")
                print(f"         Serviço: {item.get('service_name', 'N/A')}")
                print()
        else:
            print(f"   ✅ No duplication found")
        
        return len(status_items) >= 7 or len(duplicate_item_ids) > 0 or len(duplicate_assignment_ids) > 0
    else:
        print(f"   ❌ Failed to get daily tasks: {response['data']}")
        return False

if __name__ == "__main__":
    success = create_test_assignments()
    if success:
        print("\n🎯 TEST ASSIGNMENTS CREATED - DUPLICATION ISSUE MAY BE REPRODUCED")
    else:
        print("\n⚠️  TEST ASSIGNMENTS CREATED BUT NO DUPLICATION DETECTED")