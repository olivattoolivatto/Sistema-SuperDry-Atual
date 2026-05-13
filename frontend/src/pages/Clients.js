import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Plus, Search, Edit2, Trash2, History as HistoryIcon, MessageCircle,
  Mail, MapPin, X, Save, Phone, AtSign, Instagram, FileText,
  ChevronDown, ChevronUp, Loader2, AlertTriangle, ExternalLink, Check
} from 'lucide-react';
import { clientsApi, placesApi } from '../services/api';
import MiniMap from '../components/MiniMap';

// ===== Helpers =====
const onlyDigits = (s = '') => String(s || '').replace(/\D+/g, '');

const maskPhoneBR = (v) => {
  const d = onlyDigits(v).slice(0, 11);
  if (d.length <= 10) {
    return d
      .replace(/^(\d{2})(\d)/, '($1) $2')
      .replace(/(\d{4})(\d)/, '$1-$2');
  }
  return d
    .replace(/^(\d{2})(\d)/, '($1) $2')
    .replace(/(\d{5})(\d)/, '$1-$2');
};

const maskCpfCnpj = (v) => {
  const d = onlyDigits(v).slice(0, 14);
  if (d.length <= 11) {
    return d
      .replace(/^(\d{3})(\d)/, '$1.$2')
      .replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
      .replace(/\.(\d{3})(\d)/, '.$1-$2');
  }
  return d
    .replace(/^(\d{2})(\d)/, '$1.$2')
    .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1/$2')
    .replace(/(\d{4})(\d)/, '$1-$2');
};

