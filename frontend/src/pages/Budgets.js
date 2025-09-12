import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
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
  MessageSquare,
  MessageCircle,
  Download,
  ChevronUp,
  ChevronDown,
  ArrowUpDown
} from 'lucide-react';
import { budgetsApi, clientsApi, servicesApi } from '../services/api';
import { toast } from '../hooks/use-toast';

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

const BudgetCard = ({ budget, onEdit, onDelete, onWhatsApp, onPDF }) => {
  // Função para agrupar itens iguais
  const groupItems = (items) => {
    const grouped = {};
    
    items.forEach(item => {
      const key = item.service_name;
      if (grouped[key]) {
        grouped[key].count += 1;
        grouped[key].totalValue += parseFloat(item.total_value || 0);
      } else {
        grouped[key] = {
          name: item.service_name,
          count: 1,
          totalValue: parseFloat(item.total_value || 0)
        };
      }
    });
    
    return Object.values(grouped);
  };

  const groupedItems = budget.items ? groupItems(budget.items) : [];

  return (
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
          onClick={() => onWhatsApp(budget)}
          className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
          title="Enviar WhatsApp"
        >
          <MessageCircle className="w-4 h-4" />
        </button>
        <button
          onClick={() => onPDF(budget)}
          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          title="Gerar PDF"
        >
          <Download className="w-4 h-4" />
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

    {groupedItems.length > 0 && (
      <div className="mt-4 border-t pt-4">
        <h4 className="text-sm font-medium text-gray-900 mb-2">Itens:</h4>
        <div className="space-y-1">
          {groupedItems.map((groupedItem, index) => (
            <div key={index} className="text-xs text-gray-600 flex justify-between">
              <span className="truncate pr-2">
                {groupedItem.name}
                {groupedItem.count > 1 && (
                  <span className="font-semibold text-blue-600"> ({groupedItem.count}un)</span>
                )}
              </span>
              <span className="font-medium">R$ {groupedItem.totalValue.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
  );
};

const BatchItemForm = ({ services, onAdd, onCancel }) => {
  const [serviceSearchTerm, setServiceSearchTerm] = useState('');
  const [selectedService, setSelectedService] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [showServiceDropdown, setShowServiceDropdown] = useState(false);

  // Função para normalizar texto para pesquisa
  const normalizeText = (text) => {
    return text
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '') // Remove acentos
      .replace(/\s+/g, ' ') // Normaliza espaços
      .trim();
  };

  // Filtrar e ordenar serviços baseado na pesquisa
  const filteredServices = serviceSearchTerm.trim() 
    ? services.filter(service => {
        const searchNormalized = normalizeText(serviceSearchTerm);
        const serviceNameNormalized = normalizeText(service.name);
        const serviceCategoryNormalized = normalizeText(service.category);
        const serviceTypeNormalized = normalizeText(service.service_type || '');
        
        return serviceNameNormalized.includes(searchNormalized) ||
               serviceCategoryNormalized.includes(searchNormalized) ||
               serviceTypeNormalized.includes(searchNormalized);
      }).slice(0, 10)
    : [];

  const handleServiceSelect = (service) => {
    setSelectedService(service);
    setServiceSearchTerm(service.name);
    setShowServiceDropdown(false);
  };

  const handleAdd = () => {
    if (!selectedService || quantity < 1) return;
    
    const batchItem = {
      service: selectedService,
      quantity: parseInt(quantity)
    };
    
    onAdd(batchItem);
    
    // Reset form
    setSelectedService(null);
    setServiceSearchTerm('');
    setQuantity(1);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Adicionar Item ao Lote</h3>
        </div>

        <div className="p-6 space-y-4">
          {/* Pesquisa de Serviço */}
          <div className="relative">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Buscar Serviço *
            </label>
            <input
              type="text"
              value={serviceSearchTerm}
              onChange={(e) => {
                setServiceSearchTerm(e.target.value);
                setShowServiceDropdown(true);
                setSelectedService(null);
              }}
              onFocus={() => setShowServiceDropdown(true)}
              placeholder="Digite para buscar serviços..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            
            {showServiceDropdown && filteredServices.length > 0 && (
              <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                {filteredServices.map((service) => (
                  <button
                    key={service.id}
                    type="button"
                    onClick={() => handleServiceSelect(service)}
                    className="w-full px-3 py-3 text-left hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors"
                  >
                    <div className="font-medium text-gray-900">{service.name}</div>
                    <div className="text-sm text-gray-600">
                      {service.category} • R$ {service.sale_price.toFixed(2)}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Serviço Selecionado */}
          {selectedService && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="font-medium text-green-900">{selectedService.name}</div>
              <div className="text-sm text-green-700">
                R$ {selectedService.sale_price.toFixed(2)} • {selectedService.category}
              </div>
            </div>
          )}

          {/* Quantidade */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Quantidade (repetições) *
            </label>
            <input
              type="number"
              min="1"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Número de vezes que este item será adicionado ao orçamento
            </p>
          </div>
        </div>

        <div className="flex justify-end space-x-3 px-6 py-4 border-t border-gray-200">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleAdd}
            disabled={!selectedService || quantity < 1}
            className="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            Adicionar ao Lote
          </button>
        </div>
      </div>
    </div>
  );
};

const BudgetForm = ({ budget, preSelectedClient, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    client_id: preSelectedClient?.id || '',
    payment_method: 'PIX_CNPJ_25995295000104',
    salesperson: 'Gabriela Alcântara',
    internal_observations: '',
    budget_observations: '',
    items: []
  });
  const [clients, setClients] = useState([]);
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [clientSearch, setClientSearch] = useState(preSelectedClient?.name || '');
  const [clientSuggestions, setClientSuggestions] = useState([]);
  const [selectedClient, setSelectedClient] = useState(preSelectedClient || null);
  const [showItemForm, setShowItemForm] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [showQuickAddClient, setShowQuickAddClient] = useState(false);
  const [creatingClient, setCreatingClient] = useState(false);
  
  // Estados para Lançamento em Lote
  const [batchMode, setBatchMode] = useState(false);
  const [showBatchItemForm, setShowBatchItemForm] = useState(false);
  const [batchItems, setBatchItems] = useState([]);

  useEffect(() => {
    loadClients();
    loadServices();
    
    if (budget) {
      setFormData({
        client_id: budget.client_id,
        payment_method: budget.payment_method,
        salesperson: budget.salesperson,
        internal_observations: budget.internal_observations || '',
        budget_observations: budget.budget_observations || '',
        items: budget.items || []
      });
      
      // Pre-select client when editing budget
      setClientSearch(budget.client_name || '');
      setSelectedClient({
        id: budget.client_id,
        name: budget.client_name
      });
    }
    
    if (preSelectedClient) {
      setSelectedClient(preSelectedClient);
      setClientSearch(preSelectedClient.name);
    }
  }, [budget, preSelectedClient]);

  const loadClients = async () => {
    try {
      const response = await clientsApi.getAll();
      setClients(response.data);
    } catch (error) {
      console.error('Erro ao carregar clientes:', error);
    }
  };

  const loadServices = async () => {
    try {
      const response = await servicesApi.getAll();
      setServices(response.data.filter(s => s.is_active));
    } catch (error) {
      console.error('Erro ao carregar serviços:', error);
    }
  };

  const handleClientSearch = async (e) => {
    const value = e.target.value;
    setClientSearch(value);
    setShowQuickAddClient(false);
    
    if (value.length > 1) {
      try {
        const response = await clientsApi.getAll({ search: value });
        setClientSuggestions(response.data);
        
        // Se não encontrou resultados e o nome tem mais de 2 caracteres, mostrar opção de criar
        if (response.data.length === 0 && value.length > 2) {
          setShowQuickAddClient(true);
        }
      } catch (error) {
        console.error('Erro ao buscar clientes:', error);
        setClientSuggestions([]);
        if (value.length > 2) {
          setShowQuickAddClient(true);
        }
      }
    } else {
      setClientSuggestions([]);
    }
  };

  const handleClientSelect = (client) => {
    setSelectedClient(client);
    setClientSearch(client.name);
    setFormData(prev => ({
      ...prev,
      client_id: client.id
    }));
    setClientSuggestions([]);
    setShowQuickAddClient(false);
  };

  const handleQuickAddClient = async () => {
    if (!clientSearch.trim()) return;
    
    setCreatingClient(true);
    try {
      // Criar cliente com dados mínimos
      const quickClientData = {
        name: clientSearch.trim(),
        phone_primary: "A COMPLETAR",
        phone_alternative: "",
        email: "a.completar@email.com",
        cpf_cnpj: "",
        address: {
          full_address: "Endereço a completar",
          complement: "",
          neighborhood: "Bairro a completar", 
          city: "Cidade a completar",
          state: "SP",
          latitude: 0,
          longitude: 0
        }
      };
      
      const response = await clientsApi.create(quickClientData);
      const newClient = response.data;
      
      // Selecionar o cliente recém-criado
      setSelectedClient(newClient);
      setFormData(prev => ({
        ...prev,
        client_id: newClient.id
      }));
      setClientSuggestions([]);
      setShowQuickAddClient(false);
      
      // Mostrar mensagem de aviso
      toast({
        title: "Cliente criado rapidamente!",
        description: `${newClient.name} foi adicionado. ⚠️ COMPLETE O CADASTRO (telefone, endereço) antes de enviar para rota.`,
        variant: "default",
      });
      
    } catch (error) {
      console.error('Erro ao criar cliente:', error);
      toast({
        title: "Erro!",
        description: "Não foi possível criar o cliente. Tente novamente.",
        variant: "destructive",
      });
    }
    setCreatingClient(false);
  };

  const handleAddItem = (itemData) => {
    const service = services.find(s => s.id === itemData.service_id);
    if (!service) return;

    // Ensure numeric values
    const quantity = parseFloat(itemData.quantity) || 1;
    const area_m2 = parseFloat(itemData.area_m2) || 0;
    const linear_meters = parseFloat(itemData.linear_meters) || 0;
    const unit_price = parseFloat(itemData.unit_price) || parseFloat(service.sale_price) || 0; // Usar preço editável ou preço do catálogo como fallback
    
    // Calculate total based on the measure type
    let finalQuantity = quantity;
    if (service.measure_type === 'AREA_DE_TAPETE' || service.measure_type === 'TAPETE_REDONDO_DIAMETRO' || service.measure_type === 'AREA_PERSIANA') {
      finalQuantity = area_m2;
    } else if (service.measure_type.includes('METRAGEM_LINEAR')) {
      finalQuantity = linear_meters;
    }

    const newItem = {
      id: editingItem ? editingItem.id : `ITM-${String(Date.now()).slice(-7).padStart(7, '0')}`,
      service_id: itemData.service_id,
      service_name: service.name,
      service_code: itemData.service_id,
      quantity: finalQuantity,
      unit_price: unit_price,
      area_m2: area_m2,
      linear_meters: linear_meters,
      total_value: finalQuantity * unit_price,
      observations: itemData.observations || '',
      status: editingItem ? editingItem.status : 'RETIRAR',
      execution_location: service.execution_location || 'RETIRADA',
      is_retoque: editingItem ? editingItem.is_retoque : false,
      created_at: editingItem ? editingItem.created_at : new Date().toISOString()
    };

    setFormData(prev => ({
      ...prev,
      items: editingItem 
        ? prev.items.map(item => item.id === editingItem.id ? newItem : item)
        : [...prev.items, newItem]
    }));
    setShowItemForm(false);
    setEditingItem(null); // Clear editing state
  };

  const handleEditItem = (item) => {
    setEditingItem(item);
    setShowItemForm(true);
  };

  // Funções para Lançamento em Lote
  const handleAddToBatch = (batchItem) => {
    setBatchItems(prev => [...prev, batchItem]);
    setShowBatchItemForm(false);
  };

  const handleRemoveFromBatch = (index) => {
    setBatchItems(prev => prev.filter((_, i) => i !== index));
  };

  const handleProcessBatch = async () => {
    try {
      // Processar cada item do lote
      for (const batchItem of batchItems) {
        const { service, quantity } = batchItem;
        
        // Criar múltiplas instâncias do mesmo serviço
        for (let i = 0; i < quantity; i++) {
          const itemData = {
            service_id: service.id,
            quantity: 1,
            // Todas as medidas com valor "1"
            area_m2: 1,
            linear_meters: 1,
            width: 1,
            height: 1,
            diameter: 1,
            fabric_folds: 1,
            fabric_per_fold: 18, // Manter padrão existente
            observations: ''
          };
          
          await handleAddItem(itemData);
        }
      }
      
      // Limpar lote após processamento
      setBatchItems([]);
      setBatchMode(false);
      
      toast({
        title: "Lote processado!",
        description: `${batchItems.reduce((sum, item) => sum + item.quantity, 0)} itens adicionados ao orçamento.`,
        variant: "default",
      });
      
    } catch (error) {
      console.error('Erro ao processar lote:', error);
      toast({
        title: "Erro!",
        description: "Erro ao processar lote. Tente novamente.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteItem = (itemId) => {
    if (window.confirm('Tem certeza que deseja excluir este item?')) {
      setFormData(prev => ({
        ...prev,
        items: prev.items.filter(item => item.id !== itemId)
      }));
    }
  };

  const calculateTotals = () => {
    const items = formData.items;
    return {
      totalValue: items.reduce((sum, item) => sum + parseFloat(item.total_value || 0), 0),
      totalArea: items.reduce((sum, item) => sum + parseFloat(item.area_m2 || 0), 0),
      totalLinear: items.reduce((sum, item) => sum + parseFloat(item.linear_meters || 0), 0),
      totalUnits: items.length
    };
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
    
    if (!selectedClient) {
      alert('Por favor, selecione um cliente válido');
      return;
    }
    
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
          <div className="relative">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Cliente *
            </label>
            <input
              type="text"
              placeholder="Digite o nome do cliente para buscar..."
              value={clientSearch}
              onChange={handleClientSearch}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            
            {(clientSuggestions.length > 0 || showQuickAddClient) && (
              <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                {clientSuggestions.map((client) => (
                  <button
                    key={client.id}
                    type="button"
                    onClick={() => handleClientSelect(client)}
                    className="w-full px-3 py-3 text-left hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">
                          {client.name}
                        </div>
                        <div className="text-sm text-gray-500">
                          {client.id} • {client.phone_primary}
                        </div>
                        <div className="text-xs text-gray-400">
                          {client.address.neighborhood}, {client.address.city} - {client.address.state}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
                
                {showQuickAddClient && (
                  <button
                    type="button"
                    onClick={handleQuickAddClient}
                    disabled={creatingClient}
                    className="w-full px-3 py-3 text-left hover:bg-green-50 border-b border-gray-100 last:border-b-0 transition-colors bg-green-25 border-green-200"
                  >
                    <div className="flex items-center">
                      <Plus className="w-4 h-4 text-green-600 mr-2" />
                      <div>
                        <div className="font-medium text-green-800">
                          {creatingClient ? 'Criando cliente...' : `+ Criar cliente "${clientSearch}"`}
                        </div>
                        <div className="text-xs text-green-600">
                          Criação rápida - Complete o cadastro depois
                        </div>
                      </div>
                    </div>
                  </button>
                )}
              </div>
            )}
            
            {selectedClient && (
              <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="font-medium text-blue-900">{selectedClient.name}</div>
                    <div className="text-sm text-blue-700">
                      {selectedClient.id} • {selectedClient.phone_primary}
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    {/* Checkbox Lançamento em Lote */}
                    <label className="flex items-center space-x-2 text-sm">
                      <input
                        type="checkbox"
                        checked={batchMode}
                        onChange={(e) => setBatchMode(e.target.checked)}
                        className="rounded border-blue-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="font-medium text-blue-900">Lançamento em Lote</span>
                    </label>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedClient(null);
                        setClientSearch('');
                        setFormData(prev => ({ ...prev, client_id: '' }));
                        setBatchMode(false);
                        setBatchItems([]);
                      }}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              </div>
            )}
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

          {/* Seção de Itens */}
          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">
                {batchMode ? 'Lançamento em Lote - Itens Selecionados' : 'Itens do Orçamento'}
              </h3>
              
              {batchMode ? (
                <div className="flex space-x-2">
                  <button
                    type="button"
                    onClick={() => setShowBatchItemForm(true)}
                    className="flex items-center px-3 py-2 bg-purple-600 text-white hover:bg-purple-700 rounded-lg transition-colors text-sm"
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Adicionar ao Lote
                  </button>
                  {batchItems.length > 0 && (
                    <button
                      type="button"
                      onClick={handleProcessBatch}
                      className="flex items-center px-3 py-2 bg-green-600 text-white hover:bg-green-700 rounded-lg transition-colors text-sm"
                    >
                      <Package className="w-4 h-4 mr-1" />
                      Processar Lote ({batchItems.reduce((sum, item) => sum + item.quantity, 0)} itens)
                    </button>
                  )}
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowItemForm(true)}
                  className="flex items-center px-3 py-2 bg-green-600 text-white hover:bg-green-700 rounded-lg transition-colors text-sm"
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Adicionar Item
                </button>
              )}
            </div>

            {/* Lista de Itens do Lote */}
            {batchMode && batchItems.length > 0 && (
              <div className="mb-6 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                <h4 className="text-sm font-medium text-purple-900 mb-3">Itens no Lote:</h4>
                <div className="space-y-2">
                  {batchItems.map((batchItem, index) => (
                    <div key={index} className="flex items-center justify-between bg-white p-3 rounded border">
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">{batchItem.service.name}</div>
                        <div className="text-sm text-gray-600">
                          R$ {batchItem.service.sale_price.toFixed(2)} × {batchItem.quantity} = 
                          R$ {(batchItem.service.sale_price * batchItem.quantity).toFixed(2)}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveFromBatch(index)}
                        className="ml-3 text-red-600 hover:text-red-800"
                        title="Remover do lote"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
                <div className="mt-3 text-sm text-purple-700 font-medium">
                  Total do Lote: {batchItems.reduce((sum, item) => sum + item.quantity, 0)} itens • 
                  R$ {batchItems.reduce((sum, item) => sum + (item.service.sale_price * item.quantity), 0).toFixed(2)}
                </div>
              </div>
            )}

            {formData.items.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full bg-white border border-gray-200 rounded-lg">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Descrição</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Unidade</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Área M²</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Metragem Linear</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Quantidade</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Valor</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Informações</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {formData.items.map((item, index) => (
                      <tr key={item.id} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td className="px-4 py-3">
                          <div className="text-sm font-medium text-gray-900">{item.service_name}</div>
                          <div className="text-xs text-gray-500 font-mono">{item.service_code}</div>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900">{item.quantity}</td>
                        <td className="px-4 py-3 text-sm text-gray-900">{item.area_m2 ? parseFloat(item.area_m2).toFixed(2) : '-'}</td>
                        <td className="px-4 py-3 text-sm text-gray-900">{item.linear_meters ? parseFloat(item.linear_meters).toFixed(2) : '-'}</td>
                        <td className="px-4 py-3 text-sm text-gray-900">{item.quantity}</td>
                        <td className="px-4 py-3 text-sm font-medium text-green-600">R$ {parseFloat(item.total_value).toFixed(2)}</td>
                        <td className="px-4 py-3">
                          <div className="text-xs text-gray-600">
                            <div>Local: {item.execution_location}</div>
                            <div>Status: {item.status}</div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end space-x-2">
                            <button
                              type="button"
                              onClick={() => handleEditItem(item)}
                              className="p-1 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                              title="Editar"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteItem(item.id)}
                              className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors"
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

                {/* Totalizadores */}
                <div className="mt-4 bg-gray-50 p-4 rounded-lg">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div className="text-center">
                      <div className="font-medium text-gray-900">{calculateTotals().totalUnits}</div>
                      <div className="text-gray-500">Itens</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium text-gray-900">{calculateTotals().totalArea.toFixed(2)} m²</div>
                      <div className="text-gray-500">Área Total</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium text-gray-900">{calculateTotals().totalLinear.toFixed(2)} m</div>
                      <div className="text-gray-500">Metragem Linear</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium text-green-600 text-lg">R$ {calculateTotals().totalValue.toFixed(2)}</div>
                      <div className="text-gray-500">Valor Total</div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500 border border-gray-200 rounded-lg">
                <Package className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                <p>Nenhum item adicionado</p>
                <p className="text-sm">Clique em "Adicionar Item" para começar</p>
              </div>
            )}
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

        {/* Batch Item Form Modal */}
        {showBatchItemForm && (
          <BatchItemForm
            services={services}
            onAdd={handleAddToBatch}
            onCancel={() => setShowBatchItemForm(false)}
          />
        )}

        {/* Item Form Modal */}
        {showItemForm && (
          <ItemFormModal
            services={services}
            editingItem={editingItem}
            onSave={handleAddItem}
            onCancel={() => {
              setShowItemForm(false);
              setEditingItem(null);
            }}
          />
        )}
      </div>
    </div>
  );
};

const ItemFormModal = ({ services, editingItem, onSave, onCancel }) => {
  const [selectedService, setSelectedService] = useState(null);
  const [serviceSearchTerm, setServiceSearchTerm] = useState('');
  const [filteredServices, setFilteredServices] = useState([]);
  const [showServiceDropdown, setShowServiceDropdown] = useState(false);
  const [formData, setFormData] = useState({
    service_id: '',
    quantity: 1,
    observations: '',
    width: '',
    height: '',
    diameter: '',
    fabric_folds: '',
    fabric_per_fold: 18,
    linear_meters: '',
    unit_price: 0 // Novo campo para preço editável
  });

  // Function to normalize text (remove accents, case insensitive, whitespace insensitive)
  const normalizeText = (text) => {
    return text
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '') // Remove accents
      .replace(/\s+/g, ' ') // Normalize whitespace
      .trim();
  };

  // Filter services based on search term
  useEffect(() => {
    if (serviceSearchTerm.length >= 2) {
      const normalizedSearch = normalizeText(serviceSearchTerm);
      const filtered = services.filter(service => {
        const normalizedName = normalizeText(service.name);
        const normalizedId = normalizeText(service.id);
        const normalizedCategory = normalizeText(service.category || '');
        
        return normalizedName.includes(normalizedSearch) ||
               normalizedId.includes(normalizedSearch) ||
               normalizedCategory.includes(normalizedSearch);
      });
      setFilteredServices(filtered);
      setShowServiceDropdown(true);
    } else {
      setFilteredServices([]);
      setShowServiceDropdown(false);
    }
  }, [serviceSearchTerm, services]);

  useEffect(() => {
    if (editingItem) {
      // Populate form with editing item data
      setFormData({
        service_id: editingItem.service_id,
        quantity: editingItem.quantity,
        observations: editingItem.observations || '',
        width: '',
        height: '',
        diameter: '',
        fabric_folds: '',
        fabric_per_fold: 18,
        linear_meters: editingItem.linear_meters || '',
        unit_price: editingItem.unit_price || 0 // Carregar preço do item sendo editado
      });
      const service = services.find(s => s.id === editingItem.service_id);
      if (service) {
        setSelectedService(service);
        setServiceSearchTerm(service.name); // Set search term to service name
      }
    }
  }, [editingItem, services]);

  const handleServiceSelect = (service) => {
    setSelectedService(service);
    setServiceSearchTerm(service.name);
    setFormData(prev => ({ 
      ...prev, 
      service_id: service.id,
      unit_price: service.sale_price // Definir preço padrão do catálogo
    }));
    setShowServiceDropdown(false);
  };

  const handleServiceSearchChange = (e) => {
    const value = e.target.value;
    setServiceSearchTerm(value);
    
    // Clear selected service if search is cleared
    if (value === '') {
      setSelectedService(null);
      setFormData(prev => ({ ...prev, service_id: '' }));
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

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Calculate measurements based on service type
    let calculatedData = { ...formData };
    
    if (selectedService) {
      switch (selectedService.measure_type) {
        case 'AREA_DE_TAPETE':
        case 'CARPETE_TAPETE_LOCAL':
        case 'AREA_PERSIANA':
          if (formData.width && formData.height) {
            calculatedData.area_m2 = parseFloat(formData.width) * parseFloat(formData.height);
            calculatedData.quantity = calculatedData.area_m2;
          }
          break;
        case 'TAPETE_REDONDO_DIAMETRO':
          if (formData.diameter) {
            const radius = parseFloat(formData.diameter) / 2;
            calculatedData.area_m2 = radius * radius * 3.14;
            calculatedData.quantity = calculatedData.area_m2;
          }
          break;
        case 'METRAGEM_LINEAR_CORTINA_SIMPLES':
        case 'METRAGEM_LINEAR_PE_DIREITO_DUPLO':
        case 'METRAGEM_LINEAR_ESPECIAL':
          // Priorizar valor manual ou calculado
          if (formData.linear_meters) {
            calculatedData.linear_meters = parseFloat(formData.linear_meters);
            calculatedData.quantity = parseFloat(formData.linear_meters);
          } else if (formData.fabric_folds && formData.fabric_per_fold) {
            calculatedData.linear_meters = (parseFloat(formData.fabric_folds) * parseFloat(formData.fabric_per_fold)) / 100;
            calculatedData.quantity = calculatedData.linear_meters;
          }
          break;
        default:
          calculatedData.quantity = parseFloat(formData.quantity) || 1;
      }
    }
    
    onSave(calculatedData);
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
        const calculatedLinearMeters = formData.fabric_folds && formData.fabric_per_fold 
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
                  placeholder="Opcional - para cálculo automático"
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
                <label className="block text-sm text-gray-700 mb-1">Metragem Linear *</label>
                <input
                  type="number"
                  name="linear_meters"
                  value={formData.linear_meters || calculatedLinearMeters}
                  onChange={handleInputChange}
                  step="0.01"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Digite ou será calculado automaticamente"
                />
              </div>
            </div>
            <div className="text-sm text-gray-600 bg-blue-50 p-3 rounded-lg">
              <p><strong>Como usar:</strong></p>
              <p>• <strong>Cálculo automático:</strong> Preencha "Quantidade de Dobras" e "Tecido por Dobra"</p>
              <p>• <strong>Manual:</strong> Digite diretamente no campo "Metragem Linear"</p>
              <p>• Se preencher os campos de dobras, o valor será calculado automaticamente</p>
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
            {editingItem ? 'Editar Item' : 'Adicionar Item'}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Serviço *
            </label>
            <div className="relative">
              <input
                type="text"
                value={serviceSearchTerm}
                onChange={handleServiceSearchChange}
                onFocus={() => {
                  if (serviceSearchTerm.length >= 2) {
                    setShowServiceDropdown(true);
                  }
                }}
                placeholder="Digite para pesquisar serviços (mín. 2 caracteres)"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              
              {showServiceDropdown && filteredServices.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                  {filteredServices.map((service) => (
                    <div
                      key={service.id}
                      onClick={() => handleServiceSelect(service)}
                      className="px-3 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                    >
                      <div className="font-medium text-gray-900">{service.name}</div>
                      <div className="text-sm text-gray-500">
                        {service.id} • {service.category} • R$ {service.sale_price.toFixed(2)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              {serviceSearchTerm.length >= 2 && filteredServices.length === 0 && showServiceDropdown && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg p-3 text-center text-gray-500">
                  Nenhum serviço encontrado para "{serviceSearchTerm}"
                </div>
              )}
            </div>
          </div>

          {selectedService && (
            <div className="p-4 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">Informações do Serviço</h4>
              <div className="text-sm text-blue-800 space-y-1">
                <p><strong>Categoria:</strong> {selectedService.category}</p>
                <p><strong>Tipo de Medida:</strong> {selectedService.measure_type}</p>
                <p><strong>Local de Execução:</strong> {selectedService.execution_location}</p>
                <p><strong>Status:</strong> {selectedService.default_service_status}</p>
                <p><strong>Preço do Catálogo:</strong> R$ {selectedService.sale_price.toFixed(2)}</p>
              </div>
            </div>
          )}

          {/* Campo para editar preço unitário */}
          {selectedService && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Preço Unitário (R$) *
              </label>
              <input
                type="number"
                name="unit_price"
                value={formData.unit_price}
                onChange={handleInputChange}
                min="0"
                step="0.01"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="0.00"
              />
              <p className="text-xs text-gray-500 mt-1">
                Você pode ajustar o preço para aplicar descontos ou incrementos em relação ao valor do catálogo
              </p>
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
              disabled={!selectedService}
              className="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
            >
              {editingItem ? 'Atualizar' : 'Adicionar'} Item
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
  const [serviceSearchTerm, setServiceSearchTerm] = useState('');
  const [filteredServices, setFilteredServices] = useState([]);
  const [showServiceDropdown, setShowServiceDropdown] = useState(false);
  const [formData, setFormData] = useState({
    service_id: '',
    quantity: 1,
    observations: '',
    width: '',
    height: '',
    diameter: '',
    fabric_folds: '',
    fabric_per_fold: 18,
    linear_meters: ''
  });
  const [loading, setLoading] = useState(false);

  // Function to normalize text (same as in ItemFormModal)
  const normalizeText = (text) => {
    return text
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '') // Remove accents
      .replace(/\s+/g, ' ') // Normalize whitespace
      .trim();
  };

  // Filter services based on search term
  useEffect(() => {
    if (serviceSearchTerm.length >= 2) {
      const normalizedSearch = normalizeText(serviceSearchTerm);
      const filtered = services.filter(service => {
        const normalizedName = normalizeText(service.name);
        const normalizedId = normalizeText(service.id);
        const normalizedCategory = normalizeText(service.category || '');
        
        return normalizedName.includes(normalizedSearch) ||
               normalizedId.includes(normalizedSearch) ||
               normalizedCategory.includes(normalizedSearch);
      });
      setFilteredServices(filtered);
      setShowServiceDropdown(true);
    } else {
      setFilteredServices([]);
      setShowServiceDropdown(false);
    }
  }, [serviceSearchTerm, services]);

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

  const handleServiceSelect = (service) => {
    setSelectedService(service);
    setServiceSearchTerm(service.name);
    setFormData(prev => ({ ...prev, service_id: service.id }));
    setShowServiceDropdown(false);
  };

  const handleServiceSearchChange = (e) => {
    const value = e.target.value;
    setServiceSearchTerm(value);
    
    // Clear selected service if search is cleared
    if (value === '') {
      setSelectedService(null);
      setFormData(prev => ({ ...prev, service_id: '' }));
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
        const calculatedLinearMeters = formData.fabric_folds && formData.fabric_per_fold 
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
                  placeholder="Opcional - para cálculo automático"
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
                <label className="block text-sm text-gray-700 mb-1">Metragem Linear *</label>
                <input
                  type="number"
                  name="linear_meters"
                  value={formData.linear_meters || calculatedLinearMeters}
                  onChange={handleInputChange}
                  step="0.01"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Digite ou será calculado automaticamente"
                />
              </div>
            </div>
            <div className="text-sm text-gray-600 bg-blue-50 p-3 rounded-lg">
              <p><strong>Como usar:</strong></p>
              <p>• <strong>Cálculo automático:</strong> Preencha "Quantidade de Dobras" e "Tecido por Dobra"</p>
              <p>• <strong>Manual:</strong> Digite diretamente no campo "Metragem Linear"</p>
              <p>• Se preencher os campos de dobras, o valor será calculado automaticamente</p>
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
            <div className="relative">
              <input
                type="text"
                value={serviceSearchTerm}
                onChange={handleServiceSearchChange}
                onFocus={() => {
                  if (serviceSearchTerm.length >= 2) {
                    setShowServiceDropdown(true);
                  }
                }}
                placeholder="Digite para pesquisar serviços (mín. 2 caracteres)"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              
              {showServiceDropdown && filteredServices.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                  {filteredServices.map((service) => (
                    <div
                      key={service.id}
                      onClick={() => handleServiceSelect(service)}
                      className="px-3 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                    >
                      <div className="font-medium text-gray-900">{service.name}</div>
                      <div className="text-sm text-gray-500">
                        {service.id} • {service.category} • R$ {service.sale_price.toFixed(2)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              {serviceSearchTerm.length >= 2 && filteredServices.length === 0 && showServiceDropdown && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg p-3 text-center text-gray-500">
                  Nenhum serviço encontrado para "{serviceSearchTerm}"
                </div>
              )}
            </div>
          </div>

          {selectedService && (
            <div className="p-4 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">Informações do Serviço</h4>
              <div className="text-sm text-blue-800 space-y-1">
                <p><strong>Categoria:</strong> {selectedService.category}</p>
                <p><strong>Tipo de Medida:</strong> {selectedService.measure_type}</p>
                <p><strong>Local de Execução:</strong> {selectedService.execution_location}</p>
                <p><strong>Status:</strong> {selectedService.default_service_status}</p>
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
  const location = useLocation();
  const preSelectedClient = location.state?.selectedClient;
  
  const [budgets, setBudgets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showForm, setShowForm] = useState(!!preSelectedClient);
  const [editingBudget, setEditingBudget] = useState(null);
  const [sortColumn, setSortColumn] = useState('created_at');
  const [sortDirection, setSortDirection] = useState('desc');

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

  // Função de ordenação
  const handleSort = (column) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  // Função para ordenar os orçamentos
  const sortedBudgets = [...budgets].sort((a, b) => {
    let aValue, bValue;

    switch (sortColumn) {
      case 'id':
        aValue = a.id;
        bValue = b.id;
        break;
      case 'client_name':
        aValue = a.client_name.toLowerCase();
        bValue = b.client_name.toLowerCase();
        break;
      case 'total_value':
        aValue = parseFloat(a.total_value);
        bValue = parseFloat(b.total_value);
        break;
      case 'total_units':
        aValue = parseInt(a.total_units);
        bValue = parseInt(b.total_units);
        break;
      case 'payment_method':
        aValue = PAYMENT_METHODS[a.payment_method];
        bValue = PAYMENT_METHODS[b.payment_method];
        break;
      case 'salesperson':
        aValue = a.salesperson;
        bValue = b.salesperson;
        break;
      case 'created_at':
      default:
        aValue = new Date(a.created_at);
        bValue = new Date(b.created_at);
        break;
    }

    if (sortDirection === 'asc') {
      return aValue > bValue ? 1 : -1;
    } else {
      return aValue < bValue ? 1 : -1;
    }
  });

  // Função para renderizar ícone de ordenação
  const renderSortIcon = (column) => {
    if (sortColumn !== column) {
      return <ArrowUpDown className="w-4 h-4" />;
    }
    return sortDirection === 'asc' ? 
      <ChevronUp className="w-4 h-4" /> : 
      <ChevronDown className="w-4 h-4" />;
  };

  const handleSaveBudget = async (budgetData) => {
    try {
      if (editingBudget) {
        // Update existing budget
        await budgetsApi.update(editingBudget.id, budgetData);
        toast({
          title: "Sucesso!",
          description: "Orçamento atualizado com sucesso!",
          variant: "default",
        });
      } else {
        // Create new budget
        await budgetsApi.create(budgetData);
        toast({
          title: "Sucesso!",
          description: "Orçamento criado com sucesso!",
          variant: "default",
        });
      }
      
      setShowForm(false);
      setEditingBudget(null);
      loadBudgets();
    } catch (error) {
      console.error('Erro ao salvar orçamento:', error);
      toast({
        title: "Erro!",
        description: "Erro ao salvar orçamento. Tente novamente.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteBudget = async (budget) => {
    if (window.confirm(`Tem certeza que deseja excluir o orçamento ${budget.id}?`)) {
      try {
        await budgetsApi.delete(budget.id);
        toast({
          title: "Sucesso!",
          description: "Orçamento excluído com sucesso!",
          variant: "default",
        });
        loadBudgets();
      } catch (error) {
        console.error('Erro ao excluir orçamento:', error);
        toast({
          title: "Erro!",
          description: "Erro ao excluir orçamento. Tente novamente.",
          variant: "destructive",
        });
      }
    }
  };

  const handleWhatsAppBudget = async (budget) => {
    try {
      const response = await budgetsApi.generateWhatsApp(budget.id);
      const data = response.data;
      
      // Check if URL with text is available
      if (data.whatsapp_url_with_text) {
        // Open WhatsApp with the formatted message
        window.open(data.whatsapp_url_with_text, '_blank');
        
        toast({
          title: "WhatsApp aberto!",
          description: "Mensagem do orçamento formatada e pronta para envio.",
          variant: "default",
        });
      } else {
        // Message too long, open WhatsApp without text and show copy option
        window.open(data.whatsapp_url, '_blank');
        
        // Copy message to clipboard
        navigator.clipboard.writeText(data.message).then(() => {
          toast({
            title: "WhatsApp aberto + Mensagem copiada!",
            description: "Cole a mensagem manualmente no WhatsApp. Já está na área de transferência.",
            variant: "default",
          });
        }).catch(() => {
          // Fallback: show message in alert for manual copy
          alert(`WhatsApp aberto!\n\nMensagem para copiar:\n\n${data.message}`);
        });
      }
      
    } catch (error) {
      console.error('Erro ao gerar WhatsApp:', error);
      toast({
        title: "Erro!",
        description: "Erro ao gerar mensagem WhatsApp. Tente novamente.",
        variant: "destructive",
      });
    }
  };

  const handlePDFBudget = async (budget) => {
    try {
      const response = await budgetsApi.generatePDF(budget.id);
      
      // Create blob and download PDF
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `orcamento_${budget.id}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast({
        title: "PDF gerado!",
        description: "Orçamento baixado com sucesso!",
        variant: "default",
      });
    } catch (error) {
      console.error('Erro ao gerar PDF:', error);
      toast({
        title: "Erro!",
        description: "Erro ao gerar PDF. Tente novamente.",
        variant: "destructive",
      });
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

      {/* Budgets Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full table-auto">
            <thead className="bg-gray-50">
              <tr>
                <th 
                  className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('id')}
                >
                  <div className="flex items-center space-x-1">
                    <span>ID</span>
                    {renderSortIcon('id')}
                  </div>
                </th>
                <th 
                  className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('client_name')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Cliente</span>
                    {renderSortIcon('client_name')}
                  </div>
                </th>
                <th 
                  className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 hidden sm:table-cell"
                  onClick={() => handleSort('total_units')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Itens</span>
                    {renderSortIcon('total_units')}
                  </div>
                </th>
                <th 
                  className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('total_value')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Total</span>
                    {renderSortIcon('total_value')}
                  </div>
                </th>
                <th 
                  className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 hidden md:table-cell"
                  onClick={() => handleSort('payment_method')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Pagamento</span>
                    {renderSortIcon('payment_method')}
                  </div>
                </th>
                <th 
                  className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 hidden lg:table-cell"
                  onClick={() => handleSort('salesperson')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Vendedor</span>
                    {renderSortIcon('salesperson')}
                  </div>
                </th>
                <th 
                  className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('created_at')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Data</span>
                    {renderSortIcon('created_at')}
                  </div>
                </th>

              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sortedBudgets.map((budget) => (
                <tr key={budget.id} className="hover:bg-gray-50">
                  <td className="px-3 sm:px-6 py-4">
                    <div className="text-sm font-medium text-gray-900 mb-2">{budget.id}</div>
                    <div className="flex space-x-1">
                      <button
                        onClick={() => handleWhatsAppBudget(budget)}
                        className="p-1.5 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                        title="Enviar WhatsApp"
                      >
                        <MessageCircle className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handlePDFBudget(budget)}
                        className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Gerar PDF"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => {
                          setEditingBudget(budget);
                          setShowForm(true);
                        }}
                        className="p-1.5 text-yellow-600 hover:bg-yellow-50 rounded-lg transition-colors"
                        title="Editar"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteBudget(budget)}
                        className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Excluir"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                  <td className="px-3 sm:px-6 py-4">
                    <div className="text-sm font-medium text-blue-600">{budget.client_name}</div>
                    <div className="text-xs text-gray-500 sm:hidden">
                      {budget.total_units} itens • {PAYMENT_METHODS[budget.payment_method]}
                    </div>
                    <div className="text-xs text-gray-500 md:hidden lg:inline lg:hidden">
                      {budget.salesperson}
                    </div>
                  </td>
                  <td className="px-3 sm:px-6 py-4 whitespace-nowrap text-sm text-gray-900 hidden sm:table-cell">
                    <div className="flex items-center">
                      <Package className="w-4 h-4 text-blue-600 mr-1" />
                      {budget.total_units}
                    </div>
                  </td>
                  <td className="px-3 sm:px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-semibold text-green-900">R$ {budget.total_value.toFixed(2)}</div>
                    <div className="text-xs text-gray-500">
                      {budget.total_area_m2.toFixed(1)}m² • {budget.total_linear_meters.toFixed(1)}m lin.
                    </div>
                  </td>
                  <td className="px-3 sm:px-6 py-4 whitespace-nowrap text-sm text-gray-900 hidden md:table-cell">
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {PAYMENT_METHODS[budget.payment_method]}
                    </span>
                  </td>
                  <td className="px-3 sm:px-6 py-4 whitespace-nowrap text-sm text-gray-900 hidden lg:table-cell">
                    {budget.salesperson}
                  </td>
                  <td className="px-3 sm:px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div>{new Date(budget.created_at).toLocaleDateString('pt-BR')}</div>
                    <div className="text-xs text-gray-500">
                      {new Date(budget.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </td>

                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
          preSelectedClient={preSelectedClient}
          onSave={handleSaveBudget}
          onCancel={() => {
            setShowForm(false);
            setEditingBudget(null);
          }}
        />
      )}


    </div>
  );
}