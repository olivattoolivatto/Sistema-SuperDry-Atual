import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  Search, 
  Edit2, 
  Eye, 
  EyeOff,
  Trash2,
  Filter,
  Package,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown
} from 'lucide-react';
import { servicesApi } from '../services/api';

const CATEGORIES = {
  ESTOFADOS: 'Estofados',
  COLCHOES: 'Colchões',
  BOX: 'Box',
  TAPETES: 'Tapetes',
  CARPETES_E_TAPETES_NO_LOCAL: 'Carpetes e Tapetes no Local',
  CORTINAS: 'Cortinas',
  PERSIANAS: 'Persianas',
  ITENS_INFANTIS: 'Itens Infantis',
  VEICULOS: 'Veículos',
  IMPERMEABILIZACAO: 'Impermeabilização',
  OUTROS_ITENS: 'Outros Itens'
};

const MEASURE_TYPES = {
  UNITARIO: 'Unitário',
  AREA_DE_TAPETE: 'Área de Tapete (m²)',
  CARPETE_TAPETE_LOCAL: 'Carpete/Tapete Local (m²)',
  TAPETE_REDONDO_DIAMETRO: 'Tapete Redondo (Diâmetro)',
  AREA_PERSIANA: 'Área Persiana (m²)',
  METRAGEM_LINEAR_CORTINA_SIMPLES: 'Metragem Linear - Cortina Simples',
  METRAGEM_LINEAR_PE_DIREITO_DUPLO: 'Metragem Linear - Pé Direito Duplo',
  METRAGEM_LINEAR_ESPECIAL: 'Metragem Linear - Especial'
};

const EXECUTION_LOCATIONS = {
  RETIRADA: 'Retirada',
  NO_LOCAL: 'No Local',
  CLIENTE_TROUXE: 'Cliente Trouxe'
};

const SERVICE_TYPES = {
  ESTOFADOS: ['Sofá', 'Cadeira', 'Puff', 'Poltrona', 'Chaise/Namoradeira', 'Cabeceira', 'Almofada no Local', 'Almofada Retirada'],
  COLCHOES: ['Solteiro', 'Viúvo/Solteiro Especial', 'Casal Padrão', 'Casal Queen', 'Casal King', 'Casal Super King', 'Especial'],
  BOX: ['Box Solteiro', 'Box Viúvo/Solteiro Especial', 'Box Casal Padrão', 'Box Casal Queen', 'Box Casal King', 'Box Casal Super King', 'Box Especial'],
  TAPETES: ['Tapete na Empresa', 'Tapete Parceiro'],
  CARPETES_E_TAPETES_NO_LOCAL: ['Tapete no Local', 'Carpete no Local'],
  CORTINAS: ['Cortina Simples', 'Cortina Pé Direito Duplo', 'Cortina Dupla ou Especial'],
  PERSIANAS: ['Persiana Vertical', 'Persiana Rolô/Romana', 'Persiana Horizontal Alumínio/Madeira'],
  ITENS_INFANTIS: ['Carrinho de Bebê', 'Cadeirinha', 'Bebê Conforto'],
  VEICULOS: ['Bancos de Veículo', 'Teto de Veículo', 'Carpete de Veículo', 'Forrações de Portas', 'Porta Malas', 'Interior Veículo Completo'],
  IMPERMEABILIZACAO: ['Impermeabilização de Sofá', 'Impermeabilização de Cadeiras', 'Impermeabilização de Poltronas', 'Impermeabilização de Almofadas'],
  OUTROS_ITENS: ['Itens Diversos']
};

