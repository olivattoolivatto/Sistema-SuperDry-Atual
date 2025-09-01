import React, { useState, useEffect, useRef } from 'react';
import { 
  MapPin, 
  Truck, 
  Bike, 
  Play, 
  Save, 
  Edit3, 
  Trash2,
  Clock,
  Route as RouteIcon,
  ChevronUp,
  ChevronDown,
  RotateCcw
} from 'lucide-react';
import { toast } from '../hooks/use-toast';
import { routesApi } from '../services/api';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default markers in leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

export function Routes() {
  const [availableItems, setAvailableItems] = useState([]);
  const [carRouteItems, setCarRouteItems] = useState([]);
  const [motoRouteItems, setMotoRouteItems] = useState([]);
  const [prioritizationItems, setPrioritizationItems] = useState([]);
  const [optimizedRoute, setOptimizedRoute] = useState(null);
  const [savedRoutes, setSavedRoutes] = useState([]);
  const [selectedItems, setSelectedItems] = useState(new Set());
  const [loading, setLoading] = useState(true);
  // Debug tools
  const extractDebugLogs = () => {
    const logs = localStorage.getItem('routesDebugLogs') || '';
    console.log('📋 DEBUG LOGS EXPORT:');
    console.log('='.repeat(80));
    console.log(logs);
    console.log('='.repeat(80));
    return logs;
  };

  // Add debug logs to global window for easy access
  useEffect(() => {
    window.extractRoutesDebugLogs = extractDebugLogs;
    console.log('🔧 Debug function available: window.extractRoutesDebugLogs()');
  }, []);

  // Convert UTC to Cuiabá timezone (GMT-4)
  const formatCuiabaTime = (utcDateString) => {
    try {
      const utcDate = new Date(utcDateString);
      // Cuiabá is GMT-4 (4 hours behind UTC)
      const cuiabaTime = new Date(utcDate.getTime() - (4 * 60 * 60 * 1000));
      
      return cuiabaTime.toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZone: 'America/Cuiaba' // This ensures proper timezone handling
      });
    } catch (error) {
      // Fallback to UTC if conversion fails
      return new Date(utcDateString).toLocaleString('pt-BR');
    }
  };

  // Generate route alias based on date and time with future suggestions
  const generateRouteAlias = (planned_date, planned_start_time) => {
    try {
      const date = new Date(planned_date);
      const [hours] = planned_start_time.split(':');
      const hour = parseInt(hours);
      
      // Determine period
      const period = hour >= 13 ? 'TARDE' : 'MANHÃ';
      
      // Get day of week in Portuguese
      const dayNames = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado'];
      const dayName = dayNames[date.getDay()];
      
      // Format date as DD/MM/YY
      const formattedDate = date.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: '2-digit'
      });
      
      return `Rota ${period} da ${dayName} ${formattedDate}`;
    } catch (error) {
      return `Rota ${planned_date}`;
    }
  };

  // Get suggested future date and time for new routes
  const getSuggestedDateTime = () => {
    const now = new Date();
    const currentHour = now.getHours();
    
    let suggestedDate, suggestedTime;
    
    if (currentHour < 13) {
      // If before 1 PM, suggest today at 1 PM
      suggestedDate = now.toISOString().split('T')[0];
      suggestedTime = '13:00';
    } else {
      // If after 1 PM, suggest tomorrow at 8 AM
      const tomorrow = new Date(now);
      tomorrow.setDate(tomorrow.getDate() + 1);
      suggestedDate = tomorrow.toISOString().split('T')[0];
      suggestedTime = '08:00';
    }
    
    return { suggestedDate, suggestedTime };
  };

  // Get neighborhoods from route stops with VG suffix for Várzea Grande
  const getRouteNeighborhoods = (stops) => {
    if (!stops || stops.length === 0) return '';
    
    const neighborhoods = stops
      .map(stop => {
        let neighborhood = stop.address?.neighborhood || stop.neighborhood || '';
        
        // Add (VG) suffix if city is Várzea Grande
        const city = stop.address?.city || stop.city || '';
        if (city.toLowerCase().includes('várzea grande') || city.toLowerCase().includes('varzea grande')) {
          neighborhood = neighborhood ? `${neighborhood} (VG)` : 'Várzea Grande (VG)';
        }
        
        return neighborhood;
      })
      .filter(n => n && n.trim() !== '')
      .filter((neighborhood, index, arr) => arr.indexOf(neighborhood) === index); // Remove duplicates
    
    return neighborhoods.length > 0 ? neighborhoods.join(', ') : 'Bairros não informados';
  };

  // Debug state
  const [debugInfo, setDebugInfo] = useState(''); // Debug info state
  const [isCalculatingRoute, setIsCalculatingRoute] = useState(false); // Loading state for route calculation
  
  // Enhanced logging system
  const logAction = (action, data) => {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = `[${timestamp}] ${action}: ${JSON.stringify(data, null, 2)}`;
    console.log(`🔍 USER ACTION: ${logEntry}`);
    
    // Also store in localStorage for persistence
    const existingLogs = localStorage.getItem('routesDebugLogs') || '';
    const newLogs = existingLogs + '\n' + logEntry;
    localStorage.setItem('routesDebugLogs', newLogs);
  };

  // Clear logs on component mount
  useEffect(() => {
    console.log('🧹 Clearing previous debug logs...');
    localStorage.removeItem('routesDebugLogs');
    logAction('COMPONENT_MOUNTED', { timestamp: new Date().toISOString() });
  }, []);
  
  // Route optimization form with future date suggestions
  const { suggestedDate, suggestedTime } = getSuggestedDateTime();
  const [routeDate, setRouteDate] = useState(suggestedDate);
  const [routeTime, setRouteTime] = useState(suggestedTime);
  const [currentVehicleType, setCurrentVehicleType] = useState('CARRO');
  const [routeAlias, setRouteAlias] = useState('');
  const [routeType, setRouteType] = useState('CURTA'); // New: CURTA or EFICIENTE
  
  // Map state
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const [stopPriorities, setStopPriorities] = useState({});

  useEffect(() => {
    loadAvailableItems();
    loadSavedRoutes();
    
    console.log('🚀 Routes component mounted');
    console.log('🗺️ Leaflet disponível:', typeof L !== 'undefined');
    
    // Check if Leaflet CSS is loaded
    const leafletCSS = document.querySelector('link[href*="leaflet"]');
    console.log('🎨 Leaflet CSS encontrado:', !!leafletCSS);
    
    if (typeof L === 'undefined') {
      console.log('❌ Leaflet não carregado! Tentando importar...');
      import('leaflet').then((leaflet) => {
        window.L = leaflet.default;
        console.log('✅ Leaflet importado dinamicamente');
      }).catch(err => {
        console.error('❌ Erro ao importar Leaflet:', err);
      });
    }
  }, []);

  useEffect(() => {
    console.log('🔍 State updated:');
    console.log('- carRouteItems:', carRouteItems.length);
    console.log('- motoRouteItems:', motoRouteItems.length);
    console.log('- availableItems:', availableItems.length);
  }, [carRouteItems, motoRouteItems, availableItems]);

  // Initialize map when component mounts
  useEffect(() => {
    // Always initialize map after a short delay
    const timer = setTimeout(() => {
      if (mapRef.current && !mapInstanceRef.current) {
        console.log('🗺️ Initializing map on component mount');
        initializeEmptyMap();
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  // Update map when optimized route changes
  useEffect(() => {
    if (optimizedRoute && mapInstanceRef.current) {
      console.log('🗺️ Updating map with new route data');
      updateMapWithRoute();
    }
  }, [optimizedRoute]);

  const loadAvailableItems = async () => {
    try {
      const response = await routesApi.getAvailableItems();
      setAvailableItems(response.data.available_items);
    } catch (error) {
      console.error('Erro ao carregar itens disponíveis:', error);
      toast({
        title: "Erro!",
        description: "Erro ao carregar itens disponíveis para rotas.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const loadSavedRoutes = async () => {
    try {
      const response = await routesApi.getSavedRoutes();
      setSavedRoutes(response.data || []);
    } catch (error) {
      console.error('Erro ao carregar rotas salvas:', error);
    }
  };

  const initializeEmptyMap = () => {
    console.log('🗺️ Tentando inicializar mapa vazio...');
    
    if (!mapRef.current) {
      console.log('❌ Elemento do mapa não encontrado');
      return;
    }

    try {
      // Remove existing map if any
      if (mapInstanceRef.current) {
        console.log('🧹 Removendo mapa existente...');
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }

      // Check if Leaflet is available
      if (typeof L === 'undefined') {
        console.log('❌ Leaflet não está disponível');
        return;
      }

      console.log('✅ Leaflet disponível, criando mapa...');

      // Default to Cuiabá coordinates
      const defaultLat = -15.601481;
      const defaultLng = -56.097389;

      // Create map with basic configuration
      mapInstanceRef.current = L.map(mapRef.current).setView([defaultLat, defaultLng], 11);

      // Add OpenStreetMap tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
      }).addTo(mapInstanceRef.current);

      // Add a simple marker to show the map is working
      L.marker([defaultLat, defaultLng])
        .addTo(mapInstanceRef.current)
        .bindPopup('Centro de Cuiabá<br>Aguardando dados da rota...');

      console.log('✅ Mapa vazio inicializado com sucesso!');
      
      // Force resize after initialization
      setTimeout(() => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.invalidateSize();
          console.log('🔄 Mapa redimensionado');
        }
      }, 100);
      
    } catch (error) {
      console.error('❌ Erro ao inicializar mapa vazio:', error);
      
      // Fallback: show simple message in map container
      if (mapRef.current) {
        mapRef.current.innerHTML = `
          <div style="display: flex; align-items: center; justify-content: center; height: 100%; background: #f3f4f6; color: #6b7280; font-size: 14px;">
            <div style="text-align: center;">
              <div>🗺️</div>
              <div>Mapa será exibido aqui</div>
              <div style="font-size: 12px; margin-top: 8px;">Aguardando otimização de rota...</div>
            </div>
          </div>
        `;
      }
    }
  };

  const initializeMap = () => {
    console.log('🗺️ Initializing map...');
    console.log('- mapRef.current:', !!mapRef.current);
    console.log('- optimizedRoute:', !!optimizedRoute);
    console.log('- company_address:', !!optimizedRoute?.company_address);
    
    if (!mapRef.current) {
      console.log('❌ Map container not available');
      return;
    }

    if (!optimizedRoute?.company_address) {
      console.log('❌ Company address not available');
      return;
    }

    const companyLat = optimizedRoute.company_address.latitude;
    const companyLng = optimizedRoute.company_address.longitude;

    console.log('📍 Company coordinates:', { lat: companyLat, lng: companyLng });

    if (!companyLat || !companyLng) {
      console.log('❌ Invalid company coordinates');
      return;
    }

    try {
      // Remove existing map if any
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }

      // Create map centered on company location (Cuiabá region)
      mapInstanceRef.current = L.map(mapRef.current, {
        center: [companyLat, companyLng],
        zoom: 13,
        zoomControl: true,
        scrollWheelZoom: true
      });

      // Add OpenStreetMap tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
      }).addTo(mapInstanceRef.current);

      console.log('✅ Map initialized successfully');

      // Update with route data
      updateMapWithRoute();
      
    } catch (error) {
      console.error('❌ Error initializing map:', error);
    }
  };

  const updateMapWithRoute = () => {
    logAction('UPDATE_MAP_START', { 
      hasMapInstance: !!mapInstanceRef.current, 
      hasOptimizedRoute: !!optimizedRoute,
      stopsCount: optimizedRoute?.stops?.length || 0,
      hasCompanyAddress: !!optimizedRoute?.company_address,
      hasRouteGeometry: !!optimizedRoute?.route_geometry
    });
    
    console.log('🗺️ Updating map with route...');
    console.log('- mapInstanceRef.current:', !!mapInstanceRef.current);
    console.log('- optimizedRoute:', !!optimizedRoute);
    console.log('- stops count:', optimizedRoute?.stops?.length || 0);
    console.log('- company_address:', !!optimizedRoute?.company_address);
    
    if (!mapInstanceRef.current || !optimizedRoute || !optimizedRoute.company_address) {
      console.log('❌ Map instance, route, or company address not available');
      logAction('UPDATE_MAP_FAILED', { 
        reason: 'Missing requirements',
        hasMapInstance: !!mapInstanceRef.current,
        hasOptimizedRoute: !!optimizedRoute,
        hasCompanyAddress: !!optimizedRoute?.company_address
      });
      return;
    }

    if (!optimizedRoute.stops || optimizedRoute.stops.length === 0) {
      console.log('❌ No stops available in route');
      logAction('UPDATE_MAP_FAILED', { reason: 'No stops available' });
      return;
    }

    try {
      logAction('MAP_CLEARING_LAYERS', {});
      
      // Clear existing markers and polylines, but keep the base map
      mapInstanceRef.current.eachLayer((layer) => {
        if (layer instanceof L.Marker || layer instanceof L.Polyline) {
          mapInstanceRef.current.removeLayer(layer);
        }
      });

      const companyLat = optimizedRoute.company_address.latitude;
      const companyLng = optimizedRoute.company_address.longitude;

      console.log('🏢 Adding company marker at:', { lat: companyLat, lng: companyLng });

      // Add company marker (start/end point)
      const companyIcon = L.divIcon({
        className: 'company-marker',
        html: `<div style="
          background: linear-gradient(135deg, #10B981 0%, #059669 100%);
          color: white;
          width: 50px;
          height: 50px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          border: 4px solid white;
          box-shadow: 0 4px 8px rgba(0,0,0,0.4);
          font-size: 20px;
          position: relative;
        ">
          🏢
          <div style="
            position: absolute;
            bottom: -8px;
            left: 50%;
            transform: translateX(-50%);
            background: #059669;
            color: white;
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 8px;
            white-space: nowrap;
          ">INÍCIO/FIM</div>
        </div>`,
        iconSize: [50, 50],
        iconAnchor: [25, 25]
      });
      
      const companyMarker = L.marker([companyLat, companyLng], { icon: companyIcon })
        .addTo(mapInstanceRef.current)
        .bindPopup(`<div style="text-align: center;">
          <h4 style="margin: 0 0 8px 0; color: #10B981; font-weight: bold;">🏢 ${optimizedRoute.company_address.name || 'SuperDry - Sede'}</h4>
          <div style="background: #F0FDF4; padding: 8px; border-radius: 6px; margin: 8px 0;">
            <p style="margin: 0; color: #059669; font-weight: bold;">🚀 INÍCIO da Rota (1º local)</p>
            <p style="margin: 4px 0 0 0; color: #059669; font-weight: bold;">🏁 FIM da Rota (último local)</p>
          </div>
          <p style="margin: 4px 0; font-size: 11px; color: #666;">${optimizedRoute.company_address.full_address || 'Endereço da empresa'}</p>
        </div>`);

      console.log('✅ Company marker added');
      logAction('COMPANY_MARKER_ADDED', { coordinates: [companyLat, companyLng] });

      // Add numbered markers for each stop
      const markers = [companyMarker]; // For bounds calculation
      
      // Sort stops by order_sequence to display in optimized order
      const sortedStops = [...optimizedRoute.stops].sort((a, b) => (a.order_sequence || 0) - (b.order_sequence || 0));
      
      sortedStops.forEach((stop, arrayIndex) => {
        const lat = stop.address.latitude;
        const lng = stop.address.longitude;
        
        // Use the OSRM-optimized order_sequence, not array index
        const deliveryOrder = stop.order_sequence || (arrayIndex + 1);
        
        console.log(`📍 Adding stop for ${stop.client_name} at:`, { 
          lat, lng, 
          client: stop.client_name, 
          order: deliveryOrder,
          originalIndex: arrayIndex + 1,
          osrmSequence: stop.order_sequence 
        });
        
        logAction('ADDING_STOP_MARKER', { 
          stopIndex: arrayIndex + 1, 
          coordinates: [lat, lng], 
          clientName: stop.client_name, 
          orderSequence: deliveryOrder,
          osrmOptimized: stop.order_sequence 
        });
        
        if (lat && lng && !isNaN(lat) && !isNaN(lng)) {
          const displayName = stop.client_name.split(' ')[0] || stop.client_name.substring(0, 8);
          
          const markerIcon = L.divIcon({
            html: `<div style="
              background: linear-gradient(135deg, #DC2626 0%, #B91C1C 100%); 
              color: white; 
              border-radius: 12px; 
              padding: 6px 12px;
              display: flex; 
              align-items: center; 
              justify-content: center; 
              font-weight: bold; 
              border: 3px solid white; 
              box-shadow: 0 4px 8px rgba(0,0,0,0.3); 
              font-size: 12px;
              min-width: 60px;
              max-width: 100px;
              position: relative;
            ">
              <span style="
                background: #FFF; 
                color: #DC2626; 
                border-radius: 50%; 
                width: 22px; 
                height: 22px; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                font-size: 11px; 
                font-weight: bold;
                margin-right: 6px;
                border: 1px solid #DC2626;
              ">${deliveryOrder}</span>
              <span style="font-size: 11px;">${displayName}</span>
            </div>`,
            className: 'custom-div-icon',
            iconSize: [80, 32],
            iconAnchor: [40, 16]
          });

          const marker = L.marker([lat, lng], { icon: markerIcon })
            .addTo(mapInstanceRef.current);

          // Create detailed popup content with correct sequence information
          const popupContent = `
            <div style="min-width: 280px; font-size: 13px;">
              <h4 style="margin: 0 0 8px 0; color: #DC2626; font-weight: bold;">
                🎯 ${deliveryOrder}ª PARADA: ${stop.client_name}
              </h4>
              <div style="background: #EFF6FF; padding: 8px; border-radius: 6px; margin: 6px 0; border-left: 4px solid #3B82F6;">
                <strong>📍 Sequência OSRM:</strong> ${deliveryOrder}º lugar na rota otimizada
                <div style="font-size: 11px; color: #6B7280; margin-top: 2px;">
                  (Otimizado pela API OSRM para eficiência máxima)
                </div>
              </div>
              <p style="margin: 4px 0;"><b>🛠️ Serviço:</b> ${stop.service_name}</p>
              <p style="margin: 4px 0;"><b>💰 Valor:</b> R$ ${stop.service_value.toFixed(2)}</p>
              <p style="margin: 4px 0;"><b>⏱️ Duração:</b> ${stop.estimated_duration} minutos</p>
              <p style="margin: 4px 0;"><b>🎚️ Prioridade:</b> <span style="color: #7C3AED;">${stop.priority}</span></p>
              <p style="margin: 4px 0;"><b>📋 Tipo:</b> ${stop.service_status}</p>
              <hr style="margin: 8px 0;">
              <p style="margin: 0; font-size: 11px; color: #666;">📍 ${stop.address.full_address || stop.address.neighborhood}</p>
            </div>
          `;
          
          marker.bindPopup(popupContent);
          markers.push(marker);
          
          console.log(`✅ Stop marker added for ${stop.client_name} - OSRM Order: ${deliveryOrder} (Original: ${arrayIndex + 1})`);
          logAction('STOP_MARKER_ADDED', { 
            clientName: stop.client_name, 
            deliveryOrder: deliveryOrder, 
            orderSequence: stop.order_sequence,
            osrmOptimized: true
          });
        } else {
          console.log(`❌ Invalid coordinates for ${stop.client_name}:`, { lat, lng });
          logAction('INVALID_STOP_COORDINATES', { clientName: stop.client_name, coordinates: [lat, lng] });
        }
      });

      // Draw route line if geometry is available
      if (optimizedRoute.route_geometry && optimizedRoute.route_geometry.coordinates) {
        console.log('🛣️ Drawing route line...');
        logAction('DRAWING_ROUTE_GEOMETRY', { geometryPoints: optimizedRoute.route_geometry.coordinates.length });
        
        const routeCoords = optimizedRoute.route_geometry.coordinates.map(coord => [coord[1], coord[0]]);
        
        const routeLine = L.polyline(routeCoords, {
          color: '#DC2626',
          weight: 5,
          opacity: 0.8,
          dashArray: '10, 5'
        }).addTo(mapInstanceRef.current);

        console.log('✅ Route line drawn with', routeCoords.length, 'points');
        logAction('ROUTE_LINE_DRAWN', { points: routeCoords.length, type: 'geometry' });
      } else {
        console.log('⚠️ No route geometry available');
        logAction('NO_ROUTE_GEOMETRY', {});
        
        // Draw simple lines between points if no geometry
        if (optimizedRoute.stops.length > 0) {
          const simpleRoute = [
            [companyLat, companyLng],
            ...optimizedRoute.stops
              .filter(stop => stop.address.latitude && stop.address.longitude)
              .map(stop => [stop.address.latitude, stop.address.longitude]),
            [companyLat, companyLng]
          ];
          
          L.polyline(simpleRoute, {
            color: '#3B82F6',
            weight: 3,
            opacity: 0.6,
            dashArray: '5, 10'
          }).addTo(mapInstanceRef.current);
          
          console.log('✅ Simple route line drawn');
          logAction('SIMPLE_ROUTE_LINE_DRAWN', { points: simpleRoute.length });
        }
      }

      // Adjust map view to fit all markers
      if (markers.length > 1) {
        console.log('🔍 Fitting bounds for', markers.length, 'markers');
        logAction('FITTING_MAP_BOUNDS', { markersCount: markers.length });
        const group = new L.featureGroup(markers);
        mapInstanceRef.current.fitBounds(group.getBounds().pad(0.15));
        logAction('MAP_BOUNDS_SET', { type: 'fitted_to_markers' });
      } else {
        // Fallback to company location
        mapInstanceRef.current.setView([companyLat, companyLng], 13);
        logAction('MAP_BOUNDS_SET', { type: 'fallback_to_company', coordinates: [companyLat, companyLng] });
      }

      console.log('✅ Map update completed successfully');
      logAction('UPDATE_MAP_SUCCESS', { 
        stopsCount: optimizedRoute.stops.length,
        markersCount: markers.length,
        hasRouteGeometry: !!(optimizedRoute.route_geometry && optimizedRoute.route_geometry.coordinates)
      });

    } catch (error) {
      console.error('❌ Error updating map:', error);
      logAction('UPDATE_MAP_ERROR', { error: error.message, stack: error.stack });
    }
  };

  const handleItemSelection = (item, isSelected) => {
    const newSelected = new Set(selectedItems);
    if (isSelected) {
      newSelected.add(item.budget_item_id);
    } else {
      newSelected.delete(item.budget_item_id);
    }
    setSelectedItems(newSelected);
  };

  const handleVehicleAssignment = (item, vehicleType) => {
    logAction('VEHICLE_ASSIGNMENT_START', { item: item.budget_item_id, vehicleType, clientName: item.client_name });
    
    console.log('🚗 handleVehicleAssignment called:', { item: item.budget_item_id, vehicleType });
    console.log('🚗 Current carRouteItems:', carRouteItems);
    console.log('🚗 Current motoRouteItems:', motoRouteItems);
    
    if (vehicleType === 'CARRO') {
      console.log('🚗 Adding to car route items');
      setCarRouteItems(prev => {
        const newItems = [...prev, item];
        console.log('🚗 New car route items:', newItems);
        return newItems;
      });
      logAction('ITEM_ADDED_TO_CAR', { item: item.budget_item_id, clientName: item.client_name });
    } else {
      console.log('🏍️ Adding to moto route items');
      setMotoRouteItems(prev => {
        const newItems = [...prev, item];
        console.log('🏍️ New moto route items:', newItems);
        return newItems;
      });
      logAction('ITEM_ADDED_TO_MOTO', { item: item.budget_item_id, clientName: item.client_name });
    }
    
    // Remove from available items
    console.log('➖ Removing from available items');
    setAvailableItems(prev => prev.filter(i => i.budget_item_id !== item.budget_item_id));
    
    // Remove from selection
    const newSelected = new Set(selectedItems);
    newSelected.delete(item.budget_item_id);
    setSelectedItems(newSelected);
    
    console.log('✅ Vehicle assignment completed');
    logAction('VEHICLE_ASSIGNMENT_COMPLETED', { vehicleType, remainingAvailable: availableItems.length - 1 });
  };

  const handleRemoveFromRoute = (itemId, fromRoute) => {
    // Find the item to restore
    let itemToRestore;
    
    if (fromRoute === 'CARRO') {
      itemToRestore = carRouteItems.find(item => item.budget_item_id === itemId);
      setCarRouteItems(prev => prev.filter(item => item.budget_item_id !== itemId));
    } else {
      itemToRestore = motoRouteItems.find(item => item.budget_item_id === itemId);
      setMotoRouteItems(prev => prev.filter(item => item.budget_item_id !== itemId));
    }
    
    // Add back to available items
    if (itemToRestore) {
      setAvailableItems(prev => [...prev, itemToRestore]);
    }
  };

  const handleOptimizeRoute = async (vehicleType) => {
    logAction('MOVE_TO_PRIORITIZATION_START', { vehicleType });
    
    console.log('🚀 Moving items to prioritization for vehicleType:', vehicleType);
    
    const items = vehicleType === 'CARRO' ? carRouteItems : motoRouteItems;
    logAction('ITEMS_TO_PRIORITIZE', { count: items.length, items: items.map(i => ({ id: i.budget_item_id, client: i.client_name })) });
    
    if (items.length === 0) {
      toast({
        title: "Aviso",
        description: "Adicione itens à rota antes de enviar para priorização.",
        variant: "default",
      });
      return;
    }

    // Add items to prioritization list with default priority and vehicle type
    const itemsWithPriority = items.map(item => ({
      ...item,
      priority: 'AUTOMATICA',
      vehicleType: vehicleType
    }));

    setPrioritizationItems(prev => [...prev, ...itemsWithPriority]);
    setCurrentVehicleType(vehicleType);
    
    // Clear the route items that were moved to prioritization
    if (vehicleType === 'CARRO') {
      setCarRouteItems([]);
    } else {
      setMotoRouteItems([]);
    }
    
    toast({
      title: "Itens enviados!",
      description: `${items.length} itens enviados para priorização de rota.`,
      variant: "default",
    });

    // NOVO: Scroll automático para a seção de priorização
    setTimeout(() => {
      const prioritizationElements = document.querySelectorAll('h2');
      const prioritizationSection = Array.from(prioritizationElements).find(h2 => 
        h2.textContent.includes('Priorização de Rota')
      );
      if (prioritizationSection) {
        prioritizationSection.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'start' 
        });
        console.log('📍 Scrolled to prioritization section');
        logAction('SCROLLED_TO_PRIORITIZATION', { vehicleType });
      }
    }, 500);

    console.log('✅ Items moved to prioritization successfully');
    logAction('MOVE_TO_PRIORITIZATION_COMPLETED', { vehicleType, totalPrioritizationItems: prioritizationItems.length + items.length });
  };

  const handlePriorityChange = async (itemId, newPriority) => {
    setPrioritizationItems(prev => 
      prev.map(item => 
        item.budget_item_id === itemId 
          ? { ...item, priority: newPriority }
          : item
      )
    );
  };

  const handleCalculateOptimizedRoute = async (routeType) => {
    logAction('CALCULATE_ROUTE_START', { 
      routeType, 
      prioritizationItemsCount: prioritizationItems.length,
      vehicleType: currentVehicleType,
      routeDate,
      routeTime,
      items: prioritizationItems.map(i => ({ id: i.budget_item_id, client: i.client_name, priority: i.priority }))
    });
    
    console.log('🚀 BOTÃO CALCULAR ROTA CLICADO!');
    console.log('Items na priorização:', prioritizationItems);
    
    console.log('🚀 === INICIANDO OTIMIZAÇÃO ===');
    console.log('Prioritization items:', prioritizationItems);
    console.log('Route type:', routeType);
    console.log('Vehicle type:', currentVehicleType);
    
    // NOVO: Ativar popup de loading ao invés do debug discreto
    setIsCalculatingRoute(true);
    setDebugInfo(`Iniciando otimização ${routeType.toLowerCase()}...`);
    
    if (prioritizationItems.length === 0) {
      console.log('❌ Nenhum item para otimizar');
      logAction('CALCULATE_ROUTE_ERROR', { error: 'No items to optimize', routeType });
      toast({
        title: "Aviso",
        description: "Adicione itens à lista de priorização antes de otimizar.",
        variant: "default",
      });
      return;
    }

    // Validate that all clients have addresses
    const itemsWithoutAddress = prioritizationItems.filter(item => {
      return !item.address || 
             !item.address.latitude || 
             !item.address.longitude || 
             !item.address.full_address;
    });

    if (itemsWithoutAddress.length > 0) {
      console.log('❌ Clientes sem endereço completo:', itemsWithoutAddress);
      logAction('CALCULATE_ROUTE_ERROR', { 
        error: 'Clients without complete address', 
        routeType,
        clientsWithoutAddress: itemsWithoutAddress.map(item => item.client_name)
      });
      
      const clientNames = itemsWithoutAddress.map(item => item.client_name).join(', ');
      toast({
        title: "Endereços Incompletos!",
        description: `Os seguintes clientes não possuem endereço completo cadastrado: ${clientNames}. Por favor, complete o cadastro antes de otimizar a rota.`,
        variant: "destructive",
      });
      return;
    }

    // Validate that all clients have proper neighborhood (not "BAIRRO A COMPLETAR")
    const itemsWithIncompleteNeighborhood = prioritizationItems.filter(item => {
      const neighborhood = item.address?.neighborhood || item.neighborhood || '';
      return neighborhood === 'BAIRRO A COMPLETAR' || neighborhood.toUpperCase() === 'BAIRRO A COMPLETAR';
    });

    if (itemsWithIncompleteNeighborhood.length > 0) {
      console.log('❌ Clientes com bairro incompleto:', itemsWithIncompleteNeighborhood);
      logAction('CALCULATE_ROUTE_ERROR', { 
        error: 'Clients with incomplete neighborhood', 
        routeType,
        clientsWithIncompleteNeighborhood: itemsWithIncompleteNeighborhood.map(item => item.client_name)
      });
      
      const clientNames = itemsWithIncompleteNeighborhood.map(item => item.client_name).join(', ');
      toast({
        title: "Cadastros Incompletos!",
        description: `Os seguintes clientes precisam ter o BAIRRO completado no cadastro: ${clientNames}. Por favor, edite o cadastro dos clientes antes de otimizar a rota.`,
        variant: "destructive",
      });
      return;
    }

    try {
      console.log('🔨 Criando rota...');
      logAction('CREATING_ROUTE', { vehicleType: currentVehicleType, date: routeDate, time: routeTime });
      
      // Create route
      const routeData = {
        vehicle_type: currentVehicleType,
        planned_date: routeDate,
        planned_start_time: routeTime,
        stops: []
      };

      console.log('📤 Enviando dados para criar rota:', routeData);
      const createResponse = await routesApi.createRoute(routeData);
      console.log('✅ Rota criada:', createResponse.data);
      const routeId = createResponse.data.id;
      logAction('ROUTE_CREATED', { routeId, response: createResponse.data });
      
      // Add stops with priorities from prioritization list
      const stopsData = prioritizationItems.map(item => ({
        budget_item_id: item.budget_item_id,
        priority: item.priority
      }));
      
      console.log('📍 Adicionando paradas:', stopsData);
      logAction('ADDING_STOPS', { routeId, stopsCount: stopsData.length, stops: stopsData });
      const stopsResponse = await routesApi.updateRouteStops(routeId, stopsData);
      console.log('✅ Paradas adicionadas:', stopsResponse.data);
      logAction('STOPS_ADDED', { routeId, response: stopsResponse.data });
      
      // Optimize route based on selected type
      console.log(`⚡ Otimizando rota ${routeType}...`);
      logAction('OPTIMIZING_ROUTE', { routeId, routeType });
      const optimizeResponse = await routesApi.optimizeRoute(routeId, { route_type: routeType });
      console.log('⚡ Resposta da otimização:', optimizeResponse.data);
      logAction('ROUTE_OPTIMIZED', { routeId, response: optimizeResponse.data });
      
      // Get optimized route details
      console.log('📋 Buscando detalhes da rota...');
      const routeDetails = await routesApi.getRoute(routeId);
      console.log('📋 Detalhes da rota:', routeDetails.data);
      logAction('ROUTE_DETAILS_FETCHED', { routeId, details: routeDetails.data });
      
      // CRITICAL: Set the optimized route data
      console.log('💾 Definindo optimizedRoute state...');
      console.log('💾 Dados recebidos:', routeDetails.data);
      setOptimizedRoute(routeDetails.data);
      setDebugInfo(`Rota ${routeId} otimizada às ${new Date().toLocaleTimeString()} - ${routeDetails.data.stops?.length || 0} paradas - ${routeDetails.data.total_distance || '0'} km - ${routeDetails.data.total_duration || '0'} min`);
      console.log('💾 optimizedRoute definido!');
      logAction('OPTIMIZED_ROUTE_STATE_SET', { 
        routeId, 
        stopsCount: routeDetails.data.stops?.length || 0,
        distance: routeDetails.data.total_distance,
        duration: routeDetails.data.total_duration,
        hasCompanyAddress: !!routeDetails.data.company_address,
        hasRouteGeometry: !!routeDetails.data.route_geometry
      });
      
      // Initialize stop priorities state
      const priorities = {};
      if (routeDetails.data.stops) {
        routeDetails.data.stops.forEach(stop => {
          priorities[stop.id] = stop.priority;
        });
      }
      setStopPriorities(priorities);

      // Clear prioritization items after successful optimization
      console.log('🧹 Limpando lista de priorização...');
      setPrioritizationItems([]);
      
      console.log('🎉 OTIMIZAÇÃO CONCLUÍDA COM SUCESSO!');
      
      // Scroll to the visualization section after a short delay
      setTimeout(() => {
        const visualizationSection = document.getElementById('visualization-section');
        if (visualizationSection) {
          visualizationSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
          console.log('📍 Scrolled to visualization section');
        }
      }, 1000);
      
      toast({
        title: "Sucesso!",
        description: `Rota ${routeType.toLowerCase()} otimizada com ${optimizeResponse.data.total_stops || 0} paradas.`,
        variant: "default",
      });
      
      // NOVO: Desativar loading
      setIsCalculatingRoute(false);
      
    } catch (error) {
      console.error('❌ ERRO NA OTIMIZAÇÃO:', error);
      console.error('Error details:', error.response?.data || error.message);
      console.error('Error code:', error.code);
      
      let errorMessage = "Erro ao otimizar rota. Verifique o console para detalhes.";
      
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        errorMessage = "Timeout na otimização da rota. O OSRM pode estar sobrecarregado. Tente novamente em alguns segundos.";
        console.error('🕒 TIMEOUT ERROR: OSRM optimization took too long');
      } else if (error.response?.status === 500) {
        errorMessage = "Erro interno no servidor durante a otimização. Verifique se todos os endereços são válidos.";
      }
      
      logAction('CALCULATE_ROUTE_ERROR', { 
        error: error.message, 
        routeType, 
        errorCode: error.code,
        isTimeout: error.code === 'ECONNABORTED'
      });
      
      toast({
        title: "Erro!",
        description: errorMessage,
        variant: "destructive",
      });
      
      // NOVO: Desativar loading em caso de erro
      setIsCalculatingRoute(false);
    }
  };

  const handleOptimizeFromPrioritization = async () => {
    await handleCalculateOptimizedRoute(routeType);
  };

  const handleRemoveFromPrioritization = (itemId) => {
    const itemToRemove = prioritizationItems.find(item => item.budget_item_id === itemId);
    
    // Remove from prioritization list
    setPrioritizationItems(prev => prev.filter(item => item.budget_item_id !== itemId));
    
    // Add back to available items
    if (itemToRemove) {
      setAvailableItems(prev => [...prev, itemToRemove]);
    }
  };

  const handleSaveRoute = async () => {
    if (!optimizedRoute) {
      toast({
        title: "Aviso",
        description: "Otimize uma rota antes de salvar.",
        variant: "default",
      });
      return;
    }

    try {
      console.log('💾 Salvando rota otimizada...');
      
      // Determine the alias to use: custom or default
      const finalAlias = routeAlias.trim() || generateRouteAlias(routeDate, routeTime, currentVehicleType, optimizedRoute.stops?.length || 0);
      
      // Create route data with alias
      const routeData = {
        vehicle_type: currentVehicleType,
        planned_date: routeDate,
        planned_start_time: routeTime,
        alias: finalAlias,
        stops: []
      };

      console.log('📤 Enviando dados para salvar rota:', routeData);
      const createResponse = await routesApi.create(routeData);
      console.log('✅ Rota criada:', createResponse.data);
      const routeId = createResponse.data.id;
      
      // Add stops from optimized route
      const stopsData = optimizedRoute.stops.map(stop => ({
        budget_item_id: stop.budget_item_id,
        priority: stop.priority || 'AUTOMATICA'
      }));
      
      console.log('📍 Adicionando paradas:', stopsData);
      await routesApi.addStops(routeId, stopsData);
      
      // Optimize the route
      console.log('⚡ Otimizando rota salva...');
      await routesApi.optimize(routeId, routeType);
      
      // Refresh saved routes list
      await loadSavedRoutes();
      
      // Clear form
      setOptimizedRoute(null);
      setStopPriorities({});
      setRouteAlias(''); // Clear alias field
      
      toast({
        title: "Sucesso!",
        description: `Rota "${finalAlias}" salva com sucesso!`,
        variant: "default",
      });

      console.log('✅ Rota salva e adicionada à lista');
      
    } catch (error) {
      console.error('Erro ao salvar rota:', error);
      toast({
        title: "Erro!",
        description: "Erro ao salvar rota. Tente novamente.",
        variant: "destructive",
      });
    }
  };

  const handleEditRoute = async (routeId) => {
    logAction('EDIT_ROUTE_START', { routeId });
    
    try {
      console.log('✏️ Loading route for editing:', routeId);
      
      // Get route details
      const routeDetails = await routesApi.get(routeId);
      const route = routeDetails.data;
      
      console.log('📋 Route details loaded:', route);
      logAction('ROUTE_DETAILS_LOADED_FOR_EDIT', { 
        routeId, 
        stopsCount: route.stops?.length || 0,
        vehicleType: route.vehicle_type,
        status: route.status
      });
      
      // Set the optimized route to display it
      setOptimizedRoute(route);
      setDebugInfo(`Editando rota ${routeId} - ${route.stops?.length || 0} paradas - ${route.total_distance || '0'} km - ${route.total_duration || '0'} min`);
      
      // Set form data for editing
      setRouteDate(route.planned_date);
      setRouteTime(route.planned_start_time);
      setCurrentVehicleType(route.vehicle_type);
      
      // Load route stops into prioritization for editing
      if (route.stops && route.stops.length > 0) {
        // Convert route stops back to prioritization items format
        const prioritizationItems = route.stops.map(stop => ({
          budget_item_id: stop.budget_item_id,
          budget_id: stop.budget_id,
          service_name: stop.service_name,
          service_value: stop.service_value,
          client_name: stop.client_name,
          address: stop.address,
          priority: stop.priority || 'AUTOMATICA',
          service_status: stop.service_status
        }));
        
        setPrioritizationItems(prioritizationItems);
        
        // Initialize priorities
        const priorities = {};
        route.stops.forEach(stop => {
          priorities[stop.budget_item_id] = stop.priority || 'AUTOMATICA';
        });
        setStopPriorities(priorities);
        
        console.log('📍 Route stops loaded into prioritization:', prioritizationItems);
        logAction('ROUTE_STOPS_LOADED_FOR_EDIT', { 
          routeId, 
          stopsCount: prioritizationItems.length,
          stops: prioritizationItems.map(s => ({ id: s.budget_item_id, client: s.client_name, priority: s.priority }))
        });
      }
      
      // Scroll to visualization section
      setTimeout(() => {
        const visualizationSection = document.getElementById('visualization-section');
        if (visualizationSection) {
          visualizationSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
          console.log('📍 Scrolled to visualization section for editing');
        }
        
        // Also scroll to prioritization section so user can see the items loaded
        setTimeout(() => {
          const prioritizationElements = document.querySelectorAll('h2');
          const prioritizationSection = Array.from(prioritizationElements).find(h2 => h2.textContent.includes('Priorização de Rota'));
          if (prioritizationSection) {
            prioritizationSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }, 1000);
      }, 500);
      
      toast({
        title: "Rota carregada para edição!",
        description: `Rota ${routeId} carregada com ${route.stops?.length || 0} paradas. Modifique as prioridades e clique em "Calcular Rota Otimizada" para atualizar.`,
        variant: "default",
      });
      
      logAction('EDIT_ROUTE_SUCCESS', { routeId });
      
    } catch (error) {
      console.error('❌ Error loading route for editing:', error);
      logAction('EDIT_ROUTE_ERROR', { routeId, error: error.message });
      toast({
        title: "Erro!",
        description: "Erro ao carregar rota para edição. Verifique o console para detalhes.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteRoute = async (routeId) => {
    try {
      console.log('Iniciando exclusão da rota:', routeId);
      
      // Confirm deletion with better UX
      const confirmed = window.confirm(
        `Tem certeza que deseja excluir a rota ${routeId}?\n\nEsta ação não pode ser desfeita.`
      );
      
      if (!confirmed) {
        console.log('Exclusão cancelada pelo usuário');
        return;
      }

      console.log('Chamando API para excluir rota...');
      await routesApi.delete(routeId);
      
      console.log('Rota excluída com sucesso, atualizando lista...');
      // Refresh saved routes list
      await loadSavedRoutes();
      
      toast({
        title: "Rota excluída!",
        description: `Rota ${routeId} foi excluída com sucesso.`,
        variant: "default",
      });
      
      console.log('Processo de exclusão concluído');
    } catch (error) {
      console.error('Erro ao excluir rota:', error);
      toast({
        title: "Erro!",
        description: `Erro ao excluir rota ${routeId}. Tente novamente.`,
        variant: "destructive",
      });
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'PRIMEIRA': return 'bg-red-100 text-red-800 border-red-200';
      case 'ULTIMA': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default: return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  const getPriorityLabel = (priority) => {
    switch (priority) {
      case 'PRIMEIRA': return 'Primeira';
      case 'ULTIMA': return 'Última';
      default: return 'Automática';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Loading Modal/Popup para cálculo de rota */}
      {isCalculatingRoute && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4 shadow-2xl">
            <div className="text-center">
              {/* Ícone animado */}
              <div className="relative mx-auto mb-6">
                <div className="w-16 h-16 border-4 border-purple-200 rounded-full animate-spin border-t-purple-600"></div>
                <RouteIcon className="w-8 h-8 text-purple-600 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
              </div>
              
              {/* Título */}
              <h3 className="text-xl font-bold text-gray-900 mb-4">
                Calculando Rota Otimizada
              </h3>
              
              {/* Descrição */}
              <p className="text-gray-600 mb-6">
                Estamos processando sua rota usando algoritmos avançados de otimização OSRM...
              </p>
              
              {/* Detalhes */}
              <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-700">Tipo de Rota:</span>
                  <span className="font-semibold text-purple-700">
                    {routeType === 'CURTA' ? 'Rota Curta' : 'Rota Eficiente'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm mt-2">
                  <span className="text-gray-700">Veículo:</span>
                  <span className="font-semibold text-purple-700">{currentVehicleType}</span>
                </div>
                <div className="flex items-center justify-between text-sm mt-2">
                  <span className="text-gray-700">Paradas:</span>
                  <span className="font-semibold text-purple-700">{prioritizationItems.length}</span>
                </div>
              </div>
              
              {/* Nota de tempo */}
              <p className="text-xs text-gray-500 mt-4">
                Isso pode levar alguns segundos...
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Rotas</h1>
        <p className="text-gray-600 mt-2">
          Gerencie e otimize as rotas de entrega e coleta
        </p>
      </div>

      {/* Section 1: Available Items */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center mb-6">
          <MapPin className="w-5 h-5 text-green-600 mr-2" />
          <h2 className="text-xl font-semibold text-gray-900">Serviços Disponíveis para Rota</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full table-auto">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-20 sm:w-auto">
                  <span className="hidden sm:inline">Selecionar Veículo</span>
                  <span className="sm:hidden">Veículo</span>
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden">
                  Selecionar
                </th>
                <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Descrição
                </th>
                <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cliente
                </th>
                <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden sm:table-cell">
                  Bairro
                </th>
                <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden sm:table-cell">
                  Valor
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {availableItems.map((item, index) => (
                <tr key={`available-${item.budget_item_id}-${index}`} className="hover:bg-gray-50">
                  <td className="px-2 py-4 whitespace-nowrap w-20 sm:w-auto">
                    <div className="flex flex-col sm:flex-row space-y-1 sm:space-y-0 sm:space-x-2">
                      <button
                        onClick={() => handleVehicleAssignment(item, 'CARRO')}
                        className="inline-flex items-center justify-center px-2 sm:px-3 py-1 text-xs bg-blue-100 text-blue-800 rounded-full hover:bg-blue-200 min-w-0"
                      >
                        <Truck className="w-3 h-3 sm:mr-1" />
                        <span className="hidden sm:inline ml-1">Carro</span>
                      </button>
                      <button
                        onClick={() => handleVehicleAssignment(item, 'MOTO')}
                        className="inline-flex items-center justify-center px-2 sm:px-3 py-1 text-xs bg-green-100 text-green-800 rounded-full hover:bg-green-200 min-w-0"
                      >
                        <Bike className="w-3 h-3 sm:mr-1" />
                        <span className="hidden sm:inline ml-1">Moto</span>
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap hidden">
                    <input
                      type="checkbox"
                      checked={selectedItems.has(item.budget_item_id)}
                      onChange={(e) => handleItemSelection(item, e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                  </td>
                  <td className="px-2 sm:px-4 py-4">
                    <div className="text-sm font-medium text-gray-900">{item.service_name}</div>
                    <div className="text-sm text-gray-500">{item.service_code}</div>
                    <div className="text-xs text-gray-500 sm:hidden mt-1">
                      {item.neighborhood} • R$ {item.service_value.toFixed(2)}
                    </div>
                  </td>
                  <td className="px-2 sm:px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item.client_name}
                  </td>
                  <td className="px-2 sm:px-4 py-4 whitespace-nowrap text-sm text-gray-900 hidden sm:table-cell">
                    {item.neighborhood}
                  </td>
                  <td className="px-2 sm:px-4 py-4 whitespace-nowrap text-sm text-gray-900 hidden sm:table-cell">
                    R$ {item.service_value.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {availableItems.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <RouteIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>Nenhum serviço disponível para rotas</p>
          </div>
        )}
      </div>

      {/* Section 2: Car Route */}
      <RouteSection
        title="Rota Carro"
        icon={<Truck className="w-5 h-5 text-blue-600 mr-2" />}
        items={carRouteItems}
        onRemoveItem={(itemId) => handleRemoveFromRoute(itemId, 'CARRO')}
        onOptimize={() => handleOptimizeRoute('CARRO')}
        vehicleColor="blue"
      />

      {/* Section 3: Moto Route */}
      <RouteSection
        title="Rota Moto"
        icon={<Bike className="w-5 h-5 text-green-600 mr-2" />}
        items={motoRouteItems}
        onRemoveItem={(itemId) => handleRemoveFromRoute(itemId, 'MOTO')}
        onOptimize={() => handleOptimizeRoute('MOTO')}
        vehicleColor="green"
      />

      {/* Section 4: Route Prioritization */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center mb-6">
          <div className="flex items-center">
            <RouteIcon className="w-5 h-5 text-purple-600 mr-2" />
            <h2 className="text-xl font-semibold text-gray-900">Priorização de Rota</h2>
          </div>
        </div>

        {prioritizationItems.length > 0 ? (
          <div>
            {/* Vehicle Type and Route Type Selectors */}
            <div className="mb-6 space-y-4">
              {/* Vehicle Type Indicator */}
              <div className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center">
                  {currentVehicleType === 'CARRO' ? (
                    <Truck className="w-4 h-4 text-blue-600 mr-2" />
                  ) : (
                    <Bike className="w-4 h-4 text-green-600 mr-2" />
                  )}
                  <span className="text-sm font-medium text-gray-700">
                    Tipo de Veículo: <span className="font-bold">{currentVehicleType}</span>
                  </span>
                </div>
              </div>

              {/* Route Type Selection */}
              <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
                <h4 className="text-sm font-medium text-purple-900 mb-3">Tipo de Rota:</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <button
                    onClick={() => setRouteType('CURTA')}
                    className={`flex items-center justify-center px-4 py-3 rounded-lg border-2 transition-colors ${
                      routeType === 'CURTA'
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-300 bg-white text-gray-700 hover:border-blue-300'
                    }`}
                  >
                    <RouteIcon className="w-4 h-4 mr-2" />
                    <div className="text-left">
                      <div className="font-medium">ROTA CURTA</div>
                      <div className="text-xs opacity-75">Menor distância possível</div>
                    </div>
                  </button>
                  
                  <button
                    onClick={() => setRouteType('EFICIENTE')}
                    className={`flex items-center justify-center px-4 py-3 rounded-lg border-2 transition-colors ${
                      routeType === 'EFICIENTE'
                        ? 'border-green-500 bg-green-50 text-green-700'
                        : 'border-gray-300 bg-white text-gray-700 hover:border-green-300'
                    }`}
                  >
                    <Clock className="w-4 h-4 mr-2" />
                    <div className="text-left">
                      <div className="font-medium">ROTA EFICIENTE</div>
                      <div className="text-xs opacity-75">Menor tempo, melhor trânsito</div>
                    </div>
                  </button>
                </div>
                
                {/* Route type description */}
                <div className="mt-3 text-xs text-gray-600">
                  {routeType === 'CURTA' ? (
                    "🎯 Calcula o trajeto com menor quilometragem total"
                  ) : (
                    "⚡ Considera trânsito, lado da rua e eficiência temporal"
                  )}
                </div>
              </div>
            </div>

            {/* Prioritization List */}
            <div className="space-y-3">
              {prioritizationItems.map((item, index) => (
                <div key={`priority-${item.budget_item_id}-${index}`} className="flex items-center p-4 bg-gray-50 rounded-lg border border-gray-200">
                  {/* Item Number */}
                  <div className="flex-shrink-0 w-8 h-8 bg-purple-600 text-white rounded-full flex items-center justify-center text-sm font-bold mr-4">
                    {index + 1}
                  </div>
                  
                  {/* Item Details */}
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">{item.client_name}</div>
                    <div className="text-sm text-gray-600">{item.service_name}</div>
                    <div className="text-xs text-gray-500">{item.neighborhood}</div>
                  </div>
                  
                  {/* Priority Control */}
                  <div className="mx-4">
                    <label className="block text-xs font-medium text-gray-500 mb-1">PRIORIDADE</label>
                    <select
                      value={item.priority}
                      onChange={(e) => handlePriorityChange(item.budget_item_id, e.target.value)}
                      className={`text-xs px-3 py-1 rounded-full border font-medium ${getPriorityColor(item.priority)}`}
                    >
                      <option value="PRIMEIRA">Primeira</option>
                      <option value="AUTOMATICA">Automática</option>
                      <option value="ULTIMA">Última</option>
                    </select>
                  </div>

                  {/* Value and Actions */}
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <div className="text-sm font-medium text-gray-900">R$ {item.service_value.toFixed(2)}</div>
                    </div>
                    <button
                      onClick={() => handleRemoveFromPrioritization(item.budget_item_id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Remover da lista"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Priority Legend */}
            <div className="mt-4 p-4 bg-purple-50 rounded-lg">
              <h4 className="text-sm font-medium text-purple-900 mb-2">Legenda das Prioridades:</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
                <div className="flex items-center">
                  <span className="inline-block w-3 h-3 bg-red-100 border border-red-200 rounded mr-2"></span>
                  <span><b>Primeira:</b> Mais próxima da empresa (prioritária)</span>
                </div>
                <div className="flex items-center">
                  <span className="inline-block w-3 h-3 bg-blue-100 border border-blue-200 rounded mr-2"></span>
                  <span><b>Automática:</b> Otimização pelo sistema</span>
                </div>
                <div className="flex items-center">
                  <span className="inline-block w-3 h-3 bg-yellow-100 border border-yellow-200 rounded mr-2"></span>
                  <span><b>Última:</b> Mais distante da empresa (final)</span>
                </div>
              </div>
            </div>

            {/* Calcular Rota Otimizada Button - Moved to bottom */}
            <div className="mt-6 flex justify-center">
              <button
                onClick={() => {
                  handleCalculateOptimizedRoute(routeType);
                }}
                className="flex items-center px-8 py-3 bg-purple-600 text-white hover:bg-purple-700 rounded-lg transition-colors shadow-lg"
              >
                <Play className="w-5 h-5 mr-3" />
                <span className="font-medium">Calcular Rota Otimizada</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <RouteIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>Use os botões "Otimizar Rota" das seções acima para enviar itens para priorização</p>
          </div>
        )}
      </div>

      {/* Section 5: Visualize and Save (Always Visible) */}
      <div id="visualization-section" className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center mb-6">
          <RouteIcon className="w-5 h-5 text-blue-600 mr-2" />
          <h2 className="text-xl font-semibold text-gray-900">Visualizar e Salvar</h2>
        </div>

        {/* Route Planning Controls */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Data da Rota
            </label>
            <input
              type="date"
              value={routeDate}
              onChange={(e) => setRouteDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Horário de Início
            </label>
            <input
              type="time"
              value={routeTime}
              onChange={(e) => setRouteTime(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div className="flex items-end">
            <div className="bg-white px-4 py-2 rounded-lg border border-gray-300">
              <div className="flex items-center">
                {currentVehicleType === 'CARRO' ? (
                  <Truck className="w-4 h-4 text-blue-600 mr-2" />
                ) : (
                  <Bike className="w-4 h-4 text-green-600 mr-2" />
                )}
                <span className="text-sm font-medium">
                  {currentVehicleType}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Debug Information */}
        {debugInfo && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="text-sm text-blue-800">
              <strong>🔧 Debug:</strong> {debugInfo}
            </div>
            <div className="text-xs text-blue-600 mt-1">
              optimizedRoute: {optimizedRoute ? `${optimizedRoute.stops?.length || 0} paradas - ${optimizedRoute.total_distance || '0'} km - ${optimizedRoute.total_duration || '0'} min` : 'null'}
            </div>
            <div className="text-xs text-blue-600 mt-1">
              Last updated: {new Date().toLocaleTimeString()}
            </div>
          </div>
        )}

        {/* Interactive Map - ALWAYS VISIBLE */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            {optimizedRoute ? 'Mapa da Rota Otimizada' : 'Mapa de Cuiabá - Aguardando Rota'}
          </h3>
          <div className="border border-gray-300 rounded-lg overflow-hidden">
            <div 
              ref={mapRef}
              style={{ height: '400px', width: '100%' }}
              className="bg-gray-100"
            />
          </div>
          <div className="mt-2 text-xs text-gray-500 flex items-center">
            <MapPin className="w-3 h-3 mr-1" />
            {optimizedRoute 
              ? 'Mapa com rota otimizada • 🏢 = Empresa • Números = Paradas'
              : 'Mapa aguardando dados da otimização de rota'
            }
          </div>
        </div>

        {optimizedRoute && optimizedRoute.stops && optimizedRoute.stops.length > 0 ? (
          <div>
            {/* Route Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <MapPin className="w-5 h-5 text-blue-600 mr-2" />
                  <div>
                    <div className="text-sm text-blue-600 font-medium">Total de Paradas</div>
                    <div className="text-2xl font-bold text-blue-900">{optimizedRoute.stops?.length || 0}</div>
                  </div>
                </div>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <Clock className="w-5 h-5 text-green-600 mr-2" />
                  <div>
                    <div className="text-sm text-green-600 font-medium">Duração Estimada</div>
                    <div className="text-2xl font-bold text-green-900">{Math.floor((optimizedRoute.total_duration || 0) / 60)}h {(optimizedRoute.total_duration || 0) % 60}min</div>
                  </div>
                </div>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <RouteIcon className="w-5 h-5 text-purple-600 mr-2" />
                  <div>
                    <div className="text-sm text-purple-600 font-medium">Distância Total</div>
                    <div className="text-2xl font-bold text-purple-900">{optimizedRoute.total_distance || 0} km</div>
                  </div>
                </div>
              </div>
            </div>

            {/* COMENTADO TEMPORARIAMENTE: Seção de mapa duplicada que estava causando problemas
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Mapa da Rota Otimizada</h3>
              <div className="border border-gray-300 rounded-lg overflow-hidden">
                <div 
                  ref={mapRef}
                  style={{ height: '400px', width: '100%' }}
                  className="bg-gray-100"
                />
              </div>
              <div className="mt-2 text-xs text-gray-500 flex items-center">
                <MapPin className="w-3 h-3 mr-1" />
                Mapa centralizado em Cuiabá • 🏢 = Empresa (início/fim) • Números = Paradas ordenadas
              </div>
            </div>
            */}

            {/* Route Details Summary */}
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-900 mb-3">Resumo da Rota Otimizada</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Início:</span>
                  <div className="font-medium">{routeTime}</div>
                </div>
                <div>
                  <span className="text-gray-500">Duração Total:</span>
                  <div className="font-medium">{Math.floor(optimizedRoute.total_duration / 60)}h {optimizedRoute.total_duration % 60}min</div>
                </div>
                <div>
                  <span className="text-gray-500">Distância:</span>
                  <div className="font-medium">{optimizedRoute.total_distance} km</div>
                </div>
                <div>
                  <span className="text-gray-500">Valor Total:</span>
                  <div className="font-medium text-green-600">
                    R$ {optimizedRoute.stops.reduce((total, stop) => total + stop.service_value, 0).toFixed(2)}
                  </div>
                </div>
              </div>
            </div>

            {/* Route Alias Input */}
            <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <h4 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
                <FileText className="w-4 h-4 mr-2 text-blue-600" />
                Nome da Rota (Opcional)
              </h4>
              <div className="space-y-2">
                <input
                  type="text"
                  value={routeAlias}
                  onChange={(e) => setRouteAlias(e.target.value)}
                  placeholder="Digite um nome personalizado para esta rota..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                />
                <p className="text-xs text-gray-500">
                  <strong>Padrão:</strong> {generateRouteAlias(routeDate, routeTime, currentVehicleType, optimizedRoute?.stops?.length || 0)}
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end space-x-4">
              <button
                onClick={() => {
                  console.log('🧹 Clearing route data...');
                  setOptimizedRoute(null);
                  setStopPriorities({});
                  setDebugInfo('');
                  setRouteAlias(''); // Clear alias field
                  
                  // Reinitialize empty map
                  if (mapInstanceRef.current) {
                    setTimeout(() => {
                      initializeEmptyMap();
                    }, 100);
                  }
                  
                  console.log('✅ Route data cleared');
                }}
                className="flex items-center px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                <Edit3 className="w-4 h-4 mr-2" />
                Limpar
              </button>
              <button
                onClick={handleSaveRoute}
                className="flex items-center px-6 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors"
              >
                <Save className="w-4 h-4 mr-2" />
                Salvar Rota
              </button>
            </div>
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <MapPin className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhuma Rota Otimizada</h3>
            <p>Use o botão "Calcular Rota Otimizada" na seção de priorização para gerar uma rota.</p>
            
            {/* Additional debug info when no route */}
            <div className="mt-4 text-xs text-gray-400">
              <p>Debug: optimizedRoute = {optimizedRoute ? 'exists' : 'null'}</p>
              {optimizedRoute && (
                <>
                  <p>- stops: {optimizedRoute.stops ? optimizedRoute.stops.length : 'no stops'}</p>
                  <p>- total_distance: {optimizedRoute.total_distance || 'undefined'}</p>
                  <p>- company_address: {optimizedRoute.company_address ? 'exists' : 'missing'}</p>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Section 6: Saved Routes */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center mb-6">
          <RouteIcon className="w-5 h-5 text-orange-600 mr-2" />
          <h2 className="text-xl font-semibold text-gray-900">Rotas Salvas</h2>
        </div>

        <div className="space-y-3">
          {savedRoutes.slice(0, 20).map((route, index) => (
            <div key={`saved-${route.id}-${index}`} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center">
                {route.vehicle_type === 'CARRO' ? (
                  <Truck className="w-5 h-5 text-blue-600 mr-3" />
                ) : (
                  <Bike className="w-5 h-5 text-green-600 mr-3" />
                )}
                <div>
                  <div className="text-sm font-medium text-gray-900">{generateRouteAlias(route.planned_date, route.planned_start_time)}</div>
                  <div className="text-xs text-gray-500 font-mono">{route.id}</div>
                  <div className="text-xs text-gray-500">
                    {new Date(route.planned_date).toLocaleDateString('pt-BR')} às {route.planned_start_time}
                  </div>
                  <div className="text-xs text-gray-500">
                    {route.stops.length} paradas • {Math.round(route.total_duration / 60)}h {route.total_duration % 60}min
                  </div>
                  <div className="text-xs text-blue-600 mt-1">
                    <strong>Bairros:</strong> {getRouteNeighborhoods(route.stops)}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    <strong>Última edição:</strong> {formatCuiabaTime(route.updated_at)}
                    {route.last_edited_by && (
                      <span className="ml-2">por <strong>{route.last_edited_by}</strong></span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button 
                  onClick={() => handleEditRoute(route.id)}
                  className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  title="Editar rota"
                >
                  <Edit3 className="w-4 h-4" />
                </button>
                <button 
                  onClick={() => handleDeleteRoute(route.id)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title={`Excluir rota ${route.id}`}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {savedRoutes.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <RouteIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>Nenhuma rota salva</p>
          </div>
        )}
      </div>
    </div>
  );
}

// Route Section Component
function RouteSection({ title, icon, items, onRemoveItem, onOptimize, vehicleColor }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          {icon}
          <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
        </div>
        {items.length > 0 && (
          <button
            onClick={onOptimize}
            className={`flex items-center px-4 py-2 text-white rounded-lg transition-colors ${
              vehicleColor === 'blue' 
                ? 'bg-blue-600 hover:bg-blue-700' 
                : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            <Play className="w-4 h-4 mr-2" />
            Otimizar Rota
          </button>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full table-auto">
          <thead>
            <tr className="bg-gray-50">
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Descrição
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Cliente
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Bairro
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Valor
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Ações
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {items.map((item, index) => (
              <tr key={`route-item-${item.budget_item_id}-${index}`} className="hover:bg-gray-50">
                <td className="px-4 py-4">
                  <div className="text-sm font-medium text-gray-900">{item.service_name}</div>
                  <div className="text-sm text-gray-500">{item.service_code}</div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                  {item.client_name}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                  {item.neighborhood}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                  R$ {item.service_value.toFixed(2)}
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <button
                    onClick={() => onRemoveItem(item.budget_item_id)}
                    className="text-red-600 hover:text-red-900"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {items.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <RouteIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
          <p>Nenhum item adicionado à {title.toLowerCase()}</p>
        </div>
      )}
    </div>
  );
}