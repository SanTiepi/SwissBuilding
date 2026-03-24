import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ContractsTab from '../building-detail/ContractsTab';

vi.mock('@/api/contracts', () => ({
  contractsApi: {
    listByBuilding: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'contract-1',
          building_id: 'b-1',
          contract_type: 'maintenance',
          reference_code: 'CTR-001',
          title: 'Elevator maintenance',
          counterparty_type: 'contact',
          date_start: '2024-01-01',
          date_end: '2025-12-31',
          annual_cost_chf: 4800,
          status: 'active',
          counterparty_display_name: 'Schindler SA',
        },
        {
          id: 'contract-2',
          building_id: 'b-1',
          contract_type: 'cleaning',
          reference_code: 'CTR-002',
          title: 'Building cleaning',
          counterparty_type: 'organization',
          date_start: '2023-06-01',
          date_end: null,
          annual_cost_chf: 7200,
          status: 'active',
          counterparty_display_name: 'CleanPro GmbH',
        },
      ],
      total: 2,
      page: 1,
      size: 20,
      pages: 1,
    }),
    getSummary: vi.fn().mockResolvedValue({
      building_id: 'b-1',
      total_contracts: 2,
      active_contracts: 2,
      annual_cost_chf: 12000,
      expiring_90d: 0,
      auto_renewal_count: 1,
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

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('ContractsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders contract list with display names', async () => {
    render(<ContractsTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Schindler SA')).toBeInTheDocument();
      expect(screen.getByText('CleanPro GmbH')).toBeInTheDocument();
    });
  });

  it('renders contract titles', async () => {
    render(<ContractsTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Elevator maintenance')).toBeInTheDocument();
      expect(screen.getByText('Building cleaning')).toBeInTheDocument();
    });
  });

  it('renders summary bar', async () => {
    render(<ContractsTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const twos = screen.getAllByText('2');
      expect(twos.length).toBeGreaterThan(0);
    });
  });

  it('renders status badges', async () => {
    render(<ContractsTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const badges = screen.getAllByText('active');
      expect(badges.length).toBeGreaterThan(0);
    });
  });

  it('renders reference codes', async () => {
    render(<ContractsTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('CTR-001')).toBeInTheDocument();
      expect(screen.getByText('CTR-002')).toBeInTheDocument();
    });
  });
});
