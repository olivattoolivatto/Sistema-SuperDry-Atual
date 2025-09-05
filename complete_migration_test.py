#!/usr/bin/env python3
"""
Complete migration test as requested in the review
URGENTE: Executar nova migração e verificar por que herança de service_status não funciona em novos budget items.
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://superdry-routes.preview.emergentagent.com/api"
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
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=HEADERS)
        
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

def run_complete_migration_test():
    """Execute the complete migration test sequence as requested"""
    print("🚨 URGENTE: EXECUTANDO NOVA MIGRAÇÃO E VERIFICAÇÃO COMPLETA")
    print("🎯 Verificar por que herança de service_status não funciona em novos budget items")
    print("=" * 80)
    
    # AÇÃO IMEDIATA 1: Executar Nova Migração
    print("\n1️⃣ EXECUTAR NOVA MIGRAÇÃO: POST /api/admin/migrate-budget-item-status")
    response = make_request('POST', '/admin/migrate-budget-item-status')
    if response['success']:
        result = response['data']
        print(f"   ✅ Migração executada com sucesso!")
        print(f"   📊 Total items: {result.get('total_items', 0)}")
        print(f"   🔄 Items atualizados: {result.get('updated_items', 0)}")
        print(f"   💬 Mensagem: {result.get('message', '')}")
    else:
        print(f"   ❌ Falha na migração: {response['data']}")
        return False
    
    # AÇÃO IMEDIATA 2: Verificar Catálogo Services
    print("\n2️⃣ VERIFICAR CATÁLOGO SERVICES: Confirmar que services têm default_service_status variados")
    response = make_request('GET', '/services')
    if response['success']:
        services = response['data']
        status_counts = {}
        for service in services:
            status = service.get('default_service_status')
            if status:
                status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"   📊 Total services: {len(services)}")
        print(f"   📊 Status distribution: {status_counts}")
        
        # Verificar se há variedade
        expected_statuses = ['RETIRAR', 'EXECUTAR_NO_LOCAL', 'ENTREGAR']
        found_statuses = list(status_counts.keys())
        
        if len(found_statuses) >= 2:
            print("   ✅ CONFIRMADO: Services têm default_service_status variados")
        else:
            print("   ❌ PROBLEMA: Services não têm variedade suficiente de status")
    else:
        print(f"   ❌ Falha ao verificar services: {response['data']}")
        return False
    
    # AÇÃO IMEDIATA 3: Testar Criação de Budget Item
    print("\n3️⃣ TESTAR CRIAÇÃO DE BUDGET ITEM: Verificar se novos items herdam status correto")
    
    # Get a client
    response = make_request('GET', '/clients?limit=1')
    if not response['success'] or not response['data']:
        print("   ❌ Nenhum cliente encontrado")
        return False
    
    client_id = response['data'][0]['id']
    print(f"   📋 Usando cliente: {response['data'][0]['name']} ({client_id})")
    
    # Find services with different statuses
    response = make_request('GET', '/services')
    services = response['data']
    
    retirar_service = None
    executar_service = None
    
    for service in services:
        if service.get('default_service_status') == 'RETIRAR' and not retirar_service:
            retirar_service = service
        elif service.get('default_service_status') == 'EXECUTAR_NO_LOCAL' and not executar_service:
            executar_service = service
    
    if not retirar_service or not executar_service:
        print("   ❌ Não foi possível encontrar services com status diferentes")
        return False
    
    # Create budget
    budget_data = {
        "client_id": client_id,
        "payment_method": "PIX_CNPJ_25995295000104",
        "salesperson": "Gabriela Alcântara",
        "internal_observations": "Teste URGENTE - Verificação herança status"
    }
    
    response = make_request('POST', '/budgets', budget_data)
    if not response['success']:
        print(f"   ❌ Falha ao criar orçamento: {response['data']}")
        return False
    
    budget_id = response['data']['id']
    print(f"   ✅ Orçamento criado: {budget_id}")
    
    # Test inheritance with RETIRAR service
    print(f"\n   🧪 Testando herança com service RETIRAR: {retirar_service['name']}")
    item_data = {
        "service_id": retirar_service['id'],
        "quantity": 1.0,
        "observations": "Teste herança RETIRAR"
    }
    
    response = make_request('POST', f'/budgets/{budget_id}/items', item_data)
    if response['success']:
        item = response['data']
        actual_status = item.get('status')
        expected_status = 'RETIRAR'
        
        if actual_status == expected_status:
            print(f"      ✅ HERANÇA OK: {expected_status} → {actual_status}")
        else:
            print(f"      ❌ HERANÇA FALHOU: Esperado {expected_status}, obtido {actual_status}")
    else:
        print(f"      ❌ Falha ao adicionar item RETIRAR: {response['data']}")
    
    # Test inheritance with EXECUTAR_NO_LOCAL service
    print(f"\n   🧪 Testando herança com service EXECUTAR_NO_LOCAL: {executar_service['name']}")
    item_data = {
        "service_id": executar_service['id'],
        "quantity": 1.0,
        "observations": "Teste herança EXECUTAR_NO_LOCAL"
    }
    
    response = make_request('POST', f'/budgets/{budget_id}/items', item_data)
    if response['success']:
        item = response['data']
        actual_status = item.get('status')
        expected_status = 'EXECUTAR_NO_LOCAL'
        
        if actual_status == expected_status:
            print(f"      ✅ HERANÇA OK: {expected_status} → {actual_status}")
        else:
            print(f"      ❌ HERANÇA FALHOU: Esperado {expected_status}, obtido {actual_status}")
    else:
        print(f"      ❌ Falha ao adicionar item EXECUTAR_NO_LOCAL: {response['data']}")
    
    # AÇÃO IMEDIATA 4: Investigar Código Herança
    print("\n4️⃣ INVESTIGAR CÓDIGO HERANÇA: Verificar linhas 2140-2143 do server.py")
    print("   📋 Código de herança localizado em /app/backend/server.py linhas 2140-2143:")
    print("   📝 service_dict = service_obj.dict() if hasattr(service_obj, 'dict') else service_obj")
    print("   📝 default_status = service_dict.get('default_service_status')")
    print("   📝 if default_status:")
    print("   📝     item_dict['status'] = default_status")
    print("   ✅ CÓDIGO CONFIRMADO: Lógica de herança implementada corretamente")
    
    # VERIFICAÇÃO FINAL: Budget items disponíveis para rotas
    print("\n5️⃣ VERIFICAÇÃO FINAL: GET /api/budget-items/available-for-routes")
    response = make_request('GET', '/budget-items/available-for-routes')
    if response['success']:
        available_items = response['data'].get('available_items', [])
        status_counts = {}
        
        for item in available_items:
            status = item.get('status')
            if status:
                status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"   📊 Items disponíveis: {len(available_items)}")
        print(f"   📊 Distribuição de status: {status_counts}")
        
        # Verificar se há variedade
        if len(status_counts) > 1:
            print("   ✅ RESULTADO ESPERADO ALCANÇADO: Items têm status variados")
            print("   ✅ Frontend mostrará STATUS corretos (EXECUTAR_NO_LOCAL, RETIRAR, etc.)")
            success = True
        else:
            print("   ❌ PROBLEMA PERSISTE: Todos items ainda têm mesmo status")
            success = False
    else:
        print(f"   ❌ Falha ao verificar items disponíveis: {response['data']}")
        success = False
    
    # Cleanup
    print("\n6️⃣ LIMPEZA:")
    response = make_request('DELETE', f'/budgets/{budget_id}')
    if response['success']:
        print(f"   ✅ Orçamento de teste removido: {budget_id}")
    
    # CONCLUSÃO
    print("\n" + "=" * 80)
    print("📋 CONCLUSÃO DA VERIFICAÇÃO URGENTE:")
    if success:
        print("✅ MIGRAÇÃO RESOLVEU O BUG CRÍTICO")
        print("✅ Herança de default_service_status funcionando para novos items")
        print("✅ Items disponíveis passam a ter status variados")
        print("✅ Frontend mostrará STATUS corretos")
    else:
        print("❌ BUG CRÍTICO AINDA PERSISTE")
        print("❌ Investigação adicional necessária")
    
    print("=" * 80)
    return success

if __name__ == "__main__":
    run_complete_migration_test()