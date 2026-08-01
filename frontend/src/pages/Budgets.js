import React, { useEffect, useMemo, useState, useRef, useCallback } from 'react';
import {
  Plus, Search, FileText, Loader2, Edit2, Trash2,
  Download, MessageCircle, AlertTriangle, ChevronDown, ChevronUp,
  User, X, ArrowUpDown, ArrowUp, ArrowDown, Archive, CheckCircle, Clock, XCircle,
} from 'lucide-react';
import { budgetsApi, clientsApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import BudgetEditor from './budgets/BudgetEditor';
import ItemDetailDrawer from './budgets/ItemDetailDrawer';
import {
  STATUS_COLOR, PAYMENT_STATUS_COLOR, fmtMoney, normalize,
} from './budgets/_constants';
import { BACKEND_URL } from '../lib/backendUrl';

// ── Status administrativo do orçamento ───────────────────────────────────────
const BUDGET_STATUS_CONFIG = {
  RASCUNHO:  { label: 'Rascunho',  color: 'bg-gray-100 text-gray-600' },
  ENVIADO:   { label: 'Enviado',   color: 'bg-yellow-100 text-yellow-700' },
  APROVADO:  { label: 'Aprovado',  color: 'bg-green-100 text-green-700' },
  CANCELADO: { label: 'Cancelado', color: 'bg-red-100 text-red-600' },
  ARQUIVADO: { label: 'Arquivado', color: 'bg-gray-200 text-gray-500' },
};

async function changeBudgetStatus(budgetId, newStatus) {
  const token = localStorage.getItem('superdry_token');
  const r = await fetch(`${BACKEND_URL}/api/budgets/${budgetId}/budget-status`, {
    method: 'PUT',
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ budget_status: newStatus }),
  });
  if (!r.ok) {
    let detail = 'Erro ao atualizar status';
    try { const d = await r.json(); detail = d.detail || detail; } catch {}
    throw new Error(`${r.status}: ${detail}`);
  }
  return r.json();
}

