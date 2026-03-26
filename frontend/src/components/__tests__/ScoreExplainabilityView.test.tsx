import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGetScoreExplainability = vi.fn();
vi.mock('@/api/intelligence', () => ({
  intelligenceApi: {
    getScoreExplainability: (...args: unknown[]) => mockGetScoreExplainability(...args),
  },
}));

import ScoreExplainabilityView from '../building-detail/ScoreExplainabilityView';

function makeReport() {
  return {
    building_id: 'b-1',
    generated_at: '2026-03-01T00:00:00Z',
    methodology_summary: 'Calcul fonde sur les preuves documentaires.',
    total_line_items: 12,
    scores: [
      {
        metric_name: 'trust_score',
        metric_label: 'Confiance',
        value: 0.82,
        unit: '%',
        methodology: 'Moyenne ponderee de la fraicheur et provenance.',
        line_items: [
          {
            item_type: 'document',
            item_id: 'd-1',
            label: 'Rapport amiante 2025',
            detail: 'Document avec provenance verifiee',
            contribution: '+0.15',
            link: '/documents/d-1',
            source_class: 'diagnostic',
            timestamp: '2025-06-15T00:00:00Z',
          },
        ],
        confidence: 'exact',
      },
      {
        metric_name: 'completeness',
        metric_label: 'Completude',
        value: 0.91,
        unit: '%',
        methodology: 'Ratio des champs remplis sur total attendu.',
        line_items: [],
        confidence: 'estimated',
      },
    ],
  };
}

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ScoreExplainabilityView', () => {
  it('shows metric cards with values', async () => {
    mockGetScoreExplainability.mockResolvedValue(makeReport());
    wrap(<ScoreExplainabilityView buildingId="b-1" />);

    await screen.findByTestId('score-explainability-view');
    expect(screen.getByText('Confiance')).toBeInTheDocument();
    expect(screen.getByText('82%')).toBeInTheDocument();
    expect(screen.getByText('Completude')).toBeInTheDocument();
    expect(screen.getByText('91%')).toBeInTheDocument();
  });

  it('expanding a card shows line items', async () => {
    mockGetScoreExplainability.mockResolvedValue(makeReport());
    wrap(<ScoreExplainabilityView buildingId="b-1" />);

    await screen.findByTestId('score-explainability-view');
    // Click the Confiance card to expand
    fireEvent.click(screen.getByText('Confiance'));
    expect(screen.getByText('Rapport amiante 2025')).toBeInTheDocument();
    expect(screen.getByText('+0.15')).toBeInTheDocument();
  });

  it('shows methodology summary text', async () => {
    mockGetScoreExplainability.mockResolvedValue(makeReport());
    wrap(<ScoreExplainabilityView buildingId="b-1" />);

    await screen.findByTestId('score-explainability-view');
    expect(screen.getByText('Calcul fonde sur les preuves documentaires.')).toBeInTheDocument();
  });
});
