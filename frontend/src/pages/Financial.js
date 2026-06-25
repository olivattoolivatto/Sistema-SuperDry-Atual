import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  DollarSign, RefreshCw, Search, CreditCard, X,
  ChevronDown, ChevronUp, FileText, MessageCircle, User, Calendar,
} from 'lucide-react';
import { itemsApi, consolidatedPaymentApi } from '../services/api';
import { fmtMoney } from './budgets/_constants';
import { toast } from '../hooks/use-toast';
import { BACKEND_URL } from '../lib/backendUrl';

const STATUS_LABEL = {
  ENTREGUE:  { label: 'Entregue',          color: 'bg-blue-100 text-blue-800' },
  EXECUTADO: { label: 'Executado no Local', color: 'bg-purple-100 text-purple-800' },
  BUSCOU:    { label: 'Cliente Buscou',     color: 'bg-teal-100 text-teal-800' },
};

const PAY_STATUS = {
  PAGO:        { label: 'Pago',        color: 'bg-emerald-100 text-emerald-800', icon: '✅' },
  PARCIAL:     { label: 'Parcial',     color: 'bg-yellow-100 text-yellow-800',   icon: '⚡' },
  PENDENTE:    { label: 'À Receber',   color: 'bg-red-100 text-red-800',         icon: '🔴' },
  INADIMPLENTE:{ label: 'Inadimplente',color: 'bg-rose-200 text-rose-900',       icon: '⚠️' },
  CORTESIA:    { label: 'Cortesia',    color: 'bg-gray-100 text-gray-700',       icon: '🎁' },
};

const MONTH_PT = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];

// ── Helpers de data ───────────────────────────────────────────────────────────
function startOfDay(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}
function startOfMonth(year, month) {
  return new Date(year, month, 1);
}

function buildDateRange(preset, customFrom, customTo) {
  const now = new Date();
  const today = startOfDay(now);
  const tomorrow = new Date(today); tomorrow.setDate(today.getDate() + 1);

  if (preset === '')           return null;
  if (preset === 'today')      return { from: today, to: tomorrow };
  if (preset === 'week') {
    const dow = today.getDay();
    const monday = new Date(today);
    monday.setDate(today.getDate() - (dow === 0 ? 6 : dow - 1));
    return { from: monday, to: tomorrow };
  }
  if (preset === 'month')      return { from: startOfMonth(now.getFullYear(), now.getMonth()), to: tomorrow };
  if (preset === 'lastmonth') {
    const from = startOfMonth(now.getFullYear(), now.getMonth() - 1);
    const to   = startOfMonth(now.getFullYear(), now.getMonth());
    return { from, to };
  }
  if (preset === 'custom') {
    const from = customFrom ? new Date(customFrom + 'T00:00:00') : null;
    const to   = customTo   ? new Date(customTo   + 'T23:59:59') : null;
    return (from || to) ? { from, to } : null;
  }
  return null;
}

function periodLabel(preset, customFrom, customTo) {
  const now = new Date();
  if (preset === '')          return 'Todo o período';
  if (preset === 'today')     return `Hoje, ${now.getDate()} de ${MONTH_PT[now.getMonth()]}`;
  if (preset === 'week')      return 'Esta semana';
  if (preset === 'month')     return `${MONTH_PT[now.getMonth()]}/${now.getFullYear()}`;
  if (preset === 'lastmonth') {
    const lm = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    return `${MONTH_PT[lm.getMonth()]}/${lm.getFullYear()}`;
  }
  if (preset === 'custom') {
    const f = customFrom ? new Date(customFrom + 'T00:00:00').toLocaleDateString('pt-BR') : '?';
    const t = customTo   ? new Date(customTo   + 'T00:00:00').toLocaleDateString('pt-BR') : '?';
    return `${f} → ${t}`;
  }
  return '';
}

// Data de referência de um item para filtragem por período:
//   → pagamento mais recente (paid_at), ou updated_at, ou created_at
function itemRefDate(doc) {
  const recs = doc?.item?.payment_records;
  if (recs && recs.length > 0) {
    return new Date(Math.max(...recs.map(p => new Date(p.paid_at).getTime())));
  }
  return new Date(doc?.item?.updated_at || doc?.item?.created_at || Date.now());
}

