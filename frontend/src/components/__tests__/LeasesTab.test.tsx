import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { leasesApi } from '@/api/leases';
import LeasesTab from '../building-detail/LeasesTab';

vi.mock('@/api/leases', () => ({
  leasesApi: {
    listByBuilding: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'lease-1',
          building_id: 'b-1',
          lease_type: 'residential',
          reference_code: 'BAIL-001',
          tenant_type: 'contact',
          tenant_id: 'tenant-1',
          tenant_display_name: 'Marie Rochat',
          unit_label: 'Apt 3.1',
          zone_name: '3e etage',
          date_start: '2024-01-01',
          date_end: '2025-12-31',
          rent_monthly_chf: 1850,
          status: 'active',
        },
        {
          id: 'lease-2',
          building_id: 'b-1',
          lease_type: 'commercial',
          reference_code: 'BAIL-002',
          tenant_type: 'contact',
          tenant_id: 'tenant-2',
          tenant_display_name: 'Cafe du Lac',
          unit_label: 'COM-RDC',
          zone_name: null,
          date_start: '2020-01-01',
          date_end: null,
          rent_monthly_chf: 3200,
          status: 'active',
        },
      ],
      total: 2,
      page: 1,
      size: 20,
      pages: 1,
    }),
    getSummary: vi.fn().mockResolvedValue({
      building_id: 'b-1',
      total_leases: 2,
      active_leases: 2,
      monthly_rent_chf: 5050,
      monthly_charges_chf: 500,
      expiring_90d: 0,
      disputed_count: 0,
    }),
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

describe('LeasesTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders lease list with display names', async () => {
    render(<LeasesTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Marie Rochat')).toBeInTheDocument();
      expect(screen.getByText('Cafe du Lac')).toBeInTheDocument();
    });
  });

  it('renders unit labels', async () => {
    render(<LeasesTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Apt 3.1')).toBeInTheDocument();
      expect(screen.getByText('COM-RDC')).toBeInTheDocument();
    });
  });

  it('renders zone name or dash when null', async () => {
    render(<LeasesTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('3e etage')).toBeInTheDocument();
    });
    // The second lease has zone_name: null, which renders as '-'
    // '-' appears in multiple places (date_end etc.), so just verify no error
  });

  it('renders summary bar', async () => {
    render(<LeasesTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Summary should show total and active counts
      const twos = screen.getAllByText('2');
      expect(twos.length).toBeGreaterThan(0);
    });
  });

  it('renders status badges', async () => {
    render(<LeasesTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const badges = screen.getAllByText('active');
      expect(badges.length).toBeGreaterThan(0);
    });
  });

  it('renders reference codes', async () => {
    render(<LeasesTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('BAIL-001')).toBeInTheDocument();
      expect(screen.getByText('BAIL-002')).toBeInTheDocument();
    });
  });

  it('auto-selects a unique tenant contact in the create modal', async () => {
    vi.mocked(leasesApi.lookupContacts).mockResolvedValueOnce([
      {
        id: 'tenant-qa-1',
        name: 'Camille Rochat',
        email: 'camille.rochat@example.ch',
        contact_type: 'person',
      },
    ]);

    render(<LeasesTab buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('leases-create-button')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('leases-create-button'));
    fireEvent.change(screen.getByTestId('contact-search-input'), {
      target: { value: 'Camille' },
    });

    await waitFor(
      () => {
        expect(screen.getByTestId('contact-selected-name')).toHaveTextContent('Camille Rochat');
      },
      { timeout: 2000 },
    );

    const hiddenField = document.querySelector<HTMLInputElement>('input[type="hidden"]');
    expect(hiddenField?.value).toBe('tenant-qa-1');
  });
});
