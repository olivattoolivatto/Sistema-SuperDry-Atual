import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  X, Save, Plus, Trash2, ChevronDown, ChevronUp, Loader2, MapPin,
  Calendar, User as UserIcon, CreditCard, FileText, Search, AlertCircle, Copy,
} from 'lucide-react';
import { clientsApi, servicesApi, placesApi, budgetsApi, usersApi } from '../../services/api';
import { BACKEND_URL } from '../../lib/backendUrl';
import { useAuth } from '../../contexts/AuthContext';
import {
  EXECUTION_MODES, EXEC_MODE_TO_STATUS, PAYMENT_METHODS,
  fmtMoney, normalize,
} from './_constants';

// Mini autocomplete reaproveitando o padrão da página Clientes
function AddressAutocomplete({ value, onSelect, placeholder, compact = false }) {
  const [query, setQuery] = useState(value || '');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debRef = useRef(null);
  const boxRef = useRef(null);

  useEffect(() => { setQuery(value || ''); }, [value]);

  useEffect(() => {
    if (debRef.current) clearTimeout(debRef.current);
    if (!query || query.length < 3) { setResults([]); setOpen(false); return; }
    debRef.current = setTimeout(async () => {
      try {
        setLoading(true);
        const r = await placesApi.search(query);
        setResults(r.data?.results || []);
        setOpen(true);
      } catch (e) { setResults([]); }
      finally { setLoading(false); }
    }, 350);
  }, [query]);

  useEffect(() => {
    const onClick = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const handleChoose = async (p) => {
    setOpen(false);
    setQuery(p.description || '');
    let lat = p?.geometry?.location?.lat;
    let lng = p?.geometry?.location?.lng;
    let neighborhood = p?.neighborhood;
    let city = p?.city;
    let state = p?.state;
    let fullAddress = p.description || '';
    if ((!lat || !lng || !neighborhood || !city || !state) && p.place_id) {
      try {
        const det = await placesApi.getDetails(p.place_id);
        const d = det.data?.details?.result || det.data?.details || {};
        fullAddress = d.formatted_address || fullAddress;
        const geo = d.geometry?.location;
        if (geo) { lat = geo.lat; lng = geo.lng; }
        (d.address_components || []).forEach((c) => {
          const t = c.types || [];
          if (t.includes('sublocality') || t.includes('neighborhood') || t.includes('sublocality_level_1')) neighborhood = c.long_name;
          if (t.includes('administrative_area_level_2') || t.includes('locality')) city = c.long_name;
          if (t.includes('administrative_area_level_1')) state = c.short_name || c.long_name;
        });
      } catch (e) { /* ignore */ }
    }
    onSelect({
      full_address: fullAddress, neighborhood: neighborhood || '',
      city: city || '', state: state || '',
      latitude: lat || null, longitude: lng || null,
    });
  };

  return (
    <div className="relative" ref={boxRef}>
      <div className="relative">
        <MapPin className={`w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400`} />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          placeholder={placeholder || 'Buscar endereço…'}
          className={`w-full pl-9 pr-9 ${compact ? 'py-2' : 'py-2.5'} border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm`}
        />
        {loading && <Loader2 className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 animate-spin" />}
      </div>
      {open && results.length > 0 && (
        <ul className="absolute z-30 mt-1 w-full max-h-60 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-lg">
          {results.slice(0, 10).map((p) => (
            <li
              key={p.place_id || p.description}
              onClick={() => handleChoose(p)}
              className="px-3 py-2 hover:bg-blue-50 cursor-pointer text-sm border-b border-gray-100 last:border-0"
            >
              <div className="font-medium text-gray-900 truncate">{p.structured_formatting?.main_text || p.description}</div>
              <div className="text-xs text-gray-500 truncate">{p.structured_formatting?.secondary_text || ''}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// Sub-form para um item individual
function ItemSubForm({ item, services, onChange, onRemove, onDuplicate, idx, paymentMethods = PAYMENT_METHODS, salespersons = [] }) {
  const [showAdvanced, setShowAdvanced] = useState(
    !!(item.pickup_address || item.execution_address || item.delivery_address)
  );
  const [serviceSearch, setServiceSearch] = useState('');
  const [showServicePicker, setShowServicePicker] = useState(false);

  const filteredServices = useMemo(() => {
    const q = normalize(serviceSearch);
    return services.filter(s => s.is_active !== false && (
      !q || normalize(s.name).includes(q) || normalize(s.id).includes(q) ||
      normalize(s.category || '').includes(q)
    )).slice(0, 30);
  }, [services, serviceSearch]);

  const selectService = (s) => {
    // Serviços de parceiro → CLIENTE_TROUXE automaticamente
    const isParceiro = /parceiro/i.test(s.name);
    const execMode = isParceiro ? 'CLIENTE_TROUXE'
      : s.execution_location === 'NO_LOCAL' ? 'EXECUTAR_NO_LOCAL'
      : s.execution_location === 'CLIENTE_TROUXE' ? 'CLIENTE_TROUXE'
      : 'RETIRAR_E_LEVAR';
    onChange({
      ...item,
      service_id: s.id,
      service_name: s.name,
      service_code: s.id,
      service_category: s.category,
      measure_type: s.measure_type,
      execution_location: s.execution_location,
      unit_price: s.sale_price || 0,
      status: isParceiro ? 'CLIENTE_TROUXE' : (s.default_service_status || 'RETIRAR'),
      execution_mode: execMode,
    });
    setShowServicePicker(false);
    setServiceSearch('');
  };

  const measureType = item.measure_type;
  const needsArea = ['AREA_DE_TAPETE', 'CARPETE_TAPETE_LOCAL', 'AREA_PERSIANA'].includes(measureType);
  const needsLinear = ['METRAGEM_LINEAR_CORTINA_SIMPLES', 'METRAGEM_LINEAR_PE_DIREITO_DUPLO', 'METRAGEM_LINEAR_ESPECIAL'].includes(measureType);
  const needsDiameter = measureType === 'TAPETE_REDONDO_DIAMETRO';

  // Calcula total_value automaticamente
  useEffect(() => {
    let qty = Number(item.quantity || 1);
    if (needsArea && item.width && item.height) qty = Number(item.width) * Number(item.height);
    if (needsLinear && item.fabric_folds && item.fabric_per_fold) qty = Number(item.fabric_folds) * Number(item.fabric_per_fold);
    if (needsDiameter && item.diameter) qty = Math.PI * Math.pow(Number(item.diameter) / 2, 2);
    const total = qty * Number(item.unit_price || 0);
    const computedAreaM2 = needsArea && item.width && item.height ? Number(item.width) * Number(item.height) : null;
    const computedLinear = needsLinear && item.fabric_folds && item.fabric_per_fold ? Number(item.fabric_folds) * Number(item.fabric_per_fold) : null;
    if (Math.abs((item.total_value || 0) - total) > 0.001 ||
        (computedAreaM2 !== null && item.area_m2 !== computedAreaM2) ||
        (computedLinear !== null && item.linear_meters !== computedLinear)) {
      onChange({
        ...item,
        quantity: qty,
        total_value: total,
        area_m2: computedAreaM2 ?? item.area_m2,
        linear_meters: computedLinear ?? item.linear_meters,
      });
    }
    // eslint-disable-next-line
  }, [item.unit_price, item.width, item.height, item.diameter, item.fabric_folds, item.fabric_per_fold, item.quantity, measureType]);

  return (
    <div className="bg-gray-50 rounded-xl border border-gray-200 overflow-hidden">
      <div className="bg-blue-600 text-white px-3 py-2 flex items-center justify-between">
        <div className="text-sm font-semibold flex items-center gap-2">
          Item #{idx + 1}{item.service_name ? ` — ${item.service_name}` : ''}
          {(item.pickup_address || item.execution_address || item.delivery_address) && (
            <span className="inline-flex items-center gap-0.5 text-[10px] bg-white/20 px-1.5 py-0.5 rounded-full font-normal">
              <MapPin className="w-3 h-3" /> endereço próprio
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {onDuplicate && (
            <button onClick={onDuplicate} className="p-1 hover:bg-white/20 rounded" title="Duplicar para outro endereço">
              <Copy className="w-4 h-4" />
            </button>
          )}
          <button onClick={onRemove} className="p-1 hover:bg-white/20 rounded" title="Remover item">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="p-3 space-y-3">
        {/* Serviço */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Serviço *</label>
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowServicePicker(v => !v)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-left flex items-center justify-between"
            >
              <span className={item.service_id ? 'text-gray-900' : 'text-gray-400'}>
                {item.service_name || 'Selecionar serviço…'}
              </span>
              <ChevronDown className="w-4 h-4 text-gray-400" />
            </button>
            {showServicePicker && (
              <div className="absolute z-20 top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-72 overflow-hidden flex flex-col">
                <div className="p-2 border-b border-gray-100">
                  <div className="relative">
                    <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      value={serviceSearch}
                      onChange={e => setServiceSearch(e.target.value)}
                      placeholder="Buscar serviço…"
                      className="w-full pl-8 pr-2 py-1.5 text-sm border border-gray-200 rounded-md"
                      autoFocus
                    />
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto">
                  {filteredServices.length === 0 && (
                    <div className="p-3 text-sm text-gray-500 text-center">Nenhum serviço encontrado.</div>
                  )}
                  {filteredServices.map(s => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => selectService(s)}
                      className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm border-b border-gray-100 last:border-0"
                    >
                      <div className="font-medium text-gray-900">{s.name}</div>
                      <div className="text-xs text-gray-500 flex justify-between">
                        <span>{s.id} • {s.category}</span>
                        <span className="text-blue-700 font-semibold">{fmtMoney(s.sale_price)}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Medidas dinâmicas */}
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Qtd</label>
            <input
              type="number"
              step="0.01"
              value={item.quantity || ''}
              onChange={(e) => onChange({ ...item, quantity: Number(e.target.value) || 1 })}
              disabled={needsArea || needsLinear || needsDiameter}
              onFocus={(e) => e.target.select()} className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm disabled:bg-gray-100"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Valor unit.</label>
            <input
              type="number" step="0.01"
              value={item.unit_price || ''}
              onChange={(e) => onChange({ ...item, unit_price: Number(e.target.value) })}
              onFocus={(e) => e.target.select()} className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Total</label>
            <div className="px-2 py-2 border border-emerald-200 bg-emerald-50 rounded-lg text-sm font-bold text-emerald-700">
              {fmtMoney(item.total_value)}
            </div>
          </div>
        </div>

        {/* Campos por tipo de medida */}
        {needsArea && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Largura (m)</label>
              <input type="number" step="0.01" value={item.width || ''}
                onChange={(e) => onChange({ ...item, width: Number(e.target.value) })}
                onFocus={(e) => e.target.select()} className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Altura (m)</label>
              <input type="number" step="0.01" value={item.height || ''}
                onChange={(e) => onChange({ ...item, height: Number(e.target.value) })}
                onFocus={(e) => e.target.select()} className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />
            </div>
          </div>
        )}
        {needsLinear && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Varões</label>
              <input type="number" value={item.fabric_folds || ''}
                onChange={(e) => onChange({ ...item, fabric_folds: Number(e.target.value) })}
                onFocus={(e) => e.target.select()} className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Tecido/varão (m)</label>
              <input type="number" step="0.01" value={item.fabric_per_fold ?? 18}
                onChange={(e) => onChange({ ...item, fabric_per_fold: Number(e.target.value) })}
                onFocus={(e) => e.target.select()} className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />
            </div>
          </div>
        )}
        {needsDiameter && (
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Diâmetro (m)</label>
            <input type="number" step="0.01" value={item.diameter || ''}
              onChange={(e) => onChange({ ...item, diameter: Number(e.target.value) })}
              onFocus={(e) => e.target.select()} className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>
        )}

        {/* Modo de execução */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Modo de execução</label>
          <select
            value={item.execution_mode || 'RETIRAR_E_LEVAR'}
            onChange={(e) => {
              const mode = e.target.value;
              onChange({
                ...item,
                execution_mode: mode,
                status: EXEC_MODE_TO_STATUS[mode] || item.status,
              });
            }}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
          >
            {EXECUTION_MODES.map(m => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
          <div className="text-[11px] text-gray-500 mt-1">
            {EXECUTION_MODES.find(m => m.value === (item.execution_mode || 'RETIRAR_E_LEVAR'))?.desc}
          </div>
        </div>

        {/* Observações */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Observações do item</label>
          <textarea
            value={item.observations || ''}
            onChange={(e) => onChange({ ...item, observations: e.target.value })}
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
        </div>

        {/* Avançado: endereços + datas + retoque */}
        <button
          type="button"
          onClick={() => setShowAdvanced(v => !v)}
          className="w-full flex items-center justify-between text-xs font-medium text-blue-700 py-1.5"
        >
          <span>Opções avançadas (endereços, datas, retoque)</span>
          {showAdvanced ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>

        {showAdvanced && (
          <div className="space-y-3 border-t border-gray-200 pt-3">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={!!item.is_retoque}
                onChange={(e) => onChange({ ...item, is_retoque: e.target.checked })} />
              É retoque
            </label>

            {/* Endereços específicos por etapa */}
            {['RETIRAR_E_LEVAR', 'EXECUTAR_NO_LOCAL'].includes(item.execution_mode || 'RETIRAR_E_LEVAR') && (() => {
              const isExec = item.execution_mode === 'EXECUTAR_NO_LOCAL';
              const field = isExec ? 'execution_address' : 'pickup_address';
              const addr = item[field];
              return (
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    {isExec ? 'Endereço de execução' : 'Endereço de retirada'} (override)
                  </label>
                  <AddressAutocomplete
                    compact
                    value={addr?.full_address || ''}
                    onSelect={(a) => onChange({ ...item, [field]: { ...a, complement: addr?.complement || '' } })}
                    placeholder="Padrão = endereço do cliente"
                  />
                  {addr?.full_address && (
                    <input
                      value={addr.complement || ''}
                      onChange={(e) => onChange({ ...item, [field]: { ...addr, complement: e.target.value } })}
                      placeholder="Complemento (apto, bloco, quadra, lote…)"
                      className="w-full mt-1 px-3 py-1.5 border border-gray-300 rounded-lg text-xs"
                    />
                  )}
                </div>
              );
            })()}
            {['RETIRAR_E_LEVAR', 'CLIENTE_TROUXE'].includes(item.execution_mode || 'RETIRAR_E_LEVAR') && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Endereço de entrega (override)</label>
                <AddressAutocomplete
                  compact
                  value={item.delivery_address?.full_address || ''}
                  onSelect={(a) => onChange({ ...item, delivery_address: { ...a, complement: item.delivery_address?.complement || '' } })}
                  placeholder="Padrão = endereço do cliente"
                />
                {item.delivery_address?.full_address && (
                  <input
                    value={item.delivery_address.complement || ''}
                    onChange={(e) => onChange({ ...item, delivery_address: { ...item.delivery_address, complement: e.target.value } })}
                    placeholder="Complemento (apto, bloco, quadra, lote…)"
                    className="w-full mt-1 px-3 py-1.5 border border-gray-300 rounded-lg text-xs"
                  />
                )}
              </div>
            )}

            {/* Datas planejadas */}
            <div className="grid grid-cols-2 gap-2">
              {item.execution_mode === 'RETIRAR_E_LEVAR' && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Data retirada</label>
                    <input type="date" value={item.scheduled_pickup_date || ''}
                      onChange={(e) => onChange({ ...item, scheduled_pickup_date: e.target.value })}
                      className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Hora retirada</label>
                    <input type="time" value={item.scheduled_pickup_time || ''}
                      onChange={(e) => onChange({ ...item, scheduled_pickup_time: e.target.value })}
                      className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />
                  </div>
                </>
              )}
              {(item.execution_mode === 'EXECUTAR_NO_LOCAL' || !item.execution_mode) && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Data execução</label>
                    <input type="date" value={item.scheduled_execution_date || ''}
                      onChange={(e) => onChange({ ...item, scheduled_execution_date: e.target.value })}
                      className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Hora execução</label>
                    <input type="time" value={item.scheduled_execution_time || ''}
                      onChange={(e) => onChange({ ...item, scheduled_execution_time: e.target.value })}
                      className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />
                  </div>
                </>
              )}
              {['RETIRAR_E_LEVAR', 'CLIENTE_TROUXE'].includes(item.execution_mode || 'RETIRAR_E_LEVAR') && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Data entrega</label>
                    <input type="date" value={item.scheduled_delivery_date || ''}
                      onChange={(e) => onChange({ ...item, scheduled_delivery_date: e.target.value })}
                      className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Hora entrega</label>
                    <input type="time" value={item.scheduled_delivery_time || ''}
                      onChange={(e) => onChange({ ...item, scheduled_delivery_time: e.target.value })}
                      className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm" />
                  </div>
                </>
              )}
            </div>

            {/* Override de pagamento */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Método de pagamento (override)
              </label>
              <select
                value={item.payment_method || ''}
                onChange={(e) => onChange({ ...item, payment_method: e.target.value || null })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
              >
                <option value="">Herdar do orçamento</option>
                {PAYMENT_METHODS.map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>
          </div>
        )}

        {/* Comissão do técnico */}
        <div className="mt-3 border-t border-gray-100 pt-3">
          <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
            <input
              type="checkbox"
              checked={!!item.commission_enabled}
              onChange={e => onChange({ ...item, commission_enabled: e.target.checked,
                commission_user_id: e.target.checked ? item.commission_user_id : null,
                commission_user_name: e.target.checked ? item.commission_user_name : null,
                commission_pct: e.target.checked ? item.commission_pct : null,
              })}
              className="h-4 w-4 text-indigo-600 rounded"
            />
            <span className="font-medium text-gray-700">Comissão do Técnico</span>
          </label>
          {item.commission_enabled && (
            <div className="mt-2 grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-gray-500 mb-0.5">Técnico / Usuário</label>
                <select
                  value={item.commission_user_id || ''}
                  onChange={e => {
                    const sp = salespersons.find(s => s.id === e.target.value);
                    onChange({ ...item,
                      commission_user_id: e.target.value || null,
                      commission_user_name: sp ? (sp.display_name || sp.name) : null,
                    });
                  }}
                  className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-xs bg-white"
                >
                  <option value="">Selecione…</option>
                  {salespersons.map(s => (
                    <option key={s.id} value={s.id}>{s.display_name || s.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-0.5">% Comissão</label>
                <div className="flex items-center gap-1">
                  <input
                    type="number" min={0} max={100} step={0.5}
                    value={item.commission_pct ?? ''}
                    onChange={e => onChange({ ...item, commission_pct: e.target.value ? parseFloat(e.target.value) : null })}
                    placeholder="0"
                    onFocus={(e) => e.target.select()} className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-xs"
                  />
                  <span className="text-xs text-gray-500 shrink-0">%</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const newEmptyItem = () => ({
  id: undefined, // gerado pelo backend
  service_id: '',
  service_name: '',
  service_code: '',
  measure_type: '',
  quantity: 1,
  unit_price: 0,
  total_value: 0,
  area_m2: null,
  linear_meters: null,
  execution_location: 'RETIRADA',
  execution_mode: 'RETIRAR_E_LEVAR',
  status: 'RETIRAR',
  observations: '',
  is_retoque: false,
  pickup_address: null,
  execution_address: null,
  delivery_address: null,
  scheduled_pickup_date: '',
  scheduled_pickup_time: '',
  scheduled_execution_date: '',
  scheduled_execution_time: '',
  scheduled_delivery_date: '',
  scheduled_delivery_time: '',
  payment_method: null,
});

// ── Lançamento em Lote ────────────────────────────────────────────────────────
function BatchModal({ services, onClose, onAdd }) {
  const [serviceId, setServiceId] = useState('');
  const [serviceName, setServiceName] = useState('');
  const [qty, setQty] = useState(1);
  const [unitPrice, setUnitPrice] = useState(0);
  const [execMode, setExecMode] = useState('RETIRAR_E_LEVAR');
  const [observations, setObservations] = useState('');
  const [useGenericName, setUseGenericName] = useState(false);
  const [genericName, setGenericName] = useState('Tapete');

  // Regra: nome genérico = parceiro → modo de execução CLIENTE_TROUXE automaticamente
  const handleGenericToggle = (checked) => {
    setUseGenericName(checked);
    if (checked) setExecMode('CLIENTE_TROUXE');
  };
  const [serviceSearch, setServiceSearch] = useState('');
  const [showServicePicker, setShowServicePicker] = useState(false);

  const selectedSvc = services.find(s => s.id === serviceId);

  const filteredServices = useMemo(() => {
    const q = normalize(serviceSearch);
    return services.filter(s => s.is_active !== false && (
      !q || normalize(s.name).includes(q) || normalize(s.id).includes(q) ||
      normalize(s.category || '').includes(q)
    )).slice(0, 30);
  }, [services, serviceSearch]);

  const selectService = (svc) => {
    setServiceId(svc.id);
    setServiceName(svc.name);
    setUnitPrice(svc.sale_price || 0);
    // Serviços de parceiro (nome contém "parceiro") → CLIENTE_TROUXE automaticamente
    const isParceiro = /parceiro/i.test(svc.name);
    if (isParceiro) {
      setExecMode('CLIENTE_TROUXE');
    } else if (svc.execution_location === 'NO_LOCAL') {
      setExecMode('EXECUTAR_NO_LOCAL');
    } else if (svc.execution_location === 'CLIENTE_TROUXE') {
      setExecMode('CLIENTE_TROUXE');
    } else {
      setExecMode('RETIRAR_E_LEVAR');
    }
    setShowServicePicker(false);
    setServiceSearch('');
  };

  const generate = () => {
    if (!serviceId && !useGenericName) return;
    const name = useGenericName ? genericName : (selectedSvc?.name || serviceName);
    const code = selectedSvc?.id || 'GEN';
    const price = parseFloat(unitPrice) || 0;
    const items = Array.from({ length: qty }, (_, i) => ({
      id: undefined,
      service_id: serviceId || '',
      service_name: name,
      service_code: code,
      measure_type: selectedSvc?.measure_type || 'UNITARIO',
      quantity: 1,
      unit_price: price,
      total_value: price,
      area_m2: null,
      linear_meters: null,
      execution_location: execMode === 'EXECUTAR_NO_LOCAL' ? 'NO_LOCAL'
        : execMode === 'CLIENTE_TROUXE' || execMode === 'CLIENTE_LEVARA' ? 'CLIENTE_TROUXE'
        : 'RETIRADA',
      execution_mode: execMode,
      status: EXEC_MODE_TO_STATUS[execMode] || 'RETIRAR',
      observations: observations || '',
      is_retoque: false,
      pickup_address: null, execution_address: null, delivery_address: null,
      scheduled_pickup_date: '', scheduled_pickup_time: '',
      scheduled_execution_date: '', scheduled_execution_time: '',
      scheduled_delivery_date: '', scheduled_delivery_time: '',
      payment_method: null,
    }));
    onAdd(items);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center p-4"
      style={{ alignItems: 'flex-end' }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md"
        style={{ maxHeight: 'min(70dvh, 70vh)', overflowY: 'auto' }}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 sticky top-0 bg-white z-10">
          <h3 className="font-semibold text-gray-900">Lançamento em Lote</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <div className="px-5 py-4 space-y-4">
          {/* Modo genérico para parceiros */}
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={useGenericName} onChange={e => handleGenericToggle(e.target.checked)} />
            <span>Usar nome genérico (registro de parceiro)</span>
          </label>

          {useGenericName ? (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Nome do item</label>
              <input value={genericName} onChange={e => setGenericName(e.target.value)}
                placeholder="Ex: Tapete, Sofá, etc."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            </div>
          ) : (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Serviço</label>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setShowServicePicker(v => !v)}
                  className="w-full flex items-center justify-between px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-left"
                >
                  <span className={serviceId ? 'text-gray-900' : 'text-gray-400'}>
                    {selectedSvc?.name || 'Buscar serviço…'}
                  </span>
                  <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
                </button>
                {showServicePicker && (
                  <div className="absolute z-20 bottom-full left-0 right-0 mb-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-56 overflow-hidden flex flex-col">
                    <div className="p-2 border-b border-gray-100">
                      <div className="relative">
                        <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                          value={serviceSearch}
                          onChange={e => setServiceSearch(e.target.value)}
                          placeholder="Buscar serviço…"
                          className="w-full pl-8 pr-2 py-1.5 text-sm border border-gray-200 rounded-md"
                          autoFocus
                        />
                      </div>
                    </div>
                    <div className="flex-1 overflow-y-auto">
                      {filteredServices.length === 0 && (
                        <div className="p-3 text-sm text-gray-500 text-center">Nenhum serviço encontrado.</div>
                      )}
                      {filteredServices.map(s => (
                        <button
                          key={s.id}
                          type="button"
                          onClick={() => selectService(s)}
                          className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm border-b border-gray-100 last:border-0"
                        >
                          <div className="font-medium text-gray-900">{s.name}</div>
                          <div className="text-xs text-gray-500 flex justify-between">
                            <span>{s.id} • {s.category}</span>
                            <span className="text-blue-700 font-semibold">{fmtMoney(s.sale_price)}</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Quantidade</label>
              <input type="number" min={1} max={100} value={qty}
                onChange={e => setQty(Math.max(1, parseInt(e.target.value) || 1))}
                onFocus={(e) => e.target.select()} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Valor unitário (R$)</label>
              <input type="number" min={0} step="0.01" value={unitPrice}
                onChange={e => setUnitPrice(e.target.value)}
                onFocus={(e) => e.target.select()} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Modo de execução</label>
            <select value={execMode} onChange={e => setExecMode(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white">
              {EXECUTION_MODES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Observações (aplicada a todos)</label>
            <input value={observations} onChange={e => setObservations(e.target.value)}
              placeholder="Opcional"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>

          <div className="bg-orange-50 border border-orange-200 rounded-lg px-4 py-2 text-sm text-orange-800">
            Serão criados <strong>{qty}</strong> item(s) — total: <strong>R$ {(parseFloat(unitPrice || 0) * qty).toFixed(2)}</strong>
          </div>
        </div>
        <div className="flex gap-2 px-5 pb-5">
          <button onClick={onClose}
            className="flex-1 py-2.5 rounded-xl border border-gray-300 text-sm text-gray-700 hover:bg-gray-50">
            Cancelar
          </button>
          <button
            onClick={generate}
            disabled={!serviceId && !useGenericName}
            className="flex-1 py-2.5 rounded-xl bg-orange-500 text-white text-sm font-semibold hover:bg-orange-600 disabled:opacity-40">
            Gerar {qty} item(s)
          </button>
        </div>
      </div>
    </div>
  );
}

export default function BudgetEditor({ budget, onClose, onSaved, preselectedClient = null }) {
  const isEdit = Boolean(budget?.id);
  const { user: currentUser } = useAuth();
  const [clients, setClients] = useState([]);
  const [services, setServices] = useState([]);
  const [paymentMethods, setPaymentMethods] = useState(PAYMENT_METHODS);
  const [salespersons, setSalespersons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [clientSearch, setClientSearch] = useState('');
  const [batchOpen, setBatchOpen] = useState(false);
  // Cadastro rápido de cliente (inline na tela de orçamento)
  const [quickOpen, setQuickOpen] = useState(false);
  const [qcName, setQcName] = useState('');
  const [qcPhone, setQcPhone] = useState('');
  const [qcAddr, setQcAddr] = useState(null);       // objeto do AddressAutocomplete
  const [qcComplement, setQcComplement] = useState('');
  const [qcSaving, setQcSaving] = useState(false);
  const [form, setForm] = useState({
    client_id: budget?.client_id || preselectedClient?.id || '',
    client_name: budget?.client_name || preselectedClient?.name || '',
    payment_method: budget?.payment_method || '',
    salesperson: budget?.salesperson || currentUser?.display_name || currentUser?.name || '',
    internal_observations: budget?.internal_observations || '',
    budget_observations: budget?.budget_observations || '',
    items: budget?.items?.length ? budget.items : [],
  });
  // If preselectedClient provided, skip to step 2 directly
  const [step, setStep] = useState(preselectedClient ? 2 : 1);
  // Quando o usuário escolhe o método manualmente, paramos de sugerir automaticamente.
  const [paymentTouched, setPaymentTouched] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [c, s, pm, sp] = await Promise.all([
          clientsApi.getAll({ limit: 1000 }),
          servicesApi.getAll({ active_only: true }),
          fetch(`${BACKEND_URL}/api/payment-methods`).then(r => r.json()),
          usersApi.salespersons(),
        ]);
        setClients(c.data || []);
        setServices(s.data || []);
        const methods = pm.payment_methods || PAYMENT_METHODS;
        setPaymentMethods(methods);
        setSalespersons(sp.data || []);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, []);

  const filteredClients = useMemo(() => {
    const q = normalize(clientSearch);
    const digits = clientSearch.replace(/\D/g, '');
    if (!q) return clients.slice(0, 50);
    return clients.filter(c =>
      normalize(c.name).includes(q) ||
      normalize(c.id).includes(q) ||
      normalize(c.email || '').includes(q) ||
      (digits.length > 0 && (c.phone_primary || '').includes(digits))
    ).slice(0, 50);
  }, [clients, clientSearch]);

  const totals = useMemo(() => ({
    value: (form.items || []).reduce((acc, i) => acc + Number(i.total_value || 0), 0),
    units: (form.items || []).length,
    area: (form.items || []).reduce((acc, i) => acc + Number(i.area_m2 || 0), 0),
    linear: (form.items || []).reduce((acc, i) => acc + Number(i.linear_meters || 0), 0),
  }), [form.items]);

  // Condição de pagamento padrão = Cartão de Crédito, com parcelas pelo valor do
  // orçamento (até 200→2x, 300→3x, 400→4x, 500→5x, 600+→6x). Apenas sugestão:
  // some assim que o usuário escolhe outro método. O pagamento real é no Financeiro.
  useEffect(() => {
    if (budget?.payment_method) return;   // edição: respeita o método já salvo
    if (paymentTouched) return;           // usuário definiu manualmente
    if (!paymentMethods.length) return;
    const t = Math.round((totals.value || 0) * 100) / 100;
    const n = t <= 0 ? 1 : Math.min(6, Math.max(2, Math.ceil(t / 100)));
    const target = paymentMethods.find(m => m.value === `CREDITO_${n}X`)
                || paymentMethods.find(m => /credit|cr[eé]dito/i.test(`${m.value} ${m.label}`));
    if (target) {
      setForm(prev => prev.payment_method === target.value ? prev : { ...prev, payment_method: target.value });
    }
  }, [totals.value, paymentMethods, paymentTouched, budget]);

  const selectClient = (c) => {
    setForm(f => ({ ...f, client_id: c.id, client_name: c.name }));
    setClientSearch('');
    setStep(2);
  };

  // Cola texto do WhatsApp e extrai nome + telefone.
  // Remove chars Unicode invisíveis que o WhatsApp injeta (U+202A, U+202C, U+2011, etc.)
  // antes de checar o padrão de telefone — sem isso nonPhone.length fica > 2 e o número
  // é ignorado.
  const quickParsePaste = (text) => {
    const INVIS = /[​-‏‪-‮⁠-⁯﻿]/g;
    const lines = text.split('\n')
      .map(l => l.replace(INVIS, '').trim())
      .filter(Boolean);
    for (const line of lines) {
      const digits = line.replace(/\D/g, '');
      const nonPhone = line.replace(/[\d\s()+\-.]/g, '');
      if (!qcPhone && digits.length >= 8 && digits.length <= 13 && nonPhone.length <= 2) {
        setQcPhone(line);
      } else if (!qcName) {
        setQcName(line);
      }
    }
  };

  // Cria o cliente e já seleciona no orçamento
  const quickCreateClient = async () => {
    if (!qcName.trim()) { setError('Informe o nome do cliente.'); return; }
    if (!qcPhone.trim()) { setError('Informe o telefone do cliente.'); return; }
    setQcSaving(true);
    setError('');
    try {
      const address = {
        full_address: qcAddr?.full_address || '',
        neighborhood: qcAddr?.neighborhood || '',
        city: qcAddr?.city || '',
        state: qcAddr?.state || '',
        latitude: qcAddr?.latitude || null,
        longitude: qcAddr?.longitude || null,
        complement: qcComplement || '',
      };
      const r = await clientsApi.create({
        name: qcName.trim(), phone_primary: qcPhone.trim(), address,
      });
      const novo = r.data;
      setClients(prev => [novo, ...prev]);          // entra na lista local
      // limpa o form rápido
      setQuickOpen(false); setQcName(''); setQcPhone(''); setQcAddr(null); setQcComplement('');
      selectClient(novo);                            // já seleciona e avança para itens
    } catch (e) {
      setError(e.response?.data?.detail || 'Erro ao cadastrar cliente.');
    } finally { setQcSaving(false); }
  };

  const addItem = () => setForm(f => ({ ...f, items: [...(f.items || []), newEmptyItem()] }));
  const updateItem = (idx, newItem) => setForm(f => ({
    ...f,
    items: f.items.map((it, i) => i === idx ? newItem : it),
  }));
  const removeItem = (idx) => setForm(f => ({ ...f, items: f.items.filter((_, i) => i !== idx) }));
  // Duplica um item para outro endereço (mesmo serviço/medidas, endereços limpos)
  const duplicateItem = (idx) => setForm(f => {
    const orig = f.items[idx];
    const clone = {
      ...orig,
      id: undefined,                    // novo item — backend gera ID
      pickup_address: null,             // limpa endereços para forçar o novo
      execution_address: null,
      delivery_address: null,
      paid_value: 0,
      payment_status: 'PENDENTE',
      payment_records: [],
      status_history: [],
      execution_sessions: [],
      current_route_id: null,
      observations: orig.observations ? `${orig.observations} (2º endereço)` : '2º endereço',
    };
    const items = [...f.items];
    items.splice(idx + 1, 0, clone);
    return { ...f, items };
  });

  const save = async () => {
    setError('');
    if (!form.client_id) { setError('Selecione um cliente.'); setStep(1); return; }
    if (!form.items?.length) { setError('Adicione ao menos 1 item.'); setStep(2); return; }
    for (const [i, it] of form.items.entries()) {
      if (!it.service_id) { setError(`Item ${i+1}: selecione um serviço.`); setStep(2); return; }
      if (!it.unit_price) { setError(`Item ${i+1}: valor unitário é obrigatório.`); setStep(2); return; }
    }
    try {
      setSaving(true);
      const payload = {
        client_id: form.client_id,
        payment_method: form.payment_method,
        salesperson: form.salesperson,
        internal_observations: form.internal_observations,
        budget_observations: form.budget_observations,
        items: form.items,
      };
      const r = isEdit
        ? await budgetsApi.update(budget.id, payload)
        : await budgetsApi.create(payload);
      onSaved?.(r.data);
      onClose?.();
    } catch (e) {
      setError(e.response?.data?.detail || 'Erro ao salvar orçamento.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-white" />
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="bg-white w-full sm:max-w-3xl sm:rounded-2xl rounded-t-2xl shadow-2xl flex flex-col max-h-[96vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 sticky top-0 bg-white z-10">
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900 truncate">
              {isEdit ? `Editar Orçamento — ${budget.id}` : 'Novo Orçamento'}
            </h3>
            <p className="text-xs text-gray-500">
              {form.client_name ? `Cliente: ${form.client_name}` : 'Selecione o cliente para começar'}
            </p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Stepper */}
        <div className="px-4 py-2 border-b border-gray-100 bg-gray-50 flex gap-2 overflow-x-auto">
          {[
            { n: 1, label: 'Cliente', icon: UserIcon },
            { n: 2, label: `Itens (${form.items.length})`, icon: FileText },
            { n: 3, label: 'Cabeçalho', icon: CreditCard },
          ].map(s => {
            const Icon = s.icon;
            const active = step === s.n;
            return (
              <button
                key={s.n}
                onClick={() => setStep(s.n)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap ${
                  active ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border border-gray-200'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {s.n}. {s.label}
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3">
          {/* STEP 1: CLIENTE */}
          {step === 1 && (
            <div className="space-y-3">
              {/* Cadastro rápido de cliente */}
              <div className="border border-emerald-200 bg-emerald-50/50 rounded-lg">
                <button
                  onClick={() => setQuickOpen(v => !v)}
                  className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-emerald-700"
                >
                  <span className="flex items-center gap-1.5"><Plus className="w-4 h-4" /> Cadastrar novo cliente</span>
                  {quickOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {quickOpen && (
                  <div className="px-3 pb-3 space-y-2">
                    <div>
                      <label className="block text-[11px] text-gray-500 mb-0.5">Colar do WhatsApp (opcional)</label>
                      <textarea
                        rows={2}
                        onChange={(e) => quickParsePaste(e.target.value)}
                        placeholder="Cole nome + telefone e o sistema preenche abaixo…"
                        className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-xs"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        value={qcName} onChange={(e) => setQcName(e.target.value)}
                        placeholder="Nome *"
                        className="px-2 py-2 border border-gray-300 rounded-lg text-sm"
                      />
                      <input
                        value={qcPhone} onChange={(e) => setQcPhone(e.target.value)}
                        placeholder="Telefone *"
                        className="px-2 py-2 border border-gray-300 rounded-lg text-sm"
                      />
                    </div>
                    <AddressAutocomplete
                      value={qcAddr?.full_address || ''}
                      onSelect={setQcAddr}
                      placeholder="Endereço (opcional — pode adicionar depois)"
                      compact
                    />
                    <input
                      value={qcComplement} onChange={(e) => setQcComplement(e.target.value)}
                      placeholder="Complemento (condomínio, qd, lt, apto…)"
                      className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-xs"
                    />
                    <button
                      onClick={quickCreateClient}
                      disabled={qcSaving}
                      className="w-full py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {qcSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                      Cadastrar e usar no orçamento
                    </button>
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Buscar cliente</label>
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    value={clientSearch}
                    onChange={(e) => setClientSearch(e.target.value)}
                    placeholder="Nome, telefone, email…"
                    className="w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                    autoFocus
                  />
                </div>
              </div>

              <div className="text-xs text-gray-500">
                {clientSearch ? `${filteredClients.length} encontrado(s)` : `Mostrando ${filteredClients.length} de ${clients.length} clientes`}
              </div>
              <div className="space-y-2">
                {filteredClients.map(c => {
                  const selected = form.client_id === c.id;
                  return (
                    <button
                      key={c.id}
                      onClick={() => selectClient(c)}
                      className={`w-full text-left px-3 py-2 rounded-lg border transition ${
                        selected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="min-w-0">
                          <div className="font-medium text-gray-900 truncate">{c.name}</div>
                          <div className="text-xs text-gray-500">{c.id} • {c.phone_primary}</div>
                        </div>
                        {selected && <span className="text-xs text-blue-700 font-semibold">Selecionado</span>}
                      </div>
                    </button>
                  );
                })}
                {filteredClients.length === 0 && (
                  <div className="p-4 text-center text-sm text-gray-500 bg-gray-50 rounded-lg">
                    Nenhum cliente encontrado.{' '}
                    <button
                      onClick={() => setQuickOpen(true)}
                      className="text-emerald-600 font-medium hover:underline"
                    >
                      Cadastrar novo cliente
                    </button>{' '}
                    usando o painel acima.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* STEP 2: ITENS */}
          {step === 2 && (
            <div className="space-y-3">
              {/* Botões no TOPO — sempre visíveis sem precisar rolar */}
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={addItem}
                  className="flex-1 py-2.5 rounded-xl border-2 border-dashed border-blue-300 text-blue-600 hover:bg-blue-50 text-sm font-medium flex items-center justify-center gap-1"
                >
                  <Plus className="w-4 h-4" /> Adicionar Item
                </button>
                <button
                  type="button"
                  onClick={() => setBatchOpen(true)}
                  className="flex-1 py-2.5 rounded-xl border-2 border-dashed border-orange-300 text-orange-600 hover:bg-orange-50 text-sm font-medium flex items-center justify-center gap-1"
                >
                  <Plus className="w-4 h-4" /> Lançar em Lote
                </button>
              </div>
              {batchOpen && (
                <BatchModal
                  services={services}
                  onClose={() => setBatchOpen(false)}
                  onAdd={(newItems) => {
                    setForm(f => ({ ...f, items: [...(f.items || []), ...newItems] }));
                    setBatchOpen(false);
                  }}
                />
              )}
              {form.items.length === 0 && (
                <div className="p-6 text-center text-sm text-gray-500 bg-gray-50 rounded-xl">
                  <FileText className="w-10 h-10 mx-auto text-gray-300 mb-2" />
                  Nenhum item adicionado ainda.
                </div>
              )}
              {form.items.map((item, idx) => (
                <ItemSubForm
                  key={idx}
                  idx={idx}
                  item={item}
                  services={services}
                  paymentMethods={paymentMethods}
                  salespersons={salespersons}
                  onChange={(it) => updateItem(idx, it)}
                  onRemove={() => removeItem(idx)}
                  onDuplicate={() => duplicateItem(idx)}
                />
              ))}
            </div>
          )}

          {/* STEP 3: CABEÇALHO */}
          {step === 3 && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Vendedor</label>
                <select
                  value={form.salesperson}
                  onChange={(e) => setForm({ ...form, salesperson: e.target.value })}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm bg-white"
                >
                  {salespersons.map(s => (
                    <option key={s.id} value={s.display_name || s.name}>
                      {s.display_name || s.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Método de pagamento padrão</label>
                <select
                  value={form.payment_method}
                  onChange={(e) => { setPaymentTouched(true); setForm({ ...form, payment_method: e.target.value }); }}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm bg-white"
                >
                  {paymentMethods.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
                <div className="text-[11px] text-gray-500 mt-1">
                  Cada item pode sobrescrever este método em "Opções avançadas".
                </div>
                {totals.value > 0 && /^CREDITO_(\d+)X$/.test(form.payment_method || '') && (() => {
                  const n = parseInt(form.payment_method.match(/^CREDITO_(\d+)X$/)[1], 10);
                  const t = Math.round(totals.value * 100) / 100;
                  return (
                    <div className="mt-1.5 text-[11px] bg-blue-50 text-blue-700 border border-blue-200 rounded-md px-2 py-1.5">
                      💳 <b>Crédito em {n}x</b> de {fmtMoney(t / n)} cada — sugerido pelo valor do orçamento.
                      <span className="text-blue-500"> Pagamento real é definido no Financeiro.</span>
                    </div>
                  );
                })()}
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Observações do orçamento (cliente vê)</label>
                <textarea
                  rows={3}
                  value={form.budget_observations || ''}
                  onChange={(e) => setForm({ ...form, budget_observations: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Observações internas (não aparecem no PDF/WhatsApp)</label>
                <textarea
                  rows={2}
                  value={form.internal_observations || ''}
                  onChange={(e) => setForm({ ...form, internal_observations: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 text-red-700 border border-red-200 rounded-lg px-3 py-2 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" /> {error}
            </div>
          )}
        </div>

        {/* Footer com totais e ações */}
        <div className="border-t border-gray-200 p-3 sm:p-4 bg-gray-50 space-y-2">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="bg-white border border-gray-200 rounded-lg py-1.5">
              <div className="text-[10px] text-gray-500 uppercase">Itens</div>
              <div className="text-sm font-bold text-gray-900">{totals.units}</div>
            </div>
            <div className="bg-white border border-gray-200 rounded-lg py-1.5">
              <div className="text-[10px] text-gray-500 uppercase">M² / Linear</div>
              <div className="text-sm font-bold text-gray-900">
                {totals.area > 0 ? `${totals.area.toFixed(2)}m²` : totals.linear > 0 ? `${totals.linear.toFixed(2)}m` : '—'}
              </div>
            </div>
            <div className="bg-emerald-600 text-white rounded-lg py-1.5">
              <div className="text-[10px] uppercase opacity-90">Total</div>
              <div className="text-sm font-bold">{fmtMoney(totals.value)}</div>
            </div>
          </div>

          <div className="flex gap-2">
            {step > 1 && (
              <button
                onClick={() => setStep(step - 1)}
                className="flex-1 px-3 py-2.5 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-100 text-sm font-medium"
              >
                Voltar
              </button>
            )}
            {step < 3 ? (
              <button
                onClick={() => setStep(step + 1)}
                disabled={step === 1 && !form.client_id}
                className="flex-1 px-3 py-2.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
              >
                Avançar
              </button>
            ) : (
              <button
                onClick={save}
                disabled={saving}
                className="flex-1 px-3 py-2.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 text-sm font-semibold disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                {isEdit ? 'Salvar Alterações' : 'Criar Orçamento'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


