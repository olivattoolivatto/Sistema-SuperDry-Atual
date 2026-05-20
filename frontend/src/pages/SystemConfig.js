import React, { useState, useEffect } from 'react';
import { Save, MapPin, Building2, Shield, Users, ChevronDown, ChevronRight, Plus, Edit2, Trash2, Loader2, X, KeyRound } from 'lucide-react';
import { systemConfigApi, placesApi, usersApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from '../hooks/use-toast';
import MiniMap from '../components/MiniMap';

const formatCNPJ = (value) => {
  const numbers = value.replace(/\D/g, '');
  return numbers.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
};

const formatCEP = (value) => {
  const numbers = value.replace(/\D/g, '');
  return numbers.replace(/(\d{5})(\d{3})/, '$1-$2');
};

const formatPhone = (value) => {
  const numbers = value.replace(/\D/g, '');
  if (numbers.length === 11) {
    return numbers.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
  } else if (numbers.length === 10) {
    return numbers.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
  }
  return numbers;
};

// ── Wrapper retrátil genérico ─────────────────────────────────────────────────
function CollapsibleSection({ label, icon, expanded, onToggle, children }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors" onClick={onToggle}>
        <div className="flex items-center gap-2">
          <span className="text-base">{icon}</span>
          <h2 className="text-sm font-semibold text-gray-900">{label}</h2>
        </div>
        {expanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
      </div>
      {expanded && <div className="border-t border-gray-100 p-4">{children}</div>}
    </div>
  );
}

// ── Módulos disponíveis para permissão ────────────────────────────────────────
const ALL_MODULES = [
  { path: '/',               label: 'Painel' },
  { path: '/clients',        label: 'Clientes' },
  { path: '/budgets',        label: 'Orçamentos' },
  { path: '/routes',         label: 'Rotas' },
  { path: '/routes-geo',     label: 'Rotas Geoapify' },
  { path: '/agenda',         label: 'Agenda' },
  { path: '/whatsapp',       label: 'WhatsApp' },
  { path: '/technician',     label: 'Execução e Lavagem' },
  { path: '/financial',      label: 'Financeiro' },
  { path: '/finance-manager',label: 'Ger. Financeiro' },
  { path: '/reports',        label: 'Relatórios' },
  { path: '/tickets',        label: 'Chamados' },
  { path: '/catalog',        label: 'Catálogo' },
  { path: '/budget-config',  label: 'Config. Orçamento' },
  { path: '/system-config',  label: 'Config. Sistema' },
];

const ROLE_DEFAULT_MODULES = {
  ADMIN:      ALL_MODULES.map(m => m.path),
  ATENDENTE:  ['/', '/clients', '/budgets', '/routes', '/routes-geo', '/agenda', '/whatsapp'],
  TECNICO:    ['/', '/agenda', '/technician'],
  FINANCEIRO: ['/', '/financial', '/finance-manager', '/reports'],
  MANUTENCAO: ['/', '/tickets'],
};

export const SystemConfig = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [addressSuggestions, setAddressSuggestions] = useState([]);
  
  // Estados para controlar expansão das seções
  const [expandedSections, setExpandedSections] = useState({
    company: false,
    contact: false,
    dataPolicy: false,
    logo: false,
    payment: false,
    users: false,
  });

  useEffect(() => {
    loadConfig();
  }, []);

  const toggleSection = (sectionName) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionName]: !prev[sectionName]
    }));
  };

  const loadConfig = async () => {
    try {
      const response = await systemConfigApi.get();
      setConfig(response.data);
    } catch (error) {
      console.error('Erro ao carregar configurações:', error);
      toast({
        title: "Erro!",
        description: "Erro ao carregar configurações. Tente novamente.",
        variant: "destructive",
      });
    }
    setLoading(false);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await systemConfigApi.update(config);
      setConfig(response.data);
      toast({
        title: "Sucesso!",
        description: "Configurações salvas com sucesso!",
        variant: "default",
      });
    } catch (error) {
      console.error('Erro ao salvar:', error);
      toast({
        title: "Erro!",
        description: "Erro ao salvar configurações. Tente novamente.",
        variant: "destructive",
      });
    }
    setSaving(false);
  };

  const handleChange = (field, value) => {
    setConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleAddressChange = async (e) => {
    const value = e.target.value;
    handleChange('address_full', value);

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
      
      let fullAddress = suggestion.formatted_address || suggestion.description;
      let neighborhood = suggestion.neighborhood || '';
      let city = suggestion.city || '';
      let state = suggestion.state || '';
      let latitude = null;
      let longitude = null;
      
      // First priority: Extract location data from search result
      if (suggestion.geometry && suggestion.geometry.location) {
        latitude = suggestion.geometry.location.lat;
        longitude = suggestion.geometry.location.lng;
        console.log('📍 Coordenadas obtidas do resultado da busca:', { latitude, longitude });
      }
      
      // If we don't have coordinates or address components, try to get details
      if ((!latitude || !longitude || !neighborhood || !city || !state) && suggestion.place_id) {
        try {
          console.log('🔍 Buscando detalhes adicionais via place_id...');
          const response = await placesApi.getDetails(suggestion.place_id);
          const details = response.data.details.result;
          console.log('Detalhes obtidos da API:', details);
          
          // Update coordinates if not already available
          if (!latitude || !longitude) {
            latitude = details.geometry?.location?.lat || latitude;
            longitude = details.geometry?.location?.lng || longitude;
            console.log('📍 Coordenadas obtidas dos detalhes:', { latitude, longitude });
          }
          
          // Extract address components if not already available
          if (details && details.address_components && (!neighborhood || !city || !state)) {
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

            neighborhood = neighborhood || getComponent(['sublocality_level_1', 'sublocality']) ||
                          getComponent(['neighborhood']) ||
                          getComponent(['administrative_area_level_4']) ||
                          getComponent(['administrative_area_level_3']);
            
            city = city || getComponent(['locality']) ||
                  getComponent(['administrative_area_level_2']) ||
                  getComponent(['sublocality']);
            
            state = state || getComponent(['administrative_area_level_1'], false);
            
            fullAddress = details.formatted_address || fullAddress;
          }
        } catch (detailsError) {
          console.log('⚠️ Erro ao obter detalhes da API, usando dados disponíveis:', detailsError);
        }
      }
      
      // Enhanced fallback extraction from formatted_address
      if (!neighborhood || !city || !state) {
        console.log('Usando fallback parsing para:', fullAddress);
        
        // Parse "Rua das Flôres, 123 - Dr. Fábio Leite, Cuiabá - MT, 78087, Brasil"
        const parts = fullAddress.split(',').map(part => part.trim());
        
        if (parts.length >= 3) {
          // Try to extract state from last meaningful part
          for (let i = parts.length - 1; i >= 0; i--) {
            const part = parts[i];
            if (part.includes(' - ') && !state) {
              const dashParts = part.split(' - ');
              if (dashParts.length >= 2) {
                const lastDash = dashParts[dashParts.length - 1].trim();
                if (lastDash.length === 2 && /^[A-Z]{2}$/.test(lastDash)) {
                  state = lastDash;
                  // City is usually before the state
                  if (dashParts.length >= 2) {
                    city = dashParts[dashParts.length - 2].trim();
                  }
                }
              }
            }
          }
          
          // Try to extract neighborhood from earlier parts
          if (!neighborhood && parts.length >= 2) {
            const secondPart = parts[1];
            if (secondPart.includes(' - ')) {
              const dashParts = secondPart.split(' - ');
              if (dashParts.length >= 2) {
                neighborhood = dashParts[dashParts.length - 1].trim();
              }
            } else {
              neighborhood = parts[1];
            }
          }
          
          // If city not found yet, try from earlier parts
          if (!city && parts.length >= 3) {
            const thirdPart = parts[2];
            if (thirdPart.includes(' - ')) {
              const dashParts = thirdPart.split(' - ');
              city = dashParts[0].trim();
            }
          }
        }
        
        // Additional fallback for Brazilian addresses
        if (!city && fullAddress.includes('Cuiabá')) {
          city = 'Cuiabá';
        }
        if (!state && fullAddress.includes(' MT')) {
          state = 'MT';
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

      // Update config with all fields
      setConfig(prev => ({
        ...prev,
        address_full: fullAddress,
        neighborhood: neighborhood || '',
        city: city || '',
        state: state || '',
        latitude: latitude,
        longitude: longitude
      }));
      
      // Clear suggestions
      setAddressSuggestions([]);
      
      // Show success message
      if (neighborhood || city || state) {
        toast({
          title: "Endereço selecionado!",
          description: `Campos preenchidos automaticamente: ${[neighborhood, city, state].filter(Boolean).join(', ')}`,
          variant: "default",
        });
      }
      
      console.log('✅ Endereço selecionado e campos preenchidos automaticamente');
      
    } catch (error) {
      console.error('Erro ao selecionar endereço:', error);
      
      // Fallback - at least save the main address
      setConfig(prev => ({
        ...prev,
        address_full: suggestion.formatted_address || suggestion.description
      }));
      setAddressSuggestions([]);
      console.log('⚠️ Usando fallback - apenas endereço principal preenchido');
    }
  };

  const handleAddressSearch = async (address) => {
    // Function kept for compatibility but logic moved to handleAddressChange
    handleChange('address_full', address);
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            {[1,2,3,4].map(i => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Configurações do Sistema</h1>
        <p className="text-gray-600 mt-2">
          Configure os dados da empresa e políticas do sistema
        </p>
      </div>

      <div className="space-y-2">
        {/* Company Information */}
        <div className="bg-white rounded-lg border border-gray-200">
          <div
            className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => toggleSection('company')}
          >
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-semibold text-gray-900">Dados da Empresa</h2>
            </div>
            {expandedSections.company ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
          </div>

          {expandedSections.company && (
            <div className="px-4 pb-4 border-t border-gray-100">
              <div className="pt-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nome da Empresa
              </label>
              <input
                type="text"
                value={config?.company_name || ''}
                onChange={(e) => handleChange('company_name', e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Nome da empresa"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Endereço Completo
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={config?.address_full || ''}
                  onChange={handleAddressChange}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Digite o endereço para busca automática"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Este endereço será usado como ponto de partida e chegada das rotas
                </p>
                
                {/* Address Suggestions */}
                {addressSuggestions.length > 0 && (
                  <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-80 overflow-y-auto">
                    {addressSuggestions.map((suggestion, index) => (
                      <button
                        key={`${suggestion.place_id}-${index}`}
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          handleAddressSelect(suggestion);
                        }}
                        className="w-full px-4 py-3 text-left hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors focus:outline-none focus:bg-blue-50"
                      >
                        <div className="font-medium text-gray-900 text-sm">
                          {suggestion.structured_formatting?.main_text || suggestion.description?.split(',')[0]}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {suggestion.structured_formatting?.secondary_text || suggestion.formatted_address || suggestion.description}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Mini Map for Company Location */}
            {config?.latitude && config?.longitude && (
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Localização da Empresa
                </label>
                <div className="border border-gray-200 rounded-lg p-2">
                  <MiniMap
                    latitude={config.latitude}
                    longitude={config.longitude}
                    title={config.company_name || "Empresa"}
                    height="200px"
                    className="w-full"
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  📍 Lat: {config.latitude.toFixed(6)}, Lng: {config.longitude.toFixed(6)} • Clique para abrir no Google Maps
                </p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Complemento
              </label>
              <input
                type="text"
                value={config?.address_complement || ''}
                onChange={(e) => handleChange('address_complement', e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Sala, andar, etc."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                CNPJ
              </label>
              <input
                type="text"
                value={config?.cnpj || ''}
                onChange={(e) => handleChange('cnpj', formatCNPJ(e.target.value))}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="00.000.000/0000-00"
                maxLength={18}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                CEP
              </label>
              <input
                type="text"
                value={config?.cep || ''}
                onChange={(e) => handleChange('cep', formatCEP(e.target.value))}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="00000-000"
                maxLength={9}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Bairro
              </label>
              <input
                type="text"
                value={config?.neighborhood || ''}
                onChange={(e) => handleChange('neighborhood', e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Preenchido automaticamente"
              />
              <p className="text-xs text-gray-500 mt-1">
                Preenchido automaticamente ao selecionar endereço
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Cidade
              </label>
              <input
                type="text"
                value={config?.city || ''}
                onChange={(e) => handleChange('city', e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Preenchido automaticamente"
              />
              <p className="text-xs text-gray-500 mt-1">
                Preenchido automaticamente ao selecionar endereço
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Estado
              </label>
              <input
                type="text"
                value={config?.state || ''}
                onChange={(e) => handleChange('state', e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="SP"
                maxLength={2}
              />
              <p className="text-xs text-gray-500 mt-1">
                Preenchido automaticamente ao selecionar endereço
              </p>
            </div>
          </div>
              </div>
            </div>
          )}
        </div>

        {/* Contact Information */}
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => toggleSection('contact')}>
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-green-600" />
              <h2 className="text-sm font-semibold text-gray-900">Informações de Contato</h2>
            </div>
            {expandedSections.contact ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
          </div>
          {expandedSections.contact && (
          <div className="px-4 pb-4 border-t border-gray-100 pt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Telefone
              </label>
              <input
                type="text"
                value={config?.phone || ''}
                onChange={(e) => handleChange('phone', formatPhone(e.target.value))}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="(00) 0000-0000"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                WhatsApp
              </label>
              <input
                type="text"
                value={config?.whatsapp || ''}
                onChange={(e) => handleChange('whatsapp', formatPhone(e.target.value))}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="(00) 00000-0000"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email
              </label>
              <input
                type="email"
                value={config?.email || ''}
                onChange={(e) => handleChange('email', e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="contato@empresa.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Website
              </label>
              <input
                type="url"
                value={config?.website || ''}
                onChange={(e) => handleChange('website', e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="https://www.empresa.com"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Instagram
              </label>
              <div className="relative">
                <span className="absolute left-3 top-3 text-gray-500">@</span>
                <input
                  type="text"
                  value={config?.instagram || ''}
                  onChange={(e) => handleChange('instagram', e.target.value.replace('@', ''))}
                  className="w-full p-3 pl-8 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="nomedousuario"
                />
              </div>
            </div>
          </div>
          </div>
          )}
        </div>

        {/* Data Retention Policy */}
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => toggleSection('dataPolicy')}>
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-purple-600" />
              <h2 className="text-sm font-semibold text-gray-900">Política de Retenção (LGPD)</h2>
            </div>
            {expandedSections.dataPolicy ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
          </div>
          {expandedSections.dataPolicy && (
          <div className="px-4 pb-4 border-t border-gray-100 pt-4">
          <div className="space-y-4">
            <p className="text-xs text-yellow-700 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              Configure os prazos de guarda de dados pessoais conforme a LGPD.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Fotos (anos)
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={config?.retention_photos_years || 2}
                  onChange={(e) => handleChange('retention_photos_years', parseInt(e.target.value))}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Assinaturas Digitais (anos)
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={config?.retention_signatures_years || 2}
                  onChange={(e) => handleChange('retention_signatures_years', parseInt(e.target.value))}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Documentos (anos)
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={config?.retention_documents_years || 2}
                  onChange={(e) => handleChange('retention_documents_years', parseInt(e.target.value))}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Ação após o prazo
              </label>
              <select
                value={config?.retention_action || 'ANONYMIZE'}
                onChange={(e) => handleChange('retention_action', e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="ANONYMIZE">Anonimizar dados (manter estatísticas)</option>
                <option value="DELETE">Excluir definitivamente</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Anonimização remove dados pessoais mas mantém histórico estatístico
              </p>
            </div>
          </div>
          </div>
          )}
        </div>

        {/* Logo da Empresa */}
        <CollapsibleSection
          sectionKey="logo" label="Logo da Empresa" icon="🖼️"
          expanded={expandedSections.logo} onToggle={() => toggleSection('logo')}>
          <LogoManager />
        </CollapsibleSection>

        {/* Formas de Pagamento */}
        <CollapsibleSection
          sectionKey="payment" label="Formas de Pagamento" icon="💳"
          expanded={expandedSections.payment} onToggle={() => toggleSection('payment')}>
          <PaymentMethodsManager config={config} setConfig={setConfig} inline />
        </CollapsibleSection>

        {/* Gestão de Usuários */}
        <UsersManager
          expanded={expandedSections.users}
          onToggle={() => toggleSection('users')}
        />

        {/* Save Button */}
        <div className="flex justify-end pt-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium transition-colors"
          >
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Salvando...' : 'Salvar Configurações'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// Logo Manager
// ============================================================
function LogoManager() {
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
  const [status, setStatus] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [flash, setFlash] = useState('');
  const inputRef = React.useRef();

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/system-config/logo`)
      .then(r => r.json())
      .then(setStatus)
      .catch(() => {});
  }, []);

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const token = localStorage.getItem('superdry_token');
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${BACKEND_URL}/api/system-config/logo`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (!r.ok) throw new Error((await r.json()).detail);
      setFlash('Logo atualizada com sucesso!');
      setStatus(s => ({ ...s, has_custom_logo: true, logo_url: `/api/system-config/logo/file` }));
      setTimeout(() => setFlash(''), 3000);
    } catch (err) {
      setFlash('Erro: ' + err.message);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  return (
    <div>
      <p className="text-sm text-gray-500 mb-4">Usada no cabeçalho do PDF de orçamentos.</p>
      {flash && <div className="mb-3 text-sm bg-green-100 text-green-800 px-3 py-2 rounded">{flash}</div>}
      <div className="flex items-center gap-6">
        <div className="w-32 h-24 border border-gray-200 rounded-lg overflow-hidden bg-gray-50 flex items-center justify-center">
          {status?.has_custom_logo || status?.has_fallback_logo ? (
            <img
              src={`${BACKEND_URL}/api/system-config/logo/file?t=${Date.now()}`}
              alt="Logo atual"
              className="object-contain w-full h-full p-1"
            />
          ) : (
            <span className="text-xs text-gray-400">Sem logo</span>
          )}
        </div>
        <div>
          <input ref={inputRef} type="file" accept="image/*" onChange={handleFile} className="hidden" />
          <button
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {uploading ? 'Enviando…' : status?.has_custom_logo ? 'Trocar Logo' : 'Enviar Logo'}
          </button>
          <p className="text-xs text-gray-400 mt-2">PNG recomendado · máx. 2 MB</p>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Payment Methods Manager
// ============================================================
function PaymentMethodsManager({ config, setConfig, inline = false }) {
  const [newLabel, setNewLabel] = useState('');
  const [newValue, setNewValue] = useState('');
  const [editIdx, setEditIdx] = useState(null);
  const [editLabel, setEditLabel] = useState('');

  const methods = config?.payment_methods || [];

  const slugify = (s) => s.toUpperCase().replace(/\s+/g, '_').replace(/[^A-Z0-9_]/g, '');

  const add = () => {
    const label = newLabel.trim();
    if (!label) return;
    const value = newValue.trim() || slugify(label);
    if (methods.find(m => m.value === value)) { alert('Valor/chave já existe.'); return; }
    setConfig(prev => ({ ...prev, payment_methods: [...methods, { value, label }] }));
    setNewLabel(''); setNewValue('');
  };

  const remove = (idx) => {
    setConfig(prev => ({ ...prev, payment_methods: methods.filter((_, i) => i !== idx) }));
  };

  const startEdit = (idx) => { setEditIdx(idx); setEditLabel(methods[idx].label); };

  const saveEdit = () => {
    const updated = methods.map((m, i) => i === editIdx ? { ...m, label: editLabel.trim() || m.label } : m);
    setConfig(prev => ({ ...prev, payment_methods: updated }));
    setEditIdx(null);
  };

  return (
    <div>
      <p className="text-sm text-gray-500 mb-3">Gerencie as opções disponíveis em orçamentos e atendimentos.</p>

      <div className="space-y-2 mb-4">
        {methods.map((m, idx) => (
          <div key={m.value} className="flex items-center gap-2 p-2.5 bg-gray-50 rounded-lg border border-gray-200">
            {editIdx === idx ? (
              <>
                <input
                  className="flex-1 px-2 py-1 border border-blue-400 rounded text-sm"
                  value={editLabel}
                  onChange={e => setEditLabel(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && saveEdit()}
                  autoFocus
                />
                <button onClick={saveEdit} className="text-xs px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700">OK</button>
                <button onClick={() => setEditIdx(null)} className="text-xs px-2 py-1 text-gray-500 hover:text-gray-700"><X className="w-3.5 h-3.5" /></button>
              </>
            ) : (
              <>
                <span className="flex-1 text-sm font-medium text-gray-900">{m.label}</span>
                <span className="text-xs text-gray-400 font-mono bg-gray-100 px-2 py-0.5 rounded">{m.value}</span>
                <button onClick={() => startEdit(idx)} className="p-1 text-gray-400 hover:text-blue-600"><Edit2 className="w-3.5 h-3.5" /></button>
                <button onClick={() => remove(idx)} className="p-1 text-gray-400 hover:text-rose-600"><Trash2 className="w-3.5 h-3.5" /></button>
              </>
            )}
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <input
          placeholder="Nome (ex: PIX Diego)"
          value={newLabel}
          onChange={e => setNewLabel(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
        />
        <input
          placeholder="Chave opcional (ex: PIX_DIEGO)"
          value={newValue}
          onChange={e => setNewValue(e.target.value)}
          className="w-44 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
        />
        <button onClick={add} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 flex items-center gap-1">
          <Plus className="w-4 h-4" /> Adicionar
        </button>
      </div>
      <p className="text-xs text-gray-400 mt-2">Clique em "Salvar Configurações" para aplicar as alterações.</p>
    </div>
  );
}

// ============================================================
// Users Manager (admin only)
// ============================================================
const ROLE_LABELS = {
  ADMIN: 'Administrador',
  TECNICO: 'Técnico',
  ATENDENTE: 'Atendente',
  FINANCEIRO: 'Financeiro',
  MANUTENCAO: 'Manutenção',
};

function UsersManager({ expanded, onToggle }) {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: '', display_name: '', email: '', password: '', role: 'ATENDENTE', is_active: true, allowed_modules: null });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [useCustomModules, setUseCustomModules] = useState(false);
  const [selectedModules, setSelectedModules] = useState([]);

  const isAdmin = currentUser?.role === 'ADMIN';

  const load = async () => {
    if (!isAdmin) return;
    try {
      setLoading(true);
      const r = await usersApi.list();
      setUsers(r.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { if (expanded && isAdmin) load(); }, [expanded, isAdmin]);

  const openCreate = () => {
    setEditing(null);
    const defaultRole = 'ATENDENTE';
    setForm({ name: '', display_name: '', email: '', password: '', role: defaultRole, is_active: true, allowed_modules: null });
    setUseCustomModules(false);
    setSelectedModules(ROLE_DEFAULT_MODULES[defaultRole] || []);
    setError('');
    setModalOpen(true);
  };

  const openEdit = (u) => {
    setEditing(u);
    const hasCustom = !!(u.allowed_modules && u.allowed_modules.length > 0);
    setUseCustomModules(hasCustom);
    setSelectedModules(hasCustom ? u.allowed_modules : (ROLE_DEFAULT_MODULES[u.role] || []));
    setForm({ name: u.name, display_name: u.display_name || '', email: u.email, password: '', role: u.role, is_active: u.is_active, allowed_modules: u.allowed_modules });
    setError('');
    setModalOpen(true);
  };

  const handleRoleChange = (role) => {
    setForm(f => ({ ...f, role }));
    if (!useCustomModules) setSelectedModules(ROLE_DEFAULT_MODULES[role] || []);
  };

  const toggleModule = (path) =>
    setSelectedModules(prev => prev.includes(path) ? prev.filter(p => p !== path) : [...prev, path]);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!form.name.trim() || !form.email.trim()) { setError('Usuário e email são obrigatórios.'); return; }
    if (!editing && !form.password) { setError('Senha obrigatória ao criar usuário.'); return; }
    try {
      setSaving(true);
      const payload = {
        ...form,
        allowed_modules: useCustomModules ? selectedModules : null,
      };
      if (!payload.password) delete payload.password;
      if (editing) {
        await usersApi.update(editing.id, payload);
      } else {
        await usersApi.create(payload);
      }
      setModalOpen(false);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar usuário.');
    } finally { setSaving(false); }
  };

  const onDelete = async (u) => {
    if (!window.confirm(`Excluir usuário ${u.name}?`)) return;
    try { await usersApi.delete(u.id); await load(); }
    catch (err) { alert(err.response?.data?.detail || 'Erro ao excluir.'); }
  };

  if (!isAdmin) return null;

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors" onClick={onToggle}>
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-indigo-600" />
          <h2 className="text-sm font-semibold text-gray-900">Usuários e Permissões</h2>
          <span className="text-[10px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">{users.length}</span>
        </div>
        {expanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
      </div>

      {expanded && (
        <div className="border-t border-gray-100 p-4 space-y-3">
          <div className="flex justify-end">
            <button onClick={openCreate}
              className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-xs font-medium inline-flex items-center gap-1">
              <Plus className="w-3.5 h-3.5" /> Novo Usuário
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center py-4"><Loader2 className="w-5 h-5 animate-spin text-indigo-600" /></div>
          ) : (
            <div className="space-y-2">
              {users.map(u => (
                <div key={u.id} className="flex items-center gap-2 p-2.5 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900 truncate">{u.name}</div>
                    <div className="text-xs text-gray-500 truncate">{u.email}</div>
                    <div className="flex items-center gap-1 mt-0.5">
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-indigo-50 text-indigo-700 font-medium">{ROLE_LABELS[u.role] || u.role}</span>
                      {u.allowed_modules && <span className="text-[10px] text-orange-600 bg-orange-50 px-1.5 py-0.5 rounded">Permissões custom</span>}
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${u.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                        {u.is_active ? 'Ativo' : 'Inativo'}
                      </span>
                    </div>
                  </div>
                  <button onClick={() => openEdit(u)} className="p-1.5 text-amber-600 hover:bg-amber-50 rounded shrink-0"><Edit2 className="w-3.5 h-3.5" /></button>
                  <button onClick={() => onDelete(u)} className="p-1.5 text-rose-600 hover:bg-rose-50 rounded shrink-0"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              ))}
              {users.length === 0 && <p className="text-center text-gray-400 text-sm py-4">Nenhum usuário cadastrado.</p>}
            </div>
          )}
        </div>
      )}

      {modalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <form onSubmit={onSubmit} className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">{editing ? 'Editar Usuário' : 'Novo Usuário'}</h3>
              <button type="button" onClick={() => setModalOpen(false)} className="p-1.5 hover:bg-gray-100 rounded-lg"><X className="w-5 h-5" /></button>
            </div>

            {/* Dados básicos */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Usuário * <span className="text-gray-400 font-normal">(apelido/login)</span>
                </label>
                <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                  placeholder="ex: diego"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Nome do Usuário <span className="text-gray-400 font-normal">(aparece em documentos)</span>
                </label>
                <input value={form.display_name} onChange={e => setForm({ ...form, display_name: e.target.value })}
                  placeholder="ex: Diego Olivatto"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Email *</label>
                <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Perfil base *</label>
                <select value={form.role} onChange={e => handleRoleChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500">
                  {Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Senha {editing && <span className="text-gray-400">(deixe em branco para manter)</span>}
                </label>
                <div className="relative">
                  <KeyRound className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })}
                    className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500" />
                </div>
              </div>
            </div>

            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />
              Usuário ativo
            </label>

            {/* Permissões de módulos */}
            <div className="border border-gray-200 rounded-xl p-3 space-y-3">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-800 cursor-pointer">
                <input type="checkbox" checked={useCustomModules}
                  onChange={e => {
                    setUseCustomModules(e.target.checked);
                    if (!e.target.checked) setSelectedModules(ROLE_DEFAULT_MODULES[form.role] || []);
                  }} />
                Personalizar acesso por módulo
              </label>

              {useCustomModules && (
                <div>
                  <p className="text-xs text-gray-500 mb-2">Marque os módulos que este usuário pode acessar:</p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
                    {ALL_MODULES.map(m => (
                      <label key={m.path} className="flex items-center gap-1.5 text-xs text-gray-700 cursor-pointer select-none">
                        <input type="checkbox"
                          checked={selectedModules.includes(m.path)}
                          onChange={() => toggleModule(m.path)}
                          className="h-3.5 w-3.5 text-indigo-600" />
                        {m.label}
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {!useCustomModules && (
                <p className="text-xs text-gray-400">
                  Módulos padrão do perfil <strong>{ROLE_LABELS[form.role]}</strong>:{' '}
                  {(ROLE_DEFAULT_MODULES[form.role] || []).map(p => ALL_MODULES.find(m => m.path === p)?.label).filter(Boolean).join(', ')}
                </p>
              )}
            </div>

            {error && <div className="text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg px-3 py-2">{error}</div>}

            <div className="flex gap-2">
              <button type="button" onClick={() => setModalOpen(false)}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-medium">
                Cancelar
              </button>
              <button type="submit" disabled={saving}
                className="flex-1 px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-60">
                {saving && <Loader2 className="w-4 h-4 animate-spin" />} Salvar
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}