const ServiceTable = ({ services, onEdit, onToggleStatus, onDelete }) => (
  <div className="overflow-x-auto">
    <table className="min-w-full bg-white">
      <thead className="bg-gray-50">
        <tr>
          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            Código
          </th>
          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            Nome do Serviço
          </th>
          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            Tipo
          </th>
          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            Medida
          </th>
          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            Execução
          </th>
          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            Custo
          </th>
          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            Venda
          </th>
          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            Status
          </th>
          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
            Ações
          </th>
        </tr>
      </thead>
      <tbody className="bg-white divide-y divide-gray-200">
        {services.map((service, index) => (
          <tr key={service.id} className={`${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'} ${!service.is_active ? 'opacity-60' : ''}`}>
            <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
              {service.id}
            </td>
            <td className="px-6 py-4 whitespace-nowrap">
              <div className="text-sm font-medium text-gray-900">{service.name}</div>
            </td>
            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {service.service_type}
            </td>
            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {MEASURE_TYPES[service.measure_type]}
            </td>
            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {EXECUTION_LOCATIONS[service.execution_location]}
            </td>
            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-red-600">
              R$ {service.cost_price.toFixed(2)}
            </td>
            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-green-600">
              R$ {service.sale_price.toFixed(2)}
            </td>
            <td className="px-6 py-4 whitespace-nowrap">
              {service.is_active ? (
                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                  Ativo
                </span>
              ) : (
                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                  Inativo
                </span>
              )}
            </td>
            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
              <div className="flex items-center justify-end space-x-2">
                <button
                  onClick={() => onToggleStatus(service)}
                  className={`p-2 rounded-lg transition-colors ${
                    service.is_active 
                      ? 'text-yellow-600 hover:bg-yellow-50' 
                      : 'text-green-600 hover:bg-green-50'
                  }`}
                  title={service.is_active ? 'Inativar' : 'Ativar'}
                >
                  {service.is_active ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => onEdit(service)}
                  className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  title="Editar"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => onDelete(service)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title="Excluir"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const ServiceForm = ({ service, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    name: '',
    category: 'ESTOFADOS',
    service_type: '',
    measure_type: 'UNITARIO',
    execution_location: 'RETIRADA',
    cost_price: 0,
    sale_price: 0
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (service) {
      setFormData(service);
    }
  }, [service]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name.includes('price') ? parseFloat(value) || 0 : value
    }));
  };

  const handleCategoryChange = (e) => {
    const category = e.target.value;
    setFormData(prev => ({
      ...prev,
      category,
      service_type: SERVICE_TYPES[category]?.[0] || ''
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

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {service ? 'Editar Serviço' : 'Novo Serviço'}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nome do Serviço *
            </label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Categoria *
              </label>
              <select
                name="category"
                value={formData.category}
                onChange={handleCategoryChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {Object.entries(CATEGORIES).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tipo de Serviço *
              </label>
              <select
                name="service_type"
                value={formData.service_type}
                onChange={handleInputChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {SERVICE_TYPES[formData.category]?.map((type) => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tipo de Medida *
              </label>
              <select
                name="measure_type"
                value={formData.measure_type}
                onChange={handleInputChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {Object.entries(MEASURE_TYPES).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Local de Execução *
              </label>
              <select
                name="execution_location"
                value={formData.execution_location}
                onChange={handleInputChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {Object.entries(EXECUTION_LOCATIONS).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Valor de Custo (R$) *
              </label>
              <input
                type="number"
                name="cost_price"
                value={formData.cost_price}
                onChange={handleInputChange}
                min="0"
                step="0.01"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Valor de Venda (R$) *
              </label>
              <input
                type="number"
                name="sale_price"
                value={formData.sale_price}
                onChange={handleInputChange}
                min="0"
                step="0.01"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
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

export function Catalog() {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [showInactive, setShowInactive] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingService, setEditingService] = useState(null);

  useEffect(() => {
    loadServices();
  }, []);

  const loadServices = async () => {
    try {
      setLoading(true);
      const params = {
        search: searchTerm,
        include_inactive: showInactive
      };
      if (selectedCategory) {
        params.category = selectedCategory;
      }
      
      const response = await servicesApi.getAll(params);
      setServices(response.data);
    } catch (error) {
      console.error('Erro ao carregar serviços:', error);
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
        loadServices();
      }
    }, 500);

    return () => clearTimeout(debounced);
  }, [searchTerm, selectedCategory, showInactive]);

  const handleSaveService = async (serviceData) => {
    try {
      if (editingService) {
        await servicesApi.update(editingService.id, serviceData);
      } else {
        await servicesApi.create(serviceData);
      }
      
      setShowForm(false);
      setEditingService(null);
      loadServices();
    } catch (error) {
      console.error('Erro ao salvar serviço:', error);
      alert('Erro ao salvar serviço. Tente novamente.');
    }
  };

  const handleToggleStatus = async (service) => {
    try {
      if (service.is_active) {
        await servicesApi.deactivate(service.id);
      } else {
        // Para reativar, fazemos um update
        await servicesApi.update(service.id, { ...service, is_active: true });
      }
      loadServices();
    } catch (error) {
      console.error('Erro ao alterar status do serviço:', error);
      alert('Erro ao alterar status do serviço. Tente novamente.');
    }
  };

  const handleDeleteService = async (service) => {
    if (window.confirm(`Tem certeza que deseja excluir o serviço ${service.name}?`)) {
      try {
        // Como não temos endpoint de delete, vamos inativar
        await servicesApi.deactivate(service.id);
        loadServices();
      } catch (error) {
        console.error('Erro ao excluir serviço:', error);
        alert('Erro ao excluir serviço. Tente novamente.');
      }
    }
  };

  // Group services by category
  const groupedServices = services.reduce((acc, service) => {
    const category = service.category;
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(service);
    return acc;
  }, {});

  const activeCount = services.filter(s => s.is_active).length;
  const inactiveCount = services.filter(s => !s.is_active).length;

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
          <h1 className="text-2xl font-bold text-gray-900">Catálogo de Serviços</h1>
          <p className="text-gray-600">Gerencie os serviços oferecidos pela lavanderia</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5 mr-2" />
          Novo Serviço
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Buscar serviços..."
              value={searchTerm}
              onChange={handleSearch}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Todas as categorias</option>
              {Object.entries(CATEGORIES).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="showInactive"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="showInactive" className="text-sm text-gray-700">
              Mostrar inativos
            </label>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-green-600">{activeCount}</div>
          <div className="text-sm text-gray-600">Serviços Ativos</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-red-600">{inactiveCount}</div>
          <div className="text-sm text-gray-600">Serviços Inativos</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-blue-600">{services.length}</div>
          <div className="text-sm text-gray-600">Total de Serviços</div>
        </div>
      </div>

      {/* Services by Category */}
      {Object.entries(groupedServices).map(([category, categoryServices]) => (
        <div key={category} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              {CATEGORIES[category]} ({categoryServices.length})
            </h2>
          </div>
          <ServiceTable
            services={categoryServices}
            onEdit={(service) => {
              setEditingService(service);
              setShowForm(true);
            }}
            onToggleStatus={handleToggleStatus}
            onDelete={handleDeleteService}
          />
        </div>
      ))}

      {services.length === 0 && (
        <div className="text-center py-12">
          <Package className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhum serviço encontrado</h3>
          <p className="text-gray-500 mb-4">
            {searchTerm || selectedCategory ? 'Tente ajustar seus filtros' : 'Comece cadastrando seu primeiro serviço'}
          </p>
          {!searchTerm && !selectedCategory && (
            <button
              onClick={() => setShowForm(true)}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors"
            >
              <Plus className="w-5 h-5 mr-2" />
              Cadastrar Serviço
            </button>
          )}
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <ServiceForm
          service={editingService}
          onSave={handleSaveService}
          onCancel={() => {
            setShowForm(false);
            setEditingService(null);
          }}
        />
      )}
    </div>
  );
}