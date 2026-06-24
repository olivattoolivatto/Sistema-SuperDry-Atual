import React, { useState } from 'react';
import { BarChart3, FileSpreadsheet, ChevronRight, ChevronLeft, Printer, Lock, Ruler, Loader2, Search } from 'lucide-react';
import { reportsApi } from '../services/api';

const fmtMoney = (n) => (Number(n) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const fmtArea = (n) => `${(Number(n) || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m²`;

// Parceiros conhecidos (cadastros reais em /clients) — usado só para popular o
// seletor; o backend aceita qualquer client_id de parceiro em
// GET /reports/partner-items?partner_client_id=...
const PARTNERS = [
  { id: '', label: 'Todos os parceiros' },
  { id: 'CLI-0006', label: 'Leonardo Dry Clean' },
  { id: 'CLI-0009', label: 'Forma Clean (Maika/Renan)' },
  { id: 'CLI-0010', label: 'Higia Service (Vinícius/Lucas)' },
  { id: 'CLI-0011', label: 'Wesley Higienização' },
  { id: 'CLI-0016', label: 'Felipe Gonçalves / João Farias' },
];

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}
function firstDayOfMonthISO() {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10);
}
function fmtDateBR(iso) {
  if (!iso) return '—';
  const [y, m, d] = iso.split('-');
  return d && m && y ? `${d}/${m}/${y}` : iso;
}

