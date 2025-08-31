import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;

// Create axios instance
const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // Increased to 60 seconds for OSRM optimization
});

// Add request interceptor for debugging
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Client API
export const clientsApi = {
  getAll: (params = {}) => api.get('/clients', { params }),
  getById: (id) => api.get(`/clients/${id}`),
  create: (data) => api.post('/clients', data),
  update: (id, data) => api.put(`/clients/${id}`, data),
  delete: (id) => api.delete(`/clients/${id}`),
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
  addItem: (budgetId, itemData) => api.post(`/budgets/${budgetId}/items`, itemData),
  generateWhatsApp: (id) => api.get(`/budgets/${id}/whatsapp`),
  generatePDF: (id) => api.get(`/budgets/${id}/pdf`, { responseType: 'blob' }),
};

// Places API (Google)
export const placesApi = {
  search: (query) => api.get('/places/search', { params: { query } }),
  getDetails: (placeId) => api.get('/places/details', { params: { place_id: placeId } }),
};

// Dashboard API
export const dashboardApi = {
  getSummary: () => api.get('/dashboard'),
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
  create: (routeData) => api.post('/routes', routeData),
  addStops: (routeId, stops) => api.put(`/routes/${routeId}/stops`, { stops }),
  optimize: (routeId, routeType) => api.put(`/routes/${routeId}/optimize`, { route_type: routeType }),
  get: (routeId) => api.get(`/routes/${routeId}`),
  getSavedRoutes: () => api.get('/routes'),
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
  getEventsByRoute: (routeId) => api.get(`/calendar/events/${routeId}`),
  getAllEvents: (startDate, endDate) => api.get('/calendar/events', {
    params: { start_date: startDate, end_date: endDate }
  }),
  getEventDetail: (eventId) => api.get(`/calendar/events/detail/${eventId}`),
  updateEvent: (eventId, eventData) => api.put(`/calendar/events/${eventId}`, eventData),
  deleteEvent: (eventId) => api.delete(`/calendar/events/${eventId}`)
};

export default api;