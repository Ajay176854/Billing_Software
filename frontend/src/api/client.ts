import axios from 'axios';
import { setupCache } from 'axios-cache-interceptor';

const instance = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

// Wrap axios with automatic caching for GET requests (15s TTL)
const api = setupCache(instance, {
  ttl: 15 * 1000,
  methods: ['get']
});

api.interceptors.response.use((response) => {
  if (response.config.method && ['post', 'put', 'delete', 'patch'].includes(response.config.method)) {
    // We can wipe the local cache store on successful mutation
    // @ts-ignore - clear() exists on MemoryStorage but isn't on the base AxiosStorage type
    if (typeof api.storage.clear === 'function') api.storage.clear();
  }
  return response;
});

// JWT interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 interceptor — auto logout
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
