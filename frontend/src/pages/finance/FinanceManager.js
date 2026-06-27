import React, { useEffect, useMemo, useState } from 'react';
import {
  Plus, Wallet, CreditCard, Banknote, Landmark, Tag, ListTree, Receipt,
  Pencil, Trash2, X, ChevronRight, AlertTriangle, CheckCircle2, Sparkles,
  Building2, User, Home, TrendingUp, TrendingDown, Filter, Search, Clock,
  ArrowUpDown, CheckCheck, CircleDashed, Layers, Upload, ArrowLeftRight, Check,
} from 'lucide-react';
import { financeAccountsApi, financeCategoriesApi, financeEntriesApi, financeSummaryApi } from '../../services/api';

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmtMoney = (n) => (Number(n) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const todayISO = () => new Date().toISOString().slice(0, 10);
const fmtDateLabel = (iso) => {
  if (!iso) return '-';
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: 'short' });
};

// Identidade visual SuperDry
const BRAND_BLUE = '#1F4E8C';   // Empresa (PJ)
const BRAND_GREEN = '#8CC63F';  // Pessoal (PF)
const AMBOS_COLOR = '#6D5BD0';  // Visão Geral (PF+PJ combinados) — cor própria, nem azul nem verde

// Cor de identidade por ambiente — usada em botões, bordas, cabeçalhos e abas
// para deixar visualmente claro em qual ambiente o usuário está (pedido explícito
// do dono, que mistura bastante PF/PJ por ser MEI).
const SCOPE_COLOR = { EMPRESA: BRAND_BLUE, PESSOAL: BRAND_GREEN, AMBOS: AMBOS_COLOR };
const SCOPE_BG_SOFT = { EMPRESA: `${BRAND_BLUE}15`, PESSOAL: `${BRAND_GREEN}1f`, AMBOS: `${AMBOS_COLOR}15` };
const scopeAccent = (s) => SCOPE_COLOR[s] || AMBOS_COLOR;
const scopeBadgeLabel = (s) => (s === 'EMPRESA' ? 'PJ' : s === 'PESSOAL' ? 'PF' : 'Geral');

const SETTLED_STATUSES = ['PAGO', 'CONCILIADO'];

const ACCOUNT_TYPES = [
  { value: 'CONTA_CORRENTE', label: 'Conta Corrente', icon: Landmark },
  { value: 'CARTAO_CREDITO', label: 'Cartão de Crédito', icon: CreditCard },
  { value: 'DINHEIRO', label: 'Dinheiro', icon: Banknote },
  { value: 'POUPANCA', label: 'Poupança', icon: Landmark },
  { value: 'CONTA_PAGAMENTO', label: 'Conta de Pagamento', icon: Wallet },
];

// Opções de navegação (inclui a Visão Geral combinada). Para formulários de
// conta/lançamento (onde o item precisa de um dono real, PJ ou PF), use ENTRY_SCOPES.
const SCOPES = [
  { value: 'EMPRESA', label: 'Empresa (PJ)', icon: Building2 },
  { value: 'PESSOAL', label: 'Pessoal (PF)', icon: User },
  { value: 'AMBOS', label: 'Visão Geral', icon: Layers },
];
const ENTRY_SCOPES = SCOPES.filter(s => s.value !== 'AMBOS');

const ENTRY_KINDS = [
  { value: 'DESPESA', label: 'Despesa' },
  { value: 'RECEITA', label: 'Receita' },
  { value: 'TRANSFERENCIA', label: 'Transferência' },
];

const PAYMENT_METHODS_FIN = ['PIX', 'CREDITO', 'DEBITO', 'DINHEIRO', 'BOLETO', 'TRANSFERENCIA'];

const STATUS_COLOR = {
  A_CATEGORIZAR: 'bg-amber-100 text-amber-700',
  PENDENTE: 'bg-sky-100 text-sky-700',
  PAGO: 'bg-emerald-100 text-emerald-700',
  CONCILIADO: 'bg-violet-100 text-violet-700',
};

const STATUS_LABEL = {
  A_CATEGORIZAR: 'A Categorizar',
  PENDENTE: 'Pendente',
  PAGO: 'Pago',
  CONCILIADO: 'Conciliado',
};

function Modal({ title, onClose, children, wide = false }) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className={`bg-white rounded-xl shadow-xl w-full ${wide ? 'max-w-2xl' : 'max-w-md'} max-h-[90vh] overflow-y-auto`}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900">{title}</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg"><X className="w-5 h-5 text-gray-400" /></button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

function Field({ label, children, hint }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
      {hint && <p className="text-[11px] text-gray-400 mt-1">{hint}</p>}
    </div>
  );
}

const inputCls = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500';

