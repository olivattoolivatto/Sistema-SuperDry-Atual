#!/usr/bin/env python3
import re, sys

# ─── BudgetEditor.js ────────────────────────────────────────────────────────
path = '/home/opc/superdry/frontend/src/pages/budgets/BudgetEditor.js'
with open(path, 'r') as f:
    c = f.read()

# P1: imports (idempotent)
c = c.replace(
    "  Calendar, User as UserIcon, CreditCard, FileText, Search, AlertCircle, Copy,\n} from 'lucide-react';",
    "  Calendar, User as UserIcon, CreditCard, FileText, Search, AlertCircle, Copy,\n  MessageSquare, Download, Send,\n} from 'lucide-react';"
)

# P2: state + functions after qcSaving (idempotent)
c = c.replace(
    "  const [qcSaving, setQcSaving] = useState(false);\n",
    "  const [qcSaving, setQcSaving] = useState(false);\n  const [sendPanel, setSendPanel] = useState(false);\n  const [sendData, setSendData] = useState(null);\n  const [sendLoading, setSendLoading] = useState(false);\n  const [copied, setCopied] = useState(false);\n\n  const openSendPanel = async () => {\n    if (!budget?.id) return;\n    setSendLoading(true);\n    setSendPanel(true);\n    setSendData(null);\n    try {\n      const r = await budgetsApi.generateWhatsApp(budget.id);\n      setSendData(r.data);\n    } catch (e) {\n      setSendData({ error: 'Não foi possível gerar o texto. Verifique se o orçamento foi salvo.' });\n    } finally {\n      setSendLoading(false);\n    }\n  };\n\n  const handleCopy = () => {\n    if (!sendData?.message) return;\n    navigator.clipboard.writeText(sendData.message).then(() => {\n      setCopied(true);\n      setTimeout(() => setCopied(false), 2000);\n    });\n  };\n\n"
)

# P3: wrap close button and add send button (idempotent)
c = c.replace(
    '      <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">\n        <X className="w-5 h-5" />\n      </button>\n    </div>',
    '      <div className="flex items-center gap-1">\n        {isEdit && (\n          <button\n            onClick={openSendPanel}\n            title="Enviar para cliente"\n            className="p-2 hover:bg-green-50 text-green-600 rounded-lg"\n          >\n            <Send className="w-5 h-5" />\n          </button>\n        )}\n        <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">\n          <X className="w-5 h-5" />\n        </button>\n      </div>\n    </div>'
)

# P4: add send panel overlay before Stepper (idempotent)
OVERLAY = '''
        {/* Painel "Enviar para cliente" */}
        {sendPanel && (
          <div className="absolute inset-0 z-20 bg-white flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 sticky top-0 bg-white">
              <div>
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-green-600" /> Enviar para cliente
                </h3>
                <p className="text-xs text-gray-500">{form.client_name}</p>
              </div>
              <button onClick={() => setSendPanel(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {sendLoading && (
                <div className="flex items-center justify-center py-10">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                </div>
              )}
              {sendData?.error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                  {sendData.error}
                </div>
              )}
              {sendData?.message && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      Texto do orçamento — copiar e colar no WhatsApp
                    </label>
                    <textarea
                      readOnly
                      value={sendData.message}
                      rows={14}
                      className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg bg-gray-50 resize-none"
                    />
                  </div>
                  {sendData.note && (
                    <p className="text-[11px] text-gray-400 italic">{sendData.note}</p>
                  )}
                </>
              )}
            </div>
            {!sendLoading && sendData && !sendData.error && (
              <div className="px-4 py-3 border-t border-gray-100 space-y-2">
                <button
                  onClick={handleCopy}
                  className="w-full py-2.5 border border-gray-300 rounded-lg text-sm font-medium flex items-center justify-center gap-2 hover:bg-gray-50"
                >
                  <Copy className="w-4 h-4" />
                  {copied ? 'Copiado!' : 'Copiar texto'}
                </button>
                {sendData.whatsapp_url && (
                  <a
                    href={sendData.whatsapp_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full py-2.5 bg-green-500 text-white rounded-lg text-sm font-medium flex items-center justify-center gap-2 hover:bg-green-600 block text-center"
                  >
                    <MessageSquare className="w-4 h-4 inline" /> Abrir WhatsApp
                  </a>
                )}
                <a
                  href={`${BACKEND_URL}/api/budgets/${budget.id}/pdf`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium flex items-center justify-center gap-2 hover:bg-blue-700 block text-center"
                >
                  <Download className="w-4 h-4 inline" /> Download PDF
                </a>
              </div>
            )}
          </div>
        )}
'''
c = c.replace('    {/* Stepper */}', OVERLAY + '    {/* Stepper */}', 1)

