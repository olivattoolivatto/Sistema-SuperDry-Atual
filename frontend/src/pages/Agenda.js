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
      
      // Load routes
      await loadSavedRoutes();
      
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

  const loadCalendarEvents = async () => {
    if (!isGoogleAuthenticated) return;
    
    try {
      // Para simplificar, vamos mostrar eventos das rotas selecionadas
      if (selectedRoute) {
        const response = await fetch(`${BACKEND_URL}/api/calendar/events/${selectedRoute.id}`);
        if (response.ok) {
          const data = await response.json();
          setCalendarEvents(data.events || []);
        }
      }
    } catch (error) {
      console.error('Erro ao carregar eventos do calendário:', error);
    }
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
                      <div>
                        <p className="text-sm font-medium text-gray-900">{event.estimated_start_time}</p>
                        <p className="text-xs text-gray-600">{event.duration} min</p>
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
    </div>
  );
}