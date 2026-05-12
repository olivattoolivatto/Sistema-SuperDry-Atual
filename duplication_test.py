#!/usr/bin/env python3
"""
INVESTIGAÇÃO URGENTE - PROBLEMAS DE DUPLICAÇÃO E INCONSISTÊNCIA DE DADOS

PROBLEMAS REPORTADOS:
1. SERVTEC (Agenda): Mostra 7 eventos
2. Modo Rua: Mostra apenas 1 evento (deveria ser pelo menos 3)
3. Console.log mostra: "Total status_items desencapsulados: 7"
4. ERRO React: Keys duplicadas `TASS-ab148306` e `TASS-99f7fc9e`

INVESTIGAÇÃO NECESSÁRIA:
1. Verificar quantos assignments existem realmente para TECH-001
2. Listar todos os assignment_ids únicos e verificar duplicações
3. Testar GET /api/technician/TECH-001/daily-tasks para hoje e verificar:
   - Quantos status_items retorna
   - Se há assignment_ids duplicados nos status_items
   - Se há inconsistências na lógica de desencapsulamento
4. Verificar se um assignment com múltiplos event_ids está gerando múltiplos status_items com mesmo assignment_id
5. Analisar por que o Modo Rua não está processando todos os itens
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://superdry-laundry.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class DuplicationInvestigator:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.test_results = []
    
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
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("📊 INVESTIGAÇÃO SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "No tests run")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   - {result['test']}: {result['message']}")
        
        print("=" * 80)
    
    def investigate_duplication_issues(self):
        """
        Main investigation function for duplication and inconsistency issues
        """
        print("\n" + "=" * 80)
        print("🚨 INVESTIGAÇÃO URGENTE - PROBLEMAS DE DUPLICAÇÃO E INCONSISTÊNCIA DE DADOS")
        print("=" * 80)
        print("PROBLEMAS REPORTADOS:")
        print("1. SERVTEC (Agenda): Mostra 7 eventos")
        print("2. Modo Rua: Mostra apenas 1 evento (deveria ser pelo menos 3)")
        print("3. Console.log mostra: 'Total status_items desencapsulados: 7'")
        print("4. ERRO React: Keys duplicadas `TASS-ab148306` e `TASS-99f7fc9e`")
        print("=" * 80)
        
        today = datetime.now().strftime('%Y-%m-%d')
        technician_id = "TECH-001"
        
        # STEP 1: Verificar quantos assignments existem para TECH-001
        print(f"\n1️⃣ VERIFICANDO ASSIGNMENTS EXISTENTES PARA {technician_id}:")
        print("-" * 60)
        
        # Test multiple dates to find assignments
        test_dates = [today, "2025-01-15", "2025-01-16", "2025-01-17", "2025-09-14", "2025-09-15"]
        all_assignments = []
        assignment_ids_found = set()
        
        for test_date in test_dates:
            print(f"🔍 Testando data: {test_date}")
            
            response = self.make_request('GET', f'/technician/{technician_id}/daily-tasks?date={test_date}')
            if response['success']:
                daily_tasks = response['data']
                assignments = daily_tasks.get('assignments', [])
                
                print(f"   📋 Assignments encontrados: {len(assignments)}")
                
                for assignment in assignments:
                    assignment_id = assignment.get('id')
                    event_ids = assignment.get('event_ids', [])
                    status = assignment.get('status')
                    assignment_type = assignment.get('assignment_type')
                    
                    if assignment_id:
                        assignment_ids_found.add(assignment_id)
                        all_assignments.append({
                            'date': test_date,
                            'id': assignment_id,
                            'event_ids': event_ids,
                            'event_count': len(event_ids),
                            'status': status,
                            'type': assignment_type
                        })
                        
                        print(f"      - {assignment_id}: {len(event_ids)} event_ids, status: {status}")
            else:
                print(f"   ❌ Erro ao buscar data {test_date}: {response['data']}")
        
        print(f"\n📊 RESUMO DOS ASSIGNMENTS ENCONTRADOS:")
        print(f"   🔢 Total de assignment_ids únicos: {len(assignment_ids_found)}")
        print(f"   📋 Total de registros de assignments: {len(all_assignments)}")
        print(f"   📅 Datas testadas: {len(test_dates)}")
        
        if assignment_ids_found:
            print(f"   🆔 Assignment IDs encontrados: {sorted(list(assignment_ids_found))}")
        
        self.log_test("Assignment Investigation", True, 
                    f"Found {len(assignment_ids_found)} unique assignment_ids across {len(test_dates)} dates")
        
        # STEP 2: Testar GET /api/technician/TECH-001/daily-tasks para hoje especificamente
        print(f"\n2️⃣ TESTANDO DAILY-TASKS PARA HOJE ({today}):")
        print("-" * 50)
        
        response = self.make_request('GET', f'/technician/{technician_id}/daily-tasks?date={today}')
        if not response['success']:
            self.log_test("Daily Tasks Today", False, 
                        f"Failed to get daily tasks for today ({today})", response['data'])
            return False
        
        daily_tasks_today = response['data']
        assignments_today = daily_tasks_today.get('assignments', [])
        status_items_today = daily_tasks_today.get('status_items', [])
        agenda_events_today = daily_tasks_today.get('agenda_events', [])
        
        print(f"📊 DADOS PARA HOJE ({today}):")
        print(f"   📋 Assignments: {len(assignments_today)}")
        print(f"   📦 Status Items: {len(status_items_today)}")
        print(f"   📅 Agenda Events: {len(agenda_events_today)}")
        print(f"   🔢 Total status_items desencapsulados: {len(status_items_today)}")
        
        # Show detailed status_items for analysis
        if status_items_today:
            print(f"\n📦 DETALHES DOS STATUS_ITEMS ENCONTRADOS:")
            for i, item in enumerate(status_items_today, 1):
                item_id = item.get('id')
                assignment_id = item.get('assignment_id')
                client_name = item.get('client_name', 'N/A')
                service_name = item.get('service_name', 'N/A')
                status = item.get('status', 'N/A')
                
                print(f"   {i:2d}. ID: {item_id}")
                print(f"       Assignment ID: {assignment_id}")
                print(f"       Cliente: {client_name}")
                print(f"       Serviço: {service_name}")
                print(f"       Status: {status}")
                print()
        
        # STEP 3: Verificar duplicações nos status_items
        print(f"\n3️⃣ VERIFICANDO DUPLICAÇÕES NOS STATUS_ITEMS:")
        print("-" * 50)
        
        status_item_ids = []
        assignment_ids_in_status_items = []
        duplicate_keys = []
        
        for item in status_items_today:
            item_id = item.get('id')
            assignment_id = item.get('assignment_id')
            
            if item_id:
                if item_id in status_item_ids:
                    duplicate_keys.append(item_id)
                status_item_ids.append(item_id)
            
            if assignment_id:
                assignment_ids_in_status_items.append(assignment_id)
        
        # Count assignment_id occurrences
        assignment_id_counts = {}
        for assignment_id in assignment_ids_in_status_items:
            assignment_id_counts[assignment_id] = assignment_id_counts.get(assignment_id, 0) + 1
        
        duplicate_assignment_ids = {aid: count for aid, count in assignment_id_counts.items() if count > 1}
        
        print(f"📊 ANÁLISE DE DUPLICAÇÕES:")
        print(f"   🆔 Total de item IDs: {len(status_item_ids)}")
        print(f"   🔄 Item IDs únicos: {len(set(status_item_ids))}")
        print(f"   ❌ Keys duplicadas encontradas: {len(duplicate_keys)}")
        if duplicate_keys:
            print(f"      Duplicadas: {duplicate_keys}")
        
        print(f"   📋 Assignment IDs nos status_items: {len(assignment_ids_in_status_items)}")
        print(f"   🔄 Assignment IDs únicos: {len(set(assignment_ids_in_status_items))}")
        print(f"   ❌ Assignment IDs duplicados: {len(duplicate_assignment_ids)}")
        if duplicate_assignment_ids:
            print(f"      Duplicados: {duplicate_assignment_ids}")
        
        # Check for the specific duplicate keys mentioned in the issue
        reported_duplicates = ['TASS-ab148306', 'TASS-99f7fc9e']
        found_reported_duplicates = [key for key in reported_duplicates if key in duplicate_keys]
        
        if found_reported_duplicates:
            print(f"   🚨 DUPLICATAS REPORTADAS CONFIRMADAS: {found_reported_duplicates}")
            self.log_test("Reported Duplicates Found", False, 
                        f"Found reported duplicate keys: {found_reported_duplicates}")
        else:
            print(f"   ✅ Duplicatas reportadas não encontradas hoje")
            self.log_test("Reported Duplicates Found", True, 
                        f"Reported duplicate keys not found in today's data")
        
        # STEP 4: Verificar se assignments com múltiplos event_ids geram múltiplos status_items
        print(f"\n4️⃣ VERIFICANDO DESENCAPSULAMENTO DE ASSIGNMENTS:")
        print("-" * 55)
        
        multi_event_assignments = []
        desencapsulation_issues = []
        
        for assignment in assignments_today:
            assignment_id = assignment.get('id')
            event_ids = assignment.get('event_ids', [])
            
            if len(event_ids) > 1:
                multi_event_assignments.append({
                    'id': assignment_id,
                    'event_ids': event_ids,
                    'event_count': len(event_ids)
                })
                
                # Count how many status_items have this assignment_id
                status_items_for_assignment = [
                    item for item in status_items_today 
                    if item.get('assignment_id') == assignment_id
                ]
                
                print(f"📋 Assignment {assignment_id}:")
                print(f"   🎯 Event IDs: {event_ids} ({len(event_ids)} eventos)")
                print(f"   📦 Status items gerados: {len(status_items_for_assignment)}")
                
                if len(status_items_for_assignment) != len(event_ids):
                    desencapsulation_issues.append({
                        'assignment_id': assignment_id,
                        'expected_items': len(event_ids),
                        'actual_items': len(status_items_for_assignment),
                        'event_ids': event_ids
                    })
                    print(f"   ❌ PROBLEMA: Esperados {len(event_ids)} status_items, encontrados {len(status_items_for_assignment)}")
                else:
                    print(f"   ✅ OK: Desencapsulamento correto")
                
                # Show details of generated status_items
                for i, status_item in enumerate(status_items_for_assignment, 1):
                    item_id = status_item.get('id')
                    client_name = status_item.get('client_name', 'N/A')
                    service_name = status_item.get('service_name', 'N/A')
                    print(f"      {i}. {item_id} - {client_name} - {service_name}")
                print()
        
        print(f"📊 ANÁLISE DO DESENCAPSULAMENTO:")
        print(f"   📋 Assignments com múltiplos eventos: {len(multi_event_assignments)}")
        print(f"   ❌ Problemas de desencapsulamento: {len(desencapsulation_issues)}")
        
        if desencapsulation_issues:
            print(f"   🚨 PROBLEMAS ENCONTRADOS:")
            for issue in desencapsulation_issues:
                print(f"      - {issue['assignment_id']}: {issue['actual_items']}/{issue['expected_items']} items")
            
            self.log_test("Desencapsulation Issues", False, 
                        f"Found {len(desencapsulation_issues)} desencapsulation problems")
        else:
            self.log_test("Desencapsulation Issues", True, 
                        "No desencapsulation issues found")
        
        # STEP 5: Análise final e diagnóstico
        print(f"\n5️⃣ DIAGNÓSTICO FINAL:")
        print("-" * 30)
        
        print(f"🔍 RESUMO DA INVESTIGAÇÃO:")
        print(f"   📊 Status items encontrados hoje: {len(status_items_today)}")
        print(f"   📋 Assignments encontrados hoje: {len(assignments_today)}")
        print(f"   ❌ Keys duplicadas: {len(duplicate_keys)}")
        print(f"   🔄 Assignment IDs duplicados: {len(duplicate_assignment_ids)}")
        print(f"   ⚠️  Problemas de desencapsulamento: {len(desencapsulation_issues)}")
        
        # Determine if the reported issues are present
        issues_found = []
        if len(status_items_today) == 7:
            issues_found.append("✅ Confirmado: 7 status_items desencapsulados (conforme console.log)")
        else:
            issues_found.append(f"⚠️  Status items: {len(status_items_today)} (reportados: 7)")
        
        if duplicate_keys:
            issues_found.append(f"❌ Keys duplicadas encontradas: {duplicate_keys}")
        else:
            issues_found.append("✅ Nenhuma key duplicada encontrada hoje")
        
        if duplicate_assignment_ids:
            issues_found.append(f"❌ Assignment IDs duplicados: {duplicate_assignment_ids}")
        else:
            issues_found.append("✅ Nenhum assignment ID duplicado")
        
        print(f"\n🎯 CONCLUSÕES:")
        for issue in issues_found:
            print(f"   {issue}")
        
        # Recommendations
        print(f"\n💡 RECOMENDAÇÕES:")
        if duplicate_keys or duplicate_assignment_ids:
            print("   1. Verificar lógica de desencapsulamento no endpoint daily-tasks")
            print("   2. Garantir que cada status_item tenha ID único")
            print("   3. Verificar se assignments não estão sendo processados múltiplas vezes")
            print("   4. Implementar validação de unicidade no frontend")
        else:
            print("   1. Sistema funcionando corretamente hoje")
            print("   2. Problema pode ser intermitente ou específico de certas datas")
            print("   3. Monitorar logs do frontend para identificar quando duplicatas ocorrem")
        
        # Final test result
        critical_issues = len(duplicate_keys) + len(duplicate_assignment_ids) + len(desencapsulation_issues)
        
        if critical_issues == 0:
            self.log_test("Duplication Investigation", True, 
                        f"No critical duplication issues found today - system functioning correctly")
            return True
        else:
            self.log_test("Duplication Investigation", False, 
                        f"Found {critical_issues} critical issues: {len(duplicate_keys)} duplicate keys, {len(duplicate_assignment_ids)} duplicate assignment_ids, {len(desencapsulation_issues)} desencapsulation problems")
            return False

if __name__ == "__main__":
    investigator = DuplicationInvestigator()
    
    print("🚨 STARTING URGENT DUPLICATION INVESTIGATION")
    print(f"🔗 Testing against: {BASE_URL}")
    print("=" * 80)
    
    # Run the investigation
    investigator.investigate_duplication_issues()
    
    # Print final summary
    investigator.print_summary()