# P5: curtain labels + /100 fix (idempotent)
c = c.replace('Varões</label>', 'Dobras</label>')
c = c.replace('Tecido/varão (m)</label>', 'Tecido/dobra (cm)</label>')
c = c.replace(
    'if (needsLinear && item.fabric_folds && item.fabric_per_fold) qty = Number(item.fabric_folds) * Number(item.fabric_per_fold);',
    'if (needsLinear && item.fabric_folds && item.fabric_per_fold) qty = Number(item.fabric_folds) * Number(item.fabric_per_fold) / 100;'
)
c = c.replace(
    'const computedLinear = needsLinear && item.fabric_folds && item.fabric_per_fold ? Number(item.fabric_folds) * Number(item.fabric_per_fold) : null;',
    'const computedLinear = needsLinear && item.fabric_folds && item.fabric_per_fold ? Number(item.fabric_folds) * Number(item.fabric_per_fold) / 100 : null;'
)

# P6: BatchModal dropdown direction — up→down
c = c.replace(
    'className="absolute z-20 bottom-full left-0 right-0 mb-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-56 overflow-hidden flex flex-col"',
    'className="absolute z-20 top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-72 overflow-hidden flex flex-col"'
)

# P7: DecimalInput component + replace decimal inputs
if 'function DecimalInput' not in c:
    DECIMAL_COMPONENT = (
        '// Campo decimal com suporte a vírgula como separador (resolve bug de zero persistente no mobile)\n'
        'function DecimalInput({ value, defaultValue: def, onChange: onChangeProp, className, disabled, ...rest }) {\n'
        '  const toStr = (v) => (v != null && !isNaN(v) ? String(v) : (def != null ? String(def) : \'\'));\n'
        '  const [raw, setRaw] = React.useState(() => toStr(value));\n'
        '  const lastParent = React.useRef(value);\n'
        '  React.useEffect(() => {\n'
        '    if (value !== lastParent.current) {\n'
        '      lastParent.current = value;\n'
        '      setRaw(toStr(value));\n'
        '    }\n'
        '  // eslint-disable-next-line\n'
        '  }, [value]);\n'
        '  return (\n'
        '    <input\n'
        '      type="text"\n'
        '      inputMode="decimal"\n'
        '      value={raw}\n'
        '      onChange={(e) => {\n'
        '        const txt = e.target.value;\n'
        '        setRaw(txt);\n'
        '        const v = parseFloat(txt.replace(\',\', \'.\'));\n'
        '        if (!isNaN(v)) onChangeProp(v);\n'
        '      }}\n'
        '      onBlur={(e) => {\n'
        '        const v = parseFloat(e.target.value.replace(\',\', \'.\'));\n'
        '        const fallback = def != null ? def : 0;\n'
        '        const final = isNaN(v) ? fallback : v;\n'
        '        lastParent.current = final;\n'
        '        setRaw(String(final));\n'
        '        onChangeProp(final);\n'
        '      }}\n'
        '      onFocus={(e) => e.target.select()}\n'
        '      disabled={disabled}\n'
        '      className={className}\n'
        '      {...rest}\n'
        '    />\n'
        '  );\n'
        '}\n'
        '\n'
    )
    c = c.replace('// Sub-form para um item individual\n', DECIMAL_COMPONENT + '// Sub-form para um item individual\n', 1)

