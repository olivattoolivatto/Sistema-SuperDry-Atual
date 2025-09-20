import React, { useState, useEffect } from 'react';
import { 
  Car, 
  Building, 
  Calendar, 
  MapPin, 
  Camera, 
  FileText, 
  CreditCard,
  Phone,
  Settings,
  Navigation,
  CheckCircle,
  Package,
  Truck,
  User,
  Trash2
} from 'lucide-react';
import { routesApi, budgetItemsApi, technicianApi } from '../services/api';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Função para extrair endereço legível do objeto cliente (COPIADA DA AGENDA)
const getClientAddress = (client) => {
  if (!client) return 'Endereço não informado';
  
  // Se address é um objeto
  if (client.address && typeof client.address === 'object') {
    return client.address.full_address || 'Endereço não informado';
  }
  
  // Se full_address existe diretamente no cliente
  if (client.full_address) {
    return client.full_address;
  }
  
  // Fallback para endereço simples
  if (client.address && typeof client.address === 'string') {
    return client.address;
  }
  
  return 'Endereço não informado';
};

// Função para extrair complemento do endereço (COPIADA DA AGENDA)
const getClientComplement = (client) => {
  if (!client) return 'NENHUM';
  
  // Se address é um objeto
  if (client.address && typeof client.address === 'object' && client.address.complement) {
    return client.address.complement;
  }
  
  // Se complement existe diretamente no cliente
  if (client.address_complement || client.complement) {
    return client.address_complement || client.complement;
  }
  
  return 'NENHUM';
};

// Função para gerar emoji do serviço baseado nas palavras-chave
const getServiceEmoji = (serviceName) => {
  if (!serviceName) return '✨'; // Emoji padrão
  
  const name = serviceName.toLowerCase();
  
  // Verificar palavras-chave específicas
  if (name.includes('impermeabilização')) return '💦';
  if (name.includes('carro') || name.includes('veiculo') || name.includes('veículo')) return '🚘';
  if (name.includes('pagamento') || name.includes('cartão') || name.includes('credito') || name.includes('débito') || name.includes('debito')) return '💳';
  if (name.includes('colchao') || name.includes('colchão') || name.includes('box') || name.includes('cabeceira')) return '🛏️';
  if (name.includes('cortina')) return '🪟';
  if (name.includes('sofa') || name.includes('sofá')) return '🛋️';
  if (name.includes('poltrona')) return '💺';
  if (name.includes('edredom') || name.includes('colcha') || name.includes('pillowtop')) return '🧺';
  if (name.includes('almofada') || name.includes('puff') || name.includes('outros')) return '📦';
  if (name.includes('carpete')) return '⬜';
  if (name.includes('carrinho') || name.includes('cadeirinha') || name.includes('bebe') || name.includes('bebê')) return '🛒👶';
  
  return '✨'; // Emoji padrão para serviços não mapeados
};

// Função para gerar título do evento com múltiplos serviços
const generateEventTitle = (budget, clientName) => {
  if (!budget.items || budget.items.length === 0) {
    return `✨ ${clientName}`;
  }

  // Agrupar itens por emoji (serviço similar) e coletar status
  const serviceGroups = {};
  
  budget.items.forEach(item => {
    const emoji = getServiceEmoji(item.service_name);
    const status = item.status || 'EXECUTAR_NO_LOCAL';
    
    if (!serviceGroups[emoji]) {
      serviceGroups[emoji] = {
        emoji,
        statuses: new Set(),
        services: new Set()
      };
    }
    
    serviceGroups[emoji].statuses.add(status);
    serviceGroups[emoji].services.add(item.service_name);
  });

  console.log('🎨 Grupos de serviços para título:', serviceGroups);

  // Construir partes do título
  const titleParts = [];
  
  Object.values(serviceGroups).forEach(group => {
    let part = group.emoji;
    
    // Verificar se tem RETIRAR ou ENTREGAR
    const hasRetirar = group.statuses.has('RETIRAR');
    const hasEntregar = group.statuses.has('ENTREGAR');
    
    if (hasRetirar && hasEntregar) {
      part += 'RETIRAR/ENTREGAR';
    } else if (hasRetirar) {
      part += 'RETIRAR';
    } else if (hasEntregar) {
      part += 'ENTREGAR';
    }
    // Se for apenas EXECUTAR_NO_LOCAL, não adiciona texto
    
    titleParts.push(part);
  });

  // Juntar partes com "e" e adicionar nome do cliente
  let title;
  if (titleParts.length === 1) {
    title = `${titleParts[0]} ${clientName}`;
  } else if (titleParts.length === 2) {
    title = `${titleParts[0]} e ${titleParts[1]} ${clientName}`;
  } else {
    // Mais de 2 serviços: usar vírgulas e "e" no final
    const lastPart = titleParts.pop();
    title = `${titleParts.join(', ')} e ${lastPart} ${clientName}`;
  }

  console.log('🎯 Título gerado:', title);
  return title;
};

// Função para buscar dados do orçamento e cliente - VERSÃO MELHORADA
const getBudgetAndClientData = async (budgetItemId) => {
  try {
    console.log(`🔍 Buscando dados para budget item: ${budgetItemId}`);
    
    // NOVA ABORDAGEM: Usar endpoint available-for-routes para encontrar dados completos
    const availableItemsResponse = await fetch(`${BACKEND_URL}/api/budget-items/available-for-routes`);
    if (!availableItemsResponse.ok) {
      throw new Error('Erro ao buscar itens disponíveis');
    }
    const availableData = await availableItemsResponse.json();
    
    // Procurar o item específico na lista de itens disponíveis
    const specificItem = availableData.available_items.find(item => item.budget_item_id === budgetItemId);
    
    if (!specificItem) {
      throw new Error(`Item ${budgetItemId} não encontrado nos itens disponíveis`);
    }
    
    console.log(`✅ Item encontrado nos disponíveis: ${specificItem.client_name} - ${specificItem.service_name}`);
    
    // Buscar orçamento completo para ter todos os dados
    const budgetResponse = await fetch(`${BACKEND_URL}/api/budgets/${specificItem.budget_id}`);
    if (!budgetResponse.ok) {
      throw new Error('Erro ao buscar orçamento completo');
    }
    const budget = await budgetResponse.json();
    
    // Buscar dados do cliente
    const clientResponse = await fetch(`${BACKEND_URL}/api/clients/${specificItem.client_id}`);
    if (!clientResponse.ok) {
      throw new Error('Erro ao buscar cliente');
    }
    const client = await clientResponse.json();
    
    console.log(`✅ Dados completos encontrados - Cliente: ${client.name}, Orçamento: ${budget.code}, Serviço: ${specificItem.service_name}`);
    
    // Retornar dados no formato esperado, incluindo o item específico
    return { 
      budget: {
        ...budget,
        // Filtrar apenas o item específico para generateEventTitle funcionar corretamente
        items: budget.items.filter(item => item.id === budgetItemId)
      }, 
      client,
      specificItem // Dados diretos do item para facilitar acesso
    };
  } catch (error) {
    console.error('❌ Erro ao buscar dados do orçamento/cliente:', error);
    throw error;
  }
};

