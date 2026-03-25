import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { remediationIntelligenceApi } from '@/api/remediationIntelligence';
import { ReadinessAdvisorPanel } from '../building-detail/ReadinessAdvisorPanel';

vi.mock('@/api/remediationIntelligence', () => ({
  remediationIntelligenceApi: {
    getReadinessAdvisor: vi.fn().mockResolvedValue({
      building_id: 'b-1',
      suggestions: [
        {
          type: 'blocker',
          title: 'Unresolved unknown: missing_sample',
          description: 'Unknown issue in category missing_sample needs resolution.',
          evidence_refs: ['ref-1'],
          confidence: 0.9,
          recommended_action: 'Resolve the unknown by providing missing information.',
        },
        {
          type: 'missing_pollutant',
          title: 'No diagnostic for radon',
          description: 'No diagnostic covering radon has been performed.',
          evidence_refs: [],
          confidence: 0.95,
          recommended_action: 'Commission a radon diagnostic.',
        },
        {
          type: 'proof_gap',
          title: '2 draft compliance artefacts',
          description: '2 compliance artefacts remain in draft.',
          evidence_refs: [],
          confidence: 0.8,
          recommended_action: 'Submit draft compliance artefacts.',
        },
      ],
      generated_at: '2026-03-25T10:00:00Z',
    }),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('ReadinessAdvisorPanel', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    vi.clearAllMocks();
  });

  const renderPanel = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <ReadinessAdvisorPanel buildingId="b-1" />
      </QueryClientProvider>,
    );

  it('renders suggestions', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText(/Unresolved unknown/)).toBeTruthy();
    });
  });

  it('shows blocker badge', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Blocker')).toBeTruthy();
    });
  });

  it('shows missing pollutant suggestion', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText(/No diagnostic for radon/)).toBeTruthy();
    });
  });

  it('shows recommended action', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText(/Resolve the unknown/)).toBeTruthy();
    });
  });

  it('shows proof gap', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getAllByText(/draft compliance/).length).toBeGreaterThan(0);
    });
  });

  it('displays confidence indicator', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('90%')).toBeTruthy();
    });
  });

  it('shows no issues when empty', async () => {
    vi.mocked(remediationIntelligenceApi.getReadinessAdvisor).mockResolvedValueOnce({
      building_id: 'b-1',
      suggestions: [],
      generated_at: '2026-03-25T10:00:00Z',
    });
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('intelligence.no_suggestions')).toBeTruthy();
    });
  });
});
