import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Car, Building, Calendar, MapPin, Camera, FileText, CreditCard, Phone,
  Settings, Navigation, CheckCircle, Package, Truck, User, Trash2,
  ChevronDown, ChevronUp, ChevronRight, ArrowUpDown, Search, X, Check,
  Edit3, RefreshCw, Tag, ShieldAlert
} from 'lucide-react';
import { routesApi, budgetItemsApi, technicianApi, itemsApi } from '../services/api';
import { BACKEND_URL } from '../lib/backendUrl';
import { useAuth } from '../contexts/AuthContext';
import { TECHNICIAN_ID, TECHNICIAN_IDS_READ } from '../constants/technician';

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
  // Modo persistido — um refresh mantém o técnico no mesmo modo (rua/empresa)
  const [currentMode, setCurrentModeState] = useState(
    () => localStorage.getItem('tech_mode') || 'selection'
  ); // selection | street | company
  const setCurrentMode = (m) => {
    setCurrentModeState(m);
    localStorage.setItem('tech_mode', m);
  };
  const { user: authUser } = useAuth();
  const technicianData = authUser
    ? { id: authUser.id || authUser._id || authUser.username, name: authUser.name || authUser.username || 'Usuário', role: authUser.role || 'Técnico' }
    : null;

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
        <StreetMode onBack={() => setCurrentMode('selection')} onSwitchMode={() => setCurrentMode('company')} />
      )}
      
      {currentMode === 'company' && (
        <CompanyMode onBack={() => setCurrentMode('selection')} onSwitchMode={() => setCurrentMode('street')} />
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
// ── Utilitário: status visual do atendimento ──────────────────────────────────
// DONE = estados realmente finalizados pelo técnico (ou já no pipeline da empresa).
// AGUARDANDO_ENTREGA / AGUARDANDO_BUSCAR são TAREFAS PENDENTES de entrega numa rota —
// não são "concluído"; o técnico ainda precisa entregar/o cliente buscar.
const DONE_STATUSES = new Set(['EXECUTADO','ENTREGUE','BUSCOU','COLETADO','EM_LAVAGEM',
  'EM_LAVAGEM_PARCEIRO']);
const CANCEL_STATUSES = new Set(['CANCELADO_PELO_CLIENTE']);
const RESCHEDULE_STATUSES = new Set(['RETIRAR','EXECUTAR_NO_LOCAL','ENTREGAR','AGENDADO',
  'AGUARDANDO_ENTREGA','AGUARDANDO_BUSCAR']);

function getCardExecutionStatus(items) {
  if (!items || items.length === 0) return 'pending';
  const statuses = items.map(i => i.status || 'RETIRAR');
  const done     = statuses.filter(s => DONE_STATUSES.has(s)).length;
  const cancelled= statuses.filter(s => CANCEL_STATUSES.has(s)).length;
  const resched  = statuses.filter(s => RESCHEDULE_STATUSES.has(s)).length;
  const total    = statuses.length;

  if (done === total)                        return 'completed';   // verde
  if (cancelled === total)                   return 'cancelled';   // vermelho
  if (resched === total)                     return 'reschedule';  // laranja
  if (done + cancelled + resched === total && done > 0) return 'partial'; // amarelo
  return 'pending';
}

const CARD_STYLES = {
  completed:  { border: 'border-green-400',  bg: 'bg-green-50',  label: '✅ Concluído',            labelCls: 'text-green-700 bg-green-100' },
  partial:    { border: 'border-yellow-400', bg: 'bg-yellow-50', label: '⚡ Parcialmente concluído', labelCls: 'text-yellow-800 bg-yellow-100' },
  reschedule: { border: 'border-orange-400', bg: 'bg-orange-50', label: '🔄 Reagendar',             labelCls: 'text-orange-800 bg-orange-100' },
  cancelled:  { border: 'border-red-400',    bg: 'bg-red-50',    label: '✕ Cancelado',             labelCls: 'text-red-700 bg-red-100' },
  pending:    { border: 'border-gray-200',   bg: 'bg-white',     label: null,                      labelCls: '' },
};

function StreetMode({ onBack, onSwitchMode }) {
  const [activeTab, setActiveTab] = useState('agenda');
  const [dailyClients, setDailyClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showOnlyToday, setShowOnlyToday] = useState(true);
  const [finalizing, setFinalizing] = useState(false);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    loadDailyAgenda();
  }, []);

  const loadDailyAgenda = async (silent = false) => {
    try {
      if (!silent) setLoading(true);   // reload silencioso (ex.: ao voltar de um cliente) não pisca spinner
      setLoadError('');

      // Buscar tarefas híbridas do técnico para múltiplas datas se necessário
      const today = new Date().toISOString().split('T')[0];
      console.log(`📅 TechnicianMode: Buscando tarefas para a data: ${today}`);
      
      let response = await technicianApi.getDailyTasks(
        TECHNICIAN_IDS_READ, // migração TECH-001 -> USR-6249, ver constants/technician.js
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
          const dateResponse = await technicianApi.getDailyTasks(TECHNICIAN_IDS_READ, date);
          
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
      
      // 1. Processar assignments removido - agora os status_items contêm os assignments desencapsulados
      console.log(`🔍 Processando assignments via status_items desencapsulados (${assignments.length} assignments originais)`);
      
      // Os assignments agora são processados via status_items que foram desencapsulados no backend
      
      // 2. Processar status_items (ITENS DESENCAPSULADOS DOS ASSIGNMENTS)
      console.log(`🔍 Processando ${status_items.length} status items para unificação`);
      
      let _routeSeq = 0;  // ordem de chegada = ordem da rota (event_ids vêm ordenados por order_sequence)
      for (const item of status_items) {
        const clientId = item.client_id;
        // Chave composta: cada ROTA (assignment) do cliente vira um card próprio.
        // 2 itens na mesma rota/parada → 1 card. Mesmo cliente em rotas diferentes → cards separados.
        const groupKey = `${item.assignment_id || 'noassign'}__${clientId}`;

        if (!unifiedClients[groupKey]) {
          const fullAddress = getClientAddress(item.client_address);
          const complement = getClientComplement(item.client_address);

          unifiedClients[groupKey] = {
            id: clientId,
            cardKey: groupKey,                 // chave única do card (cliente + rota)
            routeSeq: _routeSeq++,             // ordem da rota (Geoapify) — preserva sequência
            name: item.client_name,
            address: item.client_address,
            phone: item.client_phone,
            scheduledTime: item.scheduled_time || '—',
            manualPriority: item.manual_priority ?? null,
            items: [],
            internalObservations: item.internal_observations,
            budgetObservations: item.budget_observations,
            assigned_date: item.assigned_date || new Date().toISOString().split('T')[0],
            source: 'AGENDA_ASSIGNMENT',
            status: item.assignment_status || 'ASSIGNED',
            original_assignment_id: item.assignment_id,
            route_id: item.route_id,
            full_address: fullAddress,
            complement: complement
          };

          if (item.budget_id) {
            try {
              const budgetResponse = await fetch(`${BACKEND_URL}/api/budgets/${item.budget_id}`);
              if (budgetResponse.ok) {
                const budgetData = await budgetResponse.json();
                unifiedClients[groupKey].budgetObservations = budgetData.budget_observations;
              }
            } catch (budgetError) {
              console.warn(`⚠️ Erro ao buscar orçamento ${item.budget_id}:`, budgetError);
            }
          }
        }

        const existingItem = unifiedClients[groupKey].items.find(ex => ex.id === item.id);
        if (!existingItem) {
          unifiedClients[groupKey].items.push({
            id: item.id,
            name: item.service_name,
            status: item.status,
            value: parseFloat(item.service_value),
            observations: item.observations
          });
        }
        // Card reflete o horário mais cedo entre seus itens, e a prioridade manual
        // de qualquer um deles (geralmente todos vêm da mesma edição rápida).
        if (item.scheduled_time && (unifiedClients[groupKey].scheduledTime === '—' ||
            item.scheduled_time < unifiedClients[groupKey].scheduledTime)) {
          unifiedClients[groupKey].scheduledTime = item.scheduled_time;
        }
        if (item.manual_priority !== null && item.manual_priority !== undefined) {
          unifiedClients[groupKey].manualPriority = item.manual_priority;
        }
      }
      
      // Converter para array e ordenar por data
      const clientsArray = Object.values(unifiedClients);
      
      // Ordenar por DATA e depois pela SEQUÊNCIA DA ROTA (ordem otimizada Geoapify)
      clientsArray.sort((a, b) => {
        const dateA = a.assigned_date || new Date().toISOString().split('T')[0];
        const dateB = b.assigned_date || new Date().toISOString().split('T')[0];
        if (dateA !== dateB) return dateA.localeCompare(dateB);
        // Mesma data → respeita a ordem da rota calculada
        return (a.routeSeq ?? 999) - (b.routeSeq ?? 999);
      });
      
      console.log('👥 Clientes unificados (ordenados por data e tipo):', clientsArray);
      
      setDailyClients(clientsArray);
      setLoading(false);
      
    } catch (error) {
      console.error('Erro ao carregar agenda híbrida:', error);
      // Antes caía num fallback de clientes fictícios ("João Silva"/"Maria Santos") —
      // risco real do técnico confundir dados mock com tarefas de verdade em campo.
      // Agora mostra erro explícito + permite tentar de novo.
      setLoadError('Não foi possível carregar a agenda do dia. Verifique sua conexão e tente novamente.');
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
      <div className="bg-blue-600 text-white p-4 flex items-center justify-between">
        <div className="flex items-center">
          <button onClick={onBack} className="mr-3">
            <span className="text-xl">←</span>
          </button>
          <h2 className="text-lg font-semibold">Modo Rua</h2>
        </div>
        <div className="flex items-center gap-2">
          {onSwitchMode && (
            <button
              onClick={onSwitchMode}
              className="flex items-center gap-1 bg-orange-500 hover:bg-orange-600 text-white text-xs font-medium px-2.5 py-1.5 rounded-lg shadow-sm transition-colors"
              title="Ir para o Modo Empresa"
            >
              <Building className="w-3.5 h-3.5" /> Empresa
            </button>
          )}
        </div>
        {loadError && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-2.5 py-1.5 text-xs flex items-center gap-2">
            <span>{loadError}</span>
            <button onClick={() => loadDailyAgenda()} className="shrink-0 px-2 py-1 bg-red-600 text-white rounded-md text-[10px] font-medium hover:bg-red-700">
              Tentar novamente
            </button>
          </div>
        )}
        <button
          onClick={async () => {
            const todayIso = new Date().toISOString().split('T')[0]; // YYYY-MM-DD para API
            const fmtDate  = iso => iso.split('-').reverse().join('/'); // DD/MM/YYYY para exibição
            const parseDate = input => {
              // Aceita DD/MM/YYYY ou DD-MM-YYYY → devolve YYYY-MM-DD
              const p = input.trim().split(/[\/\-]/);
              if (p.length === 3 && p[0].length <= 2) return `${p[2]}-${p[1].padStart(2,'0')}-${p[0].padStart(2,'0')}`;
              return input; // já estava em YYYY-MM-DD
            };

            // Pergunta a data no formato brasileiro
            const dateInput = window.prompt('Finalizar agenda de qual data? (DD/MM/AAAA)', fmtDate(todayIso));
            if (!dateInput) return;
            const date = parseDate(dateInput);
            const dateDisplay = fmtDate(date);

            // Conta itens que SERIAM reagendados (pendentes de execução) dessa data
            const RESCHED = new Set(['RETIRAR','EXECUTAR_NO_LOCAL','ENTREGAR','AGENDADO']);
            const toReschedule = (dailyClients || [])
              .filter(c => (c.assigned_date || todayIso) === date)
              .flatMap(c => c.items || [])
              .filter(it => RESCHED.has(it.status)).length;

            const msg = toReschedule > 0
              ? `Finalizar agenda de ${dateDisplay}?\n\n${toReschedule} serviço(s) NÃO executado(s) serão liberados para nova rota.\nOs já concluídos seguem para o financeiro normalmente.`
              : `Finalizar agenda de ${dateDisplay}?\n\nTodos os serviços desta data já foram tratados — nada será reagendado.`;
            if (!window.confirm(msg)) return;

            setFinalizing(true);
            try {
              const r = await technicianApi.finalizeToday(date);
              const res = r.data.results;
              alert(`Agenda de ${dateDisplay} finalizada!\n✅ Finalizados: ${res.finalized}\n🔄 Reagendados: ${res.rescheduled}\n📦 Empresa: ${res.empresa}\n✕ Cancelados: ${res.cancelled}`);
              loadDailyAgenda();
            } catch(e) { alert('Erro: ' + (e.response?.data?.detail || e.message)); }
            finally { setFinalizing(false); }
          }}
          disabled={finalizing}
          className="text-xs bg-white text-blue-700 font-semibold px-3 py-1.5 rounded-lg hover:bg-blue-50 disabled:opacity-50"
        >
          {finalizing ? '...' : '✓ Finalizar Agenda'}
        </button>
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
          <AgendaTab clients={dailyClients} loading={loading} generateNavigationLink={generateNavigationLink} reload={loadDailyAgenda} />
        )}
        {activeTab === 'payments' && <PaymentsTab />}
        {activeTab === 'tickets' && <TicketsTab />}
        {activeTab === 'photos' && <PhotosTab />}
      </div>
    </div>
  );
}