# unit_price: replace full <input .../> block
c = c.replace(
    '<input\n              type="number" step="0.01"\n              value={item.unit_price || \'\'}\n              onChange={(e) => onChange({ ...item, unit_price: Number(e.target.value) })}\n              onFocus={(e) => e.target.select()} className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm"\n            />',
    '<DecimalInput value={item.unit_price || 0} defaultValue={0}\n              onChange={(v) => onChange({ ...item, unit_price: v })}\n              className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />'
)
# width
c = c.replace(
    '<input type="number" step="0.01" value={item.width || \'\'}\n                onChange={(e) => onChange({ ...item, width: Number(e.target.value) })}\n                onFocus={(e) => e.target.select()} className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />',
    '<DecimalInput value={item.width || 0} defaultValue={0}\n                onChange={(v) => onChange({ ...item, width: v })}\n                className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />'
)
# height
c = c.replace(
    '<input type="number" step="0.01" value={item.height || \'\'}\n                onChange={(e) => onChange({ ...item, height: Number(e.target.value) })}\n                onFocus={(e) => e.target.select()} className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />',
    '<DecimalInput value={item.height || 0} defaultValue={0}\n                onChange={(v) => onChange({ ...item, height: v })}\n                className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />'
)
# fabric_per_fold
c = c.replace(
    '<input type="number" step="0.01" value={item.fabric_per_fold ?? 18}\n                onChange={(e) => onChange({ ...item, fabric_per_fold: Number(e.target.value) })}\n                onFocus={(e) => e.target.select()} className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />',
    '<DecimalInput value={item.fabric_per_fold ?? 18} defaultValue={18}\n                onChange={(v) => onChange({ ...item, fabric_per_fold: v })}\n                className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />'
)
# diameter
c = c.replace(
    '<input type="number" step="0.01" value={item.diameter || \'\'}\n              onChange={(e) => onChange({ ...item, diameter: Number(e.target.value) })}\n              onFocus={(e) => e.target.select()} className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />',
    '<DecimalInput value={item.diameter || 0} defaultValue={0}\n              onChange={(v) => onChange({ ...item, diameter: v })}\n              className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />'
)

# P8: Send button — labeled green button
c = c.replace(
    '            className="p-2 hover:bg-green-50 text-green-600 rounded-lg"\n          >\n            <Send className="w-5 h-5" />\n          </button>',
    '            className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs font-semibold rounded-lg"\n          >\n            <Send className="w-3.5 h-3.5" />\n            Enviar\n          </button>'
)

# P9: UI visual differentiation (subtle)
c = c.replace(
    'className="flex items-center justify-between px-4 py-3 border-b border-gray-200 sticky top-0 bg-white z-10"',
    'className="flex items-center justify-between px-4 py-3 border-b-2 border-blue-600 sticky top-0 bg-white z-10"'
)
c = c.replace(
    'className="px-4 py-2 border-b border-gray-100 bg-gray-50 flex gap-2 overflow-x-auto"',
    'className="px-4 py-2 border-b border-blue-100 bg-blue-50 flex gap-2 overflow-x-auto"'
)
c = c.replace(
    'className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3">',
    'className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3 bg-gray-50">'
)

with open(path, 'w') as f:
    f.write(c)

with open(path, 'r') as f:
    v = f.read()
checks = [
    'MessageSquare', 'sendPanel', 'openSendPanel', 'Painel "Enviar',
    'Dobras</label>', 'Tecido/dobra (cm)', '/ 100;',
    'top-full left-0 right-0 mt-1', 'max-h-72',
    'function DecimalInput', 'DecimalInput value={item.unit_price',
    'DecimalInput value={item.width', 'DecimalInput value={item.fabric_per_fold',
    'DecimalInput value={item.diameter',
    'bg-green-600 hover:bg-green-700',
    'border-b-2 border-blue-600',
    'bg-blue-50', 'bg-gray-50">',
]
missing = [x for x in checks if x not in v]
print('BEDITOR_OK' if not missing else 'BEDITOR_FAIL: missing=' + str(missing))

# ─── server.py ──────────────────────────────────────────────────────────────
spath = '/home/opc/superdry/backend/server.py'
with open(spath, 'r') as f:
    s = f.read()

