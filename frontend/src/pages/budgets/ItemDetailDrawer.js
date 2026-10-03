import React, { useEffect, useMemo, useState, useRef } from 'react';
import {
  X, Clock, Play, StopCircle, Wallet, ChevronDown, ChevronUp,
  AlertCircle, Loader2, History, MapPin, Calendar as CalendarIcon,
  DollarSign, Check, ArrowRight, RefreshCw, Send,
} from 'lucide-react';
import api, { itemsApi, enumsApi, placesApi, technicianApi } from '../../services/api';
import { TECHNICIAN_ID } from '../../constants/technician';
import {
  STATUS_COLOR, PAYMENT_STATUS_COLOR, PAYMENT_METHODS, fmtMoney,
  EXECUTION_MODES,
} from './_constants';

const TYPE_ICON = {
  STATUS: History, EXEC_START: Play, EXEC_END: StopCircle,
  PAYMENT: Wallet, ROUTE: MapPin,
};

const TYPE_COLOR = {
  STATUS: 'bg-blue-50 text-blue-700',
  EXEC_START: 'bg-emerald-50 text-emerald-700',
  EXEC_END: 'bg-amber-50 text-amber-700',
  PAYMENT: 'bg-violet-50 text-violet-700',
  ROUTE: 'bg-sky-50 text-sky-700',
};

