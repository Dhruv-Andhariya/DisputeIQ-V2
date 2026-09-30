import axios from 'axios';
import { getToken, clearToken } from './auth/tokenStorage';

// Dev: '/api' goes through the Vite proxy (vite.config.js) to the backend on :8000.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const AUTH_EXPIRED_EVENT = 'disputeiq:auth-expired';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Any 401 on an authenticated call means the token is missing, expired, or revoked:
// drop it and let the AuthProvider send the user back to the login page.
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const isLoginAttempt = err.config?.url?.startsWith('/auth/login');
    if (err.response?.status === 401 && !isLoginAttempt) {
      clearToken();
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
    }
    return Promise.reject(err);
  }
);

// Human-readable message from a FastAPI error response.
export function apiErrorMessage(err, fallback = 'Something went wrong. Please try again.') {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    // 422 validation errors: [{loc: [...,'field'], msg}]
    return detail
      .map((d) => {
        const field = d.loc?.[d.loc.length - 1];
        const msg = (d.msg || '').replace(/^Value error, /, '');
        return field ? `${field.replace(/_/g, ' ')}: ${msg}` : msg;
      })
      .join('. ');
  }
  if (!err?.response) return 'Cannot reach the DisputeIQ API. Is the backend running?';
  return fallback;
}

// Auth & organization
export const loginRequest = (email, password) => api.post('/auth/login', { email, password });
export const registerRequest = (payload) => api.post('/auth/register', payload);
export const fetchCurrentUser = () => api.get('/auth/me');
export const logoutRequest = () => api.post('/auth/logout');
export const fetchOrganizationUsers = () => api.get('/organizations/me/users');
export const createOrganizationUser = (payload) => api.post('/organizations/me/users', payload);
export const updateOrganizationUser = (id, payload) => api.patch(`/organizations/me/users/${id}`, payload);
export const fetchOrganizationActivity = (limit = 10) => api.get('/organizations/me/audit-events', { params: { limit } });

// Disputes
export const fetchDisputes = () => api.get('/disputes');
export const fetchDisputeById = (id) => api.get(`/disputes/${id}`);
export const fetchLatestInvestigation = (id) => api.get(`/disputes/${id}/investigation`);
export const triggerInvestigation = (id) => api.post(`/disputes/${id}/investigate`);
export const fetchEvidence = (id) => api.get(`/disputes/${id}/evidence`);
export const fetchTimeline = (id) => api.get(`/disputes/${id}/timeline`);
export const fetchAuditEvents = (id) => api.get(`/disputes/${id}/audit`);
export const approveDispute = (id, notes) => api.post(`/disputes/${id}/approve`, { notes });
export const rejectDispute = (id, notes) => api.post(`/disputes/${id}/reject`, { notes });
export const triggerDemoFailure = (dispute_id) => api.post('/demo/failure', { dispute_id });
export const fetchEvaluationSummary = () => api.get('/evaluation/summary');

// Phase 2 merchant domain
export const fetchCustomers = () => api.get('/domain/customers');
export const createCustomer = (payload) => api.post('/domain/customers', payload);
export const updateCustomer = (id, payload) => api.patch(`/domain/customers/${id}`, payload);
export const fetchOrders = () => api.get('/domain/orders');
export const createOrder = (payload) => api.post('/domain/orders', payload);
export const updateOrder = (id, payload) => api.patch(`/domain/orders/${id}`, payload);
export const fetchTransactions = () => api.get('/domain/transactions');
export const createTransaction = (payload) => api.post('/domain/transactions', payload);
export const fetchDomainDisputes = () => api.get('/domain/disputes');
export const fetchDomainDispute = (id) => api.get(`/domain/disputes/${id}`);
export const createDomainDispute = (payload) => api.post('/domain/disputes', payload);
export const updateDomainDispute = (id, payload) => api.patch(`/domain/disputes/${id}`, payload);

// Phase 3 evidence ingestion
export const fetchUploadedEvidence = (disputeId) => api.get(`/domain/disputes/${disputeId}/evidence`);
// Remove the JSON default so the browser can set multipart/form-data with its boundary.
export const uploadEvidence = (disputeId, formData) => api.post(`/domain/disputes/${disputeId}/evidence`, formData, {
  headers: { 'Content-Type': undefined },
});
export const downloadEvidence = (evidenceId) => api.get(`/domain/evidence/${evidenceId}/download`, { responseType: 'blob' });
export const processEvidence = (evidenceId) => api.post(`/domain/evidence/${evidenceId}/process`);
export const fetchEvidenceProcessing = (evidenceId) => api.get(`/domain/evidence/${evidenceId}/processing`);

export default api;