// ── Relatório: Fechamento de Parceiro (Tapetes/Cortinas) ───────────────────────
function PartnerBillingReport({ onBack }) {
  const [partnerId, setPartnerId] = useState('');
  const [startDate, setStartDate] = useState(firstDayOfMonthISO());
  const [endDate, setEndDate] = useState(todayISO());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null); // { rows, totals_by_partner }

  const runReport = async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (partnerId) params.partner_client_id = partnerId;
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      const res = await reportsApi.partnerItems(params);
      setResult(res.data);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erro ao gerar relatório. Tente novamente.');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const rows = result?.rows || [];
  const totalsByPartner = result?.totals_by_partner || {};
  const areaTotal = Object.values(totalsByPartner).reduce((s, t) => s + (t.area_m2 || 0), 0);
  const valorTotal = Object.values(totalsByPartner).reduce((s, t) => s + (t.valor || 0), 0);
  const qtdTotal = Object.values(totalsByPartner).reduce((s, t) => s + (t.qtd || 0), 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700">
          <ChevronLeft className="w-4 h-4" /> Voltar aos relatórios
        </button>
        {result && (
          <button onClick={() => window.print()} className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-blue-600 border border-gray-200 rounded-lg px-2.5 py-1.5">
            <Printer className="w-3.5 h-3.5" /> Imprimir / PDF
          </button>
        )}
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 grid gap-3 sm:grid-cols-4">
        <div className="sm:col-span-2">
          <label className="text-[10px] text-gray-400 uppercase tracking-wide">Parceiro</label>
          <select
            value={partnerId}
            onChange={(e) => setPartnerId(e.target.value)}
            className="mt-1 w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm"
          >
            {PARTNERS.map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[10px] text-gray-400 uppercase tracking-wide">De</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="mt-1 w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="text-[10px] text-gray-400 uppercase tracking-wide">Até</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="mt-1 w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm"
          />
        </div>
        <div className="sm:col-span-4 flex justify-end">
          <button
            onClick={runReport}
            disabled={loading}
            className="flex items-center gap-1.5 bg-[#1F4E8C] text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-800 disabled:opacity-60"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Gerar relatório
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-3 py-2">{error}</div>
      )}

      {result && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="bg-[#1F4E8C] text-white px-5 py-4">
            <h2 className="text-base font-bold">Fechamento de Cobrança — Parceiro</h2>
            <p className="text-xs text-blue-100 mt-0.5">Tapetes e Cortinas terceirizados</p>
          </div>

          <div className="px-5 py-3 border-b border-gray-100 grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
            <div>
              <div className="text-[10px] text-gray-400 uppercase tracking-wide">Parceiro</div>
              <div className="font-semibold text-gray-900">{partnerId ? (PARTNERS.find(p => p.id === partnerId)?.label || partnerId) : 'Todos os parceiros'}</div>
            </div>
            <div>
              <div className="text-[10px] text-gray-400 uppercase tracking-wide">Período de referência</div>
              <div className="font-medium text-gray-700">{fmtDateBR(startDate)} a {fmtDateBR(endDate)}</div>
            </div>
            <div>
              <div className="text-[10px] text-gray-400 uppercase tracking-wide">Gerado em</div>
              <div className="font-medium text-gray-700">{new Date().toLocaleDateString('pt-BR')}</div>
            </div>
          </div>

          <div className="px-5 py-2 bg-amber-50 border-b border-amber-100 text-[11px] text-amber-700">
            As datas filtram pela data de referência de cada item (medição/coleta extraída do WhatsApp, com fallback na criação do orçamento).
          </div>

          {rows.length === 0 ? (
            <div className="px-5 py-10 text-center text-sm text-gray-400">
              Nenhum item de parceiro encontrado nesse período.
            </div>
          ) : (
            <>
              {/* Tabela */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-[11px] text-gray-500 uppercase tracking-wide">
                      <th className="text-left px-3 py-2">Data ref.</th>
                      <th className="text-left px-3 py-2">Parceiro</th>
                      <th className="text-left px-3 py-2">Objeto</th>
                      <th className="text-left px-3 py-2">Identificação</th>
                      <th className="text-right px-3 py-2">Medidas</th>
                      <th className="text-right px-3 py-2">Área</th>
                      <th className="text-right px-3 py-2">Valor</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {rows.map((r, i) => (
                      <tr key={r.item_id || i} className={i % 2 ? 'bg-gray-50/40' : ''}>
                        <td className="px-3 py-1.5 text-gray-500 text-xs">{fmtDateBR(r.data_referencia)}</td>
                        <td className="px-3 py-1.5 text-xs text-gray-700">{r.parceiro}</td>
                        <td className="px-3 py-1.5 text-xs text-gray-700">{r.objeto}</td>
                        <td className="px-3 py-1.5 text-xs text-gray-700">
                          {r.etiqueta ? <span className="font-medium">{r.etiqueta}</span> : <span className="text-gray-400 italic">sem nome</span>}
                        </td>
                        <td className="px-3 py-1.5 text-right text-xs text-gray-600 font-mono">
                          {r.diametro ? `Ø ${Number(r.diametro).toFixed(2)}m` : (r.largura && r.comprimento ? `${Number(r.largura).toFixed(2)}×${Number(r.comprimento).toFixed(2)}m` : '—')}
                        </td>
                        <td className="px-3 py-1.5 text-right text-xs text-gray-700">{r.area_m2 != null ? fmtArea(r.area_m2) : '—'}</td>
                        <td className="px-3 py-1.5 text-right text-sm font-semibold text-gray-900">{fmtMoney(r.valor)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Resumo */}
              <div className="px-5 py-4 bg-gray-50 border-t border-gray-200">
                <h3 className="text-xs font-bold text-[#1F4E8C] uppercase tracking-wide mb-2">Resumo por parceiro</h3>
                <div className="grid gap-2 mb-3">
                  {Object.entries(totalsByPartner).map(([nome, t]) => (
                    <div key={nome} className="bg-white rounded-lg border border-gray-200 px-3 py-2 flex items-center justify-between text-sm">
                      <span className="font-medium text-gray-800">{nome}</span>
                      <span className="text-xs text-gray-500">{t.qtd} itens · {fmtArea(t.area_m2)}</span>
                      <span className="font-semibold text-gray-900">{fmtMoney(t.valor)}</span>
                    </div>
                  ))}
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                  <div className="bg-white rounded-lg border border-gray-200 px-3 py-2">
                    <div className="text-[10px] text-gray-400">Itens</div>
                    <div className="font-semibold text-gray-900">{qtdTotal}</div>
                  </div>
                  <div className="bg-white rounded-lg border border-gray-200 px-3 py-2">
                    <div className="text-[10px] text-gray-400 flex items-center gap-1"><Ruler className="w-3 h-3" /> Metragem total lavada</div>
                    <div className="font-semibold text-gray-900">{fmtArea(areaTotal)}</div>
                  </div>
                  <div className="bg-[#8CC63F] rounded-lg px-3 py-2 text-white sm:col-span-2">
                    <div className="text-[10px] text-green-50">Total a cobrar</div>
                    <div className="font-bold text-lg">{fmtMoney(valorTotal)}</div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Menu de relatórios ───────────────────────────────────────────────────────────
const REPORTS = [
  {
    id: 'partner-billing',
    title: 'Fechamento de Parceiro — Tapetes/Cortinas',
    subtitle: 'Escolha o parceiro e o período',
    icon: FileSpreadsheet,
    available: true,
  },
  { id: 'commissions', title: 'Comissões de Vendedores e Técnicos', subtitle: 'Em breve', icon: BarChart3, available: false },
  { id: 'delinquency', title: 'Inadimplência', subtitle: 'Em breve', icon: BarChart3, available: false },
  { id: 'revenue', title: 'Faturamento por Período', subtitle: 'Em breve', icon: BarChart3, available: false },
];

export function Reports() {
  const [open, setOpen] = useState(null);

  if (open === 'partner-billing') {
    return <PartnerBillingReport onBack={() => setOpen(null)} />;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-gradient-to-br from-[#1F4E8C] to-blue-700 rounded-xl flex items-center justify-center">
          <BarChart3 className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Relatórios</h1>
          <p className="text-xs text-gray-500">Relatórios fixos do sistema</p>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {REPORTS.map((r) => {
          const Icon = r.icon;
          return (
            <button
              key={r.id}
              disabled={!r.available}
              onClick={() => r.available && setOpen(r.id)}
              className={`flex items-center justify-between text-left bg-white rounded-xl border p-4 transition ${
                r.available ? 'border-gray-200 hover:border-blue-300 hover:shadow-sm cursor-pointer' : 'border-gray-100 opacity-60 cursor-not-allowed'
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${r.available ? 'bg-blue-50 text-blue-600' : 'bg-gray-100 text-gray-400'}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-gray-900 truncate">{r.title}</div>
                  <div className="text-xs text-gray-500 truncate">{r.subtitle}</div>
                </div>
              </div>
              {r.available
                ? <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />
                : <Lock className="w-3.5 h-3.5 text-gray-300 shrink-0" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default Reports;
