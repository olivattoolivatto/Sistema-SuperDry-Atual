import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Truck, FileText, ClipboardCheck, Droplets, DollarSign,
  Wallet, Wrench, Users, RefreshCcw, AlertCircle, Zap
} from 'lucide-react';
import { dashboardApi, clientsApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const CARDS = [
  {
    key: 'items_pending_routes',
    title: 'Itens Pendentes de Rota',
    icon: Truck,
    color: 'amber',
    description: 'Itens aguardando inclusão em uma rota.',
    path: '/routes',
    roles: ['ADMIN', 'ATENDENTE', 'TECNICO'],
  },
  {
    key: 'active_budgets',
    title: 'Orçamentos Ativos',
    icon: FileText,
    color: 'blue',
    description: 'Orçamentos lançados sem rota associada.',
    path: '/budgets',
    roles: ['ADMIN', 'ATENDENTE'],
  },
  {
    key: 'execution_today',
    title: 'Execução de Hoje',
    icon: ClipboardCheck,
    color: 'emerald',
    description: 'Itens para serem executados hoje (Modo Técnico).',
    path: '/technician',
    roles: ['ADMIN', 'TECNICO'],
  },
  {
    key: 'items_in_washing',
    title: 'Em Lavagem / Execução',
    icon: Droplets,
    color: 'sky',
    description: 'Itens em processo de lavagem ou aguardando.',
    path: '/washing',
    roles: ['ADMIN', 'TECNICO'],
  },
  {
    key: 'financial_pending',
    title: 'Pendências Financeiras',
    icon: DollarSign,
    color: 'rose',
    description: 'Serviços sem registro de pagamento.',
    path: '/financial',
    roles: ['ADMIN', 'FINANCEIRO', 'ATENDENTE'],
  },
  {
    key: 'finance_summary',
    title: 'Resumo Financeiro',
    icon: Wallet,
    color: 'violet',
    description: 'Saldo bancário, caixa, faturamento.',
    path: '/finance-manager',
    roles: ['ADMIN', 'FINANCEIRO'],
    isComplex: true,
  },
  {
    key: 'tickets_open',
    title: 'Chamados em Aberto',
    icon: Wrench,
    color: 'orange',
    description: 'Chamados e manutenções em aberto.',
    path: '/tickets',
    roles: ['ADMIN', 'MANUTENCAO'],
  },
];

const COLOR_MAP = {
  amber:   { bg: 'bg-amber-50',   text: 'text-amber-700',   ring: 'ring-amber-200',   bar: 'bg-amber-500'   },
  blue:    { bg: 'bg-blue-50',    text: 'text-blue-700',    ring: 'ring-blue-200',    bar: 'bg-blue-500'    },
  emerald: { bg: 'bg-emerald-50', text: 'text-emerald-700', ring: 'ring-emerald-200', bar: 'bg-emerald-500' },
  sky:     { bg: 'bg-sky-50',     text: 'text-sky-700',     ring: 'ring-sky-200',     bar: 'bg-sky-500'     },
  rose:    { bg: 'bg-rose-50',    text: 'text-rose-700',    ring: 'ring-rose-200',    bar: 'bg-rose-500'    },
  violet:  { bg: 'bg-violet-50',  text: 'text-violet-700',  ring: 'ring-violet-200',  bar: 'bg-violet-500'  },
  orange:  { bg: 'bg-orange-50',  text: 'text-orange-700',  ring: 'ring-orange-200',  bar: 'bg-orange-500'  },
};

function StatCard({ card, value, onClick }) {
  const Icon = card.icon;
  const c = COLOR_MAP[card.color] || COLOR_MAP.blue;
  return (
    <button
      onClick={onClick}
      className="text-left bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-all overflow-hidden group"
    >
      <div className={`h-1 ${c.bar}`} />
      <div className="p-4 sm:p-5">
        <div className="flex items-start justify-between mb-3">
          <div className={`w-11 h-11 rounded-xl ${c.bg} ${c.text} flex items-center justify-center ring-1 ${c.ring}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div className="text-3xl font-bold text-gray-900 tabular-nums">{value}</div>
        </div>
        <div className="text-sm font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">
          {card.title}
        </div>
        <div className="text-xs text-gray-500 mt-1">{card.description}</div>
      </div>
    </button>
  );
}

function FinanceCard({ data, onClick }) {
  const c = COLOR_MAP.violet;
  const fmt = (n) => (n || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  return (
    <button onClick={onClick} className="text-left bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-all overflow-hidden col-span-1 sm:col-span-2">
      <div className={`h-1 ${c.bar}`} />
      <div className="p-4 sm:p-5">
        <div className="flex items-center justify-between mb-3">
          <div className={`w-11 h-11 rounded-xl ${c.bg} ${c.text} flex items-center justify-center ring-1 ${c.ring}`}>
            <Wallet className="w-5 h-5" />
          </div>
          <div className="text-xs text-gray-400">Resumo Financeiro</div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <div className="text-[11px] text-gray-500 uppercase">Caixa</div>
            <div className="text-base sm:text-lg font-bold text-gray-900">{fmt(data?.cash_balance)}</div>
          </div>
          <div>
            <div className="text-[11px] text-gray-500 uppercase">Banco</div>
            <div className="text-base sm:text-lg font-bold text-gray-900">{fmt(data?.bank_balance)}</div>
          </div>
          <div>
            <div className="text-[11px] text-gray-500 uppercase">Receita Mês</div>
            <div className="text-base sm:text-lg font-bold text-gray-900">{fmt(data?.month_revenue)}</div>
          </div>
        </div>
        {!data?.available && (
          <div className="text-[11px] mt-2 text-amber-700 bg-amber-50 inline-flex items-center gap-1 px-2 py-0.5 rounded">
            <AlertCircle className="w-3 h-3" /> Módulo financeiro ainda não configurado
          </div>
        )}
      </div>
    </button>
  );
}

export function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const load = async () => {
    try {
      setLoading(true);
      setLoadError('');
      const r = await dashboardApi.getSummary();
      setData(r.data);
    } catch (e) {
      console.error(e);
      setLoadError('Não foi possível carregar o painel. Verifique sua conexão e tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const visibleCards = CARDS.filter(c => !user || user.role === 'ADMIN' || c.roles.includes(user.role));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-gradient-to-br from-blue-600 to-indigo-700 text-white rounded-2xl p-4 sm:p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold">Olá, {user?.name?.split(' ')[0] || 'usuário'} 👋</h1>
            <p className="text-blue-100 text-sm mt-0.5">
              Visão geral das operações da SuperDry
            </p>
          </div>
          <button
            onClick={load}
            className="p-2 rounded-lg bg-white/15 hover:bg-white/25 transition"
            title="Atualizar"
          >
            <RefreshCcw className="w-5 h-5" />
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="px-2 py-1 rounded-md bg-white/15">
            <Users className="inline w-3 h-3 mr-1" /> {data?.total_clients || 0} clientes
          </span>
          <span className="px-2 py-1 rounded-md bg-white/15">
            {new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' })}
          </span>
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

      {/* Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
        {visibleCards.map(card => {
          if (card.isComplex) {
            return (
              <FinanceCard
                key={card.key}
                data={data?.finance_summary}
                onClick={() => navigate(card.path)}
              />
            );
          }
          return (
            <StatCard
              key={card.key}
              card={card}
              value={data?.[card.key] ?? 0}
              onClick={() => navigate(card.path)}
            />
          );
        })}
      </div>

      {/* Atalhos rápidos */}
      {(!user || user.role === 'ADMIN' || user.role === 'ATENDENTE') && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4">
          <div className="text-xs font-semibold text-gray-500 uppercase mb-3">Atalhos</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <button onClick={() => navigate('/automations')}
              className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-700 transition-colors">
              <Zap className="w-4 h-4 shrink-0" />
              <span className="text-sm font-medium">Automações</span>
            </button>
            <button onClick={() => navigate('/budgets')}
              className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-gray-50 hover:bg-gray-100 text-gray-700 transition-colors">
              <FileText className="w-4 h-4 shrink-0" />
              <span className="text-sm font-medium">Novo Orçamento</span>
            </button>
            <button onClick={() => navigate('/financial')}
              className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-gray-50 hover:bg-gray-100 text-gray-700 transition-colors">
              <DollarSign className="w-4 h-4 shrink-0" />
              <span className="text-sm font-medium">Financeiro</span>
            </button>
            <button onClick={() => navigate('/routes-geo')}
              className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-gray-50 hover:bg-gray-100 text-gray-700 transition-colors">
              <Truck className="w-4 h-4 shrink-0" />
              <span className="text-sm font-medium">Rotas</span>
            </button>
          </div>
        </div>
      )}

      {/* Footer info */}
      <div className="text-xs text-gray-400 text-center pt-2">
        Última atualização: {data?.generated_at ? new Date(data.generated_at).toLocaleString('pt-BR') : '-'}
      </div>
    </div>
  );
}

export default Dashboard;