// Componente da Tab Agenda
function AgendaTab({ clients, loading, generateNavigationLink, reload }) {
  const [selectedClient, setSelectedClient] = useState(null);
  // "Apenas hoje" persistido — sobrevive a refresh (importante p/ lançamentos retroativos)
  const [showOnlyToday, setShowOnlyTodayState] = useState(() => {
    const saved = localStorage.getItem('tech_only_today');
    return saved === null ? true : saved === '1';
  });
  const setShowOnlyToday = (v) => {
    setShowOnlyTodayState(v);
    localStorage.setItem('tech_only_today', v ? '1' : '0');
  };
  
  // Filtrar clientes por data - APENAS ASSIGNMENTS DA AGENDA
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
        onBack={() => { setSelectedClient(null); if (reload) reload(true); }}
        generateNavigationLink={generateNavigationLink}
      />
    );
  }

  // Ordena: concluídos por último; dentro de cada grupo, respeita a sequência da rota
  const orderedClients = [...filteredClients].sort((a, b) => {
    const rank = (c) => {
      const s = getCardExecutionStatus(c.items);
      return s === 'completed' ? 2 : s === 'cancelled' ? 1 : 0;
    };
    const r = rank(a) - rank(b);
    if (r !== 0) return r;
    return (a.routeSeq ?? 999) - (b.routeSeq ?? 999);
  });
  const pendingCount = orderedClients.filter(c => getCardExecutionStatus(c.items) !== 'completed').length;
  const doneCount = orderedClients.length - pendingCount;

  return (
    <div className="space-y-4">
      {/* Filtros */}
      <div className="bg-white rounded-lg shadow-md p-4 border border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-800">
            Agenda — {pendingCount} pendente(s)
            {doneCount > 0 && <span className="text-sm font-normal text-gray-400"> · {doneCount} concluído(s)</span>}
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

      {orderedClients.map(client => (
        <ClientCard
          key={client.cardKey || client.id}
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
  const { user: cardUser } = useAuth();
  const isAdminCard = cardUser?.role === 'ADMIN';
  const [editingPriority, setEditingPriority] = useState(false);
  const [priorityDraft, setPriorityDraft] = useState(client.manualPriority ?? '');
  const [savingPriority, setSavingPriority] = useState(false);

  const saveManualPriority = async (e) => {
    e.stopPropagation();
    const value = priorityDraft === '' ? null : parseInt(priorityDraft, 10);
    setSavingPriority(true);
    try {
      // Aplica em todos os itens deste card (mesma visita/parada) — eles vêm da
      // mesma assignment, então a edição vale pra todos de uma vez.
      await Promise.all(client.items.map(it =>
        technicianApi.updateItemSchedule(client.original_assignment_id, {
          item_id: it.id, manual_priority: value,
        })
      ));
      setEditingPriority(false);
    } catch (err) {
      alert('Erro ao salvar prioridade. Tente novamente.');
    } finally { setSavingPriority(false); }
  };

  const totalValue = client.items.reduce((sum, item) => sum + item.value, 0);
  const execStatus = getCardExecutionStatus(client.items);
  const cardStyle  = CARD_STYLES[execStatus];
  const isDone = execStatus === 'completed' || execStatus === 'cancelled';
  const [collapsed, setCollapsed] = useState(isDone);  // concluídos começam retraídos

  const handleRemoveAssignment = async (assignmentId) => {
    try {
      if (!window.confirm('Tem certeza que deseja remover este serviço da sua agenda?')) return;
      await technicianApi.updateAssignmentStatus(assignmentId, 'CANCELLED');
      alert('Serviço removido da sua agenda com sucesso!');
      window.location.reload();
    } catch (error) {
      if (error.response?.status === 404) {
        window.location.reload();
      } else {
        alert('Erro ao remover da agenda. Tente novamente.');
      }
    }
  };
  
  // Card concluído/cancelado retraído — versão compacta e discreta
  if (isDone && collapsed) {
    return (
      <div className={`rounded-lg border ${cardStyle.border} bg-white/60 opacity-70 hover:opacity-100 transition`}>
        <button
          onClick={() => setCollapsed(false)}
          className="w-full flex items-center justify-between px-4 py-2.5 text-left"
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-base">{execStatus === 'completed' ? '✅' : '✕'}</span>
            <span className="font-medium text-gray-500 text-sm truncate line-through">{client.name}</span>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${cardStyle.labelCls}`}>{cardStyle.label}</span>
            <span className="text-[10px] text-gray-400">{client.items.length} item(s)</span>
          </div>
          <span className="text-xs text-gray-400 shrink-0">R$ {totalValue.toFixed(2)} ▾</span>
        </button>
      </div>
    );
  }

  return (
    <div className={`rounded-lg shadow-md border-2 ${cardStyle.border} ${cardStyle.bg} ${isDone ? 'opacity-75' : ''}`}>
      {isDone && (
        <button onClick={() => setCollapsed(true)}
          className="w-full text-[10px] text-gray-400 hover:text-gray-600 py-1 border-b border-gray-100">
          ▴ recolher (já concluído)
        </button>
      )}
      {/* Header do card */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {client.source === 'AGENDA_ASSIGNMENT' ? (
              <Calendar className="w-4 h-4 text-purple-600" />
            ) : (
              <MapPin className="w-4 h-4 text-blue-600" />
            )}
            <span className="font-semibold text-gray-800">{client.name}</span>
            {cardStyle.label && (
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${cardStyle.labelCls}`}>
                {cardStyle.label}
              </span>
            )}
            
            {/* CORREÇÃO: Mostrar data + horário ao invés de apenas horário */}
            <div className="flex flex-col">
              <span className="text-blue-600 font-medium text-sm">{client.scheduledTime}</span>
              {client.scheduledDate && (
                <span className="text-gray-500 text-xs">
                  {new Date(client.scheduledDate).toLocaleDateString('pt-BR')}
                </span>
              )}
            </div>

            {/* Prioridade manual — sobrepõe o horário na ordenação. Edição rápida: um
                número só, aplicado a todos os itens desta parada. Vazio = neutro. */}
            {client.manualPriority !== null && client.manualPriority !== undefined && !editingPriority && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-800">
                prioridade {client.manualPriority}
              </span>
            )}
            {isAdminCard && !editingPriority && (
              <button
                onClick={(e) => { e.stopPropagation(); setEditingPriority(true); }}
                className="text-[10px] text-gray-400 hover:text-gray-600 underline"
              >
                {client.manualPriority !== null && client.manualPriority !== undefined ? 'editar' : '+ prioridade'}
              </button>
            )}
            {isAdminCard && editingPriority && (
              <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                <input
                  type="number"
                  value={priorityDraft}
                  onChange={(e) => setPriorityDraft(e.target.value)}
                  placeholder="neutro"
                  className="w-16 px-1 py-0.5 border border-gray-300 rounded text-xs"
                />
                <button onClick={saveManualPriority} disabled={savingPriority}
                  className="text-[10px] text-green-700 font-medium disabled:opacity-50">ok</button>
                <button onClick={(e) => { e.stopPropagation(); setEditingPriority(false); }}
                  className="text-[10px] text-gray-400">x</button>
              </div>
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
        <div>
          <p className="text-sm text-gray-600 mt-1">{getClientAddress(client)}</p>
          {client.complement && client.complement !== 'NENHUM' && (
            <p className="text-xs text-gray-500 mt-0.5">Compl.: {client.complement}</p>
          )}
        </div>
        
        {/* Observações do Orçamento e Internas - APÓS O ENDEREÇO */}
        <div className="mt-2 space-y-1">
          <div className="p-2 bg-green-50 rounded-md">
            <p className="text-xs font-medium text-green-800">💰 Observações do Orçamento:</p>
            <p className="text-xs text-green-700">
              {client.budgetObservations && client.budgetObservations.trim() 
                ? client.budgetObservations 
                : 'Sem informações'}
            </p>
          </div>
          <div className="p-2 bg-blue-50 rounded-md">
            <p className="text-xs font-medium text-blue-800">📝 Observações Internas:</p>
            <p className="text-xs text-blue-700">
              {client.internalObservations && client.internalObservations.trim() 
                ? client.internalObservations 
                : 'Sem informações'}
            </p>
          </div>
        </div>
        
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
          
          {/* Botão de exclusão - apenas para assignments da agenda */}
          {client.original_assignment_id && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleRemoveAssignment(client.original_assignment_id);
              }}
              className="p-1 text-red-600 hover:text-red-800 hover:bg-red-50 rounded"
              title="Remover da agenda"
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
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';
  const [selectedItems, setSelectedItems] = useState(new Set());
  const [technicianNotes, setTechnicianNotes] = useState('');
  const [itemPhotos, setItemPhotos] = useState({});
  const [cameraProblems, setCameraProblems] = useState({}); // itemId → boolean
  const [uploadingPhotos, setUploadingPhotos] = useState(false);
  const [processing, setProcessing] = useState(false);
  // Modal AFTER photo — aparece antes de mudar status para EXECUTADO/ENTREGUE
  const [afterPhotoModal, setAfterPhotoModal] = useState(null); // null | { itemIds, finalStatus, label }
  const [afterItemPhotos, setAfterItemPhotos] = useState({}); // itemId → [photoObj]
  const [afterCameraProblems, setAfterCameraProblems] = useState({}); // itemId → boolean
  const [uploadingAfterPhotos, setUploadingAfterPhotos] = useState({});
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const [paymentMethods, setPaymentMethods] = useState([
    { value: 'DINHEIRO', label: 'Dinheiro' },
    { value: 'PIX_CNPJ_25995295000104', label: 'PIX SuperDry' },
    { value: 'PIX_CNPJ_30369419000186', label: 'PIX Alternativo' },
    { value: 'DEBITO', label: 'Débito' },
    { value: 'CREDITO_1X', label: 'Crédito 1x' },
    { value: 'LINK_PAGAMENTO', label: 'Link de Pagamento' },
  ]);
  const [showDoneItems, setShowDoneItems] = useState(false);

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/payment-methods`)
      .then(r => r.json())
      .then(d => { if (d.payment_methods?.length) setPaymentMethods(d.payment_methods); })
      .catch(() => {});
  }, []);

  const handleItemSelect = (itemId, checked) => {
    const newSelected = new Set(selectedItems);
    if (checked) newSelected.add(itemId);
    else newSelected.delete(itemId);
    setSelectedItems(newSelected);
  };

  // Itens que estão na empresa em processamento — não são acionáveis em campo
  // AGUARDANDO_ENTREGA foi removido daqui: quando está numa rota, o técnico precisa entregar
  const IN_COMPANY = new Set(['COLETADO', 'EM_LAVAGEM']);
  const FIELD_DONE = new Set(['EXECUTADO', 'ENTREGUE', 'BUSCOU', 'CANCELADO']);

  // Cada item ATIVO NO CAMPO precisa de foto BEFORE OU ter "problema com câmera" marcado
  const allItemsHavePhotos = () =>
    client.items
      .filter(item => !IN_COMPANY.has(item.status) && !FIELD_DONE.has(item.status))
      .every(item =>
        (itemPhotos[item.id] || []).length > 0 || cameraProblems[item.id]
      );

  // Upload de foto AFTER
  const uploadAfterPhoto = async (itemId, files) => {
    setUploadingAfterPhotos(prev => ({ ...prev, [itemId]: true }));
    try {
      const formData = new FormData();
      formData.append('item_id', itemId);
      formData.append('technician_id', TECHNICIAN_ID);
      formData.append('photo_type', 'AFTER');
      for (let file of files) formData.append('files', file);
      const response = await fetch(`${BACKEND_URL}/api/technician/upload-photos`, { method: 'POST', body: formData });
      if (!response.ok) throw new Error(`${response.status}`);
      const photos = Array.from(files).map(file => ({
        id: Date.now() + Math.random(),
        file, url: URL.createObjectURL(file), name: file.name, photoType: 'AFTER',
      }));
      setAfterItemPhotos(prev => ({ ...prev, [itemId]: [...(prev[itemId] || []), ...photos] }));
    } catch (e) {
      alert(`Erro ao enviar foto DEPOIS: ${e.message}`);
    } finally {
      setUploadingAfterPhotos(prev => ({ ...prev, [itemId]: false }));
    }
  };

  // Verifica se todos os itens do afterPhotoModal têm foto AFTER ou camera problem
  const allAfterItemsReady = () => {
    if (!afterPhotoModal) return false;
    return afterPhotoModal.itemIds.every(id =>
      (afterItemPhotos[id] || []).length > 0 || afterCameraProblems[id]
    );
  };

  // ─── helpers ────────────────────────────────────────────────────────────────

  const getSelectedItemObjects = () =>
    client.items.filter(i => selectedItems.has(i.id));

  // Cada ação só vale para itens no status compatível — evita marcar, ex.,
  // um item "executar no local" como "entrega efetuada".
  const ACTION_STATUSES = {
    CONCLUIDO: ['EXECUTAR_NO_LOCAL'],                    // Serviço Concluído
    RETIRADA:  ['RETIRAR'],                              // Retirada Efetuada
    ENTREGA:   ['ENTREGAR', 'AGUARDANDO_ENTREGA'],       // Entrega Efetuada
    BUSCOU:    ['AGUARDANDO_BUSCAR', 'AGUARDANDO_ENTREGA'], // Cliente Buscou (na loja)
  };
  // Ação válida só se TODOS os itens selecionados estiverem em status compatível
  const actionAllowed = (key) => {
    const sel = getSelectedItemObjects();
    return sel.length > 0 && sel.every(i => ACTION_STATUSES[key].includes(i.status));
  };
  // Status dos itens selecionados (para mensagem de ajuda quando nada se aplica)
  const STREET_STATUS_LABELS = {
    RETIRAR: 'Retirar', EXECUTAR_NO_LOCAL: 'Executar no local',
    ENTREGAR: 'Entregar', AGUARDANDO_ENTREGA: 'Aguardando entrega',
    AGUARDANDO_BUSCAR: 'Aguardando cliente buscar', COLETADO: 'Coletado',
    EM_LAVAGEM: 'Em lavagem', CLIENTE_TROUXE: 'Cliente trouxe',
  };
  const selectedStatuses = [...new Set(getSelectedItemObjects().map(i => i.status))];
  const anyPrimaryAction = ['CONCLUIDO', 'RETIRADA', 'ENTREGA', 'BUSCOU'].some(actionAllowed);

  // Itens selecionados que ainda precisam de foto ANTES (e não têm "problema de câmera"
  // marcado, e não estão na empresa/já finalizados — esses nunca precisaram de foto).
  const selectedItemsMissingPhoto = () =>
    getSelectedItemObjects().filter(i =>
      !IN_COMPANY.has(i.status) && !FIELD_DONE.has(i.status) &&
      (itemPhotos[i.id] || []).length === 0 && !cameraProblems[i.id]
    );

  // Bloqueia conclusão/retirada/entrega/cliente-buscou sem foto ANTES registrada
  // (antes isso era garantido pela tela de fotos ser um passo obrigatório anterior;
  // agora que está tudo na mesma tela, a checagem precisa ser explícita aqui).
  const requirePhotosForSelection = () => {
    const missing = selectedItemsMissingPhoto();
    if (missing.length > 0) {
      alert(
        `Tire ao menos 1 foto ANTES de "${missing[0].name}"` +
        (missing.length > 1 ? ` (e mais ${missing.length - 1} item(ns))` : '') +
        `, ou marque "Problema com câmera" na seção de fotos acima.`
      );
      return false;
    }
    return true;
  };

  const changeStatus = async (itemId, status, notes = '') => {
    const token = localStorage.getItem('superdry_token');
    return fetch(`${BACKEND_URL}/api/items/${itemId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ status, notes }),
    });
  };

  const registerPayment = async (itemId, method, value, notes) => {
    const token = localStorage.getItem('superdry_token');
    return fetch(`${BACKEND_URL}/api/items/${itemId}/payment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ method, value, notes: notes || '' }),
    });
  };

  // ─── action: Serviço Concluído ───────────────────────────────────────────────
  const handleServiceCompleted = () => {
    if (selectedItems.size === 0) { alert('Selecione pelo menos um item.'); return; }
    if (!requirePhotosForSelection()) return;
    // Pede foto AFTER antes do modal de pagamento
    setAfterPhotoModal({ type: 'CONCLUIDO', itemIds: [...selectedItems], label: 'Serviço Concluído' });
  };

  // ─── action: Retirada Efetuada ───────────────────────────────────────────────
  const handlePickupDone = async () => {
    if (selectedItems.size === 0) { alert('Selecione pelo menos um item.'); return; }
    if (!requirePhotosForSelection()) return;
    setProcessing(true);
    try {
      const collectedIds = [...selectedItems];
      for (const id of collectedIds) {
        await changeStatus(id, 'COLETADO', technicianNotes || 'Retirada efetuada pelo técnico em campo.');
      }
      // Oferecer envio do comprovante via WhatsApp para cada item
      for (const itemId of collectedIds) {
        try {
          const r = await fetch(
            `${BACKEND_URL}/api/items/${itemId}/whatsapp-receipt?doc_type=pickup`,
            { headers: { Authorization: `Bearer ${localStorage.getItem('superdry_token')}` } }
          );
          if (r.ok) {
            const data = await r.json();
            if (data.whatsapp_url && window.confirm(
              `Enviar comprovante de retirada para o cliente via WhatsApp?`
            )) {
              window.open(data.whatsapp_url, '_blank');
            }
          }
        } catch (_) {}
      }
      setSelectedItems(new Set());
      setTechnicianNotes('');
      onBack();
    } catch (e) {
      alert('Erro ao registrar retirada: ' + e.message);
    } finally {
      setProcessing(false);
    }
  };

  // ─── action: Entrega Efetuada ────────────────────────────────────────────────
  const handleDeliveryDone = () => {
    if (selectedItems.size === 0) { alert('Selecione pelo menos um item.'); return; }
    if (!requirePhotosForSelection()) return;
    // Pede foto AFTER antes do modal de pagamento
    setAfterPhotoModal({ type: 'ENTREGUE', itemIds: [...selectedItems], label: 'Entrega Efetuada' });
  };

  // ─── action: Cliente Buscou ──────────────────────────────────────────────────
  const handleClientPickedUp = () => {
    if (selectedItems.size === 0) { alert('Selecione pelo menos um item.'); return; }
    if (!requirePhotosForSelection()) return;
    setPendingAction({ type: 'BUSCOU', itemIds: [...selectedItems] });
    setShowPaymentModal(true);
  };

  // ─── action: Cancelado pelo Cliente ─────────────────────────────────────────
  const handleCancelled = async () => {
    if (selectedItems.size === 0) { alert('Selecione pelo menos um item.'); return; }
    if (!window.confirm(`Confirmar cancelamento de ${selectedItems.size} item(s)?`)) return;
    setProcessing(true);
    try {
      for (const id of selectedItems) {
        await changeStatus(id, 'CANCELADO_PELO_CLIENTE', technicianNotes || 'Cancelado pelo cliente durante atendimento em campo.');
      }
      alert(`${selectedItems.size} item(s) cancelado(s).`);
      setSelectedItems(new Set());
      setTechnicianNotes('');
      onBack();
    } catch (e) {
      alert('Erro ao cancelar: ' + e.message);
    } finally {
      setProcessing(false);
    }
  };

  // ─── action: Reagendar ───────────────────────────────────────────────────────
  const handleReschedule = async () => {
    if (selectedItems.size === 0) { alert('Selecione pelo menos um item.'); return; }
    if (!window.confirm(`Reagendar ${selectedItems.size} item(s)? O item voltará à fila de rotas.`)) return;
    setProcessing(true);
    try {
      for (const itemObj of getSelectedItemObjects()) {
        // Volta ao status original conforme tipo: EXECUTAR_NO_LOCAL ou RETIRAR
        const originalStatus = itemObj.status === 'ENTREGAR' ? 'ENTREGAR'
          : itemObj.status === 'EXECUTAR_NO_LOCAL' ? 'EXECUTAR_NO_LOCAL'
          : 'RETIRAR';
        await changeStatus(itemObj.id, originalStatus, technicianNotes || 'Reagendado — cliente indisponível.');
        // Limpa vínculo com rota atual
        const token = localStorage.getItem('superdry_token');
        await fetch(`${BACKEND_URL}/api/items/${itemObj.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ current_route_id: null, current_route_stop_id: null }),
        });
      }
      alert(`${selectedItems.size} item(s) liberado(s) para reagendamento.`);
      setSelectedItems(new Set());
      setTechnicianNotes('');
      onBack();
    } catch (e) {
      alert('Erro ao reagendar: ' + e.message);
    } finally {
      setProcessing(false);
    }
  };

  // ─── confirmar fotos AFTER e prosseguir para pagamento ──────────────────────
  const handleAfterPhotosConfirmed = () => {
    if (!allAfterItemsReady()) return;
    const { type, itemIds } = afterPhotoModal;
    setAfterPhotoModal(null);
    setAfterItemPhotos({});
    setAfterCameraProblems({});
    setPendingAction({ type, itemIds });
    setShowPaymentModal(true);
  };

  // ─── confirmar pagamento (modal) ─────────────────────────────────────────────
  const handlePaymentConfirm = async (method, collectNow, receivedValue, payNotes) => {
    setShowPaymentModal(false);
    setProcessing(true);
    try {
      const { type, itemIds } = pendingAction;
      const finalStatus = type === 'CONCLUIDO' ? 'EXECUTADO'
        : type === 'ENTREGUE' ? 'ENTREGUE'
        : 'BUSCOU';

      // Valor total dos itens selecionados (para distribuição proporcional do recebido)
      const selObjs = itemIds.map(id => client.items.find(i => i.id === id)).filter(Boolean);
      const totalValue = selObjs.reduce((s, i) => s + (i.value || 0), 0);
      // Se o usuário não informou valor, usa o total do serviço
      const totalReceived = (receivedValue != null && receivedValue > 0) ? receivedValue : totalValue;

      let distributed = 0;
      for (let idx = 0; idx < itemIds.length; idx++) {
        const id = itemIds[idx];
        const item = client.items.find(i => i.id === id);
        await changeStatus(id, finalStatus, technicianNotes || `${type} — atendimento em campo.`);
        if (collectNow && item) {
          // Distribui o valor recebido proporcionalmente; último item leva o resíduo
          let portion;
          if (idx === itemIds.length - 1) {
            portion = Math.round((totalReceived - distributed) * 100) / 100;
          } else {
            const ratio = totalValue > 0 ? (item.value || 0) / totalValue : 1 / itemIds.length;
            portion = Math.round(totalReceived * ratio * 100) / 100;
            distributed += portion;
          }
          if (portion > 0) await registerPayment(id, method, portion, payNotes);
        }
      }

      const label = type === 'CONCLUIDO' ? 'Serviço concluído'
        : type === 'ENTREGUE' ? 'Entrega efetuada'
        : 'Cliente buscou';
      alert(`${label}: ${itemIds.length} item(s) atualizado(s).${collectNow ? ` Pagamento de R$ ${totalReceived.toFixed(2)} registrado.` : ' Pagamento pendente.'}`);
      setSelectedItems(new Set());
      setTechnicianNotes('');
      setPendingAction(null);
      onBack();
    } catch (e) {
      alert('Erro ao finalizar: ' + e.message);
    } finally {
      setProcessing(false);
    }
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
          <div className="flex items-start space-x-2">
            <MapPin className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
            <div>
              <span className="text-sm text-gray-700">{getClientAddress(client)}</span>
              {client.complement && client.complement !== 'NENHUM' && (
                <span className="block text-xs text-gray-500">Compl.: {client.complement}</span>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Phone className="w-4 h-4 text-green-600" />
            <span className="text-sm text-gray-700">{client.phone}</span>
          </div>
          
          {/* Observações logo após o endereço - SEMPRE EXIBIR */}
          <div className="mt-3 space-y-2">
            <div className="p-2 bg-blue-50 rounded-md">
              <p className="text-xs font-medium text-blue-800">📝 Observações Internas:</p>
              <p className="text-xs text-blue-700">
                {client.internalObservations && client.internalObservations.trim() 
                  ? client.internalObservations 
                  : 'Sem informações'}
              </p>
            </div>
            <div className="p-2 bg-green-50 rounded-md">
              <p className="text-xs font-medium text-green-800">💰 Observações do Orçamento:</p>
              <p className="text-xs text-green-700">
                {client.budgetObservations && client.budgetObservations.trim() 
                  ? client.budgetObservations 
                  : 'Sem informações'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Registro Fotográfico — incorporado na mesma tela do atendimento
          (antes era uma tela separada; unificado a pedido do Diego) */}
      <PhotoCaptureScreen
        client={client}
        embedded
        itemPhotos={itemPhotos}
        cameraProblems={cameraProblems}
        setCameraProblems={setCameraProblems}
        setItemPhotos={setItemPhotos}
        uploadingPhotos={uploadingPhotos}
        setUploadingPhotos={setUploadingPhotos}
        isAdmin={isAdmin}
        inCompanyStatuses={IN_COMPANY}
        fieldDoneStatuses={FIELD_DONE}
        onRefreshClient={onBack}
      />

      {/* Items List */}
      {(() => {
        const FINISHED    = new Set(['EXECUTADO','ENTREGUE','BUSCOU','CANCELADO']);
        const AT_COMPANY  = new Set(['COLETADO','EM_LAVAGEM']);
        const AT_COMPANY_LABELS = {
          COLETADO:   'Coletado — na empresa',
          EM_LAVAGEM: 'Em lavagem',
        };
        const pending    = client.items.filter(i => !FINISHED.has(i.status) && !AT_COMPANY.has(i.status));
        const atCompany  = client.items.filter(i => AT_COMPANY.has(i.status));
        const done       = client.items.filter(i => FINISHED.has(i.status));

        const ItemRow = (item) => {
          const isDone      = FINISHED.has(item.status);
          const isAtCompany = AT_COMPANY.has(item.status);
          return (
            <div key={item.id} className={`border rounded-md p-3 transition ${
              isDone      ? 'border-gray-100 bg-gray-50 opacity-60' :
              isAtCompany ? 'border-blue-100 bg-blue-50' :
                            'border-gray-200 bg-white'
            }`}>
              <div className="flex items-center space-x-3">
                {isDone
                  ? <span className="text-green-500 text-lg w-4 text-center">✓</span>
                  : isAtCompany
                    ? <span className="text-blue-400 text-lg w-4 text-center">🏢</span>
                    : <input type="checkbox" checked={selectedItems.has(item.id)}
                        onChange={(e) => handleItemSelect(item.id, e.target.checked)}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded" />
                }
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className={`font-medium ${isDone ? 'text-gray-400 line-through' : isAtCompany ? 'text-blue-700' : 'text-gray-800'}`}>
                      {item.name}
                    </span>
                    <span className={`font-medium text-sm ${isDone || isAtCompany ? 'text-gray-400' : 'text-green-600'}`}>
                      R$ {item.value.toFixed(2)}
                    </span>
                  </div>
                  <p className={`text-xs mt-0.5 ${isDone ? 'text-gray-400' : isAtCompany ? 'text-blue-600 font-medium' : 'text-gray-500'}`}>
                    {isAtCompany ? AT_COMPANY_LABELS[item.status] : item.status}
                    {item.payment_status && item.payment_status !== 'PENDENTE' && (
                      <span className="ml-2 text-emerald-600">· {item.payment_status}</span>
                    )}
                  </p>
                  {item.observations && !isDone && !isAtCompany && (
                    <p className="text-xs text-gray-400 italic mt-0.5">Obs: {item.observations}</p>
                  )}
                </div>
              </div>
            </div>
          );
        };

        return (
          <div className="bg-white rounded-lg shadow-md p-4 mb-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium text-gray-800">
                Itens/Serviços
                {pending.length > 0 && (
                  <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full">
                    {pending.length} pendente{pending.length > 1 ? 's' : ''}
                  </span>
                )}
              </h4>
              {done.length > 0 && (
                <button onClick={() => setShowDoneItems(v => !v)}
                  className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1">
                  {showDoneItems ? '▲' : '▼'} {done.length} concluído{done.length > 1 ? 's' : ''}
                </button>
              )}
            </div>

            <div className="space-y-2">
              {pending.map(item => ItemRow(item))}
            </div>

            {/* Itens na empresa — sempre visíveis mas não acionáveis */}
            {atCompany.length > 0 && (
              <div className="mt-3 pt-3 border-t border-blue-100 space-y-2">
                <p className="text-xs text-blue-500 font-medium mb-1">🏢 Na empresa ({atCompany.length})</p>
                {atCompany.map(item => ItemRow(item))}
              </div>
            )}

            {done.length > 0 && showDoneItems && (
              <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
                {done.map(item => ItemRow(item))}
              </div>
            )}

            {done.length > 0 && !showDoneItems && (
              <button onClick={() => setShowDoneItems(true)}
                className="mt-3 w-full text-xs text-gray-400 hover:text-gray-500 py-1.5 border border-dashed border-gray-200 rounded-md">
                ▼ Ver {done.length} item{done.length > 1 ? 's' : ''} já concluído{done.length > 1 ? 's' : ''}
              </button>
            )}
          </div>
        );
      })()}

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
          {!anyPrimaryAction && (
            <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-2.5 py-2 mb-2">
              ⚠ Nenhuma ação de conclusão se aplica à seleção atual
              ({selectedStatuses.map(s => STREET_STATUS_LABELS[s] || s).join(', ')}).
              Selecione itens do mesmo tipo (ex.: só itens a entregar, ou só a executar no local).
            </div>
          )}
          <div className="grid grid-cols-2 gap-2">
            {actionAllowed('CONCLUIDO') && (
            <button
              disabled={processing}
              onClick={handleServiceCompleted}
              className="bg-green-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-green-700 transition-colors flex items-center justify-center space-x-1 disabled:opacity-50">
              <CheckCircle className="w-4 h-4" />
              <span>Serviço Concluído</span>
            </button>
            )}
            {actionAllowed('RETIRADA') && (
            <button
              disabled={processing}
              onClick={handlePickupDone}
              className="bg-blue-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors flex items-center justify-center space-x-1 disabled:opacity-50">
              <Package className="w-4 h-4" />
              <span>Retirada Efetuada</span>
            </button>
            )}
            {actionAllowed('ENTREGA') && (
            <button
              disabled={processing}
              onClick={handleDeliveryDone}
              className="bg-purple-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-purple-700 transition-colors flex items-center justify-center space-x-1 disabled:opacity-50">
              <Truck className="w-4 h-4" />
              <span>Entrega Efetuada</span>
            </button>
            )}
            {actionAllowed('BUSCOU') && (
            <button
              disabled={processing}
              onClick={handleClientPickedUp}
              className="bg-orange-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-orange-700 transition-colors flex items-center justify-center space-x-1 disabled:opacity-50">
              <User className="w-4 h-4" />
              <span>Cliente Buscou</span>
            </button>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2 mt-2">
            <button
              disabled={processing}
              onClick={handleCancelled}
              className="bg-red-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-50">
              Cancelado pelo Cliente
            </button>
            <button
              disabled={processing}
              onClick={handleReschedule}
              className="bg-yellow-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-yellow-700 transition-colors disabled:opacity-50">
              Reagendar
            </button>
          </div>
          {processing && <p className="text-center text-sm text-gray-500 mt-2">Processando...</p>}
        </div>
      )}

      {/* Modal AFTER photo — exibido antes do modal de pagamento */}
      {afterPhotoModal && (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-60 flex items-end">
          <div className="bg-white w-full rounded-t-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
              <div>
                <h3 className="font-semibold text-gray-900 text-sm flex items-center gap-2">
                  <Camera className="w-4 h-4 text-green-600" />
                  Foto DEPOIS — {afterPhotoModal.label}
                </h3>
                <p className="text-xs text-gray-500">Registre o resultado do serviço em cada item</p>
              </div>
              <button
                onClick={() => { setAfterPhotoModal(null); setAfterItemPhotos({}); setAfterCameraProblems({}); }}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {afterPhotoModal.itemIds.map(itemId => {
                const item = client.items.find(i => i.id === itemId);
                if (!item) return null;
                const photos = afterItemPhotos[itemId] || [];
                const hasProblem = afterCameraProblems[itemId] || false;
                const uploading = uploadingAfterPhotos[itemId];
                const isReady = photos.length > 0 || hasProblem;

                return (
                  <div key={itemId} className={`border rounded-xl p-3 ${isReady ? 'border-green-300 bg-green-50' : 'border-gray-200'}`}>
                    <div className="flex items-center gap-2 mb-2">
                      {isReady
                        ? <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0" />
                        : <Camera className="w-4 h-4 text-blue-600 flex-shrink-0" />
                      }
                      <span className="text-sm font-medium text-gray-800 truncate">{item.name}</span>
                    </div>

                    {!hasProblem && (
                      <div className="mb-2">
                        <input
                          type="file"
                          multiple
                          accept="image/*"
                          capture="environment"
                          disabled={uploading}
                          onChange={e => { uploadAfterPhoto(itemId, Array.from(e.target.files)); e.target.value = ''; }}
                          className="block w-full text-xs text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-green-100 file:text-green-800 hover:file:bg-green-200 disabled:opacity-50"
                        />
                        {uploading && <p className="text-xs text-gray-400 mt-1">Enviando...</p>}
                      </div>
                    )}

                    {photos.length > 0 && (
                      <div className="flex gap-2 flex-wrap mb-2">
                        {photos.map(p => (
                          <img key={p.id} src={p.url} alt="" className="w-16 h-16 object-cover rounded-lg border border-green-200" />
                        ))}
                      </div>
                    )}

                    {photos.length === 0 && (
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={hasProblem}
                          onChange={e => setAfterCameraProblems(prev => ({ ...prev, [itemId]: e.target.checked }))}
                          className="w-4 h-4 accent-gray-600"
                        />
                        <span className="text-xs text-gray-600">Problema com câmera — não foi possível fotografar</span>
                      </label>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="px-4 py-3 border-t border-gray-100">
              <button
                onClick={handleAfterPhotosConfirmed}
                disabled={!allAfterItemsReady()}
                className="w-full py-3 rounded-xl bg-green-600 text-white font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                <CheckCircle className="w-4 h-4" />
                Confirmar e registrar {afterPhotoModal.label.toLowerCase()}
              </button>
              {!allAfterItemsReady() && (
                <p className="text-xs text-center text-gray-400 mt-1">
                  Tire foto de cada item ou marque "problema com câmera"
                </p>
              )}
              {isAdmin && !allAfterItemsReady() && (
                <button
                  onClick={handleAfterPhotosConfirmed}
                  className="w-full mt-2 py-2.5 rounded-xl border border-orange-400 text-orange-600 font-semibold text-sm hover:bg-orange-50 flex items-center justify-center gap-2"
                >
                  <ShieldAlert className="w-4 h-4" />
                  Pular fotos — Admin
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal de Pagamento */}
      {showPaymentModal && <PaymentModal
        items={getSelectedItemObjects()}
        onConfirm={handlePaymentConfirm}
        onSkip={() => handlePaymentConfirm(null, false, 0, '')}
        onCancel={() => { setShowPaymentModal(false); setPendingAction(null); }}
        paymentMethods={paymentMethods}
      />}
    </div>
  );
}

// Modal de Pagamento
function PaymentModal({ items, onConfirm, onSkip, onCancel, paymentMethods }) {
  const [method, setMethod] = useState('DINHEIRO');
  const total = items.reduce((s, i) => s + (i.value || 0), 0);
  const [receivedValue, setReceivedValue] = useState(total.toFixed(2));
  const [notes, setNotes] = useState('');

  const received = parseFloat(receivedValue) || 0;
  const diff = received - total;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 flex items-end justify-center z-50 p-4">
      <div className="bg-white rounded-t-2xl w-full max-w-md p-5 space-y-4">
        <h3 className="text-lg font-bold text-gray-900">Registrar Pagamento</h3>
        <p className="text-sm text-gray-600">
          {items.length} item(s) · Valor do serviço: <strong>R$ {total.toFixed(2)}</strong>
        </p>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Forma de Pagamento</label>
          <select
            value={method}
            onChange={e => setMethod(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500"
          >
            {paymentMethods.map(m => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Valor Recebido</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">R$</span>
            <input
              type="number"
              step="0.01"
              value={receivedValue}
              onChange={e => setReceivedValue(e.target.value)}
              className="w-full border border-gray-300 rounded-lg pl-9 pr-3 py-2 text-sm focus:ring-2 focus:ring-green-500"
            />
          </div>
          {Math.abs(diff) >= 0.01 && (
            <p className={`text-xs mt-1 ${diff < 0 ? 'text-amber-600' : 'text-blue-600'}`}>
              {diff < 0
                ? `Desconto / saldo pendente: R$ ${Math.abs(diff).toFixed(2)}`
                : `Valor a mais (troco / adicional): R$ ${diff.toFixed(2)}`}
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Observação do pagamento</label>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={2}
            placeholder="Ex: desconto de última hora, pagou parcial, combinou restante..."
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 resize-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-2 pt-1">
          <button
            onClick={() => onConfirm(method, true, received, notes)}
            className="bg-green-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-green-700"
          >
            Pagou Agora
          </button>
          <button
            onClick={onSkip}
            className="bg-gray-200 text-gray-800 py-3 rounded-xl font-semibold text-sm hover:bg-gray-300"
          >
            Cobrar Depois
          </button>
        </div>
        <button
          onClick={onCancel}
          className="w-full text-center text-sm text-gray-500 py-1"
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}

// Componente Modo Empresa (Básico)
// ─── Company Mode ──────────────────────────────────────────────────────────────

const COMPANY_STATUS_LABELS = {
  CLIENTE_TROUXE: 'Cliente Trouxe', COLETADO: 'Coletado',
  EM_LAVAGEM: 'Em Lavagem', EM_LAVAGEM_PARCEIRO: 'Em Lavagem (Parceiro)',
  AGUARDANDO_ENTREGA: 'Aguardando Entrega', AGUARDANDO_BUSCAR: 'Aguardando Buscar',
  ENTREGAR: 'Entregar',
};
const PARTNER_COLORS = ['AZUL','AMARELO','CINZA','LARANJA','ROXO','ROSA','VERDE'];
const COLOR_HEX = { AZUL:'#3B82F6',AMARELO:'#EAB308',CINZA:'#6B7280',LARANJA:'#F97316',ROXO:'#8B5CF6',ROSA:'#EC4899',VERDE:'#22C55E' };

function useSortFilter(data, defaultSort = 'client_name') {
  const [sort, setSort] = useState({ field: defaultSort, dir: 1 });
  const [filter, setFilter] = useState('');
  const processed = useMemo(() => {
    let d = data;
    if (filter) {
      const q = filter.toLowerCase();
      d = d.filter(i =>
        (i.client_name||'').toLowerCase().includes(q) ||
        (i.neighborhood||'').toLowerCase().includes(q) ||
        (i.budget_id||'').toLowerCase().includes(q) ||
        (i.service_name||'').toLowerCase().includes(q)
      );
    }
    return [...d].sort((a, b) => {
      const av = a[sort.field] ?? ''; const bv = b[sort.field] ?? '';
      return typeof av === 'string' ? av.localeCompare(bv) * sort.dir : (av - bv) * sort.dir;
    });
  }, [data, sort, filter]);
  const toggle = (field) => setSort(s => ({ field, dir: s.field === field ? -s.dir : 1 }));
  return { processed, filter, setFilter, sort, toggle };
}

function SortHeader({ label, field, sort, toggle, onSelectAll, allSelected }) {
  return (
    <th className="px-2 py-2 text-left text-xs font-semibold text-gray-600 whitespace-nowrap">
      <div className="flex items-center gap-1">
        {onSelectAll !== undefined && (
          <input type="checkbox" checked={allSelected} onChange={onSelectAll} className="mr-1 h-3.5 w-3.5" />
        )}
        <button onClick={() => toggle(field)} className="flex items-center gap-0.5 hover:text-blue-600">
          {label} <ArrowUpDown className="w-3 h-3" />
          {sort.field === field && <span>{sort.dir === 1 ? '↑' : '↓'}</span>}
        </button>
      </div>
    </th>
  );
}

function fmtMeasure(item) {
  if (item.diameter) return `Ø${item.diameter}m`;
  if (item.width && item.height) return `${item.width}x${item.height}m`;
  if (item.area_m2) return `${item.area_m2}m²`;
  if (item.linear_meters) return `${item.linear_meters}m lin.`;
  return '—';
}

function PartnerLabelBadge({ label }) {
  if (!label) return <span className="text-gray-400 text-xs">—</span>;
  if (label.type === 'COLOR_NUM') {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-mono font-bold"
        style={{ color: COLOR_HEX[label.color] || '#666' }}>
        <span style={{ width: 10, height: 10, borderRadius: 2, background: COLOR_HEX[label.color], display: 'inline-block' }} />
        {label.color}-{label.number}
      </span>
    );
  }
  return <span className="text-xs text-gray-700">{label.text}</span>;
}

// ── ItemTable: reusable selectable + sortable table ─────────────────────────

function ItemTable({ items: raw, selected, setSelected, columns, extraColumns, selectable = true }) {
  const { processed, filter, setFilter, sort, toggle } = useSortFilter(raw);
  const allSelected = selectable && processed.length > 0 && processed.every(i => selected.has(i.id));
  const toggleAll = () => setSelected(allSelected ? new Set() : new Set(processed.map(i => i.id)));
  const toggle1 = (id) => { if (!selectable) return; setSelected(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; }); };

  return (
    <div>
      <div className="relative mb-2">
        <Search className="w-3.5 h-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
        <input value={filter} onChange={e => setFilter(e.target.value)}
          placeholder="Filtrar por cliente, bairro, orçamento..."
          className="w-full pl-7 pr-3 py-1.5 border border-gray-300 rounded-lg text-xs" />
      </div>
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="w-full text-xs">
          <thead className="bg-gray-50">
            <tr>
              <SortHeader label="Cliente" field="client_name" sort={sort} toggle={toggle}
                onSelectAll={selectable ? toggleAll : undefined} allSelected={allSelected} />
              <SortHeader label="Bairro" field="neighborhood" sort={sort} toggle={toggle} />
              <SortHeader label="Orçamento" field="budget_id" sort={sort} toggle={toggle} />
              <SortHeader label="Serviço" field="service_name" sort={sort} toggle={toggle} />
              <SortHeader label="Medidas" field="area_m2" sort={sort} toggle={toggle} />
              <SortHeader label="Status" field="status" sort={sort} toggle={toggle} />
              {(extraColumns || []).map(c => <th key={c} className="px-2 py-2 text-left text-xs font-semibold text-gray-600">{c}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {processed.map(item => (
              <tr key={item.id} onClick={() => toggle1(item.id)}
                className={`transition-colors ${selectable ? 'cursor-pointer hover:bg-blue-50' : ''} ${selectable && selected.has(item.id) ? 'bg-blue-50' : ''}`}>
                <td className="px-2 py-2">
                  <div className="flex items-center gap-1.5">
                    {selectable && <input type="checkbox" checked={selected.has(item.id)} readOnly className="h-3.5 w-3.5" />}
                    <span className="font-medium text-gray-900">{item.client_name}</span>
                  </div>
                </td>
                <td className="px-2 py-2 text-gray-600">{item.neighborhood || '—'}</td>
                <td className="px-2 py-2 font-mono text-gray-500">{item.budget_id}</td>
                <td className="px-2 py-2 text-gray-700">{item.service_name}</td>
                <td className="px-2 py-2 text-gray-600">{fmtMeasure(item)}</td>
                <td className="px-2 py-2">
                  <span className="px-1.5 py-0.5 bg-gray-100 text-gray-700 rounded text-[10px] font-medium">
                    {COMPANY_STATUS_LABELS[item.status] || item.status}
                  </span>
                </td>
                {columns && columns(item)}
              </tr>
            ))}
            {processed.length === 0 && (
              <tr><td colSpan={10} className="py-6 text-center text-gray-400 text-xs">Nenhum item</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mt-1 text-[10px] text-gray-400">{processed.length} item(s)</div>
    </div>
  );
}

// ── Panel wrapper ─────────────────────────────────────────────────────────────

const PANEL_THEMES = {
  blue:   { header: 'bg-blue-600',   body: 'bg-blue-50' },
  purple: { header: 'bg-purple-600', body: 'bg-purple-50' },
  green:  { header: 'bg-green-600',  body: 'bg-green-50' },
  teal:   { header: 'bg-teal-600',   body: 'bg-teal-50' },
};

function Panel({ title, onClose, children, color = 'blue' }) {
  const t = PANEL_THEMES[color] || PANEL_THEMES.blue;
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex flex-col">
      <div className={`${t.header} text-white flex items-center justify-between px-4 py-3 shrink-0`}>
        <h3 className="font-semibold">{title}</h3>
        <button onClick={onClose}><X className="w-5 h-5 text-white/90" /></button>
      </div>
      <div className={`flex-1 overflow-y-auto p-4 ${t.body}`}>{children}</div>
    </div>
  );
}

// ── LAVAGEM panel ─────────────────────────────────────────────────────────────

function LawagemPanel({ items, onClose, onDone }) {
  const eligible = items.filter(i => ['CLIENTE_TROUXE','COLETADO'].includes(i.status));
  const [selected, setSelected] = useState(new Set());
  const [isPartner, setIsPartner] = useState(false);
  const [saving, setSaving] = useState(false);
  const [flash, setFlash] = useState('');

  const confirm = async () => {
    if (!selected.size) return;
    setSaving(true);
    try {
      const status = isPartner ? 'EM_LAVAGEM_PARCEIRO' : 'EM_LAVAGEM';
      await itemsApi.bulkStatus([...selected], status, 'Enviado para lavagem');
      setFlash(`${selected.size} item(s) → ${status}`);
      setTimeout(() => { onDone(); onClose(); }, 1500);
    } catch(e) { setFlash('Erro: ' + e.message); }
    setSaving(false);
  };

  return (
    <Panel title="Lavagem — Enviar Itens" onClose={onClose} color="blue">
      {flash && <div className="mb-3 text-sm bg-green-100 text-green-800 px-3 py-2 rounded">{flash}</div>}
      <div className="mb-3 flex items-center gap-3">
        <label className="flex items-center gap-1.5 text-sm font-medium text-gray-700">
          <input type="checkbox" checked={isPartner} onChange={e => setIsPartner(e.target.checked)} />
          Lavagem Parceiro
        </label>
        <span className="text-xs text-gray-400">
          Status destino: <strong>{isPartner ? 'EM_LAVAGEM_PARCEIRO' : 'EM_LAVAGEM'}</strong>
        </span>
      </div>
      <ItemTable items={eligible} selected={selected} setSelected={setSelected} />
      <div className="mt-4 flex justify-end gap-2">
        <button onClick={onClose} className="px-4 py-2 rounded-lg border border-gray-300 text-sm text-gray-700">Cancelar</button>
        <button onClick={confirm} disabled={!selected.size || saving}
          className="px-5 py-2 rounded-lg bg-blue-600 text-white text-sm font-semibold disabled:opacity-50">
          {saving ? 'Salvando…' : `Enviado para Lavagem (${selected.size})`}
        </button>
      </div>
    </Panel>
  );
}

// ── IDENTIFICAÇÃO E MEDIDAS panel ────────────────────────────────────────────

function MeasuresPanel({ items, onClose, onDone }) {
  const eligible = items.filter(i => ['EM_LAVAGEM','EM_LAVAGEM_PARCEIRO'].includes(i.status));
  const [edits, setEdits] = useState({});
  const [saving, setSaving] = useState(false);
  const [flash, setFlash] = useState('');
  const [expandedId, setExpandedId] = useState(null);
  const [sort, setSort] = useState({ field: 'client_name', dir: 1 });

  const setField = (id, field, val) =>
    setEdits(prev => {
      const cur = { ...(prev[id] || {}), [field]: val };
      const w = field === 'width'    ? val : (cur.width    ?? items.find(i=>i.id===id)?.width);
      const h = field === 'height'   ? val : (cur.height   ?? items.find(i=>i.id===id)?.height);
      const d = field === 'diameter' ? val : (cur.diameter ?? items.find(i=>i.id===id)?.diameter);
      if (d && parseFloat(d) > 0)
        cur.area_m2 = parseFloat((Math.PI * Math.pow(parseFloat(d)/2, 2)).toFixed(4));
      else if (w && h && parseFloat(w) > 0 && parseFloat(h) > 0)
        cur.area_m2 = parseFloat((parseFloat(w) * parseFloat(h)).toFixed(4));
      return { ...prev, [id]: cur };
    });

  const getPartnerLabel = (id) => edits[id]?.partner_label;
  const setPartnerLabel = (id, label) => setField(id, 'partner_label', label);
  const val = (id, field) => edits[id]?.[field] ?? items.find(i=>i.id===id)?.[field] ?? '';

  const saveAll = async () => {
    setSaving(true);
    let saved = 0;
    try {
      for (const [id, payload] of Object.entries(edits)) {
        if (Object.keys(payload).length > 0) { await itemsApi.updateMeasures(id, payload); saved++; }
      }
      setFlash(`${saved} item(s) atualizado(s)`);
      setTimeout(() => { onDone(); onClose(); }, 1500);
    } catch(e) { setFlash('Erro: ' + e.message); }
    setSaving(false);
  };

  const toggleSort = (field) =>
    setSort(s => ({ field, dir: s.field === field ? -s.dir : 1 }));

  const sorted = [...eligible].sort((a, b) => {
    const av = a[sort.field] ?? ''; const bv = b[sort.field] ?? '';
    return typeof av === 'string' ? av.localeCompare(bv) * sort.dir : (av - bv) * sort.dir;
  });

  const SortTh = ({ field, label }) => (
    <th className="px-2 py-2 text-left text-[10px] font-semibold text-gray-500 cursor-pointer hover:text-blue-600 whitespace-nowrap"
      onClick={() => toggleSort(field)}>
      {label}{sort.field === field ? (sort.dir === 1 ? ' ↑' : ' ↓') : ''}
    </th>
  );

  return (
    <Panel title="Identificação e Medidas" onClose={onClose} color="purple">
      {flash && <div className="mb-3 text-sm bg-green-100 text-green-800 px-3 py-2 rounded">{flash}</div>}

      {/* ── Tabela compacta ── */}
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="w-full text-xs" style={{tableLayout:'fixed'}}>
          <thead className="bg-gray-50">
            <tr>
              <SortTh field="client_name" label="Cliente" />
              <SortTh field="area_m2" label="Medidas" />
              <SortTh field="status" label="Status" />
              <th className="px-2 py-2 text-left text-[10px] font-semibold text-gray-500">Etiq.</th>
              <th className="px-1 py-2 w-4" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sorted.map(item => {
              const isOpen = expandedId === item.id;
              const edit = edits[item.id] || {};
              const pl = edit.partner_label ?? item.partner_label;
              const plType = pl?.type || null;
              const area = val(item.id, 'area_m2');
              const w = val(item.id, 'width'); const h = val(item.id, 'height');
              const d = val(item.id, 'diameter'); const lm = val(item.id, 'linear_meters');
              const measureStr = d ? `Ø${d}m` : (w && h) ? `${w}×${h}` : area ? `${area}m²` : lm ? `${lm}ml` : '—';
              const confirmed = edit.confirmed_measures ?? item.confirmed_measures;

              return (
                <React.Fragment key={item.id}>
                  {/* Linha compacta */}
                  <tr
                    className={`cursor-pointer transition-colors ${isOpen ? 'bg-blue-50' : 'hover:bg-gray-50'}`}
                    onClick={() => setExpandedId(isOpen ? null : item.id)}
                  >
                    <td className="px-2 py-2 font-medium text-gray-900">
                      <div className="flex items-center gap-1">
                        {confirmed && <span className="text-green-500">✓</span>}
                        <span className="truncate block max-w-[90px]">{item.client_name}</span>
                      </div>
                      <span className="text-[10px] text-gray-400 truncate block max-w-[90px]">{item.service_name}</span>
                    </td>
                    <td className="px-1 py-2 text-gray-600 whitespace-nowrap">{measureStr}</td>
                    <td className="px-1 py-2">
                      <span className={`text-[9px] px-1 py-0.5 rounded-full font-medium ${
                        item.status === 'EM_LAVAGEM_PARCEIRO' ? 'bg-indigo-100 text-indigo-700' : 'bg-blue-100 text-blue-700'
                      }`}>{item.status === 'EM_LAVAGEM_PARCEIRO' ? 'Parc.' : 'Lav.'}</span>
                    </td>
                    <td className="px-1 py-2"><PartnerLabelBadge label={pl} /></td>
                    <td className="px-1 py-2 text-gray-400 text-center">{isOpen ? '▲' : '▼'}</td>
                  </tr>

                  {/* Card expandido */}
                  {isOpen && (
                    <tr>
                      <td colSpan={5} className="px-2 py-3 bg-blue-50 border-b border-blue-200">
                        <div className="space-y-2">
                          <div className="font-semibold text-gray-900 text-xs flex items-center justify-between flex-wrap gap-1">
                            <span className="truncate">{item.client_name}</span>
                            <span className="text-sm font-bold text-green-700 shrink-0">
                              R${((edit.total_value ?? item.total_value) || 0).toFixed(2)}
                            </span>
                          </div>

                          {/* Tapete Quadrado */}
                          <div className="border-2 border-blue-300 rounded-lg p-2 bg-blue-50">
                            <div className="text-[9px] font-bold text-blue-700 uppercase mb-1">Tapete Quad./Ret.</div>
                            <div className="grid grid-cols-3 gap-1.5">
                              {[['width','Larg.(m)'],['height','Comp.(m)'],['area_m2','Área m²']].map(([f,l]) => (
                                <div key={f}>
                                  <label className="block text-[9px] text-blue-600 mb-0.5">{l}</label>
                                  <input type="number" step="0.01" placeholder="0.00"
                                    value={val(item.id, f)}
                                    readOnly={f==='area_m2' && !!d}
                                    onChange={e => setField(item.id, f, e.target.value ? parseFloat(e.target.value) : null)}
                                    className={`w-full px-1.5 py-1 border border-blue-300 rounded text-[11px] ${f==='area_m2'?'bg-blue-100 font-semibold':'bg-white'}`} />
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Tapete Redondo */}
                          <div className="border-2 border-green-300 rounded-lg p-2 bg-green-50">
                            <div className="text-[9px] font-bold text-green-700 uppercase mb-1">Tapete Redondo</div>
                            <div className="grid grid-cols-2 gap-1.5">
                              {[['diameter','Diâm.(m)'],['area_m2','Área m² (auto)']].map(([f,l]) => (
                                <div key={f}>
                                  <label className="block text-[9px] text-green-600 mb-0.5">{l}</label>
                                  <input type="number" step="0.01" placeholder="0.00"
                                    value={val(item.id, f)} readOnly={f==='area_m2'}
                                    onChange={e => f!=='area_m2' && setField(item.id, f, e.target.value ? parseFloat(e.target.value) : null)}
                                    className={`w-full px-1.5 py-1 border border-green-300 rounded text-[11px] ${f==='area_m2'?'bg-green-100 font-semibold cursor-default':'bg-white'}`} />
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Cortina */}
                          <div className="border-2 border-orange-300 rounded-lg p-2 bg-orange-50">
                            <div className="text-[9px] font-bold text-orange-700 uppercase mb-1">Cortina / M. Linear</div>
                            <div className="grid grid-cols-3 gap-1.5">
                              {[['linear_meters','M. lin.'],['fabric_folds','Dobras'],['fabric_per_fold','Cm/dob.']].map(([f,l]) => (
                                <div key={f}>
                                  <label className="block text-[9px] text-orange-600 mb-0.5">{l}</label>
                                  <input type="number" step="0.01" placeholder="0"
                                    value={val(item.id, f)}
                                    onChange={e => setField(item.id, f, e.target.value ? parseFloat(e.target.value) : null)}
                                    className="w-full px-1.5 py-1 border border-orange-300 rounded text-[11px] bg-white" />
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Confirmação */}
                          <label className="flex items-center gap-2 text-xs cursor-pointer">
                            <input type="checkbox"
                              checked={edit.confirmed_measures ?? item.confirmed_measures ?? false}
                              onChange={e => setField(item.id, 'confirmed_measures', e.target.checked)} />
                            <span className="font-medium text-gray-700">Confirmado</span>
                          </label>

                          {/* Identificação Parceiro */}
                          <div>
                            <div className="text-[10px] font-medium text-gray-600 mb-1">Identificação Parceiro</div>
                            <div className="flex gap-1.5 mb-1.5">
                              {['COLOR_NUM','TEXT','NONE'].map(t => (
                                <button key={t} onClick={() => setPartnerLabel(item.id, t==='NONE'?null:{type:t,color:'AZUL',number:'001',text:''})}
                                  className={`px-2 py-0.5 text-[9px] rounded border ${plType===t||(!plType&&t==='NONE')?'bg-blue-600 text-white border-blue-600':'border-gray-300 text-gray-600'}`}>
                                  {t==='COLOR_NUM'?'DRY CLEAN':t==='TEXT'?'OUTROS':'Nenhum'}
                                </button>
                              ))}
                            </div>
                            {plType==='COLOR_NUM' && (
                              <div className="flex gap-1.5 flex-wrap items-center">
                                {PARTNER_COLORS.map(c => (
                                  <button key={c} onClick={() => setPartnerLabel(item.id, {type:'COLOR_NUM',color:c,number:pl?.number||'001'})}
                                    className="w-5 h-5 rounded border-2 transition shrink-0"
                                    style={{background:COLOR_HEX[c],borderColor:pl?.color===c?'#1e40af':'transparent'}} />
                                ))}
                                <input type="text" maxLength={3} placeholder="000"
                                  value={pl?.number||''}
                                  onChange={e => setPartnerLabel(item.id, {type:'COLOR_NUM',color:pl?.color||'AZUL',number:e.target.value.replace(/\D/g,'')})}
                                  className="w-12 px-1.5 py-0.5 border border-gray-300 rounded text-[11px] font-mono" />
                              </div>
                            )}
                            {plType==='TEXT' && (
                              <input placeholder="Nome do cliente do parceiro"
                                value={pl?.text||''}
                                onChange={e => setPartnerLabel(item.id, {type:'TEXT',text:e.target.value})}
                                className="w-full px-2 py-1 border border-gray-300 rounded text-xs" />
                            )}
                          </div>

                          <div className="flex justify-end pt-1">
                            <button onClick={() => setExpandedId(null)}
                              className="px-5 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700">
                              OK
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
            {eligible.length === 0 && (
              <tr><td colSpan={6} className="py-8 text-center text-gray-400 text-xs">Nenhum item em lavagem</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex justify-end gap-2">
        <button onClick={onClose} className="px-4 py-2 rounded-lg border border-gray-300 text-sm text-gray-700">Cancelar</button>
        <button onClick={saveAll} disabled={saving}
          className="px-5 py-2 rounded-lg bg-green-600 text-white text-sm font-semibold disabled:opacity-50">
          {saving ? 'Salvando…' : 'Salvar Alterações'}
        </button>
      </div>
    </Panel>
  );
}

// ── RECOLHER TAPETES panel ────────────────────────────────────────────────────

function RecolherPanel({ items, onClose, onDone }) {
  const eligible = items.filter(i => ['EM_LAVAGEM','EM_LAVAGEM_PARCEIRO'].includes(i.status));
  const [selected, setSelected] = useState(new Set());
  const [saving, setSaving] = useState(false);
  const [flash, setFlash] = useState('');

  const confirm = async () => {
    if (!selected.size) return;
    setSaving(true);
    try {
      // Parceiro → AGUARDANDO_BUSCAR, nosso → AGUARDANDO_ENTREGA
      const partnerIds = [...selected].filter(id => {
        const item = eligible.find(i => i.id === id);
        return item?.status === 'EM_LAVAGEM_PARCEIRO' || item?.partner_label;
      });
      const ownIds = [...selected].filter(id => !partnerIds.includes(id));
      if (ownIds.length) await itemsApi.bulkStatus(ownIds, 'AGUARDANDO_ENTREGA', 'Recolhimento confirmado');
      if (partnerIds.length) await itemsApi.bulkStatus(partnerIds, 'AGUARDANDO_BUSCAR', 'Recolhimento confirmado — parceiro');
      setFlash(`${selected.size} item(s) recolhido(s)`);
      setTimeout(() => { onDone(); onClose(); }, 1500);
    } catch(e) { setFlash('Erro: ' + e.message); }
    setSaving(false);
  };

  return (
    <Panel title="Recolher Tapetes / Itens" onClose={onClose} color="green">
      {flash && <div className="mb-3 text-sm bg-green-100 text-green-800 px-3 py-2 rounded">{flash}</div>}
      <p className="text-xs text-gray-500 mb-3">
        Próprios → AGUARDANDO_ENTREGA · Parceiros → AGUARDANDO_BUSCAR
      </p>
      <ItemTable items={eligible} selected={selected} setSelected={setSelected}
        extraColumns={['Etiqueta Parceiro']}
        columns={item => (
          <td className="px-2 py-2"><PartnerLabelBadge label={item.partner_label} /></td>
        )} />
      <div className="mt-4 flex justify-end gap-2">
        <button onClick={onClose} className="px-4 py-2 rounded-lg border border-gray-300 text-sm text-gray-700">Cancelar</button>
        <button onClick={confirm} disabled={!selected.size || saving}
          className="px-5 py-2 rounded-lg bg-green-600 text-white text-sm font-semibold disabled:opacity-50">
          {saving ? 'Salvando…' : `Confirmar Recolhimento (${selected.size})`}
        </button>
      </div>
    </Panel>
  );
}

// ── PRONTOS / AGUARDANDO ENTREGA — painel informativo ─────────────────────────

function ProntosPanel({ items, onClose }) {
  const eligible = items.filter(i => ['AGUARDANDO_ENTREGA','AGUARDANDO_BUSCAR','ENTREGAR'].includes(i.status));
  const total = eligible.reduce((s, i) => s + (i.total_value || 0), 0);

  return (
    <Panel title="Tapetes Prontos / Aguardando Entrega" onClose={onClose} color="teal">
      <p className="text-xs text-gray-500 mb-3">
        Itens que já saíram da lavagem e estão disponíveis para entrega ou retirada pelo cliente.
      </p>
      {eligible.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <CheckCircle className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Nenhum item pronto no momento.</p>
        </div>
      ) : (
        <ItemTable items={eligible} selectable={false}
          extraColumns={['Etiqueta', 'Valor']}
          columns={item => (
            <>
              <td className="px-2 py-2"><PartnerLabelBadge label={item.partner_label} /></td>
              <td className="px-2 py-2 font-bold text-gray-700 whitespace-nowrap">R${(item.total_value||0).toFixed(2)}</td>
            </>
          )} />
      )}
      <div className="mt-4 flex items-center justify-between">
        <span className="text-xs text-gray-500">
          {eligible.length} item(s) · Total <strong className="text-gray-800">R${total.toFixed(2)}</strong>
        </span>
        <button onClick={onClose} className="px-4 py-2 rounded-lg border border-gray-300 text-sm text-gray-700">Fechar</button>
      </div>
    </Panel>
  );
}

// ── CompanyMode main ──────────────────────────────────────────────────────────

function CompanyMode({ onBack, onSwitchMode }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [panel, setPanel] = useState(null); // 'lavagem'|'measures'|'recolher'|'recolhimento'
  const [expanded, setExpanded] = useState({});
  const [loadError, setLoadError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setLoadError('');
      const res = await itemsApi.companyMode();
      setItems(res.data || []);
    } catch(e) {
      console.error(e);
      setLoadError('Não foi possível carregar os itens. Verifique sua conexão e tente novamente.');
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const byStatus = useMemo(() => {
    const groups = {};
    for (const s of Object.keys(COMPANY_STATUS_LABELS)) groups[s] = [];
    items.forEach(i => { if (groups[i.status]) groups[i.status].push(i); });
    return groups;
  }, [items]);

  const sections = [
    { key: 'recepcao', label: '📥 RECEPÇÃO', statuses: ['CLIENTE_TROUXE','COLETADO'], color: 'yellow' },
    { key: 'lavagem',  label: '🧽 LAVAGEM',  statuses: ['EM_LAVAGEM','EM_LAVAGEM_PARCEIRO'], color: 'blue' },
    { key: 'saida',    label: '📦 DEPÓSITO SAÍDA', statuses: ['AGUARDANDO_ENTREGA','AGUARDANDO_BUSCAR','ENTREGAR'], color: 'green' },
  ];

  const toggleExpand = (key) => setExpanded(prev => ({ ...prev, [key]: !prev[key] }));

  const SECTION_COLORS = {
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    blue:   'bg-blue-50  border-blue-200  text-blue-800',
    green:  'bg-green-50 border-green-200 text-green-800',
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-orange-600 text-white p-4 flex items-center gap-3 sticky top-0 z-10">
        <button onClick={onBack} className="text-xl">←</button>
        <h2 className="text-lg font-semibold flex-1">Modo Empresa</h2>
        {onSwitchMode && (
          <button
            onClick={onSwitchMode}
            className="flex items-center gap-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium px-2.5 py-1.5 rounded-lg shadow-sm transition-colors"
            title="Ir para o Modo Rua"
          >
            <Car className="w-3.5 h-3.5" /> Rua
          </button>
        )}
        <button onClick={load} className="p-1.5 hover:bg-orange-500 rounded-lg">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {loadError && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg mx-4 mt-3 px-3 py-2 text-xs flex items-center justify-between gap-2">
          <span>{loadError}</span>
          <button onClick={load} className="shrink-0 px-2 py-1 bg-red-600 text-white rounded-md text-[10px] font-medium hover:bg-red-700">
            Tentar novamente
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-orange-600" />
        </div>
      ) : (
        <div className="p-4 space-y-3">
          {/* Resumo por seção — expansível */}
          {sections.map(sec => {
            const secItems = sec.statuses.flatMap(s => byStatus[s] || []);
            const isOpen = expanded[sec.key];
            const cc = SECTION_COLORS[sec.color];
            return (
              <div key={sec.key} className={`rounded-xl border ${cc} overflow-hidden`}>
                <button onClick={() => toggleExpand(sec.key)}
                  className="w-full flex items-center justify-between px-4 py-3">
                  <span className="font-semibold text-sm">{sec.label}</span>
                  <div className="flex items-center gap-3">
                    {sec.statuses.map(s => (
                      <span key={s} className="text-xs">
                        {COMPANY_STATUS_LABELS[s]}: <strong>{(byStatus[s]||[]).length}</strong>
                      </span>
                    ))}
                    <span className="font-bold">{secItems.length} total</span>
                    {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </div>
                </button>
                {isOpen && (
                  <div className="bg-white border-t border-gray-100 overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-50">
                        <tr>
                          {['Cliente','Bairro','Orçamento','Serviço','Medidas','Status','Etiqueta','Valor'].map(h => (
                            <th key={h} className="px-2 py-2 text-left font-semibold text-gray-600 whitespace-nowrap">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {secItems.map(item => (
                          <tr key={item.id} className="hover:bg-gray-50">
                            <td className="px-2 py-2 font-medium text-gray-900 whitespace-nowrap">{item.client_name}</td>
                            <td className="px-2 py-2 text-gray-500">{item.neighborhood||'—'}</td>
                            <td className="px-2 py-2 font-mono text-gray-400 text-[10px]">{item.budget_id}</td>
                            <td className="px-2 py-2 text-gray-700">{item.service_name}</td>
                            <td className="px-2 py-2 text-gray-600">{fmtMeasure(item)}</td>
                            <td className="px-2 py-2">
                              <span className="px-1.5 py-0.5 bg-gray-100 text-gray-700 rounded text-[10px]">
                                {COMPANY_STATUS_LABELS[item.status]||item.status}
                              </span>
                            </td>
                            <td className="px-2 py-2"><PartnerLabelBadge label={item.partner_label} /></td>
                            <td className="px-2 py-2 font-medium text-gray-900 whitespace-nowrap">
                              {item.original_total_value && (
                                <span className="text-amber-600 line-through mr-1 text-[10px]">R${item.original_total_value.toFixed(2)}</span>
                              )}
                              R${(item.total_value||0).toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}

          {/* Botões de operação */}
          <div className="grid grid-cols-2 gap-3 mt-4">
            <button onClick={() => setPanel('lavagem')}
              className="flex flex-col items-center gap-1 bg-blue-600 text-white py-4 rounded-xl shadow hover:bg-blue-700 transition">
              <Package className="w-6 h-6" />
              <span className="text-sm font-semibold">Lavagem</span>
              <span className="text-[11px] opacity-80">{(byStatus.CLIENTE_TROUXE||[]).length + (byStatus.COLETADO||[]).length} pendentes</span>
            </button>
            <button onClick={() => setPanel('measures')}
              className="flex flex-col items-center gap-1 bg-purple-600 text-white py-4 rounded-xl shadow hover:bg-purple-700 transition">
              <Tag className="w-6 h-6" />
              <span className="text-sm font-semibold">Identificação e Medidas</span>
              <span className="text-[11px] opacity-80">{(byStatus.EM_LAVAGEM||[]).length + (byStatus.EM_LAVAGEM_PARCEIRO||[]).length} em lavagem</span>
            </button>
            <button onClick={() => setPanel('recolher')}
              className="flex flex-col items-center gap-1 bg-green-600 text-white py-4 rounded-xl shadow hover:bg-green-700 transition">
              <CheckCircle className="w-6 h-6" />
              <span className="text-sm font-semibold">Recolher Tapetes</span>
              <span className="text-[11px] opacity-80">{(byStatus.EM_LAVAGEM||[]).length + (byStatus.EM_LAVAGEM_PARCEIRO||[]).length} disponíveis</span>
            </button>
            <button onClick={() => setPanel('prontos')}
              className="flex flex-col items-center gap-1 bg-teal-600 text-white py-4 rounded-xl shadow hover:bg-teal-700 transition">
              <CheckCircle className="w-6 h-6" />
              <span className="text-sm font-semibold">Prontos / Ag. Entrega</span>
              <span className="text-[11px] opacity-80">{(byStatus.AGUARDANDO_ENTREGA||[]).length + (byStatus.AGUARDANDO_BUSCAR||[]).length + (byStatus.ENTREGAR||[]).length} itens</span>
            </button>
          </div>
        </div>
      )}

      {/* Panels */}
      {panel === 'lavagem'      && <LawagemPanel     items={items} onClose={() => setPanel(null)} onDone={load} />}
      {panel === 'measures'     && <MeasuresPanel    items={items} onClose={() => setPanel(null)} onDone={load} />}
      {panel === 'recolher'     && <RecolherPanel    items={items} onClose={() => setPanel(null)} onDone={load} />}
      {panel === 'prontos'      && <ProntosPanel     items={items} onClose={() => setPanel(null)} />}
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
function PhotoCaptureScreen({ client, onBack, embedded = false, itemPhotos, setItemPhotos, uploadingPhotos, setUploadingPhotos, onProceed, allItemsHavePhotos, cameraProblems, setCameraProblems, isAdmin, inCompanyStatuses, fieldDoneStatuses, onRefreshClient }) {
  const [photoObservations, setPhotoObservations] = useState({});
  const [damageInfo, setDamageInfo] = useState({});
  const [currentPhotoForObservation, setCurrentPhotoForObservation] = useState(null);
  const [flash, setFlash] = useState('');
  const [skippedItems, setSkippedItems] = useState(new Set()); // "deixar pra depois"
  const [cancellingItem, setCancellingItem] = useState(null);

  const IN_COMPANY = inCompanyStatuses || new Set(['COLETADO','EM_LAVAGEM']);
  const FIELD_DONE = fieldDoneStatuses || new Set(['EXECUTADO','ENTREGUE','BUSCOU','CANCELADO']);

  // Itens que realmente precisam de foto hoje
  const activeItems = (client.items || []).filter(
    item => !IN_COMPANY.has(item.status) && !FIELD_DONE.has(item.status) && !skippedItems.has(item.id)
  );

  const handleSkipItem = (itemId) => {
    setSkippedItems(prev => new Set([...prev, itemId]));
  };

  const handleCancelItem = async (item) => {
    if (!window.confirm(`Cancelar "${item.name}"? Esta ação não pode ser desfeita.`)) return;
    setCancellingItem(item.id);
    try {
      await itemsApi.updateStatus(item.id, 'CANCELADO');
      // Força recarregar o cliente (volta pra lista)
      if (onRefreshClient) onRefreshClient();
    } catch (e) {
      alert('Erro ao cancelar: ' + e.message);
    } finally { setCancellingItem(null); }
  };

  const showFlash = (msg) => {
    setFlash(msg);
    setTimeout(() => setFlash(''), 2500);
  };

  const handlePhotoUpload = async (itemId, files) => {
    if (!files || files.length === 0) return;
    setUploadingPhotos(true);
    try {
      const formData = new FormData();
      formData.append('item_id', itemId);
      formData.append('technician_id', TECHNICIAN_ID);
      formData.append('photo_type', 'BEFORE');
      if (client.original_assignment_id) formData.append('assignment_id', client.original_assignment_id);
      for (let file of files) formData.append('files', file);

      const response = await fetch(`${BACKEND_URL}/api/technician/upload-photos`, { method: 'POST', body: formData });
      if (!response.ok) throw new Error(`${response.status}`);

      const uploadedPhotos = Array.from(files).map((file, i) => ({
        id: Date.now() + Math.random() + i,
        file, url: URL.createObjectURL(file),
        name: file.name, size: file.size, type: file.type,
        timestamp: new Date().toISOString(), observations: '', photoType: 'NORMAL'
      }));

      const newItemPhotos = { ...itemPhotos };
      if (!newItemPhotos[itemId]) newItemPhotos[itemId] = [];
      newItemPhotos[itemId] = [...newItemPhotos[itemId], ...uploadedPhotos];
      setItemPhotos(newItemPhotos);
      showFlash(`${uploadedPhotos.length} foto(s) adicionada(s)`);
    } catch (error) {
      showFlash('Erro no upload — verifique a conexão');
    } finally {
      setUploadingPhotos(false);
    }
  };

  const handleDamageToggle = (itemId, hasDamage) => {
    const newDamageInfo = { ...damageInfo };
    if (!newDamageInfo[itemId]) newDamageInfo[itemId] = {};
    newDamageInfo[itemId].hasDamage = hasDamage;
    if (!hasDamage) { newDamageInfo[itemId].damageDetails = ''; newDamageInfo[itemId].damagePhotos = []; }
    setDamageInfo(newDamageInfo);
  };

  const handleDamageDetailsChange = (itemId, details) => {
    const newDamageInfo = { ...damageInfo };
    if (!newDamageInfo[itemId]) newDamageInfo[itemId] = {};
    newDamageInfo[itemId].damageDetails = details;
    setDamageInfo(newDamageInfo);
  };

  const handleDamagePhotoUpload = async (itemId, files) => {
    if (!files || files.length === 0) return;
    setUploadingPhotos(true);
    try {
      const formData = new FormData();
      formData.append('item_id', itemId);
      formData.append('technician_id', TECHNICIAN_ID);
      formData.append('photo_type', 'DAMAGE');
      if (client.original_assignment_id) formData.append('assignment_id', client.original_assignment_id);
      for (let file of files) formData.append('files', file);

      const response = await fetch(`${BACKEND_URL}/api/technician/upload-photos`, { method: 'POST', body: formData });
      if (!response.ok) throw new Error(`${response.status}`);

      const damagePhotos = Array.from(files).map((file, i) => ({
        id: Date.now() + Math.random() + i,
        file, url: URL.createObjectURL(file),
        name: file.name, size: file.size, type: file.type,
        timestamp: new Date().toISOString(), observations: '', photoType: 'DAMAGE'
      }));

      const newItemPhotos = { ...itemPhotos };
      if (!newItemPhotos[itemId]) newItemPhotos[itemId] = [];
      newItemPhotos[itemId] = [...newItemPhotos[itemId], ...damagePhotos];
      setItemPhotos(newItemPhotos);

      const newDamageInfo = { ...damageInfo };
      if (!newDamageInfo[itemId]) newDamageInfo[itemId] = {};
      if (!newDamageInfo[itemId].damagePhotos) newDamageInfo[itemId].damagePhotos = [];
      newDamageInfo[itemId].damagePhotos = [...newDamageInfo[itemId].damagePhotos, ...damagePhotos];
      setDamageInfo(newDamageInfo);
      showFlash(`${damagePhotos.length} foto(s) de dano adicionada(s)`);
    } catch (error) {
      showFlash('Erro no upload de foto de dano');
    } finally {
      setUploadingPhotos(false);
    }
  };

  const removePhoto = (itemId, photoId) => {
    const newItemPhotos = { ...itemPhotos };
    newItemPhotos[itemId] = newItemPhotos[itemId].filter(photo => photo.id !== photoId);
    setItemPhotos(newItemPhotos);
    
    // Se for uma foto de dano, remover também do damageInfo
    const newDamageInfo = { ...damageInfo };
    if (newDamageInfo[itemId] && newDamageInfo[itemId].damagePhotos) {
      newDamageInfo[itemId].damagePhotos = newDamageInfo[itemId].damagePhotos.filter(photo => photo.id !== photoId);
      setDamageInfo(newDamageInfo);
    }
  };

  const updatePhotoObservation = (photoId, observation) => {
    const newObservations = { ...photoObservations };
    newObservations[photoId] = observation;
    setPhotoObservations(newObservations);
    
    // Atualizar também no itemPhotos
    const newItemPhotos = { ...itemPhotos };
    Object.keys(newItemPhotos).forEach(itemId => {
      newItemPhotos[itemId] = newItemPhotos[itemId].map(photo => 
        photo.id === photoId ? { ...photo, observations: observation } : photo
      );
    });
    setItemPhotos(newItemPhotos);
  };

  return (
    <div>
      {flash && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-gray-800 text-white text-sm px-4 py-2 rounded-full shadow-lg pointer-events-none">
          {flash}
        </div>
      )}
      {/* Header — omitido quando incorporado na tela de atendimento (já tem um acima) */}
      {!embedded && (
        <div className="flex items-center mb-4">
          <button onClick={onBack} className="mr-3 text-blue-600">
            <span className="text-xl">←</span>
          </button>
          <h3 className="text-lg font-semibold text-gray-800">Registro Fotográfico - {client.name}</h3>
        </div>
      )}
      {embedded && (
        <h4 className="font-medium text-gray-800 mb-2">📷 Registro Fotográfico</h4>
      )}

      {/* Instruções */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <div className="flex items-start space-x-2">
          <Camera className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-medium text-blue-800 mb-1">Foto ANTES obrigatória</h4>
            <p className="text-sm text-blue-700">
              Tire ao menos 1 foto do estado inicial de cada item. Se a câmera não funcionar, marque "Problema com câmera" no item.
            </p>
          </div>
        </div>
      </div>

      {/* Itens na empresa — não precisam de foto */}
      {(client.items || []).filter(i => IN_COMPANY.has(i.status)).length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
          <p className="text-xs font-semibold text-blue-700 mb-1">🏢 Itens na empresa — sem ação necessária agora:</p>
          {(client.items || []).filter(i => IN_COMPANY.has(i.status)).map(i => (
            <p key={i.id} className="text-xs text-blue-600">• {i.name} ({i.status})</p>
          ))}
        </div>
      )}

      {/* Itens pulados */}
      {skippedItems.size > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
          <p className="text-xs font-semibold text-yellow-700 mb-1">⏭ Itens deixados para depois:</p>
          {(client.items || []).filter(i => skippedItems.has(i.id)).map(i => (
            <p key={i.id} className="text-xs text-yellow-600 flex items-center justify-between">
              <span>• {i.name}</span>
              <button onClick={() => setSkippedItems(prev => { const s = new Set(prev); s.delete(i.id); return s; })}
                className="text-yellow-500 underline text-[10px]">desfazer</button>
            </p>
          ))}
        </div>
      )}

      {/* Lista de Items para Fotografar */}
      <div className="space-y-4 mb-6">
        {activeItems.map(item => {
          const itemPhotosArray = itemPhotos[item.id] || [];
          const hasPhotos = itemPhotosArray.length > 0;

          return (
            <div key={item.id} className="bg-white rounded-lg shadow-md border border-gray-200">
              {/* Header do Item */}
              <div className={`p-4 border-b border-gray-100 ${hasPhotos ? 'bg-green-50' : 'bg-gray-50'}`}>
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
                  <div className="flex flex-col items-end gap-1">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      hasPhotos
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {hasPhotos ? `${itemPhotosArray.length} foto(s)` : 'Sem fotos'}
                    </span>
                    {/* Botões Pular / Cancelar */}
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleSkipItem(item.id)}
                        className="text-[10px] px-2 py-0.5 rounded border border-yellow-300 text-yellow-600 hover:bg-yellow-50"
                      >
                        ⏭ Depois
                      </button>
                      <button
                        onClick={() => handleCancelItem(item)}
                        disabled={cancellingItem === item.id}
                        className="text-[10px] px-2 py-0.5 rounded border border-red-300 text-red-500 hover:bg-red-50 disabled:opacity-40"
                      >
                        {cancellingItem === item.id ? '…' : '✕ Cancelar'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Upload de Fotos */}
              <div className="p-4">
                {/* Foto ANTES */}
                <div className="mb-3">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {uploadingPhotos ? 'Enviando...' : '📷 Foto ANTES do serviço:'}
                  </label>
                  <input
                    type="file"
                    multiple
                    accept="image/*"
                    capture="environment"
                    disabled={uploadingPhotos || cameraProblems[item.id]}
                    onChange={(e) => { handlePhotoUpload(item.id, Array.from(e.target.files)); e.target.value = ''; }}
                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
                  />
                </div>

                {/* Fallback câmera com problema */}
                {!hasPhotos && (
                  <label className="flex items-center gap-2 mb-3 cursor-pointer bg-gray-50 border border-gray-200 rounded-lg p-2">
                    <input
                      type="checkbox"
                      checked={cameraProblems[item.id] || false}
                      onChange={e => setCameraProblems(prev => ({ ...prev, [item.id]: e.target.checked }))}
                      className="w-4 h-4 accent-gray-600"
                    />
                    <span className="text-xs text-gray-600">
                      Problema com a câmera — não foi possível fotografar este item
                    </span>
                  </label>
                )}

                {/* Checkbox de Danos */}
                <div className="mb-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                  <div className="flex items-start space-x-2">
                    <input
                      type="checkbox"
                      id={`damage-${item.id}`}
                      checked={damageInfo[item.id]?.hasDamage || false}
                      onChange={(e) => handleDamageToggle(item.id, e.target.checked)}
                      className="mt-1 h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded"
                    />
                    <label htmlFor={`damage-${item.id}`} className="text-sm text-orange-800">
                      <span className="font-medium">O item apresenta danos visíveis?</span>
                      <br />
                      <span className="text-orange-700">
                        Rasgos, manchas claramente irreversíveis (tinta, cola, desbotamento), 
                        Descosturas ou desfiamento (gatos), afundamento de espuma ou coisa parecida?
                      </span>
                    </label>
                  </div>
                  
                  {/* Campo de detalhes do dano */}
                  {damageInfo[item.id]?.hasDamage && (
                    <div className="mt-3 space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-orange-800 mb-1">
                          Detalhes sobre o Dano: *
                        </label>
                        <textarea
                          value={damageInfo[item.id]?.damageDetails || ''}
                          onChange={(e) => handleDamageDetailsChange(item.id, e.target.value)}
                          placeholder="Descreva detalhadamente os danos encontrados..."
                          className="w-full px-3 py-2 border border-orange-300 rounded-lg text-sm focus:ring-orange-500 focus:border-orange-500"
                          rows="3"
                          required
                        />
                      </div>
                      
                      {/* Upload de foto do dano */}
                      <div>
                        <label className="block text-sm font-medium text-orange-800 mb-2">
                          Foto de identificação do dano: *
                        </label>
                        <input
                          type="file"
                          multiple
                          accept="image/*"
                          capture="environment"
                          onChange={(e) => handleDamagePhotoUpload(item.id, Array.from(e.target.files))}
                          className="block w-full text-sm text-orange-700 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-orange-100 file:text-orange-800 hover:file:bg-orange-200"
                          required
                        />
                        <p className="text-xs text-orange-600 mt-1">
                          Obrigatório: Capture fotos específicas dos danos identificados
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Preview das Fotos */}
                {hasPhotos && (
                  <div className="mt-4">
                    <p className="text-sm font-medium text-gray-700 mb-3">Fotos capturadas:</p>
                    <div className="space-y-4">
                      {itemPhotosArray.map(photo => (
                        <div key={photo.id} className={`border rounded-lg p-3 ${
                          photo.photoType === 'DAMAGE' ? 'border-orange-300 bg-orange-50' : 'border-gray-200 bg-white'
                        }`}>
                          <div className="flex space-x-3">
                            {/* Thumbnail da foto */}
                            <div className="relative flex-shrink-0">
                              <img
                                src={photo.url}
                                alt={`Foto ${photo.name}`}
                                className="w-20 h-20 object-cover rounded-md border border-gray-200"
                              />
                              <button
                                onClick={() => removePhoto(item.id, photo.id)}
                                className="absolute -top-1 -right-1 bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs hover:bg-red-700"
                              >
                                ×
                              </button>
                              {photo.photoType === 'DAMAGE' && (
                                <span className="absolute -bottom-1 -left-1 bg-orange-600 text-white text-xs px-1 rounded">
                                  DANO
                                </span>
                              )}
                            </div>
                            
                            {/* Detalhes e observações */}
                            <div className="flex-1 min-w-0">
                              <div className="text-xs text-gray-500 mb-2 truncate">
                                {photo.name} • {new Date(photo.timestamp).toLocaleTimeString()}
                              </div>
                              
                              {/* Campo de observações sobre a foto */}
                              <div>
                                <label className="block text-xs font-medium text-gray-700 mb-1">
                                  Observações sobre esta foto:
                                </label>
                                <textarea
                                  value={photo.observations || photoObservations[photo.id] || ''}
                                  onChange={(e) => updatePhotoObservation(photo.id, e.target.value)}
                                  placeholder={photo.photoType === 'DAMAGE' 
                                    ? "Descreva especificamente o dano mostrado nesta foto..." 
                                    : "Descreva o que esta foto mostra (estado geral, detalhes importantes, etc.)"
                                  }
                                  className="w-full px-2 py-1 border border-gray-300 rounded text-xs focus:ring-blue-500 focus:border-blue-500"
                                  rows="2"
                                />
                              </div>
                            </div>
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
        {/* Validação: apenas itens ativos (não pulados, não na empresa) precisam de foto */}
        {(() => {
          const sem = activeItems.filter(item =>
            (itemPhotos[item.id] || []).length === 0 && !cameraProblems[item.id]
          );
          const invalidDamage = activeItems.filter(item => {
            const info = damageInfo[item.id];
            return info?.hasDamage && (!info.damageDetails?.trim() || !info.damagePhotos?.length);
          });
          const isReady = sem.length === 0 && invalidDamage.length === 0;
          return (
            <>
              <div className="mb-3 space-y-1">
                {activeItems.length === 0 && (
                  <p className="text-sm text-green-600">
                    ✅ Todos os itens foram tratados. Pode prosseguir.
                  </p>
                )}
                {sem.length > 0 && (
                  <p className="text-sm text-red-600">
                    ⚠️ {sem.length} item(s) sem foto: tire a foto, marque "Problema com câmera" ou use ⏭ Depois.
                  </p>
                )}
                {invalidDamage.length > 0 && (
                  <p className="text-sm text-orange-600">
                    ⚠️ {invalidDamage.length} item(s) com dano precisam de detalhes e foto do dano.
                  </p>
                )}
                {isReady && activeItems.length > 0 && (
                  <p className="text-sm text-green-600">
                    ✅ Todos os itens registrados. Pode prosseguir.
                  </p>
                )}
              </div>
              {/* Botão "Prosseguir" só existia porque fotos e ação eram telas separadas.
                  Incorporado: as ações (Retirada Efetuada etc.) já checam isReady sozinhas. */}
              {!embedded && (
                <>
                  <button
                    onClick={onProceed}
                    disabled={!isReady}
                    className="w-full py-2.5 rounded-lg text-sm font-semibold bg-green-600 text-white hover:bg-green-700 disabled:bg-gray-300 disabled:text-gray-500 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                  >
                    <CheckCircle className="w-4 h-4" />
                    Prosseguir para Atendimento
                  </button>
                  {isAdmin && !isReady && (
                    <button
                      onClick={onProceed}
                      className="w-full mt-2 py-2.5 rounded-lg text-sm font-semibold border border-orange-400 text-orange-600 hover:bg-orange-50 transition-colors flex items-center justify-center gap-2"
                    >
                      <ShieldAlert className="w-4 h-4" />
                      Pular fotos — Admin
                    </button>
                  )}
                </>
              )}
            </>
          );
        })()}
      </div>
    </div>
  );
}

export default TechnicianMode;
