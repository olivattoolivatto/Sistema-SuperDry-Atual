import React, { useState, useEffect } from 'react';
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
  ChevronDown
} from 'lucide-react';
import { toast } from '../hooks/use-toast';
import { routesApi } from '../services/api';

export function Routes() {
  const [availableItems, setAvailableItems] = useState([]);
  const [carRouteItems, setCarRouteItems] = useState([]);
  const [motoRouteItems, setMotoRouteItems] = useState([]);
  const [optimizedRoute, setOptimizedRoute] = useState(null);
  const [savedRoutes, setSavedRoutes] = useState([]);
  const [selectedItems, setSelectedItems] = useState(new Set());
  const [loading, setLoading] = useState(true);
  
  // Route optimization form
  const [routeDate, setRouteDate] = useState(new Date().toISOString().split('T')[0]);
  const [routeTime, setRouteTime] = useState('08:00');
  const [currentVehicleType, setCurrentVehicleType] = useState('CARRO');

  useEffect(() => {
    loadAvailableItems();
    loadSavedRoutes();
  }, []);

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
    if (vehicleType === 'CARRO') {
      setCarRouteItems(prev => [...prev, item]);
    } else {
      setMotoRouteItems(prev => [...prev, item]);
    }
    
    // Remove from available items
    setAvailableItems(prev => prev.filter(i => i.budget_item_id !== item.budget_item_id));
    
    // Remove from selection
    const newSelected = new Set(selectedItems);
    newSelected.delete(item.budget_item_id);
    setSelectedItems(newSelected);
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
    try {
      const items = vehicleType === 'CARRO' ? carRouteItems : motoRouteItems;
      
      if (items.length === 0) {
        toast({
          title: "Aviso",
          description: "Adicione itens à rota antes de otimizar.",
          variant: "default",
        });
        return;
      }

      // Create route
      const routeData = {
        vehicle_type: vehicleType,
        planned_date: routeDate,
        planned_start_time: routeTime,
        stops: []
      };

      const createResponse = await routesApi.createRoute(routeData);
      const routeId = createResponse.data.id;
      
      // Add stops with default priorities
      const stopsData = items.map(item => ({
        budget_item_id: item.budget_item_id,
        priority: 'AUTOMATICA'
      }));
      
      await routesApi.updateRouteStops(routeId, stopsData);
      
      // Optimize route
      const optimizeResponse = await routesApi.optimizeRoute(routeId);
      
      // Get optimized route details
      const routeDetails = await routesApi.getRoute(routeId);
      
      setOptimizedRoute(routeDetails.data);
      setCurrentVehicleType(vehicleType);
      
      // Clear the route items that were optimized
      if (vehicleType === 'CARRO') {
        setCarRouteItems([]);
      } else {
        setMotoRouteItems([]);
      }
      
      toast({
        title: "Sucesso!",
        description: `Rota ${vehicleType.toLowerCase()} otimizada com ${optimizeResponse.data.total_stops} paradas.`,
        variant: "default",
      });
      
    } catch (error) {
      console.error('Erro ao otimizar rota:', error);
      toast({
        title: "Erro!",
        description: "Erro ao otimizar rota. Tente novamente.",
        variant: "destructive",
      });
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

      {/* Section 4: Route Optimization */}
      {optimizedRoute && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center mb-6">
            <RouteIcon className="w-5 h-5 text-purple-600 mr-2" />
            <h2 className="text-xl font-semibold text-gray-900">Otimização de Rota</h2>
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
                  <div className="text-2xl font-bold text-green-900">{Math.round(optimizedRoute.total_duration / 60)}h {optimizedRoute.total_duration % 60}min</div>
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

          {/* Route Stops */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Paradas da Rota</h3>
            <div className="space-y-3">
              {optimizedRoute.stops.map((stop, index) => (
                <div key={stop.id} className="flex items-center p-4 bg-gray-50 rounded-lg">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                    {index + 1}
                  </div>
                  <div className="ml-4 flex-1">
                    <div className="text-sm font-medium text-gray-900">{stop.client_name}</div>
                    <div className="text-sm text-gray-500">{stop.service_name}</div>
                    <div className="text-xs text-gray-400">{stop.address.neighborhood}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium text-gray-900">R$ {stop.service_value.toFixed(2)}</div>
                    <div className="text-xs text-gray-500">{stop.estimated_duration} min</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end space-x-4">
            <button
              onClick={() => setOptimizedRoute(null)}
              className="flex items-center px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            >
              <Edit3 className="w-4 h-4 mr-2" />
              Editar
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
      )}

      {/* Section 5: Saved Routes */}
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
                <button className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg">
                  <Edit3 className="w-4 h-4" />
                </button>
                <button className="p-2 text-red-600 hover:bg-red-50 rounded-lg">
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
            className={`flex items-center px-4 py-2 bg-${vehicleColor}-600 text-white hover:bg-${vehicleColor}-700 rounded-lg transition-colors`}
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