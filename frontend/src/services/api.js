import axios from 'axios';

import { BACKEND_URL } from '../lib/backendUrl';
const API_BASE = `${BACKEND_URL}/api`;

// Create axios instance
const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // Increased to 60 seconds for OSRM optimization
});

// Token storage helpers
export const TOKEN_KEY = 'superdry_token';
export const USER_KEY = 'superdry_user';

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY);
export const getStoredUser = () => {
  try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch { return null; }
};
export const setStoredUser = (u) => u ? localStorage.setItem(USER_KEY, JSON.stringify(u)) : localStorage.removeItem(USER_KEY);

// Add request interceptor for auth + debugging
api.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor for error handling + auto logout on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
      setToken(null);
      setStoredUser(null);
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Client API
export const clientsApi = {
  getAll: (params = {}) => api.get('/clients', { params }),
  getById: (id) => api.get(`/clients/${id}`),
  getHistory: (id) => api.get(`/clients/${id}/history`),
  count: () => api.get('/clients/count'),
  create: (data) => api.post('/clients', data),
  update: (id, data) => api.put(`/clients/${id}`, data),
  delete: (id) => api.delete(`/clients/${id}`),
};

// Auth API
export const authApi = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  me: () => api.get('/auth/me'),
  changePassword: (oldPassword, newPassword) =>
    api.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword }),
};

// Users API (admin)
export const usersApi = {
  list: () => api.get('/users'),
  salespersons: () => api.get('/users/salespersons'),
  create: (data) => api.post('/users', data),
  update: (id, data) => api.put(`/users/${id}`, data),
  delete: (id) => api.delete(`/users/${id}`),
};

// Services API
export const servicesApi = {
  getAll: (params = {}) => api.get('/services', { params }),
  getById: (id) => api.get(`/services/${id}`),
  create: (data) => api.post('/services', data),
  update: (id, data) => api.put(`/services/${id}`, data),
  deactivate: (id) => api.put(`/services/${id}/deactivate`),
};

// Budgets API
export const budgetsApi = {
  getAll: (params = {}) => api.get('/budgets', { params }),
  getById: (id) => api.get(`/budgets/${id}`),
  create: (data) => api.post('/budgets', data),
  update: (id, data) => api.put(`/budgets/${id}`, data),
  delete: (id) => api.delete(`/budgets/${id}`),
  forceDelete: (id) => api.delete(`/budgets/${id}/force`),
  addItem: (budgetId, itemData) => api.post(`/budgets/${budgetId}/items`, itemData),
  generateWhatsApp: (id) => api.get(`/budgets/${id}/whatsapp`),
  generatePDF: (id) => api.get(`/budgets/${id}/pdf`, { responseType: 'blob' }),
};

// Items API (item como pilar)
export const itemsApi = {
  list: (params = {}) => api.get('/items', { params }),
  get: (id) => api.get(`/items/${id}`),
  patch: (id, fields) => api.patch(`/items/${id}`, fields),
  changeStatus: (id, status, notes) => api.post(`/items/${id}/status`, { status, notes }),
  schedule: (id, schedule) => api.post(`/items/${id}/schedule`, schedule),
  startSession: (id, payload = {}) => api.post(`/items/${id}/execution-session/start`, payload),
  finishSession: (id, sessionId, payload) =>
    api.post(`/items/${id}/execution-session/${sessionId}/finish`, payload),
  registerPayment: (id, payload) => api.post(`/items/${id}/payment`, payload),
  timeline: (id) => api.get(`/items/${id}/timeline`),
  receiptUrl: (id) => `${BACKEND_URL}/api/items/${id}/receipt`,
  pickupReceiptUrl: (id) => `${BACKEND_URL}/api/items/${id}/pickup-receipt`,
  whatsappReceipt: (id, type = 'receipt') => api.get(`/items/${id}/whatsapp-receipt`, { params: { doc_type: type } }),
  // Company Mode
  companyMode: () => api.get('/items/company-mode'),
  bulkStatus: (item_ids, status, notes = '') => api.post('/items/bulk-status', { item_ids, status, notes }),
  updateMeasures: (id, payload) => api.patch(`/items/${id}/measures`, payload),
};

