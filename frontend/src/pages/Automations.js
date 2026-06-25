import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Zap, FileText, Ruler, Play, Check, RefreshCw, AlertTriangle, ChevronDown, ChevronUp, MapPin, Building2, Loader2, MessageCircle, Send } from 'lucide-react';
import api, { placesApi } from '../services/api';
import { toast } from '../hooks/use-toast';

import { BACKEND_URL as BACKEND } from '../lib/backendUrl';
const post = (path, body) => api.post(path, body);

// ── AddressAutocomplete (mesma lógica do Clients.js) ──────────────────────────
function AddressAutocomplete({ value, onSelect, placeholder }) {
  const [query, setQuery] = useState(value?.full_address || '');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debRef = useRef(null);
  const boxRef = useRef(null);
  const skipSearchRef = useRef(false);

  useEffect(() => {
    if (debRef.current) clearTimeout(debRef.current);
    if (skipSearchRef.current) { skipSearchRef.current = false; setResults([]); setOpen(false); return; }
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
    skipSearchRef.current = true;
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
  const [addressObj, setAddressObj] = useState(null);
  const [complement, setComplement] = useState('');
  const [showFormat, setShowFormat] = useState(false);
  const [sendWhats, setSendWhats] = useState(true);
  const [sendPdf, setSendPdf] = useState(false);
  const [sending, setSending] = useState(false);

  const handlePreview = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await post('/automation/preview-budget', { text });
      setPreview(r.data);
      setEditableItems(r.data.items || []);
      setAddressObj(null); // reset endereço para nova busca
      // Pré-preenche o complemento com o endereço colado (preserva condomínio/qd/lt
      // que o Google descarta ao confirmar a rua)
      setComplement(r.data.client_address || '');
    } catch (e) {
      toast({ title: 'Erro', description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally { setLoading(false); }
  };

  // Recalcula o valor do item conforme tipo de medida (área, diâmetro ou unitário)
  const AREA_TYPES = ['AREA_DE_TAPETE', 'AREA_PERSIANA', 'CARPETE_TAPETE_LOCAL'];
  const recalcItem = (it) => {
    const price = Number(it.unit_price || it.matched?.sale_price || 0);
    const mt = it.measure_type;
    if (mt === 'TAPETE_REDONDO_DIAMETRO') {
      const d = Number(it.diameter || 0);
      const area = Math.PI * Math.pow(d / 2, 2);
      return { ...it, area_m2: +area.toFixed(4), value: +(area * price).toFixed(2) };
    }
    if (AREA_TYPES.includes(mt)) {
      const area = (Number(it.width || 0) * Number(it.height || 0)) || Number(it.area_m2 || 0);
      return { ...it, area_m2: +area.toFixed(4), value: +(area * price).toFixed(2) };
    }
    if (it.needs_quantity) {
      const qty = Number(it.quantity || 1);
      return { ...it, value: +(price * qty).toFixed(2) };
    }
    return it;
  };
  const patchItem = (i, changes) =>
    setEditableItems(prev => prev.map((it, j) => j === i ? recalcItem({ ...it, ...changes }) : it));

  const handleExecute = async () => {
    if (!preview) return;
    setLoading(true);
    try {
      const r = await post('/automation/execute-budget', {
        ...preview,
        items: editableItems,
        client_address_obj: addressObj ? { ...addressObj, complement } : null,
        complement, // complemento (condomínio/qd/lt) — preservado mesmo sem busca de endereço
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
          <p className="text-gray-400 mb-1"># Uma linha por dado (ordem livre). O sistema identifica sozinho:</p>
          <p>Nome do Cliente <span className="text-gray-400">(1ª linha)</span></p>
          <p>Telefone <span className="text-gray-400">(detectado pelos dígitos)</span></p>
          <p>Sofá 3 lugares <span className="text-gray-400">(item → preço do catálogo)</span></p>
          <p>Tapete 2x3 <span className="text-gray-400">(item por medida)</span></p>
          <p>Endereço <span className="text-gray-400">(opcional — pode adicionar depois)</span></p>
          <p>obs: Observações opcionais</p>
          <p className="text-gray-400 mt-1"># O valor é puxado do catálogo; você pode editar antes de criar.</p>
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
              <div className="mt-1.5">
                <label className="text-[10px] text-gray-500">Complemento (condomínio, quadra, lote, apto, bloco…)</label>
                <input
                  value={complement}
                  onChange={e => setComplement(e.target.value)}
                  placeholder="Ex: Cond. Belvedere 1, qd 16 lt 06, apto 101"
                  className="w-full mt-0.5 px-2 py-1.5 border border-gray-300 rounded-lg text-xs"
                />
              </div>
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
              {editableItems.map((item, i) => {
                const m = item.matched;
                const mt = item.measure_type;
                const isArea = ['AREA_DE_TAPETE', 'AREA_PERSIANA', 'CARPETE_TAPETE_LOCAL'].includes(mt);
                const isDiameter = mt === 'TAPETE_REDONDO_DIAMETRO';
                const numCls = "w-14 text-xs px-1.5 py-1 border border-gray-300 rounded";
                return (
                <div key={i} className="mb-2 pb-2 border-b border-gray-100 last:border-0">
                  <div className="flex items-center gap-1">
                    <input
                      className="flex-1 text-xs px-1.5 py-0.5 border border-gray-300 rounded min-w-0"
                      value={item.service_name}
                      onChange={e => setEditableItems(prev => prev.map((it, j) => j===i ? {...it, service_name: e.target.value} : it))}
                    />
                    <input
                      type="number" className="w-16 text-xs px-1.5 py-0.5 border border-gray-300 rounded font-semibold"
                      value={item.value}
                      onFocus={e => e.target.select()}
                      onChange={e => setEditableItems(prev => prev.map((it, j) => j===i ? {...it, value: parseFloat(e.target.value)||0} : it))}
                    />
                  </div>

                  {/* Campos de medida / quantidade */}
                  {(isArea || isDiameter) && (
                    <div className="mt-1 flex items-center gap-1 flex-wrap">
                      {isArea && <>
                        <input type="number" step="0.01" placeholder="larg." className={numCls}
                          value={item.width ?? ''} onFocus={e => e.target.select()}
                          onChange={e => patchItem(i, { width: parseFloat(e.target.value) || 0 })} />
                        <span className="text-gray-400 text-xs">×</span>
                        <input type="number" step="0.01" placeholder="alt." className={numCls}
                          value={item.height ?? ''} onFocus={e => e.target.select()}
                          onChange={e => patchItem(i, { height: parseFloat(e.target.value) || 0 })} />
                        <span className="text-[10px] text-gray-500">= {Number(item.area_m2 || 0).toFixed(2)}m²</span>
                      </>}
                      {isDiameter && <>
                        <span className="text-[10px] text-gray-500">Ø</span>
                        <input type="number" step="0.01" placeholder="diâm." className={numCls}
                          value={item.diameter ?? ''} onFocus={e => e.target.select()}
                          onChange={e => patchItem(i, { diameter: parseFloat(e.target.value) || 0 })} />
                        <span className="text-[10px] text-gray-500">= {Number(item.area_m2 || 0).toFixed(2)}m²</span>
                      </>}
                      <span className="text-[10px] text-gray-400">× R$ {item.unit_price || m?.sale_price}/m²</span>
                    </div>
                  )}
                  {item.needs_quantity && (
                    <div className="mt-1 flex items-center gap-1">
                      <span className="text-[10px] text-gray-500">Qtd:</span>
                      <input type="number" min="1" className={numCls}
                        value={item.quantity ?? 1} onFocus={e => e.target.select()}
                        onChange={e => patchItem(i, { quantity: parseInt(e.target.value) || 1 })} />
                      <span className="text-[10px] text-gray-400">× R$ {item.unit_price || m?.sale_price}/un</span>
                    </div>
                  )}

                  {m ? (
                    <div className={`mt-1 text-[10px] flex items-center gap-1 flex-wrap ${m.low_confidence ? 'text-amber-600' : 'text-emerald-600'}`}>
                      <span>{m.low_confidence ? '⚠️' : '✓'} {m.service_name}</span>
                      {item.needs_measure && <span className="bg-amber-50 text-amber-600 px-1 rounded">preencha a medida acima</span>}
                      {m.low_confidence && <span className="text-amber-500">(confira o serviço)</span>}
                    </div>
                  ) : (
                    <div className="mt-0.5 text-[10px] text-gray-400">sem correspondência no catálogo — defina o valor manualmente</div>
                  )}
                </div>
                );
              })}
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
        <div className="bg-green-50 border border-green-200 rounded-xl p-3 space-y-3 text-sm">
          <div className="font-semibold text-green-800 flex items-center gap-2">
            <Check className="w-4 h-4" /> Criado com sucesso!
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs text-green-700">
            <div>Cliente: <strong>{result.client_id}</strong> {result.client_created ? '(novo)' : '(existente)'}</div>
            <div>Orçamento: <strong>{result.budget_id}</strong></div>
            <div>Itens: <strong>{result.items_created}</strong></div>
          </div>

          {/* Envio */}
          <div className="border-t border-green-200 pt-3 space-y-2">
            <p className="text-xs text-green-700">
              📄 O link do PDF já estará incluído na mensagem de WhatsApp automaticamente.
            </p>
            <div className="flex gap-2">
              <button
                disabled={sending}
                onClick={async () => {
                  setSending(true);
                  try {
                    const r = await api.get(`/budgets/${result.budget_id}/whatsapp`);
                    if (r.data?.whatsapp_url) window.open(r.data.whatsapp_url, '_blank');
                  } catch (e) {
                    toast({ title: 'Erro ao gerar mensagem', description: e.message, variant: 'destructive' });
                  } finally { setSending(false); }
                }}
                className="flex-1 py-2 rounded-xl bg-green-600 text-white text-sm font-semibold hover:bg-green-700 disabled:opacity-40 flex items-center justify-center gap-2"
              >
                {sending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <MessageCircle className="w-4 h-4" />}
                Enviar para o cliente
              </button>
              <button
                onClick={() => { setResult(null); setText(''); setSendWhats(true); setSendPdf(false); }}
                className="px-4 py-2 rounded-xl border border-green-300 text-green-700 text-sm hover:bg-green-100"
              >
                Novo
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const COLOR_HEX = { AZUL:'#3B82F6', AMARELO:'#EAB308', CINZA:'#6B7280', LARANJA:'#F97316', ROXO:'#8B5CF6', ROSA:'#EC4899', VERDE:'#22C55E' };

function MeasureTag({ item }) {
  const pl = item.partner_label;
  if (item.diameter)
    return <span className="text-[10px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-mono">Ø {item.diameter}m · {item.area_m2}m²</span>;
  if (item.width)
    return <span className="text-[10px] bg-gray-50 text-gray-700 px-1.5 py-0.5 rounded font-mono">{item.width}×{item.height}m · {item.area_m2}m²</span>;
  return null;
}

function LabelTag({ pl }) {
  if (!pl) return null;
  if (pl.type === 'COLOR_NUM')
    return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border" style={{color: COLOR_HEX[pl.color]||'#666', borderColor: COLOR_HEX[pl.color]||'#ccc'}}>{pl.color}-{pl.number}</span>;
  return null;
}

// ── AutoMeasures ───────────────────────────────────────────────────────────────
function AutoMeasures() {
  const [text, setText] = useState('');
  const [preview, setPreview] = useState(null);
  const [editableItems, setEditableItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  // dados extras por cliente novo: { [clientName]: { name, phone, address, skip } }
  const [clientExtras, setClientExtras] = useState({});

  const setExtra = (clientName, patch) =>
    setClientExtras(prev => ({ ...prev, [clientName]: { ...(prev[clientName] || {}), ...patch } }));

  const handlePreview = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setResult(null);
    setClientExtras({});
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
      const r = await post('/automation/execute-measures', { items: editableItems, client_extras: clientExtras });
      setResult(r.data);
      setPreview(null);
      setText('');
      setClientExtras({});
      toast({ title: 'Sucesso!', description: `${r.data.processed} tapete(s) lançados.` });
    } catch (e) {
      toast({ title: 'Erro', description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally { setLoading(false); }
  };

  const updateItem = (i, patch) =>
    setEditableItems(prev => prev.map((it, j) => j === i ? { ...it, ...patch } : it));

  const removeItem = (i) =>
    setEditableItems(prev => prev.filter((_, j) => j !== i));

  // Detecta itens com mesmas dimensões por cliente (aviso de possível duplicata)
  const dimsSig = (it) => it.diameter ? `d${it.diameter}` : `${it.width}x${it.height}`;
  const dupeSigs = new Set();
  const warnSigs = new Set();
  editableItems.forEach(it => {
    const sig = `${it.client_name}|${dimsSig(it)}`;
    if (dupeSigs.has(sig)) warnSigs.add(sig);
    dupeSigs.add(sig);
  });

  // Agrupa itens por cliente para exibição
  const grouped = editableItems.reduce((acc, item, idx) => {
    const key = item.client_name || '(sem nome)';
    if (!acc[key]) acc[key] = { items: [], exists: item.client_exists, is_partner: item.is_partner, is_ambiguous: item.is_ambiguous };
    acc[key].items.push({ ...item, _idx: idx });
    return acc;
  }, {});

  const totalArea = editableItems.reduce((s, it) => s + (it.area_m2 || 0), 0);
  const novosClientes = Object.values(grouped).filter(g => !g.exists && !g.is_partner).length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
          <Ruler className="w-4 h-4 text-purple-600" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Automação de Medidas</h3>
          <p className="text-xs text-gray-500">Cole a mensagem do WhatsApp — o sistema identifica tudo</p>
        </div>
      </div>

      <textarea
        value={text}
        onChange={e => { setText(e.target.value); setPreview(null); setResult(null); }}
        placeholder="Cole aqui as mensagens do WhatsApp com as medidas dos tapetes..."
        rows={9}
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

      {/* Preview agrupado por cliente */}
      {preview && editableItems.length > 0 && (
        <div className="border border-purple-200 rounded-xl p-3 space-y-3 bg-purple-50">

          {/* Cabeçalho resumo */}
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-purple-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              {editableItems.length} tapetes · {Object.keys(grouped).length} clientes
            </h4>
            <div className="flex gap-2 text-[10px]">
              {novosClientes > 0 && (
                <span className="bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">
                  {novosClientes} novo{novosClientes > 1 ? 's' : ''}
                </span>
              )}
              <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">
                {totalArea.toFixed(2)} m² total
              </span>
            </div>
          </div>

          {/* Grupos por cliente */}
          <div className="space-y-2 max-h-[28rem] overflow-y-auto pr-0.5">
            {Object.entries(grouped).map(([clientName, group]) => (
              <div key={clientName} className="bg-white rounded-lg border border-purple-100 overflow-hidden">

                {/* Header do cliente */}
                {(() => {
                  const isNew = !group.exists && !group.is_partner;
                  const extra = clientExtras[clientName] || {};
                  const skipping = extra.skip;
                  return (
                    <>
                      <div className={`flex items-center justify-between px-3 py-2 ${group.is_partner ? 'bg-orange-50' : group.exists ? 'bg-green-50' : 'bg-amber-50'}`}>
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-xs font-semibold text-gray-800 truncate">{clientName}</span>
                          {group.is_ambiguous && (
                            <span className="text-[10px] bg-red-100 text-red-600 px-1.5 py-0.5 rounded-full shrink-0">⚠ Nome ambíguo</span>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <span className="text-[10px] text-gray-500">{group.items.length} tapete{group.items.length > 1 ? 's' : ''}</span>
                          {group.is_partner
                            ? <span className="text-[10px] bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded-full font-medium">Parceiro</span>
                            : group.exists
                              ? group.active_items?.length > 0
                                ? <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full font-medium">↻ Atualiza orçamento</span>
                                : <span className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full font-medium">Cadastrado</span>
                              : skipping
                                ? <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full font-medium">Preencher depois</span>
                                : <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full font-medium">Novo cliente</span>
                          }
                        </div>
                      </div>

                      {/* Painel de cadastro para clientes novos */}
                      {isNew && !skipping && (
                        <div className="px-3 py-2 bg-amber-50 border-b border-amber-100 space-y-2">
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="block text-[10px] text-gray-500 mb-0.5">Nome completo</label>
                              <input
                                value={extra.name ?? clientName}
                                onChange={e => setExtra(clientName, { name: e.target.value })}
                                className="w-full px-2 py-1 border border-amber-200 rounded text-xs bg-white"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] text-gray-500 mb-0.5">Telefone</label>
                              <input
                                value={extra.phone || ''}
                                onChange={e => setExtra(clientName, { phone: e.target.value })}
                                placeholder="(65) 99999-0000"
                                className="w-full px-2 py-1 border border-amber-200 rounded text-xs bg-white"
                              />
                            </div>
                          </div>
                          <div>
                            <label className="block text-[10px] text-gray-500 mb-0.5">Endereço</label>
                            <AddressAutocomplete
                              value={extra.address || null}
                              onSelect={addr => setExtra(clientName, { address: addr })}
                              placeholder="Buscar endereço..."
                            />
                            {extra.address?.latitude && (
                              <span className="text-[10px] text-green-600 mt-0.5 block">
                                ✓ {extra.address.full_address}
                              </span>
                            )}
                          </div>
                          <div>
                            <label className="block text-[10px] text-gray-500 mb-0.5">Complemento</label>
                            <input
                              value={extra.complement || ''}
                              onChange={e => setExtra(clientName, { complement: e.target.value })}
                              placeholder="Apto 42, Bloco B, Casa 3..."
                              className="w-full px-2 py-1 border border-amber-200 rounded text-xs bg-white"
                            />
                          </div>
                          <div>
                            <label className="block text-[10px] text-gray-500 mb-0.5">Observações</label>
                            <textarea
                              value={extra.observations || ''}
                              onChange={e => setExtra(clientName, { observations: e.target.value })}
                              placeholder="Ex: mora no Goiabeiras, portão azul, ligar antes..."
                              rows={2}
                              className="w-full px-2 py-1 border border-amber-200 rounded text-xs bg-white resize-none"
                            />
                          </div>
                          <button
                            onClick={() => setExtra(clientName, { skip: true })}
                            className="text-[10px] text-gray-400 hover:text-gray-600 underline"
                          >
                            Preencher depois (só salvar o nome)
                          </button>
                        </div>
                      )}

                      {/* Botão para desfazer "preencher depois" */}
                      {isNew && skipping && (
                        <div className="px-3 py-1.5 bg-gray-50 border-b border-gray-100">
                          <button
                            onClick={() => setExtra(clientName, { skip: false })}
                            className="text-[10px] text-amber-600 hover:text-amber-700 underline"
                          >
                            Preencher dados agora
                          </button>
                        </div>
                      )}
                    </>
                  );
                })()}

                {/* Linhas de tapetes */}
                <div className="divide-y divide-gray-50">
                  {group.items.map((item) => {
                    const idx = item._idx;
                    const hasMultipleActive = (item.active_items?.length || 0) > 1;
                    const isDupeSig = warnSigs.has(`${item.client_name}|${dimsSig(item)}`);
                    return (
                      <div key={idx} className={`flex flex-col gap-1 px-3 py-1.5 ${isDupeSig ? 'bg-yellow-50' : ''}`}>
                        <div className="flex items-center gap-2">
                        <MeasureTag item={item} />
                        <LabelTag pl={item.partner_label} />
                        {isDupeSig && (
                          <span className="text-[10px] bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded-full shrink-0">⚠ mesmo tamanho</span>
                        )}
                        {/* Indicador de ação */}
                        {item.action === 'update' && item.target_item_id && !hasMultipleActive && (
                          <span className="text-[10px] text-blue-600 ml-auto shrink-0">↻ {item.target_item_id}</span>
                        )}
                        {item.action === 'create' && item.client_exists && (
                          <span className="text-[10px] text-amber-600 shrink-0">+ novo item</span>
                        )}
                        {/* Botão remover */}
                        <button onClick={() => removeItem(idx)}
                          className="ml-auto text-gray-300 hover:text-red-400 text-xs shrink-0 px-1"
                          title="Remover este tapete">✕</button>
                        {/* Edição inline de medidas */}
                        <div className="flex items-center gap-1 shrink-0">
                          {item.diameter != null ? (
                            <div className="flex items-center gap-1">
                              <span className="text-[10px] text-gray-400">Ø</span>
                              <input type="number" step="0.01" value={item.diameter || ''}
                                onChange={e => { const v = parseFloat(e.target.value)||0; updateItem(idx, {diameter: v, area_m2: parseFloat((Math.PI*(v/2)**2).toFixed(4))}); }}
                                className="w-14 px-1 py-0.5 border border-gray-200 rounded text-[11px] text-center" />
                              <span className="text-[10px] text-gray-400">m</span>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1">
                              <input type="number" step="0.01" value={item.width || ''}
                                onChange={e => { const w = parseFloat(e.target.value)||0; updateItem(idx, {width: w, area_m2: parseFloat((w*(item.height||0)).toFixed(4))}); }}
                                className="w-12 px-1 py-0.5 border border-gray-200 rounded text-[11px] text-center" />
                              <span className="text-[10px] text-gray-400">×</span>
                              <input type="number" step="0.01" value={item.height || ''}
                                onChange={e => { const h = parseFloat(e.target.value)||0; updateItem(idx, {height: h, area_m2: parseFloat(((item.width||0)*h).toFixed(4))}); }}
                                className="w-12 px-1 py-0.5 border border-gray-200 rounded text-[11px] text-center" />
                              <span className="text-[10px] text-gray-400">m</span>
                            </div>
                          )}
                        </div>
                        </div>
                        {/* Seletor de status do item */}
                        <div className="flex items-center gap-2 pb-0.5">
                          <span className="text-[10px] text-gray-400 shrink-0">Status:</span>
                          <select
                            value={item.status || 'CLIENTE_TROUXE'}
                            onChange={e => updateItem(idx, { status: e.target.value })}
                            className="flex-1 text-[10px] border border-gray-200 rounded px-1 py-0.5 bg-white"
                          >
                            <option value="CLIENTE_TROUXE">Cliente trouxe</option>
                            <option value="COLETADO">Coletado</option>
                            <option value="EM_LAVAGEM">Em lavagem</option>
                            <option value="RETIRAR">Aguardando retirada</option>
                            <option value="AGUARDANDO_ENTREGA">Aguardando entrega</option>
                            <option value="ENTREGAR">Pronto para entregar</option>
                          </select>
                        </div>
                        {/* Seletor de item quando há múltiplos ativos sem medida */}
                        {hasMultipleActive && (
                          <div className="flex items-center gap-2 pb-0.5">
                            <span className="text-[10px] text-gray-400 shrink-0">Atualizar:</span>
                            <select
                              value={item.target_item_id || ''}
                              onChange={e => updateItem(idx, {
                                target_item_id: e.target.value || null,
                                action: e.target.value ? 'update' : 'create'
                              })}
                              className="flex-1 text-[10px] border border-gray-200 rounded px-1 py-0.5 bg-white"
                            >
                              <option value="">+ criar novo item</option>
                              {(item.active_items || []).map(ai => (
                                <option key={ai.item_id} value={ai.item_id}>
                                  {ai.item_id} — {ai.status}{ai.width ? ` (${ai.width}×${ai.height}m)` : ai.diameter ? ` (Ø${ai.diameter}m)` : ' (sem medida)'}
                                </option>
                              ))}
                            </select>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          <div className="flex gap-2 pt-1">
            <button onClick={() => setPreview(null)}
              className="flex-1 py-2 rounded-lg border border-gray-300 text-sm text-gray-700 hover:bg-gray-50">
              Cancelar
            </button>
            <button onClick={handleExecute} disabled={loading}
              className="flex-1 py-2 rounded-lg bg-green-600 text-white text-sm font-semibold hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2">
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Confirmar e Lançar
            </button>
          </div>
        </div>
      )}

      {result && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-3 text-sm space-y-2">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="font-semibold text-green-800 flex items-center gap-1.5">
              <Check className="w-4 h-4" /> {result.processed} lançado{result.processed !== 1 ? 's' : ''}
            </span>
            {result.duplicates > 0 && (
              <span className="text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full text-xs font-medium">
                {result.duplicates} duplicata{result.duplicates !== 1 ? 's' : ''} ignorada{result.duplicates !== 1 ? 's' : ''}
              </span>
            )}
            {result.skipped > 0 && (
              <span className="text-gray-500 text-xs">{result.skipped} sem nome</span>
            )}
          </div>
          <div className="text-xs space-y-0.5 max-h-40 overflow-y-auto">
            {(result.results || []).map((r, i) => (
              <div key={i} className={
                r.status === 'created'   ? 'text-green-700' :
                r.status === 'duplicate' ? 'text-amber-600' : 'text-gray-400'
              }>
                {r.status === 'created'   ? `✚ ${r.budget_id}` :
                 r.status === 'duplicate' ? `↩ ${r.reason}` :
                 `— ${r.reason}`}
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
