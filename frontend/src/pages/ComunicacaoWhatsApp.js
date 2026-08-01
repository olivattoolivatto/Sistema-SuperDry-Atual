import React, { useState, useEffect, useCallback } from 'react';
import {
  MessageSquare, RefreshCw, Phone, Clock, DollarSign,
  ChevronRight, AlertCircle, Loader2, Send, Users,
} from 'lucide-react';
import { marketingApi } from '../services/api';
import { BACKEND_URL } from '../lib/backendUrl';

// ── helpers ──────────────────────────────────────────────────────────────────

function cleanPhone(raw = '') {
  const digits = raw.replace(/\D/g, '');
  return digits.startsWith('55') ? digits : `55${digits}`;
}

function waLink(phone, text) {
  const p = cleanPhone(phone);
  if (!p || p.length < 10) return null;
  const encoded = encodeURIComponent(text);
  const url = `https://wa.me/${p}?text=${encoded}`;
  return url.length > 2000 ? `https://wa.me/${p}` : url;
}

function fmtBRL(v) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v || 0);
}

function daysBadge(days) {
  const cls = days >= 30
    ? 'bg-red-100 text-red-700'
    : days >= 14
    ? 'bg-amber-100 text-amber-700'
    : 'bg-gray-100 text-gray-600';
  return (
    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${cls}`}>
      {days}d
    </span>
  );
}

const SERVICE_CATEGORY_LABEL = {
  ESTOFADOS: 'Estofados',
  TAPETES: 'Tapetes',
  COLCHOES: 'Colchões',
  BOX: 'Box',
  CORTINAS: 'Cortinas',
  PERSIANAS: 'Persianas',
  ITENS_INFANTIS: 'Itens Infantis',
  VEICULOS: 'Veículos',
  IMPERMEABILIZACAO: 'Impermeabilização',
  OUTROS: 'Outros',
};

// ── Aba Remarketing ──────────────────────────────────────────────────────────

function RemarketingTab() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const r = await marketingApi.remarketing(days);
      setData(r.data || []);
    } catch {
      setError('Erro ao carregar orçamentos.');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { load(); }, [load]);

  const buildMsg = (item) => {
    const itens = (item.items || []).map(i => i.service_name).filter(Boolean).join(', ');
    return `Olá ${item.client_name?.split(' ')[0] || ''}! 😊 Passando para saber se você gostaria de agendar o serviço${itens ? ` de ${itens}` : ''}. Ainda temos disponibilidade! Qual seria o melhor horário para você?`;
  };

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-gray-600">Sem movimentação há mais de</span>
        <select
          value={days}
          onChange={e => setDays(Number(e.target.value))}
          className="border border-gray-300 rounded-lg px-2 py-1 text-sm"
        >
          {[3, 5, 7, 10, 14, 30].map(d => (
            <option key={d} value={d}>{d} dias</option>
          ))}
        </select>
        <button onClick={load} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-500" title="Atualizar">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {loading && (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
        </div>
      )}
      {error && <p className="text-sm text-red-600 py-4">{error}</p>}

      {!loading && !error && data.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <MessageSquare className="w-10 h-10 mx-auto mb-2 opacity-30" />
          <p className="text-sm">Nenhum orçamento pendente há mais de {days} dias.</p>
        </div>
      )}

      <div className="space-y-3">
        {data.map(item => {
          const msg = buildMsg(item);
          const link = waLink(item.phone, msg);
          const itensPreview = (item.items || []).map(i => i.service_name).filter(Boolean).join(', ');
          return (
            <div key={item.id} className="bg-white border border-gray-200 rounded-xl p-4 space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-gray-900 text-sm truncate">{item.client_name}</span>
                    {daysBadge(item.days_since)}
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">{item.id}</p>
                </div>
                <span className="text-sm font-semibold text-emerald-700 whitespace-nowrap">
                  {fmtBRL(item.total_value)}
                </span>
              </div>
              {itensPreview && (
                <p className="text-xs text-gray-500 truncate">{itensPreview}</p>
              )}
              <div className="flex gap-2 pt-1">
                {item.phone && link && (
                  <a
                    href={link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-medium rounded-lg flex items-center justify-center gap-1.5"
                  >
                    <MessageSquare className="w-4 h-4" /> Recontatar
                  </a>
                )}
                {!item.phone && (
                  <span className="text-xs text-gray-400 flex items-center gap-1">
                    <Phone className="w-3 h-3" /> Sem telefone
                  </span>
                )}
                <a
                  href={`${BACKEND_URL}/api/budgets/${item.id}/pdf`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 flex items-center gap-1"
                >
                  PDF
                </a>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Aba Reativação ───────────────────────────────────────────────────────────

function ReativacaoTab() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const r = await marketingApi.reactivation(days);
      setData(r.data || []);
    } catch {
      setError('Erro ao carregar clientes.');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { load(); }, [load]);

  const buildMsg = (item) => {
    const cat = SERVICE_CATEGORY_LABEL[item.service_category] || item.service_category || 'serviço';
    const firstName = item.client_name?.split(' ')[0] || '';
    return `Olá ${firstName}! 😊 Faz um tempo que você não faz a higienização de ${cat.toLowerCase()}. Que tal agendarmos? Temos disponibilidade e condições especiais para clientes recorrentes! 🧹✨`;
  };

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-gray-600">Último serviço há mais de</span>
        <select
          value={days}
          onChange={e => setDays(Number(e.target.value))}
          className="border border-gray-300 rounded-lg px-2 py-1 text-sm"
        >
          {[30, 60, 90, 120, 180, 365].map(d => (
            <option key={d} value={d}>{d} dias</option>
          ))}
        </select>
        <button onClick={load} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-500" title="Atualizar">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {loading && (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
        </div>
      )}
      {error && <p className="text-sm text-red-600 py-4">{error}</p>}

      {!loading && !error && data.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <Users className="w-10 h-10 mx-auto mb-2 opacity-30" />
          <p className="text-sm">Nenhum cliente para reativar nesse intervalo.</p>
        </div>
      )}

      <div className="space-y-3">
        {data.map((item, idx) => {
          const msg = buildMsg(item);
          const link = waLink(item.phone, msg);
          const catLabel = SERVICE_CATEGORY_LABEL[item.service_category] || item.service_category;
          return (
            <div key={`${item.client_id}-${item.service_category}-${idx}`} className="bg-white border border-gray-200 rounded-xl p-4 space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-gray-900 text-sm">{item.client_name}</span>
                    {daysBadge(item.days_since)}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{catLabel}</p>
                </div>
                <span className="text-xs text-gray-400 whitespace-nowrap flex items-center gap-1">
                  <DollarSign className="w-3 h-3" /> {fmtBRL(item.last_value)}
                </span>
              </div>
              <div className="flex gap-2 pt-1">
                {item.phone && link && (
                  <a
                    href={link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-medium rounded-lg flex items-center justify-center gap-1.5"
                  >
                    <MessageSquare className="w-4 h-4" /> Reativar
                  </a>
                )}
                {!item.phone && (
                  <span className="text-xs text-gray-400 flex items-center gap-1">
                    <Phone className="w-3 h-3" /> Sem telefone
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Aba Envio rápido ─────────────────────────────────────────────────────────

function EnvioRapidoTab() {
  const [phone, setPhone] = useState('');
  const [text, setText] = useState('');

  const link = waLink(phone, text);

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        Gere um link de WhatsApp com mensagem personalizada para qualquer número.
      </p>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Telefone (com DDD)</label>
        <input
          type="tel"
          value={phone}
          onChange={e => setPhone(e.target.value)}
          placeholder="65 99999-9999"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Mensagem</label>
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          rows={5}
          placeholder="Olá! ..."
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none"
        />
        <p className="text-[11px] text-gray-400 mt-1">{text.length} caracteres</p>
      </div>
      {link ? (
        <a
          href={link}
          target="_blank"
          rel="noopener noreferrer"
          className="w-full py-2.5 bg-green-500 hover:bg-green-600 text-white text-sm font-medium rounded-lg flex items-center justify-center gap-2 block text-center"
        >
          <Send className="w-4 h-4 inline" /> Abrir WhatsApp
        </a>
      ) : (
        <button disabled className="w-full py-2.5 bg-gray-200 text-gray-400 text-sm rounded-lg flex items-center justify-center gap-2 cursor-not-allowed">
          <Send className="w-4 h-4" /> Preencha telefone e mensagem
        </button>
      )}
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────

const TABS = [
  { id: 'remarketing', label: 'Remarketing', icon: Clock },
  { id: 'reativacao',  label: 'Reativação',  icon: Users },
  { id: 'envio',       label: 'Envio rápido', icon: Send },
];

export function ComunicacaoWhatsApp() {
  const [tab, setTab] = useState('remarketing');

  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="flex items-center gap-2 mb-5">
        <MessageSquare className="w-5 h-5 text-green-600" />
        <h1 className="text-lg font-semibold text-gray-900">Comunicação WhatsApp</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-5">
        {TABS.map(t => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-colors ${
                active ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Conteúdo */}
      {tab === 'remarketing' && <RemarketingTab />}
      {tab === 'reativacao'  && <ReativacaoTab />}
      {tab === 'envio'       && <EnvioRapidoTab />}
    </div>
  );
}
