import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  Search, 
  Edit2, 
  Trash2, 
  FileText,
  Calculator,
  User,
  DollarSign,
  Calendar,
  Package,
  MessageSquare
} from 'lucide-react';
import { budgetsApi, clientsApi, servicesApi } from '../services/api';

const PAYMENT_METHODS = {
  PIX_CNPJ_25995295000104: 'PIX (CNPJ 25995295000104)',
  PIX_CNPJ_30369419000186: 'PIX (CNPJ 30369419000186)',
  DINHEIRO: 'Dinheiro',
  CREDITO_1X: 'Crédito 1x',
  CREDITO_2X: 'Crédito 2x',
  CREDITO_3X: 'Crédito 3x',
  CREDITO_4X: 'Crédito 4x',
  CREDITO_5X: 'Crédito 5x',
  CREDITO_6X: 'Crédito 6x',
  CREDITO_7X: 'Crédito 7x',
  CREDITO_8X: 'Crédito 8x',
  DEBITO: 'Débito',
  BOLETO: 'Boleto',
  LINK_PAGAMENTO: 'Link de Pagamento',
  TRANSFERENCIA: 'Transferência',
  PERMUTA: 'Permuta'
};

const SALESPERSONS = {
  'Gabriela Alcântara': 'Gabriela Alcântara',
  'Diego Olivatto': 'Diego Olivatto',
  'Daiana Olivatto': 'Daiana Olivatto',
  'Marcos Anthonio': 'Marcos Anthonio'
};

