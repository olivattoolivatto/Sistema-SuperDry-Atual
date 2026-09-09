import React, { useState, useEffect, useCallback } from 'react';
import { Edit2, Save, X, Plus, ChevronDown, ChevronUp, BadgeCheck, Clock } from 'lucide-react';
import { budgetConfigApi, termVersionsApi } from '../services/api';
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

// ─── Gerenciador de Versões do Termo de Ciência ──────────────────────────────

const formatPreviewText = (text) => {
  if (!text) return 'Nenhum texto configurado';
  return text
    .replace(/\*(.*?)\*/g, '<strong>$1</strong>')
    .replace(/_(.*?)_/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
};

const TermVersionManager = () => {
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newText, setNewText] = useState('');
  const [newLabel, setNewLabel] = useState('');
  const [saving, setSaving] = useState(false);
  const [expandedId, setExpandedId] = useState(null);

  const load = useCallback(async () => {
    try {
      const r = await termVersionsApi.list();
      setVersions(r.data.versions || []);
      // Auto-expand active version
      const active = (r.data.versions || []).find(v => v.is_active);
      if (active) setExpandedId(active.id);
    } catch (e) {
      toast({ title: 'Erro', description: 'Não foi possível carregar as versões do termo.', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    if (!newText.trim()) {
      toast({ title: 'Atenção', description: 'O texto do termo não pode estar vazio.', variant: 'destructive' });
      return;
    }
    setSaving(true);
    try {
      await termVersionsApi.create({ text: newText.trim(), label: newLabel.trim() || undefined });
      toast({ title: 'Versão criada!', description: 'Nova versão do termo salva com sucesso.', variant: 'default' });
      setCreating(false);
      setNewText('');
      setNewLabel('');
      await load();
    } catch (e) {
      toast({ title: 'Erro', description: e?.response?.data?.detail || 'Erro ao criar versão.', variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="h-32 bg-gray-100 rounded-lg animate-pulse" />;
  }

  return (
    <div className="space-y-4">
      {/* Lista de versões */}
      {versions.length === 0 && !creating && (
        <div className="text-center py-8 text-gray-500 border-2 border-dashed border-gray-200 rounded-lg">
          <p className="mb-2">Nenhuma versão do termo cadastrada.</p>
          <p className="text-sm">Clique em "Nova Versão" para criar a primeira.</p>
        </div>
      )}

      {versions.map((v) => (
        <div
          key={v.id}
          className={`rounded-lg border ${v.is_active ? 'border-blue-400 bg-blue-50' : 'border-gray-200 bg-white'}`}
        >
          {/* Header da versão */}
          <div
            className="flex items-center justify-between p-4 cursor-pointer"
            onClick={() => setExpandedId(expandedId === v.id ? null : v.id)}
          >
            <div className="flex items-center gap-3">
              {v.is_active ? (
                <BadgeCheck className="w-5 h-5 text-blue-600 shrink-0" />
              ) : (
                <Clock className="w-5 h-5 text-gray-400 shrink-0" />
              )}
              <div>
                <span className="font-semibold text-gray-900">
                  {v.label || `v${v.version_number}`}
                </span>
                {v.is_active && (
                  <span className="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">
                    ATIVA
                  </span>
                )}
                <p className="text-xs text-gray-500 mt-0.5">
                  Criada em {v.created_at ? new Date(v.created_at).toLocaleString('pt-BR') : '—'}
                  {v.created_by_name ? ` por ${v.created_by_name}` : ''}
                </p>
              </div>
            </div>
            {expandedId === v.id
              ? <ChevronUp className="w-4 h-4 text-gray-400" />
              : <ChevronDown className="w-4 h-4 text-gray-400" />
            }
          </div>

          {/* Conteúdo expandido — somente leitura */}
          {expandedId === v.id && (
            <div className="px-4 pb-4">
              <div
                className="text-sm text-gray-700 p-4 bg-white rounded-lg border border-gray-200 leading-relaxed min-h-[80px]"
                dangerouslySetInnerHTML={{ __html: formatPreviewText(v.text) }}
              />
              <p className="text-xs text-gray-400 mt-2">
                ID: {v.id} · Versão {v.version_number}
                {!v.is_active && ' · Esta versão está arquivada — aceites já emitidos com ela continuam vinculados a este texto.'}
              </p>
            </div>
          )}
        </div>
      ))}

      {/* Editor de nova versão */}
      {creating ? (
        <div className="border-2 border-blue-300 border-dashed rounded-lg p-5 bg-blue-50 space-y-3">
          <h4 className="font-semibold text-blue-900">Nova versão do Termo de Ciência</h4>
          <p className="text-xs text-blue-700">
            A versão anterior será arquivada. Todos os novos aceites emitidos a partir de agora usarão este texto.
            Aceites já emitidos continuam amarrados ao texto original — garantia de auditoria.
          </p>
          <div>
            <label className="text-xs font-medium text-gray-700 block mb-1">Rótulo da versão (opcional)</label>
            <input
              type="text"
              value={newLabel}
              onChange={e => setNewLabel(e.target.value)}
              placeholder="ex: v2 — inclui cláusula de impermeabilização"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-700 block mb-1">Texto do termo</label>
            <textarea
              value={newText}
              onChange={e => setNewText(e.target.value)}
              placeholder="Digite o texto completo do Termo de Ciência..."
              rows={10}
              className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-vertical font-mono"
            />
            <p className="text-xs text-gray-500 mt-1">
              <strong>Formatação:</strong> *negrito* · _itálico_
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Salvando...' : 'Publicar nova versão'}
            </button>
            <button
              onClick={() => { setCreating(false); setNewText(''); setNewLabel(''); }}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50 transition-colors"
            >
              <X className="w-4 h-4" />
              Cancelar
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => {
            // Pre-fill with current active version text to make editing easier
            const active = versions.find(v => v.is_active);
            setNewText(active?.text || '');
            setNewLabel('');
            setCreating(true);
          }}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-gray-300 text-gray-600 rounded-lg hover:border-blue-400 hover:text-blue-600 transition-colors text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Nova Versão do Termo
        </button>
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

      {/* Termo de Ciência — com versionamento imutável */}
      <div className="mb-12">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Termo de Ciência</h2>
          <p className="text-gray-600">
            Texto que o cliente lê e assina digitalmente antes de autorizar o serviço.
            Cada edição gera uma nova versão — a versão anterior fica arquivada e continua
            vinculada aos aceites que foram emitidos com ela, garantindo rastreabilidade para auditoria.
          </p>
        </div>
        <TermVersionManager />
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