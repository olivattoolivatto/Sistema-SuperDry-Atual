import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Zap, FileText, Ruler, Play, Check, RefreshCw, AlertTriangle, ChevronDown, ChevronUp, MapPin, Building2, Loader2 } from 'lucide-react';
import api, { placesApi } from '../services/api';
import { toast } from '../hooks/use-toast';

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const post = (path, body) => api.post(path, body);

// ── AddressAutocomplete (mesma lógica do Clients.js) ──────────────────────────
function AddressAutocomplete({ value, onSelect, placeholder }) {
  const [query, setQuery] = useState(value?.full_address || '');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debRef = useRef(null);
  const boxRef = useRef(null);

  useEffect(() => {
    if (debRef.current) clearTimeout(debRef.current);
    if (!query || query.length < 3) { setResults([]); setOpen(false); return; }
    debRef.current = setTimeout(async () => {
      try {
        setLoading(true);
        const r = await placesApi.search(query);
        setResults(r.data?.results || []);
        setOpen(true);
      } catch { setResults([]); }
      finally { setLoading(false); }
    }, 350);
  }, [query]);

  useEffect(() => {
    const h = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  const handleChoose = async (p) => {
    setOpen(false);
    setQuery(p.description || '');
    let lat = p?.geometry?.location?.lat;
    let lng = p?.geometry?.location?.lng;
    let neighborhood = p?.neighborhood, city = p?.city, state = p?.state;
    let fullAddress = p.description || '';
    if ((!lat || !lng || !neighborhood || !city || !state) && p.place_id) {
      try {
        const det = await placesApi.getDetails(p.place_id);
        const d = det.data?.details?.result || det.data?.details || {};
        fullAddress = d.formatted_address || fullAddress;
        const geo = d.geometry?.location;
        if (geo) { lat = geo.lat; lng = geo.lng; }
        (d.address_components || []).forEach(c => {
          const t = c.types || [];
          if (t.includes('sublocality') || t.includes('sublocality_level_1') || t.includes('neighborhood'))
            neighborhood = c.long_name;
          if (t.includes('administrative_area_level_2') || t.includes('locality'))
            city = c.long_name;
          if (t.includes('administrative_area_level_1'))
            state = c.short_name || c.long_name;
        });
      } catch {}
    }
    onSelect({ full_address: fullAddress, neighborhood: neighborhood || '', city: city || '', state: state || '', latitude: lat || null, longitude: lng || null });
  };

  return (
    <div className="relative" ref={boxRef}>
      <div className="relative">
        <MapPin className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
        <input type="text" value={query} onChange={e => setQuery(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          placeholder={placeholder || 'Buscar endereço, bairro, condomínio…'}
          className="w-full pl-8 pr-8 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" />
        {loading && <Loader2 className="w-3.5 h-3.5 absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 animate-spin" />}
      </div>
      {open && results.length > 0 && (
        <ul className="absolute z-40 mt-1 w-full max-h-60 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-lg">
          {results.slice(0, 8).map(p => {
            const isPlace = p.source === 'text_search';
            return (
              <li key={p.place_id || p.description} onClick={() => handleChoose(p)}
                className="px-3 py-2 hover:bg-blue-50 cursor-pointer text-sm border-b border-gray-100 last:border-0 flex items-start gap-2">
                {isPlace
                  ? <Building2 className="w-3.5 h-3.5 text-blue-500 mt-0.5 shrink-0" />
                  : <MapPin className="w-3.5 h-3.5 text-gray-400 mt-0.5 shrink-0" />}
                <div className="min-w-0">
                  <div className="font-medium text-gray-900 truncate text-xs">{p.structured_formatting?.main_text || p.description}</div>
                  <div className="text-[10px] text-gray-500 truncate">{p.structured_formatting?.secondary_text || ''}</div>
                  {isPlace && <span className="text-[10px] text-blue-600">Local</span>}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// ── AutoBudget ─────────────────────────────────────────────────────────────────
function AutoBudget() {
  const [text, setText] = useState('');
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [editableItems, setEditableItems] = useState([]);
  const [addressObj, setAddressObj] = useState(null); // endereço com coords
  const [showFormat, setShowFormat] = useState(false);

  const handlePreview = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await post('/automation/preview-budget', { text });
      setPreview(r.data);
      setEditableItems(r.data.items || []);
      setAddressObj(null); // reset endereço para nova busca
    } catch (e) {
      toast({ title: 'Erro', description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally { setLoading(false); }
  };

  const handleExecute = async () => {
    if (!preview) return;
    setLoading(true);
    try {
      const r = await post('/automation/execute-budget', {
        ...preview,
        items: editableItems,
        client_address_obj: addressObj, // endereço com lat/lng
      });
      setResult(r.data);
      setPreview(null);
      setText('');
      toast({ title: 'Sucesso!', description: `Cliente e orçamento ${r.data.budget_id} criados.` });
    } catch (e) {
      toast({ title: 'Erro', description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally { setLoading(false); }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
          <FileText className="w-4 h-4 text-blue-600" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Automação de Orçamento</h3>
          <p className="text-xs text-gray-500">Cole os dados → sistema cria cliente + orçamento</p>
        </div>
      </div>

      {/* Formato esperado */}
      <button onClick={() => setShowFormat(v => !v)}
        className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700">
        {showFormat ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        Ver formato esperado
      </button>
      {showFormat && (
        <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-600 font-mono space-y-0.5">
          <p className="text-gray-400 mb-1"># Formato atual (será refinado):</p>
          <p>Nome do Cliente</p>
          <p>Telefone</p>
          <p>Endereço completo</p>
          <p>Nome do Serviço - Valor</p>
          <p>Outro Serviço - Valor</p>
          <p>obs: Observações opcionais</p>
        </div>
      )}

      {/* Input */}
      <textarea
        value={text}
        onChange={e => { setText(e.target.value); setPreview(null); setResult(null); }}
        placeholder="Cole aqui os dados do cliente e do orçamento..."
        rows={8}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-blue-500 resize-none"
      />

      <button
        onClick={handlePreview}
        disabled={!text.trim() || loading}
        className="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
      >
        {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
        Analisar Dados
      </button>

      {/* Preview */}
      {preview && (
        <div className="border border-blue-200 rounded-xl p-4 space-y-3 bg-blue-50">
          <h4 className="text-sm font-semibold text-blue-900 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            Confirme antes de criar
          </h4>

          <div className="grid grid-cols-1 gap-2 text-xs">
            <div className="bg-white rounded-lg p-2.5 border border-blue-200">
              <div className="text-[10px] text-gray-500 mb-0.5">Cliente</div>
              <div className="font-semibold text-gray-900">{preview.client_name || '—'}</div>
              <div className="text-gray-600 text-xs">{preview.client_phone || '—'}</div>
              {preview.client_exists && (
                <span className="inline-block mt-1 text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">
                  ✓ Já cadastrado
                </span>
              )}
            </div>

            {/* Endereço com busca */}
            <div className="col-span-2 bg-white rounded-lg p-2.5 border border-blue-200">
              <div className="text-[10px] text-gray-500 mb-1.5 flex items-center justify-between">
                <span>Endereço</span>
                {addressObj?.latitude
                  ? <span className="text-green-600 font-medium">✓ Coordenadas confirmadas</span>
                  : <span className="text-amber-600">Busque para confirmar coordenadas</span>}
              </div>
              <AddressAutocomplete
                value={addressObj || { full_address: preview.client_address || '' }}
                onSelect={setAddressObj}
                placeholder={preview.client_address || 'Buscar endereço…'}
              />
              {addressObj?.full_address && (
                <div className="mt-1.5 text-[10px] text-gray-500 space-y-0.5">
                  {addressObj.neighborhood && <span className="mr-2">📍 {addressObj.neighborhood}</span>}
                  {addressObj.city && <span className="mr-2">{addressObj.city}/{addressObj.state}</span>}
                  {addressObj.latitude && <span className="text-green-600">lat: {addressObj.latitude?.toFixed(4)}</span>}
                </div>
              )}
            </div>
            <div className="bg-white rounded-lg p-2.5 border border-blue-200">
              <div className="text-[10px] text-gray-500 mb-0.5">Itens ({editableItems.length})</div>
              {editableItems.map((item, i) => (
                <div key={i} className="flex items-center gap-1 mb-1">
                  <input
                    className="flex-1 text-xs px-1.5 py-0.5 border border-gray-300 rounded min-w-0"
                    value={item.service_name}
                    onChange={e => setEditableItems(prev => prev.map((it, j) => j===i ? {...it, service_name: e.target.value} : it))}
                  />
                  <input
                    type="number" className="w-16 text-xs px-1.5 py-0.5 border border-gray-300 rounded"
                    value={item.value}
                    onChange={e => setEditableItems(prev => prev.map((it, j) => j===i ? {...it, value: parseFloat(e.target.value)||0} : it))}
                  />
                </div>
              ))}
              <button onClick={() => setEditableItems(prev => [...prev, {service_name:'', value:0}])}
                className="text-[10px] text-blue-600 hover:text-blue-700 mt-1">+ item</button>
            </div>
          </div>

          {preview.notes && (
            <div className="text-xs text-gray-600 bg-yellow-50 border border-yellow-200 rounded px-2 py-1.5">
              📝 {preview.notes}
            </div>
          )}

          <div className="flex gap-2">
            <button onClick={() => setPreview(null)}
              className="flex-1 py-2 rounded-lg border border-gray-300 text-sm text-gray-700">
              Cancelar
            </button>
            <button onClick={handleExecute} disabled={loading}
              className="flex-1 py-2 rounded-lg bg-green-600 text-white text-sm font-semibold hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2">
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Confirmar e Criar
            </button>
          </div>
        </div>
      )}

      {/* Resultado */}
      {result && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-3 text-sm">
          <div className="font-semibold text-green-800 flex items-center gap-2 mb-2">
            <Check className="w-4 h-4" /> Criado com sucesso!
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs text-green-700">
            <div>Cliente: <strong>{result.client_id}</strong> {result.client_created ? '(novo)' : '(existente)'}</div>
            <div>Orçamento: <strong>{result.budget_id}</strong></div>
            <div>Itens: <strong>{result.items_created}</strong></div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── AutoMeasures ───────────────────────────────────────────────────────────────
function AutoMeasures() {
  const [text, setText] = useState('');
  const [preview, setPreview] = useState(null);
  const [editableItems, setEditableItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [showFormat, setShowFormat] = useState(false);

  const handlePreview = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await post('/automation/preview-measures', { text });
      setPreview(r.data);
      setEditableItems(r.data.items || []);
    } catch (e) {
      toast({ title: 'Erro', description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally { setLoading(false); }
  };

  const handleExecute = async () => {
    setLoading(true);
    try {
      const r = await post('/automation/execute-measures', { items: editableItems });
      setResult(r.data);
      setPreview(null);
      setText('');
      toast({ title: 'Sucesso!', description: `${r.data.processed} item(s) processados.` });
    } catch (e) {
      toast({ title: 'Erro', description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally { setLoading(false); }
  };

  const COLORS = ['AZUL','AMARELO','CINZA','LARANJA','ROXO','ROSA','VERDE'];
  const COLOR_HEX = { AZUL:'#3B82F6',AMARELO:'#EAB308',CINZA:'#6B7280',LARANJA:'#F97316',ROXO:'#8B5CF6',ROSA:'#EC4899',VERDE:'#22C55E' };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
          <Ruler className="w-4 h-4 text-purple-600" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Automação de Medidas</h3>
          <p className="text-xs text-gray-500">Cole as medidas → sistema preenche Identificação</p>
        </div>
      </div>

      <button onClick={() => setShowFormat(v => !v)}
        className="flex items-center gap-1 text-xs text-purple-600 hover:text-purple-700">
        {showFormat ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        Ver formato esperado
      </button>
      {showFormat && (
        <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-600 font-mono space-y-0.5">
          <p className="text-gray-400 mb-1"># Formato atual (será refinado):</p>
          <p>Cliente - Serviço 2.5x3.0</p>
          <p>Cliente - Tapete Ø1.5</p>
          <p>[PARCEIRO: DryClean]</p>
          <p>João - Tapete AZUL-224 2.0x3.0</p>
          <p>Maria - Tapete ROSA-112 1.5x2.0</p>
        </div>
      )}

      <textarea
        value={text}
        onChange={e => { setText(e.target.value); setPreview(null); setResult(null); }}
        placeholder="Cole aqui as medidas dos tapetes..."
        rows={8}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-purple-500 resize-none"
      />

      <button
        onClick={handlePreview}
        disabled={!text.trim() || loading}
        className="w-full py-2.5 bg-purple-600 text-white rounded-lg text-sm font-semibold hover:bg-purple-700 disabled:opacity-50 flex items-center justify-center gap-2"
      >
        {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
        Analisar Medidas
      </button>

      {/* Preview items */}
      {preview && editableItems.length > 0 && (
        <div className="border border-purple-200 rounded-xl p-3 space-y-3 bg-purple-50">
          <h4 className="text-sm font-semibold text-purple-900 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            {editableItems.length} item(s) detectados — confirme
          </h4>

          <div className="space-y-2 max-h-64 overflow-y-auto">
            {editableItems.map((item, i) => {
              const pl = item.partner_label;
              return (
                <div key={i} className="bg-white rounded-lg p-2.5 border border-purple-200 space-y-1.5">
                  <div className="grid grid-cols-2 gap-1.5">
                    <div>
                      <label className="block text-[10px] text-gray-500 mb-0.5">Cliente</label>
                      <input value={item.client_name || ''} onChange={e => setEditableItems(prev => prev.map((it,j)=>j===i?{...it,client_name:e.target.value}:it))}
                        className="w-full px-2 py-1 border border-gray-300 rounded text-xs" />
                    </div>
                    <div>
                      <label className="block text-[10px] text-gray-500 mb-0.5">Serviço</label>
                      <input value={item.service_name || ''} onChange={e => setEditableItems(prev => prev.map((it,j)=>j===i?{...it,service_name:e.target.value}:it))}
                        className="w-full px-2 py-1 border border-gray-300 rounded text-xs" />
                    </div>
                  </div>
                  <div className="grid grid-cols-4 gap-1.5 text-xs">
                    {['width','height','diameter','area_m2'].map(f => (
                      <div key={f}>
                        <label className="block text-[10px] text-gray-400 mb-0.5">{f}</label>
                        <input type="number" step="0.01" value={item[f]||''} onChange={e => setEditableItems(prev => prev.map((it,j)=>j===i?{...it,[f]:e.target.value?parseFloat(e.target.value):null}:it))}
                          className="w-full px-1.5 py-0.5 border border-gray-300 rounded text-[11px]" />
                      </div>
                    ))}
                  </div>
                  {pl && (
                    <div className="flex items-center gap-2 text-[10px]">
                      <span className="text-gray-500">Etiqueta:</span>
                      {pl.type === 'COLOR_NUM' ? (
                        <span className="font-bold" style={{color: COLOR_HEX[pl.color]||'#666'}}>
                          {pl.color}-{pl.number}
                        </span>
                      ) : (
                        <span className="text-gray-700">{pl.text}</span>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="flex gap-2">
            <button onClick={() => setPreview(null)}
              className="flex-1 py-2 rounded-lg border border-gray-300 text-sm text-gray-700">Cancelar</button>
            <button onClick={handleExecute} disabled={loading}
              className="flex-1 py-2 rounded-lg bg-green-600 text-white text-sm font-semibold hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2">
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Confirmar
            </button>
          </div>
        </div>
      )}

      {result && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-3 text-sm">
          <div className="font-semibold text-green-800 flex items-center gap-2 mb-2">
            <Check className="w-4 h-4" /> Processado!
          </div>
          <div className="text-xs text-green-700 space-y-0.5">
            {(result.results || []).map((r, i) => (
              <div key={i}>
                {r.status === 'created' ? `✚ Criado: ${r.budget_id}` :
                 r.status === 'updated' ? `✓ Atualizado: ${r.item_id}` :
                 `⚠ Ignorado: ${r.reason}`}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export function Automations() {
  const [tab, setTab] = useState('budget');

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-xl flex items-center justify-center">
          <Zap className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Automações</h1>
          <p className="text-xs text-gray-500">Insira dados em texto — o sistema cria tudo automaticamente</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 bg-gray-100 rounded-xl p-1">
        <button
          onClick={() => setTab('budget')}
          className={`flex-1 py-2 text-sm font-medium rounded-lg transition ${tab === 'budget' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600'}`}
        >
          Orçamento
        </button>
        <button
          onClick={() => setTab('measures')}
          className={`flex-1 py-2 text-sm font-medium rounded-lg transition ${tab === 'measures' ? 'bg-white text-purple-600 shadow-sm' : 'text-gray-600'}`}
        >
          Medidas
        </button>
      </div>

      {tab === 'budget'   && <AutoBudget />}
      {tab === 'measures' && <AutoMeasures />}
    </div>
  );
}

export default Automations;
