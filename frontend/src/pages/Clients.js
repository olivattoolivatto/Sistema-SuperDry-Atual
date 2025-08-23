import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  Search, 
  Edit2, 
  Trash2, 
  History, 
  MessageCircle,
  Phone,
  MapPin,
  Users,
  FileText
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { clientsApi, placesApi } from '../services/api';

const ClientCard = ({ client, onEdit, onDelete, onHistory, onNewBudget }) => (
  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
    <div className="flex items-start justify-between mb-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">{client.name}</h3>
        <p className="text-sm text-gray-500 font-mono">{client.id}</p>
      </div>
      <div className="flex space-x-2">
        <button
          onClick={() => onHistory(client)}
          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          title="Histórico"
        >
          <History className="w-4 h-4" />
        </button>
        <button
          onClick={() => onEdit(client)}
          className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg transition-colors"
          title="Editar"
        >
          <Edit2 className="w-4 h-4" />
        </button>
        <button
          onClick={() => onDelete(client)}
          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          title="Excluir"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>

    <div className="space-y-2 text-sm">
      <div className="flex items-center text-gray-600">
        <Phone className="w-4 h-4 mr-2" />
        <span>{client.phone_primary}</span>
        {client.phone_primary && (
          <a
            href={`https://wa.me/55${client.phone_primary.replace(/\D/g, '')}`}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-2 p-1 text-green-600 hover:bg-green-50 rounded"
            title="WhatsApp"
          >
            <MessageCircle className="w-4 h-4" />
          </a>
        )}
      </div>
      
      {client.email && (
        <div className="flex items-center text-gray-600">
          <span className="w-4 h-4 mr-2">@</span>
          <span>{client.email}</span>
        </div>
      )}
      
      <div className="flex items-start text-gray-600">
        <MapPin className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
        <div>
          <p>{client.address.full_address}</p>
          {client.address.complement && (
            <p className="text-xs text-gray-500">{client.address.complement}</p>
          )}
          <p className="text-xs text-gray-500">
            {client.address.neighborhood}, {client.address.city} - {client.address.state}
          </p>
        </div>
      </div>
    </div>

    <div className="flex space-x-2 mt-4 pt-4 border-t border-gray-100">
      <button
        onClick={() => onHistory(client)}
        className="flex-1 flex items-center justify-center px-3 py-2 text-sm bg-blue-50 text-blue-700 hover:bg-blue-100 rounded-lg transition-colors"
      >
        <History className="w-4 h-4 mr-1" />
        Histórico
      </button>
      <button
        onClick={() => onNewBudget(client)}
        className="flex-1 flex items-center justify-center px-3 py-2 text-sm bg-green-50 text-green-700 hover:bg-green-100 rounded-lg transition-colors"
      >
        <FileText className="w-4 h-4 mr-1" />
        Novo Orçamento
      </button>
    </div>
  </div>
);

