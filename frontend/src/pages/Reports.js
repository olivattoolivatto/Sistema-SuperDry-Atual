import React, { useState } from 'react';
import { BarChart3, FileSpreadsheet, ChevronRight, ChevronLeft, Printer, Lock, Ruler, Loader2, Search, Columns3, RotateCcw, MessageCircle } from 'lucide-react';
import { reportsApi, clientsApi } from '../services/api';

const COL_LABELS = ['Data ref.', 'Objeto', 'Identificação', 'Medidas', 'Área', 'Valor'];
const DEFAULT_COL_WIDTHS = [10, 32, 24, 12, 9, 13];
// Larguras fixas usadas SÓ na impressão/PDF — independentes do ajuste manual
// (que fica salvo só no localStorage de cada aparelho/navegador, por isso
// podia sair diferente no PC e no celular). Dá mais espaço pra Data/Medidas.
const PRINT_COL_WIDTHS = [14, 22, 18, 20, 10, 16];
const COL_WIDTHS_KEY = 'partnerReportColWidths';

function loadColWidths() {
  try {
    const saved = JSON.parse(localStorage.getItem(COL_WIDTHS_KEY));
    if (Array.isArray(saved) && saved.length === DEFAULT_COL_WIDTHS.length) return saved;
  } catch {}
  return [...DEFAULT_COL_WIDTHS];
}

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
  const [colWidths, setColWidths] = useState(loadColWidths);
  const [showColPanel, setShowColPanel] = useState(false);
  const [sendingWhats, setSendingWhats] = useState(false);

  const updateColWidth = (idx, value) => {
    const v = Math.max(4, Math.min(50, Number(value) || 0));
    setColWidths(prev => {
      const next = [...prev];
      next[idx] = v;
      localStorage.setItem(COL_WIDTHS_KEY, JSON.stringify(next));
      return next;
    });
  };

  const resetColWidths = () => {
    setColWidths([...DEFAULT_COL_WIDTHS]);
    localStorage.setItem(COL_WIDTHS_KEY, JSON.stringify(DEFAULT_COL_WIDTHS));
  };

  const colWidthSum = colWidths.reduce((s, v) => s + v, 0);

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

  const sendWhatsApp = async () => {
    if (!partnerId) {
      alert('Selecione um parceiro específico (não "Todos os parceiros") pra enviar o fechamento por WhatsApp.');
      return;
    }
    setSendingWhats(true);
    try {
      const partnerLabel = PARTNERS.find(p => p.id === partnerId)?.label || partnerId;
      const client = await clientsApi.getById(partnerId);
      const phoneRaw = (client.data?.phone_primary || '').replace(/[^0-9]/g, '');
      const phone = phoneRaw ? (phoneRaw.startsWith('55') ? phoneRaw : `55${phoneRaw}`) : '';
      const message =
        `🔸*FECHAMENTO DE COBRANÇA — PARCEIRO*🔸\n` +
        `                     💙_SuperDry®_💚\n` +
        `  _Lavanderia de Tapetes e Estofados_\n\n` +
        `🤝 *Parceiro:* ${partnerLabel}\n` +
        `📅 *Período:* ${fmtDateBR(startDate)} a ${fmtDateBR(endDate)}\n\n` +
        `📄 *Itens:* ${qtdTotal}\n` +
        `📏 *Metragem total lavada:* ${fmtArea(areaTotal)}\n\n` +
        `💰*TOTAL A COBRAR:* ${fmtMoney(valorTotal)}\n\n` +
        `😁_Segue o relatório detalhado em anexo (PDF)._\n` +
        `_Qualquer dúvida, estou à disposição!_`;
      const url = phone
        ? `https://wa.me/${phone}?text=${encodeURIComponent(message)}`
        : `https://wa.me/?text=${encodeURIComponent(message)}`;
      window.open(url, '_blank');
    } catch (e) {
      alert('Erro ao gerar mensagem WhatsApp. Verifique o telefone cadastrado do parceiro.');
    } finally {
      setSendingWhats(false);
    }
  };

  const rows = result?.rows || [];
  const totalsByPartner = result?.totals_by_partner || {};
  const areaTotal = Object.values(totalsByPartner).reduce((s, t) => s + (t.area_m2 || 0), 0);
  const valorTotal = Object.values(totalsByPartner).reduce((s, t) => s + (t.valor || 0), 0);
  const qtdTotal = Object.values(totalsByPartner).reduce((s, t) => s + (t.qtd || 0), 0);

  return (
    <div className="space-y-4">
      <style>{`
        @media print {
          @page { margin: 5mm; }
          html, body { overflow: visible !important; width: 100% !important; }
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          .no-print { display: none !important; }
          .print-card { border: none !important; box-shadow: none !important; width: 100% !important; }
          .print-table-wrap { overflow: visible !important; width: 100% !important; }
          .print-header { padding: 6px 16px !important; display: flex !important; align-items: baseline !important; gap: 10px !important; width: 100% !important; box-sizing: border-box !important; }
          .print-header h2 { font-size: 14px !important; margin: 0 !important; }
          .print-header p { font-size: 9px !important; margin: 0 !important; }
          .print-meta { padding: 5px 16px !important; gap: 18px !important; width: 100% !important; box-sizing: border-box !important; }
          .print-meta > div { display: flex !important; gap: 4px !important; align-items: baseline !important; }
          .print-meta .meta-label { font-size: 8px !important; }
          .print-meta .meta-value { font-size: 10.5px !important; }
          .print-table { width: 100% !important; table-layout: fixed !important; border-collapse: collapse !important; border: 1px solid #94a3b8 !important; }
          .print-colgroup col:nth-child(1) { width: ${PRINT_COL_WIDTHS[0]}% !important; }
          .print-colgroup col:nth-child(2) { width: ${PRINT_COL_WIDTHS[1]}% !important; }
          .print-colgroup col:nth-child(3) { width: ${PRINT_COL_WIDTHS[2]}% !important; }
          .print-colgroup col:nth-child(4) { width: ${PRINT_COL_WIDTHS[3]}% !important; }
          .print-colgroup col:nth-child(5) { width: ${PRINT_COL_WIDTHS[4]}% !important; }
          .print-colgroup col:nth-child(6) { width: ${PRINT_COL_WIDTHS[5]}% !important; }
          .print-table td, .print-table th { white-space: nowrap !important; }
          .print-table th, .print-table td { padding: 3px 9px !important; line-height: 1.3 !important; overflow: hidden !important; text-overflow: ellipsis !important; word-break: break-word !important; border: 1px solid #cbd5e1 !important; }
          .print-table th { font-size: 9.5px !important; background: #eef2f7 !important; }
          .print-table td { font-size: 10.5px !important; }
          .print-table tbody tr:nth-child(even) td { background: #f8fafc !important; }
          .print-summary { padding: 8px 16px !important; width: 100% !important; box-sizing: border-box !important; }
          .print-summary h3 { font-size: 11px !important; margin-bottom: 3px !important; }
          .print-summary-row { padding: 4px 14px !important; font-size: 10px !important; }
          .print-summary-box { padding: 7px 14px !important; }
          .print-summary-box .text-[10px] { font-size: 9px !important; }
          /* Evita que blocos sejam cortados na virada de página, deixando uma
             sobra (faixa cinza) sozinha numa segunda folha quase vazia. */
          .print-card, .print-header, .print-meta, .print-summary {
            break-inside: avoid !important;
            page-break-inside: avoid !important;
          }
          .print-table tr {
            break-inside: avoid !important;
            page-break-inside: avoid !important;
          }
          /* O <thead> de uma <table> HTML repete automaticamente em toda nova
             página quando o navegador decide quebrar a tabela (mesmo que reste
             só 1 linha vazia) — é essa repetição que aparece como a "faixa
             cinza" sozinha na 2ª folha. Desativando o papel de table-header-group
             ele para de repetir. */
          .print-table thead {
            display: table-row-group !important;
          }
        }
      `}</style>
      <div className="flex items-center justify-between no-print">
        <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700">
          <ChevronLeft className="w-4 h-4" /> Voltar aos relatórios
        </button>
        {result && (
          <div className="flex items-center gap-2">
            <button onClick={sendWhatsApp} disabled={sendingWhats} className="flex items-center gap-1.5 text-xs text-white bg-[#25D366] hover:bg-[#1ebe57] border border-[#25D366] rounded-lg px-2.5 py-1.5 disabled:opacity-60">
              <MessageCircle className="w-3.5 h-3.5" /> Enviar por WhatsApp
            </button>
            <button onClick={() => window.print()} className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-blue-600 border border-gray-200 rounded-lg px-2.5 py-1.5">
              <Printer className="w-3.5 h-3.5" /> Imprimir / PDF
            </button>
          </div>
        )}
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 grid gap-3 sm:grid-cols-4 no-print">
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
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-3 py-2 no-print">{error}</div>
      )}

      {result && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden print-card">
          <div className="bg-[#1F4E8C] text-white px-5 py-4 print-header">
            <h2 className="text-base font-bold">Fechamento de Cobrança — Parceiro</h2>
            <p className="text-xs text-blue-100 mt-0.5">Tapetes e Cortinas terceirizados</p>
          </div>

          <div className="px-5 py-3 border-b border-gray-100 grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm print-meta">
            <div>
              <div className="text-[10px] text-gray-400 uppercase tracking-wide meta-label">Parceiro</div>
              <div className="font-semibold text-gray-900 meta-value">{partnerId ? (PARTNERS.find(p => p.id === partnerId)?.label || partnerId) : 'Todos os parceiros'}</div>
            </div>
            <div>
              <div className="text-[10px] text-gray-400 uppercase tracking-wide meta-label">Período de referência</div>
              <div className="font-medium text-gray-700 meta-value">{fmtDateBR(startDate)} a {fmtDateBR(endDate)}</div>
            </div>
            <div>
              <div className="text-[10px] text-gray-400 uppercase tracking-wide meta-label">Gerado em</div>
              <div className="font-medium text-gray-700 meta-value">{new Date().toLocaleDateString('pt-BR')}</div>
            </div>
          </div>

          <div className="px-5 py-2 bg-amber-50 border-b border-amber-100 text-[11px] text-amber-700 no-print">
            As datas filtram pela data de referência de cada item (medição/coleta extraída do WhatsApp, com fallback na criação do orçamento).
          </div>

          {rows.length === 0 ? (
            <div className="px-5 py-10 text-center text-sm text-gray-400">
              Nenhum item de parceiro encontrado nesse período.
            </div>
          ) : (
            <>
              {/* Painel de ajuste de largura das colunas (não imprime) */}
              <div className="px-5 py-3 border-b border-gray-100 no-print">
                <button
                  onClick={() => setShowColPanel(v => !v)}
                  className="flex items-center gap-1.5 text-xs font-medium text-gray-600 hover:text-gray-900"
                >
                  <Columns3 className="w-3.5 h-3.5" />
                  Ajustar largura das colunas
                  <ChevronRight className={`w-3.5 h-3.5 transition-transform ${showColPanel ? 'rotate-90' : ''}`} />
                </button>
                {showColPanel && (
                  <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {COL_LABELS.map((label, idx) => (
                      <div key={label} className="flex flex-col gap-1">
                        <label className="text-[10px] text-gray-500 uppercase tracking-wide">{label}</label>
                        <div className="flex items-center gap-2">
                          <input
                            type="range"
                            min={4}
                            max={40}
                            value={colWidths[idx]}
                            onChange={(e) => updateColWidth(idx, e.target.value)}
                            className="flex-1"
                          />
                          <input
                            type="number"
                            min={4}
                            max={40}
                            value={colWidths[idx]}
                            onChange={(e) => updateColWidth(idx, e.target.value)}
                            className="w-12 text-xs border border-gray-200 rounded px-1 py-0.5"
                          />
                          <span className="text-[10px] text-gray-400">%</span>
                        </div>
                      </div>
                    ))}
                    <div className="flex items-end justify-between col-span-2 sm:col-span-4 pt-1">
                      <span className={`text-xs ${colWidthSum === 100 ? 'text-gray-400' : 'text-amber-600'}`}>
                        Soma atual: {colWidthSum}% {colWidthSum !== 100 && '(não precisa ser exatamente 100%)'}
                      </span>
                      <button
                        onClick={resetColWidths}
                        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
                      >
                        <RotateCcw className="w-3 h-3" /> Restaurar padrão
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Tabela */}
              <div className="overflow-x-auto print-table-wrap">
                <table className="w-full text-sm print-table border border-gray-300" style={{ tableLayout: 'fixed', borderCollapse: 'collapse' }}>
                  <colgroup className="print-colgroup">
                    {colWidths.map((w, idx) => (
                      <col key={idx} style={{ width: `${w}%` }} />
                    ))}
                  </colgroup>
                  <thead>
                    <tr className="bg-gray-50 text-[11px] text-gray-500 uppercase tracking-wide">
                      <th className="text-left px-3 py-1 border border-gray-300">Data ref.</th>
                      <th className="text-left px-3 py-1 border border-gray-300">Objeto</th>
                      <th className="text-left px-3 py-1 border border-gray-300">Identificação</th>
                      <th className="text-right px-3 py-1 border border-gray-300">Medidas</th>
                      <th className="text-right px-3 py-1 border border-gray-300">Área</th>
                      <th className="text-right px-3 py-1 border border-gray-300">Valor</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {rows.map((r, i) => (
                      <tr key={r.item_id || i} className={i % 2 ? 'bg-gray-50/40' : ''}>
                        <td className="px-3 py-0.5 text-gray-500 text-xs border border-gray-200">{fmtDateBR(r.data_referencia)}</td>
                        <td className="px-3 py-0.5 text-xs text-gray-700 border border-gray-200">{r.objeto}</td>
                        <td className="px-3 py-0.5 text-xs text-gray-700 border border-gray-200">
                          {r.etiqueta ? <span className="font-medium">{r.etiqueta}</span> : <span className="text-gray-400 italic">sem nome</span>}
                        </td>
                        <td className="px-3 py-0.5 text-right text-xs text-gray-600 font-mono border border-gray-200">
                          {r.diametro ? `Ø ${Number(r.diametro).toFixed(2)}m` : (r.largura && r.comprimento ? `${Number(r.largura).toFixed(2)}×${Number(r.comprimento).toFixed(2)}m` : '—')}
                        </td>
                        <td className="px-3 py-0.5 text-right text-xs text-gray-700 border border-gray-200">{r.area_m2 != null ? fmtArea(r.area_m2) : '—'}</td>
                        <td className="px-3 py-0.5 text-right text-sm font-semibold text-gray-900 border border-gray-200">{fmtMoney(r.valor)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Resumo */}
              <div className="px-5 py-4 bg-gray-50 border-t border-gray-200 print-summary">
                <h3 className="text-xs font-bold text-[#1F4E8C] uppercase tracking-wide mb-2">Resumo por parceiro</h3>
                <div className="grid gap-2 mb-3">
                  {Object.entries(totalsByPartner).map(([nome, t]) => (
                    <div key={nome} className="bg-white rounded-lg border border-gray-200 px-3 py-2 flex items-center justify-between text-sm print-summary-row">
                      <span className="font-medium text-gray-800">{nome}</span>
                      <span className="text-xs text-gray-500">{t.qtd} itens · {fmtArea(t.area_m2)}</span>
                      <span className="font-semibold text-gray-900">{fmtMoney(t.valor)}</span>
                    </div>
                  ))}
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                  <div className="bg-white rounded-lg border border-gray-200 px-3 py-2 print-summary-box">
                    <div className="text-[10px] text-gray-400">Itens</div>
                    <div className="font-semibold text-gray-900">{qtdTotal}</div>
                  </div>
                  <div className="bg-white rounded-lg border border-gray-200 px-3 py-2 print-summary-box">
                    <div className="text-[10px] text-gray-400 flex items-center gap-1"><Ruler className="w-3 h-3" /> Metragem total lavada</div>
                    <div className="font-semibold text-gray-900">{fmtArea(areaTotal)}</div>
                  </div>
                  <div className="bg-[#8CC63F] rounded-lg px-3 py-2 text-white sm:col-span-2 print-summary-box">
                    <div className="text-[10px] text-green-50">Total a cobrar</div>
                    <div className="font-bold text-lg">{fmtMoney(valorTotal)}</div>
                  </div>
                </div>
              </div>

              {/* Réplica dos botões no rodapé — o do topo é fácil de perder de vista */}
              <div className="px-5 py-4 border-t border-gray-200 flex items-center justify-end gap-2 no-print">
                <button onClick={sendWhatsApp} disabled={sendingWhats} className="flex items-center gap-1.5 text-xs text-white bg-[#25D366] hover:bg-[#1ebe57] border border-[#25D366] rounded-lg px-2.5 py-1.5 disabled:opacity-60">
                  <MessageCircle className="w-3.5 h-3.5" /> Enviar por WhatsApp
                </button>
                <button onClick={() => window.print()} className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-blue-600 border border-gray-200 rounded-lg px-2.5 py-1.5">
                  <Printer className="w-3.5 h-3.5" /> Imprimir / PDF
                </button>
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
