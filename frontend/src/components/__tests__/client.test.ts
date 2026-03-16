import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';

// Mock authStore before importing client
const mockLogout = vi.fn();
const mockGetState = vi.fn((): { token: string | null; logout: typeof mockLogout } => ({
  token: null,
  logout: mockLogout,
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: { getState: () => mockGetState() },
}));

// We need to import after mocks are set up
import { apiClient } from '@/api/client';

// Helper to build a minimal AxiosError-like object
function makeAxiosError(opts: {
  status?: number;
  code?: string;
  hasResponse?: boolean;
  config?: Partial<InternalAxiosRequestConfig>;
}): AxiosError {
  const response =
    opts.hasResponse !== false && opts.status
      ? ({ status: opts.status, data: {}, headers: {}, statusText: '' } as unknown as AxiosResponse)
      : undefined;

  return {
    isAxiosError: true,
    name: 'AxiosError',
    message: 'test error',
    toJSON: () => ({}),
    code: opts.code,
    response,
    config: (opts.config ?? { headers: {} }) as InternalAxiosRequestConfig,
  } as AxiosError;
}

describe('apiClient configuration', () => {
  it('has baseURL set to /api/v1', () => {
    expect(apiClient.defaults.baseURL).toBe('/api/v1');
  });

  it('has timeout set to 30000ms', () => {
    expect(apiClient.defaults.timeout).toBe(30000);
  });

  it('has Content-Type header set to application/json', () => {
    expect(apiClient.defaults.headers['Content-Type']).toBe('application/json');
  });
});

describe('request interceptor - auth token injection', () => {
  beforeEach(() => {
    mockGetState.mockReset();
    mockLogout.mockReset();
  });

  it('adds Authorization header when token is present', async () => {
    mockGetState.mockReturnValue({ token: 'test-jwt-token', logout: mockLogout });

    // Run through the request interceptor chain manually
    const handlers = (
      apiClient.interceptors.request as unknown as {
        handlers: Array<{ fulfilled: (config: InternalAxiosRequestConfig) => InternalAxiosRequestConfig }>;
      }
    ).handlers;
    const interceptor = handlers[0].fulfilled;

    const config = { headers: { set: vi.fn() } } as unknown as InternalAxiosRequestConfig;
    // Axios headers are a special object; simulate with a proxy
    const headersObj: Record<string, string> = {};
    const configWithHeaders = {
      ...config,
      headers: new Proxy(headersObj, {
        set(target, prop, value) {
          target[prop as string] = value;
          return true;
        },
        get(target, prop) {
          return target[prop as string];
        },
      }),
    } as unknown as InternalAxiosRequestConfig;

    const result = interceptor(configWithHeaders);
    expect((result.headers as unknown as Record<string, string>).Authorization).toBe('Bearer test-jwt-token');
  });

  it('does not add Authorization header when no token', async () => {
    mockGetState.mockReturnValue({ token: null, logout: mockLogout });

    const handlers = (
      apiClient.interceptors.request as unknown as {
        handlers: Array<{ fulfilled: (config: InternalAxiosRequestConfig) => InternalAxiosRequestConfig }>;
      }
    ).handlers;
    const interceptor = handlers[0].fulfilled;

    const headersObj: Record<string, string> = {};
    const configWithHeaders = {
      headers: new Proxy(headersObj, {
        set(target, prop, value) {
          target[prop as string] = value;
          return true;
        },
        get(target, prop) {
          return target[prop as string];
        },
      }),
    } as unknown as InternalAxiosRequestConfig;

    const result = interceptor(configWithHeaders);
    expect((result.headers as unknown as Record<string, string>).Authorization).toBeUndefined();
  });
});

describe('isRetryable logic (via response interceptor behavior)', () => {
  // The isRetryable function is not exported, but we can test its logic
  // by verifying the response interceptor behavior with different error types.
  // We extract the retry interceptor handler directly.

  let retryInterceptor: (error: AxiosError) => Promise<unknown>;

  beforeEach(() => {
    const handlers = (
      apiClient.interceptors.response as unknown as {
        handlers: Array<{ rejected?: (error: AxiosError) => Promise<unknown> }>;
      }
    ).handlers;
    // The retry interceptor is the first one (index 0)
    retryInterceptor = handlers[0].rejected!;
    mockGetState.mockReturnValue({ token: null, logout: mockLogout });
  });

  it('rejects immediately for 4xx errors (not retryable)', async () => {
    const error = makeAxiosError({ status: 400 });
    await expect(retryInterceptor(error)).rejects.toBe(error);
  });

  it('rejects immediately for 401 errors (not retryable)', async () => {
    const error = makeAxiosError({ status: 401 });
    await expect(retryInterceptor(error)).rejects.toBe(error);
  });

  it('rejects immediately for 404 errors (not retryable)', async () => {
    const error = makeAxiosError({ status: 404 });
    await expect(retryInterceptor(error)).rejects.toBe(error);
  });

  it('rejects immediately for canceled requests (ERR_CANCELED)', async () => {
    const error = makeAxiosError({ code: 'ERR_CANCELED', hasResponse: false });
    await expect(retryInterceptor(error)).rejects.toBe(error);
  });

  it('rejects immediately when config is missing', async () => {
    const error = makeAxiosError({ status: 500 });
    // Remove config to simulate missing config
    (error as { config: undefined }).config = undefined;
    await expect(retryInterceptor(error)).rejects.toBe(error);
  });
});

describe('401 interceptor - logout on unauthorized', () => {
  let authInterceptor: (error: AxiosError) => Promise<unknown>;

  beforeEach(() => {
    mockGetState.mockReset();
    mockLogout.mockReset();
    mockGetState.mockReturnValue({ token: 'some-token', logout: mockLogout });

    const handlers = (
      apiClient.interceptors.response as unknown as {
        handlers: Array<{ rejected?: (error: AxiosError) => Promise<unknown> }>;
      }
    ).handlers;
    // The 401 interceptor is the second one (index 1)
    authInterceptor = handlers[1].rejected!;
  });

  it('calls logout and redirects on 401 for non-auth endpoints', async () => {
    const error = makeAxiosError({
      status: 401,
      config: { url: '/buildings', headers: {} } as Partial<InternalAxiosRequestConfig>,
    });

    // Mock window.location
    const originalLocation = window.location;
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { href: '' },
    });

    await expect(authInterceptor(error)).rejects.toBe(error);
    expect(mockLogout).toHaveBeenCalled();
    expect(window.location.href).toBe('/login');

    // Restore
    Object.defineProperty(window, 'location', {
      writable: true,
      value: originalLocation,
    });
  });

  it('does NOT call logout for /auth/login endpoint', async () => {
    const error = makeAxiosError({
      status: 401,
      config: { url: '/auth/login', headers: {} } as Partial<InternalAxiosRequestConfig>,
    });

    await expect(authInterceptor(error)).rejects.toBe(error);
    expect(mockLogout).not.toHaveBeenCalled();
  });

  it('does NOT call logout for /auth/register endpoint', async () => {
    const error = makeAxiosError({
      status: 401,
      config: { url: '/auth/register', headers: {} } as Partial<InternalAxiosRequestConfig>,
    });

    await expect(authInterceptor(error)).rejects.toBe(error);
    expect(mockLogout).not.toHaveBeenCalled();
  });
});