// ── Modal de Conta ───────────────────────────────────────────────────────────
function AccountModal({ account, defaultScope, onSave, onClose }) {
  const [form, setForm] = useState({
    name: account?.name || '',
    type: account?.type || 'CONTA_CORRENTE',
    scope: account?.scope || defaultScope || 'EMPRESA',
    institution: account?.institution || '',
    holder_document: account?.holder_document || '',
    holder_name: account?.holder_name || '',
    statement_pdf_password: account?.statement_pdf_password || '',
    opening_balance: account?.opening_balance ?? 0,
    credit_limit: account?.credit_limit ?? '',
    closing_day: account?.closing_day ?? '',
    due_day: account?.due_day ?? '',
  });
  const [saving, setSaving] = useState(false);

  const isCard = form.type === 'CARTAO_CREDITO';

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...form,
        opening_balance: parseFloat(form.opening_balance) || 0,
        credit_limit: isCard && form.credit_limit !== '' ? parseFloat(form.credit_limit) : null,
        closing_day: isCard && form.closing_day !== '' ? parseInt(form.closing_day, 10) : null,
        due_day: isCard && form.due_day !== '' ? parseInt(form.due_day, 10) : null,
      };
      await onSave(payload);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={account ? 'Editar Conta' : 'Nova Conta'} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Nome *">
          <input className={inputCls} required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Nubank PJ, Cartão Nubank, Dinheiro..." />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Tipo *">
            <select className={inputCls} value={form.type} onChange={e => setForm(f => ({ ...f, type: e.target.value }))}>
              {ACCOUNT_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </Field>
          <Field label="Escopo *">
            <select className={inputCls} value={form.scope} onChange={e => setForm(f => ({ ...f, scope: e.target.value }))}>
              {ENTRY_SCOPES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </Field>
        </div>
        <Field label="Instituição">
          <input className={inputCls} value={form.institution} onChange={e => setForm(f => ({ ...f, institution: e.target.value }))} placeholder="Nubank, InfinitePay..." />
        </Field>
        <Field
          label="CPF/CNPJ do titular"
          hint="Usado pra detectar automaticamente transferências entre suas próprias contas na importação de extrato — sem isso elas entram como receita/despesa normal."
        >
          <input className={inputCls} value={form.holder_document} onChange={e => setForm(f => ({ ...f, holder_document: e.target.value }))} placeholder="25.995.295/0001-04 ou 016.152.691-85" />
        </Field>
        <Field
          label="Nome do titular (como aparece nos extratos)"
          hint="Fallback usado quando o extrato não traz CPF/CNPJ na descrição (ex: Pix enviado do BB). Precisa de nome e sobrenome pra evitar falso positivo."
        >
          <input className={inputCls} value={form.holder_name} onChange={e => setForm(f => ({ ...f, holder_name: e.target.value }))} placeholder="Diego Cesar Gonçalves Olivatto" />
        </Field>
        <Field
          label="Senha do extrato PDF (se o banco proteger o arquivo)"
          hint="Só preencha se esse banco só manda extrato em PDF protegido por senha (ex: C6 usa os 6 primeiros dígitos do CPF). Deixe vazio se o extrato vier sem senha."
        >
          <input className={inputCls} value={form.statement_pdf_password} onChange={e => setForm(f => ({ ...f, statement_pdf_password: e.target.value }))} placeholder="ex: 016152" />
        </Field>
        <Field label="Saldo inicial (R$)" hint="Saldo informado na data de cadastro da conta.">
          <input type="number" step="0.01" className={inputCls} value={form.opening_balance} onFocus={e => e.target.select()} onChange={e => setForm(f => ({ ...f, opening_balance: e.target.value }))} />
        </Field>
        {isCard && (
          <div className="grid grid-cols-3 gap-3 bg-gray-50 p-3 rounded-lg border border-gray-200">
            <Field label="Limite (R$)">
              <input type="number" step="0.01" className={inputCls} value={form.credit_limit} onFocus={e => e.target.select()} onChange={e => setForm(f => ({ ...f, credit_limit: e.target.value }))} />
            </Field>
            <Field label="Dia fechamento">
              <input type="number" min="1" max="31" className={inputCls} value={form.closing_day} onChange={e => setForm(f => ({ ...f, closing_day: e.target.value }))} />
            </Field>
            <Field label="Dia vencimento">
              <input type="number" min="1" max="31" className={inputCls} value={form.due_day} onChange={e => setForm(f => ({ ...f, due_day: e.target.value }))} />
            </Field>
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg">Cancelar</button>
          <button type="submit" disabled={saving} className="px-4 py-2 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded-lg disabled:opacity-50">{saving ? 'Salvando...' : 'Salvar'}</button>
        </div>
      </form>
    </Modal>
  );
}

// ── Modal de Categoria ───────────────────────────────────────────────────────
function CategoryModal({ category, categories, onSave, onClose }) {
  const [form, setForm] = useState({
    name: category?.name || '',
    kind: category?.kind || 'DESPESA',
    scope: category?.scope || 'AMBOS',
    parent_id: category?.parent_id || '',
  });
  const [saving, setSaving] = useState(false);

  const parentOptions = categories.filter(c => c.kind === form.kind && c.id !== category?.id && !c.parent_id);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave({ ...form, parent_id: form.parent_id || null });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={category ? 'Editar Categoria' : 'Nova Categoria'} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Nome *">
          <input className={inputCls} required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Mercado, Combustível, Impostos..." />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Tipo *">
            <select className={inputCls} value={form.kind} onChange={e => setForm(f => ({ ...f, kind: e.target.value, parent_id: '' }))}>
              <option value="DESPESA">Despesa</option>
              <option value="RECEITA">Receita</option>
            </select>
          </Field>
          <Field
            label="Escopo *"
            hint={category
              ? 'Categorias já criadas são independentes — "Ambos" só existe ao criar.'
              : 'Com "Ambos", duas categorias independentes serão criadas (uma PJ, uma PF) — editar/excluir uma não afeta a outra.'}
          >
            <select className={inputCls} value={form.scope} onChange={e => setForm(f => ({ ...f, scope: e.target.value }))}>
              {!category && <option value="AMBOS">Ambos (PF/PJ)</option>}
              <option value="EMPRESA">Empresa (PJ)</option>
              <option value="PESSOAL">Pessoal (PF)</option>
            </select>
          </Field>
        </div>
        <Field label="Categoria pai" hint="Opcional — para criar uma hierarquia (ex: Casa > Limpeza).">
          <select className={inputCls} value={form.parent_id} onChange={e => setForm(f => ({ ...f, parent_id: e.target.value }))}>
            <option value="">Nenhuma (categoria raiz)</option>
            {parentOptions.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </Field>
        <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg">Cancelar</button>
          <button type="submit" disabled={saving} className="px-4 py-2 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded-lg disabled:opacity-50">{saving ? 'Salvando...' : 'Salvar'}</button>
        </div>
      </form>
    </Modal>
  );
}

// ── Editor de splits (linhas por categoria) ─────────────────────────────────
function SplitsEditor({ splits, setSplits, categories, totalValue }) {
  const sum = useMemo(() => splits.reduce((acc, s) => acc + (parseFloat(s.value) || 0), 0), [splits]);
  const balanced = Math.abs(sum - (parseFloat(totalValue) || 0)) <= 0.01;

  const addRow = () => setSplits(s => [...s, { category_id: '', description: '', value: '' }]);
  const updateRow = (idx, field, value) => setSplits(s => s.map((row, i) => i === idx ? { ...row, [field]: value } : row));
  const removeRow = (idx) => setSplits(s => s.filter((_, i) => i !== idx));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-600">Divisão por categoria</span>
        <button type="button" onClick={addRow} className="text-xs text-blue-600 hover:underline flex items-center gap-1">
          <Plus className="w-3 h-3" /> Adicionar linha
        </button>
      </div>
      <div className="space-y-2">
        {splits.map((row, idx) => (
          <div key={idx} className="flex gap-2 items-start">
            <select className={`${inputCls} flex-1`} value={row.category_id} onChange={e => updateRow(idx, 'category_id', e.target.value)} required>
              <option value="">Categoria...</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <input className={`${inputCls} flex-1`} placeholder="Descrição (opcional)" value={row.description} onChange={e => updateRow(idx, 'description', e.target.value)} />
            <input type="number" step="0.01" className={`${inputCls} w-28`} placeholder="Valor" value={row.value} onFocus={e => e.target.select()} onChange={e => updateRow(idx, 'value', e.target.value)} required />
            <button type="button" onClick={() => removeRow(idx)} className="p-2 text-red-500 hover:bg-red-50 rounded-lg"><Trash2 className="w-4 h-4" /></button>
          </div>
        ))}
        {splits.length === 0 && <p className="text-xs text-gray-400 italic">Nenhuma linha — adicione ao menos uma categoria.</p>}
      </div>
      <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg ${balanced ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
        {balanced ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
        Soma das categorias: <strong>{fmtMoney(sum)}</strong> / Total: <strong>{fmtMoney(totalValue || 0)}</strong>
        {!balanced && <span> — diferença de {fmtMoney(Math.abs(sum - (parseFloat(totalValue) || 0)))}</span>}
      </div>
    </div>
  );
}

// ── Drawer de Lançamento (criar/editar + dividir por categoria) ─────────────
function EntryDrawer({ entry, accounts, categories, defaultScope, onSave, onClose }) {
  const [form, setForm] = useState({
    kind: entry?.kind || 'DESPESA',
    scope: entry?.scope || (defaultScope === 'AMBOS' ? 'EMPRESA' : defaultScope),
    account_id: entry?.account_id || '',
    date: entry?.date || todayISO(),
    paid_date: entry?.paid_date || '',
    establishment: entry?.establishment || '',
    total_value: entry?.total_value ?? '',
    payment_method: entry?.payment_method || 'PIX',
    notes: entry?.notes || '',
  });
  const [splits, setSplits] = useState(
    entry?.splits?.length ? entry.splits.map(s => ({ ...s, value: s.value })) : []
  );
  const [saving, setSaving] = useState(false);

  const availableCategories = categories.filter(c => c.kind === (form.kind === 'RECEITA' ? 'RECEITA' : 'DESPESA'));

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...form,
        total_value: parseFloat(form.total_value) || 0,
        splits: splits.map(s => ({ category_id: s.category_id, description: s.description, value: parseFloat(s.value) || 0 })),
      };
      await onSave(payload);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex justify-end z-50">
      <div className="bg-white w-full max-w-lg h-full overflow-y-auto shadow-2xl flex flex-col">
        <div
          className="flex items-center justify-between px-5 py-4 border-b border-gray-200 sticky top-0 bg-white z-10 border-l-4"
          style={{ borderLeftColor: scopeAccent(form.scope) }}
        >
          <div>
            <h3 className="font-semibold text-gray-900">{entry ? `Lançamento ${entry.id}` : 'Novo Lançamento'}</h3>
            <span className="text-[11px] font-medium" style={{ color: scopeAccent(form.scope) }}>{scopeBadgeLabel(form.scope)}</span>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg"><X className="w-5 h-5 text-gray-400" /></button>
        </div>
        <form onSubmit={submit} className="p-5 space-y-4 flex-1">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Tipo *">
              <select className={inputCls} value={form.kind} onChange={e => setForm(f => ({ ...f, kind: e.target.value }))}>
                {ENTRY_KINDS.map(k => <option key={k.value} value={k.value}>{k.label}</option>)}
              </select>
            </Field>
            <Field label="Escopo *">
              <select
                className={inputCls}
                value={form.scope}
                onChange={e => setForm(f => ({ ...f, scope: e.target.value, account_id: '' }))}
              >
                {ENTRY_SCOPES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Conta/Cartão *">
            <select className={inputCls} required value={form.account_id} onChange={e => setForm(f => ({ ...f, account_id: e.target.value }))}>
              <option value="">Selecione...</option>
              {accounts.filter(a => a.scope === form.scope).map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </Field>
          <Field label="Estabelecimento / Contraparte">
            <input className={inputCls} value={form.establishment} onChange={e => setForm(f => ({ ...f, establishment: e.target.value }))} placeholder="Mercado Pantanal, Cliente XYZ..." />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Data (competência) *">
              <input type="date" className={inputCls} required value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} />
            </Field>
            <Field label="Data de pagamento (caixa)">
              <input type="date" className={inputCls} value={form.paid_date} onChange={e => setForm(f => ({ ...f, paid_date: e.target.value }))} />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Valor total (R$) *">
              <input type="number" step="0.01" className={inputCls} required value={form.total_value} onFocus={e => e.target.select()} onChange={e => setForm(f => ({ ...f, total_value: e.target.value }))} />
            </Field>
            <Field label="Forma de pagamento">
              <select className={inputCls} value={form.payment_method} onChange={e => setForm(f => ({ ...f, payment_method: e.target.value }))}>
                {PAYMENT_METHODS_FIN.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Observações">
            <textarea className={inputCls} rows={2} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
          </Field>

          <div className="pt-3 border-t border-gray-100">
            <SplitsEditor splits={splits} setSplits={setSplits} categories={availableCategories} totalValue={form.total_value} />
          </div>
        </form>
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-gray-200 sticky bottom-0 bg-white">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg">Cancelar</button>
          <button onClick={submit} disabled={saving} className="px-4 py-2 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded-lg disabled:opacity-50">{saving ? 'Salvando...' : 'Salvar Lançamento'}</button>
        </div>
      </div>
    </div>
  );
}

// Cor mais escura para fechar o gradiente do card de saldo, por ambiente.
const GRADIENT_DARK_END = { EMPRESA: '#16365f', PESSOAL: '#4f7a1f' };

// ── Aba Início (estilo "Saldo geral" do Organizze) ──────────────────────────
function HomeTab({ summary, loading, onGoToEntries, scope }) {
  const headerGradient = scope === 'AMBOS'
    ? `linear-gradient(135deg, ${BRAND_BLUE}, ${BRAND_GREEN})`
    : `linear-gradient(135deg, ${scopeAccent(scope)}, ${GRADIENT_DARK_END[scope] || '#16365f'})`;

  if (loading || !summary) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2" style={{ borderColor: scopeAccent(scope) }}></div>
      </div>
    );
  }

  const { accounts = [], total_current_balance = 0, total_forecast_balance = 0, overdue_count = 0, to_categorize_count = 0 } = summary;
  const hasForecastDiff = Math.abs(total_forecast_balance - total_current_balance) > 0.01;
  const combined = scope === 'AMBOS';

  return (
    <div className="space-y-5">
      <div className="rounded-2xl p-6 text-white shadow-sm" style={{ background: headerGradient }}>
        <div className="text-sm text-white/70">{combined ? 'Saldo geral (PF + PJ)' : 'Saldo geral'}</div>
        <div className="text-3xl font-bold mt-1">{fmtMoney(total_current_balance)}</div>
        {hasForecastDiff && (
          <div className="text-xs text-white/70 mt-1">
            Previsão (com lançamentos futuros): <span className="font-medium text-white">{fmtMoney(total_forecast_balance)}</span>
          </div>
        )}
        <div className="flex gap-4 mt-4">
          {overdue_count > 0 && (
            <button onClick={onGoToEntries} className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-white/15 hover:bg-white/25 transition-colors">
              <AlertTriangle className="w-3.5 h-3.5 text-orange-300" /> {overdue_count} lançamento(s) atrasado(s)
            </button>
          )}
          {to_categorize_count > 0 && (
            <button onClick={onGoToEntries} className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-white/15 hover:bg-white/25 transition-colors">
              <CircleDashed className="w-3.5 h-3.5 text-amber-300" /> {to_categorize_count} a categorizar
            </button>
          )}
        </div>
      </div>

      <div>
        <div className="text-sm font-medium text-gray-700 mb-2">Minhas contas</div>
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {accounts.map(acc => {
            const TypeIcon = ACCOUNT_TYPES.find(t => t.value === acc.type)?.icon || Wallet;
            const itemAccent = scopeAccent(acc.scope);
            const bal = acc.balance || {};
            const diff = Math.abs((bal.forecast_balance ?? 0) - (bal.current_balance ?? 0)) > 0.01;
            return (
              <div key={acc.id} className="flex items-center justify-between px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg" style={{ backgroundColor: `${itemAccent}15` }}>
                    <TypeIcon className="w-4 h-4" style={{ color: itemAccent }} />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-medium text-gray-900">{acc.name}</span>
                      {combined && (
                        <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded-full" style={{ backgroundColor: `${itemAccent}1f`, color: itemAccent }}>
                          {scopeBadgeLabel(acc.scope)}
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-gray-500">{acc.institution || ACCOUNT_TYPES.find(t => t.value === acc.type)?.label}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold text-gray-900">{fmtMoney(bal.current_balance)}</div>
                  {diff && <div className="text-[11px] text-gray-400">Previsão: {fmtMoney(bal.forecast_balance)}</div>}
                </div>
              </div>
            );
          })}
          {accounts.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-gray-400">Nenhuma conta cadastrada neste escopo ainda.</div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Aba Contas ────────────────────────────────────────────────────────────────
function AccountsTab({ accounts, scope, onCreate, onUpdate, onDelete }) {
  const [modalAccount, setModalAccount] = useState(undefined); // undefined=closed, null=new, obj=edit
  const combined = scope === 'AMBOS';
  const filtered = combined ? accounts : accounts.filter(a => a.scope === scope);
  const accent = scopeAccent(scope);

  const importStatement = async (accountId, file) => {
    try {
      const res = await financeEntriesApi.importStatement(accountId, file);
      const r = res.data;
      window.alert(
        `Extrato lido: ${r.total_parsed} transação(ões). `
        + `${r.imported} importada(s), ${r.duplicated} já existia(m), ${r.skipped} ignorada(s)`
        + (r.transfers_detected ? `, sendo ${r.transfers_detected} transferência(s) entre contas próprias.` : '.')
      );
    } catch (e) {
      window.alert(e?.response?.data?.detail || 'Falha ao importar o extrato.');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={() => setModalAccount(null)} className="flex items-center gap-2 px-3 py-2 text-sm text-white rounded-lg" style={{ backgroundColor: accent }}>
          <Plus className="w-4 h-4" /> Nova Conta
        </button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map(acc => {
          const TypeIcon = ACCOUNT_TYPES.find(t => t.value === acc.type)?.icon || Wallet;
          const itemAccent = scopeAccent(acc.scope);
          return (
            <div key={acc.id} className="bg-white rounded-xl border border-gray-200 p-4 space-y-2 border-l-4" style={{ borderLeftColor: itemAccent }}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg" style={{ backgroundColor: `${itemAccent}15` }}><TypeIcon className="w-4 h-4" style={{ color: itemAccent }} /></div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="font-medium text-gray-900 text-sm">{acc.name}</span>
                      {combined && (
                        <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded-full" style={{ backgroundColor: `${itemAccent}1f`, color: itemAccent }}>
                          {scopeBadgeLabel(acc.scope)}
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-gray-500">{acc.institution || ACCOUNT_TYPES.find(t => t.value === acc.type)?.label}</div>
                  </div>
                </div>
                <div className="flex gap-1">
                  <label className="p-1.5 text-gray-400 hover:bg-gray-100 rounded-lg cursor-pointer" title="Importar extrato (OFX/CSV)">
                    <Upload className="w-3.5 h-3.5" />
                    <input
                      type="file"
                      accept=".ofx,.qfx,.csv,.pdf"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) importStatement(acc.id, file);
                        e.target.value = '';
                      }}
                    />
                  </label>
                  <button onClick={() => setModalAccount(acc)} className="p-1.5 text-gray-400 hover:bg-gray-100 rounded-lg"><Pencil className="w-3.5 h-3.5" /></button>
                  <button onClick={() => onDelete(acc)} className="p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500 rounded-lg"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </div>
              <div className="text-xl font-bold text-gray-900">{fmtMoney(acc.current_balance)}</div>
              {acc.type === 'CARTAO_CREDITO' && acc.credit_limit != null && (
                <div className="text-[11px] text-gray-500">Limite: {fmtMoney(acc.credit_limit)} · Fecha dia {acc.closing_day || '-'} · Vence dia {acc.due_day || '-'}</div>
              )}
            </div>
          );
        })}
        {filtered.length === 0 && (
          <div className="col-span-full text-center py-10 text-gray-400 text-sm">Nenhuma conta cadastrada neste escopo ainda.</div>
        )}
      </div>
      {modalAccount !== undefined && (
        <AccountModal
          account={modalAccount}
          defaultScope={combined ? 'EMPRESA' : scope}
          onClose={() => setModalAccount(undefined)}
          onSave={async (data) => {
            if (modalAccount) await onUpdate(modalAccount.id, data);
            else await onCreate(data);
            setModalAccount(undefined);
          }}
        />
      )}
    </div>
  );
}

// ── Aba Categorias ───────────────────────────────────────────────────────────
function CategoriesTab({ categories, scope, onCreate, onUpdate, onDelete, onSeed, onResetImport }) {
  const [modalCategory, setModalCategory] = useState(undefined);
  const accent = scopeAccent(scope);
  const visible = scope === 'AMBOS' ? categories : categories.filter(c => c.scope === scope || c.scope === 'AMBOS');
  const despesas = visible.filter(c => c.kind === 'DESPESA' && !c.parent_id);
  const receitas = visible.filter(c => c.kind === 'RECEITA' && !c.parent_id);
  const childrenOf = (id) => visible.filter(c => c.parent_id === id);

  const Row = ({ cat, indent = false }) => (
    <div className={`flex items-center justify-between py-2 ${indent ? 'pl-7' : 'pl-3'} pr-3 hover:bg-gray-50 rounded-lg group`}>
      <div className="flex items-center gap-2 text-sm text-gray-800">
        {indent && <ChevronRight className="w-3 h-3 text-gray-300" />}
        <Tag className="w-3.5 h-3.5 text-gray-400" /> {cat.name}
        {cat.scope !== 'AMBOS' && <span className="text-[10px] text-gray-400">({cat.scope === 'EMPRESA' ? 'PJ' : 'PF'})</span>}
      </div>
      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={() => setModalCategory(cat)} className="p-1 text-gray-400 hover:bg-gray-200 rounded"><Pencil className="w-3.5 h-3.5" /></button>
        <button onClick={() => onDelete(cat)} className="p-1 text-gray-400 hover:bg-red-50 hover:text-red-500 rounded"><Trash2 className="w-3.5 h-3.5" /></button>
      </div>
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        {categories.length === 0 && (
          <button onClick={onSeed} className="flex items-center gap-2 px-3 py-2 text-sm bg-violet-50 text-violet-700 hover:bg-violet-100 rounded-lg">
            <Sparkles className="w-4 h-4" /> Semear categorias padrão
          </button>
        )}
        <button
          onClick={async () => {
            if (!window.confirm(
              'Isso vai APAGAR todas as categorias existentes e criar a nova árvore completa (PF/PJ × Receitas/Despesas). Lançamentos já categorizados podem ficar com referências antigas. Continuar?'
            )) return;
            const res = await onResetImport();
            window.alert(res?.message || 'Categorias resetadas e reimportadas.');
          }}
          className="flex items-center gap-2 px-3 py-2 text-sm bg-amber-50 text-amber-700 hover:bg-amber-100 rounded-lg"
        >
          <Sparkles className="w-4 h-4" /> Resetar e importar categorias
        </button>
        <button onClick={() => setModalCategory(null)} className="flex items-center gap-2 px-3 py-2 text-sm text-white rounded-lg" style={{ backgroundColor: accent }}>
          <Plus className="w-4 h-4" /> Nova Categoria
        </button>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-100 font-medium text-sm text-gray-700 flex items-center gap-2"><ListTree className="w-4 h-4 text-rose-500" /> Despesas</div>
          <div className="p-1">
            {despesas.map(c => (
              <React.Fragment key={c.id}>
                <Row cat={c} />
                {childrenOf(c.id).map(ch => <Row key={ch.id} cat={ch} indent />)}
              </React.Fragment>
            ))}
            {despesas.length === 0 && <p className="text-xs text-gray-400 px-3 py-4">Nenhuma categoria de despesa.</p>}
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-100 font-medium text-sm text-gray-700 flex items-center gap-2"><ListTree className="w-4 h-4 text-emerald-500" /> Receitas</div>
          <div className="p-1">
            {receitas.map(c => (
              <React.Fragment key={c.id}>
                <Row cat={c} />
                {childrenOf(c.id).map(ch => <Row key={ch.id} cat={ch} indent />)}
              </React.Fragment>
            ))}
            {receitas.length === 0 && <p className="text-xs text-gray-400 px-3 py-4">Nenhuma categoria de receita.</p>}
          </div>
        </div>
      </div>
      {modalCategory !== undefined && (
        <CategoryModal
          category={modalCategory}
          categories={categories}
          onClose={() => setModalCategory(undefined)}
          onSave={async (data) => {
            if (modalCategory) await onUpdate(modalCategory.id, data);
            else await onCreate(data);
            setModalCategory(undefined);
          }}
        />
      )}
    </div>
  );
}

// ── Aba Lançamentos (fluxo de caixa estilo Organizze) ───────────────────────
function EntriesTab({ entries, accounts, categories, scope, onCreate, onUpdate, onDelete, onMarkPaid, onConfirmTransfer, onRejectTransfer }) {
  const [drawerEntry, setDrawerEntry] = useState(undefined);
  const [filterAccount, setFilterAccount] = useState('');
  const [filterKind, setFilterKind] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [sortDir, setSortDir] = useState('desc');
  const [search, setSearch] = useState('');
  const [showSearch, setShowSearch] = useState(false);

  const accountName = (id) => accounts.find(a => a.id === id)?.name || id;
  const categoryName = (id) => categories.find(c => c.id === id)?.name || '';
  const isOverdue = (e) => e.is_overdue ?? (!SETTLED_STATUSES.includes(e.status) && e.date < todayISO());
  const isPaid = (e) => SETTLED_STATUSES.includes(e.status);

  const filtered = useMemo(() => {
    let list = entries.filter(e => scope === 'AMBOS' || e.scope === scope);
    if (filterAccount) list = list.filter(e => e.account_id === filterAccount);
    if (filterKind) list = list.filter(e => e.kind === filterKind);
    if (filterCategory) list = list.filter(e => (e.splits || []).some(s => s.category_id === filterCategory));
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(e =>
        (e.establishment || '').toLowerCase().includes(q) ||
        (e.notes || '').toLowerCase().includes(q) ||
        (e.splits || []).some(s => (s.description || '').toLowerCase().includes(q))
      );
    }
    list = [...list].sort((a, b) => sortDir === 'asc' ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date));
    return list;
  }, [entries, scope, filterAccount, filterKind, filterCategory, search, sortDir]);

  // Agrupar por dia, como o "Fluxo de caixa" do Organizze
  const groups = useMemo(() => {
    const map = new Map();
    for (const e of filtered) {
      if (!map.has(e.date)) map.set(e.date, []);
      map.get(e.date).push(e);
    }
    return Array.from(map.entries());
  }, [filtered]);

  const availableCategories = categories.filter(c => scope === 'AMBOS' || c.scope === scope || c.scope === 'AMBOS');
  const accent = scopeAccent(scope);
  const combined = scope === 'AMBOS';

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <select className="text-sm border border-gray-300 rounded-lg px-2.5 py-1.5" value={filterAccount} onChange={e => setFilterAccount(e.target.value)}>
            <option value="">Todas as contas</option>
            {accounts.filter(a => combined || a.scope === scope).map(a => (
              <option key={a.id} value={a.id}>{a.name}{combined ? ` (${scopeBadgeLabel(a.scope)})` : ''}</option>
            ))}
          </select>
          <select className="text-sm border border-gray-300 rounded-lg px-2.5 py-1.5" value={filterKind} onChange={e => setFilterKind(e.target.value)}>
            <option value="">Despesas e receitas</option>
            {ENTRY_KINDS.map(k => <option key={k.value} value={k.value}>{k.label}</option>)}
          </select>
          <button
            onClick={() => setSortDir(d => d === 'asc' ? 'desc' : 'asc')}
            className="flex items-center gap-1.5 text-sm border border-gray-300 rounded-lg px-2.5 py-1.5 text-gray-600 hover:bg-gray-50"
          >
            <ArrowUpDown className="w-3.5 h-3.5" /> Data {sortDir === 'asc' ? '↑ mais antigas' : '↓ mais recentes'}
          </button>
          <button
            onClick={() => setShowSearch(s => !s)}
            className="flex items-center gap-1.5 text-sm border rounded-lg px-2.5 py-1.5"
            style={showSearch ? { borderColor: accent, backgroundColor: `${accent}15`, color: accent } : { borderColor: '#d1d5db', color: '#4b5563' }}
          >
            <Filter className="w-3.5 h-3.5" /> Refinar busca
          </button>
        </div>
        <button onClick={() => setDrawerEntry(null)} className="flex items-center gap-2 px-3 py-2 text-sm text-white rounded-lg" style={{ backgroundColor: accent }}>
          <Plus className="w-4 h-4" /> Novo Lançamento
        </button>
      </div>

      {showSearch && (
        <div className="flex flex-wrap items-center gap-2 bg-gray-50 border border-gray-200 rounded-lg p-3">
          <div className="flex items-center gap-2 flex-1 min-w-[200px]">
            <Search className="w-4 h-4 text-gray-400" />
            <input
              className="flex-1 text-sm border border-gray-300 rounded-lg px-2.5 py-1.5"
              placeholder="Buscar por estabelecimento, descrição, observação..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <select className="text-sm border border-gray-300 rounded-lg px-2.5 py-1.5" value={filterCategory} onChange={e => setFilterCategory(e.target.value)}>
            <option value="">Todas as categorias</option>
            {availableCategories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
      )}

      <div className="space-y-4">
        {groups.map(([date, dayEntries]) => {
          const dayTotal = dayEntries.reduce((acc, e) => acc + (e.kind === 'RECEITA' ? e.total_value : -e.total_value), 0);
          return (
            <div key={date}>
              <div className="flex items-center justify-between px-1 mb-1.5">
                <div className="text-xs font-medium text-gray-500 uppercase">{fmtDateLabel(date)}</div>
                <div className={`text-xs font-medium ${dayTotal >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>{fmtMoney(dayTotal)}</div>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100 overflow-hidden">
                {dayEntries.map(e => {
                  const overdue = isOverdue(e);
                  const paid = isPaid(e);
                  const suggested = !!e.transfer_suggested;
                  return (
                    <div key={e.id}>
                      <div
                        className={`flex items-center justify-between px-4 py-3 gap-3 border-l-4 ${overdue ? 'border-l-red-500 bg-red-50/40' : (suggested ? 'border-l-blue-400 bg-blue-50/30' : (e.status === 'PENDENTE' ? 'border-l-amber-400' : 'border-l-transparent'))}`}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            {combined && (
                              <span
                                className="px-1.5 py-0.5 text-[10px] font-semibold rounded-full shrink-0"
                                style={{ backgroundColor: `${scopeAccent(e.scope)}1f`, color: scopeAccent(e.scope) }}
                              >
                                {scopeBadgeLabel(e.scope)}
                              </span>
                            )}
                            <span className="text-sm font-medium text-gray-900 truncate">{e.establishment || '(sem estabelecimento)'}</span>
                            {e.status === 'A_CATEGORIZAR' && (
                              <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-amber-100 text-amber-700">A categorizar</span>
                            )}
                            {overdue && (
                              <span className="flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-red-100 text-red-700">
                                <AlertTriangle className="w-2.5 h-2.5" /> Atrasado
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-gray-500 truncate">
                            {accountName(e.account_id)}
                            {(e.splits || []).length > 0 && ` · ${e.splits.map(s => categoryName(s.category_id)).filter(Boolean).join(', ')}`}
                          </div>
                        </div>
                        <button
                          onClick={() => !paid && onMarkPaid(e)}
                          title={paid ? 'Lançamento confirmado' : 'Marcar como pago/confirmado'}
                          className={`flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-medium shrink-0 ${paid ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}`}
                        >
                          {paid ? <CheckCheck className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                          {paid ? STATUS_LABEL[e.status] : 'Não pago'}
                        </button>
                        <div className={`text-sm font-semibold w-28 text-right shrink-0 ${e.kind === 'RECEITA' ? 'text-emerald-600' : 'text-red-600'}`}>
                          {e.kind === 'RECEITA' ? '+' : '−'} {fmtMoney(e.total_value)}
                        </div>
                        <div className="flex gap-1 shrink-0">
                          <button onClick={() => setDrawerEntry(e)} className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg"><Pencil className="w-3.5 h-3.5" /></button>
                          <button onClick={() => onDelete(e)} className="p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500 rounded-lg"><Trash2 className="w-3.5 h-3.5" /></button>
                        </div>
                      </div>
                      {suggested && (
                        <div className="flex items-center justify-between gap-3 px-4 py-2 bg-blue-50 border-t border-blue-100 text-[12px]">
                          <div className="flex items-center gap-1.5 text-blue-700 min-w-0">
                            <ArrowLeftRight className="w-3.5 h-3.5 shrink-0" />
                            <span className="truncate">
                              Possível transferência interna com <strong>{accountName(e.transfer_with_account_id)}</strong> (mesmo valor, data próxima — confirme ou rejeite)
                            </span>
                          </div>
                          <div className="flex gap-1.5 shrink-0">
                            <button
                              onClick={() => onConfirmTransfer(e)}
                              className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium bg-emerald-600 text-white hover:bg-emerald-700"
                            >
                              <Check className="w-3 h-3" /> Confirmar
                            </button>
                            <button
                              onClick={() => onRejectTransfer(e)}
                              className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium bg-white border border-gray-300 text-gray-600 hover:bg-gray-50"
                            >
                              <X className="w-3 h-3" /> Rejeitar
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
        {groups.length === 0 && (
          <div className="bg-white rounded-xl border border-gray-200 px-4 py-10 text-center text-sm text-gray-400">Nenhum lançamento encontrado para os filtros atuais.</div>
        )}
      </div>

      {drawerEntry !== undefined && (
        <EntryDrawer
          entry={drawerEntry}
          accounts={combined ? accounts : accounts.filter(a => a.scope === scope)}
          categories={categories}
          defaultScope={scope}
          onClose={() => setDrawerEntry(undefined)}
          onSave={async (data) => {
            if (drawerEntry) await onUpdate(drawerEntry.id, data);
            else await onCreate(data);
            setDrawerEntry(undefined);
          }}
        />
      )}
    </div>
  );
}

// ── Página principal ──────────────────────────────────────────────────────────
export function FinanceManager() {
  const [scope, setScope] = useState('EMPRESA');
  const [tab, setTab] = useState('home');
  const [accounts, setAccounts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [entries, setEntries] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const loadAll = async () => {
    try {
      setLoading(true);
      setLoadError('');
      const [accRes, catRes, entRes] = await Promise.all([
        financeAccountsApi.list(),
        financeCategoriesApi.list(),
        financeEntriesApi.list(),
      ]);
      setAccounts(accRes.data || []);
      setCategories(catRes.data || []);
      setEntries(entRes.data || []);
    } catch (e) {
      console.error('Erro ao carregar gestor financeiro:', e);
      setLoadError('Não foi possível carregar os dados do Gestor Financeiro. Verifique sua conexão e tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  const loadSummary = async (sc) => {
    try {
      setSummaryLoading(true);
      const res = await financeSummaryApi.get({ scope: sc });
      setSummary(res.data || null);
    } catch (e) {
      console.error('Erro ao carregar saldo geral:', e);
      setLoadError('Não foi possível carregar o resumo financeiro. Verifique sua conexão e tente novamente.');
    } finally {
      setSummaryLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);
  useEffect(() => { loadSummary(scope); }, [scope]);

  const markPaid = async (entry) => {
    await financeEntriesApi.update(entry.id, { status: 'PAGO', paid_date: todayISO() });
    await Promise.all([loadAll(), loadSummary(scope)]);
  };

  const confirmTransfer = async (entry) => {
    try { await financeEntriesApi.confirmTransfer(entry.id); await Promise.all([loadAll(), loadSummary(scope)]); }
    catch (e) { alert(e.response?.data?.detail || 'Erro ao confirmar transferência.'); }
  };
  const rejectTransfer = async (entry) => {
    try { await financeEntriesApi.rejectTransfer(entry.id); await Promise.all([loadAll(), loadSummary(scope)]); }
    catch (e) { alert(e.response?.data?.detail || 'Erro ao rejeitar transferência.'); }
  };

  const createAccount = async (data) => { await financeAccountsApi.create(data); await loadAll(); await loadSummary(scope); };
  const updateAccount = async (id, data) => { await financeAccountsApi.update(id, data); await loadAll(); await loadSummary(scope); };
  const deleteAccount = async (acc) => {
    if (!window.confirm(`Excluir a conta "${acc.name}"?`)) return;
    try { await financeAccountsApi.delete(acc.id); await loadAll(); await loadSummary(scope); }
    catch (e) { alert(e.response?.data?.detail || 'Erro ao excluir conta.'); }
  };

  const createCategory = async (data) => { await financeCategoriesApi.create(data); await loadAll(); };
  const updateCategory = async (id, data) => { await financeCategoriesApi.update(id, data); await loadAll(); };
  const deleteCategory = async (cat) => {
    if (!window.confirm(`Excluir a categoria "${cat.name}"?`)) return;
    try { await financeCategoriesApi.delete(cat.id); await loadAll(); }
    catch (e) { alert(e.response?.data?.detail || 'Erro ao excluir categoria.'); }
  };
  const seedCategories = async () => { await financeCategoriesApi.seed(); await loadAll(); };
  const resetImportCategories = async () => {
    const res = await financeCategoriesApi.resetImport();
    await loadAll();
    return res.data;
  };

  const createEntry = async (data) => { await financeEntriesApi.create(data); await loadAll(); await loadSummary(scope); };
  const updateEntry = async (id, data) => { await financeEntriesApi.update(id, data); await loadAll(); await loadSummary(scope); };
  const deleteEntry = async (entry) => {
    if (!window.confirm(`Excluir o lançamento "${entry.establishment || entry.id}"?`)) return;
    try { await financeEntriesApi.delete(entry.id); await loadAll(); await loadSummary(scope); }
    catch (e) { alert(e.response?.data?.detail || 'Erro ao excluir lançamento.'); }
  };

  const TABS = [
    { value: 'home', label: 'Início', icon: Home },
    { value: 'entries', label: 'Lançamentos', icon: Receipt },
    { value: 'accounts', label: 'Contas', icon: Wallet },
    { value: 'categories', label: 'Categorias', icon: Tag },
  ];

  const pageAccent = scopeAccent(scope);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2" style={{ borderColor: pageAccent }}></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Gerenciador Financeiro</h1>
            <p className="text-gray-600 text-sm">Contas, categorias e lançamentos — separados por ambiente ou combinados na Visão Geral.</p>
          </div>
          <span
            className="px-2.5 py-1 text-xs font-semibold rounded-full shrink-0"
            style={{ backgroundColor: `${pageAccent}15`, color: pageAccent }}
          >
            {scope === 'AMBOS' ? 'Visão Geral (PF+PJ)' : (scope === 'EMPRESA' ? 'Empresa (PJ)' : 'Pessoal (PF)')}
          </span>
        </div>
        <div className="flex bg-gray-100 rounded-lg p-1">
          {SCOPES.map(s => {
            const Icon = s.icon;
            const active = scope === s.value;
            const color = SCOPE_COLOR[s.value];
            return (
              <button
                key={s.value}
                onClick={() => setScope(s.value)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors"
                style={active
                  ? { backgroundColor: 'white', boxShadow: '0 1px 2px rgba(0,0,0,0.06)', color, fontWeight: 500 }
                  : { color: `${color}99` }}
              >
                <Icon className="w-3.5 h-3.5" /> {s.label}
              </button>
            );
          })}
        </div>
      </div>

      {loadError && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-3 text-sm flex items-center justify-between gap-3">
          <span>{loadError}</span>
          <button
            onClick={() => { loadAll(); loadSummary(scope); }}
            className="shrink-0 px-3 py-1.5 bg-red-600 text-white rounded-lg text-xs font-medium hover:bg-red-700"
          >
            Tentar novamente
          </button>
        </div>
      )}

      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map(t => {
          const Icon = t.icon;
          const active = tab === t.value;
          return (
            <button
              key={t.value}
              onClick={() => setTab(t.value)}
              className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors"
              style={active ? { borderColor: pageAccent, color: pageAccent } : { borderColor: 'transparent', color: '#6b7280' }}
            >
              <Icon className="w-4 h-4" /> {t.label}
            </button>
          );
        })}
      </div>

      {tab === 'home' && (
        <HomeTab summary={summary} loading={summaryLoading} onGoToEntries={() => setTab('entries')} scope={scope} />
      )}
      {tab === 'accounts' && (
        <AccountsTab accounts={accounts} scope={scope} onCreate={createAccount} onUpdate={updateAccount} onDelete={deleteAccount} />
      )}
      {tab === 'categories' && (
        <CategoriesTab categories={categories} scope={scope} onCreate={createCategory} onUpdate={updateCategory} onDelete={deleteCategory} onSeed={seedCategories} onResetImport={resetImportCategories} />
      )}
      {tab === 'entries' && (
        <EntriesTab entries={entries} accounts={accounts} categories={categories} scope={scope} onCreate={createEntry} onUpdate={updateEntry} onDelete={deleteEntry} onMarkPaid={markPaid} onConfirmTransfer={confirmTransfer} onRejectTransfer={rejectTransfer} />
      )}
    </div>
  );
}

export default FinanceManager;