// Cobrança consolidada (vários itens / responsável financeiro)
export const consolidatedPaymentApi = {
  create: (payload) => api.post('/payments/consolidated', payload),
  whatsapp: (cpid) => api.get(`/payments/consolidated/${cpid}/whatsapp`),
  pending: () => api.get('/payments/consolidated/pending'),
  confirmManual: (cpid) => api.post(`/payments/consolidated/${cpid}/confirm-manual`),
};

// Enums / opções
export const enumsApi = {
  serviceStatus: () => api.get('/service-status/options'),
};

// Places API (Google)
export const placesApi = {
  search: (query) => api.get('/places/search', { params: { query } }),
  getDetails: (placeId) => api.get('/places/details', { params: { place_id: placeId } }),
  resolveLocation: (text) => api.post('/places/resolve-location', { text }),
};

// Dashboard API
export const dashboardApi = {
  getSummary: () => api.get('/dashboard/summary'),
  getLegacy: () => api.get('/dashboard'),
};

// Budget Config API
export const budgetConfigApi = {
  get: () => api.get('/budget-config'),
  update: (data) => api.put('/budget-config', data),
};

// System Config API
export const systemConfigApi = {
  get: () => api.get('/system-config'),
  update: (data) => api.put('/system-config', data),
};

// Routes API
export const routesApi = {
  getAvailableItems: () => api.get('/budget-items/available-for-routes'),
  getSavedRoutes: () => api.get('/routes'),
  create: (routeData) => api.post('/routes', routeData),
  get: (routeId) => api.get(`/routes/${routeId}`),
  update: (routeId, updateData) => api.put(`/routes/${routeId}`, updateData),
  addStops: (routeId, stops) => api.put(`/routes/${routeId}/stops`, stops),
  optimize: (routeId, routeType) => api.post(`/routes/${routeId}/optimize`, { route_type: routeType }),
  optimizeGeoapify: (routeId, considerTraffic = false) =>
    api.post(`/routes/${routeId}/optimize-geoapify`, {}, { params: { traffic: considerTraffic } }),
  delete: (routeId) => api.delete(`/routes/${routeId}`)
};

export const agendaApi = {
  getGoogleAuthUrl: () => api.get('/calendar/auth-url'),
  authenticateGoogle: (code, redirectUri) => api.post('/calendar/auth', { code, redirect_uri: redirectUri }),
  createEvents: (routeId, stopIds, startDate, startTime) => 
    api.post('/calendar/events', { 
      route_id: routeId, 
      stop_ids: stopIds, 
      start_date: startDate, 
      start_time: startTime 
    }),
  getDirectEvent: (eventId) => api.get(`/calendar/events/direct/${eventId}`),
  createDirectEvent: (eventData) => api.post('/calendar/events/direct', eventData),
  getEventsByRoute: (routeId) => api.get(`/calendar/events/${routeId}`),
  getAllEvents: (startDate, endDate) => api.get('/calendar/events', {
    params: { start_date: startDate, end_date: endDate }
  }),
  getEventDetail: (eventId) => api.get(`/calendar/events/detail/${eventId}`),
  updateEvent: (eventId, eventData) => api.put(`/calendar/events/${eventId}`, eventData),
  deleteEvent: (eventId) => api.delete(`/calendar/events/${eventId}`)
};

// Budget Items API
export const budgetItemsApi = {
  updateStatus: (itemId, status) => api.put(`/budget-items/${itemId}/status`, null, {
    params: { status }
  }),
  getStatusOptions: () => api.get('/service-status/options')
};

// Technician API
export const technicianApi = {
  assignEvents: (assignment) => api.post('/technician/assign-events', assignment),
  getDailyTasks: (technicianId, date, all = false) => api.get(`/technician/${technicianId}/daily-tasks`, {
    params: all ? { all: true } : { date }
  }),
  updateAssignmentStatus: (assignmentId, status) => api.put(`/technician/assignment/${assignmentId}/status`, null, {
    params: { status }
  }),
  finalizeToday: (date) => api.post('/technician/finalize-today', {}, { params: date ? { date } : {} }),
  markDesisted:   (itemId) => api.patch(`/items/${itemId}/desist`),
  reactivateItem: (itemId) => api.patch(`/items/${itemId}/reactivate`),
};

// Relatórios
export const reportsApi = {
  partnerItems: (params = {}) => api.get('/reports/partner-items', { params }),
};

export default api;
