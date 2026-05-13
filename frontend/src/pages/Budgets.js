import React, { useEffect, useMemo, useState } from 'react';
import {
  Plus, Search, FileText, Loader2, Edit2, Trash2, Eye,
  Download, MessageCircle, AlertTriangle, ChevronRight, Layers,
} from 'lucide-react';
import { budgetsApi } from '../services/api';
import BudgetEditor from './budgets/BudgetEditor';
import ItemDetailDrawer from './budgets/ItemDetailDrawer';
import {
  STATUS_COLOR, PAYMENT_STATUS_COLOR, fmtMoney, normalize,
} from './budgets/_constants';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function BudgetCard({ budget, onEdit, onDelete, onItemClick, onPDF, onWhats }) {
  const [expanded, setExpanded] = useState(false);
  const items = budget.items || [];
  const paid = items.reduce((a, i) => a + Number(i.paid_value || 0), 0);
  const total = Number(budget.total_value || 0);
  const allPaid = items.length > 0 && items.every(i => i.payment_status === 'PAGO' || i.payment_status === 'CORTESIA');
  const anyPaid = paid > 0;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="p-3 sm:p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[11px] font-mono font-semibold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">{budget.id}</span>
              {allPaid && <span className="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded font-semibold">PAGO</span>}
              {!allPaid && anyPaid && <span className="text-[10px] bg-sky-100 text-sky-700 px-1.5 py-0.5 rounded font-semibold">PARCIAL</span>}
            </div>
            <h3 className="font-semibold text-gray-900 truncate">{budget.client_name}</h3>
            <p className="text-xs text-gray-500">
              {items.length} item(ns) • {budget.salesperson} • {new Date(budget.created_at).toLocaleDateString('pt-BR')}
            </p>
          </div>
          <div className="text-right">
            <div className="text-lg sm:text-xl font-bold text-emerald-700">{fmtMoney(total)}</div>
            {anyPaid && (
              <div className="text-[11px] text-gray-500">
                Pago: <span className="text-emerald-700 font-semibold">{fmtMoney(paid)}</span>
              </div>
            )}
          </div>
        </div>

        {/* Mini status dos itens */}
        {items.length > 0 && (
          <button
            onClick={() => setExpanded(v => !v)}
            className="w-full mt-1 flex items-center justify-between text-xs text-blue-700 font-medium py-1"
          >
            <span className="flex items-center gap-1">
              <Layers className="w-3.5 h-3.5" />
              {expanded ? 'Recolher itens' : 'Ver itens'}
            </span>
            <ChevronRight className={`w-4 h-4 transition ${expanded ? 'rotate-90' : ''}`} />
          </button>
        )}

        {expanded && (
          <div className="mt-2 space-y-1">
            {items.map(it => (
              <button
                key={it.id}
                onClick={() => onItemClick(it.id)}
                className="w-full flex items-center gap-2 bg-gray-50 hover:bg-blue-50 rounded-lg px-2 py-1.5 text-left text-xs transition"
              >
                <span className="font-mono text-[10px] text-gray-500">{it.id}</span>
                <span className="flex-1 truncate font-medium text-gray-900">{it.service_name}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] ${STATUS_COLOR[it.status] || 'bg-gray-100 text-gray-700'}`}>
                  {it.status}
                </span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] ${PAYMENT_STATUS_COLOR[it.payment_status] || 'bg-gray-100 text-gray-700'}`}>
                  {it.payment_status || 'PENDENTE'}
                </span>
                <span className="font-semibold text-gray-900 whitespace-nowrap">{fmtMoney(it.total_value)}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-4 border-t border-gray-100">
        <button onClick={() => onEdit(budget)}
          className="py-2 text-xs font-medium text-amber-700 hover:bg-amber-50 flex items-center justify-center gap-1">
          <Edit2 className="w-3.5 h-3.5" /> Editar
        </button>
        <button onClick={() => onPDF(budget)}
          className="py-2 text-xs font-medium text-blue-700 hover:bg-blue-50 flex items-center justify-center gap-1 border-l border-gray-100">
          <Download className="w-3.5 h-3.5" /> PDF
        </button>
        <button onClick={() => onWhats(budget)}
          className="py-2 text-xs font-medium text-emerald-700 hover:bg-emerald-50 flex items-center justify-center gap-1 border-l border-gray-100">
          <MessageCircle className="w-3.5 h-3.5" /> WhatsApp
        </button>
        <button onClick={() => onDelete(budget)}
          className="py-2 text-xs font-medium text-rose-700 hover:bg-rose-50 flex items-center justify-center gap-1 border-l border-gray-100">
          <Trash2 className="w-3.5 h-3.5" /> Excluir
        </button>
      </div>
    </div>
  );
}

export function Budgets() {
  const [budgets, setBudgets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [itemDetailId, setItemDetailId] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      const r = await budgetsApi.getAll({ limit: 500 });
      setBudgets(r.data || []);
    } catch (e) {
      console.error(e);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    const q = normalize(search);
    if (!q) return budgets;
    return budgets.filter(b =>
      normalize(b.id).includes(q) ||
      normalize(b.client_name || '').includes(q) ||
      (b.items || []).some(it => normalize(it.id).includes(q) || normalize(it.service_name || '').includes(q))
    );
  }, [budgets, search]);

  const openNew = () => { setEditing(null); setEditorOpen(true); };
  const openEdit = (b) => { setEditing(b); setEditorOpen(true); };

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

  return (
    <div className="space-y-3">
      {/* Header / busca */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-3 sm:p-4">
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por ORC-, cliente, item…"
              className="w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>
          <button
            onClick={openNew}
            className="px-4 py-2.5 bg-blue-600 text-white rounded-lg font-medium text-sm flex items-center justify-center gap-2 hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" /> Novo Orçamento
          </button>
        </div>
        <div className="mt-2 text-xs text-gray-500">
          {search ? `${filtered.length} de ${budgets.length} orçamento(s)` : `${budgets.length} orçamento(s)`}
        </div>
      </div>

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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {filtered.map(b => (
            <BudgetCard
              key={b.id}
              budget={b}
              onEdit={openEdit}
              onDelete={(b) => setDeleteTarget(b)}
              onItemClick={setItemDetailId}
              onPDF={handlePDF}
              onWhats={handleWhats}
            />
          ))}
        </div>
      )}

      {/* Editor modal */}
      {editorOpen && (
        <BudgetEditor
          budget={editing}
          onClose={() => { setEditorOpen(false); setEditing(null); }}
          onSaved={() => load()}
        />
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
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Budgets;
