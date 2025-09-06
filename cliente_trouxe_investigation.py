#!/usr/bin/env python3
"""
INVESTIGAÇÃO PURA - APENAS VERIFICAR: Items CLIENTE_TROUXE aparecendo na lista de rotas AGORA MESMO.

CONTEXTO CRÍTICO:
- Usuário acabou de criar novos items 
- Items estão aparecendo na lista de serviços disponíveis para rota NESTE MOMENTO
- Usuário suspeita que minhas verificações anteriores "forçam" items a saírem temporariamente
- Usuário solicitou: APENAS VERIFICAR, NÃO CORRIGIR

INVESTIGAÇÃO APENAS DE LEITURA:
1. **Verificar estado ATUAL da lista de rotas**: GET /api/budget-items/available-for-routes
2. **Identificar items CLIENTE_TROUXE**: Filtrar por service_codes que deveriam ser CLIENTE_TROUXE
3. **Verificar serviços correspondentes**: Confirmar se services têm default_service_status correto
4. **Analisar inconsistências**: Items vs Services sem fazer correções

IMPORTANTE: 
- NÃO executar migrações
- NÃO fazer correções
- NÃO alterar dados
- APENAS reportar o que encontrar
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://superdry-routes.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class ClienteTrouxeInvestigator:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.findings = []
        
    def log_finding(self, category: str, finding: str, data: Any = None):
        """Log investigation findings"""
        result = {
            'category': category,
            'finding': finding,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        self.findings.append(result)
        print(f"🔍 {category}: {finding}")
        if data and isinstance(data, (dict, list)) and len(str(data)) < 200:
            print(f"   📊 Data: {data}")
    
    def make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            
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
    
    def investigate_current_available_routes(self):
        """1. Verificar estado ATUAL da lista de rotas disponíveis"""
        print("\n" + "=" * 80)
        print("🔍 INVESTIGAÇÃO 1: ESTADO ATUAL DA LISTA DE ROTAS DISPONÍVEIS")
        print("=" * 80)
        
        response = self.make_request('GET', '/budget-items/available-for-routes')
        if not response['success']:
            self.log_finding("ERRO CRÍTICO", f"Falha ao acessar lista de rotas - Status: {response['status_code']}", response['data'])
            return []
        
        data = response['data']
        available_items = data.get('available_items', [])
        
        print(f"📊 TOTAL DE ITEMS DISPONÍVEIS PARA ROTAS: {len(available_items)}")
        
        if not available_items:
            self.log_finding("LISTA VAZIA", "Nenhum item disponível para rotas encontrado")
            return []
        
        # Analisar distribuição de status
        status_distribution = {}
        service_codes_found = set()
        
        for item in available_items:
            status = item.get('status', 'N/A')
            service_code = item.get('service_code', 'N/A')
            
            status_distribution[status] = status_distribution.get(status, 0) + 1
            service_codes_found.add(service_code)
        
        print(f"📋 DISTRIBUIÇÃO DE STATUS:")
        for status, count in status_distribution.items():
            print(f"   {status}: {count} items")
        
        print(f"📋 SERVICE CODES ENCONTRADOS: {len(service_codes_found)}")
        
        # Identificar items com status CLIENTE_TROUXE
        cliente_trouxe_items = [item for item in available_items if item.get('status') == 'CLIENTE_TROUXE']
        
        if cliente_trouxe_items:
            self.log_finding("PROBLEMA CONFIRMADO", f"ENCONTRADOS {len(cliente_trouxe_items)} items com status CLIENTE_TROUXE na lista de rotas", 
                           [item.get('service_code') for item in cliente_trouxe_items])
            
            print(f"\n❌ ITEMS CLIENTE_TROUXE ENCONTRADOS NA LISTA DE ROTAS:")
            for i, item in enumerate(cliente_trouxe_items, 1):
                service_code = item.get('service_code', 'N/A')
                client_name = item.get('client_name', 'N/A')
                budget_id = item.get('budget_id', 'N/A')
                budget_item_id = item.get('budget_item_id', 'N/A')
                
                print(f"   {i:2d}. Service: {service_code} | Cliente: {client_name} | Budget: {budget_id} | Item: {budget_item_id}")
        else:
            self.log_finding("LISTA LIMPA", "Nenhum item com status CLIENTE_TROUXE encontrado na lista de rotas")
        
        return available_items
    
    def investigate_service_codes_cliente_trouxe(self, available_items):
        """2. Identificar quais service_codes deveriam ser CLIENTE_TROUXE"""
        print("\n" + "=" * 80)
        print("🔍 INVESTIGAÇÃO 2: VERIFICAR SERVICES COM default_service_status = CLIENTE_TROUXE")
        print("=" * 80)
        
        # Obter todos os services
        response = self.make_request('GET', '/services?include_inactive=true')
        if not response['success']:
            self.log_finding("ERRO CRÍTICO", f"Falha ao acessar catálogo de services - Status: {response['status_code']}", response['data'])
            return {}
        
        all_services = response['data']
        
        # Filtrar services com CLIENTE_TROUXE
        cliente_trouxe_services = {}
        for service in all_services:
            if service.get('default_service_status') == 'CLIENTE_TROUXE':
                service_id = service.get('id')
                cliente_trouxe_services[service_id] = service
        
        print(f"📊 TOTAL DE SERVICES NO CATÁLOGO: {len(all_services)}")
        print(f"📊 SERVICES COM CLIENTE_TROUXE: {len(cliente_trouxe_services)}")
        
        if cliente_trouxe_services:
            print(f"\n📋 LISTA DE SERVICES COM default_service_status = CLIENTE_TROUXE:")
            for i, (service_id, service) in enumerate(cliente_trouxe_services.items(), 1):
                service_name = service.get('name', 'N/A')
                is_active = service.get('is_active', False)
                status_icon = "✅" if is_active else "❌"
                
                print(f"   {i:2d}. {service_id} - {service_name} {status_icon}")
            
            self.log_finding("SERVICES CLIENTE_TROUXE", f"Encontrados {len(cliente_trouxe_services)} services com CLIENTE_TROUXE", 
                           list(cliente_trouxe_services.keys()))
        else:
            self.log_finding("NENHUM SERVICE", "Nenhum service encontrado com default_service_status = CLIENTE_TROUXE")
        
        return cliente_trouxe_services
    
    def investigate_inconsistencies(self, available_items, cliente_trouxe_services):
        """3. Analisar inconsistências entre items disponíveis e services CLIENTE_TROUXE"""
        print("\n" + "=" * 80)
        print("🔍 INVESTIGAÇÃO 3: ANÁLISE DE INCONSISTÊNCIAS")
        print("=" * 80)
        
        inconsistencies = []
        
        # Verificar se algum item na lista de rotas usa service_code de CLIENTE_TROUXE
        for item in available_items:
            service_code = item.get('service_code', '')
            item_status = item.get('status', '')
            
            if service_code in cliente_trouxe_services:
                # Este item usa um service que deveria ser CLIENTE_TROUXE
                service_data = cliente_trouxe_services[service_code]
                expected_status = service_data.get('default_service_status')
                
                inconsistency = {
                    'budget_item_id': item.get('budget_item_id'),
                    'budget_id': item.get('budget_id'),
                    'client_name': item.get('client_name'),
                    'service_code': service_code,
                    'service_name': service_data.get('name'),
                    'item_status': item_status,
                    'expected_status': expected_status,
                    'is_inconsistent': item_status != expected_status
                }
                
                inconsistencies.append(inconsistency)
        
        if inconsistencies:
            print(f"❌ ENCONTRADAS {len(inconsistencies)} INCONSISTÊNCIAS:")
            
            for i, inc in enumerate(inconsistencies, 1):
                status_icon = "❌" if inc['is_inconsistent'] else "✅"
                print(f"\n   {i:2d}. {status_icon} Item: {inc['budget_item_id']}")
                print(f"       Service: {inc['service_code']} - {inc['service_name']}")
                print(f"       Cliente: {inc['client_name']}")
                print(f"       Budget: {inc['budget_id']}")
                print(f"       Status Atual: {inc['item_status']}")
                print(f"       Status Esperado: {inc['expected_status']}")
                
                if inc['is_inconsistent']:
                    print(f"       🚨 INCONSISTÊNCIA: Item deveria ter status '{inc['expected_status']}' mas tem '{inc['item_status']}'")
            
            inconsistent_count = sum(1 for inc in inconsistencies if inc['is_inconsistent'])
            
            if inconsistent_count > 0:
                self.log_finding("INCONSISTÊNCIAS ENCONTRADAS", 
                               f"{inconsistent_count} de {len(inconsistencies)} items têm status incorreto", 
                               [inc['budget_item_id'] for inc in inconsistencies if inc['is_inconsistent']])
            else:
                self.log_finding("DADOS CONSISTENTES", 
                               f"Todos os {len(inconsistencies)} items têm status correto")
        else:
            self.log_finding("NENHUMA INCONSISTÊNCIA", "Nenhum item na lista de rotas usa services CLIENTE_TROUXE")
        
        return inconsistencies
    
    def investigate_specific_services(self, service_ids_to_check):
        """4. Verificar services específicos mencionados pelo usuário"""
        print("\n" + "=" * 80)
        print("🔍 INVESTIGAÇÃO 4: VERIFICAÇÃO DE SERVICES ESPECÍFICOS")
        print("=" * 80)
        
        specific_findings = {}
        
        for service_id in service_ids_to_check:
            print(f"\n🎯 Verificando {service_id}:")
            
            response = self.make_request('GET', f'/services/{service_id}')
            if response['success']:
                service = response['data']
                
                service_name = service.get('name', 'N/A')
                default_status = service.get('default_service_status', 'N/A')
                is_active = service.get('is_active', False)
                
                print(f"   📝 Nome: {service_name}")
                print(f"   🔄 Status Padrão: {default_status}")
                print(f"   ✅ Ativo: {is_active}")
                
                specific_findings[service_id] = {
                    'found': True,
                    'name': service_name,
                    'default_status': default_status,
                    'is_active': is_active,
                    'is_cliente_trouxe': default_status == 'CLIENTE_TROUXE'
                }
                
                if default_status == 'CLIENTE_TROUXE':
                    print(f"   ✅ CONFIRMADO: Service tem default_service_status = CLIENTE_TROUXE")
                else:
                    print(f"   ❌ ATENÇÃO: Service NÃO tem default_service_status = CLIENTE_TROUXE (tem: {default_status})")
                
                self.log_finding(f"SERVICE {service_id}", 
                               f"Encontrado - Status: {default_status}, Ativo: {is_active}")
            else:
                print(f"   ❌ Service {service_id} não encontrado - Status: {response['status_code']}")
                specific_findings[service_id] = {
                    'found': False,
                    'error': response['data']
                }
                
                self.log_finding(f"SERVICE {service_id}", f"Não encontrado - Status: {response['status_code']}")
        
        return specific_findings
    
    def run_investigation(self):
        """Executar investigação completa READ-ONLY"""
        print("🔍 INICIANDO INVESTIGAÇÃO PURA - APENAS LEITURA")
        print("🚨 IMPORTANTE: NENHUMA CORREÇÃO SERÁ FEITA - APENAS VERIFICAÇÃO")
        print(f"🔗 Investigando: {self.base_url}")
        print("=" * 80)
        
        # 1. Verificar estado atual da lista de rotas
        available_items = self.investigate_current_available_routes()
        
        # 2. Identificar services CLIENTE_TROUXE
        cliente_trouxe_services = self.investigate_service_codes_cliente_trouxe(available_items)
        
        # 3. Analisar inconsistências
        inconsistencies = self.investigate_inconsistencies(available_items, cliente_trouxe_services)
        
        # 4. Verificar services específicos que podem estar causando problema
        # Baseado no histórico, vamos verificar alguns services conhecidos
        specific_services = ['SRV-0036', 'SRV-0037', 'SRV-0145', 'SRV-0146', 'SRV-0161']
        specific_findings = self.investigate_specific_services(specific_services)
        
        # Resumo da investigação
        self.print_investigation_summary(available_items, cliente_trouxe_services, inconsistencies, specific_findings)
        
        return {
            'available_items': available_items,
            'cliente_trouxe_services': cliente_trouxe_services,
            'inconsistencies': inconsistencies,
            'specific_findings': specific_findings,
            'findings': self.findings
        }
    
    def print_investigation_summary(self, available_items, cliente_trouxe_services, inconsistencies, specific_findings):
        """Imprimir resumo da investigação"""
        print("\n" + "=" * 80)
        print("📋 RESUMO DA INVESTIGAÇÃO READ-ONLY")
        print("=" * 80)
        
        # Status atual
        cliente_trouxe_in_routes = len([item for item in available_items if item.get('status') == 'CLIENTE_TROUXE'])
        
        print(f"🎯 PERGUNTA DO USUÁRIO: Items CLIENTE_TROUXE estão aparecendo na lista de rotas AGORA?")
        
        if cliente_trouxe_in_routes > 0:
            print(f"❌ RESPOSTA: SIM - {cliente_trouxe_in_routes} items com status CLIENTE_TROUXE estão na lista")
            print(f"🚨 PROBLEMA CONFIRMADO: Items que não deveriam aparecer estão visíveis para criação de rotas")
        else:
            print(f"✅ RESPOSTA: NÃO - Nenhum item com status CLIENTE_TROUXE está na lista de rotas")
            print(f"✅ SISTEMA FUNCIONANDO CORRETAMENTE: Lista de rotas está limpa")
        
        # Estatísticas gerais
        print(f"\n📊 ESTATÍSTICAS:")
        print(f"   📋 Total de items disponíveis para rotas: {len(available_items)}")
        print(f"   🏷️  Total de services CLIENTE_TROUXE no catálogo: {len(cliente_trouxe_services)}")
        print(f"   ❌ Items CLIENTE_TROUXE incorretamente na lista: {cliente_trouxe_in_routes}")
        print(f"   🔍 Inconsistências encontradas: {len([inc for inc in inconsistencies if inc['is_inconsistent']])}")
        
        # Services específicos verificados
        print(f"\n🎯 SERVICES ESPECÍFICOS VERIFICADOS:")
        for service_id, finding in specific_findings.items():
            if finding['found']:
                status_icon = "✅" if finding['is_cliente_trouxe'] else "❌"
                print(f"   {service_id}: {status_icon} {finding['default_status']} ({'Ativo' if finding['is_active'] else 'Inativo'})")
            else:
                print(f"   {service_id}: ❌ Não encontrado")
        
        # Conclusão
        print(f"\n🎯 CONCLUSÃO DA INVESTIGAÇÃO:")
        if cliente_trouxe_in_routes > 0:
            print(f"   ❌ O PROBLEMA EXISTE: Items CLIENTE_TROUXE estão aparecendo na lista de rotas")
            print(f"   🔧 AÇÃO NECESSÁRIA: Executar migração ou correção para resolver inconsistências")
        else:
            print(f"   ✅ SISTEMA CORRETO: Nenhum item CLIENTE_TROUXE aparece incorretamente na lista")
            print(f"   ℹ️  POSSÍVEL CAUSA: Problema pode ter sido resolvido ou não existe no momento")
        
        print(f"\n⚠️  IMPORTANTE: Esta foi uma investigação READ-ONLY - nenhuma correção foi aplicada")

if __name__ == "__main__":
    investigator = ClienteTrouxeInvestigator()
    results = investigator.run_investigation()
    
    # Salvar resultados para análise posterior se necessário
    with open('/app/investigation_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Resultados salvos em: /app/investigation_results.json")