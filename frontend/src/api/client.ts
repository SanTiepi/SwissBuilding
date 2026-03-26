import axios, { type AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/store/authStore';

const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1000;

export interface ApiRequestConfig extends AxiosRequestConfig {
  skipRetry?: boolean;
}

interface RetryableConfig extends InternalAxiosRequestConfig {
  __retryCount?: number;
  skipRetry?: boolean;
}

function isRetryable(error: AxiosError): boolean {
  if (error.code === 'ERR_CANCELED') return false;
  if (!error.response) return true; // network error
  const status = error.response.status;
  return status >= 500 && status <= 599;
}

export const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Retry interceptor (runs first on error)
apiClient.interceptors.response.use(undefined, async (error: AxiosError) => {
  const config = error.config as RetryableConfig | undefined;
  if (!config || !isRetryable(error)) return Promise.reject(error);
  if (config.skipRetry) return Promise.reject(error);

  config.__retryCount = config.__retryCount ?? 0;
  if (config.__retryCount >= MAX_RETRIES) return Promise.reject(error);

  config.__retryCount += 1;
  const delay = BASE_DELAY_MS * Math.pow(2, config.__retryCount - 1);
  await new Promise((resolve) => setTimeout(resolve, delay));

  return apiClient(config);
});

// 401 interceptor (runs after retries are exhausted)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url ?? '';
    const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/register');
    if (error.response?.status === 401 && !isAuthEndpoint) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);
