import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Clients } from "./pages/Clients";
import { Catalog } from "./pages/Catalog";
import { Budgets } from "./pages/Budgets";
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
          </Routes>
        </Layout>
      </BrowserRouter>
    </div>
  );
}

export default App;