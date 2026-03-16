import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import ExportJobs from '@/pages/ExportJobs';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: null,
    token: null,
    isAuthenticated: false,
    login: {},
    register: {},
    logout: vi.fn(),
    isLoading: false,
  }),
}));

const mockList = vi.fn();
vi.mock('@/api/exports', () => ({
  exportsApi: {
    list: (...args: unknown[]) => mockList(...args),
  },
}));

vi.mock('@/api/backgroundJobs', () => ({
  backgroundJobsApi: {
    list: vi.fn().mockResolvedValue([]),
    get: vi.fn(),
    cancel: vi.fn(),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ExportJobs', () => {
  beforeEach(() => {
    mockList.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when export jobs fail to load', async () => {
    mockList.mockRejectedValue(new Error('boom'));

    render(<ExportJobs />, { wrapper });

    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders empty state when there are no export jobs', async () => {
    mockList.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      size: 20,
      pages: 0,
    });

    render(<ExportJobs />, { wrapper });

    expect(await screen.findByText('export.no_exports')).toBeInTheDocument();
  });
});
