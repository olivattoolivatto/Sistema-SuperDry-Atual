#!/usr/bin/env python3
"""
Backend Test Suite for SuperDry Lavanderia Budget System
Focus: Complete budget system testing with emphasis on update functionality
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://superdry-admin.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class BudgetSystemTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.test_results = []
        self.created_resources = {
            'clients': [],
            'services': [],
            'budgets': []
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
        """Create test clients and services for budget testing"""
        print("\n=== SETTING UP TEST DATA ===")
        
        # Create test client
        client_data = {
            "name": "Maria Silva Santos",
            "phone_primary": "11987654321",
            "phone_alternative": "1134567890",
            "email": "maria.santos@email.com",
            "cpf_cnpj": "123.456.789-00",
            "address": {
                "full_address": "Rua das Flores, 123",
                "complement": "Apto 45",
                "neighborhood": "Vila Madalena",
                "city": "São Paulo",
                "state": "SP",
                "latitude": -23.5505,
                "longitude": -46.6333
            }
        }
        
        response = self.make_request('POST', '/clients', client_data)
        if response['success']:
            self.created_resources['clients'].append(response['data']['id'])
            self.log_test("Setup: Create Test Client", True, f"Client created: {response['data']['id']}")
        else:
            self.log_test("Setup: Create Test Client", False, "Failed to create test client", response['data'])
            return False
        
        # Create test service
        service_data = {
            "name": "Limpeza de Sofá 3 Lugares",
            "category": "ESTOFADOS",
            "service_type": "Limpeza Profunda",
            "measure_type": "UNITARIO",
            "execution_location": "RETIRADA",
            "cost_price": 80.0,
            "sale_price": 150.0
        }
        
        response = self.make_request('POST', '/services', service_data)
        if response['success']:
            self.created_resources['services'].append(response['data']['id'])
            self.log_test("Setup: Create Test Service", True, f"Service created: {response['data']['id']}")
        else:
            self.log_test("Setup: Create Test Service", False, "Failed to create test service", response['data'])
            return False
        
        return True
    
    def test_budget_creation(self):
        """Test POST /api/budgets - Create new budget"""
        print("\n=== TESTING BUDGET CREATION ===")
        
        if not self.created_resources['clients'] or not self.created_resources['services']:
            self.log_test("Budget Creation", False, "Missing test data (clients/services)")
            return None
        
        budget_data = {
            "client_id": self.created_resources['clients'][0],
            "payment_method": "PIX_CNPJ_25995295000104",
            "salesperson": "Gabriela Alcântara",
            "internal_observations": "Cliente preferencial - desconto aplicado",
            "budget_observations": "Serviço agendado para próxima semana",
            "items": [
                {
                    "id": "ITM-0000001",
                    "service_id": self.created_resources['services'][0],
                    "service_name": "Limpeza de Sofá 3 Lugares",
                    "service_code": self.created_resources['services'][0],
                    "quantity": 1.0,
                    "unit_price": 150.0,
                    "total_value": 150.0,
                    "observations": "Sofá em bom estado",
                    "status": "RETIRAR",
                    "execution_location": "RETIRADA",
                    "is_retoque": False
                }
            ]
        }
        
        response = self.make_request('POST', '/budgets', budget_data)
        if response['success']:
            budget_id = response['data']['id']
            self.created_resources['budgets'].append(budget_id)
            
            # Verify budget data
            budget = response['data']
            checks = [
                (budget.get('client_name') == 'Maria Silva Santos', "Client name populated"),
                (budget.get('payment_method') == 'PIX_CNPJ_25995295000104', "Payment method set"),
                (budget.get('salesperson') == 'Gabriela Alcântara', "Salesperson set"),
                (budget.get('total_value') == 150.0, "Total value calculated"),
                (len(budget.get('items', [])) == 1, "Items added"),
                (budget.get('updated_at') is not None, "Updated timestamp set")
            ]
            
            all_passed = all(check[0] for check in checks)
            failed_checks = [check[1] for check in checks if not check[0]]
            
            if all_passed:
                self.log_test("Budget Creation", True, f"Budget created successfully: {budget_id}")
                return budget_id
            else:
                self.log_test("Budget Creation", False, f"Data validation failed: {failed_checks}")
                return budget_id
        else:
            self.log_test("Budget Creation", False, "Failed to create budget", response['data'])
            return None
    
    def test_budget_listing(self):
        """Test GET /api/budgets - List budgets"""
        print("\n=== TESTING BUDGET LISTING ===")
        
        response = self.make_request('GET', '/budgets')
        if response['success']:
            budgets = response['data']
            if isinstance(budgets, list) and len(budgets) > 0:
                self.log_test("Budget Listing", True, f"Retrieved {len(budgets)} budgets")
                return True
            else:
                self.log_test("Budget Listing", False, "No budgets found or invalid response format")
                return False
        else:
            self.log_test("Budget Listing", False, "Failed to retrieve budgets", response['data'])
            return False
    
    def test_budget_retrieval(self, budget_id: str):
        """Test GET /api/budgets/{budget_id} - Get specific budget"""
        print("\n=== TESTING BUDGET RETRIEVAL ===")
        
        response = self.make_request('GET', f'/budgets/{budget_id}')
        if response['success']:
            budget = response['data']
            required_fields = ['id', 'client_id', 'client_name', 'payment_method', 'salesperson', 'items', 'total_value']
            missing_fields = [field for field in required_fields if field not in budget]
            
            if not missing_fields:
                self.log_test("Budget Retrieval", True, f"Budget {budget_id} retrieved with all required fields")
                return budget
            else:
                self.log_test("Budget Retrieval", False, f"Missing fields: {missing_fields}")
                return budget
        else:
            self.log_test("Budget Retrieval", False, f"Failed to retrieve budget {budget_id}", response['data'])
            return None
    
    def test_budget_update_client_change(self, budget_id: str):
        """Test budget update - Change client"""
        print("\n=== TESTING BUDGET UPDATE: CLIENT CHANGE ===")
        
        # Create another test client
        new_client_data = {
            "name": "João Pedro Oliveira",
            "phone_primary": "11876543210",
            "email": "joao.oliveira@email.com",
            "address": {
                "full_address": "Av. Paulista, 1000",
                "neighborhood": "Bela Vista",
                "city": "São Paulo",
                "state": "SP"
            }
        }
        
        client_response = self.make_request('POST', '/clients', new_client_data)
        if not client_response['success']:
            self.log_test("Budget Update: Client Change", False, "Failed to create new client for test")
            return False
        
        new_client_id = client_response['data']['id']
        self.created_resources['clients'].append(new_client_id)
        
        # Update budget with new client
        update_data = {
            "client_id": new_client_id,
            "payment_method": "PIX_CNPJ_25995295000104",
            "salesperson": "Gabriela Alcântara",
            "internal_observations": "Cliente alterado via teste",
            "items": []
        }
        
        response = self.make_request('PUT', f'/budgets/{budget_id}', update_data)
        if response['success']:
            updated_budget = response['data']
            checks = [
                (updated_budget.get('client_id') == new_client_id, "Client ID updated"),
                (updated_budget.get('client_name') == 'João Pedro Oliveira', "Client name updated"),
                (updated_budget.get('updated_at') != updated_budget.get('created_at'), "Updated timestamp changed")
            ]
            
            all_passed = all(check[0] for check in checks)
            failed_checks = [check[1] for check in checks if not check[0]]
            
            if all_passed:
                self.log_test("Budget Update: Client Change", True, "Client successfully updated")
                return True
            else:
                self.log_test("Budget Update: Client Change", False, f"Validation failed: {failed_checks}")
                return False
        else:
            self.log_test("Budget Update: Client Change", False, "Failed to update budget client", response['data'])
            return False
    
    def test_budget_update_payment_method(self, budget_id: str):
        """Test budget update - Change payment method"""
        print("\n=== TESTING BUDGET UPDATE: PAYMENT METHOD CHANGE ===")
        
        update_data = {
            "client_id": self.created_resources['clients'][0],
            "payment_method": "CREDITO_3X",
            "salesperson": "Gabriela Alcântara",
            "internal_observations": "Método de pagamento alterado para cartão 3x",
            "items": []
        }
        
        response = self.make_request('PUT', f'/budgets/{budget_id}', update_data)
        if response['success']:
            updated_budget = response['data']
            if updated_budget.get('payment_method') == 'CREDITO_3X':
                self.log_test("Budget Update: Payment Method", True, "Payment method successfully updated to CREDITO_3X")
                return True
            else:
                self.log_test("Budget Update: Payment Method", False, f"Payment method not updated correctly: {updated_budget.get('payment_method')}")
                return False
        else:
            self.log_test("Budget Update: Payment Method", False, "Failed to update payment method", response['data'])
            return False
    
    def test_budget_update_salesperson(self, budget_id: str):
        """Test budget update - Change salesperson"""
        print("\n=== TESTING BUDGET UPDATE: SALESPERSON CHANGE ===")
        
        update_data = {
            "client_id": self.created_resources['clients'][0],
            "payment_method": "CREDITO_3X",
            "salesperson": "Diego Olivatto",
            "internal_observations": "Vendedor alterado para Diego",
            "items": []
        }
        
        response = self.make_request('PUT', f'/budgets/{budget_id}', update_data)
        if response['success']:
            updated_budget = response['data']
            if updated_budget.get('salesperson') == 'Diego Olivatto':
                self.log_test("Budget Update: Salesperson", True, "Salesperson successfully updated to Diego Olivatto")
                return True
            else:
                self.log_test("Budget Update: Salesperson", False, f"Salesperson not updated correctly: {updated_budget.get('salesperson')}")
                return False
        else:
            self.log_test("Budget Update: Salesperson", False, "Failed to update salesperson", response['data'])
            return False
    
    def test_budget_update_items(self, budget_id: str):
        """Test budget update - Add/modify items"""
        print("\n=== TESTING BUDGET UPDATE: ITEMS MODIFICATION ===")
        
        # Create additional test service
        service_data = {
            "name": "Limpeza de Tapete Persa",
            "category": "TAPETES",
            "service_type": "Limpeza Especializada",
            "measure_type": "AREA_DE_TAPETE",
            "execution_location": "RETIRADA",
            "cost_price": 25.0,
            "sale_price": 45.0
        }
        
        service_response = self.make_request('POST', '/services', service_data)
        if not service_response['success']:
            self.log_test("Budget Update: Items", False, "Failed to create additional service for test")
            return False
        
        new_service_id = service_response['data']['id']
        self.created_resources['services'].append(new_service_id)
        
        # Update budget with multiple items
        update_data = {
            "client_id": self.created_resources['clients'][0],
            "payment_method": "CREDITO_3X",
            "salesperson": "Diego Olivatto",
            "internal_observations": "Orçamento com múltiplos itens",
            "items": [
                {
                    "id": "ITM-0000002",
                    "service_id": self.created_resources['services'][0],
                    "service_name": "Limpeza de Sofá 3 Lugares",
                    "service_code": self.created_resources['services'][0],
                    "quantity": 2.0,
                    "unit_price": 150.0,
                    "total_value": 300.0,
                    "observations": "2 sofás para limpeza",
                    "status": "RETIRAR",
                    "execution_location": "RETIRADA",
                    "is_retoque": False
                },
                {
                    "id": "ITM-0000003",
                    "service_id": new_service_id,
                    "service_name": "Limpeza de Tapete Persa",
                    "service_code": new_service_id,
                    "quantity": 1.5,
                    "unit_price": 45.0,
                    "area_m2": 1.5,
                    "total_value": 67.5,
                    "observations": "Tapete persa 1.5m²",
                    "status": "RETIRAR",
                    "execution_location": "RETIRADA",
                    "is_retoque": False
                }
            ]
        }
        
        response = self.make_request('PUT', f'/budgets/{budget_id}', update_data)
        if response['success']:
            updated_budget = response['data']
            checks = [
                (len(updated_budget.get('items', [])) == 2, "Two items added"),
                (updated_budget.get('total_value') == 367.5, "Total value recalculated"),
                (updated_budget.get('total_area_m2') == 1.5, "Total area calculated"),
                (updated_budget.get('total_units') == 2, "Total units calculated")
            ]
            
            all_passed = all(check[0] for check in checks)
            failed_checks = [check[1] for check in checks if not check[0]]
            
            if all_passed:
                self.log_test("Budget Update: Items", True, "Items successfully updated with correct totals")
                return True
            else:
                self.log_test("Budget Update: Items", False, f"Validation failed: {failed_checks}", {
                    'expected_total': 367.5,
                    'actual_total': updated_budget.get('total_value'),
                    'expected_items': 2,
                    'actual_items': len(updated_budget.get('items', []))
                })
                return False
        else:
            self.log_test("Budget Update: Items", False, "Failed to update budget items", response['data'])
            return False
    
    def test_budget_update_observations(self, budget_id: str):
        """Test budget update - Change observations"""
        print("\n=== TESTING BUDGET UPDATE: OBSERVATIONS CHANGE ===")
        
        update_data = {
            "client_id": self.created_resources['clients'][0],
            "payment_method": "CREDITO_3X",
            "salesperson": "Diego Olivatto",
            "internal_observations": "Observações internas atualizadas - cliente VIP",
            "budget_observations": "Observações do orçamento atualizadas - entrega expressa",
            "items": []
        }
        
        response = self.make_request('PUT', f'/budgets/{budget_id}', update_data)
        if response['success']:
            updated_budget = response['data']
            checks = [
                (updated_budget.get('internal_observations') == "Observações internas atualizadas - cliente VIP", "Internal observations updated"),
                (updated_budget.get('budget_observations') == "Observações do orçamento atualizadas - entrega expressa", "Budget observations updated")
            ]
            
            all_passed = all(check[0] for check in checks)
            failed_checks = [check[1] for check in checks if not check[0]]
            
            if all_passed:
                self.log_test("Budget Update: Observations", True, "Observations successfully updated")
                return True
            else:
                self.log_test("Budget Update: Observations", False, f"Validation failed: {failed_checks}")
                return False
        else:
            self.log_test("Budget Update: Observations", False, "Failed to update observations", response['data'])
            return False
    
    def test_budget_update_invalid_client(self, budget_id: str):
        """Test budget update with invalid client - should fail"""
        print("\n=== TESTING BUDGET UPDATE: INVALID CLIENT (SHOULD FAIL) ===")
        
        update_data = {
            "client_id": "CLI-9999",  # Non-existent client
            "payment_method": "PIX_CNPJ_25995295000104",
            "salesperson": "Gabriela Alcântara",
            "items": []
        }
        
        response = self.make_request('PUT', f'/budgets/{budget_id}', update_data)
        if not response['success'] and (response['status_code'] == 404 or 'Client not found' in str(response['data'])):
            self.log_test("Budget Update: Invalid Client", True, "Correctly rejected invalid client ID")
            return True
        else:
            self.log_test("Budget Update: Invalid Client", False, "Should have failed with 404 for invalid client", response['data'])
            return False
    
    def test_whatsapp_message_generation(self, budget_id: str):
        """Test GET /api/budgets/{budget_id}/whatsapp - Generate WhatsApp message"""
        print("\n=== TESTING WHATSAPP MESSAGE GENERATION ===")
        
        response = self.make_request('GET', f'/budgets/{budget_id}/whatsapp')
        if response['success']:
            whatsapp_data = response['data']
            
            # Check required fields
            required_fields = ['message', 'phone', 'whatsapp_url']
            missing_fields = [field for field in required_fields if field not in whatsapp_data]
            
            if missing_fields:
                self.log_test("WhatsApp Generation", False, f"Missing fields: {missing_fields}")
                return False
            
            message = whatsapp_data['message']
            phone = whatsapp_data['phone']
            whatsapp_url = whatsapp_data['whatsapp_url']
            
            # Validate message content
            checks = [
                ('ORÇAMENTO PERSONALIZADO' in message, "Header present"),
                ('SuperDry Lavanderia' in message, "Company name present"),
                (budget_id in message, "Budget ID present"),
                ('Maria Silva Santos' in message or 'João Pedro Oliveira' in message, "Client name present"),
                ('VALOR TOTAL:' in message, "Total value section present"),
                ('R$' in message, "Currency format present"),
                ('*' in message, "Bold formatting present"),
                ('_' in message, "Italic formatting present"),
                (phone and len(phone) > 0, "Phone number present"),
                ('wa.me' in whatsapp_url, "WhatsApp URL format correct"),
                ('55' in whatsapp_url, "Brazil country code in URL"),
                ('text=' in whatsapp_url, "Message parameter in URL")
            ]
            
            all_passed = all(check[0] for check in checks)
            failed_checks = [check[1] for check in checks if not check[0]]
            
            if all_passed:
                self.log_test("WhatsApp Generation", True, f"WhatsApp message generated successfully with all required elements")
                print(f"   📱 Phone: {phone}")
                print(f"   📝 Message length: {len(message)} characters")
                print(f"   🔗 URL length: {len(whatsapp_url)} characters")
                return True
            else:
                self.log_test("WhatsApp Generation", False, f"Content validation failed: {failed_checks}")
                return False
        else:
            self.log_test("WhatsApp Generation", False, f"Failed to generate WhatsApp message", response['data'])
            return False
    
    def test_whatsapp_with_existing_budget(self):
        """Test WhatsApp generation with existing budget (ORC-0000001)"""
        print("\n=== TESTING WHATSAPP WITH EXISTING BUDGET ===")
        
        # Try common existing budget IDs
        existing_budget_ids = ['ORC-0000001', 'ORC-0000002', 'ORC-0000003']
        
        for budget_id in existing_budget_ids:
            response = self.make_request('GET', f'/budgets/{budget_id}')
            if response['success']:
                print(f"   Found existing budget: {budget_id}")
                return self.test_whatsapp_message_generation(budget_id)
        
        self.log_test("WhatsApp Existing Budget", False, "No existing budgets found to test with")
        return False
    
    def test_pdf_generation(self, budget_id: str):
        """Test GET /api/budgets/{budget_id}/pdf - Generate PDF"""
        print("\n=== TESTING PDF GENERATION ===")
        
        try:
            url = f"{self.base_url}/budgets/{budget_id}/pdf"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                # Check if response is PDF
                content_type = response.headers.get('content-type', '')
                content_disposition = response.headers.get('content-disposition', '')
                
                checks = [
                    ('application/pdf' in content_type, "PDF content type"),
                    ('attachment' in content_disposition, "Attachment disposition"),
                    (f'orcamento_{budget_id}.pdf' in content_disposition, "Correct filename"),
                    (len(response.content) > 1000, "PDF has substantial content"),
                    (response.content.startswith(b'%PDF'), "Valid PDF header")
                ]
                
                all_passed = all(check[0] for check in checks)
                failed_checks = [check[1] for check in checks if not check[0]]
                
                if all_passed:
                    self.log_test("PDF Generation", True, f"PDF generated successfully ({len(response.content)} bytes)")
                    return True
                else:
                    self.log_test("PDF Generation", False, f"PDF validation failed: {failed_checks}", {
                        'content_type': content_type,
                        'content_length': len(response.content),
                        'content_disposition': content_disposition
                    })
                    return False
            else:
                self.log_test("PDF Generation", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("PDF Generation", False, f"Exception during PDF generation: {str(e)}")
            return False
    
    def test_pdf_with_existing_budget(self):
        """Test PDF generation with existing budget (ORC-0000001)"""
        print("\n=== TESTING PDF WITH EXISTING BUDGET ===")
        
        # Try common existing budget IDs
        existing_budget_ids = ['ORC-0000001', 'ORC-0000002', 'ORC-0000003']
        
        for budget_id in existing_budget_ids:
            response = self.make_request('GET', f'/budgets/{budget_id}')
            if response['success']:
                print(f"   Found existing budget: {budget_id}")
                return self.test_pdf_generation(budget_id)
        
        self.log_test("PDF Existing Budget", False, "No existing budgets found to test with")
        return False
    
    def test_whatsapp_nonexistent_budget(self):
        """Test WhatsApp generation with non-existent budget - should fail"""
        print("\n=== TESTING WHATSAPP WITH NON-EXISTENT BUDGET (SHOULD FAIL) ===")
        
        response = self.make_request('GET', '/budgets/ORC-9999999/whatsapp')
        if not response['success'] and (response['status_code'] == 404 or 'Budget not found' in str(response['data'])):
            self.log_test("WhatsApp Non-existent Budget", True, "Correctly rejected non-existent budget")
            return True
        else:
            self.log_test("WhatsApp Non-existent Budget", False, "Should have failed with 404 for non-existent budget", response['data'])
            return False
    
    def test_pdf_nonexistent_budget(self):
        """Test PDF generation with non-existent budget - should fail"""
        print("\n=== TESTING PDF WITH NON-EXISTENT BUDGET (SHOULD FAIL) ===")
        
        try:
            url = f"{self.base_url}/budgets/ORC-9999999/pdf"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 404 or 'Budget not found' in response.text:
                self.log_test("PDF Non-existent Budget", True, "Correctly rejected non-existent budget")
                return True
            else:
                self.log_test("PDF Non-existent Budget", False, f"Should have failed with 404, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("PDF Non-existent Budget", False, f"Exception: {str(e)}")
            return False
    
    def cleanup_test_data(self):
        """Clean up created test data"""
        print("\n=== CLEANING UP TEST DATA ===")
        
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
        
        # Note: Services are not deleted as they might be used by other budgets
        print(f"ℹ️  Services created: {len(self.created_resources['services'])} (not deleted)")
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 STARTING BUDGET SYSTEM COMPREHENSIVE TESTS")
        print(f"🔗 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Setup
        if not self.setup_test_data():
            print("❌ CRITICAL: Failed to setup test data. Aborting tests.")
            return False
        
        # Test budget creation
        budget_id = self.test_budget_creation()
        if not budget_id:
            print("❌ CRITICAL: Failed to create test budget. Aborting remaining tests.")
            return False
        
        # Test budget listing
        self.test_budget_listing()
        
        # Test budget retrieval
        self.test_budget_retrieval(budget_id)
        
        # Test various update scenarios
        self.test_budget_update_client_change(budget_id)
        self.test_budget_update_payment_method(budget_id)
        self.test_budget_update_salesperson(budget_id)
        self.test_budget_update_items(budget_id)
        self.test_budget_update_observations(budget_id)
        
        # Test error handling
        self.test_budget_update_invalid_client(budget_id)
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        self.print_summary()
        
        return True
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
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
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    tester = BudgetSystemTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)