# PS1: _condense_risk helper (idempotent)
if '_condense_risk' not in s:
    s = s.replace(
        '# Utility functions for text formatting\ndef format_whatsapp_text',
        (
            '# Condensa o texto de risco para a mensagem do WhatsApp (primeira frase, max 200 chars)\n'
            'def _condense_risk(text: str, max_len: int = 200) -> str:\n'
            '    if not text:\n'
            '        return ""\n'
            '    text = text.strip()\n'
            '    m = re.search(r\'[.!?\\n]\', text[:max_len + 30])\n'
            '    snippet = text[:m.start()].strip() if m else text[:max_len].strip()\n'
            '    if len(snippet) > max_len:\n'
            '        snippet = snippet[:max_len - 3] + \'...\'\n'
            '    return snippet\n'
            '\n'
            '# Utility functions for text formatting\n'
            'def format_whatsapp_text'
        )
    )

# PS2: add risk summary block to WhatsApp endpoint (idempotent)
if '_CAT_TO_RISK_WA' not in s:
    RISK_BLOCK = (
        '        # Avisos condensados por categoria (extraídos do BudgetConfig)\n'
        '        budget_cfg = await db.budget_config.find_one({}) or {}\n'
        '        _CAT_TO_RISK_WA = {\n'
        "            'ESTOFADOS':                    ('risks_estofados',              '\U0001f6cb️ Estofados'),\n"
        "            'COLCHOES':                     ('risks_colchoes',               '\U0001f6cf️ Colchões'),\n"
        "            'BOX':                          ('risks_box',                    '\U0001f6cf️ Box'),\n"
        "            'TAPETES':                      ('risks_tapetes',                '\U0001f5de️ Tapetes'),\n"
        "            'CARPETES_E_TAPETES_NO_LOCAL':  ('risks_carpetes_tapetes_local', '\U0001f9f9 Carpetes/local'),\n"
        "            'CORTINAS':                     ('risks_cortinas',               '\U0001f4dc Cortinas'),\n"
        "            'PERSIANAS':                    ('risks_persianas',              '\U0001fa9f Persianas'),\n"
        "            'ITENS_INFANTIS':               ('risks_itens_infantis',         '\U0001f6d2 Itens Infantis'),\n"
        "            'VEICULOS':                     ('risks_veiculos',               '\U0001f697 Veículos'),\n"
        "            'IMPERMEABILIZACAO':            ('risks_impermeabilizacao',      '\U0001f4a6 Impermeabilização'),\n"
        "            'OUTROS_ITENS':                 ('risks_outros_itens',           '\U0001f4e6 Outros'),\n"
        '        }\n'
        "        cats_seen = {itm.get('service_category') for itm in budget.get('items', []) if itm.get('service_category')}\n"
        '        risk_lines = []\n'
        '        for cat in sorted(cats_seen):\n'
        '            if cat in _CAT_TO_RISK_WA:\n'
        '                rk, label = _CAT_TO_RISK_WA[cat]\n'
        "                condensed = _condense_risk(budget_cfg.get(rk, '') or '')\n"
        '                if condensed:\n'
        "                    risk_lines.append(f'⚠️ *{label}:* _{condensed}_')\n"
        '        if risk_lines:\n'
        "            message += '\\n\\n*\u26a0\ufe0f Avisos importantes:*\\n' + '\\n'.join(risk_lines)\n"
        '\n'
        '        # Link público do PDF (servido pelo backend via Tailscale Funnel ou servidor de produção)\n'
    )
    s = s.replace(
        '        # Link público do PDF (servido pelo backend via Tailscale Funnel ou servidor de produção)\n',
        RISK_BLOCK
    )

with open(spath, 'w') as f:
    f.write(s)

with open(spath, 'r') as f:
    sv = f.read()
schecks = ['_condense_risk', '_CAT_TO_RISK_WA']
smissing = [x for x in schecks if x not in sv]
print('SERVER_OK' if not smissing else 'SERVER_FAIL: missing=' + str(smissing))
