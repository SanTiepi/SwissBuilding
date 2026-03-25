import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { PassportCard } from '../PassportCard';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockSummary = vi.fn();
vi.mock('@/api/passport', async () => {
  const actual = await vi.importActual('@/api/passport');
  return {
    ...actual,
    passportApi: {
      summary: (...args: unknown[]) => mockSummary(...args),
    },
  };
});

const mockTimelineList = vi.fn();
const mockTimelineEnriched = vi.fn();
vi.mock('@/api/timeline', () => ({
  timelineApi: {
    list: (...args: unknown[]) => mockTimelineList(...args),
    enriched: (...args: unknown[]) => mockTimelineEnriched(...args),
  },
}));

vi.mock('@/hooks/useBuildings', () => ({
  useBuilding: () => ({ data: { address: '1 Test', postal_code: '1000', city: 'Lausanne' } }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function routerWrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/buildings/b1/timeline']}>
        <Routes>
          <Route path="/buildings/:buildingId/timeline" element={children} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const importedSummary = {
  source_system: 'batiscan',
  mission_ref: 'M-042',
  published_at: '2026-03-10T12:00:00Z',
  local_ingestion_status: 'ingested',
  building_match_status: 'auto_matched',
  report_readiness_status: 'ready',
  snapshot_version: 2,
  snapshot_ref: null,
  payload_hash: 'sha256abc',
  sample_count: 15,
  positive_sample_count: 4,
  ai_summary_text: 'Asbestos detected in floor tiles and pipe insulation.',
  flags: [],
};

const passportData = {
  building_id: 'b1',
  knowledge_state: {
    proven_pct: 0.45,
    inferred_pct: 0.2,
    declared_pct: 0.15,
    obsolete_pct: 0.1,
    contradictory_pct: 0.1,
    overall_trust: 0.72,
    total_data_points: 42,
    trend: 'improving',
  },
  completeness: { overall_score: 0.81, category_scores: {} },
  readiness: {},
  blind_spots: { total_open: 0, blocking: 0, by_type: {} },
  contradictions: { total: 0, unresolved: 0, by_type: {} },
  evidence_coverage: {
    diagnostics_count: 2,
    samples_count: 5,
    documents_count: 4,
    interventions_count: 0,
    latest_diagnostic_date: null,
    latest_document_date: null,
  },
  diagnostic_publications: {
    count: 1,
    pollutants_covered: ['asbestos'],
    latest_published_at: '2026-03-10T12:00:00Z',
    latest_imported_summary: importedSummary,
  },
  pollutant_coverage: {
    total_pollutants: 6,
    covered_count: 4,
    missing_count: 2,
    covered: { asbestos: 2, pcb: 1, lead: 1, radon: 1 },
    missing: ['hap', 'pfas'],
    coverage_ratio: 0.6667,
  },
  passport_grade: 'B',
  assessed_at: '2026-03-08T00:00:00Z',
};

describe('ImportedDiagnosticDossier - PassportCard', () => {
  beforeEach(() => {
    mockSummary.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders imported diagnostic sub-block when data present', async () => {
    mockSummary.mockResolvedValue(passportData);
    render(<PassportCard buildingId="b1" />, { wrapper });

    expect(await screen.findByTestId('imported-dossier-block')).toBeInTheDocument();
    expect(screen.getByText('Imported from Batiscan V4')).toBeInTheDocument();
    expect(screen.getByText(/Mission M-042/)).toBeInTheDocument();
    expect(screen.getByText(/15 samples/)).toBeInTheDocument();
  });

  it('shows flag badges (no_ai, partial_package)', async () => {
    const dataWithFlags = {
      ...passportData,
      diagnostic_publications: {
        ...passportData.diagnostic_publications,
        latest_imported_summary: {
          ...importedSummary,
          flags: ['no_ai', 'partial_package'],
          ai_summary_text: null,
        },
      },
    };
    mockSummary.mockResolvedValue(dataWithFlags);
    render(<PassportCard buildingId="b1" />, { wrapper });

    expect(await screen.findByTestId('imported-dossier-block')).toBeInTheDocument();
    expect(screen.getByTestId('imported-flag-no_ai')).toBeInTheDocument();
    expect(screen.getByTestId('imported-flag-partial_package')).toBeInTheDocument();
  });

  it('hides sub-block when no imported diagnostics', async () => {
    const dataNoImported = {
      ...passportData,
      diagnostic_publications: {
        count: 0,
        pollutants_covered: [],
        latest_published_at: null,
        latest_imported_summary: undefined,
      },
    };
    mockSummary.mockResolvedValue(dataNoImported);
    render(<PassportCard buildingId="b1" />, { wrapper });

    await screen.findByText('passport.title');
    expect(screen.queryByTestId('imported-dossier-block')).not.toBeInTheDocument();
  });
});

describe('ImportedDiagnosticDossier - Timeline', () => {
  beforeEach(() => {
    mockTimelineList.mockReset();
    mockTimelineEnriched.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders diagnostic_publication event with distinct icon and label', async () => {
    mockTimelineList.mockResolvedValue({
      items: [
        {
          id: 'pub-1',
          date: '2026-03-10T12:00:00Z',
          event_type: 'diagnostic_publication',
          title: 'Diagnostic publication (asbestos_full)',
          description: 'Imported from batiscan — Mission M-042 — 15 samples',
          icon_hint: 'clipboard',
          metadata: {
            source_system: 'batiscan',
            source_mission_id: 'M-042',
            report_readiness_status: 'ready',
            sample_count: 15,
            positive_sample_count: 4,
            flags: [],
          },
          source_id: 'pub-1',
          source_type: 'diagnostic_publication',
        },
      ],
      total: 1,
      page: 1,
      size: 50,
      pages: 1,
    });

    const { BuildingTimeline } = await import('../BuildingTimeline');
    render(<BuildingTimeline buildingId="b1" />, { wrapper });

    expect(await screen.findByText('Imported from Batiscan V4')).toBeInTheDocument();
    expect(screen.getByTestId('diagnostic-pub-meta')).toBeInTheDocument();
  });

  it('shows source label + mission ref + samples in timeline', async () => {
    mockTimelineList.mockResolvedValue({
      items: [
        {
          id: 'pub-2',
          date: '2026-03-10T12:00:00Z',
          event_type: 'diagnostic_publication',
          title: 'Diagnostic publication (asbestos_full)',
          description: 'Imported from batiscan — Mission M-042 — 15 samples',
          icon_hint: 'clipboard',
          metadata: {
            source_system: 'batiscan',
            source_mission_id: 'M-042',
            report_readiness_status: 'ready',
            sample_count: 15,
            positive_sample_count: 4,
            flags: ['no_ai'],
          },
          source_id: 'pub-2',
          source_type: 'diagnostic_publication',
        },
      ],
      total: 1,
      page: 1,
      size: 50,
      pages: 1,
    });

    const { BuildingTimeline } = await import('../BuildingTimeline');
    render(<BuildingTimeline buildingId="b1" />, { wrapper });

    await screen.findByText('Imported from Batiscan V4');
    expect(screen.getAllByText(/Mission M-042/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/15 samples/).length).toBeGreaterThanOrEqual(1);
  });

  it('timeline filter includes diagnostic_publication option', async () => {
    const BuildingTimelinePage = (await import('@/pages/BuildingTimeline')).default;
    render(<BuildingTimelinePage />, { wrapper: routerWrapper });

    // The filter button should exist — mock t() returns the key itself
    expect(await screen.findByText('timeline.event_type.diagnostic_publication')).toBeInTheDocument();
  });
});
