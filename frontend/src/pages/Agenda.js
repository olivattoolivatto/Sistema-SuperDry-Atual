import React, { useState, useEffect } from 'react';
import { 
  Calendar, 
  Clock, 
  MapPin, 
  User, 
  DollarSign, 
  Truck, 
  CheckSquare, 
  Square, 
  ArrowUp, 
  ArrowDown,
  Send,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Trash2,
  Plus,
  Smartphone,
  Edit3,
  Save,
  X
} from 'lucide-react';
import { routesApi, placesApi, clientsApi, budgetsApi, agendaApi, technicianApi } from '../services/api';
import { toast } from '../hooks/use-toast';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

export function Agenda() {
  const [savedRoutes, setSavedRoutes] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [routeEvents, setRouteEvents] = useState([]);
  const [selectedStops, setSelectedStops] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [creatingEvents, setCreatingEvents] = useState(false);
  const [showCreateEventModal, setShowCreateEventModal] = useState(false);
  const [newEvent, setNewEvent] = useState({
    title: '',
    description: '',
    location: '',
    start_date: '',
    start_time: '',
    end_date: '',
    end_time: '',
    duration: 60
  });
  const [isGoogleAuthenticated, setIsGoogleAuthenticated] = useState(false);
  const [calendarEvents, setCalendarEvents] = useState([]);
  const [calendarView, setCalendarView] = useState('week'); // 'week', '3days', 'day'
  const [currentDate, setCurrentDate] = useState(new Date());
  const [editingEvent, setEditingEvent] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [eventFormData, setEventFormData] = useState({
    summary: '',
    description: '',
    location: '',
    start_date: '',
    start_time: '',
    end_date: '',
    end_time: ''
  });
  const [locationSuggestions, setLocationSuggestions] = useState([]);
  const [customEventDate, setCustomEventDate] = useState(''); // Data personalizada para eventos da rota
  const [sendingToTechnician, setSendingToTechnician] = useState(false);
  const [sentServices, setSentServices] = useState([]); // Serviços enviados para técnico
  const [loadingSentServices, setLoadingSentServices] = useState(false);
  const [sentServicesDate, setSentServicesDate] = useState(new Date().toISOString().split('T')[0]); // Data para filtrar serviços enviados
  const [showEditServiceModal, setShowEditServiceModal] = useState(false);
  const [editingService, setEditingService] = useState(null);
  const [editServiceData, setEditServiceData] = useState({
    assigned_date: '',
    assigned_time: '',
    status: ''
  });

  useEffect(() => {
    // Check if this is a redirect from Google OAuth
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    
    if (code) {
      // Process OAuth callback
      handleOAuthCallback(code);
    } else {
      // Normal page load
      loadSavedRoutes();
      checkGoogleAuth();
    }
  }, []);

  // Load calendar events when view or date changes
  useEffect(() => {
    if (isGoogleAuthenticated) {
      loadCalendarEvents();
      loadSentServices(); // Carregar serviços enviados ao técnico
    }
  }, [currentDate, calendarView, isGoogleAuthenticated]);

  const loadSavedRoutes = async () => {
    try {
      const response = await routesApi.getSavedRoutes();
      setSavedRoutes(response.data || []);
    } catch (error) {
      console.error('Erro ao carregar rotas salvas:', error);
      toast({
        title: "Erro!",
        description: "Erro ao carregar rotas salvas.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const checkGoogleAuth = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/calendar/status`);
      const data = await response.json();
      setIsGoogleAuthenticated(data.authenticated || false);
      
      if (data.authenticated) {
        console.log('✅ Google Calendar conectado:', data.message);
      } else {
        console.log('❌ Google Calendar não conectado:', data.message);
      }
    } catch (error) {
      console.error('Erro ao verificar autenticação:', error);
      setIsGoogleAuthenticated(false);
    }
  };

  const authenticateWithGoogle = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/calendar/auth-url`);
      const data = await response.json();
      
      // Redirect to Google OAuth
      window.location.href = data.auth_url;
    } catch (error) {
      console.error('Erro ao iniciar autenticação:', error);
      toast({
        title: "Erro!",
        description: "Erro ao conectar com Google Calendar.",
        variant: "destructive",
      });
    }
  };

  const handleOAuthCallback = async (code) => {
    setLoading(true);
    
    try {
      console.log('🔄 Processando callback OAuth com código:', code);
      
      const response = await fetch(`${BACKEND_URL}/api/calendar/auth`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code: code,
          redirect_uri: 'https://laundry-sync.preview.emergentagent.com/agenda'
        })
      });

      if (!response.ok) {
        throw new Error('Erro na autenticação');
      }

      const data = await response.json();
      console.log('✅ Autenticação bem-sucedida:', data);

      // Clean URL (remove query parameters)
      window.history.replaceState({}, document.title, window.location.pathname);
      
      // Update authentication status
      setIsGoogleAuthenticated(true);
      
      // Load routes and calendar events
      await loadSavedRoutes();
      await loadCalendarEvents();
      
      toast({
        title: "Sucesso!",
        description: "Google Calendar conectado com sucesso!",
        variant: "default",
      });
      
    } catch (error) {
      console.error('Erro no callback OAuth:', error);
      
      // Clean URL even on error
      window.history.replaceState({}, document.title, window.location.pathname);
      
      toast({
        title: "Erro!",
        description: "Erro ao conectar com Google Calendar. Tente novamente.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRouteSelect = async (route) => {
    console.log('🔄 Selecionando rota:', route.id, 'com', route.stops?.length, 'stops');
    setSelectedRoute(route);
    
    // CRÍTICO: Limpar seleções e eventos anteriores
    setSelectedStops(new Set());
    setRouteEvents([]);
    
    // Inicializar data personalizada com a data planejada da rota ou hoje
    const defaultDate = route.planned_date || new Date().toISOString().split('T')[0];
    setCustomEventDate(defaultDate);
    
    if (!route.stops || route.stops.length === 0) {
      console.log('❌ Nenhum stop encontrado na rota');
      return;
    }
    
    // Transform route stops into event format com cópia profunda
    // CORREÇÃO CRÍTICA: Ordenar stops APENAS por order_sequence (ordem otimizada do mapa)
    // order_sequence = ordem otimizada pela API do mapa (OSRM)
    // delivery_order = ordem de priorização manual (não queremos esta)
    const sortedStops = [...route.stops].sort((a, b) => {
      const aOrder = a.order_sequence || 0;
      const bOrder = b.order_sequence || 0;
      return aOrder - bOrder;
    });

    console.log('📋 Ordem corrigida dos stops (APENAS por order_sequence do mapa):', {
      originalOrder: route.stops.map(s => `${s.client_name} (order_seq: ${s.order_sequence}, delivery: ${s.delivery_order})`),
      sortedOrder: sortedStops.map(s => `${s.client_name} (order_seq: ${s.order_sequence})`)
    });

    const events = sortedStops.map((stop, index) => {
      // CORREÇÃO: Priorizar budget_item_id se disponível
      const eventId = stop.budget_item_id || stop.id || `${route.id}-stop-${index}-${Date.now()}`;
      
      console.log(`📋 Criando evento ${index + 1}:`, {
        id: eventId,
        budget_item_id: stop.budget_item_id,
        stop_id: stop.id,
        client: stop.client_name,
        status: stop.service_status,
        note: 'Usando budget_item_id como prioridade'
      });
      
      // Criar objeto completamente novo (deep copy)
      const newEvent = {
        id: String(eventId), // Garantir que é string
        budget_item_id: stop.budget_item_id, // CRÍTICO: Preservar budget_item_id para assignments
        order_sequence: Number(index + 1), // Usar posição atual no array ordenado
        client_name: String(stop.client_name || ''),
        service_name: String(stop.service_name || ''),
        service_value: Number(stop.service_value || 0),
        neighborhood: String(stop.neighborhood || ''),
        vehicle_type: String(route.vehicle_type || ''),
        service_status: String(stop.service_status || ''),
        estimated_start_time: calculateEstimatedTime(route, index),
        duration: Number(calculateDuration(stop.service_status)),
        address: stop.address ? { ...stop.address } : null
      };
      
      return newEvent;
    });
    
    // Verificar IDs únicos
    const ids = events.map(e => e.id);
    const uniqueIds = [...new Set(ids)];
    if (ids.length !== uniqueIds.length) {
      console.error('❌ IDs duplicados detectados!', ids);
      // Force unique IDs
      events.forEach((event, index) => {
        event.id = `${route.id}-event-${index}-${Date.now()}`;
      });
    }
    
    console.log('✅ Eventos finais criados (ordem do mapa):', events.map((e, i) => ({
      index: i,
      id: e.id,
      client: e.client_name,
      time: e.estimated_start_time,
      duration: e.duration,
      note: 'Ordenado por order_sequence (mapa)'
    })));
    
    // Não precisamos mais reordenar - os eventos já foram criados na ordem correta
    setRouteEvents([...events]); // Force new array
    
    // Load calendar events for this route
    loadCalendarEvents();
  };

  const calculateEstimatedTime = (route, stopIndex) => {
    // Base start time from route
    const baseTime = new Date(`${route.planned_date}T${route.planned_start_time}`);
    let currentTime = new Date(baseTime);
    
    // Ordenar stops APENAS por order_sequence (ordem do mapa)
    const sortedStops = [...route.stops].sort((a, b) => {
      const aOrder = a.order_sequence || 0;
      const bOrder = b.order_sequence || 0;
      return aOrder - bOrder;
    });
    
    console.log('⏰ Calculando horário sequencial (ordem do mapa):', {
      stopIndex,
      clientName: sortedStops[stopIndex]?.client_name,
      orderSequence: sortedStops[stopIndex]?.order_sequence,
      baseTime: route.planned_start_time
    });
    
    // Add cumulative time for previous stops (na ordem do mapa)
    for (let i = 0; i < stopIndex; i++) {
      const stop = sortedStops[i];
      const duration = calculateDuration(stop.service_status);
      currentTime = new Date(currentTime.getTime() + duration * 60000); // Convert to milliseconds
      
      console.log(`  ⏱️ Stop ${i + 1}: ${stop.client_name} (order_seq: ${stop.order_sequence}) (+${duration}min) = ${currentTime.toTimeString().slice(0, 5)}`);
    }
    
    return currentTime.toTimeString().slice(0, 5); // Return HH:MM format
  };

  const calculateDuration = (serviceStatus) => {
    switch (serviceStatus) {
      case 'EXECUTAR_NO_LOCAL':
        return 90; // 1h30m (90 minutes)
      case 'RETIRAR':
      case 'ENTREGAR':
      default:
        return 30; // 30 minutes
    }
  };

  // Função para arredondar para cima de 10 em 10 minutos
  const roundUpToTens = (minutes) => {
    return Math.ceil(minutes / 10) * 10;
  };

  // Função para calcular duração otimizada quando há múltiplos itens no mesmo local
  const calculateOptimizedDuration = (stops) => {
    if (!stops || stops.length === 0) return 0;
    if (stops.length === 1) return calculateDuration(stops[0].service_status);

    // Agrupar stops por endereço (coordenadas ou endereço completo)
    const locationGroups = {};
    
    stops.forEach(stop => {
      const locationKey = stop.address?.latitude && stop.address?.longitude 
        ? `${stop.address.latitude},${stop.address.longitude}`
        : stop.address?.full_address || 'unknown';
      
      if (!locationGroups[locationKey]) {
        locationGroups[locationKey] = [];
      }
      locationGroups[locationKey].push(stop);
    });

    let totalDuration = 0;

    Object.values(locationGroups).forEach(locationStops => {
      if (locationStops.length === 1) {
        // Item único no local
        totalDuration += calculateDuration(locationStops[0].service_status);
      } else {
        // Múltiplos itens no mesmo local - aplicar otimização
        let baseDuration = 0;
        let hasExecution = false;
        
        locationStops.forEach(stop => {
          const duration = calculateDuration(stop.service_status);
          baseDuration += duration;
          
          if (stop.service_status === 'EXECUTAR_NO_LOCAL') {
            hasExecution = true;
          }
        });
        
        // Reduzir tempo quando há múltiplos itens no mesmo local
        let optimizedDuration = baseDuration;
        if (locationStops.length >= 2) {
          if (hasExecution) {
            // Se há execução no local, reduzir menos (15%)
            optimizedDuration = baseDuration * 0.85;
          } else {
            // Apenas coletas/entregas, reduzir mais (25%)
            optimizedDuration = baseDuration * 0.75;
          }
          
          // Arredondar para cima de 10 em 10 minutos
          optimizedDuration = roundUpToTens(optimizedDuration);
        }
        
        totalDuration += optimizedDuration;
      }
    });

    return totalDuration;
  };

  const toggleStopSelection = (stopId) => {
    console.log('🔄 Toggle selection para ID:', stopId);
    
    setSelectedStops(prevSelection => {
      console.log('📊 Estado anterior:', Array.from(prevSelection));
      
      const newSelection = new Set(prevSelection);
      const isCurrentlySelected = newSelection.has(stopId);
      
      if (isCurrentlySelected) {
        newSelection.delete(stopId);
        console.log('➖ Removendo seleção de:', stopId);
      } else {
        newSelection.add(stopId);
        console.log('➕ Adicionando seleção de:', stopId);
      }
      
      console.log('📊 Nova seleção:', Array.from(newSelection));
      return newSelection;
    });
  };

  const moveStop = (stopId, direction) => {
    console.log('🔄 Movendo stop:', stopId, 'direção:', direction);
    
    setRouteEvents(prevEvents => {
      const currentIndex = prevEvents.findIndex(event => event.id === stopId);
      
      if (currentIndex === -1) {
        console.error('❌ Stop não encontrado:', stopId);
        return prevEvents;
      }
      
      const newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
      
      if (newIndex < 0 || newIndex >= prevEvents.length) {
        console.log('🚫 Movimento inválido. Índice fora dos limites:', newIndex);
        return prevEvents;
      }
      
      console.log(`📊 Movendo de posição ${currentIndex} para ${newIndex}`);
      
      // Criar cópia profunda do array
      const newEvents = prevEvents.map(event => ({...event}));
      
      // Fazer swap dos elementos
      const temp = newEvents[currentIndex];
      newEvents[currentIndex] = newEvents[newIndex];
      newEvents[newIndex] = temp;
      
      // Recalcular order_sequence e horários para TODOS os eventos
      const updatedEvents = newEvents.map((event, index) => ({
        ...event,
        order_sequence: index + 1,
        estimated_start_time: calculateEstimatedTimeByIndex(index, newEvents)
      }));
      
      console.log('✅ Eventos após movimento:', updatedEvents.map((e, i) => `${i}: ${e.client_name} (${e.id})`));
      
      return updatedEvents;
    });
  };

  const calculateEstimatedTimeByIndex = (index, eventsArray = routeEvents) => {
    if (!selectedRoute) return '08:00';
    
    const baseTime = new Date(`${selectedRoute.planned_date}T${selectedRoute.planned_start_time}`);
    let currentTime = new Date(baseTime);
    
    for (let i = 0; i < index; i++) {
      const event = eventsArray[i];
      if (event) {
        currentTime = new Date(currentTime.getTime() + event.duration * 60000);
      }
    }
    
    return currentTime.toTimeString().slice(0, 5);
  };

  const updateEventTime = (eventId, newTime) => {
    console.log('🕒 Atualizando horário do evento:', eventId, 'para:', newTime);
    
    setRouteEvents(prevEvents => {
      return prevEvents.map(event => {
        if (event.id === eventId) {
          console.log('✅ Horário atualizado para evento:', event.client_name);
          return { ...event, estimated_start_time: newTime };
        }
        return event;
      });
    });
  };

  const recalculateFromTimeChange = (eventId) => {
    console.log('🕒 Recalculando a partir de mudança de horário:', eventId);
    
    setRouteEvents(prevEvents => {
      const eventIndex = prevEvents.findIndex(event => event.id === eventId);
      if (eventIndex === -1) return prevEvents;

      const newEvents = [...prevEvents];
      
      // Recalcular apenas os eventos APÓS o modificado
      for (let i = eventIndex + 1; i < newEvents.length; i++) {
        const previousEvent = newEvents[i - 1];
        const previousEndTime = addMinutesToTime(
          previousEvent.estimated_start_time, 
          previousEvent.duration
        );
        newEvents[i].estimated_start_time = previousEndTime;
      }

      return newEvents;
    });

    toast({
      title: "Sequência Atualizada!",
      description: "Os horários dos próximos eventos foram ajustados.",
      variant: "default",
    });
  };

  const updateEventDuration = (eventId, newDuration) => {
    console.log('⏱️ Atualizando duração do evento:', eventId, 'para:', newDuration);
    
    setRouteEvents(prevEvents => {
      return prevEvents.map(event => {
        if (event.id === eventId) {
          console.log('✅ Duração atualizada para evento:', event.client_name, 'de', event.duration, 'para', newDuration);
          return { ...event, duration: parseInt(newDuration) || 30 };
        }
        return event;
      });
    });
  };

  const recalculateSubsequentTimes = (eventId) => {
    console.log('🔄 Recalculando horários subsequentes a partir do evento:', eventId);
    
    setRouteEvents(prevEvents => {
      const eventIndex = prevEvents.findIndex(event => event.id === eventId);
      if (eventIndex === -1) {
        console.error('❌ Evento não encontrado para recálculo:', eventId);
        return prevEvents;
      }

      const newEvents = [...prevEvents];
      
      // Recalcular horários de todos os eventos a partir do modificado
      for (let i = eventIndex; i < newEvents.length; i++) {
        if (i === 0) {
          // Primeiro evento mantém horário base da rota
          if (selectedRoute) {
            newEvents[i].estimated_start_time = selectedRoute.planned_start_time || '08:00';
          }
        } else {
          // Eventos subsequentes calculam baseado no anterior
          const previousEvent = newEvents[i - 1];
          const previousEndTime = addMinutesToTime(
            previousEvent.estimated_start_time, 
            previousEvent.duration
          );
          newEvents[i].estimated_start_time = previousEndTime;
        }
      }

      console.log('✅ Horários recalculados:', newEvents.map(e => ({
        client: e.client_name,
        start: e.estimated_start_time,
        duration: e.duration
      })));

      return newEvents;
    });

    toast({
      title: "Horários Atualizados!",
      description: "Os horários dos eventos subsequentes foram ajustados automaticamente.",
      variant: "default",
    });
  };

  const addMinutesToTime = (timeString, minutes) => {
    const [hours, mins] = timeString.split(':').map(Number);
    const totalMinutes = hours * 60 + mins + minutes;
    
    const newHours = Math.floor(totalMinutes / 60) % 24;
    const newMins = totalMinutes % 60;
    
    return `${newHours.toString().padStart(2, '0')}:${newMins.toString().padStart(2, '0')}`;
  };

  const resetAllTimes = () => {
    console.log('🔄 Resetando todos os horários para sequência original');
    
    if (!selectedRoute || !routeEvents.length) {
      toast({
        title: "Aviso!",
        description: "Selecione uma rota primeiro.",
        variant: "default",
      });
      return;
    }

    setRouteEvents(prevEvents => {
      console.log('📊 Resetando eventos:', prevEvents.length);
      
      // Recriar eventos com valores originais da rota
      return prevEvents.map((event, index) => {
        // Recalcular horário baseado na posição original
        const originalStartTime = calculateEstimatedTimeByIndex(index, prevEvents);
        
        // Recalcular duração padrão baseada no service_status
        const originalDuration = calculateDuration(event.service_status);
        
        console.log(`🔄 Resetando evento ${index + 1}: ${event.client_name} - Horário: ${originalStartTime}, Duração: ${originalDuration}min`);
        
        return {
          ...event,
          estimated_start_time: originalStartTime,
          duration: originalDuration,
          order_sequence: index + 1
        };
      });
    });

    toast({
      title: "Reset Completo!",
      description: "Todos os horários e durações foram restaurados para os valores originais da rota.",
      variant: "default",
    });
  };

  const loadCalendarEvents = async (startDate = null, endDate = null) => {
    if (!isGoogleAuthenticated) return;
    
    try {
      // Calculate date range if not provided
      const start = startDate || getCurrentDateRange().start;
      const end = endDate || getCurrentDateRange().end;
      
      console.log('🔄 Carregando eventos do Google Calendar:', start, 'até', end);
      
      const response = await fetch(`${BACKEND_URL}/api/calendar/events?start_date=${start}&end_date=${end}`);
      if (response.ok) {
        const data = await response.json();
        console.log('✅ Eventos carregados:', data.events.length);
        setCalendarEvents(data.events || []);
      } else {
        console.error('Erro na resposta da API:', response.status);
      }
    } catch (error) {
      console.error('Erro ao carregar eventos do calendário:', error);
    }
  };

  const loadSentServices = async (filterDate = null) => {
    try {
      setLoadingSentServices(true);
      console.log('🔄 Iniciando carregamento de serviços enviados...');
      
      // Usar filterDate se fornecida, senão usar sentServicesDate ou data atual
      const queryDate = filterDate || sentServicesDate || new Date().toISOString().split('T')[0];
      
      console.log(`📅 Buscando dados híbridos para a data: ${queryDate}`);
      
      // Buscar dados híbridos (assignments + status_items) para o técnico atual
      const response = await technicianApi.getDailyTasks(
        'TECH-001', // TODO: Usar técnico logado
        queryDate
      );
      
      console.log('📋 Resposta API getDailyTasks:', response.data);
      
      const { assignments, status_items } = response.data;
      
      console.log('📋 Assignments encontrados:', assignments?.length || 0);
      console.log('📋 Status items encontrados:', status_items?.length || 0);
      
      // Processar assignments para exibição (filtrar cancelados)
      const processedAssignments = assignments
        .filter(assignment => {
          const isNotCancelled = assignment.status !== 'CANCELLED';
          console.log(`📋 Assignment ${assignment.id}: Status ${assignment.status} → Incluir: ${isNotCancelled}`);
          return isNotCancelled;
        })
        .map(assignment => ({
          id: assignment.id,
          route_id: assignment.route_id,
          event_ids: assignment.event_ids,
          technician_id: assignment.technician_id,
          assigned_date: assignment.assigned_date,
          assigned_time: assignment.assigned_time,
          status: assignment.status,
          created_at: assignment.created_at,
          updated_at: assignment.updated_at,
          type: 'ASSIGNMENT', // Marcador para identificar o tipo
          title: `Rota ${assignment.route_id} (${assignment.event_ids?.length || 0} eventos)`
        }));
      
      // Processar status_items como serviços individuais
      const processedStatusItems = status_items
        .filter(item => {
          // Incluir apenas itens com status relevantes para técnico
          const relevantStatuses = ['EXECUTAR_NO_LOCAL', 'RETIRAR', 'ENTREGAR'];
          return relevantStatuses.includes(item.status);
        })
        .map(item => ({
          id: `status-${item.id}`, // Prefixo para evitar conflito de IDs
          budget_item_id: item.id,
          client_name: item.client_name,
          client_phone: item.client_phone,
          service_name: item.service_name,
          service_value: item.service_value,
          status: item.status,
          observations: item.observations,
          client_address: item.client_address,
          assigned_date: queryDate, // Usar data da consulta
          assigned_time: '08:00', // Horário padrão para status items
          type: 'STATUS_ITEM', // Marcador para identificar o tipo
          title: `${getServiceEmoji(item.service_name)} ${item.client_name} - ${item.service_name}`
        }));
      
      // Combinar assignments e status items
      const allServices = [...processedAssignments, ...processedStatusItems];
      
      // Ordenar por data e tipo (assignments primeiro, depois status items)
      allServices.sort((a, b) => {
        // Priorizar assignments
        if (a.type === 'ASSIGNMENT' && b.type !== 'ASSIGNMENT') return -1;
        if (b.type === 'ASSIGNMENT' && a.type !== 'ASSIGNMENT') return 1;
        
        // Ordenar por data
        const dateA = a.assigned_date || queryDate;
        const dateB = b.assigned_date || queryDate;
        
        if (dateA !== dateB) {
          return dateA.localeCompare(dateB);
        }
        
        // Se mesma data, ordenar por horário
        return (a.assigned_time || '08:00').localeCompare(b.assigned_time || '08:00');
      });
      
      console.log('✅ Serviços híbridos processados para exibição:', allServices.length);
      console.log('✅ Assignments:', processedAssignments.length);
      console.log('✅ Status Items:', processedStatusItems.length);
      console.log('✅ Serviços detalhados:', allServices);
      
      setSentServices(allServices);
      
    } catch (error) {
      console.error('❌ Erro ao carregar serviços enviados:', error);
      setSentServices([]);
    } finally {
      setLoadingSentServices(false);
    }
  };

  const clearAllSelections = () => {
    console.log('🧹 Limpando todas as seleções');
    setSelectedStops(new Set());
    
    toast({
      title: "Seleções Limpas!",
      description: "Todas as seleções foram removidas.",
      variant: "default",
    });
  };

  const updateSentServiceStatus = async (assignmentId) => {
    try {
      console.log('🔄 Atualizando status do assignment:', assignmentId);
      
      // Recarregar dados atualizados
      await loadSentServices();
      
      toast({
        title: "Status Atualizado!",
        description: "Status dos serviços enviados foi atualizado.",
        variant: "default",
      });
      
    } catch (error) {
      console.error('Erro ao atualizar status:', error);
      toast({
        title: "Erro!",
        description: "Erro ao atualizar status. Tente novamente.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteAssignment = async (assignmentId) => {
    try {
      console.log('🗑️ Apagando assignment:', assignmentId);
      
      // Confirmar ação com o usuário
      if (!window.confirm('Tem certeza que deseja apagar este serviço enviado ao técnico? Esta ação não pode ser desfeita.')) {
        return;
      }
      
      // Marcar assignment como CANCELLED (não existe endpoint DELETE) 
      const response = await technicianApi.updateAssignmentStatus(assignmentId, 'CANCELLED');
      
      console.log('✅ Assignment marcado como cancelado:', response.data);
      
      toast({
        title: "Sucesso!",
        description: "Serviço removido da lista do técnico.",
        variant: "default",
      });
      
      // Recarregar lista de serviços enviados (assignments cancelados serão filtrados)
      await loadSentServices();
      
    } catch (error) {
      console.error('❌ Erro ao apagar assignment:', error);
      toast({
        title: "Erro!",
        description: "Erro ao apagar serviço. Tente novamente.",
        variant: "destructive",
      });
    }
  };

  const handleEditService = (service) => {
    console.log('✏️ Editando serviço:', service);
    
    setEditingService(service);
    setEditServiceData({
      assigned_date: service.assigned_date || new Date().toISOString().split('T')[0],
      assigned_time: service.assigned_time || '08:00',
      status: service.status || 'ASSIGNED'
    });
    setShowEditServiceModal(true);
  };

  const handleSaveServiceEdit = async () => {
    if (!editingService) return;
    
    try {
      console.log('💾 Salvando edição do serviço:', editingService.id, editServiceData);
      
      // Para assignments, atualizar status e dados
      if (editingService.type === 'ASSIGNMENT') {
        // Atualizar status do assignment
        const response = await technicianApi.updateAssignmentStatus(editingService.id, editServiceData.status);
        console.log('✅ Status do assignment atualizado:', response.data);
        
        // TODO: Implementar endpoint para atualizar data/horário do assignment
        // Por enquanto, apenas atualizar o status
      }
      
      // Para status items, atualizar via API de budget items
      if (editingService.type === 'STATUS_ITEM' && editingService.budget_item_id) {
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/budget-items/${editingService.budget_item_id}/status?status=${editServiceData.status}`, {
          method: 'PUT'
        });
        
        if (!response.ok) {
          throw new Error('Erro ao atualizar status do item');
        }
        
        console.log('✅ Status do budget item atualizado');
      }
      
      toast({
        title: "Sucesso!",
        description: "Serviço atualizado com sucesso.",
        variant: "default",
      });
      
      // Recarregar lista
      await loadSentServices();
      
      // Fechar modal
      setShowEditServiceModal(false);
      setEditingService(null);
      
    } catch (error) {
      console.error('❌ Erro ao salvar edição:', error);
      toast({
        title: "Erro!",
        description: "Erro ao atualizar serviço. Tente novamente.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteService = async (service) => {
    try {
      console.log('🗑️ Removendo serviço:', service.id);
      
      // Confirmar ação com o usuário
      if (!window.confirm(`Tem certeza que deseja remover este serviço? Esta ação não pode ser desfeita.`)) {
        return;
      }
      
      if (service.type === 'ASSIGNMENT') {
        // Para assignments, marcar como CANCELLED
        await handleDeleteAssignment(service.id);
      } else if (service.type === 'STATUS_ITEM' && service.budget_item_id) {
        // Para status items, atualizar status para CANCELADO_PELO_CLIENTE
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/budget-items/${service.budget_item_id}/status?status=CANCELADO_PELO_CLIENTE`, {
          method: 'PUT'
        });
        
        if (!response.ok) {
          throw new Error('Erro ao cancelar item');
        }
        
        console.log('✅ Status item marcado como cancelado');
        
        toast({
          title: "Sucesso!",
          description: "Serviço removido com sucesso.",
          variant: "default",
        });
        
        // Recarregar lista
        await loadSentServices();
      }
      
    } catch (error) {
      console.error('❌ Erro ao remover serviço:', error);
      toast({
        title: "Erro!",
        description: "Erro ao remover serviço. Tente novamente.",
        variant: "destructive",
      });
    }
  };

  const getCurrentDateRange = () => {
    const start = new Date(currentDate);
    let end = new Date(currentDate);
    
    if (calendarView === 'week') {
      // Início da semana (domingo)
      start.setDate(start.getDate() - start.getDay());
      // Final da semana (sábado)
      end.setDate(start.getDate() + 6);
    } else if (calendarView === '3days') {
      // 3 dias a partir da data atual
      end.setDate(start.getDate() + 2);
    } else {
      // Apenas o dia atual
      end = new Date(start);
    }
    
    return {
      start: start.toISOString().split('T')[0], // Format: YYYY-MM-DD
      end: end.toISOString().split('T')[0]
    };
  };

  const navigateDate = (direction) => {
    const newDate = new Date(currentDate);
    const daysToMove = calendarView === 'week' ? 7 : calendarView === '3days' ? 3 : 1;
    
    if (direction === 'prev') {
      newDate.setDate(newDate.getDate() - daysToMove);
    } else {
      newDate.setDate(newDate.getDate() + daysToMove);
    }
    
    setCurrentDate(newDate);
  };

  const calculateEventPositions = (events) => {
    if (!events.length) return [];

    // Sort events by start time
    const sortedEvents = [...events].sort((a, b) => {
      return new Date(a.start_datetime) - new Date(b.start_datetime);
    });

    // Calculate overlaps and assign columns
    const positionedEvents = [];
    
    for (let i = 0; i < sortedEvents.length; i++) {
      const currentEvent = sortedEvents[i];
      const currentStart = new Date(currentEvent.start_datetime);
      const currentEnd = new Date(currentEvent.end_datetime);
      
      // Find overlapping events that were already positioned
      const overlappingEvents = positionedEvents.filter(positioned => {
        const positionedStart = new Date(positioned.start_datetime);
        const positionedEnd = new Date(positioned.end_datetime);
        
        // Check if events overlap
        return (currentStart < positionedEnd && currentEnd > positionedStart);
      });

      // Find the first available column
      const usedColumns = overlappingEvents.map(e => e.column);
      let column = 0;
      while (usedColumns.includes(column)) {
        column++;
      }

      // Add positioned event
      const positionedEvent = {
        ...currentEvent,
        column: column,
        totalColumns: Math.max(column + 1, ...overlappingEvents.map(e => e.totalColumns || 1))
      };

      positionedEvents.push(positionedEvent);

      // Update totalColumns for all overlapping events
      overlappingEvents.forEach(overlapping => {
        overlapping.totalColumns = Math.max(overlapping.totalColumns || 1, column + 1);
      });

      // Update totalColumns for current event group
      const groupEvents = positionedEvents.filter(positioned => {
        const positionedStart = new Date(positioned.start_datetime);
        const positionedEnd = new Date(positioned.end_datetime);
        return (currentStart < positionedEnd && currentEnd > positionedStart);
      });

      const maxColumns = Math.max(...groupEvents.map(e => e.totalColumns || 1));
      groupEvents.forEach(event => {
        event.totalColumns = maxColumns;
      });
    }

    return positionedEvents;
  };

  const getGoogleCalendarColor = (event) => {
    // Mapeamento oficial das cores do Google Calendar
    const googleCalendarColors = {
      '1': { // Azul lavanda (padrão)
        background: '#a4bdfc',
        border: '#7986cb',
        text: '#000000',
        classes: 'border-l-blue-400'
      },
      '2': { // Verde sage
        background: '#7ae7bf',
        border: '#4caf50',
        text: '#000000',
        classes: 'border-l-green-400'
      },
      '3': { // Roxo uva
        background: '#dbadff',
        border: '#9c27b0',
        text: '#000000',
        classes: 'border-l-purple-400'
      },
      '4': { // Rosa flamingo
        background: '#ff887c',
        border: '#f44336',
        text: '#000000',
        classes: 'border-l-red-400'
      },
      '5': { // Amarelo banana
        background: '#ffd8b1',
        border: '#ff9800',
        text: '#000000',
        classes: 'border-l-yellow-400'
      },
      '6': { // Laranja tangerina
        background: '#ffb74d',
        border: '#ff5722',
        text: '#000000',
        classes: 'border-l-orange-400'
      },
      '7': { // Azul pavão
        background: '#46d6db',
        border: '#00bcd4',
        text: '#000000',
        classes: 'border-l-cyan-400'
      },
      '8': { // Cinza grafite
        background: '#e1e1e1',
        border: '#9e9e9e',
        text: '#000000',
        classes: 'border-l-gray-400'
      },
      '9': { // Azul cobalto
        background: '#5484ed',
        border: '#3f51b5',
        text: '#ffffff',
        classes: 'border-l-indigo-500'
      },
      '10': { // Verde basil
        background: '#51b749',
        border: '#4caf50',
        text: '#ffffff',
        classes: 'border-l-green-600'
      },
      '11': { // Vermelho tomate
        background: '#dc2127',
        border: '#f44336',
        text: '#ffffff',
        classes: 'border-l-red-600'
      }
    };

    // Usar cor da API do Google Calendar se disponível
    if (event.color_id && googleCalendarColors[event.color_id]) {
      return googleCalendarColors[event.color_id];
    }

    // Fallback: eventos do sistema SuperDry (azul)
    if (event.is_system_event !== false) {
      return googleCalendarColors['1']; // Azul lavanda
    }

    // Fallback padrão para eventos sem cor definida
    return googleCalendarColors['2']; // Verde sage
  };

  const handleEventDoubleClick = async (event) => {
    try {
      console.log('🖱️ Clique duplo no evento:', event.id);
      
      // Get detailed event information
      const response = await fetch(`${BACKEND_URL}/api/calendar/events/detail/${event.google_event_id || event.id}`);
      if (!response.ok) {
        throw new Error('Erro ao carregar detalhes do evento');
      }
      
      const eventDetails = await response.json();
      
      // Parse datetime for form
      const startDate = new Date(eventDetails.start_datetime);
      const endDate = new Date(eventDetails.end_datetime);
      
      setEditingEvent(eventDetails);
      setEventFormData({
        summary: eventDetails.summary || '',
        description: eventDetails.description || '',
        location: eventDetails.location || '',
        start_date: startDate.toISOString().split('T')[0],
        start_time: startDate.toTimeString().slice(0, 5),
        end_date: endDate.toISOString().split('T')[0],
        end_time: endDate.toTimeString().slice(0, 5)
      });
      setShowEditModal(true);
      
    } catch (error) {
      console.error('Erro ao abrir evento para edição:', error);
      toast({
        title: "Erro!",
        description: "Erro ao carregar detalhes do evento.",
        variant: "destructive",
      });
    }
  };

  const handleEventUpdate = async () => {
    try {
      const startDateTime = new Date(`${eventFormData.start_date}T${eventFormData.start_time}`);
      const endDateTime = new Date(`${eventFormData.end_date}T${eventFormData.end_time}`);
      
      const updateData = {
        summary: eventFormData.summary,
        description: eventFormData.description,
        location: eventFormData.location,
        start_datetime: startDateTime.toISOString(),
        end_datetime: endDateTime.toISOString()
      };
      
      const response = await fetch(`${BACKEND_URL}/api/calendar/events/${editingEvent.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData)
      });
      
      if (!response.ok) {
        throw new Error('Erro ao atualizar evento');
      }
      
      // Reload calendar events
      await loadCalendarEvents();
      
      setShowEditModal(false);
      setEditingEvent(null);
      
      toast({
        title: "Sucesso!",
        description: "Evento atualizado com sucesso!",
        variant: "default",
      });
      
    } catch (error) {
      console.error('Erro ao atualizar evento:', error);
      toast({
        title: "Erro!",
        description: "Erro ao atualizar evento. Tente novamente.",
        variant: "destructive",
      });
    }
  };

  const handleEventDelete = async () => {
    if (!window.confirm('Tem certeza que deseja excluir este evento?')) {
      return;
    }
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/calendar/events/${editingEvent.id}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error('Erro ao excluir evento');
      }
      
      // Reload calendar events
      await loadCalendarEvents();
      
      setShowEditModal(false);
      setEditingEvent(null);
      
      toast({
        title: "Sucesso!",
        description: "Evento excluído com sucesso!",
        variant: "default",
      });
      
    } catch (error) {
      console.error('Erro ao excluir evento:', error);
      toast({
        title: "Erro!",
        description: "Erro ao excluir evento. Tente novamente.",
        variant: "destructive",
      });
    }
  };

  // Função para extrair endereço legível do objeto cliente
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

  // Função para extrair complemento do endereço
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

  // Função auxiliar para buscar dados do orçamento e cliente
  const getBudgetAndClientData = async (budgetItemId) => {
    try {
      console.log(`🔍 Buscando dados para item: ${budgetItemId}`);
      
      // Buscar todos os orçamentos para encontrar o que contém este item
      const budgetsResponse = await budgetsApi.getAll();
      const budgets = budgetsResponse.data;
      
      console.log(`📊 Total de orçamentos encontrados: ${budgets.length}`);
      
      // Encontrar o orçamento que contém este item
      const budget = budgets.find(b => 
        b.items && b.items.some(item => item.id === budgetItemId)
      );
      
      if (!budget) {
        console.error(`❌ Orçamento não encontrado para item: ${budgetItemId}`);
        console.log('📋 Itens disponíveis:', budgets.map(b => ({
          id: b.id,
          items: b.items?.map(i => i.id) || []
        })));
        throw new Error(`Orçamento não encontrado para o item ${budgetItemId}`);
      }
      
      console.log(`✅ Orçamento encontrado: ${budget.id} para item: ${budgetItemId}`);
      
      // Buscar dados completos do cliente
      const clientResponse = await clientsApi.getById(budget.client_id);
      const client = clientResponse.data;
      
      console.log(`✅ Cliente encontrado: ${client.name} (${client.id})`);
      console.log('📍 Estrutura do endereço:', client.address);
      console.log('📍 Endereço extraído:', getClientAddress(client));
      console.log('📍 Complemento extraído:', getClientComplement(client));
      
      return { budget, client };
    } catch (error) {
      console.error('❌ Erro ao buscar dados do orçamento/cliente:', error);
      throw error;
    }
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
    if (name.includes('tapete')) return '🗞️';
    if (name.includes('persiana')) return '📜';
    if (name.includes('cadeira') || name.includes('cadeirão') || name.includes('cadeirao')) return '🪑';
    if (name.includes('sofa') || name.includes('sofá') || name.includes('namoradeira') || name.includes('chaise') || name.includes('cheise')) return '🛋️';
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

  // Função para formatar a descrição do evento
  const formatEventDescription = (budget, client, eventData) => {
    const totalItems = budget.items ? budget.items.length : 0;
    const totalValue = budget.items ? budget.items.reduce((sum, item) => sum + (parseFloat(item.total_value) || 0), 0) : 0;
    
    let description = `Código do Orçamento: ${budget.id}\n`;
    description += `<b>Cliente: ${client.name}</b>\n`;
    description += `Atendente: ${budget.salesperson || 'Não informado'}\n`;
    description += `Endereço: ${getClientAddress(client)}\n`;
    description += `Complemento: ${getClientComplement(client)}\n`;
    description += `Data do Orçamento: ${new Date(budget.updated_at || budget.created_at).toLocaleDateString('pt-BR')}\n`;
    description += `Forma de Pagamento: ${budget.payment_method || 'Não informado'}\n`;
    description += `<i>Observações Internas:</i> ${budget.internal_observations || 'Nenhuma observação'}\n\n`;
    description += `<b>Quantidade de Itens:</b> ${totalItems}\n`;
    
    // Adicionar itens do orçamento
    if (budget.items && budget.items.length > 0) {
      console.log('📋 Itens do orçamento:', budget.items.map(item => ({
        name: item.service_name,
        observations: item.observations,
        hasObs: !!item.observations
      })));
      
      budget.items.forEach(item => {
        const quantity = item.quantity || 1;
        const unitValue = parseFloat(item.total_value) || 0;
        let itemLine = `<i>- ${item.service_name || 'Serviço'} - ${quantity} unid. - R$ ${unitValue.toFixed(2)}`;
        
        // Adicionar observações do item se houver
        if (item.observations && item.observations.trim()) {
          itemLine += ` (Obs: ${item.observations.trim()})`;
        }
        
        itemLine += '</i>\n';
        description += itemLine;
      });
    }
    
    description += `\n<b><i>VALOR TOTAL: R$ ${totalValue.toFixed(2)}</b></i>`;
    
    return description;
  };

  // Função de debug para testar dados antes de criar eventos
  const debugEventData = async () => {
    if (!selectedRoute || selectedStops.size === 0) return;
    
    console.log('🔍 === DEBUG: DADOS DOS EVENTOS SELECIONADOS ===');
    
    const selectedEvents = routeEvents.filter(event => selectedStops.has(event.id));
    
    for (const event of selectedEvents) {
      console.log(`\n📋 Evento: ${event.client_name}`);
      console.log('   - ID do evento:', event.id);
      console.log('   - Dados completos:', event);
      
      // Tentar buscar orçamento
      try {
        const { budget, client } = await getBudgetAndClientData(event.id);
        console.log('   ✅ Orçamento encontrado:', budget.id);
        console.log('   ✅ Cliente encontrado:', client.name);
      } catch (error) {
        console.log('   ❌ Erro ao buscar orçamento:', error.message);
      }
    }
    
    console.log('🔍 === FIM DEBUG ===');
  };

  // Função para enviar eventos selecionados para o técnico
  const sendToTechnician = async () => {
    if (selectedStops.size === 0) {
      toast({
        title: "Aviso!",
        description: "Selecione pelo menos um evento para enviar ao técnico.",
        variant: "default",
      });
      return;
    }

    setSendingToTechnician(true);
    
    try {
      // Filtrar eventos selecionados e calcular horários reais
      const selectedEvents = routeEvents.filter(event => selectedStops.has(event.id));
      
      console.log(`📱 Enviando ${selectedEvents.length} eventos para técnico...`);
      
      // CORREÇÃO: Usar data e horários reais dos eventos (mesma lógica do "Lançar na Agenda")
      const eventsWithDateTime = selectedEvents.map(event => {
        // Calcular horário de início e fim baseado na data personalizada (igual ao "Lançar na Agenda")
        const startDateTime = new Date(`${customEventDate}T${event.estimated_start_time}:00`);
        const endDateTime = new Date(startDateTime.getTime() + event.duration * 60000);
        
        return {
          ...event,
          start_datetime: startDateTime.toISOString(),
          end_datetime: endDateTime.toISOString(),
          scheduled_date: customEventDate, // Data escolhida
          scheduled_time: event.estimated_start_time // Horário calculado
        };
      });
      
      console.log('🕒 Eventos com horários calculados:', eventsWithDateTime.map(e => ({
        client: e.client_name,
        start: e.start_datetime,
        end: e.end_datetime,
        date: e.scheduled_date,
        time: e.scheduled_time
      })));
      
      // Preparar dados para assignment usando budget_item_ids corretos E data/horários reais
      const assignmentData = {
        route_id: selectedRoute.id,
        event_ids: selectedEvents.map(event => {
          // CORREÇÃO CRÍTICA: Usar budget_item_id se disponível, senão usar event.id
          // Isto resolve o problema onde event_ids como EVT-003 causavam 404 errors
          // no TechnicianMode ao tentar buscar dados de orçamento
          const budget_item_id = event.budget_item_id || event.id;
          console.log(`📋 Mapeando evento ${event.id} → budget_item_id: ${budget_item_id}`);
          return budget_item_id;
        }),
        technician_id: 'TECH-001', // TODO: Permitir seleção do técnico
        assigned_date: customEventDate, // Data escolhida para lançar na agenda
        assigned_time: selectedEvents[0]?.estimated_start_time || '08:00', // Horário do primeiro evento
        assignment_type: 'AGENDA',
        // NOVO: Incluir dados de horários para sincronização
        events_schedule: eventsWithDateTime.map(event => ({
          event_id: event.budget_item_id || event.id,
          client_name: event.client_name,
          scheduled_date: event.scheduled_date,
          scheduled_time: event.scheduled_time,
          start_datetime: event.start_datetime,
          end_datetime: event.end_datetime,
          duration: event.duration
        }))
      };
      
      // Enviar para API
      const response = await technicianApi.assignEvents(assignmentData);
      
      console.log('✅ Assignment criado:', response.data);
      
      toast({
        title: "Sucesso!",
        description: `${selectedEvents.length} eventos enviados para o técnico.`,
        variant: "default",
      });

      // CORREÇÃO: NÃO limpar seleções automaticamente - manter selecionados
      // setSelectedStops(new Set());
      
      // Atualizar lista de serviços enviados
      console.log('🔄 Atualizando lista de serviços enviados...');
      await loadSentServices();
      
    } catch (error) {
      console.error('Erro ao enviar para técnico:', error);
      toast({
        title: "Erro!",
        description: "Erro ao enviar eventos para o técnico.",
        variant: "destructive",
      });
    } finally {
      setSendingToTechnician(false);
    }
  };

  const createCalendarEvents = async () => {
    if (selectedStops.size === 0) {
      toast({
        title: "Aviso!",
        description: "Selecione pelo menos um evento para lançar na agenda.",
        variant: "default",
      });
      return;
    }

    if (!customEventDate) {
      toast({
        title: "Aviso!",
        description: "Selecione uma data para os eventos.",
        variant: "default",
      });
      return;
    }

    setCreatingEvents(true);
    
    try {
      const selectedEvents = routeEvents.filter(event => selectedStops.has(event.id));
      const createdEvents = [];

      console.log('🎯 Lançando', selectedEvents.length, 'eventos na agenda:');

      for (const event of selectedEvents) {
        try {
          console.log(`📋 Processando evento: ${event.id} - ${event.client_name}`);
          
          // Buscar dados do orçamento e cliente para criar descrição rica
          const { budget, client } = await getBudgetAndClientData(event.id);
          
          // Gerar título inteligente do evento baseado em todos os itens do orçamento
          const eventTitle = generateEventTitle(budget, client.name);
          
          // Extrair endereço correto do cliente
          const clientAddress = getClientAddress(client);
          const clientComplement = getClientComplement(client);
          
          console.log(`📍 Dados do cliente para evento ${event.id}:`, {
            name: client.name,
            address: clientAddress,
            complement: clientComplement
          });
          
          // Criar descrição rica em HTML com informações detalhadas
          const eventDescription = formatEventDescription(budget, client, event);
          
          console.log(`📝 Descrição criada para ${event.id}:`, eventDescription.substring(0, 200) + '...');
          
          // Calcular horário de início e fim baseado na data personalizada
          const startDateTime = new Date(`${customEventDate}T${event.estimated_start_time}:00`);
          const endDateTime = new Date(startDateTime.getTime() + event.duration * 60000);

          const eventData = {
            summary: eventTitle,
            description: eventDescription,
            location: clientAddress,
            start_datetime: startDateTime.toISOString(),
            end_datetime: endDateTime.toISOString()
          };

          console.log(`🕒 Horários calculados para ${event.client_name}:`, {
            start: startDateTime.toISOString(),
            end: endDateTime.toISOString(),
            duration: event.duration
          });

          // Criar evento via API direta
          const response = await fetch(`${BACKEND_URL}/api/calendar/events/direct`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(eventData)
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Erro ao criar evento');
          }

          const result = await response.json();
          console.log(`✅ Evento criado: ${result.event.id} - ${result.event.summary}`);
          
          createdEvents.push({
            ...result.event,
            client_name: event.client_name,
            original_event_id: event.id
          });

        } catch (eventError) {
          console.error(`❌ Erro ao criar evento para ${event.client_name}:`, eventError);
          toast({
            title: "Erro!",
            description: `Erro ao criar evento para ${event.client_name}: ${eventError.message}`,
            variant: "destructive",
          });
        }
      }

      if (createdEvents.length > 0) {
        console.log(`🎉 Total de ${createdEvents.length} eventos criados com sucesso`);
        
        toast({
          title: "Sucesso!",
          description: `${createdEvents.length} evento(s) criado(s) na agenda com títulos inteligentes!`,
          variant: "default",
        });

        // CORREÇÃO: NÃO limpar seleções automaticamente - manter selecionados
        // setSelectedStops(new Set());
        
        // Recarregar eventos do Google Calendar
        await loadCalendarEvents();
      } else {
        toast({
          title: "Aviso!",
          description: "Nenhum evento foi criado devido a erros.",
          variant: "default",
        });
      }

    } catch (error) {
      console.error('❌ Erro geral ao lançar na agenda:', error);
      toast({
        title: "Erro!",
        description: "Erro ao lançar eventos na agenda. Tente novamente.",
        variant: "destructive",
      });
    } finally {
      setCreatingEvents(false);
    }
  };

  // Função para busca de endereços no campo Local
  const handleLocationChange = async (e) => {
    const value = e.target.value;
    setNewEvent(prev => ({ ...prev, location: value }));

    if (value.length > 2) {
      try {
        console.log('Buscando local:', value);
        const response = await placesApi.search(value);
        console.log('Resultados encontrados:', response.data.results);
        setLocationSuggestions(response.data.results || []);
      } catch (error) {
        console.error('Erro ao buscar locais:', error);
        setLocationSuggestions([]);
      }
    } else {
      setLocationSuggestions([]);
    }
  };

  // Função para selecionar uma sugestão de local
  const handleLocationSelect = async (suggestion) => {
    try {
      console.log('Selecionando local:', suggestion);
      
      let locationText = suggestion.description || suggestion.structured_formatting?.main_text || '';
      
      // Se temos o place_id, tentamos obter detalhes mais completos
      if (suggestion.place_id) {
        try {
          console.log('🔍 Buscando detalhes do local via place_id...');
          const response = await placesApi.getDetails(suggestion.place_id);
          const details = response.data.details.result;
          console.log('Detalhes obtidos da API:', details);
          
          // Usar o endereço formatado completo se disponível
          if (details && details.formatted_address) {
            locationText = details.formatted_address;
          }
        } catch (detailsError) {
          console.log('⚠️ Erro ao obter detalhes da API, usando texto da busca:', detailsError);
        }
      }
      
      // Atualizar o campo local com o endereço selecionado
      setNewEvent(prev => ({ ...prev, location: locationText }));
      
      // Limpar sugestões
      setLocationSuggestions([]);
      
      console.log('✅ Local atualizado:', locationText);
      
    } catch (error) {
      console.error('Erro ao selecionar local:', error);
      toast({
        title: "Aviso!",
        description: "Erro ao processar local selecionado.",
        variant: "default",
      });
    }
  };

  const handleCreateDirectEvent = () => {
    if (!isGoogleAuthenticated) {
      toast({
        title: "Autenticação necessária!",
        description: "Conecte-se ao Google Calendar primeiro.",
        variant: "destructive",
      });
      return;
    }

    // Initialize with default values - 2 horas de duração padrão
    const today = new Date();
    const defaultDate = today.toISOString().split('T')[0];
    const defaultTime = '08:00';
    const endTime = '10:00'; // 2 horas depois (120 minutos)

    setNewEvent({
      title: '',
      description: '',
      location: '',
      start_date: defaultDate,
      start_time: defaultTime,
      end_date: defaultDate,
      end_time: endTime,
      duration: 120 // 2 horas = 120 minutos
    });

    setShowCreateEventModal(true);
  };

  const handleConfirmCreateEvent = async () => {
    if (!newEvent.title.trim()) {
      toast({
        title: "Aviso!",
        description: "Por favor, preencha o título do evento.",
        variant: "default",
      });
      return;
    }

    setCreatingEvents(true);

    try {
      console.log('📅 Criando evento direto no Google Calendar...');
      
      // Format datetime strings for the API
      const startDateTime = `${newEvent.start_date}T${newEvent.start_time}:00`;
      const endDateTime = `${newEvent.end_date}T${newEvent.end_time}:00`;

      const eventData = {
        summary: newEvent.title,
        description: newEvent.description,
        location: newEvent.location,
        start_datetime: startDateTime,
        end_datetime: endDateTime
      };

      console.log('📤 Dados do evento:', eventData);

      const response = await fetch(`${BACKEND_URL}/api/calendar/events/direct`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(eventData)
      });

      if (!response.ok) {
        const errorData = await response.text();
        throw new Error(`Erro ${response.status}: ${errorData}`);
      }

      const data = await response.json();
      
      toast({
        title: "Sucesso!",
        description: "Evento criado no Google Calendar com sucesso!",
        variant: "default",
      });

      // Close modal and refresh calendar
      setShowCreateEventModal(false);
      
      // Refresh calendar events
      await loadCalendarEvents();
      
    } catch (error) {
      console.error('Erro ao criar evento:', error);
      toast({
        title: "Erro!",
        description: `Erro ao criar evento: ${error.message}`,
        variant: "destructive",
      });
    } finally {
      setCreatingEvents(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
        <span className="ml-2 text-lg">Carregando agenda...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agenda</h1>
          <p className="text-gray-600 mt-2">
            Gerencie e agende rotas no Google Calendar
          </p>
        </div>
        
        {!isGoogleAuthenticated && (
          <button
            onClick={authenticateWithGoogle}
            className="flex items-center px-4 py-2 bg-red-600 text-white hover:bg-red-700 rounded-lg transition-colors"
          >
            <Calendar className="w-5 h-5 mr-2" />
            Conectar Google Calendar
          </button>
        )}
        
        {isGoogleAuthenticated && (
          <div className="flex items-center space-x-4">
            <button
              onClick={handleCreateDirectEvent}
              className="flex items-center px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4 mr-2" />
              Criar Evento
            </button>
            <div className="flex items-center text-green-600">
              <CheckSquare className="w-5 h-5 mr-2" />
              Google Calendar conectado
            </div>
          </div>
        )}
      </div>

      {/* Rotas Salvas */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Rotas Salvas</h2>
        
        {savedRoutes.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            Nenhuma rota salva encontrada. Crie rotas na aba "Rotas" primeiro.
          </p>
        ) : (
          <div className="grid gap-4">
            {savedRoutes.map((route) => (
              <div
                key={route.id}
                className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                  selectedRoute?.id === route.id 
                    ? 'border-blue-500 bg-blue-50' 
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => handleRouteSelect(route)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="flex items-center">
                      {selectedRoute?.id === route.id ? (
                        <ChevronDown className="w-5 h-5 text-blue-600" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-gray-400" />
                      )}
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">{route.alias || route.id}</h3>
                      <p className="text-sm text-gray-600">
                        {route.planned_date} às {route.planned_start_time} • {route.vehicle_type} • {route.stops?.length || 0} paradas
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-green-600">
                      R$ {route.stops?.reduce((total, stop) => total + (parseFloat(stop.service_value) || 0), 0).toFixed(2) || '0,00'}
                    </p>
                    <p className="text-xs text-gray-500">
                      Atualizado: {new Date(route.updated_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Eventos da Rota Selecionada */}
      {selectedRoute && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900">
              Eventos da Rota: {selectedRoute.alias || selectedRoute.id}
            </h2>
            
            <div className="flex items-center space-x-3">
              <span className="text-sm text-gray-600">
                {selectedStops.size} de {routeEvents.length} selecionados
              </span>
              
              <div className="flex space-x-2">
                <button
                  onClick={resetAllTimes}
                  className="flex items-center px-3 py-2 bg-gray-600 text-white hover:bg-gray-700 rounded-lg transition-colors text-sm"
                  title="Resetar todos os horários para sequência original"
                >
                  <RefreshCw className="w-4 h-4 mr-1" />
                  Reset Horários
                </button>
                
                <button
                  onClick={clearAllSelections}
                  disabled={selectedStops.size === 0}
                  className="flex items-center px-3 py-2 bg-red-600 text-white hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed rounded-lg transition-colors text-sm"
                  title="Limpar todas as seleções"
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  Limpar Seleções
                </button>
                
                {selectedStops.size > 0 && (
                  <>
                    <button
                      onClick={debugEventData}
                      className="flex items-center px-3 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors text-sm mr-2"
                    >
                      🔍 Debug Dados
                    </button>
                    <button
                      onClick={sendToTechnician}
                      disabled={sendingToTechnician}
                      className="flex items-center px-4 py-2 bg-purple-600 text-white hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed rounded-lg transition-colors mr-2"
                    >
                      {sendingToTechnician ? (
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Smartphone className="w-4 h-4 mr-2" />
                      )}
                      {sendingToTechnician ? 'Enviando...' : 'Enviar para Técnico'}
                    </button>
                    <button
                      onClick={createCalendarEvents}
                      disabled={creatingEvents || !isGoogleAuthenticated}
                      className="flex items-center px-4 py-2 bg-green-600 text-white hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed rounded-lg transition-colors"
                    >
                      {creatingEvents ? (
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4 mr-2" />
                      )}
                      {creatingEvents ? 'Criando...' : 'Lançar na Agenda'}
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Campo de Data para Lançamento na Agenda */}
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center space-x-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-blue-900 mb-2">
                  📅 Data para Lançar na Agenda
                </label>
                <input
                  type="date"
                  value={customEventDate}
                  onChange={(e) => setCustomEventDate(e.target.value)}
                  className="w-full px-3 py-2 border border-blue-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
                  min={new Date().toISOString().split('T')[0]} // Não permitir datas passadas
                />
              </div>
              <div className="text-sm text-blue-700">
                <div className="font-medium">ℹ️ Horário de Início</div>
                <div>{selectedRoute.planned_start_time || '08:00'}</div>
              </div>
            </div>
            <p className="text-xs text-blue-600 mt-2">
              💡 Todos os eventos selecionados serão criados nesta data, começando no horário planejado da rota
            </p>
          </div>

          <div className="space-y-3">
            {routeEvents.map((event, index) => {
              const isSelected = selectedStops.has(event.id);
              console.log(`🔍 Renderizando evento ${index}: ${event.id} (${event.client_name}) - Selecionado: ${isSelected} - Duração: ${event.duration}min`);
              
              return (
                <div
                  key={`event-${event.id}-${index}`} // Chave mais única
                  className={`p-4 border rounded-lg transition-colors ${
                    isSelected
                      ? 'border-green-500 bg-green-50' 
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                <div className="flex items-center space-x-4">
                  {/* Checkbox */}
                  <button
                    onClick={() => toggleStopSelection(event.id)}
                    className="flex-shrink-0"
                  >
                    {isSelected ? (
                      <CheckSquare className="w-5 h-5 text-green-600" />
                    ) : (
                      <Square className="w-5 h-5 text-gray-400 hover:text-gray-600" />
                    )}
                  </button>

                  {/* Order Controls */}
                  <div className="flex flex-col space-y-1">
                    <button
                      onClick={() => moveStop(event.id, 'up')}
                      disabled={index === 0}
                      className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <ArrowUp className="w-3 h-3" />
                    </button>
                    <span className="text-xs font-medium text-gray-900 text-center">
                      {event.order_sequence}
                    </span>
                    <button
                      onClick={() => moveStop(event.id, 'down')}
                      disabled={index === routeEvents.length - 1}
                      className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <ArrowDown className="w-3 h-3" />
                    </button>
                  </div>

                  {/* Event Info */}
                  <div className="flex-1 grid grid-cols-1 md:grid-cols-5 gap-4">
                    <div className="flex items-center space-x-2">
                      <User className="w-4 h-4 text-blue-600" />
                      <div>
                        <p className="font-medium text-gray-900">{event.client_name}</p>
                        <p className="text-xs text-gray-600">{event.service_name}</p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <MapPin className="w-4 h-4 text-red-600" />
                      <span className="text-sm text-gray-700">{event.neighborhood}</span>
                    </div>

                    <div className="flex items-center space-x-2">
                      <DollarSign className="w-4 h-4 text-green-600" />
                      <span className="text-sm font-medium text-green-700">
                        R$ {event.service_value?.toFixed(2) || '0,00'}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Truck className="w-4 h-4 text-purple-600" />
                      <span className="text-sm text-gray-700">{event.vehicle_type}</span>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Clock className="w-4 h-4 text-orange-600" />
                      <div className="space-y-1">
                        <div className="flex items-center space-x-1">
                          <input
                            type="time"
                            value={event.estimated_start_time}
                            onChange={(e) => updateEventTime(event.id, e.target.value)}
                            className="text-sm font-medium text-gray-900 border border-gray-300 rounded px-2 py-1 w-20"
                          />
                          <button
                            onClick={() => recalculateFromTimeChange(event.id)}
                            className="px-2 py-1 bg-green-500 text-white text-xs rounded hover:bg-green-600 transition-colors"
                            title="Aplicar mudança de horário aos eventos seguintes"
                          >
                            Aplicar
                          </button>
                        </div>
                        <div className="flex items-center space-x-1">
                          <input
                            type="number"
                            value={event.duration}
                            onChange={(e) => updateEventDuration(event.id, e.target.value)}
                            className="text-xs text-gray-600 border border-gray-300 rounded px-1 py-0.5 w-12"
                            min="1"
                            max="480"
                          />
                          <span className="text-xs text-gray-600">min</span>
                          <button
                            onClick={() => recalculateSubsequentTimes(event.id)}
                            className="ml-1 px-2 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 transition-colors"
                            title="Aplicar mudança de duração aos horários subsequentes"
                          >
                            Aplicar
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              );
            })}
          </div>

          {routeEvents.length === 0 && (
            <p className="text-gray-500 text-center py-8">
              Nenhum evento encontrado nesta rota.
            </p>
          )}
        </div>
      )}

      {/* Seção de Serviços Enviados ao Técnico */}
      {isGoogleAuthenticated && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900">
              Serviços Enviados ao Técnico
            </h2>
            
            <div className="flex items-center space-x-4">
              {/* Filtro de Data */}
              <div className="flex items-center space-x-2">
                <label className="text-sm text-gray-600">Data:</label>
                <input
                  type="date"
                  value={sentServicesDate}
                  onChange={(e) => {
                    setSentServicesDate(e.target.value);
                    loadSentServices(e.target.value); // Recarregar automaticamente
                  }}
                  className="px-2 py-1 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              
              <div className="flex items-center space-x-3">
                <span className="text-sm text-gray-600">
                  {sentServices.length} serviço(s)
                </span>
                
                <button
                  onClick={() => loadSentServices()}
                  disabled={loadingSentServices}
                  className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  <RefreshCw className={`w-4 h-4 ${loadingSentServices ? 'animate-spin' : ''}`} />
                  <span>Atualizar Status</span>
                </button>
              </div>
            </div>
          </div>

          {loadingSentServices ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-gray-600">Carregando serviços enviados...</p>
            </div>
          ) : sentServices.length > 0 ? (
            <div className="space-y-4">
              {sentServices.map((service) => (
                <div 
                  key={service.id}
                  className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      {/* Badge do tipo */}
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        service.type === 'ASSIGNMENT' 
                          ? 'bg-purple-100 text-purple-800' 
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {service.type === 'ASSIGNMENT' ? 'Agenda' : 'Status'}
                      </span>
                      
                      <span className="font-medium text-gray-900">
                        {service.title}
                      </span>
                      
                      {/* Status badge - apenas para assignments */}
                      {service.type === 'ASSIGNMENT' && (
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          service.status === 'ASSIGNED' ? 'bg-yellow-100 text-yellow-800' :
                          service.status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-800' :
                          service.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                          service.status === 'CANCELLED' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {service.status}
                        </span>
                      )}
                      
                      {/* Status badge - para status items */}
                      {service.type === 'STATUS_ITEM' && (
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          service.status === 'EXECUTAR_NO_LOCAL' ? 'bg-purple-100 text-purple-800' :
                          service.status === 'RETIRAR' ? 'bg-blue-100 text-blue-800' :
                          service.status === 'ENTREGAR' ? 'bg-green-100 text-green-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {service.status}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center space-x-3">
                      <div className="text-sm text-gray-500">
                        {/* Mostrar data e horário */}
                        <div>
                          {new Date(service.assigned_date).toLocaleDateString('pt-BR')}
                        </div>
                        {service.assigned_time && (
                          <div className="text-xs text-blue-600">
                            {service.assigned_time}
                          </div>
                        )}
                      </div>
                      
                      {/* Botão Apagar - apenas para assignments */}
                      {service.type === 'ASSIGNMENT' && (
                        <button
                          onClick={() => handleDeleteAssignment(service.id)}
                          className="flex items-center space-x-1 px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                          title="Apagar serviço enviado ao técnico"
                        >
                          <Trash2 className="w-3 h-3" />
                          <span>Apagar</span>
                        </button>
                      )}
                    </div>
                  </div>
                  
                  {/* Conteúdo específico por tipo */}
                  {service.type === 'ASSIGNMENT' ? (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="font-medium text-gray-700">Rota:</span>
                        <p className="text-gray-600">{service.route_id || 'N/A'}</p>
                      </div>
                      
                      <div>
                        <span className="font-medium text-gray-700">Eventos:</span>
                        <p className="text-gray-600">{service.event_ids?.length || 0} item(s)</p>
                      </div>
                      
                      <div>
                        <span className="font-medium text-gray-700">Técnico:</span>
                        <p className="text-gray-600">{service.technician_id}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="font-medium text-gray-700">Cliente:</span>
                        <p className="text-gray-600">{service.client_name}</p>
                      </div>
                      
                      <div>
                        <span className="font-medium text-gray-700">Telefone:</span>
                        <p className="text-gray-600">{service.client_phone || 'N/A'}</p>
                      </div>
                      
                      <div>
                        <span className="font-medium text-gray-700">Valor:</span>
                        <p className="text-gray-600">R$ {parseFloat(service.service_value || 0).toFixed(2)}</p>
                      </div>
                    </div>
                  )}
                  
                  {/* Observações - para status items */}
                  {service.type === 'STATUS_ITEM' && service.observations && (
                    <div className="mt-3 p-2 bg-yellow-50 rounded">
                      <span className="text-xs font-medium text-yellow-800">Observações:</span>
                      <p className="text-xs text-yellow-700 mt-1">{service.observations}</p>
                    </div>
                  )}
                  
                  {/* Status detalhado (placeholder para implementação futura) */}
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      <span>👁️ Visualizado: -</span>
                      <span>📍 Localização: -</span>
                      <span>📞 Atendeu: -</span>
                      <span>📷 Fotos: -</span>
                      <span>📝 Observações: -</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Smartphone className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500">Nenhum serviço foi enviado ao técnico ainda.</p>
              <p className="text-sm text-gray-400 mt-1">
                Selecione eventos de uma rota e use o botão "Enviar para Técnico"
              </p>
            </div>
          )}
        </div>
      )}

      {/* Visualização do Calendário */}
      {isGoogleAuthenticated && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900">Visualização da Agenda</h2>
            
            {/* Controles de visualização */}
            <div className="flex items-center space-x-4">
              <div className="flex space-x-2">
                <button
                  onClick={() => setCalendarView('day')}
                  className={`px-3 py-2 text-sm rounded-lg transition-colors ${
                    calendarView === 'day' 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  1 Dia
                </button>
                <button
                  onClick={() => setCalendarView('3days')}
                  className={`px-3 py-2 text-sm rounded-lg transition-colors ${
                    calendarView === '3days' 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  3 Dias
                </button>
                <button
                  onClick={() => setCalendarView('week')}
                  className={`px-3 py-2 text-sm rounded-lg transition-colors ${
                    calendarView === 'week' 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  Semana
                </button>
              </div>
              
              {/* Navegação de datas */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => navigateDate('prev')}
                  className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ArrowUp className="w-4 h-4 rotate-[-90deg]" />
                </button>
                <span className="text-sm font-medium text-gray-900 min-w-[120px] text-center">
                  {currentDate.toLocaleDateString('pt-BR', { 
                    weekday: calendarView === 'day' ? 'long' : undefined,
                    day: 'numeric', 
                    month: 'long', 
                    year: 'numeric' 
                  })}
                </span>
                <button
                  onClick={() => navigateDate('next')}
                  className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ArrowDown className="w-4 h-4 rotate-[90deg]" />
                </button>
              </div>
            </div>
          </div>

          {/* Grade do calendário */}
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="bg-gray-50 border-b border-gray-200">
              <div className={`grid ${
                calendarView === 'week' ? 'grid-cols-8' : 
                calendarView === '3days' ? 'grid-cols-4' : 
                'grid-cols-2'
              }`}>
                <div className="p-3 text-sm font-medium text-gray-900 border-r border-gray-200">
                  Horário
                </div>
                {Array.from({ length: calendarView === 'week' ? 7 : calendarView === '3days' ? 3 : 1 }, (_, i) => {
                  const date = new Date(currentDate);
                  date.setDate(date.getDate() + i);
                  return (
                    <div key={i} className="p-3 text-sm font-medium text-gray-900 text-center border-r border-gray-200 last:border-r-0">
                      {date.toLocaleDateString('pt-BR', { weekday: 'short', day: 'numeric' })}
                    </div>
                  );
                })}
              </div>
            </div>
            
            {/* Grade de horários - das 07:00 às 00:00 com intervalos de 30min */}
            <div className="max-h-96 overflow-y-auto relative">
              <div className={`grid ${
                calendarView === 'week' ? 'grid-cols-8' : 
                calendarView === '3days' ? 'grid-cols-4' : 
                'grid-cols-2'
              } relative`}>
                {/* Coluna de horários */}
                <div className="bg-gray-50 border-r border-gray-100">
                  {Array.from({ length: 36 }, (_, index) => {
                    const totalMinutes = (7 * 60) + (index * 30); // Start at 07:00, increment by 30min
                    const hour = Math.floor(totalMinutes / 60) % 24;
                    const minute = totalMinutes % 60;
                    const isEven = index % 2 === 0;
                    
                    return (
                      <div 
                        key={index} 
                        className={`p-2 text-xs text-gray-600 border-b border-gray-100 last:border-b-0 h-8 flex items-center ${
                          isEven ? 'bg-gray-50' : 'bg-white'
                        }`}
                      >
                        {hour.toString().padStart(2, '0')}:{minute.toString().padStart(2, '0')}
                      </div>
                    );
                  })}
                </div>

                {/* Colunas dos dias */}
                {Array.from({ length: calendarView === 'week' ? 7 : calendarView === '3days' ? 3 : 1 }, (_, dayIndex) => {
                  const currentDayDate = new Date(currentDate);
                  currentDayDate.setDate(currentDayDate.getDate() + dayIndex);
                  
                  // Get all events for this day
                  const dayEvents = calendarEvents.filter(event => {
                    const eventStart = new Date(event.start_datetime);
                    return eventStart.getDate() === currentDayDate.getDate() &&
                           eventStart.getMonth() === currentDayDate.getMonth() &&
                           eventStart.getYear() === currentDayDate.getYear();
                  });

                  // Calculate overlaps and positions for events
                  const positionedEvents = calculateEventPositions(dayEvents);

                  return (
                    <div key={dayIndex} className="relative border-r border-gray-100 last:border-r-0">
                      {/* Half-hour grid lines with zebra effect */}
                      {Array.from({ length: 36 }, (_, index) => {
                        const isEven = index % 2 === 0;
                        return (
                          <div 
                            key={index} 
                            className={`h-8 border-b border-gray-100 last:border-b-0 ${
                              isEven ? 'bg-gray-50' : 'bg-white'
                            }`}
                          ></div>
                        );
                      })}

                      {/* Events positioned absolutely */}
                      {positionedEvents.map((event, index) => {
                        const eventColor = getGoogleCalendarColor(event);
                        const eventStart = new Date(event.start_datetime);
                        const eventEnd = new Date(event.end_datetime);
                        
                        // Calculate position and dimensions
                        const startHour = eventStart.getHours();
                        const startMinutes = eventStart.getMinutes();
                        const endHour = eventEnd.getHours();
                        const endMinutes = eventEnd.getMinutes();
                        
                        // Convert to grid position (relative to 07:00, now in 30-minute intervals)
                        const startTotalMinutes = (startHour - 7 + (startHour < 7 ? 24 : 0)) * 60 + startMinutes;
                        const endTotalMinutes = (endHour - 7 + (endHour < 7 ? 24 : 0)) * 60 + endMinutes;
                        
                        // Position in pixels (32px per 30 minutes = 64px per hour)
                        const top = (startTotalMinutes / 30) * 32;
                        const height = ((endTotalMinutes - startTotalMinutes) / 30) * 32;
                        
                        // Handle overlapping events
                        const leftPercent = (event.column / event.totalColumns) * 100;
                        const widthPercent = (1 / event.totalColumns) * 100;

                        return (
                          <div 
                            key={event.id}
                            className={`absolute text-xs p-1 rounded-sm shadow-sm border-l-2 cursor-pointer hover:opacity-80 transition-opacity overflow-hidden ${eventColor.classes}`}
                            style={{
                              top: `${top}px`,
                              height: `${Math.max(height, 20)}px`, // Minimum 20px height
                              left: `${leftPercent}%`,
                              width: `${widthPercent - 1}%`, // -1% for spacing
                              backgroundColor: eventColor.background,
                              borderLeftColor: eventColor.border,
                              color: eventColor.text,
                              zIndex: 10 + index
                            }}
                            title={`${event.summary}${event.location ? ' - ' + event.location : ''}\n${eventStart.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})} - ${eventEnd.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})} (Clique duplo para editar)`}
                            onDoubleClick={() => handleEventDoubleClick(event)}
                          >
                            <div className="font-medium text-xs leading-tight truncate">{event.summary}</div>
                            {height > 30 && event.location && (
                              <div className="text-xs opacity-80 truncate">{event.location}</div>
                            )}
                            {height > 50 && (
                              <div className="text-xs opacity-60">
                                {eventStart.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})} - {eventEnd.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
          
          {/* Legenda de cores do Google Calendar */}
          <div className="mt-4 p-4 bg-gray-50 rounded-lg border">
            <h4 className="text-sm font-medium text-gray-900 mb-3">Cores do Google Calendar</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#a4bdfc' }}></div>
                <span className="text-gray-700">Azul Lavanda</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#7ae7bf' }}></div>
                <span className="text-gray-700">Verde Sage</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#dbadff' }}></div>
                <span className="text-gray-700">Roxo Uva</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#ff887c' }}></div>
                <span className="text-gray-700">Rosa Flamingo</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#ffd8b1' }}></div>
                <span className="text-gray-700">SuperDry (Amarelo Banana)</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#ffb74d' }}></div>
                <span className="text-gray-700">Laranja</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#46d6db' }}></div>
                <span className="text-gray-700">Azul Pavão</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#e1e1e1' }}></div>
                <span className="text-gray-700">Cinza</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#5484ed' }}></div>
                <span className="text-gray-700">Azul Cobalto</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#51b749' }}></div>
                <span className="text-gray-700">Verde Basil</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#dc2127' }}></div>
                <span className="text-gray-700">Vermelho</span>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              * As cores dos eventos correspondem às configurações definidas no seu Google Calendar
            </p>
          </div>

          {calendarEvents.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <Calendar className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>Nenhum evento encontrado.</p>
              <p className="text-sm">Crie eventos selecionando uma rota e enviando itens para a agenda.</p>
            </div>
          )}
        </div>
      )}

      {/* Modal de Criação de Evento */}
      {showCreateEventModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Criar Novo Evento</h3>
              <p className="text-sm text-gray-600 mt-1">Duração padrão: 2 horas</p>
            </div>

            <div className="p-6 space-y-4">
              {/* Título */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Título *
                </label>
                <input
                  type="text"
                  value={newEvent.title}
                  onChange={(e) => setNewEvent(prev => ({ ...prev, title: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Digite o título do evento"
                  required
                />
              </div>

              {/* Descrição */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descrição
                </label>
                <textarea
                  value={newEvent.description}
                  onChange={(e) => setNewEvent(prev => ({ ...prev, description: e.target.value }))}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Descrição opcional do evento"
                />
              </div>

              {/* Local */}
              <div className="relative">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Local
                </label>
                <input
                  type="text"
                  value={newEvent.location}
                  onChange={handleLocationChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Digite o endereço para buscar..."
                />
                
                {locationSuggestions.length > 0 && (
                  <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-80 overflow-y-auto">
                    {locationSuggestions.map((suggestion, index) => (
                      <button
                        key={`${suggestion.place_id}-${index}`}
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          console.log('Clicou em:', suggestion);
                          handleLocationSelect(suggestion);
                        }}
                        className="w-full px-3 py-3 text-left hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors cursor-pointer"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="font-medium text-gray-900 text-sm">
                              {suggestion.structured_formatting?.main_text || suggestion.description}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {suggestion.structured_formatting?.secondary_text || ''}
                            </div>
                          </div>
                          <div className="ml-2 text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded flex-shrink-0">
                            {suggestion.source === 'places' ? 'Local' : 'Endereço'}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Data e Hora de Início */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Data Início *
                  </label>
                  <input
                    type="date"
                    value={newEvent.start_date}
                    onChange={(e) => setNewEvent(prev => ({ ...prev, start_date: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Hora Início *
                  </label>
                  <input
                    type="time"
                    value={newEvent.start_time}
                    onChange={(e) => {
                      setNewEvent(prev => {
                        // Automaticamente ajustar o horário de fim para 2 horas depois
                        const startTime = e.target.value;
                        const [hours, minutes] = startTime.split(':');
                        const startDate = new Date();
                        startDate.setHours(parseInt(hours), parseInt(minutes));
                        const endDate = new Date(startDate.getTime() + 120 * 60000); // Adicionar 2 horas
                        const endTime = endDate.toTimeString().slice(0, 5);
                        
                        return { 
                          ...prev, 
                          start_time: startTime,
                          end_time: endTime 
                        };
                      });
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>
              </div>

              {/* Data e Hora de Fim */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Data Fim *
                  </label>
                  <input
                    type="date"
                    value={newEvent.end_date}
                    onChange={(e) => setNewEvent(prev => ({ ...prev, end_date: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Hora Fim *
                  </label>
                  <input
                    type="time"
                    value={newEvent.end_time}
                    onChange={(e) => setNewEvent(prev => ({ ...prev, end_time: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>
              </div>
              
              <div className="text-xs text-gray-500 bg-blue-50 p-2 rounded">
                💡 Dica: O horário de fim é ajustado automaticamente para 2 horas após o início
              </div>
            </div>

            <div className="flex justify-end px-6 py-4 border-t border-gray-200 space-x-3">
              <button
                type="button"
                onClick={() => {
                  setShowCreateEventModal(false);
                  setLocationSuggestions([]); // Limpar sugestões de local
                  setNewEvent({
                    title: '',
                    description: '',
                    location: '',
                    start_date: '',
                    start_time: '',
                    end_date: '',
                    end_time: '',
                    duration: 120
                  });
                }}
                className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                disabled={creatingEvents}
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleConfirmCreateEvent}
                disabled={!newEvent.title || !newEvent.start_date || !newEvent.start_time || creatingEvents}
                className="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed rounded-lg transition-colors flex items-center"
              >
                {creatingEvents ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Criando...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4 mr-2" />
                    Criar Evento
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Edição de Evento */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Editar Evento</h3>
            </div>

            <div className="p-6 space-y-4">
              {/* Título */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Título *
                </label>
                <input
                  type="text"
                  value={eventFormData.summary}
                  onChange={(e) => setEventFormData(prev => ({ ...prev, summary: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>

              {/* Descrição */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descrição
                </label>
                <textarea
                  value={eventFormData.description}
                  onChange={(e) => setEventFormData(prev => ({ ...prev, description: e.target.value }))}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Local */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Local
                </label>
                <input
                  type="text"
                  value={eventFormData.location}
                  onChange={(e) => setEventFormData(prev => ({ ...prev, location: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Data e Hora de Início */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Data Início *
                  </label>
                  <input
                    type="date"
                    value={eventFormData.start_date}
                    onChange={(e) => setEventFormData(prev => ({ ...prev, start_date: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Hora Início *
                  </label>
                  <input
                    type="time"
                    value={eventFormData.start_time}
                    onChange={(e) => setEventFormData(prev => ({ ...prev, start_time: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>
              </div>

              {/* Data e Hora de Fim */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Data Fim *
                  </label>
                  <input
                    type="date"
                    value={eventFormData.end_date}
                    onChange={(e) => setEventFormData(prev => ({ ...prev, end_date: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Hora Fim *
                  </label>
                  <input
                    type="time"
                    value={eventFormData.end_time}
                    onChange={(e) => setEventFormData(prev => ({ ...prev, end_time: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-between px-6 py-4 border-t border-gray-200">
              <button
                type="button"
                onClick={handleEventDelete}
                className="px-4 py-2 bg-red-600 text-white hover:bg-red-700 rounded-lg transition-colors flex items-center"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Excluir
              </button>
              
              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowEditModal(false);
                    setEditingEvent(null);
                  }}
                  className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleEventUpdate}
                  disabled={!eventFormData.summary || !eventFormData.start_date || !eventFormData.start_time}
                  className="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed rounded-lg transition-colors"
                >
                  Salvar Alterações
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}