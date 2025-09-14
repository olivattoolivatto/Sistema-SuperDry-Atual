import React, { useState, useEffect } from 'react';
import { Save, MapPin, Building2, Shield, Users, ChevronDown, ChevronRight } from 'lucide-react';
import { systemConfigApi, placesApi } from '../services/api';
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

export const SystemConfig = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [addressSuggestions, setAddressSuggestions] = useState([]);
  
  // Estados para seções retráteis
  const [sectionsExpanded, setSectionsExpanded] = useState({
    company: false,
    contact: false,
    dataPolicy: false,
    futureFeatures: false
  });

  const toggleSection = (section) => {
    setSectionsExpanded(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };
  
  // Estados para controlar expansão das seções
  const [expandedSections, setExpandedSections] = useState({
    company: false,      // Dados da Empresa - fechado por padrão
    contact: false,      // Informações de Contato - fechado por padrão  
    dataPolicy: false,   // Política de Retenção de Dados - fechado por padrão
    futureFeatures: false // Funcionalidades Futuras - fechado por padrão
  });

  useEffect(() => {
    loadConfig();
  }, []);

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

      <div className="space-y-8">
        {/* Company Information - Retrátil */}
        <div className="bg-white rounded-lg border border-gray-200">
          <div 
            className="flex items-center justify-between p-6 cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => toggleSection('company')}
          >
            <div className="flex items-center">
              <Building2 className="w-5 h-5 text-blue-600 mr-2" />
              <h2 className="text-xl font-semibold text-gray-900">Dados da Empresa</h2>
            </div>
            {expandedSections.company ? (
              <ChevronDown className="w-5 h-5 text-gray-500" />
            ) : (
              <ChevronRight className="w-5 h-5 text-gray-500" />
            )}
          </div>

          {expandedSections.company && (
            <div className="px-6 pb-6 border-t border-gray-100">
              <div className="pt-6">
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

        {/* Contact Information - Retrátil */}
        <div className="bg-white rounded-lg border border-gray-200">
          <div 
            className="flex items-center justify-between p-6 cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => toggleSection('contact')}
          >
            <div className="flex items-center">
              <MapPin className="w-5 h-5 text-green-600 mr-2" />
              <h2 className="text-xl font-semibold text-gray-900">Informações de Contato</h2>
            </div>
            {expandedSections.contact ? (
              <ChevronDown className="w-5 h-5 text-gray-500" />
            ) : (
              <ChevronRight className="w-5 h-5 text-gray-500" />
            )}
          </div>

          {expandedSections.contact && (
            <div className="px-6 pb-6 border-t border-gray-100">
              <div className="pt-6">

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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

        {/* Data Retention Policy */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center mb-6">
            <Shield className="w-5 h-5 text-purple-600 mr-2" />
            <h2 className="text-xl font-semibold text-gray-900">Política de Retenção de Dados</h2>
          </div>

          <div className="space-y-6">
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <h3 className="text-sm font-medium text-yellow-800 mb-2">
                Configurações de Privacidade e LGPD
              </h3>
              <p className="text-sm text-yellow-700">
                Configure os prazos de guarda de dados pessoais conforme a Lei Geral de Proteção de Dados (LGPD)
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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

        {/* Future Features */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center mb-6">
            <Users className="w-5 h-5 text-orange-600 mr-2" />
            <h2 className="text-xl font-semibold text-gray-900">Funcionalidades Futuras</h2>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Em Desenvolvimento</h3>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• Cadastro de usuários e permissões</li>
              <li>• Controle de acesso por módulos</li>
              <li>• Auditoria de ações dos usuários</li>
              <li>• Configurações avançadas de segurança</li>
            </ul>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Salvando...' : 'Salvar Configurações'}
          </button>
        </div>
      </div>
    </div>
  );
};