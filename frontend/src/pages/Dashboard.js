import React, { useState, useEffect } from 'react';
import { 
  Users, 
  FileText, 
  TrendingUp, 
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign
} from 'lucide-react';
import { dashboardApi } from '../services/api';

const StatCard = ({ title, value, icon: Icon, color = 'blue', description }) => (
  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div className="flex items-center">
      <div className={`flex-shrink-0 p-3 rounded-lg bg-${color}-100`}>
        <Icon className={`w-6 h-6 text-${color}-600`} />
      </div>
      <div className="ml-4 flex-1">
        <p className="text-sm font-medium text-gray-600">{title}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        {description && (
          <p className="text-sm text-gray-500 mt-1">{description}</p>
        )}
      </div>
    </div>
  </div>
);

export function Dashboard() {
  const [dashboardData, setDashboardData] = useState({
    pending_routes: 0,
    pending_execution_today: 0,
    items_in_washing: 0,
    financial_pending: 0,
    total_clients: 0,
    active_budgets: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const response = await dashboardApi.getSummary();
      setDashboardData(response.data);
    } catch (error) {
      console.error('Erro ao carregar dados do dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Painel Inicial</h1>
            <p className="text-gray-600 mt-1">
              Resumo geral das operações da SuperDry Lavanderia
            </p>
          </div>
          <div className="text-sm text-gray-500">
            Última atualização: {new Date().toLocaleString('pt-BR')}
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard
          title="Clientes Cadastrados"
          value={dashboardData.total_clients}
          icon={Users}
          color="blue"
          description="Total de clientes ativos"
        />
        
        <StatCard
          title="Orçamentos Ativos"
          value={dashboardData.active_budgets}
          icon={FileText}
          color="green"
          description="Orçamentos em andamento"
        />
        
        <StatCard
          title="Itens Pendentes Rota"
          value={dashboardData.pending_routes}
          icon={AlertTriangle}
          color="yellow"
          description="Aguardando programação"
        />
        
        <StatCard
          title="Execução Hoje"
          value={dashboardData.pending_execution_today}
          icon={Clock}
          color="purple"
          description="Serviços agendados para hoje"
        />
        
        <StatCard
          title="Em Lavagem"
          value={dashboardData.items_in_washing}
          icon={TrendingUp}
          color="indigo"
          description="Itens em processo de lavagem"
        />
        
        <StatCard
          title="Pendências Financeiras"
          value={dashboardData.financial_pending}
          icon={DollarSign}
          color="red"
          description="Pagamentos pendentes"
        />
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Ações Rápidas</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button className="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
            <Users className="w-5 h-5 text-blue-600 mr-3" />
            <span className="text-sm font-medium">Novo Cliente</span>
          </button>
          
          <button className="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
            <FileText className="w-5 h-5 text-green-600 mr-3" />
            <span className="text-sm font-medium">Novo Orçamento</span>
          </button>
          
          <button className="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
            <CheckCircle className="w-5 h-5 text-purple-600 mr-3" />
            <span className="text-sm font-medium">Ver Agenda</span>
          </button>
        </div>
      </div>

      {/* Recent Activity Placeholder */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Atividades Recentes</h2>
        <div className="text-gray-500 text-center py-8">
          <Clock className="w-12 h-12 mx-auto mb-4 text-gray-300" />
          <p>Funcionalidade em desenvolvimento</p>
          <p className="text-sm">Em breve você verá as atividades mais recentes aqui</p>
        </div>
      </div>
    </div>
  );
}