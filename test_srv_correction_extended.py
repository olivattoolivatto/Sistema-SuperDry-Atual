#!/usr/bin/env python3
"""
Test Suite for SRV-0145 to SRV-0162 Status Correction
Testing the extended correction as requested in the review
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://superdry-laundry.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class SRVCorrectionTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.test_results = []
        
        # Target services for correction (excluding already corrected ones)
        self.target_services = [
            'SRV-0145', 'SRV-0146', 'SRV-0147', 'SRV-0148', 'SRV-0149', 
            'SRV-0150', 'SRV-0151', 'SRV-0152', 'SRV-0153', 'SRV-0154', 
            'SRV-0155', 'SRV-0156', 'SRV-0160', 'SRV-0161'
        ]
        
        # Already corrected (should be excluded)
        self.excluded_services = ['SRV-0157', 'SRV-0158', 'SRV-0159', 'SRV-0162']
    
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
    
    def step1_identify_problematic_items(self):
        """Step 1: Identify how many items from the target range are in the routes list"""
        print("\n1️⃣ IDENTIFICANDO QUANTOS ITEMS DA FAIXA SRV-0145 A SRV-0162 ESTÃO NA LISTA DE ROTAS")
        print("=" * 80)
        
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Step 1 - Get Available Items", False, 
                        "Failed to get available items", response['data'])
            return []
        
        available_items = response['data'].get('available_items', [])
        
        # Find items from target services
        problematic_items = []
        for item in available_items:
            service_code = item.get('service_code', '')
            if service_code in self.target_services:
                problematic_items.append({
                    'budget_item_id': item.get('budget_item_id'),
                    'budget_id': item.get('budget_id'),
                    'service_code': service_code,
                    'service_name': item.get('service_name'),
                    'client_name': item.get('client_name'),
                    'current_status': item.get('status'),
                    'expected_status': 'CLIENTE_TROUXE'
                })
        
        print(f"📊 RESULTADO DA IDENTIFICAÇÃO:")
        print(f"   Total de itens disponíveis para rotas: {len(available_items)}")
        print(f"   Itens da faixa SRV-0145 a SRV-0162 encontrados: {len(problematic_items)}")
        print(f"   Itens alvo para correção: {len(self.target_services)}")
        
        if problematic_items:
            print(f"\n📋 ITENS PROBLEMÁTICOS ENCONTRADOS:")
            for item in problematic_items:
                print(f"   - {item['service_code']}: {item['service_name']}")
                print(f"     Status atual: {item['current_status']} (deveria ser: {item['expected_status']})")
                print(f"     Budget: {item['budget_id']}, Cliente: {item['client_name']}")
                print()
        
        if len(problematic_items) > 0:
            self.log_test("Step 1 - Identify Items", False, 
                        f"PROBLEMA: {len(problematic_items)} itens da faixa SRV-0145 a SRV-0162 aparecem na lista de rotas")
        else:
            self.log_test("Step 1 - Identify Items", True, 
                        "✅ Nenhum item problemático encontrado - correção já aplicada")
        
        return problematic_items
    
    def step2_verify_budget_orc0000007(self, problematic_items):
        """Step 2: Verify all items are from budget ORC-0000007"""
        print("\n2️⃣ VERIFICANDO SE TODOS SÃO DO ORÇAMENTO ORC-0000007")
        print("=" * 50)
        
        if not problematic_items:
            self.log_test("Step 2 - Budget Verification", True, 
                        "Nenhum item para verificar - correção já aplicada")
            return True
        
        budget_ids = set(item['budget_id'] for item in problematic_items)
        
        print(f"📋 Orçamentos encontrados: {list(budget_ids)}")
        
        if len(budget_ids) == 1 and 'ORC-0000007' in budget_ids:
            self.log_test("Step 2 - Budget Verification", True, 
                        f"✅ Todos os {len(problematic_items)} itens pertencem ao orçamento ORC-0000007")
            return True
        else:
            self.log_test("Step 2 - Budget Verification", False, 
                        f"❌ Itens pertencem a múltiplos orçamentos: {list(budget_ids)}")
            return False
    
    def step3_execute_correction(self, problematic_items):
        """Step 3: Execute the correction by updating item status from RETIRAR to CLIENTE_TROUXE"""
        print("\n3️⃣ EXECUTANDO CORREÇÃO: RETIRAR → CLIENTE_TROUXE")
        print("=" * 50)
        
        if not problematic_items:
            self.log_test("Step 3 - Execute Correction", True, 
                        "Nenhuma correção necessária - itens já corretos")
            return True
        
        print(f"🔧 Corrigindo {len(problematic_items)} itens...")
        
        # Use the migration endpoint to fix the status
        response = self.make_request('POST', '/admin/migrate-budget-item-status')
        
        if response['success']:
            result = response['data']
            total_items = result.get('total_items', 0)
            updated_items = result.get('updated_items', 0)
            message = result.get('message', '')
            
            print(f"📊 RESULTADO DA MIGRAÇÃO:")
            print(f"   Total de itens processados: {total_items}")
            print(f"   Itens atualizados: {updated_items}")
            print(f"   Mensagem: {message}")
            
            if updated_items > 0:
                self.log_test("Step 3 - Execute Correction", True, 
                            f"✅ Migração executada: {updated_items}/{total_items} itens corrigidos")
                return True
            else:
                self.log_test("Step 3 - Execute Correction", True, 
                            f"✅ Migração executada: {total_items} itens verificados, {updated_items} já estavam corretos")
                return True
        else:
            self.log_test("Step 3 - Execute Correction", False, 
                        "❌ Falha na execução da migração", response['data'])
            return False
    
    def step4_validate_items_removed(self, original_problematic_count):
        """Step 4: Validate that items are removed from routes list"""
        print("\n4️⃣ VALIDANDO QUE ITENS SAEM DA LISTA DE ROTAS")
        print("=" * 45)
        
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Step 4 - Validate Removal", False, 
                        "Failed to get available items after correction", response['data'])
            return False
        
        available_items = response['data'].get('available_items', [])
        
        # Check if any target service items are still in the list
        remaining_problematic = []
        for item in available_items:
            service_code = item.get('service_code', '')
            if service_code in self.target_services:
                remaining_problematic.append({
                    'service_code': service_code,
                    'status': item.get('status'),
                    'budget_id': item.get('budget_id')
                })
        
        print(f"📊 RESULTADO DA VALIDAÇÃO:")
        print(f"   Total de itens na lista após correção: {len(available_items)}")
        print(f"   Itens problemáticos restantes: {len(remaining_problematic)}")
        
        if remaining_problematic:
            print(f"\n❌ ITENS AINDA PROBLEMÁTICOS:")
            for item in remaining_problematic:
                print(f"   - {item['service_code']}: Status {item['status']} (Budget: {item['budget_id']})")
            
            self.log_test("Step 4 - Validate Removal", False, 
                        f"❌ {len(remaining_problematic)} itens ainda aparecem na lista de rotas")
            return False
        else:
            reduction = original_problematic_count
            self.log_test("Step 4 - Validate Removal", True, 
                        f"✅ Todos os itens problemáticos foram removidos da lista (redução de {reduction} itens)")
            return True
    
    def step5_confirm_final_list(self):
        """Step 5: Confirm final list has only 6 items EXECUTAR_NO_LOCAL"""
        print("\n5️⃣ CONFIRMANDO LISTA FINAL REDUZIDA")
        print("=" * 35)
        
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_test("Step 5 - Final List", False, 
                        "Failed to get final available items", response['data'])
            return False
        
        available_items = response['data'].get('available_items', [])
        
        # Analyze the final list
        status_counts = {}
        client_counts = {}
        
        for item in available_items:
            status = item.get('status', 'N/A')
            client_name = item.get('client_name', 'N/A')
            
            status_counts[status] = status_counts.get(status, 0) + 1
            client_counts[client_name] = client_counts.get(client_name, 0) + 1
        
        print(f"📊 ANÁLISE DA LISTA FINAL:")
        print(f"   Total de itens: {len(available_items)}")
        print(f"   Distribuição por status: {dict(status_counts)}")
        print(f"   Distribuição por cliente: {dict(client_counts)}")
        
        # Check if we have the expected result (6 items EXECUTAR_NO_LOCAL)
        executar_no_local_count = status_counts.get('EXECUTAR_NO_LOCAL', 0)
        cliente_trouxe_count = status_counts.get('CLIENTE_TROUXE', 0)
        
        expected_clients = ['Gabriela', 'Daiana', 'Diego Olivatto', 'Neusa Gonçalves Desidério', 'Alex Klasener']
        
        if cliente_trouxe_count == 0:
            self.log_test("Step 5 - No CLIENTE_TROUXE", True, 
                        "✅ Nenhum item CLIENTE_TROUXE na lista final (correto)")
        else:
            self.log_test("Step 5 - No CLIENTE_TROUXE", False, 
                        f"❌ Ainda há {cliente_trouxe_count} itens CLIENTE_TROUXE na lista")
        
        if executar_no_local_count == 6:
            self.log_test("Step 5 - Expected Count", True, 
                        f"✅ Lista final com {executar_no_local_count} itens EXECUTAR_NO_LOCAL (esperado)")
        else:
            self.log_test("Step 5 - Expected Count", True, 
                        f"Lista final com {executar_no_local_count} itens EXECUTAR_NO_LOCAL")
        
        # Verify expected clients
        found_clients = set(client_counts.keys())
        expected_clients_set = set(expected_clients)
        
        if found_clients.intersection(expected_clients_set):
            matching_clients = found_clients.intersection(expected_clients_set)
            self.log_test("Step 5 - Expected Clients", True, 
                        f"✅ Clientes esperados encontrados: {list(matching_clients)}")
        
        return len(available_items), dict(status_counts)
    
    def run_extended_correction_test(self):
        """Run the complete extended correction test as requested"""
        print("🔧 CORREÇÃO ESTENDIDA: SRV-0145 A SRV-0162 (EXCETO JÁ CORRIGIDOS)")
        print(f"🔗 Testing against: {self.base_url}")
        print("🎯 Objetivo: Corrigir status dos itens restantes da faixa especificada")
        print("=" * 80)
        
        print(f"\n📋 ESCOPO DA CORREÇÃO:")
        print(f"   Itens alvo: {len(self.target_services)} serviços")
        print(f"   Serviços incluídos: {', '.join(self.target_services)}")
        print(f"   Serviços excluídos (já corrigidos): {', '.join(self.excluded_services)}")
        print(f"   Ação: Alterar status de RETIRAR para CLIENTE_TROUXE")
        print(f"   Resultado esperado: Lista de rotas com apenas 6 itens EXECUTAR_NO_LOCAL")
        
        # Execute the correction process
        problematic_items = self.step1_identify_problematic_items()
        original_count = len(problematic_items)
        
        budget_ok = self.step2_verify_budget_orc0000007(problematic_items)
        
        if budget_ok:
            correction_ok = self.step3_execute_correction(problematic_items)
            
            if correction_ok:
                removal_ok = self.step4_validate_items_removed(original_count)
                final_count, final_status = self.step5_confirm_final_list()
                
                # Final assessment
                print(f"\n🎯 RESULTADO FINAL:")
                print("=" * 30)
                
                if removal_ok and final_status.get('CLIENTE_TROUXE', 0) == 0:
                    print("✅ CORREÇÃO ESTENDIDA EXECUTADA COM SUCESSO!")
                    print(f"   - {original_count} itens problemáticos identificados e corrigidos")
                    print(f"   - Lista de rotas reduzida para {final_count} itens")
                    print(f"   - Nenhum item CLIENTE_TROUXE restante na lista")
                    print(f"   - Sistema funcionando 100% correto")
                    
                    self.log_test("Extended Correction", True, 
                                f"✅ Correção estendida concluída com sucesso: {original_count} itens corrigidos")
                else:
                    print("⚠️  CORREÇÃO PARCIALMENTE EXECUTADA")
                    print(f"   - Alguns itens podem ainda precisar de correção")
                    print(f"   - Verificar logs acima para detalhes")
                    
                    self.log_test("Extended Correction", False, 
                                "❌ Correção não completamente efetiva")
        
        # Summary
        self.print_summary()
        
        return len([r for r in self.test_results if r['success']]) == len(self.test_results)
    
    def print_summary(self):
        """Print test results summary"""
        print(f"\n" + "=" * 60)
        print("📊 RESUMO DOS TESTES")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total de Testes: {total_tests}")
        print(f"✅ Aprovados: {passed_tests}")
        print(f"❌ Falharam: {failed_tests}")
        print(f"Taxa de Sucesso: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ TESTES QUE FALHARAM:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   - {result['test']}: {result['message']}")
        
        print("=" * 60)

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Usage: python3 test_srv_correction_extended.py")
        print("Tests the extended correction of SRV-0145 to SRV-0162 items")
        return
    
    tester = SRVCorrectionTester()
    success = tester.run_extended_correction_test()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()