// ── Linha da tabela ───────────────────────────────────────────────────────────
function BudgetRow({ budget, onEdit, onDelete, onItemClick, onPDF, onWhats, onStatusChanged, isAdmin }) {
  const [expanded, setExpanded] = useState(false);
  const [changingStatus, setChangingStatus] = useState(false);
  const items = budget.items || [];

  const budgetStatus = budget.budget_status || 'APROVADO'; // null = legado = aprovado
  const statusCfg = BUDGET_STATUS_CONFIG[budgetStatus] || BUDGET_STATUS_CONFIG.APROVADO;

  const handleStatusChange = async (newStatus) => {
    setChangingStatus(true);
    try {
      await changeBudgetStatus(budget.id, newStatus);
      if (onStatusChanged) onStatusChanged();
    } catch (e) {
      alert('Erro ao alterar status: ' + e.message);
    } finally { setChangingStatus(false); }
  };
  const paid   = items.reduce((a, i) => a + Number(i.paid_value || 0), 0);
  const total  = Number(budget.total_value || 0);
  const allPaid = items.length > 0 && items.every(i => ['PAGO','CORTESIA'].includes(i.payment_status));
  const anyPaid = paid > 0;
  const anyPending = items.some(i => i.payment_status === 'PENDENTE');

  const payBadge = allPaid
    ? <span className="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full font-semibold">PAGO</span>
    : anyPaid
      ? <span className="text-[10px] bg-sky-100 text-sky-700 px-1.5 py-0.5 rounded-full font-semibold">PARCIAL</span>
      : <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full">PENDENTE</span>;

  return (
    <>
      <tr className="border-b border-gray-100 hover:bg-gray-50 transition group">
        {/* ID */}
        <td className="px-3 py-2.5 whitespace-nowrap">
          <span className="text-[11px] font-mono font-semibold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">{budget.id}</span>
        </td>
        {/* Cliente */}
        <td className="px-3 py-2.5">
          <div className="font-medium text-gray-900 text-sm truncate max-w-[180px]">{budget.client_name}</div>
          <div className="text-[10px] text-gray-400">{budget.salesperson}</div>
        </td>
        {/* Itens */}
        <td className="px-3 py-2.5">
          <button onClick={() => setExpanded(v => !v)}
            className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium">
            {items.length} item{items.length !== 1 ? 's' : ''}
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </td>
        {/* Valor */}
        <td className="px-3 py-2.5 whitespace-nowrap text-right">
          <div className="font-bold text-emerald-700 text-sm">{fmtMoney(total)}</div>
          {anyPaid && <div className="text-[10px] text-gray-400">pago {fmtMoney(paid)}</div>}
        </td>
        {/* Status pgto */}
        <td className="px-3 py-2.5 whitespace-nowrap">{payBadge}</td>
        {/* Data */}
        <td className="px-3 py-2.5 whitespace-nowrap text-xs text-gray-500">
          {new Date(budget.created_at).toLocaleDateString('pt-BR')}
        </td>
        {/* Status */}
        <td className="px-3 py-2.5 whitespace-nowrap">
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${statusCfg.color}`}>
            {statusCfg.label}
          </span>
        </td>
        {/* Ações */}
        <td className="px-3 py-2.5 whitespace-nowrap">
          <div className="flex items-center gap-1">
            <button onClick={() => onEdit(budget)} title="Editar"
              className="p-1.5 rounded hover:bg-amber-50 text-amber-600 hover:text-amber-700">
              <Edit2 className="w-3.5 h-3.5" />
            </button>
            <button onClick={() => onPDF(budget)} title="PDF"
              className="p-1.5 rounded hover:bg-blue-50 text-blue-600 hover:text-blue-700">
              <Download className="w-3.5 h-3.5" />
            </button>
            <button onClick={() => onWhats(budget)} title="WhatsApp"
              className="p-1.5 rounded hover:bg-emerald-50 text-emerald-600 hover:text-emerald-700">
              <MessageCircle className="w-3.5 h-3.5" />
            </button>
            {/* Ações de status rápidas */}
            {budgetStatus !== 'APROVADO' && budgetStatus !== 'ARQUIVADO' && (
              <button
                onClick={() => handleStatusChange('APROVADO')}
                disabled={changingStatus}
                title="Marcar como Aprovado"
                className="p-1.5 rounded hover:bg-green-50 text-green-600 hover:text-green-700 disabled:opacity-40"
              >
                <CheckCircle className="w-3.5 h-3.5" />
              </button>
            )}
            {budgetStatus !== 'ARQUIVADO' && (
              <button
                onClick={() => handleStatusChange('ARQUIVADO')}
                disabled={changingStatus}
                title="Arquivar"
                className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 disabled:opacity-40"
              >
                <Archive className="w-3.5 h-3.5" />
              </button>
            )}
            {budgetStatus === 'ARQUIVADO' && (
              <button
                onClick={() => handleStatusChange('APROVADO')}
                disabled={changingStatus}
                title="Restaurar"
                className="p-1.5 rounded hover:bg-green-50 text-green-600 hover:text-green-700 disabled:opacity-40"
              >
                <CheckCircle className="w-3.5 h-3.5" />
              </button>
            )}
            <button onClick={() => onDelete(budget)} title="Excluir"
              className="p-1.5 rounded hover:bg-rose-50 text-rose-500 hover:text-rose-700">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </td>
      </tr>
      {/* Itens expandidos */}
      {expanded && (
        <tr className="bg-blue-50/40 border-b border-gray-100">
          <td colSpan={7} className="px-6 py-2">
            <div className="space-y-1">
              {items.map(it => (
                <button key={it.id} onClick={() => onItemClick(it.id)}
                  className="w-full flex items-center gap-2 bg-white hover:bg-blue-50 rounded-lg px-3 py-1.5 text-left text-xs border border-gray-100 transition">
                  <span className="font-mono text-[10px] text-gray-400 w-36 shrink-0">{it.id}</span>
                  <span className="flex-1 truncate font-medium text-gray-800">{it.service_name}</span>
                  {it.area_m2 && <span className="text-[10px] text-gray-400 shrink-0">{it.area_m2}m²</span>}
                  <span className={`px-1.5 py-0.5 rounded text-[10px] shrink-0 ${STATUS_COLOR[it.status] || 'bg-gray-100 text-gray-700'}`}>
                    {it.status}
                  </span>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] shrink-0 ${PAYMENT_STATUS_COLOR[it.payment_status] || 'bg-gray-100 text-gray-700'}`}>
                    {it.payment_status || 'PENDENTE'}
                  </span>
                  <span className="font-semibold text-gray-900 whitespace-nowrap shrink-0">{fmtMoney(it.total_value)}</span>
                </button>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ── Cadastro Rápido ──────────────────────────────────────────────────────────
function QuickRegisterModal({ initialName = '', onClose, onCreated }) {
  const [name, setName] = useState(initialName);
  const [phone, setPhone] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const save = async () => {
    if (!name.trim()) { setError('Nome obrigatório.'); return; }
    setSaving(true);
    try {
      const r = await clientsApi.create({
        name: name.trim(),
        phone_primary: phone.trim() || '(sem telefone)',
        address: { full_address: '', neighborhood: '', city: '', state: '', latitude: null, longitude: null },
      });
      onCreated(r.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Erro ao cadastrar.');
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Cadastro Rápido</h3>
          <button onClick={onClose}><X className="w-5 h-5 text-gray-400" /></button>
        </div>
        <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          Endereço não informado — este cliente não poderá ser incluído em rotas até o endereço ser cadastrado.
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Nome *</label>
          <input autoFocus value={name} onChange={e => setName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && save()}
            placeholder="Nome do cliente"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Telefone (opcional)</label>
          <input value={phone} onChange={e => setPhone(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && save()}
            placeholder="(65) 9 9999-9999"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" />
        </div>
        {error && <p className="text-xs text-red-600">{error}</p>}
        <div className="flex gap-2 pt-1">
          <button onClick={onClose}
            className="flex-1 py-2 rounded-xl border border-gray-300 text-sm text-gray-700">Cancelar</button>
          <button onClick={save} disabled={saving}
            className="flex-1 py-2 rounded-xl bg-blue-600 text-white text-sm font-semibold disabled:opacity-50">
            {saving ? 'Salvando…' : 'Cadastrar e Abrir Orçamento'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Smart Search Bar ──────────────────────────────────────────────────────────
function SmartSearchBar({ budgets, search, setSearch, onOpenBudget, onQuickCreate, onOpenClientBudget }) {
  const [clients, setClients] = useState([]);
  const [open, setOpen] = useState(false);
  const [loadingClients, setLoadingClients] = useState(false);
  const debRef = useRef(null);
  const boxRef = useRef(null);
  const q = normalize(search);

  // Debounce client search
  useEffect(() => {
    if (debRef.current) clearTimeout(debRef.current);
    if (!q || q.length < 2) { setClients([]); return; }
    debRef.current = setTimeout(async () => {
      setLoadingClients(true);
      try {
        const r = await clientsApi.getAll({ limit: 8 });
        const all = r.data || [];
        setClients(all.filter(c =>
          normalize(c.name).includes(q) ||
          (c.phone_primary || '').replace(/\D/g, '').includes(search.replace(/\D/g, ''))
        ).slice(0, 5));
      } catch { setClients([]); }
      setLoadingClients(false);
    }, 300);
  }, [q]);

  // Close on outside click
  useEffect(() => {
    const h = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  const matchedBudgets = useMemo(() => {
    if (!q) return [];
    return budgets.filter(b =>
      normalize(b.id).includes(q) ||
      normalize(b.client_name || '').includes(q) ||
      (b.items || []).some(it => normalize(it.service_name || '').includes(q))
    ).slice(0, 4);
  }, [budgets, q]);

  const showDropdown = open && q.length >= 2 && (matchedBudgets.length > 0 || clients.length > 0 || true);

  // Clients already with a budget in results → exclude from client section
  const budgetClientIds = new Set(matchedBudgets.map(b => b.client_id));
  const clientsWithoutBudget = clients.filter(c => !budgetClientIds.has(c.id));

  return (
    <div className="relative flex-1" ref={boxRef}>
      <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
      {loadingClients && <Loader2 className="w-3.5 h-3.5 absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 animate-spin" />}
      <input
        value={search}
        onChange={e => { setSearch(e.target.value); setOpen(true); }}
        onFocus={() => q.length >= 2 && setOpen(true)}
        placeholder="Buscar orçamento, cliente ou cadastrar novo…"
        className="w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
      />

      {showDropdown && (
        <div className="absolute z-30 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden max-h-80 overflow-y-auto">
          {/* Orçamentos */}
          {matchedBudgets.length > 0 && (
            <div>
              <div className="px-3 py-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wide bg-gray-50">Orçamentos</div>
              {matchedBudgets.map(b => (
                <button key={b.id} onClick={() => { setOpen(false); onOpenBudget(b); }}
                  className="w-full text-left px-3 py-2 hover:bg-blue-50 border-b border-gray-50 flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-gray-900 truncate">{b.client_name}</div>
                    <div className="text-xs text-gray-400">{b.id} · {b.items?.length || 0} item(s)</div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Clientes cadastrados */}
          {clientsWithoutBudget.length > 0 && (
            <div>
              <div className="px-3 py-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wide bg-gray-50">Clientes cadastrados</div>
              {clientsWithoutBudget.map(c => (
                <button key={c.id} onClick={() => { setOpen(false); setSearch(''); onOpenClientBudget(c); }}
                  className="w-full text-left px-3 py-2 hover:bg-green-50 border-b border-gray-50 flex items-center gap-2">
                  <User className="w-3.5 h-3.5 text-green-500 shrink-0" />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-gray-900 truncate">{c.name}</div>
                    <div className="text-xs text-gray-400">{c.phone_primary} {!c.address?.full_address && '· Sem endereço'}</div>
                  </div>
                  <span className="ml-auto text-[10px] text-green-600 font-medium shrink-0">Novo orçamento</span>
                </button>
              ))}
            </div>
          )}

          {/* Cadastro rápido */}
          <button
            onClick={() => { setOpen(false); onQuickCreate(search); }}
            className="w-full text-left px-3 py-2.5 hover:bg-orange-50 flex items-center gap-2 border-t border-gray-100">
            <Plus className="w-3.5 h-3.5 text-orange-500 shrink-0" />
            <div>
              <div className="text-sm font-medium text-orange-600">Cadastro rápido</div>
              <div className="text-xs text-gray-400">
                {search.trim() ? `Cadastrar "${search.trim()}" e abrir orçamento` : 'Cadastrar novo cliente sem endereço'}
              </div>
            </div>
          </button>
        </div>
      )}
    </div>
  );
}

function getBudgetPayStatus(b) {
  const items = b.items || [];
  if (items.length > 0 && items.every(i => ['PAGO','CORTESIA'].includes(i.payment_status))) return 'PAGO';
  if (items.some(i => (i.paid_value||0) > 0)) return 'PARCIAL';
  return 'PENDENTE';
}

const SORT_COLS = {
  id:           (a, b) => a.id.localeCompare(b.id),
  client_name:  (a, b) => (a.client_name||'').localeCompare(b.client_name||''),
  items:        (a, b) => (a.items?.length||0) - (b.items?.length||0),
  total_value:  (a, b) => (a.total_value||0) - (b.total_value||0),
  payment:      (a, b) => {
    const rank = s => s === 'PAGO' ? 0 : s === 'PARCIAL' ? 1 : 2;
    return rank(getBudgetPayStatus(a)) - rank(getBudgetPayStatus(b));
  },
  created_at:   (a, b) => new Date(a.created_at) - new Date(b.created_at),
};

function SortHeader({ col, label, sort, onSort }) {
  const active = sort.col === col;
  return (
    <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide cursor-pointer select-none hover:text-gray-800 whitespace-nowrap"
      onClick={() => onSort(col)}>
      <span className="flex items-center gap-1">
        {label}
        {active
          ? sort.dir === 'asc' ? <ArrowUp className="w-3 h-3 text-blue-600" /> : <ArrowDown className="w-3 h-3 text-blue-600" />
          : <ArrowUpDown className="w-3 h-3 text-gray-300" />}
      </span>
    </th>
  );
}

export function Budgets() {
  const [budgets, setBudgets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState({ col: 'created_at', dir: 'desc' });
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [itemDetailId, setItemDetailId] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [quickRegisterName, setQuickRegisterName] = useState(null);
  const [preselectedClient, setPreselectedClient] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [statusTab, setStatusTab] = useState('ativos'); // ativos | aguardando | historico | todos
  const [paymentFilter, setPaymentFilter] = useState('todos'); // todos | PENDENTE | PARCIAL | PAGO
  const [migrating, setMigrating] = useState(false);
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';

  const handleSort = (col) => setSort(s =>
    s.col === col ? { col, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { col, dir: 'asc' }
  );

  const load = async () => {
    try {
      setLoading(true);
      setLoadError('');
      const r = await budgetsApi.getAll({ limit: 500 });
      setBudgets(r.data || []);
    } catch (e) {
      console.error(e);
      setLoadError('Não foi possível carregar os orçamentos. Verifique sua conexão e tente novamente.');
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    const q = normalize(search);
    // Filtro por aba de status
    let list = budgets.filter(b => {
      const st = b.budget_status || 'APROVADO'; // legado sem campo = aprovado
      if (statusTab === 'ativos')     return st === 'APROVADO';
      if (statusTab === 'aguardando') return st === 'RASCUNHO' || st === 'ENVIADO';
      if (statusTab === 'historico')  return st === 'CANCELADO' || st === 'ARQUIVADO';
      return true; // todos
    });
    // Filtro por pagamento
    if (paymentFilter !== 'todos') list = list.filter(b => getBudgetPayStatus(b) === paymentFilter);
    // Filtro de busca
    if (q) list = list.filter(b =>
      normalize(b.id).includes(q) ||
      normalize(b.client_name || '').includes(q) ||
      (b.items || []).some(it => normalize(it.id).includes(q) || normalize(it.service_name || '').includes(q))
    );
    const fn = SORT_COLS[sort.col];
    if (fn) list.sort((a, b) => sort.dir === 'asc' ? fn(a, b) : fn(b, a));
    return list;
  }, [budgets, search, sort, statusTab, paymentFilter]);

  // Contagens para badges das abas
  const tabCounts = useMemo(() => ({
    ativos:     budgets.filter(b => (b.budget_status || 'APROVADO') === 'APROVADO').length,
    aguardando: budgets.filter(b => ['RASCUNHO','ENVIADO'].includes(b.budget_status || 'APROVADO') && b.budget_status && b.budget_status !== 'APROVADO').length,
    historico:  budgets.filter(b => ['CANCELADO','ARQUIVADO'].includes(b.budget_status)).length,
    todos:      budgets.length,
  }), [budgets]);

  // Contagens de pagamento (sobre a lista já filtrada por status/busca, sem o filtro de pagamento)
  const payCounts = useMemo(() => {
    const base = budgets.filter(b => {
      const st = b.budget_status || 'APROVADO';
      if (statusTab === 'ativos')     return st === 'APROVADO';
      if (statusTab === 'aguardando') return st === 'RASCUNHO' || st === 'ENVIADO';
      if (statusTab === 'historico')  return st === 'CANCELADO' || st === 'ARQUIVADO';
      return true;
    });
    return {
      todos:    base.length,
      PENDENTE: base.filter(b => getBudgetPayStatus(b) === 'PENDENTE').length,
      PARCIAL:  base.filter(b => getBudgetPayStatus(b) === 'PARCIAL').length,
      PAGO:     base.filter(b => getBudgetPayStatus(b) === 'PAGO').length,
    };
  }, [budgets, statusTab]);

  const openNew = () => { setPreselectedClient(null); setEditing(null); setEditorOpen(true); };
  const openEdit = (b) => { setPreselectedClient(null); setEditing(b); setEditorOpen(true); };

  // Open new budget pre-filled with an existing client
  const openClientBudget = (client) => {
    setPreselectedClient(client);
    setEditing(null);
    setEditorOpen(true);
  };

  // After quick-register, open budget editor with the new client
  const handleQuickCreated = (client) => {
    setQuickRegisterName(null);
    openClientBudget(client);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await budgetsApi.delete(deleteTarget.id);
      setDeleteTarget(null);
      await load();
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao excluir.');
    }
  };

  const handleForceDelete = async () => {
    if (!deleteTarget) return;
    if (!window.confirm(`FORÇAR exclusão de ${deleteTarget.id}? Vínculos de rota serão removidos.`)) return;
    try {
      await budgetsApi.forceDelete(deleteTarget.id);
      setDeleteTarget(null);
      await load();
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao forçar exclusão.');
    }
  };

  const handlePDF = async (b) => {
    try {
      const r = await budgetsApi.generatePDF(b.id);
      const url = window.URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url; a.download = `${b.id}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) { alert('Erro ao gerar PDF'); }
  };

  const handleWhats = async (b) => {
    try {
      const r = await budgetsApi.generateWhatsApp(b.id);
      const url = r.data?.whatsapp_url || r.data?.url;
      if (url) window.open(url, '_blank');
      else alert('URL não retornada');
    } catch (e) { alert('Erro ao gerar mensagem WhatsApp'); }
  };

  const runMigration = async () => {
    if (!window.confirm('Definir status APROVADO em todos os orçamentos sem status? (executar só uma vez)')) return;
    setMigrating(true);
    try {
      const token = localStorage.getItem('superdry_token');
      const r = await fetch(`${BACKEND_URL}/api/budgets/migrate-status`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await r.json();
      alert(data.message || 'Migração concluída');
      await load();
    } catch (e) {
      alert('Erro na migração: ' + e.message);
    } finally { setMigrating(false); }
  };

  const runPartnerMigration = async () => {
    if (!window.confirm('Corrigir execution_mode dos itens de parceiro existentes?\nIsso os remove da tela de Rotas. Executar só uma vez.')) return;
    setMigrating(true);
    try {
      const token = localStorage.getItem('superdry_token');
      const r = await fetch(`${BACKEND_URL}/api/budgets/migrate-partner-execution-mode`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await r.json();
      alert(data.message || 'Migração de parceiros concluída');
      await load();
    } catch (e) {
      alert('Erro na migração de parceiros: ' + e.message);
    } finally { setMigrating(false); }
  };

  return (
    <div className="space-y-3">
      {/* Header / busca */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-3 sm:p-4">
        <div className="flex flex-col sm:flex-row gap-2">
          <SmartSearchBar
            budgets={budgets}
            search={search}
            setSearch={setSearch}
            onOpenBudget={openEdit}
            onOpenClientBudget={openClientBudget}
            onQuickCreate={(name) => setQuickRegisterName(name)}
          />
          <button
            onClick={openNew}
            className="px-4 py-2.5 bg-blue-600 text-white rounded-lg font-medium text-sm flex items-center justify-center gap-2 hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" /> Novo Orçamento
          </button>
        </div>

        {/* Abas de status */}
        <div className="mt-3 flex gap-1 overflow-x-auto">
          {[
            { key: 'ativos',     label: 'Ativos',     icon: <CheckCircle className="w-3 h-3" /> },
            { key: 'aguardando', label: 'Aguardando',  icon: <Clock className="w-3 h-3" /> },
            { key: 'historico',  label: 'Histórico',   icon: <Archive className="w-3 h-3" /> },
            { key: 'todos',      label: 'Todos',       icon: <FileText className="w-3 h-3" /> },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => { setStatusTab(tab.key); setPaymentFilter('todos'); }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                statusTab === tab.key
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {tab.icon}
              {tab.label}
              <span className={`text-[10px] px-1 rounded-full ${statusTab === tab.key ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-500'}`}>
                {tabCounts[tab.key]}
              </span>
            </button>
          ))}
          {isAdmin && (
            <div className="ml-auto flex gap-1">
              <button
                onClick={runMigration}
                disabled={migrating}
                title="Executar uma vez após deploy para definir status nos orçamentos existentes"
                className="px-2 py-1 text-[10px] text-gray-400 hover:text-gray-600 border border-dashed border-gray-300 rounded-lg disabled:opacity-50"
              >
                {migrating ? 'Migrando…' : '⚙ Migrar status'}
              </button>
              <button
                onClick={runPartnerMigration}
                disabled={migrating}
                title="Corrigir itens de parceiro antigos — remove da tela de Rotas. Executar só uma vez."
                className="px-2 py-1 text-[10px] text-orange-400 hover:text-orange-600 border border-dashed border-orange-300 rounded-lg disabled:opacity-50"
              >
                {migrating ? 'Migrando…' : '🤝 Migrar parceiros'}
              </button>
            </div>
          )}
        </div>

        {/* Filtro de pagamento */}
        <div className="mt-2 flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] text-gray-400 font-medium uppercase tracking-wide mr-0.5">Pagamento:</span>
          {[
            { key: 'todos',    label: 'Todos',    cls: 'bg-gray-100 text-gray-600 hover:bg-gray-200',             active: 'bg-gray-600 text-white' },
            { key: 'PENDENTE', label: 'Pendente', cls: 'bg-gray-100 text-gray-600 hover:bg-gray-200',             active: 'bg-gray-500 text-white' },
            { key: 'PARCIAL',  label: 'Parcial',  cls: 'bg-sky-50 text-sky-700 hover:bg-sky-100',                active: 'bg-sky-600 text-white' },
            { key: 'PAGO',     label: 'Pago',     cls: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100',    active: 'bg-emerald-600 text-white' },
          ].map(opt => (
            <button
              key={opt.key}
              onClick={() => setPaymentFilter(opt.key)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition ${
                paymentFilter === opt.key ? opt.active : opt.cls
              }`}
            >
              {opt.label}
              <span className={`text-[10px] px-1 rounded-full ${
                paymentFilter === opt.key ? 'bg-white/20 text-white' : 'bg-white/60 text-gray-500'
              }`}>
                {payCounts[opt.key]}
              </span>
            </button>
          ))}
        </div>

        <div className="mt-1.5 text-xs text-gray-500">
          {filtered.length} orçamento(s){paymentFilter !== 'todos' ? ` · pagamento: ${paymentFilter}` : ''}{search ? ` · busca: "${search}"` : ''}
        </div>
      </div>

      {loadError && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-3 text-sm flex items-center justify-between gap-3">
          <span>{loadError}</span>
          <button
            onClick={load}
            className="shrink-0 px-3 py-1.5 bg-red-600 text-white rounded-lg text-xs font-medium hover:bg-red-700"
          >
            Tentar novamente
          </button>
        </div>
      )}

      {/* Lista */}
      {loading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center text-gray-500">
          <FileText className="w-10 h-10 mx-auto mb-2 text-gray-300" />
          {budgets.length === 0 ? 'Nenhum orçamento cadastrado ainda.' : 'Nenhum orçamento encontrado.'}
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <SortHeader col="id"          label="Orçamento" sort={sort} onSort={handleSort} />
                  <SortHeader col="client_name" label="Cliente"   sort={sort} onSort={handleSort} />
                  <SortHeader col="items"       label="Itens"     sort={sort} onSort={handleSort} />
                  <SortHeader col="total_value" label="Valor"     sort={sort} onSort={handleSort} />
                  <SortHeader col="payment"     label="Pagamento" sort={sort} onSort={handleSort} />
                  <SortHeader col="created_at"  label="Data"      sort={sort} onSort={handleSort} />
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Status</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(b => (
                  <BudgetRow
                    key={b.id}
                    budget={b}
                    onEdit={openEdit}
                    onDelete={(b) => setDeleteTarget(b)}
                    onItemClick={setItemDetailId}
                    onPDF={handlePDF}
                    onWhats={handleWhats}
                    onStatusChanged={load}
                    isAdmin={isAdmin}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Item detail drawer */}
      {itemDetailId && (
        <ItemDetailDrawer
          itemId={itemDetailId}
          onClose={() => setItemDetailId(null)}
          onUpdated={() => load()}
        />
      )}

      {/* Delete confirmation */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-gray-900">Excluir orçamento?</h3>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              <strong>{deleteTarget.id}</strong> — {deleteTarget.client_name}<br />
              Itens em rota/execução não podem ser excluídos.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-medium"
              >
                Cancelar
              </button>
              <button
                onClick={handleDelete}
                className="flex-1 px-4 py-2 rounded-lg bg-rose-600 text-white hover:bg-rose-700 text-sm font-medium"
              >
                Excluir
              </button>
              {user?.role === 'ADMIN' && (
                <button
                  onClick={handleForceDelete}
                  className="flex-1 px-4 py-2 rounded-lg bg-gray-800 text-white hover:bg-gray-900 text-sm font-medium"
                  title="Remove TODOS os rastros: rotas, assignments, eventos, financeiro"
                >
                  Excluir Tudo
                </button>
              )}
            </div>
          </div>
        </div>
      )}
      {/* Quick Register Modal */}
      {quickRegisterName !== null && (
        <QuickRegisterModal
          initialName={quickRegisterName}
          onClose={() => setQuickRegisterName(null)}
          onCreated={handleQuickCreated}
        />
      )}

      {editorOpen && (
        <BudgetEditor
          budget={editing}
          preselectedClient={preselectedClient}
          onClose={() => { setEditorOpen(false); setPreselectedClient(null); }}
          onSaved={() => { load(); }}
        />
      )}
    </div>
  );
}

export default Budgets;
