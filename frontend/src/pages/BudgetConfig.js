import React, { useState, useEffect } from 'react';
import { Edit2, Save, X } from 'lucide-react';
import { budgetConfigApi } from '../services/api';
import { toast } from '../hooks/use-toast';

const CATEGORIES = [
  { key: 'risks_estofados', label: 'ESTOFADOS', description: 'Sofás, cadeiras, poltronas, almofadas' },
  { key: 'risks_colchoes', label: 'COLCHÕES', description: 'Todos os tipos de colchões' },
  { key: 'risks_box', label: 'BOX', description: 'Box de camas' },
  { key: 'risks_tapetes', label: 'TAPETES', description: 'Tapetes para lavagem na empresa' },
  { key: 'risks_carpetes_tapetes_local', label: 'CARPETES E TAPETES NO LOCAL', description: 'Serviços executados no local do cliente' },
  { key: 'risks_cortinas', label: 'CORTINAS', description: 'Todos os tipos de cortinas' },
  { key: 'risks_persianas', label: 'PERSIANAS', description: 'Persianas verticais, horizontais e rolô' },
  { key: 'risks_itens_infantis', label: 'ITENS INFANTIS', description: 'Carrinhos, cadeirinhas, bebê conforto' },
  { key: 'risks_veiculos', label: 'VEÍCULOS', description: 'Bancos, carpetes e forrações de veículos' },
  { key: 'risks_impermeabilizacao', label: 'IMPERMEABILIZAÇÃO', description: 'Serviços de impermeabilização' },
  { key: 'risks_outros_itens', label: 'OUTROS ITENS', description: 'Demais serviços diversos' }
];

const EditableField = ({ label, description, value, onSave, placeholder }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value || '');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setEditValue(value || '');
  }, [value]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave(editValue);
      setIsEditing(false);
      toast({
        title: "Sucesso!",
        description: "Texto salvo com sucesso!",
        variant: "default",
      });
    } catch (error) {
      console.error('Erro ao salvar:', error);
      toast({
        title: "Erro!",
        description: "Erro ao salvar texto. Tente novamente.",
        variant: "destructive",
      });
    }
    setIsSaving(false);
  };

  const handleCancel = () => {
    setEditValue(value || '');
    setIsEditing(false);
  };

  const formatPreview = (text) => {
    if (!text) return 'Nenhum texto configurado';

    // Convert WhatsApp style formatting to HTML for preview
    return text
      .replace(/\*(.*?)\*/g, '<strong>$1</strong>')
      .replace(/_(.*?)_/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{label}</h3>
          {description && (
            <p className="text-sm text-gray-500">{description}</p>
          )}
        </div>
        <div className="flex space-x-2">
          {!isEditing ? (
            <button
              onClick={() => setIsEditing(true)}
              className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
              title="Editar"
            >
              <Edit2 className="w-4 h-4" />
            </button>
          ) : (
            <>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors disabled:opacity-50"
                title="Salvar"
              >
                <Save className="w-4 h-4" />
              </button>
              <button
                onClick={handleCancel}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="Cancelar"
              >
                <X className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>

      {isEditing ? (
        <div>
          <textarea
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            placeholder={placeholder}
            className="w-full h-32 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-vertical"
            rows={4}
          />
          <div className="mt-2 text-xs text-gray-500">
            <strong>Formatação:</strong> Use *texto* para <strong>negrito</strong> e _texto_ para <em>itálico</em>
          </div>
        </div>
      ) : (
        <div 
          className="text-gray-700 p-3 bg-gray-50 rounded-lg min-h-[80px] text-sm leading-relaxed overflow-hidden"
          dangerouslySetInnerHTML={{ __html: formatPreview(value) }}
        />
      )}
    </div>
  );
};

export const BudgetConfig = ({ embedded = false }) => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await budgetConfigApi.get();
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

  const handleSaveField = async (field, value) => {
    const updatedConfig = {
      ...config,
      [field]: value
    };
    
    const response = await budgetConfigApi.update(updatedConfig);
    setConfig(response.data);
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            {[1,2,3].map(i => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={embedded ? '' : 'p-6 max-w-6xl mx-auto'}>
      {!embedded && (
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Configurações do Orçamento</h1>
          <p className="text-gray-600 mt-2">
            Configure os textos de riscos, advertências e condições gerais que aparecerão nos orçamentos PDF
          </p>
        </div>
      )}

      {/* Risk Texts Section */}
      <div className="mb-12">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Textos de Riscos e Advertências</h2>
          <p className="text-gray-600">
            Configure os textos de risco para cada categoria de serviço. Estes textos aparecerão na seção "Riscos e Advertências" do PDF quando o orçamento contiver itens da respectiva categoria.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {CATEGORIES.map((category) => (
            <EditableField
              key={category.key}
              label={category.label}
              description={category.description}
              value={config?.[category.key]}
              onSave={(value) => handleSaveField(category.key, value)}
              placeholder={`Digite os riscos e advertências para ${category.label.toLowerCase()}...`}
            />
          ))}
        </div>
      </div>

      {/* General Conditions Section */}
      <div className="mb-12">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Condições Gerais</h2>
          <p className="text-gray-600">
            Configure o texto das condições gerais que aparecerá sempre ao final de todos os orçamentos PDF.
          </p>
        </div>

        <EditableField
          label="Condições Gerais do Orçamento"
          description="Texto fixo que aparece em todos os orçamentos PDF"
          value={config?.general_conditions}
          onSave={(value) => handleSaveField('general_conditions', value)}
          placeholder="Digite as condições gerais do orçamento..."
        />
      </div>

      {/* Footer Section */}
      <div className="mb-12">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Rodapé</h2>
          <p className="text-gray-600">
            Configure o texto do rodapé que aparecerá no final de todos os orçamentos PDF e WhatsApp.
          </p>
        </div>

        <EditableField
          label="Texto do Rodapé"
          description="Aparece no final dos orçamentos PDF e WhatsApp"
          value={config?.footer_text}
          onSave={(value) => handleSaveField('footer_text', value)}
          placeholder="Digite o texto do rodapé..."
        />
      </div>

      {/* Formatting Help */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">Guia de Formatação</h3>
        <div className="text-blue-800 space-y-2">
          <p><strong>Negrito:</strong> Use *texto* para deixar o <strong>texto em negrito</strong></p>
          <p><strong>Itálico:</strong> Use _texto_ para deixar o <em>texto em itálico</em></p>
          <p><strong>Combinado:</strong> Use *_texto_* ou _*texto*_ para <strong><em>negrito e itálico</em></strong></p>
          <p className="text-sm mt-3 text-blue-600">
            <strong>Nota:</strong> Esta formatação funcionará tanto no PDF quanto nas mensagens WhatsApp
          </p>
        </div>
      </div>
    </div>
  );
};