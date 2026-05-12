#!/usr/bin/env python3
"""
Critical Investigation Script for Technician Mode Issues
Focus: Investigating the specific problems reported by the user
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://superdry-laundry.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class CriticalInvestigator:
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
    
    def investigate_critical_issues(self):
        """
        INVESTIGAÇÃO CRÍTICA DOS PROBLEMAS NO MODO TÉCNICO conforme reportado pelo usuário:
        
        PROBLEMAS REPORTADOS:
        1. Dois tipos diferentes de agendamentos/serviços aparecendo no modo rua com formatos completamente diferentes
        2. Itens duplicados (2 são réplicas)
        3. Filtro "Apenas hoje" mostra tipos diferentes de dados
        4. Erro 404 ao tentar excluir: "PUT /technician/assignment/TASS-befa2095-1/status" retorna 404 "Assignment not found"
        5. "Serviços enviados ao técnico" na Agenda está vazio
        """
        print("\n" + "=" * 80)
        print("🚨 INVESTIGAÇÃO CRÍTICA DOS PROBLEMAS NO MODO TÉCNICO")
        print("=" * 80)
        print("PROBLEMAS REPORTADOS PELO USUÁRIO:")
        print("1. Dois tipos diferentes de agendamentos/serviços aparecendo no modo rua")
        print("2. Itens duplicados (2 são réplicas)")
        print("3. Filtro 'Apenas hoje' mostra tipos diferentes de dados")
        print("4. Erro 404 ao tentar excluir: PUT /technician/assignment/TASS-befa2095-1/status")
        print("5. 'Serviços enviados ao técnico' na Agenda está vazio")
        print("=" * 80)
        
        # INVESTIGAÇÃO 1: Verificar se assignment TASS-befa2095-1 existe
        print("\n1️⃣ VERIFICANDO SE ASSIGNMENT TASS-befa2095-1 EXISTE:")
        print("-" * 60)
        
        specific_assignment_id = "TASS-befa2095-1"
        response = self.make_request('PUT', f'/technician/assignment/{specific_assignment_id}/status?status=CANCELLED')
        
        if response['status_code'] == 404:
            print(f"❌ CONFIRMADO: Assignment {specific_assignment_id} NÃO EXISTE (404 Error)")
            self.log_test("Assignment TASS-befa2095-1 Exists", False, 
                        f"Assignment {specific_assignment_id} not found - returns 404 as reported")
        else:
            print(f"✅ Assignment {specific_assignment_id} existe (Status: {response['status_code']})")
            self.log_test("Assignment TASS-befa2095-1 Exists", True, 
                        f"Assignment {specific_assignment_id} found")
        
        # INVESTIGAÇÃO 2: Listar todos assignments existentes para TECH-001
        print("\n2️⃣ LISTANDO TODOS ASSIGNMENTS PARA TECH-001:")
        print("-" * 50)
        
        # Test multiple dates to find assignments
        test_dates = ["2025-09-20", "2025-09-19", "2025-09-18", "2025-09-17", "2025-09-16", "2025-09-15"]
        all_assignments = []
        
        for test_date in test_dates:
            response = self.make_request('GET', f'/technician/TECH-001/daily-tasks?date={test_date}')
            if response['success']:
                daily_tasks = response['data']
                assignments = daily_tasks.get('assignments', [])
                
                if assignments:
                    print(f"📅 {test_date}: {len(assignments)} assignments encontrados")
                    for assignment in assignments:
                        assignment_info = {
                            'id': assignment.get('id'),
                            'date': test_date,
                            'route_id': assignment.get('route_id'),
                            'event_ids': assignment.get('event_ids', []),
                            'status': assignment.get('status'),
                            'type': assignment.get('assignment_type')
                        }
                        all_assignments.append(assignment_info)
                        print(f"   - {assignment.get('id')} (Status: {assignment.get('status')})")
                else:
                    print(f"📅 {test_date}: 0 assignments")
            else:
                print(f"📅 {test_date}: Erro ao buscar assignments")
        
        print(f"\n📊 TOTAL DE ASSIGNMENTS ENCONTRADOS: {len(all_assignments)}")
        
        if all_assignments:
            self.log_test("List All TECH-001 Assignments", True, 
                        f"Found {len(all_assignments)} assignments across {len(test_dates)} dates")
        else:
            self.log_test("List All TECH-001 Assignments", False, 
                        "No assignments found for TECH-001 in any tested date")
        
        # INVESTIGAÇÃO 3: Verificar budget_items com status RETIRAR, EXECUTAR_NO_LOCAL, ENTREGAR
        print("\n3️⃣ VERIFICANDO BUDGET_ITEMS COM STATUS DE RUA:")
        print("-" * 50)
        
        response = self.make_request('GET', '/budget-items/available-for-routes')
        duplicates_found = 0
        if response['success']:
            available_items = response['data'].get('available_items', [])
            
            # Categorizar por status
            status_counts = {}
            duplicate_analysis = {}
            
            for item in available_items:
                status = item.get('status')
                client_name = item.get('client_name')
                service_name = item.get('service_name')
                budget_id = item.get('budget_id')
                
                # Count by status
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Check for potential duplicates (same client + service)
                duplicate_key = f"{client_name}_{service_name}"
                if duplicate_key not in duplicate_analysis:
                    duplicate_analysis[duplicate_key] = []
                duplicate_analysis[duplicate_key].append({
                    'budget_item_id': item.get('budget_item_id'),
                    'budget_id': budget_id,
                    'status': status
                })
            
            print(f"📊 DISTRIBUIÇÃO POR STATUS:")
            for status, count in status_counts.items():
                print(f"   {status}: {count} itens")
            
            print(f"\n🔍 ANÁLISE DE DUPLICAÇÕES:")
            for key, items in duplicate_analysis.items():
                if len(items) > 1:
                    duplicates_found += 1
                    print(f"   ⚠️  POSSÍVEL DUPLICAÇÃO: {key}")
                    for item in items:
                        print(f"      - {item['budget_item_id']} ({item['budget_id']}) - Status: {item['status']}")
            
            if duplicates_found > 0:
                print(f"\n❌ ENCONTRADAS {duplicates_found} POSSÍVEIS DUPLICAÇÕES")
                self.log_test("Budget Items Duplication Check", False, 
                            f"Found {duplicates_found} potential duplications in available items")
            else:
                print(f"\n✅ NENHUMA DUPLICAÇÃO ENCONTRADA")
                self.log_test("Budget Items Duplication Check", True, 
                            "No duplications found in available items")
            
            self.log_test("Budget Items Status Analysis", True, 
                        f"Analyzed {len(available_items)} items: {dict(status_counts)}")
        else:
            self.log_test("Budget Items Status Analysis", False, 
                        "Failed to get available items for analysis")
        
        # INVESTIGAÇÃO 4: Testar GET /api/technician/TECH-001/daily-tasks para hoje (20/09/2025)
        print("\n4️⃣ TESTANDO DAILY-TASKS PARA HOJE (20/09/2025):")
        print("-" * 55)
        
        today_date = "2025-09-20"
        response = self.make_request('GET', f'/technician/TECH-001/daily-tasks?date={today_date}')
        
        assignments = []
        status_items = []
        if response['success']:
            daily_tasks = response['data']
            assignments = daily_tasks.get('assignments', [])
            status_items = daily_tasks.get('status_items', [])
            agenda_events = daily_tasks.get('agenda_events', [])
            
            print(f"📊 DADOS RETORNADOS PARA {today_date}:")
            print(f"   📋 Assignments: {len(assignments)} itens")
            print(f"   📦 Status Items: {len(status_items)} itens")
            print(f"   📅 Agenda Events: {len(agenda_events)} itens")
            
            # Analyze data types
            print(f"\n🔍 ANÁLISE DOS TIPOS DE DADOS:")
            
            if assignments:
                print(f"   📋 ASSIGNMENTS (Tipo 1 - Manual da Agenda):")
                for i, assignment in enumerate(assignments, 1):
                    print(f"      {i}. {assignment.get('id')} - Route: {assignment.get('route_id')} - Events: {len(assignment.get('event_ids', []))}")
            
            if status_items:
                print(f"   📦 STATUS_ITEMS (Tipo 2 - Automático por Status):")
                for i, item in enumerate(status_items, 1):
                    print(f"      {i}. {item.get('id')} - Cliente: {item.get('client_name')} - Status: {item.get('status')}")
            
            # Check for different formats (the reported issue)
            total_items = len(assignments) + len(status_items)
            if len(assignments) > 0 and len(status_items) > 0:
                print(f"\n⚠️  CONFIRMADO: DOIS TIPOS DIFERENTES DE DADOS RETORNADOS")
                print(f"   - Assignments (formato agenda): {len(assignments)} itens")
                print(f"   - Status Items (formato automático): {len(status_items)} itens")
                self.log_test("Different Data Types Issue", True, 
                            f"Confirmed: Two different data types returned - {len(assignments)} assignments + {len(status_items)} status_items")
            else:
                print(f"\n✅ APENAS UM TIPO DE DADOS RETORNADO")
                self.log_test("Different Data Types Issue", False, 
                            f"Only one data type returned - not reproducing the reported issue")
            
            self.log_test("Daily Tasks Today Test", True, 
                        f"Successfully retrieved daily tasks for {today_date}: {total_items} total items")
        else:
            self.log_test("Daily Tasks Today Test", False, 
                        f"Failed to get daily tasks for {today_date}", response['data'])
        
        # INVESTIGAÇÃO 5: Verificar assignments órfãos ou inconsistências
        print("\n5️⃣ VERIFICANDO ASSIGNMENTS ÓRFÃOS E INCONSISTÊNCIAS:")
        print("-" * 60)
        
        orphaned_assignments = []
        invalid_event_ids = []
        
        for assignment in all_assignments:
            assignment_id = assignment['id']
            event_ids = assignment.get('event_ids', [])
            
            # Check if event_ids are valid (should be budget_item_ids starting with ITM-)
            for event_id in event_ids:
                if not event_id.startswith('ITM-'):
                    invalid_event_ids.append({
                        'assignment_id': assignment_id,
                        'invalid_event_id': event_id,
                        'date': assignment['date']
                    })
        
        if invalid_event_ids:
            print(f"❌ ENCONTRADOS {len(invalid_event_ids)} EVENT_IDS INVÁLIDOS:")
            for invalid in invalid_event_ids:
                print(f"   - Assignment {invalid['assignment_id']}: Event ID '{invalid['invalid_event_id']}' (deveria ser ITM-XXXXXXX)")
            
            self.log_test("Assignment Event IDs Validation", False, 
                        f"Found {len(invalid_event_ids)} invalid event_ids in assignments")
        else:
            print(f"✅ TODOS OS EVENT_IDS SÃO VÁLIDOS")
            self.log_test("Assignment Event IDs Validation", True, 
                        "All event_ids in assignments are valid")
        
        # RESULTADO FINAL DA INVESTIGAÇÃO
        print("\n" + "=" * 80)
        print("📋 RESUMO DA INVESTIGAÇÃO CRÍTICA:")
        print("=" * 80)
        
        issues_found = []
        
        if response['status_code'] == 404:  # TASS-befa2095-1 not found
            issues_found.append("Assignment TASS-befa2095-1 não existe (404 Error)")
        
        if duplicates_found > 0:
            issues_found.append(f"{duplicates_found} possíveis duplicações encontradas")
        
        if len(assignments) > 0 and len(status_items) > 0:
            issues_found.append("Dois tipos diferentes de dados confirmados")
        
        if invalid_event_ids:
            issues_found.append(f"{len(invalid_event_ids)} event_ids inválidos encontrados")
        
        if len(all_assignments) == 0:
            issues_found.append("Nenhum assignment encontrado para TECH-001")
        
        if issues_found:
            print("❌ PROBLEMAS IDENTIFICADOS:")
            for i, issue in enumerate(issues_found, 1):
                print(f"   {i}. {issue}")
            
            self.log_test("Critical Technician Mode Investigation", False, 
                        f"Investigation completed - {len(issues_found)} issues identified")
        else:
            print("✅ NENHUM PROBLEMA CRÍTICO IDENTIFICADO")
            self.log_test("Critical Technician Mode Investigation", True, 
                        "Investigation completed - no critical issues found")
        
        return len(issues_found) == 0
    
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

if __name__ == "__main__":
    investigator = CriticalInvestigator()
    investigator.investigate_critical_issues()
    investigator.print_summary()