const BudgetCard = ({ budget, onEdit, onDelete, onAddItem }) => (
  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div className="flex items-start justify-between mb-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">{budget.id}</h3>
        <p className="text-blue-600 font-medium">{budget.client_name}</p>
        <p className="text-sm text-gray-500">
          Vendedor: {budget.salesperson}
        </p>
      </div>
      <div className="flex space-x-2">
        <button
          onClick={() => onAddItem(budget)}
          className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
          title="Adicionar Item"
        >
          <Plus className="w-4 h-4" />
        </button>
        <button
          onClick={() => onEdit(budget)}
          className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg transition-colors"
          title="Editar"
        >
          <Edit2 className="w-4 h-4" />
        </button>
        <button
          onClick={() => onDelete(budget)}
          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          title="Excluir"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>

    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
      <div className="text-center p-3 bg-blue-50 rounded-lg">
        <Package className="w-5 h-5 text-blue-600 mx-auto mb-1" />
        <div className="text-lg font-bold text-blue-900">{budget.total_units}</div>
        <div className="text-xs text-blue-600">Itens</div>
      </div>
      
      <div className="text-center p-3 bg-green-50 rounded-lg">
        <Calculator className="w-5 h-5 text-green-600 mx-auto mb-1" />
        <div className="text-lg font-bold text-green-900">{budget.total_area_m2.toFixed(1)}</div>
        <div className="text-xs text-green-600">m²</div>
      </div>
      
      <div className="text-center p-3 bg-purple-50 rounded-lg">
        <Calculator className="w-5 h-5 text-purple-600 mx-auto mb-1" />
        <div className="text-lg font-bold text-purple-900">{budget.total_linear_meters.toFixed(1)}</div>
        <div className="text-xs text-purple-600">m lineares</div>
      </div>
      
      <div className="text-center p-3 bg-yellow-50 rounded-lg">
        <DollarSign className="w-5 h-5 text-yellow-600 mx-auto mb-1" />
        <div className="text-lg font-bold text-yellow-900">R$ {budget.total_value.toFixed(2)}</div>
        <div className="text-xs text-yellow-600">Total</div>
      </div>
    </div>

    <div className="text-sm text-gray-600 space-y-1">
      <div className="flex justify-between">
        <span>Pagamento:</span>
        <span className="font-medium">{PAYMENT_METHODS[budget.payment_method]}</span>
      </div>
      <div className="flex justify-between">
        <span>Criado:</span>
        <span>{new Date(budget.created_at).toLocaleDateString('pt-BR')}</span>
      </div>
      {budget.budget_observations && (
        <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
          <strong>Observações:</strong> {budget.budget_observations}
        </div>
      )}
    </div>

    {budget.items && budget.items.length > 0 && (
      <div className="mt-4 border-t pt-4">
        <h4 className="text-sm font-medium text-gray-900 mb-2">Itens:</h4>
        <div className="space-y-1">
          {budget.items.map((item, index) => (
            <div key={index} className="text-xs text-gray-600 flex justify-between">
              <span className="truncate pr-2">{item.service_name}</span>
              <span className="font-medium">R$ {item.total_value.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
);

const BudgetForm = ({ budget, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    client_id: '',
    payment_method: 'PIX_CNPJ_25995295000104',
    salesperson: 'Gabriela Alcântara',
    internal_observations: '',
    budget_observations: ''
  });
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [clientSearch, setClientSearch] = useState('');

  useEffect(() => {
    loadClients();
    if (budget) {
      setFormData({
        client_id: budget.client_id,
        payment_method: budget.payment_method,
        salesperson: budget.salesperson,
        internal_observations: budget.internal_observations || '',
        budget_observations: budget.budget_observations || ''
      });
    }
  }, [budget]);

  const loadClients = async () => {
    try {
      const response = await clientsApi.getAll();
      setClients(response.data);
    } catch (error) {
      console.error('Erro ao carregar clientes:', error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onSave(formData);
    } finally {
      setLoading(false);
    }
  };

  const filteredClients = clients.filter(client =>
    client.name.toLowerCase().includes(clientSearch.toLowerCase()) ||
    client.id.toLowerCase().includes(clientSearch.toLowerCase())
  );

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {budget ? 'Editar Orçamento' : 'Novo Orçamento'}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Cliente *
            </label>
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Buscar cliente..."
                value={clientSearch}
                onChange={(e) => setClientSearch(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <select
                name="client_id"
                value={formData.client_id}
                onChange={handleInputChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Selecione um cliente</option>
                {filteredClients.map((client) => (
                  <option key={client.id} value={client.id}>
                    {client.name} ({client.id})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Forma de Pagamento *
              </label>
              <select
                name="payment_method"
                value={formData.payment_method}
                onChange={handleInputChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {Object.entries(PAYMENT_METHODS).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Vendedor Responsável *
              </label>
              <select
                name="salesperson"
                value={formData.salesperson}
                onChange={handleInputChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {Object.entries(SALESPERSONS).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Observações Internas
            </label>
            <textarea
              name="internal_observations"
              value={formData.internal_observations}
              onChange={handleInputChange}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Instruções para o técnico (não aparece no orçamento)"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Observações do Orçamento
            </label>
            <textarea
              name="budget_observations"
              value={formData.budget_observations}
              onChange={handleInputChange}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Observações que aparecerão no PDF do orçamento"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
            >
              {loading ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const AddItemForm = ({ budget, onSave, onCancel }) => {
  const [services, setServices] = useState([]);
  const [selectedService, setSelectedService] = useState(null);
  const [formData, setFormData] = useState({
    service_id: '',
    quantity: 1,
    observations: '',
    width: '',
    height: '',
    diameter: '',
    fabric_folds: '',
    fabric_per_fold: 18
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadServices();
  }, []);

  const loadServices = async () => {
    try {
      const response = await servicesApi.getAll();
      setServices(response.data.filter(s => s.is_active));
    } catch (error) {
      console.error('Erro ao carregar serviços:', error);
    }
  };

  const handleServiceChange = (e) => {
    const serviceId = e.target.value;
    const service = services.find(s => s.id === serviceId);
    setSelectedService(service);
    setFormData(prev => ({
      ...prev,
      service_id: serviceId
    }));
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onSave(formData);
    } finally {
      setLoading(false);
    }
  };

  const renderMeasureFields = () => {
    if (!selectedService) return null;

    switch (selectedService.measure_type) {
      case 'AREA_DE_TAPETE':
      case 'CARPETE_TAPETE_LOCAL':
      case 'AREA_PERSIANA':
        return (
          <div className="space-y-4">
            <h4 className="font-medium text-gray-900">
              Medidas do {selectedService.measure_type.includes('PERSIANA') ? 'Persiana' : 'Tapete/Carpete'}
            </h4>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-gray-700 mb-1">Largura (m)</label>
                <input
                  type="number"
                  name="width"
                  value={formData.width}
                  onChange={handleInputChange}
                  step="0.01"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-700 mb-1">Altura (m)</label>
                <input
                  type="number"
                  name="height"
                  value={formData.height}
                  onChange={handleInputChange}
                  step="0.01"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-700 mb-1">Área Total (m²)</label>
                <input
                  type="number"
                  value={formData.width && formData.height ? (parseFloat(formData.width) * parseFloat(formData.height)).toFixed(2) : ''}
                  readOnly
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                />
              </div>
            </div>
          </div>
        );

      case 'TAPETE_REDONDO_DIAMETRO':
        const radius = formData.diameter ? parseFloat(formData.diameter) / 2 : 0;
        const area = radius ? (radius * radius * 3.14).toFixed(2) : '';
        return (
          <div className="space-y-4">
            <h4 className="font-medium text-gray-900">Medidas do Tapete</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-700 mb-1">Diâmetro (m)</label>
                <input
                  type="number"
                  name="diameter"
                  value={formData.diameter}
                  onChange={handleInputChange}
                  step="0.01"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-700 mb-1">Área Total (m²)</label>
                <input
                  type="number"
                  value={area}
                  readOnly
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                />
              </div>
            </div>
          </div>
        );

      case 'METRAGEM_LINEAR_CORTINA_SIMPLES':
      case 'METRAGEM_LINEAR_PE_DIREITO_DUPLO':
      case 'METRAGEM_LINEAR_ESPECIAL':
        const linearMeters = formData.fabric_folds && formData.fabric_per_fold 
          ? ((parseFloat(formData.fabric_folds) * parseFloat(formData.fabric_per_fold)) / 100).toFixed(2)
          : '';
        return (
          <div className="space-y-4">
            <h4 className="font-medium text-gray-900">Medidas da Cortina</h4>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-gray-700 mb-1">Quantidade de Dobras</label>
                <input
                  type="number"
                  name="fabric_folds"
                  value={formData.fabric_folds}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-700 mb-1">Tecido por Dobra</label>
                <input
                  type="number"
                  name="fabric_per_fold"
                  value={formData.fabric_per_fold}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-700 mb-1">Metragem Linear</label>
                <input
                  type="number"
                  value={linearMeters}
                  readOnly
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                />
              </div>
            </div>
          </div>
        );

      default:
        return (
          <div>
            <label className="block text-sm text-gray-700 mb-1">Quantidade</label>
            <input
              type="number"
              name="quantity"
              value={formData.quantity}
              onChange={handleInputChange}
              min="1"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        );
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            Adicionar Item ao Orçamento {budget.id}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Serviço *
            </label>
            <select
              name="service_id"
              value={formData.service_id}
              onChange={handleServiceChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Selecione um serviço</option>
              {services.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.name} ({service.id}) - R$ {service.sale_price.toFixed(2)}
                </option>
              ))}
            </select>
          </div>

          {selectedService && (
            <div className="p-4 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">Informações do Serviço</h4>
              <div className="text-sm text-blue-800 space-y-1">
                <p><strong>Categoria:</strong> {selectedService.category}</p>
                <p><strong>Tipo de Medida:</strong> {selectedService.measure_type}</p>
                <p><strong>Local de Execução:</strong> {selectedService.execution_location}</p>
                <p><strong>Preço Unitário:</strong> R$ {selectedService.sale_price.toFixed(2)}</p>
              </div>
            </div>
          )}

          {renderMeasureFields()}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Observações do Item
            </label>
            <textarea
              name="observations"
              value={formData.observations}
              onChange={handleInputChange}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Observações específicas deste item"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || !selectedService}
              className="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
            >
              {loading ? 'Adicionando...' : 'Adicionar Item'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export function Budgets() {
  const [budgets, setBudgets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [showAddItemForm, setShowAddItemForm] = useState(false);
  const [editingBudget, setEditingBudget] = useState(null);
  const [selectedBudget, setSelectedBudget] = useState(null);

  useEffect(() => {
    loadBudgets();
  }, []);

  const loadBudgets = async () => {
    try {
      setLoading(true);
      const response = await budgetsApi.getAll({ search: searchTerm });
      setBudgets(response.data);
    } catch (error) {
      console.error('Erro ao carregar orçamentos:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
  };

  useEffect(() => {
    const debounced = setTimeout(() => {
      if (searchTerm !== undefined) {
        loadBudgets();
      }
    }, 500);

    return () => clearTimeout(debounced);
  }, [searchTerm]);

  const handleSaveBudget = async (budgetData) => {
    try {
      if (editingBudget) {
        // Update logic would go here
        alert('Funcionalidade de edição será implementada em breve');
      } else {
        await budgetsApi.create(budgetData);
      }
      
      setShowForm(false);
      setEditingBudget(null);
      loadBudgets();
    } catch (error) {
      console.error('Erro ao salvar orçamento:', error);
      alert('Erro ao salvar orçamento. Tente novamente.');
    }
  };

  const handleAddItem = async (itemData) => {
    try {
      await budgetsApi.addItem(selectedBudget.id, itemData);
      setShowAddItemForm(false);
      setSelectedBudget(null);
      loadBudgets();
    } catch (error) {
      console.error('Erro ao adicionar item:', error);
      alert('Erro ao adicionar item. Tente novamente.');
    }
  };

  const handleDeleteBudget = async (budget) => {
    if (window.confirm(`Tem certeza que deseja excluir o orçamento ${budget.id}?`)) {
      try {
        // Delete logic would go here
        alert('Funcionalidade de exclusão será implementada em breve');
      } catch (error) {
        console.error('Erro ao excluir orçamento:', error);
        alert('Erro ao excluir orçamento. Tente novamente.');
      }
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
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Orçamentos</h1>
          <p className="text-gray-600">Gerencie os orçamentos da lavanderia</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5 mr-2" />
          Novo Orçamento
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
        <input
          type="text"
          placeholder="Buscar orçamentos por código ou cliente..."
          value={searchTerm}
          onChange={handleSearch}
          className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* Budgets Count */}
      <div className="text-sm text-gray-600">
        {budgets.length} orçamento{budgets.length !== 1 ? 's' : ''} encontrado{budgets.length !== 1 ? 's' : ''}
      </div>

      {/* Budgets Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {budgets.map((budget) => (
          <BudgetCard
            key={budget.id}
            budget={budget}
            onEdit={(budget) => {
              setEditingBudget(budget);
              setShowForm(true);
            }}
            onDelete={handleDeleteBudget}
            onAddItem={(budget) => {
              setSelectedBudget(budget);
              setShowAddItemForm(true);
            }}
          />
        ))}
      </div>

      {budgets.length === 0 && (
        <div className="text-center py-12">
          <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhum orçamento encontrado</h3>
          <p className="text-gray-500 mb-4">
            {searchTerm ? 'Tente ajustar sua busca' : 'Comece criando seu primeiro orçamento'}
          </p>
          {!searchTerm && (
            <button
              onClick={() => setShowForm(true)}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors"
            >
              <Plus className="w-5 h-5 mr-2" />
              Criar Orçamento
            </button>
          )}
        </div>
      )}

      {/* Budget Form Modal */}
      {showForm && (
        <BudgetForm
          budget={editingBudget}
          onSave={handleSaveBudget}
          onCancel={() => {
            setShowForm(false);
            setEditingBudget(null);
          }}
        />
      )}

      {/* Add Item Form Modal */}
      {showAddItemForm && selectedBudget && (
        <AddItemForm
          budget={selectedBudget}
          onSave={handleAddItem}
          onCancel={() => {
            setShowAddItemForm(false);
            setSelectedBudget(null);
          }}
        />
      )}
    </div>
  );
}