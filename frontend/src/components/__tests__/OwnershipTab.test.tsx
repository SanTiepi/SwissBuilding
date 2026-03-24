import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import OwnershipTab from '../building-detail/OwnershipTab';

vi.mock('@/api/ownership', () => ({
  ownershipApi: {
    listByBuilding: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'own-1',
          building_id: 'b-1',
          owner_type: 'contact',
          owner_id: 'owner-1',
          share_pct: 60,
          ownership_type: 'co_ownership',
          status: 'active',
          acquisition_date: '2020-01-15',
          owner_display_name: 'Jean Dupont',
        },
        {
          id: 'own-2',
          building_id: 'b-1',
          owner_type: 'contact',
          owner_id: 'owner-2',
          share_pct: 40,
          ownership_type: 'co_ownership',
          status: 'active',
          acquisition_date: '2020-01-15',
          owner_display_name: 'Marie Rochat',
        },
      ],
      total: 2,
      page: 1,
      size: 20,
      pages: 1,
    }),
    getSummary: vi.fn().mockResolvedValue({
      building_id: 'b-1',
      total_records: 2,
      active_records: 2,
      total_share_pct: 100,
      owner_count: 2,
      co_ownership: true,
    }),
    lookupContacts: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock('@/api/leases', () => ({
  leasesApi: {
    lookupContacts: vi.fn().mockResolvedValue([]),
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

describe('OwnershipTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders ownership list with display names', async () => {
    render(<OwnershipTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Jean Dupont')).toBeInTheDocument();
      expect(screen.getByText('Marie Rochat')).toBeInTheDocument();
    });
  });

  it('renders share percentages', async () => {
    render(<OwnershipTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('60%')).toBeInTheDocument();
      expect(screen.getByText('40%')).toBeInTheDocument();
    });
  });

  it('renders summary bar', async () => {
    render(<OwnershipTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Summary should show total and active counts
      const twos = screen.getAllByText('2');
      expect(twos.length).toBeGreaterThan(0);
    });
  });

  it('renders status badges', async () => {
    render(<OwnershipTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const badges = screen.getAllByText('active');
      expect(badges.length).toBeGreaterThan(0);
    });
  });

  it('renders acquisition dates', async () => {
    render(<OwnershipTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const dates = screen.getAllByText('2020-01-15');
      expect(dates.length).toBeGreaterThan(0);
    });
  });

  it('renders co-ownership indicator in summary', async () => {
    render(<OwnershipTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('100.0%')).toBeInTheDocument();
    });
  });
});
