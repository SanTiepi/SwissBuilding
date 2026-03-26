import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import type { IndispensabilityReport } from '@/api/intelligence';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGetIndispensabilityReport = vi.fn();
const mockGetScoreExplainability = vi.fn();
vi.mock('@/api/intelligence', () => ({
  intelligenceApi: {
    getIndispensabilityReport: (...args: unknown[]) => mockGetIndispensabilityReport(...args),
    getScoreExplainability: (...args: unknown[]) => mockGetScoreExplainability(...args),
  },
}));

import IndispensabilityView from '../building-detail/IndispensabilityView';

function makeReport(overrides: Partial<IndispensabilityReport> = {}): IndispensabilityReport {
  return {
    building_id: 'b-1',
    generated_at: '2026-03-01T00:00:00Z',
    headline: 'SwissBuilding unifie 12 sources pour ce batiment.',
    fragmentation: {
      sources_unified: 12,
      systems_replaced: ['Excel', 'Email'],
      contradictions_detected: 5,
      contradictions_resolved: 4,
      silent_risk: 'medium',
      proof_chains_count: 8,
      documents_with_provenance: 10,
      documents_without_provenance: 3,
      enrichment_fields_count: 15,
      cross_source_fields: 7,
      fragmentation_score: 65,
    },
    defensibility: {
      decisions_with_full_trace: 6,
      decisions_without_trace: 2,
      defensibility_score: 0.78,
      vulnerability_points: ['Diagnostic amiante expire'],
      snapshots_count: 3,
      time_coverage_days: 180,
    },
    counterfactual: {
      with_platform: {
        sources: 12,
        contradictions_visible: 4,
        proof_chains: 8,
        grade: 'B',
        trust: 0.82,
        completeness: 0.91,
      },
      without_platform: {
        sources: 3,
        contradictions_visible: 0,
        proof_chains: 0,
        grade: null,
        trust: 0.3,
        completeness: 0.4,
      },
      delta: ['Unification de 12 sources', 'Resolution de 4 contradictions'],
      cost_of_fragmentation_hours: 42,
    },
    ...overrides,
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

describe('IndispensabilityView', () => {
  it('renders comparison, gauges, and cost when data loads', async () => {
    mockGetIndispensabilityReport.mockResolvedValue(makeReport());
    wrap(<IndispensabilityView buildingId="b-1" />);

    expect(await screen.findByTestId('indispensability-view')).toBeInTheDocument();
    expect(screen.getByTestId('avec-sans-comparison')).toBeInTheDocument();
    expect(screen.getByTestId('indispensability-gauges')).toBeInTheDocument();
    expect(screen.getByTestId('fragmentation-cost')).toBeInTheDocument();
  });

  it('shows fragmentation and defensibility scores', async () => {
    mockGetIndispensabilityReport.mockResolvedValue(makeReport());
    wrap(<IndispensabilityView buildingId="b-1" />);

    await screen.findByTestId('indispensability-gauges');
    expect(screen.getByText('65%')).toBeInTheDocument(); // fragmentation
    expect(screen.getByText('78%')).toBeInTheDocument(); // defensibility (0.78 * 100)
  });

  it('shows cost of fragmentation hours', async () => {
    mockGetIndispensabilityReport.mockResolvedValue(makeReport());
    wrap(<IndispensabilityView buildingId="b-1" />);

    await screen.findByTestId('fragmentation-cost');
    expect(screen.getByText('42h')).toBeInTheDocument();
  });

  it('has an export button', async () => {
    mockGetIndispensabilityReport.mockResolvedValue(makeReport());
    wrap(<IndispensabilityView buildingId="b-1" />);

    await screen.findByTestId('indispensability-view');
    const exportBtn = screen.getByText('indispensability.export_button');
    expect(exportBtn.closest('button')).toBeInTheDocument();
  });
});
