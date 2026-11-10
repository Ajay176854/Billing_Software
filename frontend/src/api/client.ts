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

// Response interceptor — handle network errors with resilience retry and auto logout on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;

    // Retry transient network errors (up to 2 times with 500ms backoff) before declaring backend error
    const isNetworkError = error.code === 'ERR_NETWORK' || error.message === 'Network Error' || error.code === 'ECONNABORTED';
    if (isNetworkError && config && !config._isRetry) {
      config._retryCount = (config._retryCount || 0) + 1;
      if (config._retryCount <= 2) {
        await new Promise((resolve) => setTimeout(resolve, 500 * config._retryCount));
        return api(config);
      }
      // Only dispatch backend-error after all retries are exhausted
      window.dispatchEvent(new Event('backend-error'));
    }

    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