// Componente principal do Modo Técnico
export function TechnicianMode() {
  const [currentMode, setCurrentMode] = useState('selection'); // selection | street | company
  const [technicianData, setTechnicianData] = useState(null);

  // Carregar dados do técnico logado
  useEffect(() => {
    // TODO: Implementar autenticação do técnico
    setTechnicianData({
      id: 'TECH-001',
      name: 'João Silva',
      role: 'Técnico de Campo'
    });
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 pb-16">
      {/* Header */}
      <div className="bg-blue-600 text-white p-4 shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">Modo Técnico</h1>
            <p className="text-blue-100 text-sm">
              {technicianData?.name || 'Carregando...'}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm">{new Date().toLocaleDateString('pt-BR')}</p>
            <p className="text-blue-100 text-xs">
              {new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
            </p>
          </div>
        </div>
      </div>

      {/* Conteúdo Principal */}
      {currentMode === 'selection' && (
        <ModeSelection onModeSelect={setCurrentMode} />
      )}
      
      {currentMode === 'street' && (
        <StreetMode onBack={() => setCurrentMode('selection')} />
      )}
      
      {currentMode === 'company' && (
        <CompanyMode onBack={() => setCurrentMode('selection')} />
      )}
    </div>
  );
}

// Componente de Seleção de Modo
function ModeSelection({ onModeSelect }) {
  return (
    <div className="p-6 space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">Selecione o Modo</h2>
        <p className="text-gray-600">Escolha o ambiente de trabalho</p>
      </div>

      {/* Modo Rua */}
      <div 
        onClick={() => onModeSelect('street')}
        className="bg-white rounded-lg shadow-md p-6 border-l-4 border-blue-500 cursor-pointer hover:shadow-lg transition-shadow"
      >
        <div className="flex items-center space-x-4">
          <div className="bg-blue-100 p-3 rounded-full">
            <Car className="w-8 h-8 text-blue-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-800">Modo Rua</h3>
            <p className="text-gray-600 text-sm">Atendimento externo aos clientes</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">RETIRAR</span>
              <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded text-xs">EXECUTAR_NO_LOCAL</span>
              <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">ENTREGAR</span>
            </div>
          </div>
        </div>
      </div>

      {/* Modo Empresa */}
      <div 
        onClick={() => onModeSelect('company')}
        className="bg-white rounded-lg shadow-md p-6 border-l-4 border-orange-500 cursor-pointer hover:shadow-lg transition-shadow"
      >
        <div className="flex items-center space-x-4">
          <div className="bg-orange-100 p-3 rounded-full">
            <Building className="w-8 h-8 text-orange-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-800">Modo Empresa</h3>
            <p className="text-gray-600 text-sm">Operação interna e controle produtivo</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs">CLIENTE_TROUXE</span>
              <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">EM_LAVAGEM</span>
              <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">AGUARDANDO_ENTREGA</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Componente Modo Rua
function StreetMode({ onBack }) {
  const [activeTab, setActiveTab] = useState('agenda');
  const [dailyClients, setDailyClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showOnlyToday, setShowOnlyToday] = useState(true); // Novo filtro por data

  useEffect(() => {
    loadDailyAgenda();
  }, []);

  const loadDailyAgenda = async () => {
    try {
      setLoading(true);
      
      // Buscar tarefas híbridas do técnico para múltiplas datas se necessário
      const today = new Date().toISOString().split('T')[0];
      console.log(`📅 TechnicianMode: Buscando tarefas para a data: ${today}`);
      
      let response = await technicianApi.getDailyTasks(
        'TECH-001', // TODO: Usar technicianData.id quando disponível
        today
      );
      
      // Se não encontrou assignments para hoje, tentar datas próximas
      let allAssignments = response.data.assignments || [];
      let allStatusItems = response.data.status_items || [];
      let allAgendaEvents = response.data.agenda_events || [];
      
      if (allAssignments.length === 0) {
        console.log('🔍 Nenhum assignment encontrado para hoje, buscando em datas próximas...');
        
        // Tentar ontem e amanhã
        const dates = [
          new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString().split('T')[0], // Ontem
          new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().split('T')[0], // Amanhã
        ];
        
        for (const date of dates) {
          console.log(`🔍 Tentando data: ${date}`);
          const dateResponse = await technicianApi.getDailyTasks('TECH-001', date);
          
          if (dateResponse.data.assignments && dateResponse.data.assignments.length > 0) {
            console.log(`✅ Encontrou ${dateResponse.data.assignments.length} assignments para ${date}`);
            allAssignments = [...allAssignments, ...dateResponse.data.assignments];
            allStatusItems = [...allStatusItems, ...dateResponse.data.status_items];
            allAgendaEvents = [...allAgendaEvents, ...dateResponse.data.agenda_events];
          }
        }
      }
      
      // Usar dados combinados
      const combinedResponse = {
        assignments: allAssignments,
        status_items: allStatusItems,
        agenda_events: allAgendaEvents
      };
      
      console.log('📋 Tarefas híbridas recebidas:', combinedResponse);
      
      const { agenda_events, status_items, assignments } = combinedResponse;
      
      // Combinar dados de agenda e status em um formato unificado
      const unifiedClients = {};
      
      // 1. Processar assignments da agenda (filtrar cancelados) - DESENCAPSULAR
      for (const assignment of assignments.filter(a => a.status !== 'CANCELLED')) {
        // Buscar dados reais dos eventos para gerar CARDS INDIVIDUAIS por cliente
        console.log(`🔍 Desencapsulando assignment ${assignment.id} com eventos:`, assignment.event_ids);
        
        try {
          // OPÇÃO A: Para cada event_id, criar um CARD INDIVIDUAL
          for (let i = 0; i < assignment.event_ids.length; i++) {
            const eventId = assignment.event_ids[i];
            
            try {
              let clientName = 'Cliente';
              let clientAddress = 'Endereço não disponível';
              let clientPhone = '(65) 99999-9999';
              let totalValue = 0;
              let displayTitle = `📋 Agendamento ${assignment.id.slice(-8)}`;
              
              // CORREÇÃO: Verificar se é um budget_item_id válido (ITM-XXXXXXX) ou event_id fictício (EVT-XXX)
              if (eventId.startsWith('ITM-')) {
                console.log(`✅ Processando budget_item_id individual: ${eventId}`);
                
                try {
                  // Buscar dados do budget item específico usando nova abordagem
                  const { budget, client, specificItem } = await getBudgetAndClientData(eventId);
                  
                  console.log(`📊 Dados obtidos para ${eventId}:`, {
                    budget_code: budget.code,
                    client_name: client.name,
                    service_name: specificItem.service_name,
                    items_count: budget.items?.length || 0
                  });
                  
                  // USAR NOME REAL DO SERVIÇO diretamente do specificItem
                  const realServiceName = specificItem.service_name;
                  const serviceEmoji = getServiceEmoji(realServiceName);
                  const serviceStatus = specificItem.status || 'EXECUTAR_NO_LOCAL';
                  
                  // Gerar título bonito com nome real do serviço
                  let statusText = '';
                  if (serviceStatus === 'RETIRAR') statusText = 'RETIRAR ';
                  else if (serviceStatus === 'ENTREGAR') statusText = 'ENTREGAR ';
                  
                  displayTitle = `${serviceEmoji}${statusText}${client.name} - ${realServiceName}`;
                  
                  console.log(`🎨 Título com nome real gerado: "${displayTitle}"`);
                  
                  // Usar dados reais do cliente COM ENDEREÇO CORRETO
                  clientName = client.name;
                  clientAddress = getClientAddress(client); // CORREÇÃO: Usar função para extrair endereço correto
                  clientPhone = client.phone || '(65) 99999-9999';
                  
                  console.log(`📍 Endereço extraído corretamente: "${clientAddress}"`);
                  
                  // Usar valor do item específico
                  totalValue = parseFloat(specificItem.service_value || 0);
                  
                } catch (budgetError) {
                  console.error(`❌ Erro ao buscar dados do orçamento ${eventId}:`, budgetError);
                  
                  // FALLBACK MELHORADO: Tentar buscar da lista de itens disponíveis diretamente
                  try {
                    console.log(`🔄 Tentando fallback direto para ${eventId}...`);
                    
                    const availableItemsResponse = await fetch(`${BACKEND_URL}/api/budget-items/available-for-routes`);
                    if (availableItemsResponse.ok) {
                      const availableData = await availableItemsResponse.json();
                      const directItem = availableData.available_items.find(item => item.budget_item_id === eventId);
                      
                      if (directItem) {
                        displayTitle = `${getServiceEmoji(directItem.service_name)} ${directItem.client_name} - ${directItem.service_name}`;
                        clientName = directItem.client_name;
                        totalValue = parseFloat(directItem.service_value || 0);
                        
                        console.log(`✅ Fallback direto funcionou: "${displayTitle}"`);
                      } else {
                        throw new Error('Item não encontrado no fallback direto');
                      }
                    } else {
                      throw new Error('Fallback direto falhou');
                    }
                  } catch (fallbackError) {
                    console.error(`❌ Fallback direto também falhou:`, fallbackError);
                    
                    // ÚLTIMO FALLBACK: Nome mais descritivo
                    displayTitle = `🔧 Serviço de Cliente (${eventId.slice(-6)})`;
                  }
                }
                
              } else {
                console.log(`⚠️ Event ID fictício detectado: ${eventId} - usando fallback`);
                displayTitle = `🔧 Evento ${eventId}`;
              }
              
              // Criar ID único para este card individual
              const individualCardId = `${assignment.id}-${i}`;
              
              unifiedClients[individualCardId] = {
                id: individualCardId,
                name: displayTitle, // Título individual por cliente
                address: clientAddress,
                phone: clientPhone,
                scheduledTime: assignment.assigned_time || '08:00',
                scheduledDate: assignment.assigned_date,
                items: [{
                  id: `${individualCardId}-item`,
                  name: displayTitle,
                  status: assignment.status,
                  value: totalValue,
                  observations: `Evento ${i + 1}/${assignment.event_ids.length} do agendamento ${assignment.id}`
                }],
                internalObservations: `Agendamento criado em ${new Date(assignment.created_at).toLocaleDateString('pt-BR')}`,
                source: 'AGENDA_ASSIGNMENT',
                assigned_date: assignment.assigned_date,
                status: assignment.status,
                event_ids: [eventId], // Apenas este event_id específico
                total_value: totalValue,
                original_assignment_id: assignment.id // Referência ao assignment original
              };
              
              console.log(`✅ Card individual ${individualCardId} criado: "${displayTitle}"`);
              
            } catch (eventError) {
              console.error(`❌ Erro ao processar evento individual ${eventId}:`, eventError);
              
              // Fallback para evento com erro
              const fallbackCardId = `${assignment.id}-${i}-fallback`;
              
              // FALLBACK MELHORADO: Tentar buscar nome real do serviço
              let fallbackTitle = `🔧 Serviço de Cliente (${eventId.slice(-6)})`;
              let fallbackValue = 0;
              let fallbackName = 'Cliente';
              
              try {
                console.log(`🔄 Tentando buscar dados para fallback do evento ${eventId}...`);
                
                const availableItemsResponse = await fetch(`${BACKEND_URL}/api/budget-items/available-for-routes`);
                if (availableItemsResponse.ok) {
                  const availableData = await availableItemsResponse.json();
                  const fallbackItem = availableData.available_items.find(item => item.budget_item_id === eventId);
                  
                  if (fallbackItem) {
                    fallbackTitle = `${getServiceEmoji(fallbackItem.service_name)} ${fallbackItem.client_name} - ${fallbackItem.service_name}`;
                    fallbackValue = parseFloat(fallbackItem.service_value || 0);
                    fallbackName = fallbackItem.client_name;
                    
                    console.log(`✅ Fallback com nome real funcionou: "${fallbackTitle}"`);
                  }
                }
              } catch (fallbackError) {
                console.error(`❌ Fallback para nomes reais falhou:`, fallbackError);
              }
              
              unifiedClients[fallbackCardId] = {
                id: fallbackCardId,
                name: fallbackTitle,
                address: assignment.route_id ? `Rota: ${assignment.route_id}` : 'Eventos diversos',
                phone: '(65) 99999-9999',
                scheduledTime: assignment.assigned_time || '08:00',
                scheduledDate: assignment.assigned_date,
                items: [],
                internalObservations: `Agendamento criado em ${new Date(assignment.created_at).toLocaleDateString('pt-BR')}`,
                source: 'AGENDA_ASSIGNMENT',
                assigned_date: assignment.assigned_date,
                status: assignment.status,
                event_ids: [eventId],
                total_value: fallbackValue,
                original_assignment_id: assignment.id
              };
            }
          }
          
        } catch (assignmentError) {
          console.error(`❌ Erro ao desencapsular assignment ${assignment.id}:`, assignmentError);
          
          // Fallback para assignment inteiro com erro
          const fallbackId = assignment.id;
          unifiedClients[fallbackId] = {
            id: fallbackId,
            name: `📋 Agendamento ${assignment.id.slice(-8)}`,
            address: assignment.route_id ? `Rota: ${assignment.route_id}` : 'Eventos diversos',
            phone: '(65) 99999-9999',
            scheduledTime: assignment.assigned_time || '08:00',
            scheduledDate: assignment.assigned_date,
            items: [],
            internalObservations: `Agendamento do tipo ${assignment.assignment_type} criado em ${new Date(assignment.created_at).toLocaleDateString('pt-BR')}`,
            source: 'AGENDA_ASSIGNMENT',
            assigned_date: assignment.assigned_date,
            status: assignment.status,
            event_ids: assignment.event_ids,
            total_value: 0
          };
        }
      }
      
      // 2. Processar itens por status
      for (const item of status_items) {
        const clientId = item.client_id;
        
        if (!unifiedClients[clientId]) {
          // CORREÇÃO: Usar função helper para extrair endereço correto de status_items
          const formattedAddress = item.client_address && typeof item.client_address === 'object' 
            ? (item.client_address.full_address || 'Endereço não informado')
            : item.client_address || 'Endereço não informado';
            
          unifiedClients[clientId] = {
            id: clientId,
            name: item.client_name,
            address: formattedAddress,
            phone: item.client_phone,
            scheduledTime: '08:00', // TODO: Definir lógica de horário
            items: [],
            internalObservations: item.internal_observations,
            budgetObservations: null, // Será preenchido abaixo
            source: 'STATUS_BASED'
          };
          
          // Buscar observações do orçamento
          if (item.budget_id) {
            try {
              const budgetResponse = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/budgets/${item.budget_id}`);
              if (budgetResponse.ok) {
                const budgetData = await budgetResponse.json();
                unifiedClients[clientId].budgetObservations = budgetData.budget_observations;
                console.log(`✅ Observações do orçamento ${item.budget_id}: ${budgetData.budget_observations}`);
              }
            } catch (budgetError) {
              console.warn(`⚠️ Erro ao buscar orçamento ${item.budget_id}:`, budgetError);
            }
          }
        }
        
        unifiedClients[clientId].items.push({
          id: item.id,
          name: item.service_name,
          status: item.status,
          value: parseFloat(item.service_value),
          observations: item.observations
        });
      }
      
      // Converter para array e ordenar por data
      const clientsArray = Object.values(unifiedClients);
      
      // Ordenar por data e tipo de fonte (assignments da agenda primeiro, depois status items)
      clientsArray.sort((a, b) => {
        // Priorizar assignments da agenda
        if (a.source === 'AGENDA_ASSIGNMENT' && b.source !== 'AGENDA_ASSIGNMENT') return -1;
        if (b.source === 'AGENDA_ASSIGNMENT' && a.source !== 'AGENDA_ASSIGNMENT') return 1;
        
        // Ordenar por data (assignments têm assigned_date, status items usam data atual)
        const dateA = a.assigned_date || new Date().toISOString().split('T')[0];
        const dateB = b.assigned_date || new Date().toISOString().split('T')[0];
        
        if (dateA !== dateB) {
          return dateA.localeCompare(dateB);
        }
        
        // Se mesma data, ordenar por horário agendado
        return a.scheduledTime.localeCompare(b.scheduledTime);
      });
      
      console.log('👥 Clientes unificados (ordenados por data e tipo):', clientsArray);
      
      setDailyClients(clientsArray);
      setLoading(false);
      
    } catch (error) {
      console.error('Erro ao carregar agenda híbrida:', error);
      
      // Fallback para dados mock em caso de erro
      const mockClients = [
        {
          id: 'CLI-001',
          name: 'João Silva',
          address: 'Rua das Flores, 123 - Centro',
          phone: '(11) 99999-9999',
          scheduledTime: '08:30',
          items: [
            { id: 'ITM-001', name: 'Sofá 3 Lugares', status: 'EXECUTAR_NO_LOCAL', value: 320.00, observations: 'Mancha no braço direito' },
            { id: 'ITM-002', name: 'Cadeira Presidencial', status: 'EXECUTAR_NO_LOCAL', value: 80.00, observations: '' }
          ],
          internalObservations: 'Cliente preferencial. Cuidado com pets.',
          source: 'MOCK'
        },
        {
          id: 'CLI-002', 
          name: 'Maria Santos',
          address: 'Av. Principal, 456 - Jardins',
          phone: '(11) 88888-8888',
          scheduledTime: '10:00',
          items: [
            { id: 'ITM-003', name: 'Tapete Persa 2x3m', status: 'RETIRAR', value: 150.00, observations: 'Cuidado com as franjas' }
          ],
          internalObservations: 'Portão azul, tocar interfone.',
          source: 'MOCK'
        }
      ];
      
      setDailyClients(mockClients);
      setLoading(false);
    }
  };

  const generateNavigationLink = (address) => {
    const wazeUrl = `https://waze.com/ul?q=${encodeURIComponent(address)}`;
    const mapsUrl = `https://maps.google.com/maps?q=${encodeURIComponent(address)}`;
    return { wazeUrl, mapsUrl };
  };

  return (
    <div>
      {/* Header com botão voltar */}
      <div className="bg-blue-600 text-white p-4 flex items-center">
        <button onClick={onBack} className="mr-3">
          <span className="text-xl">←</span>
        </button>
        <h2 className="text-lg font-semibold">Modo Rua</h2>
      </div>

      {/* Tabs de navegação */}
      <div className="bg-white shadow-sm">
        <div className="flex">
          <TabButton 
            active={activeTab === 'agenda'} 
            onClick={() => setActiveTab('agenda')}
            icon={<Calendar className="w-4 h-4" />}
            label="Agenda"
          />
          <TabButton 
            active={activeTab === 'payments'} 
            onClick={() => setActiveTab('payments')}
            icon={<CreditCard className="w-4 h-4" />}
            label="Pagamentos"
          />
          <TabButton 
            active={activeTab === 'tickets'} 
            onClick={() => setActiveTab('tickets')}
            icon={<Phone className="w-4 h-4" />}
            label="Chamados"
          />
          <TabButton 
            active={activeTab === 'photos'} 
            onClick={() => setActiveTab('photos')}
            icon={<Camera className="w-4 h-4" />}
            label="Fotos"
          />
        </div>
      </div>

      {/* Conteúdo das tabs */}
      <div className="p-4">
        {activeTab === 'agenda' && (
          <AgendaTab clients={dailyClients} loading={loading} generateNavigationLink={generateNavigationLink} />
        )}
        {activeTab === 'payments' && <PaymentsTab />}
        {activeTab === 'tickets' && <TicketsTab />}
        {activeTab === 'photos' && <PhotosTab />}
      </div>
    </div>
  );
}

// Componente da Tab Agenda
function AgendaTab({ clients, loading, generateNavigationLink }) {
  const [selectedClient, setSelectedClient] = useState(null);
  const [showOnlyToday, setShowOnlyToday] = useState(true);
  
  // Filtrar clientes por data
  const filteredClients = clients.filter(client => {
    if (!showOnlyToday) return true; // Mostrar todos
    
    const today = new Date().toISOString().split('T')[0];
    const clientDate = client.assigned_date || today;
    
    return clientDate === today;
  });

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-2 text-gray-600">Carregando agenda...</p>
      </div>
    );
  }

  if (selectedClient) {
    return (
      <ClientDetails 
        client={selectedClient} 
        onBack={() => setSelectedClient(null)}
        generateNavigationLink={generateNavigationLink}
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* Filtros */}
      <div className="bg-white rounded-lg shadow-md p-4 border border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-800">
            Agenda do Dia - {filteredClients.length} cliente(s)
          </h3>
          
          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={showOnlyToday}
                onChange={(e) => setShowOnlyToday(e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="text-sm text-gray-700">Apenas hoje</span>
            </label>
            
            <div className="text-sm text-gray-500">
              {showOnlyToday 
                ? `Hoje (${new Date().toLocaleDateString('pt-BR')})` 
                : 'Todos os pendentes'
              }
            </div>
          </div>
        </div>
      </div>
      
      {filteredClients.map(client => (
        <ClientCard 
          key={client.id} 
          client={client} 
          onClick={() => setSelectedClient(client)}
          generateNavigationLink={generateNavigationLink}
        />
      ))}
    </div>
  );
}

// Card do Cliente
function ClientCard({ client, onClick, generateNavigationLink }) {
  const { wazeUrl, mapsUrl } = generateNavigationLink(getClientAddress(client));
  
  const totalValue = client.items.reduce((sum, item) => sum + item.value, 0);
  
  const handleRemoveAssignment = async (assignmentId) => {
    try {
      console.log(`🗑️ Removendo assignment ${assignmentId} da agenda`);
      
      // Confirmar ação com o usuário
      if (!window.confirm('Tem certeza que deseja remover este serviço da sua agenda? Esta ação não pode ser desfeita.')) {
        return;
      }
      
      // Marcar assignment como CANCELLED (não existe endpoint DELETE)
      const response = await technicianApi.updateAssignmentStatus(assignmentId, 'CANCELLED');
      
      console.log(`✅ Assignment ${assignmentId} marcado como cancelado:`, response.data);
      
      alert('Serviço removido da sua agenda com sucesso!');
      
      // Recarregar dados da agenda
      window.location.reload(); // Solução temporária - TODO: implementar reload otimizado
      
    } catch (error) {
      console.error(`❌ Erro ao remover assignment ${assignmentId}:`, error);
      alert('Erro ao remover da agenda. Tente novamente.');
    }
  };
  
  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200">
      {/* Header do card */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {/* Ícone específico por tipo de source */}
            {client.source === 'AGENDA_ASSIGNMENT' ? (
              <Calendar className="w-4 h-4 text-purple-600" />
            ) : (
              <MapPin className="w-4 h-4 text-blue-600" />
            )}
            <span className="font-semibold text-gray-800">{client.name}</span>
            
            {/* CORREÇÃO: Mostrar data + horário ao invés de apenas horário */}
            <div className="flex flex-col">
              <span className="text-blue-600 font-medium text-sm">{client.scheduledTime}</span>
              {client.scheduledDate && (
                <span className="text-gray-500 text-xs">
                  {new Date(client.scheduledDate).toLocaleDateString('pt-BR')}
                </span>
              )}
            </div>
            
            {/* Badge do tipo de source */}
            {client.source === 'AGENDA_ASSIGNMENT' ? (
              <span className="px-2 py-1 text-xs font-medium bg-purple-100 text-purple-800 rounded-full">
                Agenda
              </span>
            ) : (
              <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                Status
              </span>
            )}
          </div>
          <div className="text-right">
            <p className="text-sm font-medium text-green-600">R$ {totalValue.toFixed(2)}</p>
            {/* Mostrar data se for assignment da agenda */}
            {client.assigned_date && (
              <p className="text-xs text-gray-500">
                {new Date(client.assigned_date).toLocaleDateString('pt-BR')}
              </p>
            )}
          </div>
        </div>
        <p className="text-sm text-gray-600 mt-1">{getClientAddress(client)}</p>
        
        {/* Status do assignment se for da agenda */}
        {client.source === 'AGENDA_ASSIGNMENT' && (
          <div className="mt-2 flex items-center space-x-2">
            <span className={`px-2 py-1 text-xs font-medium rounded-full ${
              client.status === 'ASSIGNED' ? 'bg-yellow-100 text-yellow-800' :
              client.status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-800' :
              client.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {client.status}
            </span>
            {client.event_ids && (
              <span className="text-xs text-gray-500">
                {client.event_ids.length} evento(s) da agenda
              </span>
            )}
          </div>
        )}
      </div>

      {/* Items summary */}
      <div className="p-4">
        <div className="flex flex-wrap gap-2 mb-3">
          {client.items.map(item => (
            <div key={item.id} className="flex items-center space-x-1">
              <span className="text-sm">
                {item.status === 'EXECUTAR_NO_LOCAL' ? '🛋️' : 
                 item.status === 'RETIRAR' ? '📦' : 
                 item.status === 'ENTREGAR' ? '🚚' : '✨'}
              </span>
              <span className="text-sm text-gray-700">{item.name}</span>
            </div>
          ))}
        </div>

        {/* Action buttons */}
        <div className="flex space-x-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              window.open(wazeUrl, '_blank');
            }}
            className="flex-1 bg-green-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-green-700 transition-colors flex items-center justify-center space-x-1"
          >
            <Navigation className="w-4 h-4" />
            <span>Waze</span>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              window.open(mapsUrl, '_blank');
            }}
            className="flex-1 bg-blue-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors flex items-center justify-center space-x-1"
          >
            <MapPin className="w-4 h-4" />
            <span>Maps</span>
          </button>
          <button
            onClick={onClick}
            className="flex-1 bg-gray-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors flex items-center justify-center space-x-1"
          >
            <User className="w-4 h-4" />
            <span>Iniciar Atendimento</span>
          </button>
          
          {/* Botão Remover para assignments da agenda */}
          {client.source === 'AGENDA_ASSIGNMENT' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleRemoveAssignment(client.id);
              }}
              className="bg-red-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-red-700 transition-colors flex items-center justify-center"
              title="Remover da minha agenda"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// Detalhes do Cliente
function ClientDetails({ client, onBack, generateNavigationLink }) {
  const [selectedItems, setSelectedItems] = useState(new Set());
  const [technicianNotes, setTechnicianNotes] = useState('');
  const [showPhotoCapture, setShowPhotoCapture] = useState(true); // Iniciar com captura de fotos
  const [itemPhotos, setItemPhotos] = useState({}); // {itemId: [photos]}
  const [uploadingPhotos, setUploadingPhotos] = useState(false);

  const handleItemSelect = (itemId, checked) => {
    const newSelected = new Set(selectedItems);
    if (checked) {
      newSelected.add(itemId);
    } else {
      newSelected.delete(itemId);
    }
    setSelectedItems(newSelected);
  };

  // Verificar se todos os itens têm pelo menos uma foto
  const allItemsHavePhotos = () => {
    return client.items.every(item => {
      const photos = itemPhotos[item.id] || [];
      return photos.length > 0;
    });
  };

  // Prosseguir para o atendimento após captura de fotos
  const proceedToService = () => {
    if (!allItemsHavePhotos()) {
      alert('Por favor, registre pelo menos uma foto para cada item antes de prosseguir.');
      return;
    }
    setShowPhotoCapture(false);
  };

  // Se ainda está na fase de captura de fotos
  if (showPhotoCapture) {
    return (
      <PhotoCaptureScreen 
        client={client}
        onBack={onBack}
        itemPhotos={itemPhotos}
        setItemPhotos={setItemPhotos}
        uploadingPhotos={uploadingPhotos}
        setUploadingPhotos={setUploadingPhotos}
        onProceed={proceedToService}
        allItemsHavePhotos={allItemsHavePhotos}
      />
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center mb-4">
        <button onClick={onBack} className="mr-3 text-blue-600">
          <span className="text-xl">←</span>
        </button>
        <h3 className="text-lg font-semibold text-gray-800">{client.name}</h3>
      </div>

      {/* Client Info */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-4">
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <MapPin className="w-4 h-4 text-blue-600" />
            <span className="text-sm text-gray-700">{getClientAddress(client)}</span>
          </div>
          <div className="flex items-center space-x-2">
            <Phone className="w-4 h-4 text-green-600" />
            <span className="text-sm text-gray-700">{client.phone}</span>
          </div>
          
          {/* Observações logo após o endereço */}
          {(client.internalObservations || client.budgetObservations) && (
            <div className="mt-3 space-y-2">
              {client.internalObservations && (
                <div className="p-2 bg-blue-50 rounded-md">
                  <p className="text-xs font-medium text-blue-800">📝 Observações Internas:</p>
                  <p className="text-xs text-blue-700">{client.internalObservations}</p>
                </div>
              )}
              {client.budgetObservations && (
                <div className="p-2 bg-green-50 rounded-md">
                  <p className="text-xs font-medium text-green-800">💰 Observações do Orçamento:</p>
                  <p className="text-xs text-green-700">{client.budgetObservations}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Items List */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-4">
        <h4 className="font-medium text-gray-800 mb-3">Itens/Serviços</h4>
        <div className="space-y-3">
          {client.items.map(item => (
            <div key={item.id} className="border border-gray-200 rounded-md p-3">
              <div className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  checked={selectedItems.has(item.id)}
                  onChange={(e) => handleItemSelect(item.id, e.target.checked)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-800">{item.name}</span>
                    <span className="font-medium text-green-600">R$ {item.value.toFixed(2)}</span>
                  </div>
                  <p className="text-sm text-gray-600">Status: {item.status}</p>
                  {item.observations && (
                    <p className="text-sm text-gray-500 italic">Obs: {item.observations}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Technician Notes */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-4">
        <h4 className="font-medium text-gray-800 mb-3">Observações do Técnico</h4>
        <textarea
          value={technicianNotes}
          onChange={(e) => setTechnicianNotes(e.target.value)}
          placeholder="Adicione observações sobre o atendimento..."
          className="w-full p-3 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          rows={3}
        />
      </div>

      {/* Action Buttons */}
      {selectedItems.size > 0 && (
        <div className="bg-white rounded-lg shadow-md p-4">
          <h4 className="font-medium text-gray-800 mb-3">Ações para {selectedItems.size} item(s)</h4>
          <div className="grid grid-cols-2 gap-2">
            <button className="bg-green-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-green-700 transition-colors flex items-center justify-center space-x-1">
              <CheckCircle className="w-4 h-4" />
              <span>Serviço Concluído</span>
            </button>
            <button className="bg-blue-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors flex items-center justify-center space-x-1">
              <Package className="w-4 h-4" />
              <span>Retirada Efetuada</span>
            </button>
            <button className="bg-purple-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-purple-700 transition-colors flex items-center justify-center space-x-1">
              <Truck className="w-4 h-4" />
              <span>Entrega Efetuada</span>
            </button>
            <button className="bg-orange-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-orange-700 transition-colors flex items-center justify-center space-x-1">
              <User className="w-4 h-4" />
              <span>Cliente Buscou</span>
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-2">
            <button className="bg-red-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-red-700 transition-colors">
              Cancelado pelo Cliente
            </button>
            <button className="bg-yellow-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-yellow-700 transition-colors">
              Reagendar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Componente Modo Empresa (Básico)
function CompanyMode({ onBack }) {
  const [statusCounts, setStatusCounts] = useState({
    CLIENTE_TROUXE: 2,
    COLETADO: 3, 
    EM_LAVAGEM: 5,
    EM_LAVAGEM_PARCEIRO: 3,
    AGUARDANDO_ENTREGA: 7,
    AGUARDANDO_BUSCAR: 5
  });

  return (
    <div>
      {/* Header */}
      <div className="bg-orange-600 text-white p-4 flex items-center">
        <button onClick={onBack} className="mr-3">
          <span className="text-xl">←</span>
        </button>
        <h2 className="text-lg font-semibold">Modo Empresa</h2>
      </div>

      <div className="p-4 space-y-4">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Controle Produtivo</h3>
        
        {/* Recepção */}
        <StatusSection 
          title="📥 RECEPÇÃO" 
          items={[
            { status: 'CLIENTE_TROUXE', count: statusCounts.CLIENTE_TROUXE, color: 'yellow' },
            { status: 'COLETADO', count: statusCounts.COLETADO, color: 'blue' }
          ]}
        />

        {/* Lavagem */}
        <StatusSection 
          title="🧽 LAVAGEM" 
          items={[
            { status: 'EM_LAVAGEM', count: statusCounts.EM_LAVAGEM, color: 'blue' },
            { status: 'EM_LAVAGEM_PARCEIRO', count: statusCounts.EM_LAVAGEM_PARCEIRO, color: 'indigo' }
          ]}
        />

        {/* Depósito Saída */}
        <StatusSection 
          title="📦 DEPÓSITO SAÍDA" 
          items={[
            { status: 'AGUARDANDO_ENTREGA', count: statusCounts.AGUARDANDO_ENTREGA, color: 'green' },
            { status: 'AGUARDANDO_BUSCAR', count: statusCounts.AGUARDANDO_BUSCAR, color: 'purple' }
          ]}
        />
      </div>
    </div>
  );
}

// Componente de Seção de Status
function StatusSection({ title, items }) {
  const totalCount = items.reduce((sum, item) => sum + item.count, 0);
  
  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-gray-800">{title}</h4>
        <span className="bg-gray-100 text-gray-800 px-2 py-1 rounded text-sm font-medium">
          {totalCount} itens
        </span>
      </div>
      <div className="space-y-2">
        {items.map(item => (
          <div key={item.status} className="flex items-center justify-between p-2 bg-gray-50 rounded">
            <span className="text-sm text-gray-700">{item.status}</span>
            <span className={`px-2 py-1 rounded text-xs font-medium
              ${item.color === 'yellow' ? 'bg-yellow-100 text-yellow-800' :
                item.color === 'blue' ? 'bg-blue-100 text-blue-800' :
                item.color === 'indigo' ? 'bg-indigo-100 text-indigo-800' :
                item.color === 'green' ? 'bg-green-100 text-green-800' :
                item.color === 'purple' ? 'bg-purple-100 text-purple-800' :
                'bg-gray-100 text-gray-800'}`}>
              {item.count}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Componentes de Tab (Placeholders)
function PaymentsTab() {
  return (
    <div className="text-center py-8 text-gray-500">
      <CreditCard className="w-12 h-12 mx-auto mb-2 opacity-50" />
      <p>Sistema de Pagamentos</p>
      <p className="text-sm">Em desenvolvimento</p>
    </div>
  );
}

function TicketsTab() {
  return (
    <div className="text-center py-8 text-gray-500">
      <Phone className="w-12 h-12 mx-auto mb-2 opacity-50" />
      <p>Sistema de Chamados</p>
      <p className="text-sm">Em desenvolvimento</p>
    </div>
  );
}

function PhotosTab() {
  return (
    <div className="text-center py-8 text-gray-500">
      <Camera className="w-12 h-12 mx-auto mb-2 opacity-50" />
      <p>Sistema de Fotos</p>
      <p className="text-sm">Em desenvolvimento</p>
    </div>
  );
}

// Componente de Tab Button
function TabButton({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 flex flex-col items-center py-3 px-2 text-xs font-medium transition-colors
        ${active 
          ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50' 
          : 'text-gray-500 hover:text-gray-700'}`}
    >
      {icon}
      <span className="mt-1">{label}</span>
    </button>
  );
}

// Componente de Captura de Fotos
function PhotoCaptureScreen({ client, onBack, itemPhotos, setItemPhotos, uploadingPhotos, setUploadingPhotos, onProceed, allItemsHavePhotos }) {
  const [selectedFiles, setSelectedFiles] = useState({});
  
  // Backend URL
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

  const handleFileSelect = (itemId, files) => {
    const newSelectedFiles = { ...selectedFiles };
    newSelectedFiles[itemId] = files;
    setSelectedFiles(newSelectedFiles);
  };

  const handlePhotoUpload = async (itemId) => {
    const files = selectedFiles[itemId];
    if (!files || files.length === 0) {
      alert('Selecione pelo menos uma foto para este item.');
      return;
    }

    setUploadingPhotos(true);
    
    try {
      const formData = new FormData();
      formData.append('item_id', itemId);
      formData.append('technician_id', 'TECH-001'); // TODO: Usar técnico logado
      formData.append('photo_type', 'BEFORE');
      
      if (client.original_assignment_id) {
        formData.append('assignment_id', client.original_assignment_id);
      }
      
      // Adicionar todas as fotos ao FormData
      for (let file of files) {
        formData.append('files', file);
      }
      
      // Upload real para o backend
      const response = await fetch(`${BACKEND_URL}/api/technician/upload-photos`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Erro no upload: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('✅ Upload realizado com sucesso:', result);
      
      // Criar previews locais das fotos
      const uploadedPhotos = [];
      for (let file of files) {
        const photoPreview = {
          id: Date.now() + Math.random(),
          file: file,
          url: URL.createObjectURL(file),
          name: file.name,
          size: file.size,
          type: file.type,
          timestamp: new Date().toISOString()
        };
        uploadedPhotos.push(photoPreview);
      }
      
      // Atualizar estado das fotos
      const newItemPhotos = { ...itemPhotos };
      if (!newItemPhotos[itemId]) {
        newItemPhotos[itemId] = [];
      }
      newItemPhotos[itemId] = [...newItemPhotos[itemId], ...uploadedPhotos];
      setItemPhotos(newItemPhotos);
      
      // Limpar seleção de arquivos
      const newSelectedFiles = { ...selectedFiles };
      delete newSelectedFiles[itemId];
      setSelectedFiles(newSelectedFiles);
      
      alert(`${uploadedPhotos.length} foto(s) enviada(s) com sucesso!`);
      
    } catch (error) {
      console.error('❌ Erro ao fazer upload das fotos:', error);
      alert('Erro ao fazer upload das fotos. Verifique sua conexão e tente novamente.');
    } finally {
      setUploadingPhotos(false);
    }
  };

  const removePhoto = (itemId, photoId) => {
    const newItemPhotos = { ...itemPhotos };
    newItemPhotos[itemId] = newItemPhotos[itemId].filter(photo => photo.id !== photoId);
    setItemPhotos(newItemPhotos);
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center mb-4">
        <button onClick={onBack} className="mr-3 text-blue-600">
          <span className="text-xl">←</span>
        </button>
        <h3 className="text-lg font-semibold text-gray-800">Registro Fotográfico - {client.name}</h3>
      </div>

      {/* Instruções */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
        <div className="flex items-start space-x-2">
          <Camera className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-medium text-yellow-800 mb-2">Antes de iniciar o serviço registre a situação inicial do Item:</h4>
            <p className="text-sm text-yellow-700">
              Capture fotos do estado atual de cada item antes de iniciar o trabalho. 
              É obrigatório registrar pelo menos uma foto para cada item listado abaixo.
            </p>
          </div>
        </div>
      </div>

      {/* Lista de Items para Fotografar */}
      <div className="space-y-4 mb-6">
        {client.items.map(item => {
          const itemPhotosArray = itemPhotos[item.id] || [];
          const hasPhotos = itemPhotosArray.length > 0;
          
          return (
            <div key={item.id} className="bg-white rounded-lg shadow-md border border-gray-200">
              {/* Header do Item */}
              <div className={`p-4 border-b border-gray-100 ${hasPhotos ? 'bg-green-50' : 'bg-red-50'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {hasPhotos ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : (
                      <Camera className="w-5 h-5 text-red-600" />
                    )}
                    <div>
                      <h5 className="font-medium text-gray-800">{item.name}</h5>
                      <p className="text-sm text-gray-600">Status: {item.status} • R$ {item.value.toFixed(2)}</p>
                      {item.observations && (
                        <p className="text-sm text-gray-500 italic">Obs: {item.observations}</p>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      hasPhotos 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {hasPhotos ? `${itemPhotosArray.length} foto(s)` : 'Sem fotos'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Upload de Fotos */}
              <div className="p-4">
                <div className="mb-3">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Selecionar fotos para este item:
                  </label>
                  <input
                    type="file"
                    multiple
                    accept="image/*"
                    capture="environment"
                    onChange={(e) => handleFileSelect(item.id, Array.from(e.target.files))}
                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  />
                </div>

                {selectedFiles[item.id] && selectedFiles[item.id].length > 0 && (
                  <div className="mb-3">
                    <p className="text-sm text-gray-600 mb-2">
                      {selectedFiles[item.id].length} arquivo(s) selecionado(s):
                    </p>
                    <div className="text-xs text-gray-500 space-y-1">
                      {Array.from(selectedFiles[item.id]).map((file, index) => (
                        <div key={index}>• {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)</div>
                      ))}
                    </div>
                    <button
                      onClick={() => handlePhotoUpload(item.id)}
                      disabled={uploadingPhotos}
                      className="mt-2 bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                    >
                      {uploadingPhotos ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          <span>Enviando...</span>
                        </>
                      ) : (
                        <>
                          <Camera className="w-4 h-4" />
                          <span>Adicionar Fotos</span>
                        </>
                      )}
                    </button>
                  </div>
                )}

                {/* Preview das Fotos */}
                {hasPhotos && (
                  <div className="mt-3">
                    <p className="text-sm font-medium text-gray-700 mb-2">Fotos capturadas:</p>
                    <div className="grid grid-cols-2 gap-2">
                      {itemPhotosArray.map(photo => (
                        <div key={photo.id} className="relative">
                          <img
                            src={photo.url}
                            alt={`Foto ${photo.name}`}
                            className="w-full h-24 object-cover rounded-md border border-gray-200"
                          />
                          <button
                            onClick={() => removePhoto(item.id, photo.id)}
                            className="absolute top-1 right-1 bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-700"
                          >
                            ×
                          </button>
                          <div className="text-xs text-gray-500 mt-1 truncate">
                            {photo.name}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Botão para Prosseguir */}
      <div className="bg-white rounded-lg shadow-md p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600">
              Progresso: {Object.values(itemPhotos).filter(photos => photos.length > 0).length} de {client.items.length} itens fotografados
            </p>
            {!allItemsHavePhotos() && (
              <p className="text-sm text-red-600 mt-1">
                Registre fotos para todos os itens antes de prosseguir.
              </p>
            )}
          </div>
          <button
            onClick={onProceed}
            disabled={!allItemsHavePhotos()}
            className={`py-2 px-6 rounded-md text-sm font-medium transition-colors flex items-center space-x-2 ${
              allItemsHavePhotos()
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            <CheckCircle className="w-4 h-4" />
            <span>Prosseguir para Atendimento</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default TechnicianMode;