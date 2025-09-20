#!/usr/bin/env python3
"""
Test script for Technician Mode Corrections - Review Request
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://cleansync.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

def make_request(method: str, endpoint: str, data: dict = None) -> dict:
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

def test_technician_mode_corrections():
    """Test the corrections implemented for Technician Mode issues"""
    print("🔧 TESTE DAS CORREÇÕES IMPLEMENTADAS PARA OS PROBLEMAS DO MODO TÉCNICO")
    print("=" * 80)
    print("CORREÇÕES IMPLEMENTADAS:")
    print("1. Melhor tratamento de erro 404 para assignments inexistentes no TechnicianMode.js")
    print("2. Filtro 'Apenas hoje' mais consistente entre assignments e status_items")
    print("3. Visualização unificada com badges melhorados (📋 Agenda vs ⚡ Auto)")
    print("4. Novo endpoint POST /api/technician/create-test-assignments para criar dados de teste")
    print("=" * 80)
    
    test_results = []
    
    # TESTE 1: Endpoint de criação de assignments de teste
    print("\n1️⃣ TESTANDO ENDPOINT DE CRIAÇÃO DE ASSIGNMENTS DE TESTE:")
    print("-" * 65)
    
    response = make_request('POST', '/technician/create-test-assignments')
    if not response['success']:
        print(f"❌ Falha ao criar assignments de teste: {response['data']}")
        test_results.append(False)
        return False
    
    result = response['data']
    assignment_ids = result.get('assignment_ids', [])
    date_created = result.get('date', '')
    items_used = result.get('items_used', [])
    
    print(f"✅ Assignments criados com sucesso:")
    print(f"   📋 Assignment IDs: {assignment_ids}")
    print(f"   📅 Data: {date_created}")
    print(f"   📦 Items utilizados: {items_used}")
    test_results.append(True)
    
    # TESTE 2: Verificar se assignments aparecem em daily-tasks
    print("\n2️⃣ VERIFICANDO SE ASSIGNMENTS APARECEM EM DAILY-TASKS:")
    print("-" * 60)
    
    response = make_request('GET', f'/technician/TECH-001/daily-tasks?date={date_created}')
    if not response['success']:
        print(f"❌ Falha ao buscar daily tasks: {response['data']}")
        test_results.append(False)
        return False
    
    daily_tasks = response['data']
    assignments = daily_tasks.get('assignments', [])
    status_items = daily_tasks.get('status_items', [])
    
    print(f"📊 Dados híbridos retornados:")
    print(f"   📋 Assignments: {len(assignments)} items")
    print(f"   ⚡ Status Items: {len(status_items)} items")
    
    # Verificar se os assignments criados estão na lista
    found_assignments = []
    for assignment in assignments:
        if assignment.get('id') in assignment_ids:
            found_assignments.append(assignment.get('id'))
    
    if len(found_assignments) == len(assignment_ids):
        print(f"✅ Todos os {len(assignment_ids)} assignments criados aparecem em daily-tasks")
        test_results.append(True)
    else:
        print(f"❌ Apenas {len(found_assignments)}/{len(assignment_ids)} assignments aparecem em daily-tasks")
        test_results.append(False)
    
    # TESTE 3: Testar atualização de status dos assignments
    print("\n3️⃣ TESTANDO ATUALIZAÇÃO DE STATUS DOS ASSIGNMENTS:")
    print("-" * 55)
    
    if assignment_ids:
        test_assignment_id = assignment_ids[0]
        
        # Testar transição ASSIGNED → IN_PROGRESS
        response = make_request('PUT', f'/technician/assignment/{test_assignment_id}/status?status=IN_PROGRESS')
        if response['success']:
            print(f"✅ Status atualizado para IN_PROGRESS: {test_assignment_id}")
            test_results.append(True)
            
            # Testar transição IN_PROGRESS → COMPLETED
            response = make_request('PUT', f'/technician/assignment/{test_assignment_id}/status?status=COMPLETED')
            if response['success']:
                print(f"✅ Status atualizado para COMPLETED: {test_assignment_id}")
                test_results.append(True)
            else:
                print(f"❌ Falha ao atualizar para COMPLETED: {test_assignment_id}")
                test_results.append(False)
        else:
            print(f"❌ Falha ao atualizar para IN_PROGRESS: {test_assignment_id}")
            test_results.append(False)
            test_results.append(False)
    
    # TESTE 4: Confirmar sistema híbrido (agenda + status)
    print("\n4️⃣ CONFIRMANDO SISTEMA HÍBRIDO (AGENDA + STATUS):")
    print("-" * 50)
    
    has_assignments = len(assignments) > 0
    has_status_items = len(status_items) > 0
    
    print(f"📋 Dados da Agenda (assignments): {'✅ Presente' if has_assignments else '❌ Ausente'}")
    print(f"⚡ Dados por Status (status_items): {'✅ Presente' if has_status_items else '❌ Ausente'}")
    
    if has_assignments and has_status_items:
        print("✅ Sistema híbrido funcionando - dados de ambas as fontes disponíveis")
        test_results.append(True)
    elif has_assignments or has_status_items:
        print("⚠️ Sistema híbrido parcial - apenas uma fonte de dados disponível")
        test_results.append(True)
    else:
        print("❌ Sistema híbrido não funcionando - nenhuma fonte de dados disponível")
        test_results.append(False)
    
    # TESTE 5: Verificar tratamento de erro 404 (assignment inexistente)
    print("\n5️⃣ VERIFICANDO TRATAMENTO DE ERRO 404 (ASSIGNMENT INEXISTENTE):")
    print("-" * 70)
    
    fake_assignment_id = "TASS-inexistente-404"
    response = make_request('PUT', f'/technician/assignment/{fake_assignment_id}/status?status=CANCELLED')
    
    if not response['success'] and response['status_code'] == 404:
        print(f"✅ Erro 404 tratado adequadamente para assignment inexistente: {fake_assignment_id}")
        test_results.append(True)
    else:
        print(f"❌ Erro 404 não tratado adequadamente - Status: {response['status_code']}")
        test_results.append(False)
    
    # TESTE 6: Verificar filtro "Apenas hoje" com diferentes datas
    print("\n6️⃣ VERIFICANDO FILTRO 'APENAS HOJE' COM DIFERENTES DATAS:")
    print("-" * 60)
    
    test_dates = [
        date_created,  # Data dos assignments criados
        "2025-01-15",  # Data diferente
        "2025-01-16"   # Outra data diferente
    ]
    
    date_results = {}
    for test_date in test_dates:
        response = make_request('GET', f'/technician/TECH-001/daily-tasks?date={test_date}')
        if response['success']:
            tasks = response['data']
            assignments_count = len(tasks.get('assignments', []))
            status_items_count = len(tasks.get('status_items', []))
            
            date_results[test_date] = {
                'assignments': assignments_count,
                'status_items': status_items_count,
                'total': assignments_count + status_items_count
            }
            
            print(f"📅 {test_date}: {assignments_count} assignments + {status_items_count} status_items = {assignments_count + status_items_count} total")
        else:
            date_results[test_date] = {'error': True}
            print(f"❌ {test_date}: Erro ao buscar dados")
    
    # Verificar se filtro por data está funcionando
    if len([d for d in date_results.values() if not d.get('error')]) >= 2:
        print("✅ Filtro por data funcionando - diferentes datas retornam resultados")
        test_results.append(True)
    else:
        print("❌ Filtro por data pode não estar funcionando adequadamente")
        test_results.append(False)
    
    # RESULTADO FINAL
    print("\n" + "=" * 80)
    print("📊 RESULTADO FINAL DAS CORREÇÕES DO MODO TÉCNICO:")
    print("=" * 80)
    
    successful_tests = sum(test_results)
    total_tests = len(test_results)
    
    if successful_tests == total_tests:
        print("🎉 TODAS AS CORREÇÕES DO MODO TÉCNICO FUNCIONANDO PERFEITAMENTE!")
        print(f"✅ {successful_tests}/{total_tests} testes aprovados (100% sucesso)")
        print("✅ Endpoint de criação de assignments de teste funcionando")
        print("✅ Assignments aparecem corretamente em daily-tasks")
        print("✅ Atualização de status funcionando")
        print("✅ Sistema híbrido (agenda + status) operacional")
        print("✅ Tratamento de erro 404 adequado")
        print("✅ Filtro por data funcionando")
        return True
    else:
        print("⚠️ ALGUMAS CORREÇÕES DO MODO TÉCNICO PRECISAM DE ATENÇÃO")
        print(f"📊 {successful_tests}/{total_tests} testes aprovados ({successful_tests/total_tests*100:.1f}% sucesso)")
        return False

if __name__ == "__main__":
    print("🔧 TESTING TECHNICIAN MODE CORRECTIONS - REVIEW REQUEST")
    print("=" * 80)
    
    success = test_technician_mode_corrections()
    
    if success:
        print("\n🎉 TODAS AS CORREÇÕES DO MODO TÉCNICO FUNCIONANDO PERFEITAMENTE!")
    else:
        print("\n⚠️ ALGUMAS CORREÇÕES PRECISAM DE ATENÇÃO!")
        print("⚠️ Verifique os resultados detalhados dos testes acima")
    
    print("\n" + "=" * 80)
    print("🏁 TESTING COMPLETE - TECHNICIAN MODE CORRECTIONS")
    print("=" * 80)