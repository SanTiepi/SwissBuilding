import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { expansionApi } from '@/api/expansion';
import AdminExpansion from '@/pages/AdminExpansion';

vi.mock('@/api/expansion', () => ({
  expansionApi: {
    listOpportunities: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'opp-1',
          opportunity_type: 'upsell',
          priority: 'high',
          recommended_action: 'Propose diagnostic extension',
          evidence: '3 buildings without PCB diagnostic',
          status: 'open',
          building_id: 'b-1',
          org_id: null,
          created_at: '2026-03-20T00:00:00Z',
          acted_at: null,
        },
        {
          id: 'opp-2',
          opportunity_type: 'cross_sell',
          priority: 'medium',
          recommended_action: 'Offer portfolio view',
          evidence: 'Org has 5+ buildings',
          status: 'open',
          building_id: null,
          org_id: 'org-1',
          created_at: '2026-03-19T00:00:00Z',
          acted_at: null,
        },
      ],
      total: 2,
      page: 1,
      size: 50,
      pages: 1,
    }),
    listTriggers: vi.fn().mockResolvedValue([
      {
        id: 'tr-1',
        trigger_type: 'new_building',
        source_entity: 'building:b-5',
        detail: 'New building added to portfolio',
        created_at: '2026-03-21T00:00:00Z',
      },
    ]),
    listDistributionSignals: vi.fn().mockResolvedValue([
      {
        id: 'ds-1',
        signal_type: 'shared_link_opened',
        channel: 'email',
        reach: 12,
        detail: 'Shared link accessed by external user',
        created_at: '2026-03-21T00:00:00Z',
      },
    ]),
    actOnOpportunity: vi.fn().mockResolvedValue({ id: 'opp-1', status: 'acted' }),
    dismissOpportunity: vi.fn().mockResolvedValue({ id: 'opp-2', status: 'dismissed' }),
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

describe('AdminExpansion', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page title', async () => {
    render(<AdminExpansion />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('expansion.title')).toBeInTheDocument();
    });
  });

  it('renders opportunities table', async () => {
    render(<AdminExpansion />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('Propose diagnostic extension')).toBeInTheDocument();
      expect(screen.getByText('Offer portfolio view')).toBeInTheDocument();
    });
  });

  it('renders priority badges', async () => {
    render(<AdminExpansion />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('high')).toBeInTheDocument();
      expect(screen.getByText('medium')).toBeInTheDocument();
    });
  });

  it('renders evidence text', async () => {
    render(<AdminExpansion />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('3 buildings without PCB diagnostic')).toBeInTheDocument();
    });
  });

  it('renders triggers feed', async () => {
    render(<AdminExpansion />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('new_building')).toBeInTheDocument();
    });
  });

  it('renders distribution signals', async () => {
    render(<AdminExpansion />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('shared_link_opened')).toBeInTheDocument();
    });
  });

  it('calls act on opportunity', async () => {
    render(<AdminExpansion />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('act-opp-1')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('act-opp-1'));
    await waitFor(() => {
      expect(expansionApi.actOnOpportunity).toHaveBeenCalledWith('opp-1');
    });
  });

  it('calls dismiss on opportunity', async () => {
    render(<AdminExpansion />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('dismiss-opp-2')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('dismiss-opp-2'));
    await waitFor(() => {
      expect(expansionApi.dismissOpportunity).toHaveBeenCalledWith('opp-2');
    });
  });
});
