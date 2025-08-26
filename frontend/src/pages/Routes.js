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
  
  // Route optimization form
  const [routeDate, setRouteDate] = useState(new Date().toISOString().split('T')[0]);
  const [routeTime, setRouteTime] = useState('08:00');
  const [currentVehicleType, setCurrentVehicleType] = useState('CARRO');
  const [routeType, setRouteType] = useState('CURTA'); // New: CURTA or EFICIENTE
  
  // Map state
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const [stopPriorities, setStopPriorities] = useState({});

  useEffect(() => {
    loadAvailableItems();
    loadSavedRoutes();
    
    console.log('🚀 Routes component mounted');
  }, []);

  useEffect(() => {
    console.log('🔍 State updated:');
    console.log('- carRouteItems:', carRouteItems.length);
    console.log('- motoRouteItems:', motoRouteItems.length);
    console.log('- availableItems:', availableItems.length);
  }, [carRouteItems, motoRouteItems, availableItems]);

  // Initialize map when optimized route is available
  useEffect(() => {
    if (optimizedRoute && mapRef.current && !mapInstanceRef.current) {
      initializeMap();
    } else if (optimizedRoute && mapInstanceRef.current) {
      updateMapWithRoute();
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
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
      const response = await routesApi.getRoutes();
      setSavedRoutes(response.data);
    } catch (error) {
      console.error('Erro ao carregar rotas salvas:', error);
    }
  };

  const initializeMap = () => {
    if (!optimizedRoute?.company_address) return;

    const companyLat = optimizedRoute.company_address.latitude;
    const companyLng = optimizedRoute.company_address.longitude;

    // Create map centered on company location (Cuiabá region)
    mapInstanceRef.current = L.map(mapRef.current).setView([companyLat, companyLng], 13);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(mapInstanceRef.current);

    updateMapWithRoute();
  };

  const updateMapWithRoute = () => {
    if (!mapInstanceRef.current || !optimizedRoute) return;

    // Clear existing layers
    mapInstanceRef.current.eachLayer((layer) => {
      if (layer instanceof L.Marker || layer instanceof L.Polyline) {
        mapInstanceRef.current.removeLayer(layer);
      }
    });

    const companyLat = optimizedRoute.company_address.latitude;
    const companyLng = optimizedRoute.company_address.longitude;

    // Add company marker (start/end point)
    const companyIcon = L.divIcon({
      html: `<div style="background-color: #10B981; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">🏢</div>`,
      className: 'custom-div-icon',
      iconSize: [30, 30],
      iconAnchor: [15, 15]
    });

    L.marker([companyLat, companyLng], { icon: companyIcon })
      .addTo(mapInstanceRef.current)
      .bindPopup(`<b>Empresa - Início/Fim da Rota</b><br>${optimizedRoute.company_address.full_address}`);

    // Add numbered markers for each stop
    optimizedRoute.stops.forEach((stop, index) => {
      const lat = stop.address.latitude;
      const lng = stop.address.longitude;
      
      if (lat && lng) {
        // Create numbered marker
        const markerIcon = L.divIcon({
          html: `<div style="background-color: #3B82F6; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">${index + 1}</div>`,
          className: 'custom-div-icon',
          iconSize: [30, 30],
          iconAnchor: [15, 15]
        });

        const marker = L.marker([lat, lng], { icon: markerIcon })
          .addTo(mapInstanceRef.current);

        // Create popup content with stop details
        const popupContent = `
          <div style="min-width: 200px;">
            <b>Parada ${index + 1}: ${stop.client_name}</b><br>
            <b>Serviço:</b> ${stop.service_name}<br>
            <b>Valor:</b> R$ ${stop.service_value.toFixed(2)}<br>
            <b>Duração:</b> ${stop.estimated_duration} minutos<br>
            <b>Prioridade:</b> ${stop.priority}<br>
            <b>Status:</b> ${stop.service_status}<br>
            <small>${stop.address.full_address}</small>
          </div>
        `;
        
        marker.bindPopup(popupContent);
      }
    });

    // Draw route if geometry is available
    if (optimizedRoute.route_geometry && optimizedRoute.route_geometry.coordinates) {
      const routeCoords = optimizedRoute.route_geometry.coordinates.map(coord => [coord[1], coord[0]]);
      
      L.polyline(routeCoords, {
        color: '#3B82F6',
        weight: 4,
        opacity: 0.8
      }).addTo(mapInstanceRef.current);
    }

    // Adjust map view to fit all markers
    if (optimizedRoute.stops.length > 0) {
      const group = new L.featureGroup();
      
      // Add company marker to group
      group.addLayer(L.marker([companyLat, companyLng]));
      
      // Add stop markers to group
      optimizedRoute.stops.forEach(stop => {
        if (stop.address.latitude && stop.address.longitude) {
          group.addLayer(L.marker([stop.address.latitude, stop.address.longitude]));
        }
      });

      mapInstanceRef.current.fitBounds(group.getBounds().pad(0.1));
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
    } else {
      console.log('🏍️ Adding to moto route items');
      setMotoRouteItems(prev => {
        const newItems = [...prev, item];
        console.log('🏍️ New moto route items:', newItems);
        return newItems;
      });
    }
    
    // Remove from available items
    console.log('➖ Removing from available items');
    setAvailableItems(prev => prev.filter(i => i.budget_item_id !== item.budget_item_id));
    
    // Remove from selection
    const newSelected = new Set(selectedItems);
    newSelected.delete(item.budget_item_id);
    setSelectedItems(newSelected);
    
    console.log('✅ Vehicle assignment completed');
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
    console.log('🚀 Moving items to prioritization for vehicleType:', vehicleType);
    
    const items = vehicleType === 'CARRO' ? carRouteItems : motoRouteItems;
    
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

    console.log('✅ Items moved to prioritization successfully');
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

  const handleOptimizeFromPrioritization = async () => {
    if (prioritizationItems.length === 0) {
      toast({
        title: "Aviso",
        description: "Adicione itens à lista de priorização antes de otimizar.",
        variant: "default",
      });
      return;
    }

    try {
      console.log('🔨 Creating route from prioritization...');
      console.log('🎯 Route type selected:', routeType);
      console.log('📦 Items to optimize:', prioritizationItems);
      
      // Create route
      const routeData = {
        vehicle_type: currentVehicleType,
        planned_date: routeDate,
        planned_start_time: routeTime,
        stops: []
      };

      const createResponse = await routesApi.createRoute(routeData);
      console.log('✅ Route created:', createResponse.data.id);
      const routeId = createResponse.data.id;
      
      // Add stops with priorities from prioritization list
      const stopsData = prioritizationItems.map(item => ({
        budget_item_id: item.budget_item_id,
        priority: item.priority,
        route_type: routeType // Add route type info
      }));
      
      console.log('📍 Adding stops with priorities and route type:', stopsData);
      await routesApi.updateRouteStops(routeId, stopsData);
      
      // Optimize route based on selected type
      console.log(`⚡ Optimizing ${routeType} route...`);
      const optimizeResponse = await routesApi.optimizeRoute(routeId, { route_type: routeType });
      console.log('⚡ Optimization response:', optimizeResponse.data);
      
      // Get optimized route details
      console.log('📋 Getting route details...');
      const routeDetails = await routesApi.getRoute(routeId);
      console.log('📋 Route details:', routeDetails.data);
      
      // Ensure we have valid route data before setting
      if (routeDetails.data && routeDetails.data.stops && routeDetails.data.stops.length > 0) {
        setOptimizedRoute(routeDetails.data);
        
        // Initialize stop priorities state
        const priorities = {};
        routeDetails.data.stops.forEach(stop => {
          priorities[stop.id] = stop.priority;
        });
        setStopPriorities(priorities);

        // Clear prioritization items after successful optimization
        setPrioritizationItems([]);
        
        console.log('🎉 Route optimization completed successfully!');
        
        toast({
          title: "Sucesso!",
          description: `Rota ${routeType.toLowerCase()} otimizada com ${optimizeResponse.data.total_stops} paradas.`,
          variant: "default",
        });

        // Force map update after setting route
        setTimeout(() => {
          if (mapInstanceRef.current) {
            mapInstanceRef.current.invalidateSize();
          }
        }, 100);
        
      } else {
        console.error('❌ Invalid route data received');
        toast({
          title: "Erro!",
          description: "Dados da rota inválidos. Tente novamente.",
          variant: "destructive",
        });
      }
      
    } catch (error) {
      console.error('Erro ao otimizar rota:', error);
      toast({
        title: "Erro!",
        description: "Erro ao otimizar rota. Tente novamente.",
        variant: "destructive",
      });
    }
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
      await loadSavedRoutes(); // Refresh saved routes
      setOptimizedRoute(null); // Clear current optimization
      setStopPriorities({});
      
      toast({
        title: "Sucesso!",
        description: "Rota salva com sucesso!",
        variant: "default",
      });
    } catch (error) {
      console.error('Erro ao salvar rota:', error);
      toast({
        title: "Erro!",
        description: "Erro ao salvar rota. Tente novamente.",
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
      await routesApi.deleteRoute(routeId);
      
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
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Selecionar
                </th>
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
                  Veículo
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {availableItems.map((item) => (
                <tr key={item.budget_item_id} className="hover:bg-gray-50">
                  <td className="px-4 py-4 whitespace-nowrap">
                    <input
                      type="checkbox"
                      checked={selectedItems.has(item.budget_item_id)}
                      onChange={(e) => handleItemSelection(item, e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                  </td>
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
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleVehicleAssignment(item, 'CARRO')}
                        className="inline-flex items-center px-3 py-1 text-xs bg-blue-100 text-blue-800 rounded-full hover:bg-blue-200"
                      >
                        <Truck className="w-3 h-3 mr-1" />
                        Carro
                      </button>
                      <button
                        onClick={() => handleVehicleAssignment(item, 'MOTO')}
                        className="inline-flex items-center px-3 py-1 text-xs bg-green-100 text-green-800 rounded-full hover:bg-green-200"
                      >
                        <Bike className="w-3 h-3 mr-1" />
                        Moto
                      </button>
                    </div>
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
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <RouteIcon className="w-5 h-5 text-purple-600 mr-2" />
            <h2 className="text-xl font-semibold text-gray-900">Priorização de Rota</h2>
          </div>
          {prioritizationItems.length > 0 && (
            <button
              onClick={handleOptimizeFromPrioritization}
              className="flex items-center px-6 py-2 bg-purple-600 text-white hover:bg-purple-700 rounded-lg transition-colors"
            >
              <Play className="w-4 h-4 mr-2" />
              Calcular Rota Otimizada
            </button>
          )}
        </div>

        {prioritizationItems.length > 0 ? (
          <div>
            {/* Vehicle Type Indicator */}
            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
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

            {/* Prioritization List */}
            <div className="space-y-3">
              {prioritizationItems.map((item, index) => (
                <div key={item.budget_item_id} className="flex items-center p-4 bg-gray-50 rounded-lg border border-gray-200">
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
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <RouteIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>Use os botões "Otimizar Rota" das seções acima para enviar itens para priorização</p>
          </div>
        )}
      </div>

      {/* Section 5: Visualize and Save (Always Visible) */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
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

        {optimizedRoute ? (
          <div>
            {/* Route Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <MapPin className="w-5 h-5 text-blue-600 mr-2" />
                  <div>
                    <div className="text-sm text-blue-600 font-medium">Total de Paradas</div>
                    <div className="text-2xl font-bold text-blue-900">{optimizedRoute.stops.length}</div>
                  </div>
                </div>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <Clock className="w-5 h-5 text-green-600 mr-2" />
                  <div>
                    <div className="text-sm text-green-600 font-medium">Duração Estimada</div>
                    <div className="text-2xl font-bold text-green-900">{Math.floor(optimizedRoute.total_duration / 60)}h {optimizedRoute.total_duration % 60}min</div>
                  </div>
                </div>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <RouteIcon className="w-5 h-5 text-purple-600 mr-2" />
                  <div>
                    <div className="text-sm text-purple-600 font-medium">Distância Total</div>
                    <div className="text-2xl font-bold text-purple-900">{optimizedRoute.total_distance} km</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Interactive Map */}
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

            {/* Action Buttons */}
            <div className="flex justify-end space-x-4">
              <button
                onClick={() => {
                  setOptimizedRoute(null);
                  setStopPriorities({});
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
          {savedRoutes.slice(0, 20).map((route) => (
            <div key={route.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center">
                {route.vehicle_type === 'CARRO' ? (
                  <Truck className="w-5 h-5 text-blue-600 mr-3" />
                ) : (
                  <Bike className="w-5 h-5 text-green-600 mr-3" />
                )}
                <div>
                  <div className="text-sm font-medium text-gray-900">{route.id}</div>
                  <div className="text-xs text-gray-500">
                    {new Date(route.planned_date).toLocaleDateString('pt-BR')} às {route.planned_start_time}
                  </div>
                  <div className="text-xs text-gray-500">
                    {route.stops.length} paradas • {Math.round(route.total_duration / 60)}h {route.total_duration % 60}min
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button 
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
            {items.map((item) => (
              <tr key={item.budget_item_id} className="hover:bg-gray-50">
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