const ClientForm = ({ client, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    name: '',
    phone_primary: '',
    phone_alternative: '',
    email: '',
    cpf_cnpj: '',
    instagram: '',
    address: {
      full_address: '',
      complement: '',
      neighborhood: '',
      city: '',
      state: '',
      latitude: null,
      longitude: null
    }
  });
  const [addressSuggestions, setAddressSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (client) {
      setFormData(client);
    }
  }, [client]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleAddressChange = async (e) => {
    const value = e.target.value;
    setFormData(prev => ({
      ...prev,
      address: { ...prev.address, full_address: value }
    }));

    if (value.length > 2) {
      try {
        console.log('Buscando endereço:', value);
        const response = await placesApi.search(value);
        console.log('Resultados encontrados:', response.data.results);
        setAddressSuggestions(response.data.results || []);
      } catch (error) {
        console.error('Erro ao buscar endereços:', error);
        setAddressSuggestions([]);
      }
    } else {
      setAddressSuggestions([]);
    }
  };

  const handleAddressSelect = async (suggestion) => {
    try {
      console.log('Selecionando endereço:', suggestion);
      
      // First try to get details from API if available
      let neighborhood = '';
      let city = '';
      let state = '';
      let latitude = null;
      let longitude = null;
      let fullAddress = suggestion.description || suggestion.structured_formatting?.main_text || '';
      
      try {
        const response = await placesApi.getDetails(suggestion.place_id);
        const details = response.data.details.result;
        console.log('Detalhes obtidos da API:', details);
        
        if (details && details.address_components) {
          const addressComponents = details.address_components;
          console.log('Componentes do endereço:', addressComponents);
          
          // Extract address components with multiple fallbacks
          const getComponent = (types, preferLongName = true) => {
            const component = addressComponents.find(c => 
              types.some(type => c.types.includes(type))
            );
            if (!component) return '';
            return preferLongName ? component.long_name : component.short_name;
          };

          neighborhood = getComponent(['sublocality_level_1', 'sublocality']) ||
                        getComponent(['neighborhood']) ||
                        getComponent(['administrative_area_level_4']) ||
                        getComponent(['administrative_area_level_3']);
          
          city = getComponent(['locality']) ||
                getComponent(['administrative_area_level_2']) ||
                getComponent(['sublocality']);
          
          state = getComponent(['administrative_area_level_1'], false);
          
          latitude = details.geometry?.location?.lat || null;
          longitude = details.geometry?.location?.lng || null;
          fullAddress = details.formatted_address || fullAddress;
        }
      } catch (detailsError) {
        console.log('Erro ao obter detalhes da API, usando extração local:', detailsError);
        
        // Fallback: Extract from description text
        const description = suggestion.description || '';
        const parts = description.split(',').map(part => part.trim());
        
        if (parts.length >= 3) {
          // Format: "Rua Nome da Rua, número - Bairro, Cidade - Estado, CEP, País"
          const lastPart = parts[parts.length - 1]; // "Brasil"
          const secondLastPart = parts[parts.length - 2]; // "CEP" or "Estado"
          const thirdLastPart = parts[parts.length - 3]; // "Cidade - Estado"
          
          // Extract state (usually 2 letters after dash)
          if (thirdLastPart && thirdLastPart.includes(' - ')) {
            const stateParts = thirdLastPart.split(' - ');
            if (stateParts.length >= 2) {
              city = stateParts[0];
              state = stateParts[1];
            }
          } else if (secondLastPart && secondLastPart.length <= 3) {
            state = secondLastPart;
            city = thirdLastPart;
          }
          
          // Extract neighborhood correctly from second part after dash
          if (parts.length >= 2) {
            const addressPart = parts[1]; // "número - Bairro"
            if (addressPart && addressPart.includes(' - ')) {
              // Split by dash and take the part after it (Bairro)
              const addressSplit = addressPart.split(' - ');
              if (addressSplit.length >= 2) {
                neighborhood = addressSplit[1]; // Take the neighborhood part after the dash
              }
            } else {
              // If no dash, the whole second part might be the neighborhood
              neighborhood = addressPart;
            }
          }
        }
      }

      console.log('Componentes extraídos:', { 
        neighborhood, 
        city, 
        state,
        latitude,
        longitude,
        fullAddress
      });

      // Update form data
      const newFormData = {
        ...formData,
        address: {
          ...formData.address,
          full_address: fullAddress,
          neighborhood: neighborhood || '',
          city: city || '',
          state: state || '',
          latitude: latitude,
          longitude: longitude
        }
      };

      console.log('Atualizando formData:', newFormData);
      setFormData(newFormData);
      
      // Limpar sugestões
      setAddressSuggestions([]);
      console.log('✅ Endereço selecionado e campos preenchidos automaticamente');
      
    } catch (error) {
      console.error('Erro geral ao selecionar endereço:', error);
      
      // Final fallback - usar apenas os dados da sugestão
      setFormData(prev => ({
        ...prev,
        address: {
          ...prev.address,
          full_address: suggestion.description || suggestion.structured_formatting?.main_text || '',
          neighborhood: '',
          city: '',
          state: '',
          latitude: null,
          longitude: null
        }
      }));
      setAddressSuggestions([]);
      console.log('⚠️ Usando fallback final - apenas endereço principal preenchido');
    }
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
            {client ? 'Editar Cliente' : 'Novo Cliente'}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nome do Cliente *
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

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Telefone Principal/WhatsApp *
              </label>
              <input
                type="tel"
                name="phone_primary"
                value={formData.phone_primary}
                onChange={handleInputChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="(65) 99999-9999"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Telefone Alternativo
              </label>
              <input
                type="tel"
                name="phone_alternative"
                value={formData.phone_alternative}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="(65) 99999-9999"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                CPF/CNPJ
              </label>
              <input
                type="text"
                name="cpf_cnpj"
                value={formData.cpf_cnpj}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Instagram
              </label>
              <input
                type="text"
                name="instagram"
                value={formData.instagram}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="usuario_instagram"
              />
            </div>
          </div>

          <div className="relative">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Endereço Completo *
            </label>
            <input
              type="text"
              value={formData.address.full_address}
              onChange={handleAddressChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Digite o endereço para buscar..."
            />
            
            {addressSuggestions.length > 0 && (
              <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-80 overflow-y-auto">
                {addressSuggestions.map((suggestion, index) => (
                  <button
                    key={`${suggestion.place_id}-${index}`}
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      console.log('Clicou em:', suggestion);
                      handleAddressSelect(suggestion);
                    }}
                    className="w-full px-3 py-3 text-left hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors cursor-pointer"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-medium text-gray-900 text-sm">
                          {suggestion.structured_formatting?.main_text || suggestion.description}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {suggestion.structured_formatting?.secondary_text || ''}
                        </div>
                      </div>
                      <div className="ml-2 text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded flex-shrink-0">
                        {suggestion.source === 'places' ? 'Local' : 'Endereço'}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Complemento
            </label>
            <input
              type="text"
              value={formData.address.complement}
              onChange={(e) => setFormData(prev => ({
                ...prev,
                address: { ...prev.address, complement: e.target.value }
              }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Apto, Bloco, etc."
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Bairro
              </label>
              <input
                type="text"
                value={formData.address.neighborhood}
                readOnly
                className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cidade
              </label>
              <input
                type="text"
                value={formData.address.city}
                readOnly
                className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Estado
              </label>
              <input
                type="text"
                value={formData.address.state}
                readOnly
                className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
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

export function Clients() {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingClient, setEditingClient] = useState(null);

  useEffect(() => {
    loadClients();
  }, []);

  const loadClients = async () => {
    try {
      setLoading(true);
      const response = await clientsApi.getAll({ search: searchTerm });
      setClients(response.data);
    } catch (error) {
      console.error('Erro ao carregar clientes:', error);
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
        loadClients();
      }
    }, 500);

    return () => clearTimeout(debounced);
  }, [searchTerm]);

  const handleSaveClient = async (clientData) => {
    try {
      if (editingClient) {
        await clientsApi.update(editingClient.id, clientData);
      } else {
        await clientsApi.create(clientData);
      }
      
      setShowForm(false);
      setEditingClient(null);
      loadClients();
    } catch (error) {
      console.error('Erro ao salvar cliente:', error);
      alert('Erro ao salvar cliente. Tente novamente.');
    }
  };

  const handleDeleteClient = async (client) => {
    if (window.confirm(`Tem certeza que deseja excluir o cliente ${client.name}?`)) {
      try {
        await clientsApi.delete(client.id);
        loadClients();
      } catch (error) {
        console.error('Erro ao excluir cliente:', error);
        alert('Erro ao excluir cliente. Tente novamente.');
      }
    }
  };

  const handleHistory = (client) => {
    // TODO: Implementar modal de histórico
    alert(`Histórico do cliente ${client.name} será implementado em breve.`);
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
          <h1 className="text-2xl font-bold text-gray-900">Clientes</h1>
          <p className="text-gray-600">Gerencie os clientes da lavanderia</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5 mr-2" />
          Novo Cliente
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
        <input
          type="text"
          placeholder="Buscar clientes por nome, código ou telefone..."
          value={searchTerm}
          onChange={handleSearch}
          className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* Clients Count */}
      <div className="text-sm text-gray-600">
        {clients.length} cliente{clients.length !== 1 ? 's' : ''} encontrado{clients.length !== 1 ? 's' : ''}
      </div>

      {/* Clients Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {clients.map((client) => (
          <ClientCard
            key={client.id}
            client={client}
            onEdit={(client) => {
              setEditingClient(client);
              setShowForm(true);
            }}
            onDelete={handleDeleteClient}
            onHistory={handleHistory}
          />
        ))}
      </div>

      {clients.length === 0 && (
        <div className="text-center py-12">
          <Users className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhum cliente encontrado</h3>
          <p className="text-gray-500 mb-4">
            {searchTerm ? 'Tente ajustar sua busca' : 'Comece cadastrando seu primeiro cliente'}
          </p>
          {!searchTerm && (
            <button
              onClick={() => setShowForm(true)}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors"
            >
              <Plus className="w-5 h-5 mr-2" />
              Cadastrar Cliente
            </button>
          )}
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <ClientForm
          client={editingClient}
          onSave={handleSaveClient}
          onCancel={() => {
            setShowForm(false);
            setEditingClient(null);
          }}
        />
      )}
    </div>
  );
}