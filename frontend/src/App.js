import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AuthProvider, ProtectedRoute, useAuth } from "./contexts/AuthContext";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Clients } from "./pages/Clients";
import { Catalog } from "./pages/Catalog";
import { Budgets } from "./pages/Budgets";
import { Routes as RoutesPage } from "./pages/Routes";
import { RoutesGeoapify } from "./pages/RoutesGeoapify";
import { SimuladorRotas } from "./pages/SimuladorRotas";
import { Financial } from "./pages/Financial";
import { Automations } from "./pages/Automations";
import { BudgetConfig } from "./pages/BudgetConfig";
import { SystemConfig } from "./pages/SystemConfig";
import { Agenda } from "./pages/Agenda";
import { Reports } from "./pages/Reports";
import TechnicianMode from "./pages/TechnicianMode";
import { FinanceManager } from "./pages/finance/FinanceManager";
import { ComunicacaoWhatsApp } from "./pages/ComunicacaoWhatsApp";
import { AutomationPage } from "./pages/automation/AutomationPage";
import AcceptancePage from "./pages/AcceptancePage";
import PhotoGalleryPage from "./pages/PhotoGalleryPage";
import { Toaster } from "./components/ui/sonner";
import "./App.css";

const Placeholder = ({ title }) => (
  <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
    <h2 className="text-xl font-semibold text-gray-900 mb-2">{title}</h2>
    <p className="text-gray-500">Em breve nesta tela.</p>
  </div>
);

function LoginGate() {
  const { user, loading } = useAuth();
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
    </div>
  );
  if (user) return <Navigate to="/" replace />;
  return <Login />;
}

function ProtectedShell() {
  return (
    <ProtectedRoute>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/clients" element={<Clients />} />
          <Route path="/catalog" element={<Catalog />} />
          <Route path="/budgets" element={<Budgets />} />
          <Route path="/routes" element={<RoutesPage />} />
          <Route path="/routes-geo" element={<RoutesGeoapify />} />
          <Route path="/routes-simulator" element={<SimuladorRotas />} />
          <Route path="/budget-config" element={<BudgetConfig />} />
          <Route path="/system-config" element={<SystemConfig />} />
          <Route path="/agenda" element={<Agenda />} />
          <Route path="/technician" element={<TechnicianMode />} />
          <Route path="/whatsapp" element={<ComunicacaoWhatsApp />} />
          <Route path="/financial" element={<Financial />} />
          <Route path="/automations" element={<Automations />} />
          <Route path="/automation-ai" element={<AutomationPage />} />
          <Route path="/finance-manager" element={<FinanceManager />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/tickets" element={<Placeholder title="Chamados e Manutenção" />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </ProtectedRoute>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginGate />} />
            {/* Rotas públicas — sem autenticação */}
            <Route path="/aceite/:token" element={<AcceptancePage />} />
            <Route path="/galeria/:token" element={<PhotoGalleryPage />} />
            <Route path="/*" element={<ProtectedShell />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
      <Toaster />
    </div>
  );
}

export default App;
