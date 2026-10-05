import React, { useState, useEffect, useRef } from 'react';
import { FlaskConical, Truck, Bike, Trash2, Plus, X, Check, Search, Loader2 } from 'lucide-react';
import { toast } from '../hooks/use-toast';
import { routesApi } from '../services/api';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix default marker icons (mesmo ajuste usado em RoutesGeoapify.js/MiniMap.js)
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

const SCENARIO_COLORS = ['#2563EB', '#DC2626', '#059669', '#D97706', '#7C3AED', '#DB2777', '#0891B2', '#65A30D'];
const LETTERS = 'ABCDEFGHIJKLMNOP';

function getSuggestedDateTime() {
  const now  = new Date();
  const hour = now.getHours();
  if (hour < 13) return { suggestedDate: now.toISOString().split('T')[0], suggestedTime: '13:00' };
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  return { suggestedDate: tomorrow.toISOString().split('T')[0], suggestedTime: '08:00' };
}

let scenarioSeq = 0;
function newScenario() {
  const idx = scenarioSeq++;
  const { suggestedDate, suggestedTime } = getSuggestedDateTime();
  const letter = LETTERS[idx % LETTERS.length];
  return {
    id: `scn-${Date.now()}-${idx}`,
    letter,
    color: SCENARIO_COLORS[idx % SCENARIO_COLORS.length],
    name: `Cenário ${letter}`,
    vehicleType: 'CARRO',
    traffic: false,
    plannedDate: suggestedDate,
    plannedTime: suggestedTime,
    itemIds: [],
    priorities: {},
    result: null,
    simulating: false,
    confirming: false,
    confirmedRouteId: null,
  };
}

// Mapa de resultado de um cenário -- mesmo padrão de desenho (empresa + paradas
// numeradas + traçado real do Geoapify) usado em RoutesGeoapify.js, só que cada
// cenário tem seu próprio mapa isolado (cards lado a lado).
function ScenarioMap({ result }) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;
    try {
      mapInstanceRef.current = L.map(mapRef.current).setView([-15.601481, -56.097389], 11);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
      }).addTo(mapInstanceRef.current);
      setTimeout(() => mapInstanceRef.current?.invalidateSize(), 200);
    } catch (e) { console.error('Map init error:', e); }
    return () => {
      if (mapInstanceRef.current) { mapInstanceRef.current.remove(); mapInstanceRef.current = null; }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !result?.stops?.length) return;

    map.eachLayer(layer => {
      if (layer instanceof L.Marker || layer instanceof L.Polyline) map.removeLayer(layer);
    });

    const companyLat = result.company_address?.latitude  || -15.6014;
    const companyLng = result.company_address?.longitude || -56.0974;

    const companyIcon = L.divIcon({
      className: '',
      html: `<div style="background:linear-gradient(135deg,#10B981,#059669);color:white;width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:15px;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,.4)">🏢</div>`,
      iconSize: [36, 36], iconAnchor: [18, 18]
    });
    L.marker([companyLat, companyLng], { icon: companyIcon }).addTo(map).bindPopup('<b>Empresa</b>');

    const markers = [];
    const sortedStops = [...result.stops].sort((a, b) => (a.order_sequence || 0) - (b.order_sequence || 0));
    sortedStops.forEach((stop, i) => {
      const lat = stop.address?.latitude;
      const lng = stop.address?.longitude;
      if (!lat || !lng) return;
      const seq = stop.order_sequence || (i + 1);
      const icon = L.divIcon({
        className: '',
        html: `<div style="background:linear-gradient(135deg,#2563EB,#1D4ED8);color:white;border-radius:16px;padding:3px 8px;display:flex;align-items:center;gap:4px;font-size:10px;font-weight:bold;border:2px solid white;box-shadow:0 2px 5px rgba(0,0,0,.3);white-space:nowrap"><span style="background:white;color:#2563EB;border-radius:50%;width:15px;height:15px;display:inline-flex;align-items:center;justify-content:center;font-size:9px;font-weight:bold">${seq}</span>${(stop.client_name || '').split(' ')[0]}</div>`,
        iconSize: [70, 24], iconAnchor: [35, 12]
      });
      const marker = L.marker([lat, lng], { icon }).addTo(map);
      marker.bindPopup(`<b>${seq}ª parada — ${stop.client_name}</b><br>${stop.service_name}<br>R$ ${Number(stop.service_value || 0).toFixed(2)}<br>${stop.address?.neighborhood || ''}`);
      markers.push(marker);
    });

    const geom = result.route_geometry;
    let drewRealRoute = false;
    if (geom && Array.isArray(geom.coordinates)) {
      const segments = geom.type === 'MultiLineString' ? geom.coordinates : [geom.coordinates];
      segments.forEach(seg => {
        const latlngs = seg.map(([lng, lat]) => [lat, lng]);
        if (latlngs.length > 1) {
          L.polyline(latlngs, { color: '#2563EB', weight: 4, opacity: 0.8 }).addTo(map);
          drewRealRoute = true;
        }
      });
    }
    if (!drewRealRoute) {
      const lineCoords = [
        [companyLat, companyLng],
        ...sortedStops.filter(s => s.address?.latitude && s.address?.longitude).map(s => [s.address.latitude, s.address.longitude]),
        [companyLat, companyLng],
      ];
      L.polyline(lineCoords, { color: '#94A3B8', weight: 3, opacity: 0.6, dashArray: '8,5' }).addTo(map);
    }

    if (markers.length > 0) {
      const all = [L.marker([companyLat, companyLng]), ...markers];
      map.fitBounds(L.featureGroup(all).getBounds().pad(0.15));
    }
    setTimeout(() => map.invalidateSize(), 100);
  }, [result]);

  return <div ref={mapRef} style={{ height: '220px', width: '100%', borderRadius: '8px' }} />;
}

