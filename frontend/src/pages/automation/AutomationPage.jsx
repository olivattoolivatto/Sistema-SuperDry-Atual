import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Wand2, Send, Loader2, MapPin, Building2, User, Phone,
  Calendar, Clock, Plus, Trash2, ChevronDown, ChevronUp,
  CheckCircle2, AlertCircle, RefreshCw, Search, UserPlus,
  DollarSign, StickyNote, Zap, ArrowRightLeft, CalendarCheck,
} from 'lucide-react';
import api, { placesApi, clientsApi } from '../../services/api';
import { toast } from '../../hooks/use-toast';

// ── helpers ───────────────────────────────────────────────────────────────────
const post = (path, body) => api.post(path, body);
const fmt = (v) =>
  v != null && !isNaN(v)
    ? Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2 })
    : '—';

// ── AddressAutocomplete ───────────────────────────────────────────────────────
function AddressAutocomplete({ value, onSelect, placeholder }) {
  const [query, setQuery] = useState(value?.full_address || '');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debRef = useRef(null);
  const boxRef = useRef(null);
  const skipRef = useRef(false);

  useEffect(() => {
    if (value?.full_address && value.full_address !== query) setQuery(value.full_address);
  }, [value?.full_address]); // eslint-disable-line

  useEffect(() => {
    if (debRef.current) clearTimeout(debRef.current);
    if (skipRef.current) { skipRef.current = false; setResults([]); setOpen(false); return; }
    if (!query || query.length < 3) { setResults([]); setOpen(false); return; }
    debRef.current = setTimeout(async () => {
      try { setLoading(true); const r = await placesApi.search(query); setResults(r.data?.results || []); setOpen(true); }
      catch { setResults([]); } finally { setLoading(false); }
    }, 350);
  }, [query]);

  useEffect(() => {
    const h = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  const choose = async (p) => {
    setOpen(false); skipRef.current = true; setQuery(p.description || '');
    let lat = p?.geometry?.location?.lat, lng = p?.geometry?.location?.lng;
    let neighborhood = p?.neighborhood, city = p?.city, state = p?.state;
    let fullAddress = p.description || '';
    if ((!lat || !lng) && p.place_id) {
      try {
        const det = await placesApi.getDetails(p.place_id);
        const d = det.data?.details?.result || det.data?.details || {};
        fullAddress = d.formatted_address || fullAddress;
        const geo = d.geometry?.location;
        if (geo) { lat = geo.lat; lng = geo.lng; }
        (d.address_components || []).forEach(c => {
          const t = c.types || [];
          if (t.includes('sublocality') || t.includes('neighborhood')) neighborhood = c.long_name;
          if (t.includes('administrative_area_level_2') || t.includes('locality')) city = c.long_name;
          if (t.includes('administrative_area_level_1')) state = c.short_name || c.long_name;
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
          placeholder={placeholder || 'Buscar endereço…'}
          className="w-full pl-8 pr-8 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" />
        {loading && <Loader2 className="w-3.5 h-3.5 absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 animate-spin" />}
      </div>
      {open && results.length > 0 && (
        <ul className="absolute z-40 mt-1 w-full max-h-60 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-lg">
          {results.slice(0, 8).map(p => (
            <li key={p.place_id || p.description} onClick={() => choose(p)}
              className="px-3 py-2 hover:bg-blue-50 cursor-pointer text-sm border-b border-gray-100 last:border-0 flex items-start gap-2">
              {p.source === 'text_search'
                ? <Building2 className="w-3.5 h-3.5 text-blue-500 mt-0.5 shrink-0" />
                : <MapPin className="w-3.5 h-3.5 text-gray-400 mt-0.5 shrink-0" />}
              <div className="min-w-0">
                <div className="font-medium text-gray-900 truncate text-xs">{p.structured_formatting?.main_text || p.description}</div>
                <div className="text-[10px] text-gray-500 truncate">{p.structured_formatting?.secondary_text || ''}</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── ClientSearch ──────────────────────────────────────────────────────────────
function ClientSearch({ value, onChange }) {
  const [q, setQ] = useState(value || '');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debRef = useRef(null);
  const boxRef = useRef(null);

  useEffect(() => {
    if (debRef.current) clearTimeout(debRef.current);
    if (!q || q.length < 2) { setResults([]); setOpen(false); return; }
    debRef.current = setTimeout(async () => {
      try { setLoading(true); const r = await clientsApi.getAll({ search: q, limit: 8 }); setResults(r.data?.clients || []); setOpen(true); }
      catch { setResults([]); } finally { setLoading(false); }
    }, 300);
  }, [q]);

  useEffect(() => {
    const h = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  return (
    <div className="relative" ref={boxRef}>
      <div className="relative">
        <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
        <input value={q} onChange={e => { setQ(e.target.value); onChange(null, e.target.value); }}
          placeholder="Buscar cliente cadastrado…"
          className="w-full pl-8 pr-8 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" />
        {loading && <Loader2 className="w-3.5 h-3.5 absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 animate-spin" />}
      </div>
      {open && results.length > 0 && (
        <ul className="absolute z-40 mt-1 w-full max-h-52 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-lg">
          {results.map(c => (
            <li key={c.id} onClick={() => { setQ(c.name); setOpen(false); onChange(c, c.name); }}
              className="px-3 py-2 hover:bg-blue-50 cursor-pointer text-sm border-b border-gray-100 last:border-0">
              <div className="font-medium text-gray-900">{c.name}</div>
              <div className="text-[11px] text-gray-500">{c.phone_primary} · {c.address?.full_address || ''}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── ItemRow ───────────────────────────────────────────────────────────────────
function ItemRow({ item, idx, onChange, onRemove }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 cursor-pointer"
        onClick={() => setOpen(o => !o)}>
        <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-[11px] font-bold flex items-center justify-center shrink-0">{idx + 1}</span>
        <span className="flex-1 text-sm font-medium text-gray-800 truncate">{item.service_name || 'Item sem nome'}</span>
        <span className="text-sm font-semibold text-blue-700">R$ {fmt(item.value)}</span>
        <button onClick={e => { e.stopPropagation(); onRemove(idx); }}
          className="p-1 hover:bg-red-100 rounded text-red-400 hover:text-red-600">
          <Trash2 className="w-3.5 h-3.5" />
        </button>
        {open ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </div>
      {open && (
        <div className="px-3 py-3 space-y-3 bg-white border-t border-gray-100">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Serviço</label>
            <input value={item.service_name || ''} onChange={e => onChange(idx, { service_name: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500" />
            {item.matched_service && (
              <p className="text-[11px] text-green-600 mt-0.5">
                ✓ Match: {item.matched_service.name} (score {item.matched_service.match_score?.toFixed(1)})
              </p>
            )}
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Qtd</label>
              <input type="number" min="1" value={item.quantity || 1}
                onChange={e => onChange(idx, { quantity: Number(e.target.value) })}
                className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Preço unit. (R$)</label>
              <input type="number" step="0.01" value={item.unit_price || item.value || ''}
                onChange={e => onChange(idx, { unit_price: Number(e.target.value) })}
                className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Total (R$)</label>
              <input type="number" step="0.01" value={item.value || ''}
                onChange={e => onChange(idx, { value: Number(e.target.value) })}
                className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          {(item.width || item.height || item.diameter || item.area_m2) && (
            <div className="text-[11px] text-gray-500 bg-gray-50 rounded px-2 py-1">
              {item.width && item.height ? `${item.width}m × ${item.height}m = ` : ''}
              {item.diameter ? `Ø ${item.diameter}m = ` : ''}
              {item.area_m2 ? `${item.area_m2} m²` : ''}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export function AutomationPage() {
  // Painel esquerdo
  const [text, setText] = useState('');
  const [interpreting, setInterpreting] = useState(false);
  const [interpreted, setInterpreted] = useState(null); // resultado bruto da IA

  // Painel direito — formulário
  const [clientObj, setClientObj] = useState(null);  // cliente encontrado
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [addressObj, setAddressObj] = useState(null);
  const [complement, setComplement] = useState('');
  // Endereço de execução (diferente do cliente)
  const [diffExecAddr, setDiffExecAddr] = useState(false);
  const [execAddrObj, setExecAddrObj] = useState(null);
  const [execComplement, setExecComplement] = useState('');
  const [schedDate, setSchedDate] = useState('');
  const [schedTime, setSchedTime] = useState('');
  const [items, setItems] = useState([]);
  const [totalPix, setTotalPix] = useState('');
  const [totalCash, setTotalCash] = useState('');
  const [notes, setNotes] = useState('');

  // Ações
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState(null);

  // ── Interpretar mensagem ──────────────────────────────────────────────────
  const handleInterpret = async () => {
    if (!text.trim()) return;
    setInterpreting(true);
    setInterpreted(null);
    try {
      const r = await post('/automation/interpret-message', { text });
      const d = r.data;
      setInterpreted(d);
      // preenche o formulário automaticamente
      applyResult(d);
    } catch (e) {
      toast({ title: 'Erro ao interpretar', description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally {
      setInterpreting(false);
    }
  };

  const applyResult = (d) => {
    setName(d.client_name || '');
    setPhone(d.phone || '');
    setComplement(d.complement || '');
    setSchedDate(d.scheduled_date || '');
    setSchedTime(d.scheduled_time || '');
    setItems((d.items || []).map(it => ({ ...it, quantity: it.quantity || 1 })));
    setTotalPix(d.total_pix != null ? String(d.total_pix) : '');
    setTotalCash(d.total_cash != null ? String(d.total_cash) : '');
    setNotes(d.notes || '');
    // endereço: só pre-preenche o texto; usuário confirma via autocomplete
    if (d.address) {
      setAddressObj({ full_address: d.address, neighborhood: '', city: '', state: '', latitude: null, longitude: null });
    }
  };

  // ── Itens ─────────────────────────────────────────────────────────────────
  const patchItem = (idx, changes) =>
    setItems(prev => prev.map((it, i) => i === idx ? { ...it, ...changes } : it));
  const removeItem = (idx) => setItems(prev => prev.filter((_, i) => i !== idx));
  const addItem = () => setItems(prev => [...prev, { service_name: '', value: 0, quantity: 1 }]);

  // Total calculado
  const calcTotal = items.reduce((acc, it) => acc + Number(it.value || 0), 0);

  // ── Salvar ────────────────────────────────────────────────────────────────
  const handleSave = async (launchAgenda = false) => {
    if (!name.trim()) { toast({ title: 'Nome do cliente é obrigatório', variant: 'destructive' }); return; }
    if (items.length === 0) { toast({ title: 'Adicione pelo menos um item', variant: 'destructive' }); return; }
    if (launchAgenda && !schedDate) {
      toast({ title: 'Informe a data do serviço para lançar na agenda', variant: 'destructive' }); return;
    }
    setSaving(true);
    try {
      const payload = {
        client_id: clientObj?.id || null,
        client_name: name,
        client_phone: phone,
        client_address: addressObj?.full_address || interpreted?.address || '',
        client_address_obj: addressObj ? { ...addressObj, complement } : null,
        complement,
        // endereço de execução (diferente do cliente)
        execution_address: diffExecAddr ? (execAddrObj?.full_address || '') : null,
        execution_address_obj: diffExecAddr ? (execAddrObj ? { ...execAddrObj, complement: execComplement } : null) : null,
        execution_complement: diffExecAddr ? execComplement : null,
        scheduled_date: schedDate || null,
        scheduled_time: schedTime || null,
        items: items.map(it => ({
          service_name: it.service_name,
          value: Number(it.value || 0),
          unit_price: Number(it.unit_price || it.value || 0),
          quantity: Number(it.quantity || 1),
          width: it.width || null,
          height: it.height || null,
          diameter: it.diameter || null,
          area_m2: it.area_m2 || null,
          matched_service_id: it.matched_service?.id || null,
        })),
        notes,
        origin: 'AUTOMACAO',
        launch_agenda: launchAgenda,
      };
      const r = await post('/automation/execute-budget', payload);
      const d = r.data;
      setResult(d);
      const agendaMsg = launchAgenda
        ? (d.agenda_error
            ? ` (⚠️ Agenda: ${d.agenda_error})`
            : ' e lançado na agenda ✅')
        : '';
      toast({
        title: '✅ Criado com sucesso!',
        description: `Orçamento ${d.budget_id} criado${agendaMsg}.`,
      });
      // limpa formulário
      setText(''); setInterpreted(null); setName(''); setPhone(''); setAddressObj(null);
      setComplement(''); setDiffExecAddr(false); setExecAddrObj(null); setExecComplement('');
      setSchedDate(''); setSchedTime(''); setItems([]); setNotes('');
      setTotalPix(''); setTotalCash('');
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-full min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3">
        <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
          <Wand2 className="w-4 h-4 text-purple-600" />
        </div>
        <div>
          <h1 className="text-base font-semibold text-gray-900">Automação com IA</h1>
          <p className="text-xs text-gray-500">Cole a mensagem do WhatsApp — o sistema extrai e preenche o formulário</p>
        </div>
      </div>

      {/* Sucesso */}
      {result && (
        <div className="mx-4 mt-4 bg-green-50 border border-green-200 rounded-xl p-4 flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-green-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-green-800">Orçamento criado com sucesso!</p>
            <p className="text-sm text-green-700">
              Orçamento: <span className="font-mono">{result.budget_id}</span>
              {result.client_id && <> · Cliente: <span className="font-mono">{result.client_id}</span></>}
              {result.items_created != null && <> · <span className="font-medium">{result.items_created} item(s)</span></>}
              {result.client_created && <span className="ml-1 text-[11px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">cliente novo</span>}
            </p>
            {result.calendar_event_id && (
              <p className="text-xs text-green-700 mt-1 flex items-center gap-1">
                <CalendarCheck className="w-3.5 h-3.5" />
                Evento criado na Agenda Google
              </p>
            )}
            {result.agenda_error && (
              <p className="text-xs text-orange-600 mt-1 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" />
                Agenda: {result.agenda_error}
              </p>
            )}
            <button onClick={() => setResult(null)} className="mt-2 text-xs text-green-600 underline">
              Novo atendimento
            </button>
          </div>
        </div>
      )}

      {/* Dois painéis */}
      <div className="flex-1 flex flex-col lg:flex-row gap-0 overflow-hidden">

        {/* ── Painel Esquerdo: Colar Mensagem ──────────────────────────── */}
        <div className="lg:w-[42%] flex flex-col border-r border-gray-200 bg-white">
          <div className="px-4 pt-4 pb-2 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <Zap className="w-4 h-4 text-yellow-500" /> Colar Mensagem WhatsApp
            </h2>
          </div>
          <div className="flex-1 flex flex-col p-4 gap-3 overflow-y-auto">
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              rows={14}
              placeholder={`Cole aqui a mensagem do WhatsApp.\n\nExemplo:\nMariane de Oliveira\n+55 65 99973-1235\nEdifício Amadeo Modigliani Cuiabá\nApartamento 2402\nHorário 20/7 9:00\n\n🔶 Orçamento - Estofado e Tapete 🔶\n\n💧Lavagem a seco - Sofá 2 lugares - R$290,00\n...`}
              className="flex-1 w-full border border-gray-300 rounded-xl px-3 py-2.5 text-sm font-mono resize-none focus:ring-2 focus:ring-purple-400 focus:border-purple-400 placeholder-gray-400"
            />

            <div className="flex gap-2">
              <button onClick={handleInterpret} disabled={interpreting || !text.trim()}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-purple-600 text-white rounded-xl text-sm font-semibold hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                {interpreting
                  ? <><Loader2 className="w-4 h-4 animate-spin" /> Interpretando…</>
                  : <><Wand2 className="w-4 h-4" /> Interpretar</>}
              </button>
              {text && (
                <button onClick={() => { setText(''); setInterpreted(null); }}
                  className="px-3 py-2.5 border border-gray-300 text-gray-600 rounded-xl text-sm hover:bg-gray-50">
                  <RefreshCw className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Resultado da interpretação */}
            {interpreted && (
              <div className="mt-1 bg-purple-50 border border-purple-200 rounded-xl p-3 space-y-2">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="w-4 h-4 text-purple-600" />
                  <span className="text-xs font-semibold text-purple-700">
                    Interpretado ({interpreted.source})
                  </span>
                </div>
                {[
                  ['Nome', interpreted.client_name],
                  ['Telefone', interpreted.phone],
                  ['Endereço', interpreted.address],
                  ['Complemento', interpreted.complement],
                  ['Data', interpreted.scheduled_date],
                  ['Hora', interpreted.scheduled_time],
                  ['Total PIX', interpreted.total_pix != null ? `R$ ${fmt(interpreted.total_pix)}` : null],
                  ['Total Dinheiro', interpreted.total_cash != null ? `R$ ${fmt(interpreted.total_cash)}` : null],
                ].filter(([, v]) => v).map(([k, v]) => (
                  <div key={k} className="flex items-start gap-2 text-xs">
                    <span className="text-purple-500 font-medium w-20 shrink-0">{k}:</span>
                    <span className="text-gray-800">{v}</span>
                  </div>
                ))}
                <div className="mt-2">
                  <span className="text-xs text-purple-500 font-medium">Itens ({interpreted.items?.length || 0}):</span>
                  {(interpreted.items || []).map((it, i) => (
                    <div key={i} className="text-xs text-gray-700 ml-2 mt-0.5">
                      {i + 1}. {it.service_name}
                      {it.quantity > 1 ? ` ×${it.quantity}` : ''} — R$ {fmt(it.value)}
                    </div>
                  ))}
                </div>
                {interpreted.client_exists && (
                  <div className="mt-2 flex items-center gap-1.5 text-xs text-amber-700 bg-amber-50 rounded-lg px-2 py-1">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    Cliente já cadastrado (ID: {interpreted.existing_client_id})
                  </div>
                )}
                <button onClick={() => applyResult(interpreted)}
                  className="mt-2 w-full flex items-center justify-center gap-2 px-3 py-2 bg-purple-600 text-white rounded-lg text-xs font-semibold hover:bg-purple-700">
                  Aplicar ao formulário →
                </button>
              </div>
            )}
          </div>
        </div>

        {/* ── Painel Direito: Formulário Manual ──────────────────────────── */}
        <div className="lg:flex-1 flex flex-col bg-white overflow-y-auto">
          <div className="px-4 pt-4 pb-2 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <User className="w-4 h-4 text-blue-500" /> Formulário do Atendimento
            </h2>
          </div>

          <div className="flex-1 px-4 py-4 space-y-5 overflow-y-auto">

            {/* Cliente */}
            <section>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Cliente</h3>
              <div className="space-y-2">
                <ClientSearch
                  value={name}
                  onChange={(c, txt) => {
                    setClientObj(c);
                    setName(c ? c.name : txt);
                    if (c) {
                      setPhone(c.phone_primary || '');
                      if (c.address) setAddressObj(c.address);
                    }
                  }}
                />
                {clientObj && (
                  <div className="text-xs text-green-700 bg-green-50 rounded-lg px-2 py-1 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Cliente selecionado: <span className="font-semibold">{clientObj.name}</span>
                    <button onClick={() => { setClientObj(null); }} className="ml-auto text-green-600 underline">trocar</button>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                      <User className="w-3 h-3" /> Nome completo
                    </label>
                    <input value={name} onChange={e => setName(e.target.value)}
                      placeholder="Nome do cliente"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                      <Phone className="w-3 h-3" /> Telefone
                    </label>
                    <input value={phone} onChange={e => setPhone(e.target.value)}
                      placeholder="65 99999-0000"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500" />
                  </div>
                </div>
              </div>
            </section>

            {/* Endereço do cliente */}
            <section>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Endereço do Cliente</h3>
              <div className="space-y-2">
                <AddressAutocomplete
                  value={addressObj}
                  onSelect={setAddressObj}
                  placeholder="Buscar endereço, condomínio, bairro…"
                />
                {addressObj?.full_address && (
                  <div className="text-[11px] text-gray-500 bg-gray-50 rounded px-2 py-1">
                    {addressObj.full_address}
                    {addressObj.neighborhood && ` · ${addressObj.neighborhood}`}
                    {addressObj.city && ` · ${addressObj.city}`}
                  </div>
                )}
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Complemento</label>
                  <input value={complement} onChange={e => setComplement(e.target.value)}
                    placeholder="Apartamento, bloco, referência…"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
            </section>

            {/* Endereço de execução (diferente do cliente) */}
            <section>
              <button
                type="button"
                onClick={() => { setDiffExecAddr(v => !v); setExecAddrObj(null); setExecComplement(''); }}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-xl border text-sm font-medium transition-colors ${
                  diffExecAddr
                    ? 'border-orange-300 bg-orange-50 text-orange-700'
                    : 'border-gray-200 bg-gray-50 text-gray-500 hover:bg-gray-100'
                }`}
              >
                <ArrowRightLeft className="w-4 h-4 shrink-0" />
                <span className="flex-1 text-left">Serviço será executado em endereço diferente do cliente</span>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${diffExecAddr ? 'bg-orange-200 text-orange-800' : 'bg-gray-200 text-gray-600'}`}>
                  {diffExecAddr ? 'ATIVO' : 'não'}
                </span>
              </button>

              {diffExecAddr && (
                <div className="mt-2 space-y-2 border border-orange-200 rounded-xl p-3 bg-orange-50">
                  <p className="text-[11px] text-orange-700 font-medium">
                    Endereço onde o técnico deve ir executar o serviço:
                  </p>
                  <AddressAutocomplete
                    value={execAddrObj}
                    onSelect={setExecAddrObj}
                    placeholder="Buscar endereço de execução…"
                  />
                  {execAddrObj?.full_address && (
                    <div className="text-[11px] text-gray-500 bg-white rounded px-2 py-1">
                      {execAddrObj.full_address}
                      {execAddrObj.neighborhood && ` · ${execAddrObj.neighborhood}`}
                    </div>
                  )}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Complemento do local</label>
                    <input value={execComplement} onChange={e => setExecComplement(e.target.value)}
                      placeholder="Ex: Sala 304, Bloco B, Fundos…"
                      className="w-full border border-orange-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-orange-400 bg-white" />
                  </div>
                  <p className="text-[10px] text-orange-600">
                    Os itens serão criados com modo <strong>EXECUTAR_NO_LOCAL</strong> e o evento na Agenda usará este endereço.
                  </p>
                </div>
              )}
            </section>

            {/* Agendamento */}
            <section>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Agendamento</h3>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                    <Calendar className="w-3 h-3" /> Data
                  </label>
                  <input type="date" value={schedDate} onChange={e => setSchedDate(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> Hora
                  </label>
                  <input type="time" value={schedTime} onChange={e => setSchedTime(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
            </section>

            {/* Itens */}
            <section>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Itens do Orçamento ({items.length})
                </h3>
                <button onClick={addItem}
                  className="flex items-center gap-1 text-xs text-blue-600 font-semibold hover:text-blue-800 px-2 py-1 rounded-lg hover:bg-blue-50">
                  <Plus className="w-3.5 h-3.5" /> Adicionar item
                </button>
              </div>
              <div className="space-y-2">
                {items.length === 0 && (
                  <div className="text-center py-6 text-gray-400 text-sm border-2 border-dashed border-gray-200 rounded-xl">
                    Nenhum item ainda. Cole uma mensagem ou adicione manualmente.
                  </div>
                )}
                {items.map((it, i) => (
                  <ItemRow key={i} item={it} idx={i} onChange={patchItem} onRemove={removeItem} />
                ))}
              </div>
            </section>

            {/* Totais */}
            <section>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Totais</h3>
              <div className="bg-blue-50 rounded-xl p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Calculado pelos itens:</span>
                  <span className="text-base font-bold text-blue-800">R$ {fmt(calcTotal)}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-blue-100">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                      <DollarSign className="w-3 h-3 text-green-600" /> Total PIX/Cartão (R$)
                    </label>
                    <input type="number" step="0.01" value={totalPix}
                      onChange={e => setTotalPix(e.target.value)}
                      placeholder={calcTotal > 0 ? String(calcTotal) : '0,00'}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 bg-white" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                      <DollarSign className="w-3 h-3 text-amber-600" /> Total Dinheiro (R$)
                    </label>
                    <input type="number" step="0.01" value={totalCash}
                      onChange={e => setTotalCash(e.target.value)}
                      placeholder="Com desconto"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 bg-white" />
                  </div>
                </div>
              </div>
            </section>

            {/* Observações */}
            <section>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
                <StickyNote className="w-3.5 h-3.5" /> Observações
              </h3>
              <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3}
                placeholder="Obs: detalhes, restrições, combinados…"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 resize-none" />
            </section>

            {/* Ações */}
            <section className="pb-6">
              <div className="flex flex-col sm:flex-row gap-2">
                <button onClick={() => handleSave(true)} disabled={saving}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                  {saving
                    ? <><Loader2 className="w-4 h-4 animate-spin" /> Salvando…</>
                    : <><Send className="w-4 h-4" /> Salvar Cliente + Criar Orçamento + Lançar na Agenda</>}
                </button>
                <button onClick={() => handleSave(false)} disabled={saving}
                  className="sm:w-44 flex items-center justify-center gap-2 px-4 py-3 border border-gray-300 text-gray-700 rounded-xl text-sm font-semibold hover:bg-gray-50 disabled:opacity-50 transition-colors">
                  Só salvar rascunho
                </button>
              </div>
              <p className="text-[11px] text-gray-400 mt-2 text-center">
                Status padrão: PENDENTE · Origem: AUTOMACAO
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AutomationPage;