const normalize = (s = '') =>
  String(s || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();

const sanitizeInstagram = (v = '') =>
  v.replace(/^https?:\/\/(www\.)?instagram\.com\//i, '').replace(/^@/, '').trim();

const onlyWhatsappDigits = (v = '') => {
  const d = onlyDigits(v);
  if (!d) return '';
  return d.startsWith('55') ? d : `55${d}`;
};

// ===== AddressAutocomplete =====
function AddressAutocomplete({ value, onSelect, placeholder }) {
  const [query, setQuery] = useState(value || '');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debRef = useRef(null);
  const boxRef = useRef(null);

  useEffect(() => { setQuery(value || ''); }, [value]);

  useEffect(() => {
    if (debRef.current) clearTimeout(debRef.current);
    if (!query || query.length < 3) {
      setResults([]);
      setOpen(false);
      return;
    }
    debRef.current = setTimeout(async () => {
      try {
        setLoading(true);
        const r = await placesApi.search(query);
        setResults(r.data?.results || []);
        setOpen(true);
      } catch (e) {
        console.error(e);
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 350);
  }, [query]);

  useEffect(() => {
    const onClick = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const handleChoose = async (p) => {
    setOpen(false);
    setQuery(p.description || '');
    // Try to enrich with place details if no geometry yet
    let lat = p?.geometry?.location?.lat;
    let lng = p?.geometry?.location?.lng;
    let neighborhood = p?.neighborhood;
    let city = p?.city;
    let state = p?.state;
    let fullAddress = p.description || '';

    if ((!lat || !lng) && p.place_id) {
      try {
        const det = await placesApi.getDetails(p.place_id);
        const d = det.data?.details?.result || det.data?.details || {};
        fullAddress = d.formatted_address || fullAddress;
        const geo = d.geometry?.location;
        if (geo) {
          lat = geo.lat;
          lng = geo.lng;
        }
        // parse address_components
        (d.address_components || []).forEach((c) => {
          const t = c.types || [];
          if (t.includes('sublocality') || t.includes('neighborhood') || t.includes('sublocality_level_1')) {
            neighborhood = c.long_name;
          }
          if (t.includes('administrative_area_level_2') || t.includes('locality')) {
            city = c.long_name;
          }
          if (t.includes('administrative_area_level_1')) {
            state = c.short_name || c.long_name;
          }
        });
      } catch (e) {
        console.warn('place details fail', e);
      }
    }

    onSelect({
      full_address: fullAddress,
      neighborhood: neighborhood || '',
      city: city || '',
      state: state || '',
      latitude: lat || null,
      longitude: lng || null,
    });
  };

  return (
    <div className="relative" ref={boxRef}>
      <div className="relative">
        <MapPin className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          placeholder={placeholder || 'Buscar endereço, bairro, local…'}
          className="w-full pl-9 pr-9 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
        />
        {loading && <Loader2 className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 animate-spin" />}
      </div>
      {open && results.length > 0 && (
        <ul className="absolute z-30 mt-1 w-full max-h-72 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-lg">
          {results.slice(0, 10).map((p) => (
            <li
              key={p.place_id || p.description}
              onClick={() => handleChoose(p)}
              className="px-3 py-2 hover:bg-blue-50 cursor-pointer text-sm border-b border-gray-100 last:border-0"
            >
              <div className="font-medium text-gray-900 truncate">
                {p.structured_formatting?.main_text || p.description}
              </div>
              <div className="text-xs text-gray-500 truncate">
                {p.structured_formatting?.secondary_text || ''}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ===== Empty initial form =====
const emptyForm = () => ({
  name: '',
  phone_primary: '',
  phone_alternative: '',
  email: '',
  cpf_cnpj: '',
  instagram: '',
  address: {
    full_address: '',
    complement: '',
    neighborhood: '',
    city: '',
    state: '',
    latitude: null,
    longitude: null,
  },
});

// ===== Client History Modal =====
function HistoryModal({ client, onClose }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState('created_at');
  const [sortAsc, setSortAsc] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await clientsApi.getHistory(client.id);
        setRows(r.data?.items || []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, [client.id]);

  const sorted = useMemo(() => {
    const arr = [...rows];
    arr.sort((a, b) => {
      const av = a[sortKey] ?? '';
      const bv = b[sortKey] ?? '';
      if (typeof av === 'number' && typeof bv === 'number') return sortAsc ? av - bv : bv - av;
      return sortAsc
        ? String(av).localeCompare(String(bv), 'pt-BR')
        : String(bv).localeCompare(String(av), 'pt-BR');
    });
    return arr;
  }, [rows, sortKey, sortAsc]);

  const Header = ({ k, label, className = '' }) => (
    <th
      onClick={() => {
        if (sortKey === k) setSortAsc(!sortAsc);
        else { setSortKey(k); setSortAsc(true); }
      }}
      className={`text-left text-[11px] font-semibold text-gray-600 uppercase px-2 py-2 cursor-pointer select-none whitespace-nowrap ${className}`}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {sortKey === k ? (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />) : null}
      </span>
    </th>
  );

  const fmtMoney = (n) => (Number(n) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="bg-white w-full sm:max-w-5xl sm:rounded-2xl rounded-t-2xl shadow-2xl flex flex-col max-h-[92vh]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <div>
            <h3 className="font-semibold text-gray-900">Histórico de {client.name}</h3>
            <p className="text-xs text-gray-500">{client.id} • {rows.length} itens</p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-100">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center h-40">
              <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
            </div>
          ) : rows.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <FileText className="w-10 h-10 mx-auto mb-2 text-gray-300" />
              Nenhum item encontrado para este cliente.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <Header k="budget_id" label="Orçamento" />
                  <Header k="service_code" label="Cód. Serviço" />
                  <Header k="service_name" label="Descrição" />
                  <Header k="measure_type" label="Unidade" />
                  <Header k="area_m2" label="M²" />
                  <Header k="linear_meters" label="M. Linear" />
                  <Header k="quantity" label="Qtd" />
                  <Header k="total_value" label="Valor" />
                  <Header k="status" label="Status" />
                </tr>
              </thead>
              <tbody>
                {sorted.map((r, idx) => (
                  <tr key={r.item_id || idx} className="border-t border-gray-100 hover:bg-blue-50/40">
                    <td className="px-2 py-2 font-mono text-xs">{r.budget_id}</td>
                    <td className="px-2 py-2 font-mono text-xs">{r.service_code}</td>
                    <td className="px-2 py-2">{r.service_name}</td>
                    <td className="px-2 py-2 text-xs">{r.measure_type}</td>
                    <td className="px-2 py-2 tabular-nums">{r.area_m2 ? Number(r.area_m2).toFixed(2) : '-'}</td>
                    <td className="px-2 py-2 tabular-nums">{r.linear_meters ? Number(r.linear_meters).toFixed(2) : '-'}</td>
                    <td className="px-2 py-2 tabular-nums">{r.quantity ?? '-'}</td>
                    <td className="px-2 py-2 tabular-nums font-medium">{fmtMoney(r.total_value)}</td>
                    <td className="px-2 py-2">
                      <span className="px-2 py-0.5 rounded-full text-[11px] bg-gray-100 text-gray-700">
                        {r.status || '-'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

// ===== Client Card =====
function ClientCard({ client, onEdit, onDelete, onHistory }) {
  const phoneDigits = onlyWhatsappDigits(client.phone_primary);
  const igUser = sanitizeInstagram(client.instagram || '');
  const addr = client.address || {};
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex flex-col">
      <div className="p-3 sm:p-4 flex-1">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="text-[11px] font-mono text-blue-700 bg-blue-50 inline-block px-1.5 py-0.5 rounded">
              {client.id}
            </div>
            <h3 className="font-semibold text-gray-900 mt-1 text-sm sm:text-base truncate">{client.name}</h3>
          </div>
        </div>

        <div className="mt-2 space-y-1 text-xs sm:text-sm text-gray-600">
          {client.phone_primary && (
            <div className="flex items-center gap-1.5">
              <Phone className="w-3.5 h-3.5 text-gray-400 shrink-0" />
              <span className="truncate">{maskPhoneBR(client.phone_primary)}</span>
              {phoneDigits && (
                <a
                  href={`https://wa.me/${phoneDigits}`}
                  target="_blank"
                  rel="noreferrer"
                  className="ml-auto p-1 rounded-md bg-green-50 text-green-700 hover:bg-green-100"
                  title="Abrir WhatsApp"
                >
                  <MessageCircle className="w-3.5 h-3.5" />
                </a>
              )}
            </div>
          )}
          {client.email && (
            <div className="flex items-center gap-1.5">
              <Mail className="w-3.5 h-3.5 text-gray-400 shrink-0" />
              <span className="truncate">{client.email}</span>
            </div>
          )}
          {igUser && (
            <div className="flex items-center gap-1.5">
              <Instagram className="w-3.5 h-3.5 text-gray-400 shrink-0" />
              <a
                href={`https://instagram.com/${igUser}`}
                target="_blank"
                rel="noreferrer"
                className="text-pink-600 hover:underline truncate"
              >
                @{igUser}
              </a>
            </div>
          )}
          {addr.full_address && (
            <div className="flex items-start gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-gray-400 shrink-0 mt-0.5" />
              <span className="text-[11px] sm:text-xs leading-snug line-clamp-2">{addr.full_address}</span>
            </div>
          )}
        </div>

        {(addr.latitude && addr.longitude) && (
          <div className="mt-3 rounded-lg overflow-hidden border border-gray-200">
            <MiniMap latitude={addr.latitude} longitude={addr.longitude} height="100px" zoom={14} title={client.name} />
          </div>
        )}
      </div>

      <div className="grid grid-cols-3 border-t border-gray-100">
        <button
          onClick={() => onHistory(client)}
          className="py-2 text-xs font-medium text-blue-700 hover:bg-blue-50 flex items-center justify-center gap-1"
        >
          <HistoryIcon className="w-3.5 h-3.5" /> Histórico
        </button>
        <button
          onClick={() => onEdit(client)}
          className="py-2 text-xs font-medium text-amber-700 hover:bg-amber-50 flex items-center justify-center gap-1 border-l border-gray-100"
        >
          <Edit2 className="w-3.5 h-3.5" /> Editar
        </button>
        <button
          onClick={() => onDelete(client)}
          className="py-2 text-xs font-medium text-rose-700 hover:bg-rose-50 flex items-center justify-center gap-1 border-l border-gray-100"
        >
          <Trash2 className="w-3.5 h-3.5" /> Excluir
        </button>
      </div>
    </div>
  );
}

// ===== Main page =====
export function Clients() {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [historyClient, setHistoryClient] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const loadClients = async () => {
    try {
      setLoading(true);
      const r = await clientsApi.getAll({ limit: 1000 });
      setClients(r.data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadClients(); }, []);

  // Client-side broad search (case + accent insensitive + multi-fields)
  const filtered = useMemo(() => {
    const q = normalize(searchTerm);
    if (!q) return clients;
    const qDigits = onlyDigits(searchTerm);
    return clients.filter((c) => {
      const name = normalize(c.name);
      if (name.includes(q)) return true;
      if (normalize(c.email || '').includes(q)) return true;
      if (normalize(c.id || '').includes(q)) return true;
      if (normalize(c.instagram || '').includes(q)) return true;
      const addr = c.address || {};
      if (normalize(addr.full_address || '').includes(q)) return true;
      if (normalize(addr.neighborhood || '').includes(q)) return true;
      if (normalize(addr.city || '').includes(q)) return true;
      if (qDigits) {
        if (onlyDigits(c.phone_primary || '').includes(qDigits)) return true;
        if (onlyDigits(c.phone_alternative || '').includes(qDigits)) return true;
        if (onlyDigits(c.cpf_cnpj || '').includes(qDigits)) return true;
      }
      return false;
    });
  }, [clients, searchTerm]);

  const openCreate = () => {
    setEditing(null);
    setForm({ ...emptyForm(), name: searchTerm });
    setError('');
    setFormOpen(true);
    setTimeout(() => {
      const el = document.getElementById('client-form-anchor');
      el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
  };

  const openEdit = (c) => {
    setEditing(c);
    setForm({
      name: c.name || '',
      phone_primary: c.phone_primary || '',
      phone_alternative: c.phone_alternative || '',
      email: c.email || '',
      cpf_cnpj: c.cpf_cnpj || '',
      instagram: c.instagram || '',
      address: {
        full_address: c.address?.full_address || '',
        complement: c.address?.complement || '',
        neighborhood: c.address?.neighborhood || '',
        city: c.address?.city || '',
        state: c.address?.state || '',
        latitude: c.address?.latitude ?? null,
        longitude: c.address?.longitude ?? null,
      },
    });
    setError('');
    setFormOpen(true);
    setTimeout(() => {
      const el = document.getElementById('client-form-anchor');
      el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
  };

  const cancelForm = () => {
    setFormOpen(false);
    setEditing(null);
    setForm(emptyForm());
    setError('');
  };

  const submitForm = async (e) => {
    e?.preventDefault();
    setError('');
    if (!form.name.trim()) { setError('Nome do cliente é obrigatório.'); return; }
    if (!form.phone_primary || onlyDigits(form.phone_primary).length < 10) {
      setError('Telefone principal inválido.');
      return;
    }
    if (!form.address.full_address) {
      setError('Endereço é obrigatório. Use a busca acima.');
      return;
    }
    const payload = {
      ...form,
      phone_primary: onlyDigits(form.phone_primary),
      phone_alternative: form.phone_alternative ? onlyDigits(form.phone_alternative) : null,
      cpf_cnpj: form.cpf_cnpj ? onlyDigits(form.cpf_cnpj) : null,
      instagram: form.instagram ? sanitizeInstagram(form.instagram) : null,
      email: form.email || null,
    };
    try {
      setSaving(true);
      if (editing) await clientsApi.update(editing.id, payload);
      else await clientsApi.create(payload);
      await loadClients();
      cancelForm();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Erro ao salvar cliente.');
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await clientsApi.delete(deleteTarget.id);
      setDeleteTarget(null);
      await loadClients();
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao excluir.');
    }
  };

  return (
    <div className="space-y-4">
      {/* Search + Add */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-3 sm:p-4">
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Digite o nome do cliente (ou telefone, email, endereço, CPF/CNPJ…)"
              className="w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
          </div>
          <button
            onClick={openCreate}
            className="px-4 py-2.5 bg-blue-600 text-white rounded-lg font-medium text-sm flex items-center justify-center gap-2 hover:bg-blue-700 active:scale-[0.98] transition"
          >
            <Plus className="w-4 h-4" /> Adicionar Novo Cliente
          </button>
        </div>
        <div className="mt-2 text-xs text-gray-500">
          {searchTerm ? `${filtered.length} de ${clients.length} clientes` : `${clients.length} cliente(s) cadastrado(s)`}
        </div>
      </div>

      {/* Form */}
      <div id="client-form-anchor" />
      {formOpen && (
        <form onSubmit={submitForm} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 sm:p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">
              {editing ? `Editar Cliente — ${editing.id}` : 'Novo Cliente'}
            </h2>
            <button type="button" onClick={cancelForm} className="p-2 rounded-lg hover:bg-gray-100">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Nome */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Nome do Cliente *</label>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
              required
            />
          </div>

          {/* Telefones */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Telefone Principal / WhatsApp *</label>
              <div className="flex gap-2">
                <input
                  value={maskPhoneBR(form.phone_primary)}
                  onChange={(e) => setForm({ ...form, phone_primary: onlyDigits(e.target.value) })}
                  placeholder="(00) 00000-0000"
                  className="flex-1 px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                  required
                />
                <a
                  href={form.phone_primary ? `https://wa.me/${onlyWhatsappDigits(form.phone_primary)}` : '#'}
                  target="_blank"
                  rel="noreferrer"
                  className={`px-3 rounded-lg flex items-center justify-center ${
                    form.phone_primary ? 'bg-green-600 text-white hover:bg-green-700' : 'bg-gray-200 text-gray-400 pointer-events-none'
                  }`}
                  title="Abrir WhatsApp"
                >
                  <MessageCircle className="w-4 h-4" />
                </a>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Telefone Alternativo</label>
              <input
                value={maskPhoneBR(form.phone_alternative)}
                onChange={(e) => setForm({ ...form, phone_alternative: onlyDigits(e.target.value) })}
                placeholder="(00) 00000-0000"
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
              />
            </div>
          </div>

          {/* Email + CPF/CNPJ */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
              <div className="relative">
                <AtSign className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">CPF / CNPJ</label>
              <input
                value={maskCpfCnpj(form.cpf_cnpj)}
                onChange={(e) => setForm({ ...form, cpf_cnpj: onlyDigits(e.target.value) })}
                placeholder="000.000.000-00"
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
              />
            </div>
          </div>

          {/* Instagram */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Instagram</label>
            <div className="flex">
              <span className="inline-flex items-center px-3 rounded-l-lg border border-r-0 border-gray-300 bg-gray-50 text-gray-500 text-sm">
                instagram.com/
              </span>
              <input
                value={sanitizeInstagram(form.instagram)}
                onChange={(e) => setForm({ ...form, instagram: sanitizeInstagram(e.target.value) })}
                placeholder="usuario"
                className="flex-1 px-3 py-2.5 border border-gray-300 rounded-r-lg focus:ring-2 focus:ring-blue-500 text-sm"
              />
              {sanitizeInstagram(form.instagram) && (
                <a
                  href={`https://instagram.com/${sanitizeInstagram(form.instagram)}`}
                  target="_blank"
                  rel="noreferrer"
                  className="ml-2 px-3 py-2.5 rounded-lg bg-pink-50 text-pink-600 hover:bg-pink-100"
                  title="Abrir Instagram"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>
              )}
            </div>
          </div>

          {/* Endereço */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Endereço Completo *</label>
            <AddressAutocomplete
              value={form.address.full_address}
              onSelect={(addr) => setForm((f) => ({ ...f, address: { ...f.address, ...addr } }))}
            />
            {form.address.latitude && form.address.longitude && (
              <div className="text-[11px] text-emerald-700 mt-1 inline-flex items-center gap-1">
                <Check className="w-3 h-3" /> Localização GPS capturada
              </div>
            )}
          </div>

          {/* Complemento */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Complemento</label>
            <input
              value={form.address.complement}
              onChange={(e) => setForm({ ...form, address: { ...form.address, complement: e.target.value } })}
              placeholder="Apto, bloco, ponto de referência…"
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>

          {/* Bairro / Cidade / Estado */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Bairro</label>
              <input
                value={form.address.neighborhood}
                onChange={(e) => setForm({ ...form, address: { ...form.address, neighborhood: e.target.value } })}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg bg-gray-50 text-sm"
                readOnly
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Cidade</label>
              <input
                value={form.address.city}
                onChange={(e) => setForm({ ...form, address: { ...form.address, city: e.target.value } })}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg bg-gray-50 text-sm"
                readOnly
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Estado</label>
              <input
                value={form.address.state}
                onChange={(e) => setForm({ ...form, address: { ...form.address, state: e.target.value } })}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg bg-gray-50 text-sm"
                readOnly
              />
            </div>
          </div>

          {error && (
            <div className="text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={cancelForm}
              className="flex-1 sm:flex-none px-4 py-2.5 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-medium"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 sm:flex-none px-4 py-2.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {editing ? 'Salvar Alterações' : 'Cadastrar Cliente'}
            </button>
          </div>
        </form>
      )}

      {/* Cards */}
      {loading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center text-gray-500">
          {clients.length === 0 ? 'Nenhum cliente cadastrado ainda.' : 'Nenhum cliente encontrado para a busca.'}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {filtered.map((c) => (
              <ClientCard
                key={c.id}
                client={c}
                onEdit={openEdit}
                onDelete={(cli) => setDeleteTarget(cli)}
                onHistory={(cli) => setHistoryClient(cli)}
              />
            ))}
          </div>
          <div className="text-center text-xs text-gray-400 pt-1">
            Total: <span className="font-semibold text-gray-600">{filtered.length}</span> cliente(s)
            {searchTerm && ` (filtrado de ${clients.length})`}
          </div>
        </>
      )}

      {/* History modal */}
      {historyClient && (
        <HistoryModal client={historyClient} onClose={() => setHistoryClient(null)} />
      )}

      {/* Delete confirmation */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-gray-900">Confirmar exclusão</h3>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Tem certeza que deseja excluir <strong>{deleteTarget.name}</strong> ({deleteTarget.id})?
              Esta ação não poderá ser desfeita.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-medium"
              >
                Cancelar
              </button>
              <button
                onClick={confirmDelete}
                className="flex-1 px-4 py-2 rounded-lg bg-rose-600 text-white hover:bg-rose-700 text-sm font-medium"
              >
                Excluir
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Clients;
