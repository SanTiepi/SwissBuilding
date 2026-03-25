import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import AdminProcedures from '@/pages/AdminProcedures';

vi.mock('@/api/permitProcedures', () => ({
  permitProceduresApi: {
    getAdminProcedures: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'proc-1',
          building_id: 'b-1',
          building_address: 'Rue de Bourg 12, 1003 Lausanne',
          procedure_type: 'building_permit',
          title: 'Renovation toiture',
          status: 'complement_requested',
          authority_name: 'CAMAC Vaud',
          reference_number: 'REF-001',
          blocks_activities: true,
          submitted_at: '2026-01-10',
          created_at: '2026-01-05',
          days_pending: 74,
          open_requests: 2,
        },
        {
          id: 'proc-2',
          building_id: 'b-2',
          building_address: 'Avenue de la Gare 5, 1800 Vevey',
          procedure_type: 'renovation_permit',
          title: 'Desamiantage facade',
          status: 'submitted',
          authority_name: 'Service de la construction',
          reference_number: null,
          blocks_activities: false,
          submitted_at: '2026-02-20',
          created_at: '2026-02-18',
          days_pending: 33,
          open_requests: 0,
        },
      ],
      total: 2,
      page: 1,
      size: 25,
      pages: 1,
    }),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    user: { id: 'u-admin', role: 'admin', email: 'admin@test.ch' },
    token: 'test-token',
  }),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

describe('AdminProcedures', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page title', async () => {
    render(<AdminProcedures />, { wrapper: createWrapper() });
    expect(screen.getByText('procedure.admin_title')).toBeInTheDocument();
  });

  it('renders procedure rows', async () => {
    render(<AdminProcedures />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('Renovation toiture')).toBeInTheDocument();
      expect(screen.getByText('Desamiantage facade')).toBeInTheDocument();
    });
  });

  it('renders building addresses', async () => {
    render(<AdminProcedures />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('Rue de Bourg 12, 1003 Lausanne')).toBeInTheDocument();
      expect(screen.getByText('Avenue de la Gare 5, 1800 Vevey')).toBeInTheDocument();
    });
  });

  it('renders authority names', async () => {
    render(<AdminProcedures />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('CAMAC Vaud')).toBeInTheDocument();
    });
  });

  it('renders days pending', async () => {
    render(<AdminProcedures />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('74')).toBeInTheDocument();
      expect(screen.getByText('33')).toBeInTheDocument();
    });
  });

  it('renders open requests count', async () => {
    render(<AdminProcedures />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });

  it('renders filter controls', () => {
    render(<AdminProcedures />, { wrapper: createWrapper() });
    expect(screen.getByTestId('filter-status')).toBeInTheDocument();
    expect(screen.getByTestId('filter-type')).toBeInTheDocument();
  });

  it('renders procedures table', async () => {
    render(<AdminProcedures />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('procedures-table')).toBeInTheDocument();
    });
  });
});
