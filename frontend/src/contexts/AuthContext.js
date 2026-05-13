import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { authApi, getToken, setToken, getStoredUser, setStoredUser } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser());
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return null;
    }
    try {
      const r = await authApi.me();
      setUser(r.data);
      setStoredUser(r.data);
      setLoading(false);
      return r.data;
    } catch (e) {
      setToken(null);
      setStoredUser(null);
      setUser(null);
      setLoading(false);
      return null;
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const login = async (email, password) => {
    const r = await authApi.login(email, password);
    setToken(r.data.access_token);
    setStoredUser(r.data.user);
    setUser(r.data.user);
    return r.data.user;
  };

  const logout = () => {
    setToken(null);
    setStoredUser(null);
    setUser(null);
    window.location.href = '/login';
  };

  const hasRole = (...roles) => {
    if (!user) return false;
    if (user.role === 'ADMIN') return true;
    return roles.includes(user.role);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refresh, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

export function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
      </div>
    );
  }
  if (!user) {
    window.location.href = '/login';
    return null;
  }
  return children;
}
