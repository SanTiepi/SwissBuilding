import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import MarketplaceRFQ from '@/pages/MarketplaceRFQ';

vi.mock('@/api/marketplaceRfq', () => ({
  marketplaceRfqApi: {
    listRequests: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'req-1',
          building_id: 'b-1',
          requester_user_id: 'u-1',
          requester_org_id: null,
          title: 'Desamiantage facade',
          description: 'Test description',
          pollutant_types: ['asbestos'],
          work_category: 'major',
          estimated_area_m2: 320,
          deadline: '2026-09-30',
          status: 'published',
          diagnostic_publication_id: null,
          budget_indication: '50k_100k',
          site_access_notes: null,
          published_at: '2026-03-01T00:00:00Z',
          closed_at: null,
          created_at: '2026-02-15T00:00:00Z',
          updated_at: '2026-03-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      size: 50,
      pages: 1,
    }),
    listQuotes: vi.fn().mockResolvedValue([]),
    createRequest: vi.fn(),
    awardQuote: vi.fn(),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

vi.mock('@/utils/formatters', () => ({
  cn: (...args: (string | undefined | false)[]) => args.filter(Boolean).join(' '),
  formatDateTime: (d: string) => d,
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>,
  );
}

describe('MarketplaceRFQ', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page title', async () => {
    renderWithProviders(<MarketplaceRFQ />);
    expect(screen.getByText('marketplace.rfq_title')).toBeInTheDocument();
  });

  it('displays RFQ list after loading', async () => {
    renderWithProviders(<MarketplaceRFQ />);
    await waitFor(() => {
      expect(screen.getByText('Desamiantage facade')).toBeInTheDocument();
    });
  });

  it('shows status badge', async () => {
    renderWithProviders(<MarketplaceRFQ />);
    await waitFor(() => {
      expect(screen.getByText('Published')).toBeInTheDocument();
    });
  });

  it('shows deadline info', async () => {
    renderWithProviders(<MarketplaceRFQ />);
    await waitFor(() => {
      expect(screen.getByText(/2026-09-30/)).toBeInTheDocument();
    });
  });

  it('has New RFQ button', () => {
    renderWithProviders(<MarketplaceRFQ />);
    expect(screen.getByText('marketplace.new_rfq')).toBeInTheDocument();
  });
});
