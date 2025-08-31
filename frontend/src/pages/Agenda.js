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
  ChevronRight
} from 'lucide-react';
import { routesApi } from '../services/api';
import { toast } from '../hooks/use-toast';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

export function Agenda() {
  const [savedRoutes, setSavedRoutes] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [routeEvents, setRouteEvents] = useState([]);
  const [selectedStops, setSelectedStops] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [creatingEvents, setCreatingEvents] = useState(false);
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
          redirect_uri: 'https://route-optimizer-19.preview.emergentagent.com/agenda'
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
    setSelectedRoute(route);
    setSelectedStops(new Set());
    
    // Transform route stops into event format
    const events = route.stops?.map((stop, index) => ({
      id: stop.id,
      order_sequence: stop.order_sequence || index + 1,
      client_name: stop.client_name,
      service_name: stop.service_name,
      service_value: stop.service_value,
      neighborhood: stop.neighborhood,
      vehicle_type: route.vehicle_type,
      service_status: stop.service_status,
      estimated_start_time: calculateEstimatedTime(route, index),
      duration: calculateDuration(stop.service_status),
      address: stop.address
    })) || [];
    
    // Sort by order_sequence
    events.sort((a, b) => a.order_sequence - b.order_sequence);
    setRouteEvents(events);
    
    // Load calendar events for this route
    loadCalendarEvents();
  };

  const calculateEstimatedTime = (route, stopIndex) => {
    // Base start time from route
    const baseTime = new Date(`${route.planned_date}T${route.planned_start_time}`);
    let currentTime = new Date(baseTime);
    
    // Add cumulative time for previous stops
    for (let i = 0; i < stopIndex; i++) {
      const stop = route.stops[i];
      const duration = calculateDuration(stop.service_status);
      currentTime = new Date(currentTime.getTime() + duration * 60000); // Convert to milliseconds
      currentTime = new Date(currentTime.getTime() + 15 * 60000); // Add 15 min travel time
    }
    
    return currentTime.toTimeString().slice(0, 5); // Return HH:MM format
  };

  const calculateDuration = (serviceStatus) => {
    switch (serviceStatus) {
      case 'EXECUTAR_NO_LOCAL':
        return 120; // 2 hours
      case 'RETIRAR':
      case 'ENTREGAR':
      default:
        return 30; // 30 minutes
    }
  };

  const toggleStopSelection = (stopId) => {
    const newSelection = new Set(selectedStops);
    if (newSelection.has(stopId)) {
      newSelection.delete(stopId);
    } else {
      newSelection.add(stopId);
    }
    setSelectedStops(newSelection);
  };

  const moveStop = (stopId, direction) => {
    const currentIndex = routeEvents.findIndex(event => event.id === stopId);
    if (currentIndex === -1) return;
    
    const newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
    if (newIndex < 0 || newIndex >= routeEvents.length) return;
    
    setRouteEvents(prevEvents => {
      const newEvents = [...prevEvents];
      // Swap elements
      [newEvents[currentIndex], newEvents[newIndex]] = [newEvents[newIndex], newEvents[currentIndex]];
      
      // Update order_sequence and recalculate times for all events
      return newEvents.map((event, index) => ({
        ...event,
        order_sequence: index + 1,
        estimated_start_time: calculateEstimatedTimeByIndex(index, newEvents)
      }));
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
        currentTime = new Date(currentTime.getTime() + 15 * 60000); // Travel time
      }
    }
    
    return currentTime.toTimeString().slice(0, 5);
  };

  const updateEventTime = (eventId, newTime) => {
    setRouteEvents(prevEvents => {
      return prevEvents.map(event => {
        if (event.id === eventId) {
          return { ...event, estimated_start_time: newTime };
        }
        return event;
      });
    });
  };

  const updateEventDuration = (eventId, newDuration) => {
    setRouteEvents(prevEvents => {
      return prevEvents.map(event => {
        if (event.id === eventId) {
          return { ...event, duration: parseInt(newDuration) };
        }
        return event;
      });
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

  const getGoogleCalendarColor = (event) => {
    // Sistema de cores similar ao Google Calendar
    
    if (event.is_system_event !== false) {
      // Eventos criados pelo sistema SuperDry - Azul (padrão Google)
      return {
        background: '#1a73e8',
        border: '#1557b0',
        text: '#ffffff',
        classes: 'border-l-blue-600'
      };
    }
    
    // Eventos externos - usar cores baseadas no conteúdo ou tipo
    const summary = event.summary?.toLowerCase() || '';
    
    if (summary.includes('reunião') || summary.includes('meeting')) {
      // Verde para reuniões
      return {
        background: '#0d7377',
        border: '#0a5d61',
        text: '#ffffff',
        classes: 'border-l-green-700'
      };
    } else if (summary.includes('almoço') || summary.includes('lunch') || summary.includes('jantar')) {
      // Laranja para refeições
      return {
        background: '#f57c00',
        border: '#e65100',
        text: '#ffffff',
        classes: 'border-l-orange-600'
      };
    } else if (summary.includes('médico') || summary.includes('doctor') || summary.includes('consulta')) {
      // Vermelho para médico/saúde
      return {
        background: '#d50000',
        border: '#b71c1c',
        text: '#ffffff',
        classes: 'border-l-red-600'
      };
    } else if (summary.includes('pessoal') || summary.includes('family') || summary.includes('família')) {
      // Roxo para pessoal/família
      return {
        background: '#8e24aa',
        border: '#6a1b9a',
        text: '#ffffff',
        classes: 'border-l-purple-600'
      };
    } else if (summary.includes('viagem') || summary.includes('travel') || summary.includes('férias')) {
      // Azul claro para viagens
      return {
        background: '#039be5',
        border: '#0277bd',
        text: '#ffffff',
        classes: 'border-l-cyan-600'
      };
    } else {
      // Padrão para outros eventos externos - Verde suave
      return {
        background: '#33b679',
        border: '#2e7d32',
        text: '#ffffff',
        classes: 'border-l-green-600'
      };
    }
  };

  const createCalendarEvents = async () => {
    if (!selectedRoute || selectedStops.size === 0) {
      toast({
        title: "Aviso!",
        description: "Selecione pelo menos um item para criar na agenda.",
        variant: "default",
      });
      return;
    }

    if (!isGoogleAuthenticated) {
      toast({
        title: "Autenticação necessária!",
        description: "Conecte-se ao Google Calendar primeiro.",
        variant: "destructive",
      });
      return;
    }

    setCreatingEvents(true);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/calendar/events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          route_id: selectedRoute.id,
          stop_ids: Array.from(selectedStops),
          start_date: selectedRoute.planned_date,
          start_time: selectedRoute.planned_start_time
        })
      });

      if (!response.ok) {
        throw new Error('Erro ao criar eventos');
      }

      const data = await response.json();
      
      toast({
        title: "Sucesso!",
        description: `${data.events.length} eventos criados no Google Calendar.`,
        variant: "default",
      });

      // Clear selection
      setSelectedStops(new Set());
      
    } catch (error) {
      console.error('Erro ao criar eventos:', error);
      toast({
        title: "Erro!",
        description: "Erro ao criar eventos no Google Calendar.",
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
          <div className="flex items-center text-green-600">
            <CheckSquare className="w-5 h-5 mr-2" />
            Google Calendar conectado
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
                      <h3 className="font-medium text-gray-900">{route.route_alias || route.id}</h3>
                      <p className="text-sm text-gray-600">
                        {route.planned_date} às {route.planned_start_time} • {route.vehicle_type} • {route.stops?.length || 0} paradas
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-green-600">
                      R$ {route.total_value?.toFixed(2) || '0,00'}
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
              Eventos da Rota: {selectedRoute.route_alias || selectedRoute.id}
            </h2>
            
            <div className="flex items-center space-x-3">
              <span className="text-sm text-gray-600">
                {selectedStops.size} de {routeEvents.length} selecionados
              </span>
              
              {selectedStops.size > 0 && (
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
              )}
            </div>
          </div>

          <div className="space-y-3">
            {routeEvents.map((event, index) => (
              <div
                key={event.id}
                className={`p-4 border rounded-lg transition-colors ${
                  selectedStops.has(event.id) 
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
                    {selectedStops.has(event.id) ? (
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
                        <input
                          type="time"
                          value={event.estimated_start_time}
                          onChange={(e) => updateEventTime(event.id, e.target.value)}
                          className="text-sm font-medium text-gray-900 border border-gray-300 rounded px-2 py-1 w-20"
                        />
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
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {routeEvents.length === 0 && (
            <p className="text-gray-500 text-center py-8">
              Nenhum evento encontrado nesta rota.
            </p>
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
            
            {/* Grade de horários - das 07:00 às 00:00 */}
            <div className="max-h-96 overflow-y-auto">
              {Array.from({ length: 18 }, (_, index) => {
                const hour = (7 + index) % 24; // Inicia às 07:00 e vai até 00:00
                return (
                <div key={hour} className={`grid ${
                  calendarView === 'week' ? 'grid-cols-8' : 
                  calendarView === '3days' ? 'grid-cols-4' : 
                  'grid-cols-2'
                } border-b border-gray-100 last:border-b-0`}>
                  <div className="p-2 text-xs text-gray-600 border-r border-gray-100 bg-gray-50">
                    {hour.toString().padStart(2, '0')}:00
                  </div>
                  {Array.from({ length: calendarView === 'week' ? 7 : calendarView === '3days' ? 3 : 1 }, (_, day) => {
                    const cellDate = new Date(currentDate);
                    cellDate.setDate(cellDate.getDate() + day);
                    cellDate.setHours(hour, 0, 0, 0);
                    
                    // Find events for this hour
                    const cellEvents = calendarEvents.filter(event => {
                      const eventStart = new Date(event.start_datetime);
                      return eventStart.getDate() === cellDate.getDate() &&
                             eventStart.getMonth() === cellDate.getMonth() &&
                             eventStart.getYear() === cellDate.getYear() &&
                             eventStart.getHours() === hour;
                    });
                    
                    return (
                      <div key={day} className="p-2 border-r border-gray-100 last:border-r-0 min-h-[40px]">
                        {cellEvents.map(event => {
                          const eventColor = getGoogleCalendarColor(event);
                          return (
                            <div 
                              key={event.id} 
                              className={`text-xs p-1.5 rounded-md mb-1 truncate shadow-sm border-l-2 ${eventColor.classes}`}
                              style={{
                                backgroundColor: eventColor.background,
                                borderLeftColor: eventColor.border,
                                color: eventColor.text
                              }}
                              title={`${event.summary}${event.location ? ' - ' + event.location : ''}`}
                            >
                              <div className="font-medium text-xs leading-tight">{event.summary}</div>
                              {event.location && (
                                <div className="text-xs opacity-80 truncate mt-0.5">{event.location}</div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    );
                  })}
                </div>
                );
              })}
            </div>
          </div>
          
          {/* Legenda de cores */}
          <div className="mt-4 p-4 bg-gray-50 rounded-lg border">
            <h4 className="text-sm font-medium text-gray-900 mb-3">Legenda de Cores</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#1a73e8' }}></div>
                <span className="text-gray-700">SuperDry (Sistema)</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#33b679' }}></div>
                <span className="text-gray-700">Eventos Gerais</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#0d7377' }}></div>
                <span className="text-gray-700">Reuniões</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#f57c00' }}></div>
                <span className="text-gray-700">Refeições</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#d50000' }}></div>
                <span className="text-gray-700">Médico/Saúde</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#8e24aa' }}></div>
                <span className="text-gray-700">Pessoal/Família</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#039be5' }}></div>
                <span className="text-gray-700">Viagens</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded bg-gradient-to-r from-blue-500 to-green-500"></div>
                <span className="text-gray-700">Outros</span>
              </div>
            </div>
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
    </div>
  );
}