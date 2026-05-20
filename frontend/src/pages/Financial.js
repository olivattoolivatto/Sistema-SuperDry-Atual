import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  DollarSign, CheckCircle, Clock, AlertCircle, RefreshCw,
  Search, Filter, CreditCard, X, ChevronDown, ChevronUp
} from 'lucide-react';
import { itemsApi } from '../services/api';
import { fmtMoney } from './budgets/_constants';
import { toast } from '../hooks/use-toast';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

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

function PaymentModal({ item, onClose, onSaved }) {
  const [methods, setMethods] = useState([]);
  const [method, setMethod] = useState('DINHEIRO');
  const [value, setValue] = useState('');
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
        body: JSON.stringify({ method, value: parseFloat(value) }),
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
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            <button type="button" onClick={() => setValue(remaining.toFixed(2))}
              className="px-3 py-2 text-xs bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">
              Total
            </button>
          </div>
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

function ItemCard({ doc, onRegisterPayment }) {
  const [expanded, setExpanded] = useState(false);
  const item = doc.item;
  const ps = PAY_STATUS[item.payment_status] || PAY_STATUS.PENDENTE;
  const ss = STATUS_LABEL[item.status] || { label: item.status, color: 'bg-gray-100 text-gray-700' };
  const pct = item.total_value > 0 ? Math.min(100, ((item.paid_value || 0) / item.total_value) * 100) : 0;

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="p-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900 truncate">{item.client_name}</p>
            <p className="text-xs text-gray-500 truncate">{item.service_name}</p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-sm font-bold text-gray-900">{fmtMoney(item.total_value)}</p>
            {item.paid_value > 0 && item.paid_value < item.total_value && (
              <p className="text-[10px] text-gray-400">pago {fmtMoney(item.paid_value)}</p>
            )}
          </div>
        </div>

        {/* Barra de progresso */}
        {item.total_value > 0 && (
          <div className="mt-2 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div className="h-full bg-green-500 rounded-full transition-all"
              style={{ width: `${pct}%` }} />
          </div>
        )}

        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${ss.color}`}>{ss.label}</span>
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${ps.color}`}>
            {ps.icon} {ps.label}
          </span>
          {doc.budget_payment_method && (
            <span className="text-[10px] text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
              {doc.budget_payment_method.replace('PIX_CNPJ_', 'PIX ').replace('CREDITO_', 'Créd. ').replace('_', ' ')}
            </span>
          )}
        </div>

        <div className="mt-2 flex items-center justify-between">
          <button onClick={() => setExpanded(v => !v)}
            className="text-[10px] text-gray-400 flex items-center gap-0.5">
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {item.payment_records?.length || 0} pagamento(s)
          </button>
          {item.payment_status !== 'PAGO' && item.payment_status !== 'CORTESIA' && (
            <button
              onClick={() => onRegisterPayment(doc)}
              className="flex items-center gap-1 px-3 py-1 bg-green-600 text-white text-xs rounded-lg hover:bg-green-700">
              <CreditCard className="w-3 h-3" /> Registrar Pagamento
            </button>
          )}
        </div>
      </div>

      {expanded && item.payment_records?.length > 0 && (
        <div className="border-t border-gray-100 px-3 py-2 space-y-1 bg-gray-50">
          {item.payment_records.map((p, i) => (
            <div key={i} className="flex items-center justify-between text-xs text-gray-600">
              <span>{new Date(p.paid_at).toLocaleDateString('pt-BR')} · {p.method}</span>
              <span className="font-semibold text-green-700">{fmtMoney(p.value)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function Financial() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterPay, setFilterPay] = useState('');  // '' | PENDENTE | PAGO | PARCIAL
  const [payModal, setPayModal] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('superdry_token');
      // Busca itens ENTREGUE, EXECUTADO e BUSCOU
      const statuses = ['ENTREGUE', 'EXECUTADO', 'BUSCOU'];
      const results = await Promise.all(
        statuses.map(s =>
          fetch(`${BACKEND_URL}/api/items?status=${s}&limit=500`, {
            headers: { Authorization: `Bearer ${token}` }
          }).then(r => r.json())
        )
      );
      const all = results.flatMap(r => r.items || []);
      // Ordenar: PENDENTE primeiro, depois PARCIAL, depois PAGO
      const order = { PENDENTE: 0, INADIMPLENTE: 1, PARCIAL: 2, PAGO: 3, CORTESIA: 4 };
      all.sort((a, b) => (order[a.item.payment_status] ?? 99) - (order[b.item.payment_status] ?? 99));
      setItems(all);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    let d = items;
    if (filterPay) d = d.filter(doc => doc.item.payment_status === filterPay);
    if (search) {
      const q = search.toLowerCase();
      d = d.filter(doc =>
        (doc.item.client_name || '').toLowerCase().includes(q) ||
        (doc.item.service_name || '').toLowerCase().includes(q) ||
        (doc.budget_id || '').toLowerCase().includes(q)
      );
    }
    return d;
  }, [items, filterPay, search]);

  const totals = useMemo(() => ({
    total:    items.reduce((s, d) => s + (d.item.total_value || 0), 0),
    received: items.reduce((s, d) => s + (d.item.paid_value || 0), 0),
    pending:  items.filter(d => ['PENDENTE','PARCIAL','INADIMPLENTE'].includes(d.item.payment_status))
                   .reduce((s, d) => s + ((d.item.total_value || 0) - (d.item.paid_value || 0)), 0),
    count:    { pago: items.filter(d => d.item.payment_status === 'PAGO').length,
                pendente: items.filter(d => d.item.payment_status === 'PENDENTE').length,
                parcial: items.filter(d => d.item.payment_status === 'PARCIAL').length }
  }), [items]);

  return (
    <div className="space-y-4">
      {/* Resumo financeiro */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-white rounded-xl border border-gray-200 p-3 text-center">
          <div className="text-xs text-gray-500 mb-1">Total Faturado</div>
          <div className="text-lg font-bold text-gray-900">{fmtMoney(totals.total)}</div>
          <div className="text-[10px] text-gray-400">{items.length} serviços</div>
        </div>
        <div className="bg-white rounded-xl border border-emerald-200 p-3 text-center">
          <div className="text-xs text-emerald-600 mb-1">Recebido</div>
          <div className="text-lg font-bold text-emerald-700">{fmtMoney(totals.received)}</div>
          <div className="text-[10px] text-gray-400">{totals.count.pago} pagos</div>
        </div>
        <div className="bg-white rounded-xl border border-red-200 p-3 text-center">
          <div className="text-xs text-red-500 mb-1">À Receber</div>
          <div className="text-lg font-bold text-red-600">{fmtMoney(totals.pending)}</div>
          <div className="text-[10px] text-gray-400">
            {totals.count.pendente} pend. · {totals.count.parcial} parc.
          </div>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-gray-200 p-3 space-y-2">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Buscar cliente, serviço, orçamento…"
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
            { v: 'PENDENTE', label: '🔴 À Receber' },
            { v: 'PARCIAL',  label: '⚡ Parcial' },
            { v: 'PAGO',     label: '✅ Pagos' },
            { v: 'INADIMPLENTE', label: '⚠️ Inadimplente' },
            { v: 'CORTESIA', label: '🎁 Cortesia' },
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
      </div>

      {/* Lista */}
      {loading ? (
        <div className="flex justify-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <DollarSign className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Nenhum registro encontrado.</p>
          <p className="text-xs mt-1">Itens aparecem aqui após serem marcados como Entregue ou Executado.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((doc, i) => (
            <ItemCard key={`${doc.budget_id}-${doc.item.id}-${i}`}
              doc={doc}
              onRegisterPayment={setPayModal} />
          ))}
        </div>
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
