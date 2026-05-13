import React, { useEffect, useMemo, useState } from 'react';
import {
  X, Clock, Play, StopCircle, Wallet, ChevronDown, ChevronUp,
  AlertCircle, Loader2, History, MapPin, Calendar as CalendarIcon,
  DollarSign, Check, ArrowRight,
} from 'lucide-react';
import { itemsApi, enumsApi } from '../../services/api';
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
          </div>

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