// ── Autocomplete de endereço (reutiliza places API) ──────────────────────────
function AddrAutocomplete({ current, onSelect, placeholder }) {
  const [query, setQuery] = useState(current?.full_address || '');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debRef = useRef(null);
  const boxRef = useRef(null);
  const skipSearchRef = useRef(false);

  useEffect(() => { skipSearchRef.current = true; setQuery(current?.full_address || ''); }, [current?.full_address]);

  useEffect(() => {
    if (debRef.current) clearTimeout(debRef.current);
    if (skipSearchRef.current) { skipSearchRef.current = false; setResults([]); setOpen(false); return; }
    if (!query || query.length < 3) { setResults([]); return; }
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

  const choose = async (p) => {
    setOpen(false);
    skipSearchRef.current = true;
    setQuery(p.description || '');
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
          if (t.includes('sublocality') || t.includes('neighborhood') || t.includes('sublocality_level_1')) neighborhood = c.long_name;
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
        <MapPin className="w-3.5 h-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
        <input value={query} onChange={e => setQuery(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          placeholder={placeholder || 'Buscar endereço…'}
          className="w-full pl-7 pr-7 py-1.5 border border-gray-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500" />
        {loading && <Loader2 className="w-3 h-3 absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 animate-spin" />}
      </div>
      {open && results.length > 0 && (
        <ul className="absolute z-50 mt-1 w-full max-h-52 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-lg">
          {results.slice(0, 6).map(p => (
            <li key={p.place_id || p.description} onClick={() => choose(p)}
              className="px-2.5 py-1.5 hover:bg-blue-50 cursor-pointer text-xs border-b border-gray-50 last:border-0">
              {p.description || p.structured_formatting?.main_text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Seção de endereços por etapa ──────────────────────────────────────────────
function AddressSection({ item, onPatch, busy }) {
  const [open, setOpen] = useState(
    !!(item.pickup_address || item.execution_address || item.delivery_address)
  );
  const mode = item.execution_mode || 'RETIRAR_E_LEVAR';
  const showPickup    = ['RETIRAR_E_LEVAR'].includes(mode);
  const showExecution = ['EXECUTAR_NO_LOCAL'].includes(mode);
  const showDelivery  = ['RETIRAR_E_LEVAR', 'CLIENTE_TROUXE'].includes(mode);
  const hasOverride = !!(item.pickup_address || item.execution_address || item.delivery_address);

  const Field = ({ label, field, value }) => (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-[11px] font-medium text-gray-600">{label}</label>
        {value && (
          <button disabled={busy} onClick={() => onPatch({ [field]: null })}
            className="text-[10px] text-red-500 hover:text-red-700">limpar (usar end. do cliente)</button>
        )}
      </div>
      <AddrAutocomplete current={value}
        onSelect={(addr) => onPatch({ [field]: { ...addr, complement: value?.complement || '' } })}
        placeholder="Padrão = endereço do cliente" />
      {value?.full_address && (
        <>
          <input
            defaultValue={value.complement || ''}
            onBlur={(e) => { if ((e.target.value || '') !== (value.complement || '')) onPatch({ [field]: { ...value, complement: e.target.value } }); }}
            placeholder="Complemento (apto, bloco, quadra, lote…)"
            className="w-full mt-1 px-2 py-1.5 border border-gray-300 rounded-lg text-xs"
          />
          <p className="text-[10px] text-green-600 mt-0.5 truncate">
            ✓ {value.full_address}{value.latitude ? '' : ' (sem coordenadas)'}
          </p>
        </>
      )}
    </div>
  );

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button onClick={() => setOpen(v => !v)}
        className="w-full px-3 py-2 flex items-center justify-between bg-gray-50 hover:bg-gray-100">
        <span className="text-xs font-medium text-gray-700 flex items-center gap-1.5">
          <MapPin className="w-3.5 h-3.5 text-gray-500" />
          Endereços do item
          {hasOverride && <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full">personalizado</span>}
        </span>
        {open ? <ChevronUp className="w-3.5 h-3.5 text-gray-400" /> : <ChevronDown className="w-3.5 h-3.5 text-gray-400" />}
      </button>
      {open && (
        <div className="p-3 space-y-3">
          {showPickup    && <Field label="Endereço de retirada"  field="pickup_address"    value={item.pickup_address} />}
          {showExecution && <Field label="Endereço de execução"  field="execution_address" value={item.execution_address} />}
          {showDelivery  && <Field label="Endereço de entrega"   field="delivery_address"  value={item.delivery_address} />}
          <p className="text-[10px] text-gray-400">
            Estes endereços valem só para este item nas rotas. Em branco = usa o endereço do cliente.
          </p>
        </div>
      )}
    </div>
  );
}

export default function ItemDetailDrawer({ itemId, onClose, onUpdated }) {
  const [data, setData] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusOptions, setStatusOptions] = useState([]);
  const [activeTab, setActiveTab] = useState('timeline'); // timeline | actions
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  // form de pagamento
  const [payMethod, setPayMethod] = useState('PIX_CNPJ_25995295000104');
  const [payValue, setPayValue] = useState('');
  const [payNotes, setPayNotes] = useState('');

  // form de status
  const [newStatus, setNewStatus] = useState('');
  const [statusNotes, setStatusNotes] = useState('');

  // sessão de execução
  const [sessionPayload, setSessionPayload] = useState({ technician_name: '', notes: '' });
  const [finishOutcome, setFinishOutcome] = useState('COMPLETED');
  const [finishReason, setFinishReason] = useState('');

  const reload = async () => {
    try {
      setLoading(true);
      const [it, tl, opts] = await Promise.all([
        itemsApi.get(itemId),
        itemsApi.timeline(itemId),
        enumsApi.serviceStatus(),
      ]);
      setData(it.data);
      setTimeline(tl.data?.events || []);
      const so = opts.data?.status_options || opts.data || [];
      setStatusOptions(so);
      setNewStatus(it.data?.item?.status || '');
    } catch (e) {
      setError(e.response?.data?.detail || 'Erro ao carregar item.');
    } finally { setLoading(false); }
  };

  useEffect(() => { if (itemId) reload(); /* eslint-disable-next-line */ }, [itemId]);

  const item = data?.item || {};
  const openSession = useMemo(() =>
    (item.execution_sessions || []).find(s => !s.finished_at),
    [item.execution_sessions]
  );

  const onPatchAddress = async (fields) => {
    try {
      setBusy(true);
      await itemsApi.patch(itemId, fields);
      await reload();
      onUpdated?.();
    } catch (e) {
      setError(e.response?.data?.detail || 'Erro ao salvar endereço.');
    } finally { setBusy(false); }
  };

  const onChangeStatus = async () => {
    if (!newStatus || newStatus === item.status) return;
    try {
      setBusy(true);
      await itemsApi.changeStatus(itemId, newStatus, statusNotes);
      setStatusNotes('');
      await reload();
      onUpdated?.();
    } catch (e) {
      setError(e.response?.data?.detail || 'Erro ao mudar status.');
    } finally { setBusy(false); }
  };

  const onStartSession = async () => {
    try {
      setBusy(true);
      await itemsApi.startSession(itemId, {
        technician_name: sessionPayload.technician_name || undefined,
        notes: sessionPayload.notes,
      });
      setSessionPayload({ technician_name: '', notes: '' });
      await reload();
      onUpdated?.();
    } catch (e) {
      setError(e.response?.data?.detail || 'Erro ao iniciar sessão.');
    } finally { setBusy(false); }
  };

  const onFinishSession = async () => {
    if (!openSession) return;
    try {
      setBusy(true);
      await itemsApi.finishSession(itemId, openSession.id, {
        outcome: finishOutcome,
        reason: finishReason,
      });
      setFinishReason('');
      await reload();
      onUpdated?.();
    } catch (e) {
      setError(e.response?.data?.detail || 'Erro ao encerrar sessão.');
    } finally { setBusy(false); }
  };

  const [sendingToTech, setSendingToTech] = useState(false);
  const [techScheduledTime, setTechScheduledTime] = useState('');
  const onSendToTechnician = async () => {
    try {
      setSendingToTech(true);
      const today = new Date().toISOString().split('T')[0];
      await technicianApi.assignEvents({
        route_id: null,
        event_ids: [itemId],
        technician_id: TECHNICIAN_ID,
        assigned_date: today,
        assignment_type: 'MANUAL',
        item_schedule: { [itemId]: { scheduled_time: techScheduledTime || null } },
      });
      await reload();
      onUpdated?.();
    } catch (e) {
      setError(e.response?.data?.detail || 'Erro ao enviar para o técnico.');
    } finally { setSendingToTech(false); }
  };

  const onPay = async () => {
    const v = Number(payValue);
    if (!v || v <= 0) { setError('Valor inválido.'); return; }
    try {
      setBusy(true);
      await itemsApi.registerPayment(itemId, {
        method: payMethod, value: v, notes: payNotes,
      });
      setPayValue(''); setPayNotes('');
      await reload();
      onUpdated?.();
    } catch (e) {
      setError(e.response?.data?.detail || 'Erro ao registrar pagamento.');
    } finally { setBusy(false); }
  };

  if (loading || !data) {
    return (
      <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-white" />
      </div>
    );
  }

  const totalValue = Number(item.total_value || 0);
  const paidValue = Number(item.paid_value || 0);
  const remaining = Math.max(totalValue - paidValue, 0);
  const paymentMethod = item.payment_method || data.budget_payment_method;
  const execMode = EXECUTION_MODES.find(m => m.value === item.execution_mode);

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="bg-white w-full sm:max-w-2xl sm:rounded-2xl rounded-t-2xl shadow-2xl flex flex-col max-h-[96vh]">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 sticky top-0 bg-white z-10">
          <div className="flex items-center justify-between mb-2">
            <div className="min-w-0">
              <div className="text-xs font-mono text-blue-700 bg-blue-50 inline-block px-1.5 py-0.5 rounded">{item.id}</div>
              <h3 className="font-semibold text-gray-900 truncate mt-1">{item.service_name}</h3>
              <p className="text-xs text-gray-500 truncate">{item.client_name} • Orçamento {data.budget_id}</p>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Badges */}
          <div className="flex flex-wrap gap-1.5">
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${STATUS_COLOR[item.status] || 'bg-gray-100 text-gray-700'}`}>
              {item.status}
            </span>
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${PAYMENT_STATUS_COLOR[item.payment_status] || 'bg-gray-100 text-gray-700'}`}>
              {item.payment_status}
            </span>
            {execMode && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-indigo-50 text-indigo-700">
                {execMode.label}
              </span>
            )}
            {item.current_route_id && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-sky-50 text-sky-700">
                {item.current_route_id}
              </span>
            )}
            {item.client_desisted && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-red-100 text-red-700">
                ✕ Cliente desistiu
              </span>
            )}
          </div>

          {/* Botão reativar — aparece só quando item está como desistência */}
          {item.client_desisted && (
            <div className="mt-2 pt-2 border-t border-gray-100">
              <button
                disabled={busy}
                onClick={async () => {
                  if (!window.confirm('Reativar este item? Ele voltará a aparecer na seleção de rotas.')) return;
                  try {
                    setBusy(true);
                    await api.patch(`/items/${itemId}/reactivate`);
                    await reload();
                    onUpdated?.();
                  } catch (e) {
                    setError(e.response?.data?.detail || 'Erro ao reativar.');
                  } finally { setBusy(false); }
                }}
                className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 text-sm font-medium border border-emerald-200 disabled:opacity-50"
              >
                <RefreshCw className="w-4 h-4" />
                Reativar item — cliente mudou de ideia
              </button>
            </div>
          )}

          {/* Tabs */}
          <div className="mt-3 flex gap-1">
            {[
              { k: 'timeline', label: 'Linha do Tempo', icon: Clock },
              { k: 'actions', label: 'Ações', icon: ArrowRight },
            ].map(t => {
              const Icon = t.icon;
              const active = activeTab === t.k;
              return (
                <button
                  key={t.k}
                  onClick={() => setActiveTab(t.k)}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium ${
                    active ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" /> {t.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3">
          {/* Resumo financeiro + dados */}
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="bg-gray-50 rounded-lg py-2">
              <div className="text-[10px] text-gray-500 uppercase">Total</div>
              <div className="text-sm font-bold text-gray-900">{fmtMoney(totalValue)}</div>
            </div>
            <div className="bg-emerald-50 rounded-lg py-2">
              <div className="text-[10px] text-emerald-700 uppercase">Pago</div>
              <div className="text-sm font-bold text-emerald-700">{fmtMoney(paidValue)}</div>
            </div>
            <div className="bg-amber-50 rounded-lg py-2">
              <div className="text-[10px] text-amber-700 uppercase">Restante</div>
              <div className="text-sm font-bold text-amber-700">{fmtMoney(remaining)}</div>
            </div>
          </div>

          {item.observations && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-2 text-sm text-yellow-900">
              <strong>Obs:</strong> {item.observations}
            </div>
          )}

          {/* Endereços por etapa */}
          <AddressSection item={item} onPatch={onPatchAddress} busy={busy} />

          {/* TAB: TIMELINE */}
          {activeTab === 'timeline' && (
            <div className="space-y-2">
              {timeline.length === 0 && (
                <div className="text-center py-6 text-sm text-gray-500">Sem eventos ainda.</div>
              )}
              {timeline.map((e, idx) => {
                const Icon = TYPE_ICON[e.type] || Clock;
                const color = TYPE_COLOR[e.type] || 'bg-gray-50 text-gray-700';
                return (
                  <div key={idx} className="flex gap-2 items-start">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${color}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0 bg-white border border-gray-200 rounded-lg p-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-sm font-medium text-gray-900 truncate">{e.label}</div>
                        <div className="text-[10px] text-gray-400 whitespace-nowrap">
                          {e.at ? new Date(e.at).toLocaleString('pt-BR') : '—'}
                        </div>
                      </div>
                      {(e.by || e.notes) && (
                        <div className="text-xs text-gray-500 mt-0.5">
                          {e.by && <span>{e.by}</span>}
                          {e.by && e.notes && ' • '}
                          {e.notes && <span>{e.notes}</span>}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* TAB: ACTIONS */}
          {activeTab === 'actions' && (
            <div className="space-y-3">
              {/* Enviar direto pro técnico — sem precisar de rota */}
              <div className="bg-white border border-gray-200 rounded-xl p-3">
                <div className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-1.5">
                  <Send className="w-4 h-4 text-orange-600" /> Enviar pro técnico
                </div>
                <p className="text-xs text-gray-500 mb-2">
                  Manda este item direto pro técnico hoje, sem precisar montar uma rota.
                  Útil pra serviço avulso (sofá, cadeira) ou item de última hora.
                </p>
                <div className="flex items-center gap-2 mb-2">
                  <label className="text-xs text-gray-500 whitespace-nowrap">Horário previsto (opcional):</label>
                  <input
                    type="time"
                    value={techScheduledTime}
                    onChange={(e) => setTechScheduledTime(e.target.value)}
                    className="px-2 py-1 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
                <button
                  onClick={onSendToTechnician}
                  disabled={sendingToTech}
                  className="w-full px-3 py-2 rounded-lg bg-orange-600 text-white text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-1"
                >
                  {sendingToTech ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  Enviar direto pro técnico
                </button>
              </div>

              {/* Mudar status */}
              <div className="bg-white border border-gray-200 rounded-xl p-3">
                <div className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-1.5">
                  <History className="w-4 h-4 text-blue-600" /> Alterar status
                </div>
                <div className="space-y-2">
                  <select
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  >
                    {statusOptions.map(o => (
                      <option key={o.value} value={o.value}>{o.label || o.value}</option>
                    ))}
                  </select>
                  <input
                    value={statusNotes}
                    onChange={(e) => setStatusNotes(e.target.value)}
                    placeholder="Notas (opcional)"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                  <button
                    onClick={onChangeStatus}
                    disabled={busy || newStatus === item.status}
                    className="w-full px-3 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-1"
                  >
                    {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                    Aplicar status
                  </button>
                </div>
              </div>

              {/* Sessão de execução */}
              <div className="bg-white border border-gray-200 rounded-xl p-3">
                <div className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-1.5">
                  <Play className="w-4 h-4 text-emerald-600" /> Sessão de execução
                </div>
                {openSession ? (
                  <div className="space-y-2">
                    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-2 text-xs text-emerald-900">
                      <strong>Sessão em andamento</strong><br />
                      Iniciada: {new Date(openSession.started_at).toLocaleString('pt-BR')}<br />
                      Técnico: {openSession.technician_name || openSession.technician_id || '—'}
                    </div>
                    <select
                      value={finishOutcome}
                      onChange={(e) => setFinishOutcome(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    >
                      <option value="COMPLETED">✅ Concluída</option>
                      <option value="PARTIAL">⚠️ Parcial (continuará depois)</option>
                      <option value="ABORTED">❌ Abortada (precisa retoque)</option>
                    </select>
                    {finishOutcome !== 'COMPLETED' && (
                      <input
                        value={finishReason}
                        onChange={(e) => setFinishReason(e.target.value)}
                        placeholder="Motivo (ex: máquina quebrou)"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                      />
                    )}
                    <button
                      onClick={onFinishSession}
                      disabled={busy}
                      className="w-full px-3 py-2 rounded-lg bg-amber-600 text-white text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-1"
                    >
                      {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <StopCircle className="w-4 h-4" />}
                      Encerrar sessão
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <input
                      value={sessionPayload.technician_name}
                      onChange={(e) => setSessionPayload({ ...sessionPayload, technician_name: e.target.value })}
                      placeholder="Nome do técnico"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    />
                    <input
                      value={sessionPayload.notes}
                      onChange={(e) => setSessionPayload({ ...sessionPayload, notes: e.target.value })}
                      placeholder="Notas (opcional)"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    />
                    <button
                      onClick={onStartSession}
                      disabled={busy}
                      className="w-full px-3 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-1"
                    >
                      {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                      Iniciar sessão
                    </button>
                  </div>
                )}
              </div>

              {/* Pagamento */}
              <div className="bg-white border border-gray-200 rounded-xl p-3">
                <div className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-1.5">
                  <Wallet className="w-4 h-4 text-violet-600" /> Registrar pagamento
                </div>
                <div className="text-xs text-gray-500 mb-2">
                  Método padrão: <strong>{paymentMethod}</strong> • Restante: <strong className="text-amber-700">{fmtMoney(remaining)}</strong>
                </div>
                <div className="space-y-2">
                  <select
                    value={payMethod}
                    onChange={(e) => setPayMethod(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  >
                    {PAYMENT_METHODS.map(m => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="number" step="0.01"
                      value={payValue}
                      onChange={(e) => setPayValue(e.target.value)}
                      placeholder="Valor (R$)"
                      className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    />
                    <button
                      type="button"
                      onClick={() => setPayValue(remaining.toFixed(2))}
                      className="px-3 py-2 rounded-lg border border-gray-300 text-xs text-gray-600 hover:bg-gray-50"
                    >
                      Restante
                    </button>
                  </div>
                  <input
                    value={payNotes}
                    onChange={(e) => setPayNotes(e.target.value)}
                    placeholder="Notas (opcional)"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                  <button
                    onClick={onPay}
                    disabled={busy}
                    className="w-full px-3 py-2 rounded-lg bg-violet-600 text-white text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-1"
                  >
                    {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <DollarSign className="w-4 h-4" />}
                    Registrar
                  </button>
                </div>

                {item.payment_records?.length > 0 && (
                  <div className="mt-3 border-t border-gray-100 pt-2 space-y-1">
                    <div className="text-[11px] uppercase font-semibold text-gray-500">Recebimentos</div>
                    {item.payment_records.map(p => (
                      <div key={p.id} className="text-xs flex justify-between bg-gray-50 px-2 py-1 rounded">
                        <span>{p.method}</span>
                        <span className="font-semibold">{fmtMoney(p.value)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 text-red-700 border border-red-200 rounded-lg px-3 py-2 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" /> {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
