import React, { useState, useEffect } from 'react';
import { Save, MapPin, Building2, Shield, Users } from 'lucide-react';
import { systemConfigApi, placesApi } from '../services/api';
import { toast } from '../hooks/use-toast';

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

  const handleAddressSearch = async (address) => {
    // Esta função será implementada futuramente com Google Places API
    // Por enquanto, apenas atualiza o endereço
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
        {/* Company Information */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center mb-6">
            <Building2 className="w-5 h-5 text-blue-600 mr-2" />
            <h2 className="text-xl font-semibold text-gray-900">Dados da Empresa</h2>
          </div>

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
              <input
                type="text"
                value={config?.address_full || ''}
                onChange={(e) => handleAddressSearch(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Digite o endereço completo para busca automática"
              />
              <p className="text-xs text-gray-500 mt-1">
                Este endereço será usado como ponto de partida e chegada das rotas
              </p>
            </div>

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
                placeholder="Bairro"
              />
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
                placeholder="Cidade"
              />
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
            </div>
          </div>
        </div>

        {/* Contact Information */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center mb-6">
            <MapPin className="w-5 h-5 text-green-600 mr-2" />
            <h2 className="text-xl font-semibold text-gray-900">Informações de Contato</h2>
          </div>

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