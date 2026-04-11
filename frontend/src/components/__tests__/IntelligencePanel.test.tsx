import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import IntelligencePanel from '@/components/IntelligencePanel';

vi.mock('@/api/crossLayerIntelligence', () => ({
  crossLayerIntelligenceApi: {
    getBuildingIntelligence: vi.fn().mockResolvedValue([
      {
        insight_id: 'abc123',
        insight_type: 'risk_cascade',
        severity: 'critical',
        title: 'Risque systemique: non-conformite dans 45 jours',
        description: 'Score de preuve faible (28/100), 2 actions en retard, 1 diagnostic expirant.',
        evidence: [
          { layer: 'evidence_score', signal: 'low_score', value: 28 },
          { layer: 'actions', signal: 'overdue_count', value: 2 },
        ],
        recommendation: 'Lancer un plan urgence',
        confidence: 0.85,
        estimated_impact: 'Blocage reglementaire dans 45 jours',
      },
      {
        insight_id: 'def456',
        insight_type: 'silent_degradation',
        severity: 'warning',
        title: 'Degradation silencieuse: inactif depuis 240 jours',
        description: 'Aucune activite depuis 240 jours.',
        evidence: [{ layer: 'activity', signal: 'days_since_last', value: 240 }],
        recommendation: 'Verifier etat du batiment',
        confidence: 0.7,
        estimated_impact: 'Perte progressive de fiabilite',
      },
      {
        insight_id: 'ghi789',
        insight_type: 'hidden_opportunity',
        severity: 'opportunity',
        title: 'Eligible au Certificat BatiConnect',
        description: 'Score eleve, completude haute.',
        evidence: [{ layer: 'evidence_score', signal: 'high_score', value: 82 }],
        recommendation: 'Initier la certification',
        confidence: 0.85,
        estimated_impact: 'Valorisation + reduction assurance',
      },
    ]),
    getPortfolioIntelligence: vi.fn().mockResolvedValue([]),
    getIntelligenceSummary: vi.fn().mockResolvedValue({
      total_insights: 3,
      by_type: { risk_cascade: 1, silent_degradation: 1, hidden_opportunity: 1 },
      by_severity: { critical: 1, warning: 1, opportunity: 1 },
      top_critical: [],
      computed_at: '2026-03-30T10:00:00Z',
    }),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('IntelligencePanel', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    vi.clearAllMocks();
  });

  const renderPanel = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <IntelligencePanel buildingId="b-1" />
      </QueryClientProvider>,
    );

  it('renders loading state initially', () => {
    renderPanel();
    expect(screen.getByTestId('intelligence-loading')).toBeTruthy();
  });

  it('renders insight cards after loading', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('intelligence-panel')).toBeTruthy();
    });
    expect(screen.getByTestId('insight-card-risk_cascade')).toBeTruthy();
    expect(screen.getByTestId('insight-card-silent_degradation')).toBeTruthy();
    expect(screen.getByTestId('insight-card-hidden_opportunity')).toBeTruthy();
  });

  it('shows insight titles and descriptions', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText(/Risque systemique/)).toBeTruthy();
    });
    expect(screen.getByText(/Degradation silencieuse/)).toBeTruthy();
    expect(screen.getByText(/Eligible au Certificat/)).toBeTruthy();
  });

  it('toggles evidence trail on click', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('intelligence-panel')).toBeTruthy();
    });

    const toggleButtons = screen.getAllByTestId('evidence-trail-toggle');
    expect(toggleButtons.length).toBeGreaterThan(0);

    fireEvent.click(toggleButtons[0]);
    // After expanding, evidence details should be visible
    await waitFor(() => {
      expect(screen.getByText('evidence_score')).toBeTruthy();
    });
  });

  it('shows confidence percentages', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('intelligence-panel')).toBeTruthy();
    });
    const matches = screen.getAllByText(/85%/);
    expect(matches.length).toBeGreaterThan(0);
  });
});