function ScenarioCard({ scenario, resolveItem, onUpdate, onRemove, onToggleItem, onSetPriority, onSimulate, onConfirm }) {
  const items = scenario.itemIds.map(resolveItem).filter(Boolean);
  const totalValue = items.reduce((sum, i) => sum + (i.service_value || 0), 0);
  const locked = !!scenario.confirmedRouteId;

  return (
    <div
      className="bg-white rounded-lg shadow-md border-2 flex flex-col shrink-0"
      style={{ borderColor: scenario.color, width: '340px' }}
    >
      <div className="p-3 border-b border-gray-100 flex items-center justify-between gap-2" style={{ backgroundColor: `${scenario.color}15` }}>
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span
            className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
            style={{ backgroundColor: scenario.color }}
          >
            {scenario.letter}
          </span>
          <input
            value={scenario.name}
            onChange={(e) => onUpdate(scenario.id, { name: e.target.value })}
            disabled={locked}
            className="font-semibold text-sm text-gray-800 bg-transparent border-none focus:outline-none focus:underline w-full truncate disabled:opacity-70"
          />
        </div>
        <button onClick={() => onRemove(scenario.id)} className="text-gray-400 hover:text-red-600 shrink-0">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      <div className="p-3 space-y-2 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <button
            onClick={() => onUpdate(scenario.id, { vehicleType: 'CARRO' })}
            disabled={locked}
            className={`flex-1 flex items-center justify-center gap-1 py-1.5 rounded text-xs font-medium border disabled:opacity-50 ${scenario.vehicleType === 'CARRO' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200'}`}
          >
            <Truck className="w-3.5 h-3.5" /> Carro
          </button>
          <button
            onClick={() => onUpdate(scenario.id, { vehicleType: 'MOTO' })}
            disabled={locked}
            className={`flex-1 flex items-center justify-center gap-1 py-1.5 rounded text-xs font-medium border disabled:opacity-50 ${scenario.vehicleType === 'MOTO' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200'}`}
          >
            <Bike className="w-3.5 h-3.5" /> Moto
          </button>
        </div>
        <label className="flex items-center gap-2 text-xs text-gray-600">
          <input
            type="checkbox"
            checked={scenario.traffic}
            disabled={locked}
            onChange={(e) => onUpdate(scenario.id, { traffic: e.target.checked })}
          />
          Considerar trânsito médio da região
        </label>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={scenario.plannedDate}
            disabled={locked}
            onChange={(e) => onUpdate(scenario.id, { plannedDate: e.target.value })}
            className="flex-1 text-xs border border-gray-200 rounded px-1.5 py-1 disabled:opacity-50"
          />
          <input
            type="time"
            value={scenario.plannedTime}
            disabled={locked}
            onChange={(e) => onUpdate(scenario.id, { plannedTime: e.target.value })}
            className="flex-1 text-xs border border-gray-200 rounded px-1.5 py-1 disabled:opacity-50"
          />
        </div>
      </div>

      <div className="p-3 border-b border-gray-100 max-h-48 overflow-y-auto space-y-1">
        {items.length === 0 && (
          <p className="text-xs text-gray-400 italic">
            Nenhum item ainda — marque itens no painel ao lado com "{scenario.letter}".
          </p>
        )}
        {items.map(item => (
          <div key={item.budget_item_id} className="flex items-center gap-1 text-xs bg-gray-50 rounded px-2 py-1">
            <div className="flex-1 min-w-0">
              <p className="font-medium text-gray-800 truncate">{item.client_name}</p>
              <p className="text-gray-500 truncate">{item.service_name} · R$ {Number(item.service_value || 0).toFixed(2)}</p>
            </div>
            <select
              value={scenario.priorities[item.budget_item_id] || 'AUTOMATICA'}
              disabled={locked}
              onChange={(e) => onSetPriority(scenario.id, item.budget_item_id, e.target.value)}
              className="text-[10px] border border-gray-200 rounded px-0.5 disabled:opacity-50"
            >
              <option value="PRIMEIRA">1ª</option>
              <option value="AUTOMATICA">Auto</option>
              <option value="ULTIMA">Últ.</option>
            </select>
            {!locked && (
              <button onClick={() => onToggleItem(scenario.id, item)} className="text-gray-400 hover:text-red-600 shrink-0">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        ))}
        {items.length > 0 && (
          <p className="text-[10px] text-gray-400 pt-1">Total: R$ {totalValue.toFixed(2)} · {items.length} item(ns)</p>
        )}
      </div>

      <div className="p-3 space-y-2">
        {!locked ? (
          <>
            <button
              onClick={() => onSimulate(scenario)}
              disabled={scenario.simulating || items.length === 0}
              className="w-full flex items-center justify-center gap-2 py-2 rounded-md text-sm font-medium bg-gray-800 text-white disabled:opacity-50"
            >
              {scenario.simulating ? <Loader2 className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}
              {scenario.simulating ? 'Simulando…' : 'Simular'}
            </button>
            {scenario.result && (
              <button
                onClick={() => onConfirm(scenario)}
                disabled={scenario.confirming}
                className="w-full flex items-center justify-center gap-2 py-2 rounded-md text-sm font-medium bg-green-600 text-white disabled:opacity-50"
              >
                {scenario.confirming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                {scenario.confirming ? 'Criando rota…' : 'Confirmar e Criar Rota'}
              </button>
            )}
          </>
        ) : (
          <div className="text-center py-2 bg-green-50 rounded-md border border-green-200">
            <p className="text-sm font-semibold text-green-700">✅ Rota real criada</p>
            <p className="text-xs text-green-600">{scenario.confirmedRouteId}</p>
          </div>
        )}

        {scenario.result && (
          <div className="pt-2 border-t border-gray-100 space-y-2">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-blue-50 rounded px-2 py-1.5">
                <p className="text-gray-500">Distância</p>
                <p className="font-semibold text-blue-700">{scenario.result.total_distance_km} km</p>
              </div>
              <div className="bg-blue-50 rounded px-2 py-1.5">
                <p className="text-gray-500">Tempo</p>
                <p className="font-semibold text-blue-700">
                  {scenario.result.total_duration_free}min
                  {scenario.result.total_duration_traffic !== scenario.result.total_duration_free &&
                    ` (trânsito: ${scenario.result.total_duration_traffic}min)`}
                </p>
              </div>
            </div>
            <ScenarioMap result={scenario.result} />
            <ol className="text-xs space-y-0.5 list-decimal list-inside text-gray-600">
              {[...scenario.result.stops].sort((a, b) => (a.order_sequence || 0) - (b.order_sequence || 0)).map(s => (
                <li key={s.id}>{s.client_name} — {s.address?.neighborhood || '—'}</li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </div>
  );
}

export function SimuladorRotas() {
  const [availableItems, setAvailableItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [scenarios, setScenarios] = useState(() => [newScenario()]);

  useEffect(() => { loadAvailable(); }, []);

  const loadAvailable = async () => {
    setLoading(true);
    try {
      const res = await routesApi.getAvailableItems();
      setAvailableItems(res.data || []);
    } catch (err) {
      toast({ title: 'Erro', description: 'Erro ao carregar itens disponíveis.', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const filteredItems = availableItems.filter(i => {
    if (!searchText.trim()) return true;
    const q = searchText.toLowerCase();
    return (i.client_name || '').toLowerCase().includes(q) ||
           (i.service_name || '').toLowerCase().includes(q) ||
           (i.neighborhood || '').toLowerCase().includes(q);
  });

  const addScenario = () => setScenarios(prev => [...prev, newScenario()]);
  const removeScenario = (id) => setScenarios(prev => prev.filter(s => s.id !== id));
  const updateScenario = (id, patch) => setScenarios(prev => prev.map(s => s.id === id ? { ...s, ...patch } : s));

  const toggleItemInScenario = (scenarioId, item) => {
    setScenarios(prev => prev.map(s => {
      if (s.id !== scenarioId) return s;
      const has = s.itemIds.includes(item.budget_item_id);
      if (has) {
        return { ...s, itemIds: s.itemIds.filter(id => id !== item.budget_item_id), result: null };
      }
      const addr = item.address;
      if (!addr || !addr.latitude || !addr.longitude || !addr.full_address) {
        toast({
          title: 'Endereço incompleto!',
          description: `${item.client_name} não possui endereço com coordenadas cadastrado. Complete o cadastro do cliente antes de incluí-lo numa simulação.`,
          variant: 'destructive',
        });
        return s;
      }
      return {
        ...s,
        itemIds: [...s.itemIds, item.budget_item_id],
        priorities: { ...s.priorities, [item.budget_item_id]: s.priorities[item.budget_item_id] || 'AUTOMATICA' },
        result: null,
      };
    }));
  };

  const setItemPriority = (scenarioId, itemId, priority) => {
    setScenarios(prev => prev.map(s => s.id === scenarioId ? { ...s, priorities: { ...s.priorities, [itemId]: priority }, result: null } : s));
  };

  const simulateScenario = async (scenario) => {
    if (scenario.itemIds.length === 0) {
      toast({ title: 'Aviso', description: 'Adicione itens a este cenário antes de simular.' });
      return;
    }
    const items = scenario.itemIds.map(id => availableItems.find(i => i.budget_item_id === id)).filter(Boolean);
    const badNeighborhood = items.filter(i => (i.address?.neighborhood || '').toUpperCase() === 'BAIRRO A COMPLETAR');
    if (badNeighborhood.length > 0) {
      toast({
        title: 'Cadastros Incompletos!',
        description: `Complete o bairro de: ${badNeighborhood.map(i => i.client_name).join(', ')}`,
        variant: 'destructive',
      });
      return;
    }

    updateScenario(scenario.id, { simulating: true });
    try {
      const stopsData = scenario.itemIds.map(id => ({ budget_item_id: id, priority: scenario.priorities[id] || 'AUTOMATICA' }));
      const res = await routesApi.simulateGeoapify({
        vehicle_type: scenario.vehicleType,
        stops: stopsData,
        traffic: scenario.traffic,
      });
      updateScenario(scenario.id, { result: res.data, simulating: false });
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Erro ao simular rota.';
      toast({ title: 'Erro ao simular', description: msg, variant: 'destructive' });
      updateScenario(scenario.id, { simulating: false });
    }
  };

  const confirmScenario = async (scenario) => {
    if (!scenario.result) {
      toast({ title: 'Aviso', description: 'Simule o cenário antes de confirmar.' });
      return;
    }
    if (!window.confirm(`Confirmar e criar a rota real do "${scenario.name}" com ${scenario.itemIds.length} item(ns)? Isso vai persistir a rota de verdade, igual às telas de Rotas.`)) {
      return;
    }

    updateScenario(scenario.id, { confirming: true });
    try {
      // Mesmo fluxo real das telas de Rotas (Geoapify): create -> addStops -> optimize-geoapify.
      const createRes = await routesApi.create({
        vehicle_type: scenario.vehicleType,
        planned_date: scenario.plannedDate,
        planned_start_time: scenario.plannedTime,
        stops: [],
      });
      const routeId = createRes.data.id;

      const stopsData = scenario.itemIds.map(id => ({ budget_item_id: id, priority: scenario.priorities[id] || 'AUTOMATICA' }));
      await routesApi.addStops(routeId, stopsData);
      await routesApi.optimizeGeoapify(routeId, scenario.traffic);

      updateScenario(scenario.id, { confirming: false, confirmedRouteId: routeId });
      toast({ title: 'Rota criada!', description: `"${scenario.name}" confirmado como rota real ${routeId}.` });

      // Os itens confirmados saem de circulação de verdade -- remove dos OUTROS
      // cenários também (não estão mais disponíveis) e recarrega a lista real.
      const confirmedIds = new Set(scenario.itemIds);
      let anyOtherAffected = false;
      setScenarios(prev => prev.map(s => {
        if (s.id === scenario.id) return s;
        const removedHere = s.itemIds.filter(id => confirmedIds.has(id));
        if (removedHere.length === 0) return s;
        anyOtherAffected = true;
        return { ...s, itemIds: s.itemIds.filter(id => !confirmedIds.has(id)), result: null };
      }));
      if (anyOtherAffected) {
        toast({
          title: 'Atenção',
          description: 'Algum(ns) item(ns) confirmado(s) também estava(m) em outro cenário e foi(ram) removido(s) dele — não está(ão) mais disponível(is).',
        });
      }
      await loadAvailable();
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Erro ao confirmar rota.';
      toast({ title: 'Erro ao confirmar', description: msg, variant: 'destructive' });
      updateScenario(scenario.id, { confirming: false });
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
          <FlaskConical className="w-5 h-5 text-amber-600" /> Simulador de Rotas
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          Monte e compare cenários de rota livremente — nada aqui é salvo no sistema até você clicar em
          {' '}<strong>"Confirmar e Criar Rota"</strong> dentro de um cenário específico. Simular não consome
          nenhum item nem cria rota alguma; só o botão de confirmar faz isso, com o mesmo efeito de
          criar/salvar das telas de Rotas.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
        {/* Painel de itens disponíveis */}
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-3 space-y-2 lg:sticky lg:top-4 lg:self-start lg:max-h-[80vh] lg:overflow-y-auto">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700">Itens Disponíveis</h3>
            <button onClick={loadAvailable} className="text-xs text-blue-600 hover:underline">atualizar</button>
          </div>
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2 top-2" />
            <input
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Buscar cliente, serviço, bairro…"
              className="w-full text-xs border border-gray-200 rounded pl-7 pr-2 py-1.5"
            />
          </div>
          {loading ? (
            <p className="text-xs text-gray-400 text-center py-4">Carregando…</p>
          ) : filteredItems.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-4">Nenhum item disponível.</p>
          ) : (
            <div className="space-y-1">
              {filteredItems.map(item => (
                <div key={item.budget_item_id} className="border border-gray-100 rounded px-2 py-1.5">
                  <p className="text-xs font-medium text-gray-800 truncate">{item.client_name}</p>
                  <p className="text-[11px] text-gray-500 truncate">
                    {item.service_name} · R$ {Number(item.service_value || 0).toFixed(2)} · {item.neighborhood || '—'}
                  </p>
                  <div className="flex gap-1 mt-1 flex-wrap">
                    {scenarios.map(s => {
                      const active = s.itemIds.includes(item.budget_item_id);
                      return (
                        <button
                          key={s.id}
                          onClick={() => toggleItemInScenario(s.id, item)}
                          disabled={!!s.confirmedRouteId}
                          title={active ? `Remover de ${s.name}` : `Adicionar a ${s.name}`}
                          className="w-6 h-6 rounded-full text-[10px] font-bold border flex items-center justify-center disabled:opacity-30"
                          style={active
                            ? { backgroundColor: s.color, color: 'white', borderColor: s.color }
                            : { backgroundColor: 'white', color: s.color, borderColor: s.color }}
                        >
                          {s.letter}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Cenários lado a lado */}
        <div className="space-y-3">
          <button onClick={addScenario} className="flex items-center gap-1 text-sm font-medium text-blue-600 hover:underline">
            <Plus className="w-4 h-4" /> Novo cenário
          </button>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {scenarios.map(s => (
              <ScenarioCard
                key={s.id}
                scenario={s}
                resolveItem={(id) => availableItems.find(i => i.budget_item_id === id) || { budget_item_id: id, client_name: '(item removido)', service_name: '', service_value: 0 }}
                onUpdate={updateScenario}
                onRemove={removeScenario}
                onToggleItem={toggleItemInScenario}
                onSetPriority={setItemPriority}
                onSimulate={simulateScenario}
                onConfirm={confirmScenario}
              />
            ))}
            {scenarios.length === 0 && (
              <p className="text-sm text-gray-400 italic py-8">Nenhum cenário ainda — clique em "Novo cenário".</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
