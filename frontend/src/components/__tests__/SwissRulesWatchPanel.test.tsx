import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SwissRulesWatchPanel from '../building-detail/SwissRulesWatchPanel';
import {
  swissRulesWatchApi,
  type RuleSource,
  type RuleChangeEvent,
  type BuildingCommuneContext,
} from '@/api/swissRulesWatch';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/utils/formatters', () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(' '),
  formatDate: (d: string) => d,
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ user: { role: 'admin' }, isAuthenticated: true }),
}));

vi.mock('@/api/swissRulesWatch', () => ({
  swissRulesWatchApi: {
    getBuildingCommuneContext: vi.fn(),
    listSources: vi.fn(),
    getUnreviewedChanges: vi.fn(),
  },
}));

const mockCommuneCtx: BuildingCommuneContext = {
  building_id: 'b-1',
  city: 'Lausanne',
  canton: 'VD',
  adapter: {
    id: 'a-1',
    commune_code: '5586',
    commune_name: 'Lausanne',
    canton_code: 'VD',
    adapter_status: 'active',
    supports_procedure_projection: true,
    supports_rule_projection: true,
    fallback_mode: 'canton_default',
    source_ids: ['s-1'],
    notes: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  overrides: [
    {
      id: 'ov-1',
      commune_code: '5586',
      canton_code: 'VD',
      override_type: 'stricter_threshold',
      rule_reference: 'OTConst Art. 60a',
      impact_summary: 'Lower threshold for asbestos',
      review_required: true,
      confidence_level: 'confirmed',
      source_id: null,
      effective_from: '2026-01-01',
      effective_to: null,
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ],
};

const mockSources: RuleSource[] = [
  {
    id: 's-1',
    source_code: 'vd-otconst',
    source_name: 'OTConst VD',
    source_url: 'https://example.com',
    watch_tier: 'weekly',
    last_checked_at: '2026-03-20T10:00:00Z',
    last_changed_at: '2026-03-15T10:00:00Z',
    freshness_state: 'current',
    change_types_detected: null,
    is_active: true,
    notes: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-03-20T10:00:00Z',
  },
  {
    id: 's-2',
    source_code: 'ge-regie',
    source_name: 'Reglement GE',
    source_url: null,
    watch_tier: 'monthly',
    last_checked_at: '2026-01-01T10:00:00Z',
    last_changed_at: null,
    freshness_state: 'stale',
    change_types_detected: null,
    is_active: true,
    notes: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T10:00:00Z',
  },
];

const mockChanges: RuleChangeEvent[] = [
  {
    id: 'ch-1',
    source_id: 's-1',
    event_type: 'amended_rule',
    title: 'Updated asbestos threshold',
    description: null,
    impact_summary: 'Lowered from 1000 to 500 mg/kg',
    detected_at: '2026-03-18T10:00:00Z',
    reviewed: false,
    reviewed_by_user_id: null,
    reviewed_at: null,
    review_notes: null,
    affects_buildings: true,
    created_at: '2026-03-18T10:00:00Z',
  },
];

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('SwissRulesWatchPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(swissRulesWatchApi.getBuildingCommuneContext).mockResolvedValue(mockCommuneCtx);
    vi.mocked(swissRulesWatchApi.listSources).mockResolvedValue(mockSources);
    vi.mocked(swissRulesWatchApi.getUnreviewedChanges).mockResolvedValue(mockChanges);
  });

  it('renders loading state initially', () => {
    vi.mocked(swissRulesWatchApi.getBuildingCommuneContext).mockReturnValue(new Promise(() => {}));
    render(<SwissRulesWatchPanel buildingId="b-1" />, { wrapper: createWrapper() });
    expect(screen.getByTestId('swiss-rules-watch-loading')).toBeInTheDocument();
  });

  it('renders panel with title after loading', async () => {
    render(<SwissRulesWatchPanel buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('swiss-rules-watch-panel')).toBeInTheDocument();
    });
    expect(screen.getByText('swiss_rules.title')).toBeInTheDocument();
  });

  it('shows commune context with adapter info', async () => {
    render(<SwissRulesWatchPanel buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('commune-context')).toBeInTheDocument();
    });
    expect(screen.getByTestId('adapter-info')).toBeInTheDocument();
    expect(screen.getByText('Lausanne')).toBeInTheDocument();
  });

  it('shows no-adapter message when adapter is null', async () => {
    vi.mocked(swissRulesWatchApi.getBuildingCommuneContext).mockResolvedValue({
      ...mockCommuneCtx,
      adapter: null,
      overrides: [],
    });
    vi.mocked(swissRulesWatchApi.listSources).mockResolvedValue([]);
    render(<SwissRulesWatchPanel buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('no-adapter')).toBeInTheDocument();
    });
  });

  it('renders active rule sources with freshness badges', async () => {
    render(<SwissRulesWatchPanel buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('rule-sources-list')).toBeInTheDocument();
    });
    expect(screen.getByTestId('source-row-s-1')).toBeInTheDocument();
    expect(screen.getByTestId('freshness-badge-s-1')).toHaveTextContent('swiss_rules.freshness_current');
    expect(screen.getByTestId('freshness-badge-s-2')).toHaveTextContent('swiss_rules.freshness_stale');
  });

  it('shows unreviewed changes for admin users', async () => {
    render(<SwissRulesWatchPanel buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('unreviewed-changes')).toBeInTheDocument();
    });
    expect(screen.getByTestId('change-row-ch-1')).toBeInTheDocument();
    expect(screen.getByText('Updated asbestos threshold')).toBeInTheDocument();
  });

  it('shows override alerts', async () => {
    render(<SwissRulesWatchPanel buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('override-alerts')).toBeInTheDocument();
    });
    expect(screen.getByTestId('override-ov-1')).toBeInTheDocument();
    expect(screen.getByText('Lower threshold for asbestos')).toBeInTheDocument();
  });

  it('calls API with correct building ID', async () => {
    render(<SwissRulesWatchPanel buildingId="b-42" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(swissRulesWatchApi.getBuildingCommuneContext).toHaveBeenCalledWith('b-42');
    });
  });

  it('shows empty state when no data', async () => {
    vi.mocked(swissRulesWatchApi.getBuildingCommuneContext).mockResolvedValue({
      building_id: 'b-1',
      city: 'Test',
      canton: 'VD',
      adapter: null,
      overrides: [],
    });
    vi.mocked(swissRulesWatchApi.listSources).mockResolvedValue([]);
    vi.mocked(swissRulesWatchApi.getUnreviewedChanges).mockResolvedValue([]);
    render(<SwissRulesWatchPanel buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('swiss-rules-empty')).toBeInTheDocument();
    });
  });
});
