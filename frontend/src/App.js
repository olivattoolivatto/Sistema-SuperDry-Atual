import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Clients } from "./pages/Clients";
import { Catalog } from "./pages/Catalog";
import { Budgets } from "./pages/Budgets";
import { Routes as RoutesPage } from "./pages/Routes";
import { BudgetConfig } from "./pages/BudgetConfig";
import { SystemConfig } from "./pages/SystemConfig";
import { Toaster } from "./components/ui/sonner";
import "./App.css";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/clients" element={<Clients />} />
            <Route path="/catalog" element={<Catalog />} />
            <Route path="/budgets" element={<Budgets />} />
            <Route path="/routes" element={<RoutesPage />} />
            <Route path="/budget-config" element={<BudgetConfig />} />
            <Route path="/system-config" element={<SystemConfig />} />
          </Routes>
        </Layout>
      </BrowserRouter>
      <Toaster />
    </div>
  );
}

export default App;