import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { remediationIntelligenceApi } from '@/api/remediationIntelligence';
import { QuoteInsightsPanel } from '../marketplace/QuoteInsightsPanel';

vi.mock('@/api/remediationIntelligence', () => ({
  remediationIntelligenceApi: {
    getComparisonInsights: vi.fn().mockResolvedValue({
      request_id: 'req-1',
      scope_coverage_matrix: [
        { item: 'asbestos_removal', present_in: ['CompanyA', 'CompanyB'], missing_from: [] },
        { item: 'air_monitoring', present_in: ['CompanyA'], missing_from: ['CompanyB'] },
      ],
      price_spread: { min: 40000, max: 55000, median: 47500, range_pct: 37.5 },
      timeline_spread: { min_weeks: 4, max_weeks: 8, median_weeks: 6 },
      common_exclusions: ['scaffolding', 'permits'],
      ambiguity_flags: [
        { field: 'timeline_weeks', quotes_affected: ['CompanyA'], description: 'Multiple timelines mentioned' },
      ],
      quote_count: 2,
    }),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('QuoteInsightsPanel', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    vi.clearAllMocks();
  });

  const renderPanel = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <QuoteInsightsPanel requestId="req-1" />
      </QueryClientProvider>,
    );

  it('renders price spread', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText(/40.*000/)).toBeTruthy();
      expect(screen.getByText(/55.*000/)).toBeTruthy();
    });
  });

  it('renders scope coverage matrix', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('asbestos_removal')).toBeTruthy();
      expect(screen.getByText('air_monitoring')).toBeTruthy();
    });
  });

  it('shows common exclusions', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('scaffolding')).toBeTruthy();
      expect(screen.getByText('permits')).toBeTruthy();
    });
  });

  it('shows ambiguity flags', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText(/Multiple timelines/)).toBeTruthy();
    });
  });

  it('shows quote count', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('(2 quotes)')).toBeTruthy();
    });
  });

  it('shows timeline spread', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('4w')).toBeTruthy();
      expect(screen.getByText('8w')).toBeTruthy();
    });
  });

  it('shows no quotes message when empty', async () => {
    vi.mocked(remediationIntelligenceApi.getComparisonInsights).mockResolvedValueOnce({
      request_id: 'req-1',
      scope_coverage_matrix: [],
      price_spread: { min: 0, max: 0, median: 0, range_pct: 0 },
      timeline_spread: { min_weeks: 0, max_weeks: 0, median_weeks: 0 },
      common_exclusions: [],
      ambiguity_flags: [],
      quote_count: 0,
    });
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('intelligence.no_quotes')).toBeTruthy();
    });
  });
});
