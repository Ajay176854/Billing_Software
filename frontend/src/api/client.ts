import axios from 'axios';

// Standard Axios instance for real-time inventory and billing operations
// Direct, zero-staleness API communication guarantees live stock numbers across all pages
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
});

// JWT interceptor — attach bearer token to every outgoing request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — handle network errors and auto logout on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Detect network errors or server unreachability
    if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
      window.dispatchEvent(new Event('backend-error'));
    }

    if (error.response?.status === 401 && !error.config.url?.includes('/auth/login')) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
