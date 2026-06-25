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
  RotateCcw,
  FileText,
  Check,
  Navigation,
  Search,
  ArrowUpDown
} from 'lucide-react';
import { toast } from '../hooks/use-toast';
import { routesApi, budgetItemsApi } from '../services/api';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix default marker icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

export function RoutesGeoapify() {
  const [availableItems, setAvailableItems]         = useState([]);
  const [carRouteItems, setCarRouteItems]           = useState([]);
  const [motoRouteItems, setMotoRouteItems]         = useState([]);
  const [prioritizationItems, setPrioritizationItems] = useState([]);
  const [optimizedRoute, setOptimizedRoute]         = useState(null);
  const [savedRoutes, setSavedRoutes]               = useState([]);
  const [selectedItems, setSelectedItems]           = useState(new Set());
  const [loading, setLoading]                       = useState(true);
  const [showStatus, setShowStatus]                 = useState(false);
  const [statusOptions, setStatusOptions]           = useState([]);
  const [editingStatus, setEditingStatus]           = useState({});
  const [isCalculatingRoute, setIsCalculatingRoute] = useState(false);
  const [currentVehicleType, setCurrentVehicleType] = useState('CARRO');
  const [considerTraffic, setConsiderTraffic]       = useState(false);
  const [routeAlias, setRouteAlias]                 = useState('');
  const [stopPriorities, setStopPriorities]         = useState({});

  // ── Rotas Salvas: filtro/ordenação ──────────────────────────────────────────
  const [savedSearchText, setSavedSearchText]       = useState('');
  const [savedVehicleFilter, setSavedVehicleFilter] = useState('TODOS'); // TODOS | CARRO | MOTO
  const [savedSortOrder, setSavedSortOrder]         = useState('recente'); // 'recente' | 'antiga'

  const { suggestedDate, suggestedTime } = getSuggestedDateTime();
  const [routeDate, setRouteDate] = useState(suggestedDate);
  const [routeTime, setRouteTime] = useState(suggestedTime);

  // ── map ────────────────────────────────────────────────────────────────────
  const mapRef         = useRef(null);
  const mapInstanceRef = useRef(null);

  // Init empty map on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      if (mapRef.current && !mapInstanceRef.current) initEmptyMap();
    }, 800);
    return () => clearTimeout(timer);
  }, []);

  // Update map when route changes
  useEffect(() => {
    if (optimizedRoute && mapInstanceRef.current) {
      updateMap();
    } else if (!optimizedRoute && mapInstanceRef.current) {
      // Clear markers/lines when route is cleared
      mapInstanceRef.current.eachLayer(layer => {
        if (layer instanceof L.Marker || layer instanceof L.Polyline) mapInstanceRef.current.removeLayer(layer);
      });
      mapInstanceRef.current.setView([-15.601481, -56.097389], 11);
    }
  }, [optimizedRoute]);

  const initEmptyMap = () => {
    if (!mapRef.current || mapInstanceRef.current) return;
    try {
      mapInstanceRef.current = L.map(mapRef.current).setView([-15.601481, -56.097389], 11);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
      }).addTo(mapInstanceRef.current);
      setTimeout(() => mapInstanceRef.current?.invalidateSize(), 200);
    } catch (e) { console.error('Map init error:', e); }
  };

  const updateMap = () => {
    const map = mapInstanceRef.current;
    if (!map || !optimizedRoute?.stops?.length) return;

    // Clear markers and polylines
    map.eachLayer(layer => {
      if (layer instanceof L.Marker || layer instanceof L.Polyline) map.removeLayer(layer);
    });

    const companyLat = optimizedRoute.company_address?.latitude  || -15.6014;
    const companyLng = optimizedRoute.company_address?.longitude || -56.0974;

    // Company marker
    const companyIcon = L.divIcon({
      className: '',
      html: `<div style="background:linear-gradient(135deg,#10B981,#059669);color:white;width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;border:3px solid white;box-shadow:0 3px 8px rgba(0,0,0,.4)">🏢</div>`,
      iconSize: [44, 44], iconAnchor: [22, 22]
    });
    L.marker([companyLat, companyLng], { icon: companyIcon })
      .addTo(map)
      .bindPopup('<b>Empresa — Início / Fim</b>');

    const markers = [];
    const sortedStops = [...optimizedRoute.stops].sort((a, b) => (a.order_sequence || 0) - (b.order_sequence || 0));

    sortedStops.forEach((stop, i) => {
      const lat = stop.address?.latitude;
      const lng = stop.address?.longitude;
      if (!lat || !lng) return;

      const seq = stop.order_sequence || (i + 1);
      const icon = L.divIcon({
        className: '',
        html: `<div style="background:linear-gradient(135deg,#2563EB,#1D4ED8);color:white;border-radius:20px;padding:5px 10px;display:flex;align-items:center;gap:6px;font-size:11px;font-weight:bold;border:2px solid white;box-shadow:0 3px 6px rgba(0,0,0,.3);white-space:nowrap"><span style="background:white;color:#2563EB;border-radius:50%;width:18px;height:18px;display:inline-flex;align-items:center;justify-content:center;font-size:10px;font-weight:bold">${seq}</span>${stop.client_name.split(' ')[0]}</div>`,
        iconSize: [90, 30], iconAnchor: [45, 15]
      });

      const marker = L.marker([lat, lng], { icon }).addTo(map);
      marker.bindPopup(`<b>${seq}ª parada — ${stop.client_name}</b><br>${stop.service_name}<br>R$ ${stop.service_value.toFixed(2)}<br>${stop.address?.neighborhood || ''}`);
      markers.push(marker);
    });

    // Traçado REAL por ruas (Geoapify route_geometry, GeoJSON [lng,lat] → Leaflet [lat,lng])
    const geom = optimizedRoute.route_geometry;
    let drewRealRoute = false;
    if (geom && Array.isArray(geom.coordinates)) {
      const segments = geom.type === 'MultiLineString' ? geom.coordinates : [geom.coordinates];
      segments.forEach(seg => {
        const latlngs = seg.map(([lng, lat]) => [lat, lng]);
        if (latlngs.length > 1) {
          L.polyline(latlngs, { color: '#2563EB', weight: 5, opacity: 0.8 }).addTo(map);
          drewRealRoute = true;
        }
      });
    }
    // Fallback (só se não houver geometria real): linha reta tracejada
    if (!drewRealRoute) {
      const lineCoords = [
        [companyLat, companyLng],
        ...sortedStops.filter(s => s.address?.latitude && s.address?.longitude)
          .map(s => [s.address.latitude, s.address.longitude]),
        [companyLat, companyLng]
      ];
      L.polyline(lineCoords, { color: '#94A3B8', weight: 3, opacity: 0.6, dashArray: '8,5' }).addTo(map);
    }

    // Fit bounds
    if (markers.length > 0) {
      const all = [L.marker([companyLat, companyLng]), ...markers];
      map.fitBounds(L.featureGroup(all).getBounds().pad(0.15));
    }

    setTimeout(() => map.invalidateSize(), 100);
  };

  // ── helpers ────────────────────────────────────────────────────────────────

  function getSuggestedDateTime() {
    const now  = new Date();
    const hour = now.getHours();
    if (hour < 13) return { suggestedDate: now.toISOString().split('T')[0], suggestedTime: '13:00' };
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    return { suggestedDate: tomorrow.toISOString().split('T')[0], suggestedTime: '08:00' };
  }

  const formatCuiabaTime = (utcStr) => {
    try {
      return new Date(utcStr).toLocaleString('pt-BR', { timeZone: 'America/Cuiaba' });
    } catch { return new Date(utcStr).toLocaleString('pt-BR'); }
  };

  const generateRouteAlias = (date, time, vehicleType = 'CARRO') => {
    try {
      const d   = typeof date === 'string' && date.includes('-') ? new Date(date) : new Date(date);
      if (isNaN(d.getTime())) return `Rota ${date}`;
      const hour   = parseInt((time || '08:00').split(':')[0]);
      const period = hour >= 13 ? 'TARDE' : 'MANHÃ';
      const days   = ['domingo','segunda','terça','quarta','quinta','sexta','sábado'];
      const dayName = days[d.getDay()];
      const formatted = d.toLocaleDateString('pt-BR', { day:'2-digit', month:'2-digit', year:'2-digit' });
      return `Rota ${period} da ${dayName} ${formatted} [Geoapify]`;
    } catch { return `Rota ${date}`; }
  };

  const getRouteNeighborhoods = (stops) => {
    if (!stops || stops.length === 0) return '';
    const hoods = stops
      .map(s => {
        let n = s.address?.neighborhood || s.neighborhood || '';
        const c = s.address?.city || s.city || '';
        if (c.toLowerCase().includes('várzea grande') || c.toLowerCase().includes('varzea grande'))
          n = n ? `${n} (VG)` : 'Várzea Grande (VG)';
        return n;
      })
      .filter((n, i, a) => n && a.indexOf(n) === i);
    return hoods.length ? hoods.join(', ') : 'Bairros não informados';
  };

  // Combina data + hora planejadas da rota num timestamp comparável; cai para updated_at se faltar algo
  const getRouteTimestamp = (route) => {
    if (route.planned_date) {
      const t = `${route.planned_date}T${route.planned_start_time || '00:00'}:00`;
      const ts = new Date(t).getTime();
      if (!isNaN(ts)) return ts;
    }
    const ts2 = new Date(route.updated_at || route.created_at || 0).getTime();
    return isNaN(ts2) ? 0 : ts2;
  };

  // Aplica filtro de texto (alias/id/bairros), filtro de veículo e ordenação por data sobre as rotas salvas
  const getFilteredSortedRoutes = () => {
    const text = savedSearchText.trim().toLowerCase();
    let list = savedRoutes.filter((route) => {
      if (savedVehicleFilter !== 'TODOS' && route.vehicle_type !== savedVehicleFilter) return false;
      if (!text) return true;
      const alias = (route.alias || generateRouteAlias(route.planned_date, route.planned_start_time, route.vehicle_type) || '').toLowerCase();
      const hoods = getRouteNeighborhoods(route.stops).toLowerCase();
      const id = (route.id || '').toLowerCase();
      const editor = (route.last_edited_by || '').toLowerCase();
      return alias.includes(text) || hoods.includes(text) || id.includes(text) || editor.includes(text);
    });
    list = [...list].sort((a, b) => {
      const diff = getRouteTimestamp(b) - getRouteTimestamp(a); // mais recente primeiro
      return savedSortOrder === 'recente' ? diff : -diff;
    });
    return list;
  };

  const getPriorityColor = (p) => {
    if (p === 'PRIMEIRA') return 'bg-red-100 text-red-800 border-red-200';
    if (p === 'ULTIMA')   return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    return 'bg-blue-100 text-blue-800 border-blue-200';
  };

  // ── data loading ───────────────────────────────────────────────────────────

  useEffect(() => {
    loadAvailableItems();
    loadSavedRoutes();
  }, []);

  const loadAvailableItems = async () => {
    try {
      const res   = await routesApi.getAvailableItems();
      const items = Array.isArray(res.data) ? res.data : res.data.available_items || [];
      setAvailableItems(items);
    } catch (err) {
      console.error(err);
      toast({ title: 'Erro', description: 'Erro ao carregar itens disponíveis.', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const loadSavedRoutes = async () => {
    try {
      const res = await routesApi.getSavedRoutes();
      setSavedRoutes(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const loadStatusOptions = async () => {
    try {
      const res = await budgetItemsApi.getStatusOptions();
      setStatusOptions(res.data.status_options);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (showStatus && statusOptions.length === 0) loadStatusOptions();
  }, [showStatus]);

  // ── status change ──────────────────────────────────────────────────────────

  const handleStatusChange = (itemId, val) =>
    setEditingStatus(prev => ({ ...prev, [itemId]: val }));

  const applyStatusChange = async (item) => {
    const newStatus = editingStatus[item.budget_item_id];
    if (!newStatus || newStatus === item.status) return;
    try {
      await budgetItemsApi.updateStatus(item.budget_item_id, newStatus);
      const valid = ['EXECUTAR_NO_LOCAL','RETIRAR','ENTREGAR'];
      setAvailableItems(prev =>
        prev.map(i => i.budget_item_id === item.budget_item_id ? { ...i, status: newStatus } : i)
            .filter(i => valid.includes(i.status))
      );
      setEditingStatus(prev => { const u = { ...prev }; delete u[item.budget_item_id]; return u; });
      toast({ title: 'Sucesso', description: `Status atualizado para ${newStatus}` });
    } catch (err) {
      toast({ title: 'Erro', description: 'Erro ao atualizar status.', variant: 'destructive' });
    }
  };

  // ── item / vehicle assignment ──────────────────────────────────────────────

  const handleVehicleAssignment = (item, vehicleType) => {
    // Validar endereço antes de adicionar à rota
    const addr = item.address;
    if (!addr || !addr.latitude || !addr.longitude || !addr.full_address) {
      toast({
        title: 'Endereço incompleto!',
        description: `${item.client_name} não possui endereço com coordenadas cadastrado. Complete o cadastro do cliente antes de incluí-lo em uma rota.`,
        variant: 'destructive',
      });
      return;
    }

    if (vehicleType === 'CARRO')
      setCarRouteItems(prev => [...prev, item]);
    else
      setMotoRouteItems(prev => [...prev, item]);
    setAvailableItems(prev => prev.filter(i => i.budget_item_id !== item.budget_item_id));
    const s = new Set(selectedItems);
    s.delete(item.budget_item_id);
    setSelectedItems(s);
  };

  const handleRemoveFromRoute = (itemId, fromRoute) => {
    let itemToRestore;
    if (fromRoute === 'CARRO') {
      itemToRestore = carRouteItems.find(i => i.budget_item_id === itemId);
      setCarRouteItems(prev => prev.filter(i => i.budget_item_id !== itemId));
    } else {
      itemToRestore = motoRouteItems.find(i => i.budget_item_id === itemId);
      setMotoRouteItems(prev => prev.filter(i => i.budget_item_id !== itemId));
    }
    if (itemToRestore) setAvailableItems(prev => [...prev, itemToRestore]);
  };

  const handleOptimizeRoute = (vehicleType) => {
    const items = vehicleType === 'CARRO' ? carRouteItems : motoRouteItems;
    if (items.length === 0) {
      toast({ title: 'Aviso', description: 'Adicione itens à rota antes de continuar.' });
      return;
    }
    const withPriority = items.map(i => ({ ...i, priority: 'AUTOMATICA', vehicleType }));
    setPrioritizationItems(prev => [...prev, ...withPriority]);
    setCurrentVehicleType(vehicleType);
    if (vehicleType === 'CARRO') setCarRouteItems([]);
    else setMotoRouteItems([]);
    toast({ title: 'Itens enviados!', description: `${items.length} itens enviados para priorização.` });
  };

  // ── prioritization ─────────────────────────────────────────────────────────

  const handlePriorityChange = (itemId, val) =>
    setPrioritizationItems(prev =>
      prev.map(i => i.budget_item_id === itemId ? { ...i, priority: val } : i)
    );

  const handleRemoveFromPrioritization = (itemId) => {
    const item = prioritizationItems.find(i => i.budget_item_id === itemId);
    setPrioritizationItems(prev => prev.filter(i => i.budget_item_id !== itemId));
    if (item) setAvailableItems(prev => [...prev, item]);
  };

  // ── GEOAPIFY route calculation ─────────────────────────────────────────────

  const handleCalculateOptimizedRoute = async () => {
    if (prioritizationItems.length === 0) {
      toast({ title: 'Aviso', description: 'Adicione itens à priorização antes de calcular.' });
      return;
    }

    const noAddress = prioritizationItems.filter(
      i => !i.address?.latitude || !i.address?.longitude || !i.address?.full_address
    );
    if (noAddress.length > 0) {
      toast({
        title: 'Endereços Incompletos!',
        description: `Clientes sem endereço completo: ${noAddress.map(i => i.client_name).join(', ')}`,
        variant: 'destructive'
      });
      return;
    }

    const badNeighborhood = prioritizationItems.filter(
      i => (i.address?.neighborhood || '').toUpperCase() === 'BAIRRO A COMPLETAR'
    );
    if (badNeighborhood.length > 0) {
      toast({
        title: 'Cadastros Incompletos!',
        description: `Complete o bairro de: ${badNeighborhood.map(i => i.client_name).join(', ')}`,
        variant: 'destructive'
      });
      return;
    }

    setIsCalculatingRoute(true);

    try {
      // Step 1 – create route
      const createRes = await routesApi.create({
        vehicle_type: currentVehicleType,
        planned_date: routeDate,
        planned_start_time: routeTime,
        stops: []
      });
      const routeId = createRes.data.id;

      // Step 2 – add stops
      const stopsData = prioritizationItems.map(i => ({
        budget_item_id: i.budget_item_id,
        priority: i.priority || 'AUTOMATICA'
      }));
      await routesApi.addStops(routeId, stopsData);

      // Step 3 – optimize with Geoapify (com ou sem tráfego médio)
      await routesApi.optimizeGeoapify(routeId, considerTraffic);

      // Step 4 – fetch optimized route details
      const details = await routesApi.get(routeId);
      setOptimizedRoute(details.data);

      const priorities = {};
      (details.data.stops || []).forEach(s => { priorities[s.id] = s.priority; });
      setStopPriorities(priorities);
      setPrioritizationItems([]);

      toast({
        title: 'Sucesso!',
        description: `Rota otimizada com ${details.data.stops?.length || 0} paradas via Geoapify.`
      });

      setTimeout(() => {
        document.getElementById('geo-visualization')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 500);

    } catch (err) {
      console.error('Geoapify route error:', err);
      const msg = err.response?.data?.detail || err.message || 'Erro ao calcular rota.';
      toast({ title: 'Erro!', description: msg, variant: 'destructive' });
    } finally {
      setIsCalculatingRoute(false);
    }
  };

  // ── save route ─────────────────────────────────────────────────────────────

  const handleSaveRoute = async () => {
    if (!optimizedRoute) {
      toast({ title: 'Aviso', description: 'Calcule uma rota antes de salvar.' });
      return;
    }
    try {
      const alias = routeAlias.trim() ||
        generateRouteAlias(routeDate, routeTime, currentVehicleType);
      await routesApi.update(optimizedRoute.id, { alias });
      await loadSavedRoutes();
      setOptimizedRoute(null);
      setStopPriorities({});
      setRouteAlias('');
      toast({ title: 'Sucesso!', description: `Rota "${alias}" salva!` });
    } catch (err) {
      toast({ title: 'Erro!', description: 'Erro ao salvar rota.', variant: 'destructive' });
    }
  };

  // ── edit / delete saved route ──────────────────────────────────────────────

  const handleEditRoute = async (routeId) => {
    try {
      const res   = await routesApi.get(routeId);
      const route = res.data;
      setOptimizedRoute(route);
      setRouteDate(route.planned_date);
      setRouteTime(route.planned_start_time);
      setCurrentVehicleType(route.vehicle_type);
      setRouteAlias(route.alias || '');
      if (route.stops?.length > 0) {
        const items = route.stops.map(s => ({
          budget_item_id: s.budget_item_id,
          budget_id: s.budget_id,
          service_name: s.service_name,
          service_value: s.service_value,
          client_name: s.client_name,
          address: s.address,
          priority: s.priority || 'AUTOMATICA',
          service_status: s.service_status
        }));
        setPrioritizationItems(items);
        const prio = {};
        route.stops.forEach(s => { prio[s.budget_item_id] = s.priority || 'AUTOMATICA'; });
        setStopPriorities(prio);
      }
      toast({ title: 'Rota carregada!', description: `Rota ${routeId} com ${route.stops?.length || 0} paradas.` });
    } catch (err) {
      toast({ title: 'Erro!', description: 'Erro ao carregar rota.', variant: 'destructive' });
    }
  };

  const handleDeleteRoute = async (routeId) => {
    if (!window.confirm(`Excluir a rota ${routeId}? Esta ação não pode ser desfeita.`)) return;
    try {
      await routesApi.delete(routeId);
      await loadSavedRoutes();
      toast({ title: 'Rota excluída!', description: `Rota ${routeId} excluída.` });
    } catch (err) {
      toast({ title: 'Erro!', description: `Erro ao excluir rota ${routeId}.`, variant: 'destructive' });
    }
  };

  // ── render ─────────────────────────────────────────────────────────────────

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
    </div>
  );

  return (
    <div className="space-y-6">

      {/* Loading overlay */}
      {isCalculatingRoute && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4 shadow-2xl text-center">
            <div className="relative mx-auto mb-6 w-16 h-16">
              <div className="w-16 h-16 border-4 border-blue-200 rounded-full animate-spin border-t-blue-600" />
              <Navigation className="w-8 h-8 text-blue-600 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Calculando Rota Geoapify</h3>
            <p className="text-gray-600 mb-4">Otimizando seus pontos de entrega/coleta...</p>
            <div className="bg-blue-50 p-3 rounded-lg border border-blue-200 text-sm">
              <div className="flex justify-between"><span>Veículo:</span><span className="font-semibold text-blue-700">{currentVehicleType}</span></div>
              <div className="flex justify-between mt-1"><span>Paradas:</span><span className="font-semibold text-blue-700">{prioritizationItems.length}</span></div>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center">
            <Navigation className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Rotas Geoapify</h1>
            <p className="text-gray-500 text-sm mt-0.5">Otimização de rotas via API Geoapify</p>
          </div>
        </div>
      </div>

      {/* Section 1: Available Items */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <MapPin className="w-5 h-5 text-green-600 mr-2" />
            <h2 className="text-xl font-semibold text-gray-900">Serviços Disponíveis para Rota</h2>
          </div>
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showStatus}
              onChange={e => setShowStatus(e.target.checked)}
              className="h-4 w-4 text-blue-600 border-gray-300 rounded"
            />
            <span className="text-sm text-gray-700">Ver Status</span>
          </label>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full table-auto">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase">Veículo</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Descrição</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cliente</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden sm:table-cell">Bairro</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden sm:table-cell">Valor</th>
                {showStatus && <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {availableItems.map((item, idx) => (
                <tr key={`avail-${item.budget_item_id}-${idx}`} className="hover:bg-gray-50">
                  <td className="px-2 py-4">
                    <div className="flex flex-col sm:flex-row gap-1">
                      <button
                        data-testid={`assign-car-${item.budget_item_id}`}
                        onClick={() => handleVehicleAssignment(item, 'CARRO')}
                        className="inline-flex items-center px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full hover:bg-blue-200"
                      >
                        <Truck className="w-3 h-3 mr-1" /> Carro
                      </button>
                      <button
                        data-testid={`assign-moto-${item.budget_item_id}`}
                        onClick={() => handleVehicleAssignment(item, 'MOTO')}
                        className="inline-flex items-center px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full hover:bg-green-200"
                      >
                        <Bike className="w-3 h-3 mr-1" /> Moto
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="text-sm font-medium text-gray-900">{item.service_name}</div>
                    <div className="text-xs text-gray-500">{item.service_code}</div>
                    <div className="text-xs text-gray-400 sm:hidden">{item.neighborhood} · R$ {item.service_value.toFixed(2)}</div>
                  </td>
                  <td className="px-4 py-4 text-sm text-gray-900 whitespace-nowrap">{item.client_name}</td>
                  <td className="px-4 py-4 text-sm text-gray-900 whitespace-nowrap hidden sm:table-cell">{item.neighborhood}</td>
                  <td className="px-4 py-4 text-sm text-gray-900 whitespace-nowrap hidden sm:table-cell">R$ {item.service_value.toFixed(2)}</td>
                  {showStatus && (
                    <td className="px-4 py-4">
                      <div className="flex items-center space-x-2">
                        <select
                          value={editingStatus[item.budget_item_id] || item.status}
                          onChange={e => handleStatusChange(item.budget_item_id, e.target.value)}
                          className="text-xs px-2 py-1 rounded border border-gray-300 focus:ring-2 focus:ring-blue-500"
                        >
                          {statusOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                        {editingStatus[item.budget_item_id] && editingStatus[item.budget_item_id] !== item.status && (
                          <button onClick={() => applyStatusChange(item)} className="p-1 text-white bg-green-600 hover:bg-green-700 rounded">
                            <Check className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </td>
                  )}
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
        onRemoveItem={id => handleRemoveFromRoute(id, 'CARRO')}
        onOptimize={() => handleOptimizeRoute('CARRO')}
        vehicleColor="blue"
      />

      {/* Section 3: Moto Route */}
      <RouteSection
        title="Rota Moto"
        icon={<Bike className="w-5 h-5 text-green-600 mr-2" />}
        items={motoRouteItems}
        onRemoveItem={id => handleRemoveFromRoute(id, 'MOTO')}
        onOptimize={() => handleOptimizeRoute('MOTO')}
        vehicleColor="green"
      />

      {/* Section 4: Prioritization */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center mb-6">
          <RouteIcon className="w-5 h-5 text-purple-600 mr-2" />
          <h2 className="text-xl font-semibold text-gray-900">Priorização de Rota</h2>
        </div>

        {prioritizationItems.length > 0 ? (
          <div>
            <div className="mb-4 p-3 bg-gray-50 rounded-lg flex items-center">
              {currentVehicleType === 'CARRO'
                ? <Truck className="w-4 h-4 text-blue-600 mr-2" />
                : <Bike className="w-4 h-4 text-green-600 mr-2" />}
              <span className="text-sm font-medium text-gray-700">
                Veículo: <strong>{currentVehicleType}</strong>
              </span>
            </div>

            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
              <Navigation className="w-4 h-4 inline mr-1" />
              A rota será calculada pelo <strong>Geoapify Route Planner</strong> considerando as prioridades definidas.
            </div>

            <div className="space-y-3">
              {prioritizationItems.map((item, idx) => (
                <div key={`prio-${item.budget_item_id}-${idx}`} className="flex items-center p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="w-8 h-8 bg-purple-600 text-white rounded-full flex items-center justify-center text-sm font-bold mr-4 shrink-0">
                    {idx + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900">{item.client_name}</div>
                    <div className="text-sm text-gray-600">{item.service_name}</div>
                    <div className="text-xs text-gray-500">{item.neighborhood}</div>
                  </div>
                  <div className="mx-3">
                    <label className="block text-xs font-medium text-gray-500 mb-1">PRIORIDADE</label>
                    <select
                      value={item.priority}
                      onChange={e => handlePriorityChange(item.budget_item_id, e.target.value)}
                      className={`text-xs px-3 py-1 rounded-full border font-medium ${getPriorityColor(item.priority)}`}
                    >
                      <option value="PRIMEIRA">Primeira</option>
                      <option value="AUTOMATICA">Automática</option>
                      <option value="ULTIMA">Última</option>
                    </select>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className="text-sm font-medium text-gray-900">R$ {item.service_value.toFixed(2)}</span>
                    <button
                      onClick={() => handleRemoveFromPrioritization(item.budget_item_id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 p-4 bg-purple-50 rounded-lg">
              <h4 className="text-sm font-medium text-purple-900 mb-2">Legenda:</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
                <div><span className="inline-block w-3 h-3 bg-red-100 border border-red-200 rounded mr-1" /><b>Primeira:</b> Início da rota</div>
                <div><span className="inline-block w-3 h-3 bg-blue-100 border border-blue-200 rounded mr-1" /><b>Automática:</b> Otimizado pelo Geoapify</div>
                <div><span className="inline-block w-3 h-3 bg-yellow-100 border border-yellow-200 rounded mr-1" /><b>Última:</b> Final da rota</div>
              </div>
            </div>

            {/* Opção: considerar tráfego médio da região */}
            <label className="mt-5 flex items-center justify-center gap-2 cursor-pointer">
              <input type="checkbox" checked={considerTraffic}
                onChange={e => setConsiderTraffic(e.target.checked)}
                className="h-4 w-4 text-blue-600 rounded border-gray-300" />
              <span className="text-sm text-gray-700">
                🚦 Considerar tráfego médio da região
                <span className="text-xs text-gray-400 ml-1">(ajusta ordem e tempo conforme o trânsito típico)</span>
              </span>
            </label>

            <div className="mt-4 flex justify-center">
              <button
                data-testid="calculate-geoapify-route"
                onClick={handleCalculateOptimizedRoute}
                className="flex items-center px-8 py-3 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors shadow-lg"
              >
                <Navigation className="w-5 h-5 mr-3" />
                <span className="font-medium">Calcular Rota com Geoapify</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <RouteIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>Use os botões "Otimizar Rota" das seções Carro/Moto para enviar itens à priorização</p>
          </div>
        )}
      </div>

      {/* Section 5: Visualize & Save */}
      <div id="geo-visualization" className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center mb-6">
          <Navigation className="w-5 h-5 text-blue-600 mr-2" />
          <h2 className="text-xl font-semibold text-gray-900">Visualizar e Salvar</h2>
        </div>

        {/* Route date/time controls */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Data da Rota</label>
            <input type="date" value={routeDate} onChange={e => setRouteDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Horário de Início</label>
            <input type="time" value={routeTime} onChange={e => setRouteTime(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
          </div>
          <div className="flex items-end">
            <div className="bg-white px-4 py-2 rounded-lg border border-gray-300 flex items-center">
              {currentVehicleType === 'CARRO'
                ? <Truck className="w-4 h-4 text-blue-600 mr-2" />
                : <Bike className="w-4 h-4 text-green-600 mr-2" />}
              <span className="text-sm font-medium">{currentVehicleType}</span>
            </div>
          </div>
        </div>

        {/* Map — always visible */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            {optimizedRoute ? 'Mapa da Rota Otimizada' : 'Mapa — Aguardando Rota'}
          </h3>
          <div className="border border-gray-300 rounded-lg overflow-hidden">
            <div ref={mapRef} style={{ height: '360px', width: '100%' }} className="bg-gray-100" />
          </div>
          <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            {optimizedRoute
              ? '🏢 = Empresa (início/fim) · Números = ordem otimizada pelo Geoapify'
              : 'Mapa aguardando dados da otimização de rota'}
          </p>
        </div>

        {optimizedRoute && optimizedRoute.stops && optimizedRoute.stops.length > 0 ? (
          <div>
            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <MapPin className="w-5 h-5 text-blue-600 mr-2" />
                  <div>
                    <div className="text-sm text-blue-600 font-medium">Paradas</div>
                    <div className="text-2xl font-bold text-blue-900">{optimizedRoute.stops.length}</div>
                  </div>
                </div>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <Clock className="w-5 h-5 text-green-600 mr-2" />
                  <div>
                    <div className="text-sm text-green-600 font-medium">Duração Estimada</div>
                    <div className="text-2xl font-bold text-green-900">
                      {Math.floor((optimizedRoute.total_duration || 0) / 60)}h {(optimizedRoute.total_duration || 0) % 60}min
                    </div>
                    {/* Comparação trânsito vs livre */}
                    {(optimizedRoute.total_duration_free != null && optimizedRoute.total_duration_traffic != null) && (
                      <div className="text-[11px] text-gray-500 mt-1 leading-tight">
                        <div>🟢 Sem trânsito: {Math.floor(optimizedRoute.total_duration_free / 60)}h {optimizedRoute.total_duration_free % 60}min</div>
                        <div>🚦 Com trânsito: {Math.floor(optimizedRoute.total_duration_traffic / 60)}h {optimizedRoute.total_duration_traffic % 60}min</div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <RouteIcon className="w-5 h-5 text-purple-600 mr-2" />
                  <div>
                    <div className="text-sm text-purple-600 font-medium">Distância</div>
                    <div className="text-2xl font-bold text-purple-900">{optimizedRoute.total_distance || 0} km</div>
                  </div>
                </div>
              </div>
              <div className="bg-orange-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <FileText className="w-5 h-5 text-orange-600 mr-2" />
                  <div>
                    <div className="text-sm text-orange-600 font-medium">Valor Total</div>
                    <div className="text-2xl font-bold text-orange-900">
                      R$ {optimizedRoute.stops.reduce((t, s) => t + s.service_value, 0).toFixed(2)}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Optimized stops order list */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <Navigation className="w-5 h-5 text-blue-600 mr-2" />
                Ordem Otimizada das Paradas
              </h3>
              <div className="space-y-2">

                {/* Ponto de início — Empresa */}
                <div className="flex items-center p-3 bg-green-50 border-2 border-green-300 rounded-lg">
                  <div className="w-8 h-8 bg-green-600 text-white rounded-full flex items-center justify-center text-lg mr-3 shrink-0">
                    🏢
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold text-green-800">
                      {optimizedRoute.company_address?.full_address
                        ? optimizedRoute.company_address.full_address.split(',')[0]
                        : 'Empresa — SuperDry'}
                    </div>
                    <div className="text-xs text-green-600">{optimizedRoute.company_address?.neighborhood || 'Ponto de saída'}</div>
                  </div>
                  <span className="text-xs font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded-full">SAÍDA</span>
                </div>

                {[...optimizedRoute.stops]
                  .sort((a, b) => (a.order_sequence || 0) - (b.order_sequence || 0))
                  .map((stop, idx) => (
                    <div key={`opt-stop-${stop.id || idx}`}
                      className="flex items-center p-3 bg-gray-50 border border-gray-200 rounded-lg">
                      <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold mr-3 shrink-0">
                        {stop.order_sequence || idx + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900">{stop.client_name}</div>
                        <div className="text-xs text-gray-600">{stop.service_name}</div>
                        <div className="text-xs text-gray-500">{stop.address?.neighborhood || stop.neighborhood}</div>
                      </div>
                      <div className="text-right ml-3">
                        <div className="text-sm font-medium text-gray-900">R$ {stop.service_value.toFixed(2)}</div>
                        <div className="text-xs text-gray-500">{stop.estimated_duration}min</div>
                        <div className="text-xs px-2 py-0.5 rounded-full font-medium mt-1 bg-blue-100 text-blue-800">
                          {stop.priority}
                        </div>
                      </div>
                    </div>
                  ))}

                {/* Ponto de retorno — Empresa */}
                <div className="flex items-center p-3 bg-green-50 border-2 border-green-300 rounded-lg">
                  <div className="w-8 h-8 bg-green-600 text-white rounded-full flex items-center justify-center text-lg mr-3 shrink-0">
                    🏢
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold text-green-800">
                      {optimizedRoute.company_address?.full_address
                        ? optimizedRoute.company_address.full_address.split(',')[0]
                        : 'Empresa — SuperDry'}
                    </div>
                    <div className="text-xs text-green-600">{optimizedRoute.company_address?.neighborhood || 'Ponto de retorno'}</div>
                  </div>
                  <span className="text-xs font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded-full">RETORNO</span>
                </div>
              </div>

              {/* Resumo do deslocamento total */}
              <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-600 flex items-center justify-between">
                <span>Deslocamento total (saída → paradas → retorno)</span>
                <span className="font-bold text-gray-900">{optimizedRoute.total_distance || 0} km</span>
              </div>
            </div>

            {/* Route alias */}
            <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <h4 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
                <FileText className="w-4 h-4 mr-2 text-blue-600" />Nome da Rota (Opcional)
              </h4>
              <input
                type="text"
                value={routeAlias}
                onChange={e => setRouteAlias(e.target.value)}
                placeholder="Digite um nome personalizado..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
              />
              <p className="text-xs text-gray-500 mt-1">
                <strong>Padrão:</strong> {generateRouteAlias(routeDate, routeTime, currentVehicleType)}
              </p>
            </div>

            {/* Actions */}
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => { setOptimizedRoute(null); setStopPriorities({}); setRouteAlias(''); }}
                className="flex items-center px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg"
              >
                <Edit3 className="w-4 h-4 mr-2" /> Limpar
              </button>
              <button
                data-testid="save-geoapify-route"
                onClick={handleSaveRoute}
                className="flex items-center px-6 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg"
              >
                <Save className="w-4 h-4 mr-2" /> Salvar Rota
              </button>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Navigation className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhuma Rota Calculada</h3>
            <p>Use o botão "Calcular Rota com Geoapify" na seção de priorização.</p>
          </div>
        )}
      </div>

      {/* Section 6: Saved Routes */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center mb-4">
          <RouteIcon className="w-5 h-5 text-orange-600 mr-2" />
          <h2 className="text-xl font-semibold text-gray-900">Rotas Salvas</h2>
        </div>

        {/* Filtro e ordenação */}
        <div className="flex flex-wrap items-center gap-3 mb-5 bg-gray-50 border border-gray-200 rounded-lg p-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={savedSearchText}
              onChange={(e) => setSavedSearchText(e.target.value)}
              placeholder="Buscar por nome, bairro, ID ou editor..."
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <select
            value={savedVehicleFilter}
            onChange={(e) => setSavedVehicleFilter(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="TODOS">Todos os veículos</option>
            <option value="CARRO">Carro</option>
            <option value="MOTO">Moto</option>
          </select>

          <button
            type="button"
            onClick={() => setSavedSortOrder(savedSortOrder === 'recente' ? 'antiga' : 'recente')}
            className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-100"
            title="Alternar ordenação"
          >
            <ArrowUpDown className="w-4 h-4 text-gray-500" />
            {savedSortOrder === 'recente' ? 'Mais recente primeiro' : 'Mais antiga primeiro'}
          </button>
        </div>

        <div className="space-y-3">
          {getFilteredSortedRoutes().slice(0, 20).map((route, idx) => (
            <div key={`saved-${route.id}-${idx}`}
              className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center">
                {route.vehicle_type === 'CARRO'
                  ? <Truck className="w-5 h-5 text-blue-600 mr-3" />
                  : <Bike className="w-5 h-5 text-green-600 mr-3" />}
                <div>
                  <div className="text-sm font-medium text-gray-900">
                    {route.alias || generateRouteAlias(route.planned_date, route.planned_start_time, route.vehicle_type)}
                  </div>
                  <div className="text-xs text-gray-500 font-mono">{route.id}</div>
                  <div className="text-xs text-gray-500">
                    {new Date(route.planned_date).toLocaleDateString('pt-BR')} às {route.planned_start_time}
                  </div>
                  <div className="text-xs text-gray-500">
                    {route.stops.length} paradas · {Math.floor(route.total_duration / 60)}h {route.total_duration % 60}min · {route.total_distance} km
                  </div>
                  <div className="text-xs text-blue-600 mt-1">
                    <strong>Bairros:</strong> {getRouteNeighborhoods(route.stops)}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    <strong>Última edição:</strong> {formatCuiabaTime(route.updated_at)}
                    {route.last_edited_by && <span className="ml-1">por <strong>{route.last_edited_by}</strong></span>}
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button onClick={() => handleEditRoute(route.id)}
                  className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg" title="Editar">
                  <Edit3 className="w-4 h-4" />
                </button>
                <button onClick={() => handleDeleteRoute(route.id)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg" title="Excluir">
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
        {savedRoutes.length > 0 && getFilteredSortedRoutes().length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <Search className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>Nenhuma rota encontrada com esse filtro</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── RouteSection sub-component ─────────────────────────────────────────────

function RouteSection({ title, icon, items, onRemoveItem, onOptimize, vehicleColor }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">{icon}<h2 className="text-xl font-semibold text-gray-900">{title}</h2></div>
        {items.length > 0 && (
          <button
            onClick={onOptimize}
            className={`flex items-center px-4 py-2 text-white rounded-lg transition-colors ${
              vehicleColor === 'blue' ? 'bg-blue-600 hover:bg-blue-700' : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            <Play className="w-4 h-4 mr-2" /> Enviar para Priorização
          </button>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full table-auto">
          <thead>
            <tr className="bg-gray-50">
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Descrição</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cliente</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Bairro</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Valor</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ações</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {items.map((item, idx) => (
              <tr key={`ri-${item.budget_item_id}-${idx}`} className="hover:bg-gray-50">
                <td className="px-4 py-4">
                  <div className="text-sm font-medium text-gray-900">{item.service_name}</div>
                  <div className="text-xs text-gray-500">{item.service_code}</div>
                </td>
                <td className="px-4 py-4 text-sm text-gray-900 whitespace-nowrap">{item.client_name}</td>
                <td className="px-4 py-4 text-sm text-gray-900 whitespace-nowrap">{item.neighborhood}</td>
                <td className="px-4 py-4 text-sm text-gray-900 whitespace-nowrap">R$ {item.service_value.toFixed(2)}</td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <button onClick={() => onRemoveItem(item.budget_item_id)} className="text-red-600 hover:text-red-900">
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
