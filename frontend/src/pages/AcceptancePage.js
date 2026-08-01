import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { CheckCircle, AlertTriangle, Shield, FileText, Loader2, ChevronDown, ChevronUp, MapPin } from 'lucide-react';

// Usa sempre o domínio atual para evitar mixed-content (HTTP dentro de HTTPS)
const BACKEND_URL = window.location.origin;

// Converte texto com simbologia WhatsApp para JSX formatado
// *bold*, _italic_, ~strikethrough~, `code`
function FormatText({ text }) {
  if (!text) return null;

  const parseInline = (line) => {
    // Tokeniza todos os marcadores inline em ordem
    const pattern = /(\*[^*\n]+\*|_[^_\n]+_|~[^~\n]+~|`[^`\n]+`)/g;
    const parts = [];
    let last = 0;
    let match;
    while ((match = pattern.exec(line)) !== null) {
      if (match.index > last) parts.push({ type: 'text', value: line.slice(last, match.index) });
      const raw = match[0];
      if (raw.startsWith('*') && raw.endsWith('*'))
        parts.push({ type: 'bold', value: raw.slice(1, -1) });
      else if (raw.startsWith('_') && raw.endsWith('_'))
        parts.push({ type: 'italic', value: raw.slice(1, -1) });
      else if (raw.startsWith('~') && raw.endsWith('~'))
        parts.push({ type: 'strike', value: raw.slice(1, -1) });
      else if (raw.startsWith('`') && raw.endsWith('`'))
        parts.push({ type: 'code', value: raw.slice(1, -1) });
      last = match.index + raw.length;
    }
    if (last < line.length) parts.push({ type: 'text', value: line.slice(last) });
    return parts;
  };

  const lines = text.split('\n');
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        if (line.trim() === '') return <div key={i} className="h-1" />;
        const parts = parseInline(line);
        return (
          <p key={i} className="text-sm leading-relaxed text-gray-700">
            {parts.map((p, j) => {
              if (p.type === 'bold') return <strong key={j}>{p.value}</strong>;
              if (p.type === 'italic') return <em key={j}>{p.value}</em>;
              if (p.type === 'strike') return <del key={j} className="text-gray-400">{p.value}</del>;
              if (p.type === 'code') return <code key={j} className="bg-gray-100 px-1 rounded text-xs font-mono">{p.value}</code>;
              return <span key={j}>{p.value}</span>;
            })}
          </p>
        );
      })}
    </div>
  );
}

// Formata data/hora em GMT-4 (America/Cuiabá)
function fmtGMT4(isoString) {
  if (!isoString) return '';
  try {
    return new Date(isoString).toLocaleString('pt-BR', {
      timeZone: 'America/Cuiaba',
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    }) + ' (GMT-4)';
  } catch {
    return new Date(isoString).toLocaleString('pt-BR');
  }
}

export default function AcceptancePage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Formulário de aceite
  const [name, setName] = useState('');
  const [checkboxes, setCheckboxes] = useState({});
  const [generalChecked, setGeneralChecked] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [acceptedAt, setAcceptedAt] = useState(null);

  // Opções avançadas
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [alternativeAddress, setAlternativeAddress] = useState('');
  const [addressNote, setAddressNote] = useState('');

  const allChecked = (() => {
    if (!data) return false;
    const allRisks = (data.risk_sections || []).every(s => checkboxes[s.category]);
    return allRisks && generalChecked;
  })();

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${BACKEND_URL}/api/acceptance/${token}`);
      if (!r.ok) throw new Error('Link inválido ou expirado');
      const d = await r.json();
      setData(d);
      if (d.status === 'ACCEPTED') {
        setDone(true);
        setAcceptedAt(d.accepted_at);
        setName(d.accepted_name || '');
      }
      const initial = {};
      (d.risk_sections || []).forEach(s => { initial[s.category] = false; });
      setCheckboxes(initial);
    } catch (e) {
      setError(e.message || 'Erro ao carregar os termos de serviço.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const handleCheck = (category, val) => setCheckboxes(prev => ({ ...prev, [category]: val }));

  const handleSubmit = async () => {
    if (!name.trim()) { alert('Por favor, informe seu nome completo.'); return; }
    if (!allChecked) { alert('Você precisa marcar todos os itens antes de confirmar.'); return; }
    setSubmitting(true);
    try {
      const r = await fetch(`${BACKEND_URL}/api/acceptance/${token}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          checkboxes: { ...checkboxes, general: generalChecked },
          alternative_address: alternativeAddress.trim() || null,
          address_note: addressNote.trim() || null,
        }),
      });
      if (!r.ok) {
        const err = await r.json();
        throw new Error(err.detail || 'Erro ao confirmar aceite.');
      }
      const resp = await r.json();
      setDone(true);
      setAcceptedAt(resp.accepted_at);
    } catch (e) {
      alert(e.message || 'Erro ao confirmar. Tente novamente.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="bg-white rounded-xl shadow p-6 max-w-sm w-full text-center">
          <AlertTriangle className="w-10 h-10 text-red-500 mx-auto mb-3" />
          <p className="text-gray-800 font-medium">{error}</p>
          <p className="text-sm text-gray-500 mt-1">Solicite um novo link ao atendente.</p>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="min-h-screen bg-green-50 flex items-center justify-center px-4">
        <div className="bg-white rounded-xl shadow p-6 max-w-sm w-full text-center">
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-gray-900 mb-1">Aceite confirmado!</h2>
          <p className="text-sm text-gray-600">
            <strong>{name || data?.accepted_name}</strong> confirmou os termos em{' '}
            <strong>{fmtGMT4(acceptedAt)}</strong>.
          </p>
          <p className="text-xs text-gray-400 mt-3">
            Registro com validade jurídica — Lei 14.063/2020 e Marco Civil da Internet.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-[#1F4E8C] text-white px-4 py-4">
        <p className="text-xs opacity-70 uppercase tracking-wide mb-0.5">{data.company_name}</p>
        <h1 className="text-base font-bold flex items-center gap-2">
          <Shield className="w-4 h-4" /> Termo de Ciência do Serviço
        </h1>
        <p className="text-xs opacity-80 mt-0.5">
          Orçamento {data.budget.id} — {data.budget.client_name}
        </p>
      </div>

      <div className="max-w-lg mx-auto px-4 py-5 space-y-4">

        {/* Intro */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-sm text-gray-700 leading-relaxed">
            Antes de iniciarmos o serviço, leia com atenção as condições e riscos de cada
            categoria. Ao confirmar, você declara que está ciente de todo o conteúdo abaixo.
          </p>
          <p className="text-xs text-gray-400 mt-2">
            IP, data, horário e dispositivo serão registrados como evidência eletrônica (GMT-4).
          </p>
        </div>

        {/* Risk sections */}
        {data.risk_sections.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-gray-800 flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-amber-500" /> Riscos por categoria de serviço
            </h2>
            {data.risk_sections.map(section => (
              <div key={section.category} className="bg-white rounded-xl border border-gray-200 p-4">
                <h3 className="text-sm font-semibold text-[#1F4E8C] mb-2">{section.label}</h3>
                <FormatText text={section.text} />
                <label className="flex items-start gap-2 mt-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checkboxes[section.category] || false}
                    onChange={e => handleCheck(section.category, e.target.checked)}
                    className="mt-0.5 accent-blue-600 w-4 h-4 flex-shrink-0"
                  />
                  <span className="text-xs text-gray-600">
                    Li e estou ciente dos riscos de <strong>{section.label}</strong>.
                  </span>
                </label>
              </div>
            ))}
          </div>
        )}

        {/* General conditions */}
        {data.general_conditions && (
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-1.5 mb-2">
              <FileText className="w-4 h-4 text-gray-500" /> Condições gerais
            </h3>
            <FormatText text={data.general_conditions} />
            <label className="flex items-start gap-2 mt-3 cursor-pointer">
              <input
                type="checkbox"
                checked={generalChecked}
                onChange={e => setGeneralChecked(e.target.checked)}
                className="mt-0.5 accent-blue-600 w-4 h-4 flex-shrink-0"
              />
              <span className="text-xs text-gray-600">
                Li e aceito as condições gerais de prestação de serviço.
              </span>
            </label>
          </div>
        )}

        {data.risk_sections.length === 0 && !data.general_conditions && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <p className="text-sm text-amber-800">
              Nenhum texto de condições cadastrado. Entre em contato com o atendente.
            </p>
          </div>
        )}

        {/* Identificação */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
          <h3 className="text-sm font-semibold text-gray-800">Sua identificação</h3>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Nome completo *</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Digite seu nome completo"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <p className="text-xs text-gray-400">
            Ao confirmar, você assina eletronicamente este termo. IP, data/hora (GMT-4) e
            dispositivo serão registrados.
          </p>
        </div>

        {/* Opções avançadas */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <button
            onClick={() => setShowAdvanced(v => !v)}
            className="w-full flex items-center justify-between px-4 py-3 text-sm text-gray-700 hover:bg-gray-50"
          >
            <span className="flex items-center gap-2 font-medium">
              <MapPin className="w-4 h-4 text-gray-400" /> Opções avançadas
              <span className="text-xs text-gray-400 font-normal">(endereço diferente, observações)</span>
            </span>
            {showAdvanced ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
          </button>

          {showAdvanced && (
            <div className="px-4 pb-4 space-y-3 border-t border-gray-100 pt-3">
              <div>
                <label className="block text-xs text-gray-600 mb-1">
                  Endereço de coleta/entrega diferente do cadastrado
                </label>
                <input
                  type="text"
                  value={alternativeAddress}
                  onChange={e => setAlternativeAddress(e.target.value)}
                  placeholder="Ex.: Rua das Flores, 123 — Bairro, Cuiabá"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">
                  Observações adicionais (horário preferencial, portaria, etc.)
                </label>
                <textarea
                  value={addressNote}
                  onChange={e => setAddressNote(e.target.value)}
                  placeholder="Ex.: Ligar antes de vir. Entrada pelo portão lateral."
                  rows={3}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>
            </div>
          )}
        </div>

        {/* Confirmar */}
        <button
          onClick={handleSubmit}
          disabled={submitting || !allChecked || !name.trim()}
          className="w-full py-3.5 rounded-xl bg-[#1F4E8C] text-white font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-900 transition-colors"
        >
          {submitting ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Confirmando...</>
          ) : (
            <><Shield className="w-4 h-4" /> Confirmar leitura e aceite</>
          )}
        </button>

        {(!allChecked || !name.trim()) && (
          <p className="text-xs text-center text-gray-400">
            {!name.trim()
              ? 'Informe seu nome completo para confirmar.'
              : 'Marque todos os itens acima para habilitar a confirmação.'}
          </p>
        )}

        {data.footer_text && (
          <p className="text-xs text-center text-gray-400 pb-4">{data.footer_text}</p>
        )}
      </div>
    </div>
  );
}
