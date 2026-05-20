import React, { useState, useMemo, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Home, Users, FileText, Package, Settings, Cog, Route as RouteIcon, Smartphone,
  MessageSquare, Wallet, BarChart3, Wrench, CalendarDays, Menu, X, LogOut,
  ShieldCheck, UserCircle, ChevronDown, Droplets, Navigation
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function CompanyLogo({ size = 'md' }) {
  const [src, setSrc] = useState(null);
  useEffect(() => {
    fetch(`${BACKEND_URL}/api/system-config/logo`)
      .then(r => r.json())
      .then(d => { if (d.has_custom_logo || d.has_fallback_logo) setSrc(`${BACKEND_URL}/api/system-config/logo/file`); })
      .catch(() => {});
  }, []);

  const sizeMap = {
    md:  'w-9 h-9 rounded-xl',
    sm:  'w-7 h-7 rounded-lg',
    xs:  'w-8 h-8 rounded-lg',
  };

  const baseCls = `${sizeMap[size] || sizeMap.md} overflow-hidden flex items-center justify-center`;
  const fallbackCls = `${baseCls} bg-white border border-blue-200`;
  const imgCls = `${baseCls} bg-white`;

  return (
    <div className={src ? imgCls : fallbackCls}>
      {src
        ? <img src={src} alt="logo" className="w-full h-full object-contain p-0.5" />
        : <span className="text-blue-600 font-bold text-sm">S</span>}
    </div>
  );
}

const ALL_ITEMS = [
  { path: '/', label: 'Painel', short: 'Painel', icon: Home, roles: ['ADMIN','TECNICO','ATENDENTE','FINANCEIRO','MANUTENCAO'] },
  { path: '/clients', label: 'Clientes', short: 'Clientes', icon: Users, roles: ['ADMIN','ATENDENTE'] },
  { path: '/budgets', label: 'Orçamentos', short: 'Orç.', icon: FileText, roles: ['ADMIN','ATENDENTE'] },
  { path: '/routes', label: 'Rotas', short: 'Rotas', icon: RouteIcon, roles: ['ADMIN','ATENDENTE'] },
  { path: '/routes-geo', label: 'Rotas Geoapify', short: 'Rotas', icon: Navigation, roles: ['ADMIN','ATENDENTE'] },
  { path: '/agenda', label: 'Agenda', short: 'Agenda', icon: CalendarDays, roles: ['ADMIN','ATENDENTE','TECNICO'] },
  { path: '/whatsapp', label: 'WhatsApp', short: 'WhatsApp', icon: MessageSquare, roles: ['ADMIN','ATENDENTE'] },
  { path: '/technician', label: 'Execução e Lavagem', short: 'Execução', icon: Smartphone, roles: ['ADMIN','TECNICO'] },
  { path: '/financial', label: 'Financeiro', short: 'Finan.', icon: Wallet, roles: ['ADMIN','FINANCEIRO'] },
  { path: '/finance-manager', label: 'Gerenciador Financeiro', short: 'Ger.Fin.', icon: BarChart3, roles: ['ADMIN','FINANCEIRO'] },
  { path: '/reports', label: 'Relatórios', short: 'Relat.', icon: BarChart3, roles: ['ADMIN','FINANCEIRO'] },
  { path: '/tickets', label: 'Chamados e Manutenção', short: 'Chamados', icon: Wrench, roles: ['ADMIN','MANUTENCAO'] },
  { path: '/catalog', label: 'Catálogo', short: 'Catálogo', icon: Package, roles: ['ADMIN'] },
  { path: '/budget-config', label: 'Config. Orçamento', short: 'Cfg.Orç.', icon: Settings, roles: ['ADMIN'] },
  { path: '/system-config', label: 'Config. Sistema', short: 'Cfg.Sist.', icon: Cog, roles: ['ADMIN'] },
];

export function Layout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [editingNav, setEditingNav] = useState(false);

  const STORAGE_KEY = `quicknav_${user?.id || 'default'}`;
  const DEFAULT_NAV = ['/', '/budgets', '/routes-geo', '/technician', '/financial'];

  const [quickNavPaths, setQuickNavPaths] = useState(() => {
    try {
      const saved = localStorage.getItem(`quicknav_${user?.id || 'default'}`);
      return saved ? JSON.parse(saved) : DEFAULT_NAV;
    } catch { return DEFAULT_NAV; }
  });

  const saveQuickNav = (paths) => {
    setQuickNavPaths(paths);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(paths));
  };

  const items = useMemo(() => {
    if (!user) return [];
    if (user.allowed_modules && user.allowed_modules.length > 0) {
      return ALL_ITEMS.filter(i =>
        i.roles.includes(user.role) || user.allowed_modules.includes(i.path)
      );
    }
    return ALL_ITEMS.filter(i => i.roles.includes(user.role));
  }, [user]);

  // Bottom nav: usa caminhos salvos, filtra só os que o usuário tem acesso
  const primary = quickNavPaths
    .map(p => items.find(i => i.path === p))
    .filter(Boolean)
    .slice(0, 5);

  const currentLabel = items.find(i => i.path === location.pathname)?.label
    || ALL_ITEMS.find(i => i.path === location.pathname)?.label
    || 'SuperDry';

  const NavLink = ({ item, compact = false }) => {
    const Icon = item.icon;
    const active = location.pathname === item.path;
    return (
      <button
        onClick={() => { navigate(item.path); setDrawerOpen(false); }}
        className={`w-full flex items-center ${compact ? 'flex-col gap-0.5 py-2' : 'gap-3 px-3 py-2.5'} rounded-lg transition-colors ${
          active
            ? 'bg-blue-600 text-white shadow-sm'
            : 'text-gray-700 hover:bg-gray-100'
        }`}
      >
        <Icon className={`${compact ? 'w-5 h-5' : 'w-5 h-5'} shrink-0`} />
        <span className={compact ? 'text-[10px] font-medium leading-tight' : 'text-sm font-medium'}>
          {compact ? item.short : item.label}
        </span>
      </button>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ============== Desktop Sidebar ============== */}
      <aside className="hidden lg:flex fixed inset-y-0 left-0 w-64 bg-white border-r border-gray-200 flex-col z-30">
        <div className="h-16 flex items-center gap-2 px-5 border-b border-gray-200">
          <CompanyLogo size="md" />
          <div className="leading-tight">
            <div className="font-bold text-gray-900">SuperDry</div>
            <div className="text-[11px] text-gray-500">Lavanderia</div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
          {items.map(it => <NavLink key={it.path} item={it} />)}
        </nav>
        <div className="border-t border-gray-200 p-3">
          <div className="flex items-center gap-2 px-1 mb-2">
            <UserCircle className="w-7 h-7 text-gray-400" />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900 truncate">{user?.name}</div>
              <div className="text-[11px] text-gray-500 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" /> {user?.role}
              </div>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm rounded-lg border border-gray-200 hover:bg-gray-50 text-gray-700"
          >
            <LogOut className="w-4 h-4" /> Sair
          </button>
        </div>
      </aside>

      {/* ============== Mobile Top Header ============== */}
      <header className="lg:hidden sticky top-0 z-40 bg-white border-b border-gray-200">
        <div className="h-14 px-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setDrawerOpen(true)}
              className="p-2 rounded-lg hover:bg-gray-100 text-gray-700"
              aria-label="Menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-1.5">
              <CompanyLogo size="sm" />
              <span className="font-bold text-gray-900 text-sm">SuperDry</span>
            </div>
          </div>
          <div className="text-sm font-semibold text-gray-700 truncate max-w-[55%]">{currentLabel}</div>
          <button
            onClick={() => setUserMenuOpen(v => !v)}
            className="p-1.5 rounded-full hover:bg-gray-100 relative"
          >
            <UserCircle className="w-7 h-7 text-gray-500" />
          </button>
        </div>
        {userMenuOpen && (
          <div className="absolute right-2 top-14 mt-1 w-56 bg-white rounded-xl shadow-lg border border-gray-200 z-50">
            <div className="px-3 py-2 border-b border-gray-100">
              <div className="text-sm font-semibold text-gray-900 truncate">{user?.name}</div>
              <div className="text-xs text-gray-500">{user?.email}</div>
              <div className="text-[11px] mt-1 inline-flex items-center gap-1 text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                <ShieldCheck className="w-3 h-3" /> {user?.role}
              </div>
            </div>
            <button
              onClick={logout}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 text-gray-700"
            >
              <LogOut className="w-4 h-4" /> Sair
            </button>
          </div>
        )}
      </header>

      {/* ============== Mobile Drawer ============== */}
      {drawerOpen && (
        <>
          <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setDrawerOpen(false)} />
          <aside className="fixed inset-y-0 left-0 z-50 w-72 bg-white shadow-2xl lg:hidden flex flex-col">
            <div className="h-14 flex items-center justify-between px-4 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <CompanyLogo size="xs" />
                <div>
                  <div className="font-bold text-gray-900 text-sm">SuperDry</div>
                  <div className="text-[10px] text-gray-500">Menu</div>
                </div>
              </div>
              <button onClick={() => setDrawerOpen(false)} className="p-1.5 hover:bg-gray-100 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto p-2 space-y-1">
              {items.map(it => <NavLink key={it.path} item={it} />)}
            </nav>
            <div className="border-t border-gray-200 p-3">
              <button
                onClick={logout}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm rounded-lg border border-gray-200 hover:bg-gray-50 text-gray-700"
              >
                <LogOut className="w-4 h-4" /> Sair
              </button>
            </div>
          </aside>
        </>
      )}

      {/* ============== Main content ============== */}
      <main className="lg:pl-64 pb-20 lg:pb-0 min-h-screen">
        <div className="hidden lg:flex h-16 items-center justify-between bg-white border-b border-gray-200 px-6 sticky top-0 z-20">
          <h1 className="text-xl font-semibold text-gray-900">{currentLabel}</h1>
          <div className="text-xs text-gray-500">{new Date().toLocaleDateString('pt-BR')}</div>
        </div>
        <div className="p-3 sm:p-4 lg:p-6 max-w-7xl mx-auto">
          {children}
        </div>
      </main>

      {/* ============== Mobile Bottom Nav ============== */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-30 safe-area-inset-bottom">
        <div className={`grid gap-0`} style={{ gridTemplateColumns: `repeat(${primary.length + 1}, 1fr)` }}>
          {primary.map(it => <NavLink key={it.path} item={it} compact />)}
          {/* Botão de configuração da barra */}
          <button
            onClick={() => setEditingNav(true)}
            className="flex flex-col items-center gap-0.5 py-2 text-gray-400 hover:bg-gray-50"
          >
            <Settings className="w-4 h-4" />
            <span className="text-[9px] font-medium">Config.</span>
          </button>
        </div>
      </nav>

      {/* ============== Modal configuração da barra de acesso rápido ============== */}
      {editingNav && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-end justify-center">
          <div className="bg-white rounded-t-2xl w-full max-w-md p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Acesso Rápido</h3>
              <button onClick={() => setEditingNav(false)}><X className="w-5 h-5 text-gray-400" /></button>
            </div>
            <p className="text-xs text-gray-500 mb-4">Selecione até 5 atalhos para a barra inferior.</p>
            <div className="space-y-1.5 max-h-72 overflow-y-auto">
              {items.map(it => {
                const selected = quickNavPaths.includes(it.path);
                const Icon = it.icon;
                return (
                  <label key={it.path} className="flex items-center gap-3 p-2.5 rounded-xl cursor-pointer hover:bg-gray-50">
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => {
                        if (selected) {
                          saveQuickNav(quickNavPaths.filter(p => p !== it.path));
                        } else if (quickNavPaths.length < 5) {
                          saveQuickNav([...quickNavPaths, it.path]);
                        }
                      }}
                      disabled={!selected && quickNavPaths.length >= 5}
                      className="h-4 w-4 text-blue-600 rounded"
                    />
                    <Icon className="w-4 h-4 text-gray-500 shrink-0" />
                    <span className="text-sm text-gray-800">{it.label}</span>
                  </label>
                );
              })}
            </div>
            <p className="text-[11px] text-gray-400 mt-3">{quickNavPaths.length}/5 selecionados</p>
            <button
              onClick={() => { saveQuickNav(['/', '/budgets', '/routes-geo', '/technician', '/financial']); }}
              className="mt-3 w-full py-2 text-xs text-gray-500 bg-gray-100 rounded-xl hover:bg-gray-200"
            >
              Restaurar padrão
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Layout;
