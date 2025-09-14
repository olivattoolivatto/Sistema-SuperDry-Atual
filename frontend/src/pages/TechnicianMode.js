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

// Função para buscar dados do orçamento e cliente
const getBudgetAndClientData = async (budgetItemId) => {
  try {
    console.log(`🔍 Buscando dados para budget item: ${budgetItemId}`);
    
    // Buscar dados do item do orçamento
    const budgetItemResponse = await fetch(`${BACKEND_URL}/api/budget-items/${budgetItemId}`);
    if (!budgetItemResponse.ok) {
      throw new Error('Erro ao buscar item do orçamento');
    }
    const budgetItem = await budgetItemResponse.json();
    
    // Buscar orçamento completo
    const budgetResponse = await fetch(`${BACKEND_URL}/api/budgets/${budgetItem.budget_id}`);
    if (!budgetResponse.ok) {
      throw new Error('Erro ao buscar orçamento');
    }
    const budget = await budgetResponse.json();
    
    // Buscar dados do cliente
    const clientResponse = await fetch(`${BACKEND_URL}/api/clients/${budget.client_id}`);
    if (!clientResponse.ok) {
      throw new Error('Erro ao buscar cliente');
    }
    const client = await clientResponse.json();
    
    console.log(`✅ Dados encontrados - Cliente: ${client.name}, Orçamento: ${budget.code}, Itens: ${budget.items.length}`);
    
    return { budget, client };
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
      
      // Buscar tarefas híbridas do técnico
      const response = await technicianApi.getDailyTasks(
        'TECH-001', // TODO: Usar technicianData.id quando disponível
        new Date().toISOString().split('T')[0]
      );
      
      console.log('📋 Tarefas híbridas recebidas:', response.data);
      
      const { agenda_events, status_items, assignments } = response.data;
      
      // Combinar dados de agenda e status em um formato unificado
      const unifiedClients = {};
      
      // 1. Processar assignments da agenda (filtrar cancelados)
      for (const assignment of assignments.filter(a => a.status !== 'CANCELLED')) {
        // Buscar dados reais dos eventos para gerar títulos bonitos
        console.log(`🔍 Processando assignment ${assignment.id} com eventos:`, assignment.event_ids);
        
        try {
          // Buscar dados reais dos eventos para gerar títulos bonitos
          const eventTitles = [];
          let totalValue = 0;
          let clientName = 'Cliente';
          let clientAddress = assignment.route_id ? `Rota: ${assignment.route_id}` : 'Endereço não disponível';
          let clientPhone = '(65) 99999-9999';
          
          // Se temos event_ids, vamos buscar os dados reais e gerar título bonito
          if (assignment.event_ids && assignment.event_ids.length > 0) {
            try {
              // Buscar dados do primeiro evento para gerar título
              const firstEventId = assignment.event_ids[0];
              
              // CORREÇÃO: Verificar se é um budget_item_id válido (ITM-XXXXXXX) ou event_id fictício (EVT-XXX)
              if (firstEventId.startsWith('ITM-')) {
                console.log(`✅ Usando budget_item_id válido: ${firstEventId}`);
                
                // Usar função original para budget_item_ids válidos
                const { budget, client } = await getBudgetAndClientData(firstEventId);
                
                // Gerar título bonito usando as mesmas funções da agenda
                const beautifulTitle = generateEventTitle(budget, client.name);
                
                console.log(`🎨 Título bonito gerado para agendamento ${assignment.id}: "${beautifulTitle}"`);
                
                // Usar dados reais do cliente
                clientName = client.name;
                clientAddress = `${client.address} - ${client.neighborhood}, ${client.city}/${client.state}`;
                clientPhone = client.phone || '(65) 99999-9999';
                
                // Calcular valor total dos itens do orçamento
                totalValue = budget.items.reduce((sum, item) => sum + parseFloat(item.service_value || 0), 0);
                
                // Usar o título bonito
                eventTitles.push(beautifulTitle);
                
              } else {
                console.log(`⚠️ Event ID fictício detectado: ${firstEventId} - usando fallback`);
                
                // FALLBACK para event_ids fictícios (EVT-XXX): 
                // Buscar dados da rota associada para obter informações do cliente
                if (assignment.route_id) {
                  try {
                    const routeResponse = await fetch(`${BACKEND_URL}/api/routes/${assignment.route_id}`);
                    if (routeResponse.ok) {
                      const routeData = await routeResponse.json();
                      const stops = routeData.stops || [];
                      
                      if (stops.length > 0) {
                        // Usar dados do primeiro stop como representação
                        const firstStop = stops[0];
                        clientName = firstStop.client_name || 'Cliente da Rota';
                        clientAddress = `${firstStop.address?.street || 'Endereço'} - ${firstStop.neighborhood || 'Bairro'}, ${firstStop.address?.city || 'Cidade'}`;
                        totalValue = stops.reduce((sum, stop) => sum + parseFloat(stop.service_value || 0), 0);
                        
                        // Gerar título simples com nome do cliente
                        const simpleTitle = `✨ ${clientName}`;
                        eventTitles.push(simpleTitle);
                        
                        console.log(`🔄 Fallback aplicado para ${assignment.id}: "${simpleTitle}"`);
                      }
                    }
                  } catch (routeError) {
                    console.error(`❌ Erro ao buscar dados da rota ${assignment.route_id}:`, routeError);
                  }
                }
                
                // Se não conseguiu dados da rota, usar título genérico
                if (eventTitles.length === 0) {
                  eventTitles.push(`📋 Agendamento ${assignment.id.slice(-8)}`);
                }
              }
              
            } catch (eventError) {
              console.error(`❌ Erro ao buscar dados do evento ${assignment.event_ids[0]}:`, eventError);
              // Fallback para o event_id se não conseguir buscar dados
              eventTitles.push(`📋 Assignment ${assignment.id.slice(-8)}`);
            }
          }
          
          // Usar o primeiro título gerado ou fallback
          const displayTitle = eventTitles.length > 0 ? eventTitles[0] : `📋 Agendamento ${assignment.id.slice(-8)}`;
          
          const assignmentId = assignment.id;
          
          unifiedClients[assignmentId] = {
            id: assignmentId,
            name: displayTitle, // Usar título bonito ou fallback inteligente
            address: clientAddress,
            phone: clientPhone,
            scheduledTime: assignment.assigned_time || '08:00', // CORREÇÃO: Usar horário do assignment
            scheduledDate: assignment.assigned_date, // NOVO: Incluir data do assignment
            items: [],
            internalObservations: `Agendamento criado em ${new Date(assignment.created_at).toLocaleDateString('pt-BR')}`,
            source: 'AGENDA_ASSIGNMENT',
            assigned_date: assignment.assigned_date,
            status: assignment.status,
            event_ids: assignment.event_ids,
            total_value: totalValue
          };
          
          // Adicionar um item representativo para o assignment
          unifiedClients[assignmentId].items.push({
            id: `${assignmentId}-summary`,
            name: `${assignment.event_ids.length} evento(s) da agenda`,
            status: assignment.status,
            value: totalValue,
            observations: `Status: ${assignment.status} | Data: ${assignment.assigned_date}`
          });
          
          console.log(`✅ Agendamento ${assignment.id} processado como: "${displayTitle}"`);
          
        } catch (assignmentError) {
          console.error(`❌ Erro ao processar agendamento ${assignment.id}:`, assignmentError);
          
          // Fallback em caso de erro
          const assignmentId = assignment.id;
          unifiedClients[assignmentId] = {
            id: assignmentId,
            name: `Assignment ${assignment.id}`,
            address: assignment.route_id ? `Rota: ${assignment.route_id}` : 'Eventos diversos',
            phone: '(65) 99999-9999',
            scheduledTime: '08:00',
            items: [],
            internalObservations: `Assignment do tipo ${assignment.assignment_type} criado em ${new Date(assignment.created_at).toLocaleDateString('pt-BR')}`,
            source: 'AGENDA_ASSIGNMENT',
            assigned_date: assignment.assigned_date,
            status: assignment.status,
            event_ids: assignment.event_ids
          };
          
          unifiedClients[assignmentId].items.push({
            id: `${assignmentId}-summary`,
            name: `${assignment.event_ids.length} evento(s) da agenda`,
            status: assignment.status,
            value: 0,
            observations: `Status: ${assignment.status} | Data: ${assignment.assigned_date}`
          });
        }
      }
      
      // 2. Processar itens por status
      status_items.forEach(item => {
        const clientId = item.client_id;
        
        if (!unifiedClients[clientId]) {
          unifiedClients[clientId] = {
            id: clientId,
            name: item.client_name,
            address: item.client_address,
            phone: item.client_phone,
            scheduledTime: '08:00', // TODO: Definir lógica de horário
            items: [],
            internalObservations: item.internal_observations,
            source: 'STATUS_BASED'
          };
        }
        
        unifiedClients[clientId].items.push({
          id: item.id,
          name: item.service_name,
          status: item.status,
          value: parseFloat(item.service_value),
          observations: item.observations
        });
      });
      
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
  const { wazeUrl, mapsUrl } = generateNavigationLink(client.address);
  
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
        <p className="text-sm text-gray-600 mt-1">{client.address}</p>
        
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
            <span>Atender</span>
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

  const handleItemSelect = (itemId, checked) => {
    const newSelected = new Set(selectedItems);
    if (checked) {
      newSelected.add(itemId);
    } else {
      newSelected.delete(itemId);
    }
    setSelectedItems(newSelected);
  };

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
            <span className="text-sm text-gray-700">{client.address}</span>
          </div>
          <div className="flex items-center space-x-2">
            <Phone className="w-4 h-4 text-green-600" />
            <span className="text-sm text-gray-700">{client.phone}</span>
          </div>
          <div className="mt-3 p-3 bg-yellow-50 rounded-md">
            <p className="text-sm font-medium text-yellow-800">Observações Internas:</p>
            <p className="text-sm text-yellow-700">{client.internalObservations}</p>
          </div>
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

export default TechnicianMode;