// ── Modal de pagamento ────────────────────────────────────────────────────────
function PaymentModal({ item, onClose, onSaved }) {
  const [methods, setMethods] = useState([]);
  const [method, setMethod] = useState('DINHEIRO');
  const [value, setValue] = useState('');
  const [notes, setNotes] = useState('');
  const [paidAt, setPaidAt] = useState(() => new Date().toISOString().slice(0, 10));
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/payment-methods`)
      .then(r => r.json())
      .then(d => setMethods(d.payment_methods || []))
      .catch(() => {});
  }, []);

  const remaining = (item.total_value || 0) - (item.paid_value || 0);

  const save = async () => {
    if (!value || parseFloat(value) <= 0) return;
    setSaving(true);
    try {
      const token = localStorage.getItem('superdry_token');
      await fetch(`${BACKEND_URL}/api/items/${item.id}/payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ method, value: parseFloat(value), notes, paid_at: paidAt }),
      });
      toast({ title: 'Pagamento registrado!', description: `R$ ${parseFloat(value).toFixed(2)} em ${method}` });
      onSaved();
      onClose();
    } catch (e) {
      toast({ title: 'Erro', description: e.message, variant: 'destructive' });
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Registrar Pagamento</h3>
          <button onClick={onClose}><X className="w-5 h-5 text-gray-400" /></button>
        </div>
        <div className="text-sm text-gray-600 space-y-1 bg-gray-50 rounded-lg p-3">
          <p><strong>{item.client_name}</strong></p>
          <p className="text-xs text-gray-500">{item.service_name}</p>
          <div className="flex justify-between mt-2 text-xs">
            <span>Total: <strong>{fmtMoney(item.total_value)}</strong></span>
            <span>Pago: <strong className="text-green-700">{fmtMoney(item.paid_value || 0)}</strong></span>
            <span>Restante: <strong className="text-red-600">{fmtMoney(remaining)}</strong></span>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Forma de Pagamento</label>
          <select value={method} onChange={e => setMethod(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
            {methods.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Valor Recebido (R$)</label>
          <div className="flex gap-2">
            <input type="number" step="0.01" min="0.01"
              value={value} onChange={e => setValue(e.target.value)}
              placeholder={remaining.toFixed(2)}
              onFocus={(e) => e.target.select()} className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            <button type="button" onClick={() => setValue(remaining.toFixed(2))}
              className="px-3 py-2 text-xs bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">
              Total
            </button>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Data do Recebimento</label>
          <input type="date" value={paidAt} max={new Date().toISOString().slice(0, 10)}
            onChange={e => setPaidAt(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Observação (opcional)</label>
          <input value={notes} onChange={e => setNotes(e.target.value)}
            placeholder="Desconto, observação de pagamento..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
        </div>
        <div className="flex gap-2">
          <button onClick={onClose}
            className="flex-1 py-2 rounded-xl border border-gray-300 text-sm text-gray-700">Cancelar</button>
          <button onClick={save} disabled={saving || !value || parseFloat(value) <= 0}
            className="flex-1 py-2 rounded-xl bg-green-600 text-white text-sm font-semibold disabled:opacity-50">
            {saving ? 'Salvando…' : 'Confirmar'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Linha de item (lista flat) ────────────────────────────────────────────────
function ItemListRow({ doc, onRegisterPayment, selected, onToggleSelect }) {
  const [expanded, setExpanded] = useState(false);
  const item = doc.item;
  const ps = PAY_STATUS[item.payment_status] || PAY_STATUS.PENDENTE;
  const ss = STATUS_LABEL[item.status] || { label: item.status, color: 'bg-gray-100 text-gray-700' };
  const pct = item.total_value > 0 ? Math.min(100, ((item.paid_value || 0) / item.total_value) * 100) : 0;
  const remaining = (item.total_value || 0) - (item.paid_value || 0);
  const canSelect = !['PAGO', 'CORTESIA'].includes(item.payment_status) && remaining > 0;

  const lastPayment = item.payment_records?.length > 0
    ? item.payment_records[item.payment_records.length - 1]
    : null;
  const refDate = lastPayment
    ? new Date(lastPayment.paid_at).toLocaleDateString('pt-BR')
    : item.scheduled_date
      ? new Date(item.scheduled_date).toLocaleDateString('pt-BR')
      : new Date(item.updated_at || item.created_at).toLocaleDateString('pt-BR');

  return (
    <>
      <div className={`flex items-center gap-2 px-4 py-2.5 border-b border-gray-50 transition-colors ${
        selected ? 'bg-emerald-50/50' : 'hover:bg-gray-50/60'
      }`}>
        {/* Checkbox */}
        <div className="shrink-0 w-5 flex justify-center">
          {canSelect ? (
            <input type="checkbox" checked={!!selected} onChange={() => onToggleSelect(doc)}
              className="h-4 w-4 text-emerald-600 rounded border-gray-300 cursor-pointer" />
          ) : <div className="w-4" />}
        </div>

        {/* Serviço + badges + barra */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-sm font-medium text-gray-800 truncate max-w-[180px]">{item.service_name}</span>
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0 ${ss.color}`}>{ss.label}</span>
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0 ${ps.color}`}>{ps.icon} {ps.label}</span>
          </div>
          {item.total_value > 0 && (
            <div className="flex items-center gap-1.5 mt-1.5">
              <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full bg-green-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
              </div>
              <span className="text-[10px] text-gray-400 shrink-0 tabular-nums">{Math.round(pct)}%</span>
            </div>
          )}
          {/* Mobile: data + método abaixo da barra */}
          <div className="flex items-center gap-2 mt-1 sm:hidden">
            <span className="text-[10px] text-gray-400">{refDate}</span>
            {lastPayment?.method && (
              <span className="text-[10px] text-gray-400 truncate">· {lastPayment.method}</span>
            )}
          </div>
        </div>

        {/* Data + método (desktop) */}
        <div className="hidden sm:flex flex-col items-end justify-center shrink-0 w-28">
          <span className="text-xs text-gray-500 tabular-nums">{refDate}</span>
          {lastPayment?.method && (
            <span className="text-[10px] text-gray-400 truncate max-w-[108px]">{lastPayment.method}</span>
          )}
        </div>

        {/* Valor */}
        <div className="shrink-0 text-right w-24">
          <span className="text-sm font-bold text-gray-900 tabular-nums">{fmtMoney(item.total_value)}</span>
          {remaining > 0 && item.paid_value > 0 && (
            <div className="text-[10px] text-amber-600 tabular-nums">falta {fmtMoney(remaining)}</div>
          )}
          {remaining > 0 && !item.paid_value && (
            <div className="text-[10px] text-red-500 tabular-nums">à receber</div>
          )}
        </div>

        {/* Ações */}
        <div className="shrink-0 flex items-center gap-1 ml-1">
          {item.payment_records?.length > 0 && (
            <button onClick={() => setExpanded(v => !v)} title="Ver pagamentos"
              className="p-1 text-gray-400 hover:text-gray-600 rounded">
              {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          )}
          {item.payment_records?.length > 0 && (
            <>
              <a href={itemsApi.receiptUrl(item.id)} target="_blank" rel="noopener noreferrer" title="Recibo"
                className="flex items-center gap-0.5 px-2 py-1 bg-blue-600 text-white text-[10px] rounded-lg hover:bg-blue-700">
                <FileText className="w-3 h-3" />
                <span className="hidden md:inline">Recibo</span>
              </a>
              <button title="WhatsApp" onClick={async () => {
                try {
                  const r = await itemsApi.whatsappReceipt(item.id, 'receipt');
                  window.open(r.data.whatsapp_url, '_blank');
                } catch { alert('Erro ao gerar link WhatsApp'); }
              }}
                className="flex items-center gap-0.5 px-2 py-1 bg-green-600 text-white text-[10px] rounded-lg hover:bg-green-700">
                <MessageCircle className="w-3 h-3" />
                <span className="hidden md:inline">Zap</span>
              </button>
            </>
          )}
          {!['PAGO', 'CORTESIA'].includes(item.payment_status) && (
            <button onClick={() => onRegisterPayment(doc)} title="Registrar pagamento"
              className="flex items-center gap-0.5 px-2 py-1 bg-emerald-600 text-white text-[10px] rounded-lg hover:bg-emerald-700">
              <CreditCard className="w-3 h-3" />
              <span className="hidden md:inline">Receber</span>
            </button>
          )}
        </div>
      </div>

      {/* Histórico de pagamentos expandido */}
      {expanded && item.payment_records?.length > 0 && (
        <div className="px-11 py-2 space-y-1 bg-gray-50 border-b border-gray-100">
          {item.payment_records.map((p, i) => (
            <div key={i} className="flex items-center justify-between text-xs text-gray-600">
              <span>
                {new Date(p.paid_at).toLocaleDateString('pt-BR')} · {p.method}
                {p.notes && <span className="ml-1 text-gray-400 italic">· {p.notes}</span>}
              </span>
              <span className="font-semibold text-green-700 tabular-nums">{fmtMoney(p.value)}</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

// ── Cabeçalho de cliente na lista ─────────────────────────────────────────────
function ClientListHeader({ clientName, docs, selectedIds, onSelectGroup }) {
  const pendingDocs = docs.filter(d =>
    !['PAGO', 'CORTESIA'].includes(d.item.payment_status) &&
    ((d.item.total_value || 0) - (d.item.paid_value || 0)) > 0
  );
  const allSelected = pendingDocs.length > 0 && pendingDocs.every(d => selectedIds.has(d.item.id));

  const totalValue   = docs.reduce((s, d) => s + (d.item.total_value || 0), 0);
  const totalPaid    = docs.reduce((s, d) => s + (d.item.paid_value  || 0), 0);
  const totalPending = totalValue - totalPaid;
  const allPaid      = docs.every(d => ['PAGO', 'CORTESIA'].includes(d.item.payment_status));
  const pct          = totalValue > 0 ? Math.min(100, (totalPaid / totalValue) * 100) : 0;

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-blue-50/70 border-b border-blue-100">
      <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
        <User className="w-3.5 h-3.5 text-blue-600" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-semibold text-gray-900 text-sm">{clientName}</span>
          {allPaid
            ? <span className="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full font-medium">✅ Tudo pago</span>
            : totalPaid > 0
              ? <span className="text-[10px] bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded-full font-medium">⚡ Parcial</span>
              : <span className="text-[10px] bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full font-medium">🔴 Pendente</span>
          }
          <span className="text-[10px] text-gray-400">{docs.length} serviço{docs.length !== 1 ? 's' : ''}</span>
          {pendingDocs.length > 1 && (
            <button onClick={() => onSelectGroup(pendingDocs, !allSelected)}
              className="text-[10px] text-emerald-600 hover:text-emerald-800 font-medium">
              {allSelected ? '☑ desmarcar pendentes' : '☐ selecionar pendentes'}
            </button>
          )}
        </div>

        {totalValue > 0 && (
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1 h-1 bg-white/80 rounded-full overflow-hidden max-w-48">
              <div className="h-full bg-green-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
            </div>
            <span className="text-[10px] text-gray-500 tabular-nums shrink-0">{Math.round(pct)}%</span>
          </div>
        )}
      </div>

      <div className="shrink-0 text-right">
        <div className="text-sm font-bold text-gray-900 tabular-nums">{fmtMoney(totalValue)}</div>
        {totalPending > 0 && (
          <div className="text-[10px] text-red-500 tabular-nums">falta {fmtMoney(totalPending)}</div>
        )}
        {totalPaid > 0 && totalPaid < totalValue && (
          <div className="text-[10px] text-green-600 tabular-nums">pago {fmtMoney(totalPaid)}</div>
        )}
      </div>
    </div>
  );
}

// ── Modal de cobrança consolidada ─────────────────────────────────────────────
function ConsolidatedPaymentModal({ docs, total, onClose, onDone }) {
  const [methods, setMethods] = useState([]);
  const [fees, setFees] = useState({});
  const [method, setMethod] = useState('PIX_CNPJ_25995295000104');
  const [payerName, setPayerName] = useState('');
  const [payerPhone, setPayerPhone] = useState('');
  const [value, setValue] = useState(total.toFixed(2));
  const [link, setLink] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/payment-methods`).then(r => r.json())
      .then(d => { setMethods(d.payment_methods || []); setFees(d.payment_fees || {}); }).catch(() => {});
    const names = new Set(docs.map(d => d.item.client_name));
    if (names.size === 1) setPayerName([...names][0]);
  }, []); // eslint-disable-line

  const clientsCount = new Set(docs.map(d => d.item.client_name)).size;

  const save = async () => {
    setSaving(true);
    try {
      const r = await consolidatedPaymentApi.create({
        item_ids: docs.map(d => d.item.id),
        method,
        payer_name: payerName,
        payer_phone: payerPhone,
        value: parseFloat(value) || total,
        payment_link: link,
        notes,
      });
      setResult(r.data.consolidated_payment);
      toast({ title: 'Cobrança registrada!', description: `${r.data.consolidated_payment.id} — ${fmtMoney(r.data.consolidated_payment.total_value)}` });
    } catch (e) {
      toast({ title: 'Erro', description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally { setSaving(false); }
  };

  const sendWhats = async () => {
    try {
      const r = await consolidatedPaymentApi.whatsapp(result.id);
      window.open(r.data.whatsapp_url, '_blank');
    } catch { alert('Erro ao gerar recibo WhatsApp'); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-5 space-y-4 max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Cobrança Consolidada</h3>
          <button onClick={onClose}><X className="w-5 h-5 text-gray-400" /></button>
        </div>

        {!result ? (
          <>
            <div className="bg-gray-50 rounded-lg p-3 space-y-1 max-h-40 overflow-y-auto">
              {docs.map(d => (
                <div key={d.item.id} className="flex justify-between text-xs">
                  <span className="text-gray-600 truncate mr-2">{d.item.client_name} · {d.item.service_name}</span>
                  <span className="font-medium text-gray-800 shrink-0">{fmtMoney((d.item.total_value||0)-(d.item.paid_value||0))}</span>
                </div>
              ))}
              <div className="flex justify-between text-sm font-bold pt-1 border-t border-gray-200 mt-1">
                <span>Total</span><span className="text-emerald-700">{fmtMoney(total)}</span>
              </div>
            </div>

            {clientsCount > 1 && (
              <div className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1.5">
                ⚠️ {clientsCount} clientes diferentes nesta cobrança. Defina abaixo quem é o responsável pelo pagamento.
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Responsável (quem paga)</label>
                <input value={payerName} onChange={e => setPayerName(e.target.value)}
                  placeholder="Nome do pagador"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Telefone (recibo)</label>
                <input value={payerPhone} onChange={e => setPayerPhone(e.target.value)}
                  placeholder="(65) 9..." className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Forma de Pagamento</label>
              <select value={method} onChange={e => setMethod(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                {methods.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Valor Recebido (R$)</label>
              <div className="flex gap-2">
                <input type="number" step="0.01" value={value} onChange={e => setValue(e.target.value)}
                  onFocus={(e) => e.target.select()} className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                <button onClick={() => setValue(total.toFixed(2))}
                  className="px-3 py-2 text-xs bg-gray-100 rounded-lg hover:bg-gray-200">Total</button>
              </div>
            </div>

            {(() => {
              const gross = parseFloat(value) || total;
              const pct = Number(fees[method] || 0);
              if (pct <= 0) return null;
              const fee = Math.round(gross * pct) / 100;
              const net = Math.round((gross - fee) * 100) / 100;
              return (
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 text-xs space-y-0.5">
                  <div className="flex justify-between text-gray-600"><span>Valor bruto</span><span>{fmtMoney(gross)}</span></div>
                  <div className="flex justify-between text-rose-600"><span>Taxa ({pct.toLocaleString('pt-BR')}%)</span><span>− {fmtMoney(fee)}</span></div>
                  <div className="flex justify-between font-bold text-emerald-700 pt-0.5 border-t border-emerald-200">
                    <span>Líquido estimado</span><span>{fmtMoney(net)}</span>
                  </div>
                  <p className="text-[10px] text-emerald-600/70 pt-0.5">Estimativa pela taxa do plano. Valor real confirmado na conciliação.</p>
                </div>
              );
            })()}

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Link de pagamento / PIX (opcional)</label>
              <input value={link} onChange={e => setLink(e.target.value)}
                placeholder="Cole aqui o link gerado (InfinitePay, etc.)"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              <p className="text-[10px] text-emerald-600 mt-0.5">✅ InfinitePay ativo: ao confirmar, o sistema gera o link automaticamente.</p>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Observação</label>
              <input value={notes} onChange={e => setNotes(e.target.value)}
                placeholder="Desconto, combinado, etc."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            </div>

            <div className="flex gap-2">
              <button onClick={onClose} className="flex-1 py-2 rounded-xl border border-gray-300 text-sm text-gray-700">Cancelar</button>
              <button onClick={save} disabled={saving || !method}
                className="flex-1 py-2 rounded-xl bg-emerald-600 text-white text-sm font-semibold disabled:opacity-50">
                {saving ? 'Salvando…' : `Confirmar ${fmtMoney(parseFloat(value)||total)}`}
              </button>
            </div>
          </>
        ) : (
          <div className="space-y-3 py-2">
            {result.status === 'PENDENTE' && result.payment_link ? (
              <>
                <div className="text-center">
                  <div className="text-4xl mb-1">🔗</div>
                  <p className="text-sm font-semibold text-gray-900">Cobrança gerada! ({result.id})</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {fmtMoney(result.total_value)} · aguardando pagamento do cliente
                  </p>
                </div>
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 space-y-2">
                  <p className="text-xs font-semibold text-blue-800">Link de pagamento:</p>
                  <div className="flex gap-2">
                    <input readOnly value={result.payment_link}
                      className="flex-1 text-xs px-2 py-1.5 border border-blue-200 rounded-lg bg-white text-blue-700 truncate" />
                    <button
                      onClick={() => { navigator.clipboard.writeText(result.payment_link); toast({ title: 'Link copiado!' }); }}
                      className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 shrink-0">
                      Copiar
                    </button>
                  </div>
                  <p className="text-[10px] text-blue-600">
                    Quando o cliente pagar, o sistema marca automaticamente como PAGO via webhook.
                  </p>
                </div>
                {result.fee_amount > 0 && (
                  <p className="text-xs text-gray-500 text-center">
                    Taxa {result.fee_pct?.toLocaleString('pt-BR')}%: − {fmtMoney(result.fee_amount)} ·
                    <strong className="text-emerald-700"> líquido estimado {fmtMoney(result.net_value)}</strong>
                  </p>
                )}
                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => {
                      const phone = result.payer_phone ? result.payer_phone.replace(/\D/g, '') : '';
                      const msg = encodeURIComponent(`Olá${result.payer_name ? ' ' + result.payer_name.split(' ')[0] : ''}! Segue o link para pagamento de ${fmtMoney(result.total_value)}:\n${result.payment_link}`);
                      window.open(`https://wa.me/${phone ? '55' + phone : ''}?text=${msg}`, '_blank');
                    }}
                    className="flex-1 py-2 rounded-xl bg-green-600 text-white text-sm font-semibold flex items-center justify-center gap-1">
                    <MessageCircle className="w-4 h-4" /> Enviar link por WhatsApp
                  </button>
                  <button onClick={onDone}
                    className="px-4 py-2 rounded-xl bg-gray-800 text-white text-sm font-semibold">Fechar</button>
                </div>
              </>
            ) : (
              <>
                <div className="text-center space-y-1">
                  <div className="text-4xl">✅</div>
                  <p className="text-sm font-semibold text-gray-900">Pagamento {result.id} registrado!</p>
                  <p className="text-xs text-gray-500">
                    {fmtMoney(result.total_value)} · {result.applied?.length} serviço(s)
                    {result.payer_name ? ` · pago por ${result.payer_name}` : ''}
                  </p>
                  {result.fee_amount > 0 && (
                    <p className="text-xs text-gray-500">
                      Taxa {result.fee_pct?.toLocaleString('pt-BR')}%: − {fmtMoney(result.fee_amount)} ·
                      <strong className="text-emerald-700"> líquido {fmtMoney(result.net_value)}</strong>
                    </p>
                  )}
                </div>
                <div className="flex gap-2 pt-1">
                  <button onClick={sendWhats}
                    className="flex-1 py-2 rounded-xl bg-green-600 text-white text-sm font-semibold flex items-center justify-center gap-1">
                    <MessageCircle className="w-4 h-4" /> Recibo WhatsApp
                  </button>
                  <button onClick={onDone}
                    className="flex-1 py-2 rounded-xl bg-gray-800 text-white text-sm font-semibold">Concluir</button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Tela principal ────────────────────────────────────────────────────────────
// ── Painel de cobranças com link (InfinitePay) aguardando confirmação ───────
// Dá visibilidade dentro do sistema enquanto a confirmação automática via
// webhook não está validada em produção: lista os links gerados, permite
// reenviar por WhatsApp e confirmar manualmente quando o pagamento for
// verificado por outro meio (ex.: painel da InfinitePay).
function PendingGatewayPayments() {
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [confirmingId, setConfirmingId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await consolidatedPaymentApi.pending();
      setPending(r.data.pending || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (!loading && pending.length === 0) return null;

  const markPaid = async (cpid) => {
    if (!window.confirm(`Confirmar que ${cpid} foi realmente pago? Isso vai dar baixa nos itens.`)) return;
    setConfirmingId(cpid);
    try {
      await consolidatedPaymentApi.confirmManual(cpid);
      toast({ title: 'Confirmado!', description: `${cpid} marcado como pago.` });
      load();
    } catch (e) {
      toast({ title: 'Erro', description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally { setConfirmingId(null); }
  };

  return (
    <div className="bg-amber-50 rounded-xl border border-amber-200 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm">🔗</span>
          <span className="text-xs font-semibold text-amber-800">
            Cobranças com link aguardando pagamento ({pending.length})
          </span>
        </div>
        <button onClick={load} disabled={loading} className="text-amber-600 hover:text-amber-800">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>
      <p className="text-[10px] text-amber-700">
        Confirmação automática (webhook) ainda não validada em produção — confira no painel da
        InfinitePay se o cliente pagou e use "Marcar como pago" para dar baixa aqui.
      </p>
      <div className="space-y-1.5">
        {pending.map(p => (
          <div key={p.id} className="bg-white rounded-lg border border-amber-100 p-2 flex items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="text-xs font-medium text-gray-900 truncate">
                {p.id} · {p.payer_name || '(sem nome)'} · {fmtMoney(p.total_value)}
              </div>
              <div className="text-[10px] text-gray-400">
                {p.item_count} item{p.item_count !== 1 ? 's' : ''} ·{' '}
                {p.created_at ? new Date(p.created_at).toLocaleDateString('pt-BR') : ''}
              </div>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                onClick={() => { navigator.clipboard.writeText(p.payment_link); toast({ title: 'Link copiado!' }); }}
                className="px-2 py-1 text-[10px] bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200">
                Copiar link
              </button>
              <button
                onClick={() => {
                  const phone = p.payer_phone ? p.payer_phone.replace(/\D/g, '') : '';
                  const msg = encodeURIComponent(`Olá${p.payer_name ? ' ' + p.payer_name.split(' ')[0] : ''}! Segue o link para pagamento de ${fmtMoney(p.total_value)}:\n${p.payment_link}`);
                  window.open(`https://wa.me/${phone ? '55' + phone : ''}?text=${msg}`, '_blank');
                }}
                className="px-2 py-1 text-[10px] bg-green-100 text-green-700 rounded-md hover:bg-green-200">
                WhatsApp
              </button>
              <button
                onClick={() => markPaid(p.id)}
                disabled={confirmingId === p.id}
                className="px-2 py-1 text-[10px] bg-emerald-600 text-white rounded-md hover:bg-emerald-700 disabled:opacity-50">
                {confirmingId === p.id ? '...' : 'Marcar pago'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Financial() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterPay, setFilterPay] = useState('');
  const [payModal, setPayModal] = useState(null);
  const [selected, setSelected] = useState(new Map());
  const [consolidateOpen, setConsolidateOpen] = useState(false);

  // ── Filtro de período ──────────────────────────────────────────────────────
  const [periodPreset, setPeriodPreset] = useState('month'); // padrão: mês atual
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');

  const dateRange = useMemo(
    () => buildDateRange(periodPreset, customFrom, customTo),
    [periodPreset, customFrom, customTo]
  );

  const activePeriodLabel = useMemo(
    () => periodLabel(periodPreset, customFrom, customTo),
    [periodPreset, customFrom, customTo]
  );

  // ── Seleção de itens ──────────────────────────────────────────────────────
  const toggleSelect = (doc) => setSelected(prev => {
    const m = new Map(prev);
    if (m.has(doc.item.id)) m.delete(doc.item.id); else m.set(doc.item.id, doc);
    return m;
  });
  const selectGroup = (docs, on) => setSelected(prev => {
    const m = new Map(prev);
    docs.forEach(d => { if (on) m.set(d.item.id, d); else m.delete(d.item.id); });
    return m;
  });
  const clearSelection = () => setSelected(new Map());
  const selectedIds   = useMemo(() => new Set(selected.keys()), [selected]);
  const selectedDocs  = useMemo(() => [...selected.values()], [selected]);
  const selectedTotal = selectedDocs.reduce((s, d) => s + ((d.item.total_value||0) - (d.item.paid_value||0)), 0);

  // ── Carga ─────────────────────────────────────────────────────────────────
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('superdry_token');
      const statuses = ['ENTREGUE', 'EXECUTADO', 'BUSCOU'];
      const results = await Promise.all(
        statuses.map(s =>
          fetch(`${BACKEND_URL}/api/items?status=${s}&limit=500`, {
            headers: { Authorization: `Bearer ${token}` }
          }).then(r => r.json())
        )
      );
      const all = results.flatMap(r => r.items || []);
      setItems(all);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  // ── Aplicar filtro de período ─────────────────────────────────────────────
  const periodFilteredItems = useMemo(() => {
    if (!dateRange) return items;
    return items.filter(doc => {
      const d = itemRefDate(doc);
      if (dateRange.from && d < dateRange.from) return false;
      if (dateRange.to   && d > dateRange.to)   return false;
      return true;
    });
  }, [items, dateRange]);

  // ── KPIs (calculados sobre itens do período) ──────────────────────────────
  const totals = useMemo(() => ({
    total:    periodFilteredItems.reduce((s, d) => s + (d.item.total_value || 0), 0),
    received: periodFilteredItems.reduce((s, d) => s + (d.item.paid_value  || 0), 0),
    pending:  periodFilteredItems
                .filter(d => ['PENDENTE','PARCIAL','INADIMPLENTE'].includes(d.item.payment_status))
                .reduce((s, d) => s + ((d.item.total_value || 0) - (d.item.paid_value || 0)), 0),
    count: {
      total:    periodFilteredItems.length,
      pago:     periodFilteredItems.filter(d => d.item.payment_status === 'PAGO').length,
      pendente: periodFilteredItems.filter(d => d.item.payment_status === 'PENDENTE').length,
      parcial:  periodFilteredItems.filter(d => d.item.payment_status === 'PARCIAL').length,
    }
  }), [periodFilteredItems]);

  // ── Agrupamento por cliente (sobre itens do período) ─────────────────────
  const grouped = useMemo(() => {
    let d = periodFilteredItems;
    if (filterPay) d = d.filter(doc => doc.item.payment_status === filterPay);
    if (search) {
      const q = search.toLowerCase();
      d = d.filter(doc =>
        (doc.item.client_name || '').toLowerCase().includes(q) ||
        (doc.item.service_name || '').toLowerCase().includes(q) ||
        (doc.budget_id || '').toLowerCase().includes(q)
      );
    }

    const map = new Map();
    for (const doc of d) {
      const name = doc.item.client_name || '(sem nome)';
      if (!map.has(name)) map.set(name, []);
      map.get(name).push(doc);
    }

    const order = (docs) => {
      if (docs.every(d => ['PAGO','CORTESIA'].includes(d.item.payment_status))) return 2;
      if (docs.some(d => (d.item.paid_value || 0) > 0)) return 1;
      return 0;
    };

    return [...map.entries()]
      .sort((a, b) => order(a[1]) - order(b[1]) || a[0].localeCompare(b[0]))
      .map(([name, docs]) => ({ name, docs }));
  }, [periodFilteredItems, filterPay, search]);

  // ── Presets de período ────────────────────────────────────────────────────
  const presets = [
    { v: 'today',     label: 'Hoje' },
    { v: 'week',      label: 'Semana' },
    { v: 'month',     label: 'Este mês' },
    { v: 'lastmonth', label: 'Mês anterior' },
    { v: 'custom',    label: '📅 Personalizado' },
    { v: '',          label: 'Todos' },
  ];

  return (
    <div className="space-y-4">

      {/* ── Seletor de período ── */}
      <div className="bg-white rounded-xl border border-gray-200 p-3 space-y-2">
        <div className="flex items-center gap-2">
          <Calendar className="w-3.5 h-3.5 text-gray-400 shrink-0" />
          <span className="text-xs font-medium text-gray-600">Período</span>
          {periodPreset !== '' && (
            <span className="text-[10px] text-blue-600 font-medium bg-blue-50 px-2 py-0.5 rounded-full">
              {activePeriodLabel}
            </span>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {presets.map(p => (
            <button key={p.v} onClick={() => setPeriodPreset(p.v)}
              className={`px-3 py-1 text-xs rounded-full font-medium border transition ${
                periodPreset === p.v
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
              }`}>
              {p.label}
            </button>
          ))}
        </div>
        {periodPreset === 'custom' && (
          <div className="flex items-center gap-2 pt-1">
            <div className="flex-1">
              <label className="block text-[10px] text-gray-500 mb-0.5">De</label>
              <input type="date" value={customFrom} onChange={e => setCustomFrom(e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-xs" />
            </div>
            <div className="flex-1">
              <label className="block text-[10px] text-gray-500 mb-0.5">Até</label>
              <input type="date" value={customTo} onChange={e => setCustomTo(e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-xs" />
            </div>
            {(customFrom || customTo) && (
              <button onClick={() => { setCustomFrom(''); setCustomTo(''); }}
                className="mt-4 text-gray-400 hover:text-gray-600">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
        <p className="text-[10px] text-gray-400">
          Referência: data do pagamento mais recente do item ou data de atualização do status.
        </p>
      </div>

      {/* ── Cobranças InfinitePay com link pendente ── */}
      <PendingGatewayPayments />

      {/* ── KPIs do período ── */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-white rounded-xl border border-gray-200 p-3 text-center">
          <div className="text-xs text-gray-500 mb-1">Faturado</div>
          <div className="text-lg font-bold text-gray-900">{fmtMoney(totals.total)}</div>
          <div className="text-[10px] text-gray-400">{totals.count.total} serviço{totals.count.total !== 1 ? 's' : ''}</div>
        </div>
        <div className="bg-white rounded-xl border border-emerald-200 p-3 text-center">
          <div className="text-xs text-emerald-600 mb-1">Recebido</div>
          <div className="text-lg font-bold text-emerald-700">{fmtMoney(totals.received)}</div>
          <div className="text-[10px] text-gray-400">{totals.count.pago} pago{totals.count.pago !== 1 ? 's' : ''}</div>
        </div>
        <div className="bg-white rounded-xl border border-red-200 p-3 text-center">
          <div className="text-xs text-red-500 mb-1">À Receber</div>
          <div className="text-lg font-bold text-red-600">{fmtMoney(totals.pending)}</div>
          <div className="text-[10px] text-gray-400">
            {totals.count.pendente} pend. · {totals.count.parcial} parc.
          </div>
        </div>
      </div>

      {/* ── Filtros de busca + status ── */}
      <div className="bg-white rounded-xl border border-gray-200 p-3 space-y-2">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Buscar cliente, serviço ou orçamento…"
              className="w-full pl-8 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
          </div>
          <button onClick={load} disabled={loading}
            className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {[
            { v: '', label: 'Todos' },
            { v: 'PENDENTE',     label: '🔴 À Receber' },
            { v: 'PARCIAL',      label: '⚡ Parcial' },
            { v: 'PAGO',         label: '✅ Pagos' },
            { v: 'INADIMPLENTE', label: '⚠️ Inadimplente' },
            { v: 'CORTESIA',     label: '🎁 Cortesia' },
          ].map(f => (
            <button key={f.v} onClick={() => setFilterPay(f.v)}
              className={`px-3 py-1 text-xs rounded-full font-medium border transition ${
                filterPay === f.v
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
              }`}>
              {f.label}
            </button>
          ))}
        </div>
        {grouped.length > 0 && (
          <p className="text-[10px] text-gray-400">
            {grouped.length} cliente{grouped.length > 1 ? 's' : ''} · {periodFilteredItems.length} serviço{periodFilteredItems.length > 1 ? 's' : ''} no período
            {items.length !== periodFilteredItems.length && ` (${items.length} no total)`}
          </p>
        )}
      </div>

      {/* ── Lista agrupada ── */}
      {loading ? (
        <div className="flex justify-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      ) : grouped.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <DollarSign className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Nenhum registro encontrado.</p>
          {periodPreset !== '' ? (
            <p className="text-xs mt-1">Tente ampliar o período ou selecionar "Todos".</p>
          ) : (
            <p className="text-xs mt-1">Itens aparecem aqui após serem marcados como Entregue ou Executado.</p>
          )}
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden mb-20">
          {grouped.map(({ name, docs }) => (
            <div key={name}>
              <ClientListHeader
                clientName={name}
                docs={docs}
                selectedIds={selectedIds}
                onSelectGroup={selectGroup}
              />
              {docs.map((doc, i) => (
                <ItemListRow
                  key={`${doc.budget_id}-${doc.item.id}-${i}`}
                  doc={doc}
                  onRegisterPayment={setPayModal}
                  selected={selectedIds.has(doc.item.id)}
                  onToggleSelect={toggleSelect}
                />
              ))}
            </div>
          ))}
        </div>
      )}

      {/* ── Barra flutuante de cobrança consolidada ── */}
      {selectedDocs.length > 0 && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 bg-white shadow-2xl border border-emerald-200 rounded-2xl px-4 py-3 flex items-center gap-4 w-[calc(100%-2rem)] max-w-lg">
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-gray-900">
              {selectedDocs.length} serviço{selectedDocs.length > 1 ? 's' : ''} selecionado{selectedDocs.length > 1 ? 's' : ''}
            </div>
            <div className="text-xs text-gray-500">
              Total a receber: <strong className="text-emerald-700">{fmtMoney(selectedTotal)}</strong>
              {new Set(selectedDocs.map(d => d.item.client_name)).size > 1 && ' · vários clientes'}
            </div>
          </div>
          <button onClick={clearSelection} className="text-xs text-gray-400 hover:text-gray-600">limpar</button>
          <button onClick={() => setConsolidateOpen(true)}
            className="px-4 py-2 bg-emerald-600 text-white text-sm font-semibold rounded-xl hover:bg-emerald-700">
            Cobrar selecionados
          </button>
        </div>
      )}

      {consolidateOpen && (
        <ConsolidatedPaymentModal
          docs={selectedDocs}
          total={selectedTotal}
          onClose={() => setConsolidateOpen(false)}
          onDone={() => { setConsolidateOpen(false); clearSelection(); load(); }}
        />
      )}

      {payModal && (
        <PaymentModal
          item={payModal.item}
          onClose={() => setPayModal(null)}
          onSaved={load}
        />
      )}
    </div>
  );
}

export default Financial;
