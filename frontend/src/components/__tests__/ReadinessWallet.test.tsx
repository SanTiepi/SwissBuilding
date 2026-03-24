import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ReadinessWallet from '@/pages/ReadinessWallet';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/hooks/useBuildings', () => ({
  useBuilding: () => ({
    data: { address: 'Rue du Test 1' },
  }),
}));

const mockList = vi.fn();
const mockEvaluateAll = vi.fn();
vi.mock('@/api/readiness', () => ({
  readinessApi: {
    list: (...args: unknown[]) => mockList(...args),
    evaluateAll: (...args: unknown[]) => mockEvaluateAll(...args),
  },
}));

const mockEcoClausesGet = vi.fn();
vi.mock('@/api/ecoclauses', () => ({
  ecoClausesApi: {
    get: (...args: unknown[]) => mockEcoClausesGet(...args),
  },
}));

const mockSnapshotsList = vi.fn();
vi.mock('@/api/snapshots', () => ({
  snapshotsApi: {
    list: (...args: unknown[]) => mockSnapshotsList(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter
        initialEntries={['/buildings/b1/readiness']}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/buildings/:buildingId/readiness" element={children} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ReadinessWallet', () => {
  beforeEach(() => {
    mockList.mockReset();
    mockEvaluateAll.mockReset();
    mockEcoClausesGet.mockReset();
    mockSnapshotsList.mockReset();
    // Default: no eco clauses, no snapshots
    mockEcoClausesGet.mockResolvedValue({ building_id: 'b1', context: 'renovation', generated_at: '2026-03-24T00:00:00Z', total_clauses: 0, detected_pollutants: [], sections: [] });
    mockSnapshotsList.mockResolvedValue({ items: [], total: 0 });
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when readiness query fails', async () => {
    mockList.mockRejectedValue(new Error('boom'));
    render(<ReadinessWallet />, { wrapper });

    expect(await screen.findByText('app.error')).toBeInTheDocument();
  });

  it('renders readiness cards when assessments load', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          readiness_type: 'safe_to_start',
          status: 'ready',
          score: 0.9,
          assessed_at: '2026-03-08T00:00:00Z',
          checks_json: [{ label: 'Diagnostic present', passed: true, details: null }],
          blockers_json: [],
          conditions_json: [],
        },
      ],
      total: 1,
    });

    render(<ReadinessWallet />, { wrapper });

    expect(await screen.findByText('readiness.safe_to_start')).toBeInTheDocument();
    expect(screen.getByText('90%')).toBeInTheDocument();
    // Check label is inside collapsible section; verify gate card renders with show_checks toggle
    expect(screen.getByText('readiness.show_checks')).toBeInTheDocument();
  });

  it('renders prework trigger card when triggers are present', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          readiness_type: 'safe_to_start',
          status: 'not_ready',
          score: 0.4,
          assessed_at: '2026-03-08T00:00:00Z',
          checks_json: [],
          blockers_json: [],
          conditions_json: [],
          prework_triggers: [
            {
              trigger_type: 'missing_diagnostic',
              reason: 'Asbestos diagnostic required before renovation',
              urgency: 'high',
              source_check: 'asbestos_coverage',
            },
            {
              trigger_type: 'missing_report',
              reason: 'Lab report pending',
              urgency: 'medium',
              source_check: 'lab_results',
            },
          ],
        },
      ],
      total: 1,
    });

    render(<ReadinessWallet />, { wrapper });

    expect(await screen.findByText('readiness.prework_triggers')).toBeInTheDocument();
    expect(screen.getByText('Asbestos diagnostic required before renovation')).toBeInTheDocument();
    expect(screen.getByText('Lab report pending')).toBeInTheDocument();
    expect(screen.getByText('missing_diagnostic')).toBeInTheDocument();
    expect(screen.getByText('missing_report')).toBeInTheDocument();
  });

  it('does not render prework trigger card when triggers array is empty', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          readiness_type: 'safe_to_start',
          status: 'ready',
          score: 1.0,
          assessed_at: '2026-03-08T00:00:00Z',
          checks_json: [],
          blockers_json: [],
          conditions_json: [],
          prework_triggers: [],
        },
      ],
      total: 1,
    });

    render(<ReadinessWallet />, { wrapper });

    // Wait for content to load
    expect(await screen.findByText('readiness.safe_to_start')).toBeInTheDocument();
    // Trigger card should not be rendered
    expect(screen.queryByText('readiness.prework_triggers')).not.toBeInTheDocument();
  });

  it('renders pfas_check prework trigger alongside other triggers', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          readiness_type: 'safe_to_start',
          status: 'not_ready',
          score: 0.3,
          assessed_at: '2026-03-08T00:00:00Z',
          checks_json: [{ label: 'PFAS assessment', passed: false, details: 'PFAS evaluation missing' }],
          blockers_json: [
            { label: 'PFAS assessment required', severity: 'high', details: 'No PFAS evaluation on file' },
          ],
          conditions_json: [],
          prework_triggers: [
            {
              trigger_type: 'pfas_check',
              reason: 'PFAS evaluation required before renovation',
              urgency: 'high',
              source_check: 'pfas_assessment',
            },
          ],
        },
      ],
      total: 1,
    });

    render(<ReadinessWallet />, { wrapper });

    expect(await screen.findByText('readiness.prework_triggers')).toBeInTheDocument();
    expect(screen.getByText('PFAS evaluation required before renovation')).toBeInTheDocument();
    expect(screen.getByText('pfas_check')).toBeInTheDocument();
    // Blocker should also appear
    expect(screen.getByText('PFAS assessment required')).toBeInTheDocument();
  });

  it('does not render prework trigger card when triggers field is missing', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          readiness_type: 'safe_to_start',
          status: 'ready',
          score: 0.9,
          assessed_at: '2026-03-08T00:00:00Z',
          checks_json: [],
          blockers_json: [],
          conditions_json: [],
          // no prework_triggers field
        },
      ],
      total: 1,
    });

    render(<ReadinessWallet />, { wrapper });

    expect(await screen.findByText('readiness.safe_to_start')).toBeInTheDocument();
    expect(screen.queryByText('readiness.prework_triggers')).not.toBeInTheDocument();
  });

  it('renders EcoClauseCard when building has pollutants', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          readiness_type: 'safe_to_start',
          status: 'not_ready',
          score: 0.5,
          assessed_at: '2026-03-08T00:00:00Z',
          checks_json: [],
          blockers_json: [],
          conditions_json: [],
          prework_triggers: [],
        },
      ],
      total: 1,
    });
    mockEcoClausesGet.mockResolvedValue({
      building_id: 'b1',
      context: 'renovation',
      generated_at: '2026-03-24T00:00:00Z',
      total_clauses: 2,
      detected_pollutants: ['asbestos', 'lead'],
      sections: [
        {
          section_id: 'sec-1',
          title: 'Decontamination Requirements',
          clauses: [
            {
              clause_id: 'EC-001',
              title: 'Asbestos removal before renovation',
              body: 'All asbestos-containing materials must be removed by certified professionals.',
              legal_references: ['OTConst Art. 60a'],
              applicability: 'Buildings with confirmed asbestos',
              pollutants: ['asbestos'],
            },
            {
              clause_id: 'EC-002',
              title: 'Lead paint containment',
              body: 'Lead paint must be encapsulated or removed before occupancy.',
              legal_references: ['ORRChim Annexe 2.18'],
              applicability: 'Buildings with lead contamination',
              pollutants: ['lead'],
            },
          ],
        },
      ],
    });

    render(<ReadinessWallet />, { wrapper });

    // Wait for gate card to load first
    expect(await screen.findByText('readiness.safe_to_start')).toBeInTheDocument();
    // Eco clause card renders with pollutant badges (wait for eco clauses query to resolve)
    expect(await screen.findByText('pollutant.asbestos')).toBeInTheDocument();
    expect(screen.getByText('pollutant.lead')).toBeInTheDocument();
    // Eco clause title and count shown
    expect(screen.getByText('eco_clause.title')).toBeInTheDocument();
  });

  it('renders prework triggers and eco clauses together without layout conflict', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          readiness_type: 'safe_to_start',
          status: 'not_ready',
          score: 0.35,
          assessed_at: '2026-03-08T00:00:00Z',
          checks_json: [{ label: 'Diagnostic present', passed: false, details: 'Missing asbestos diagnostic' }],
          blockers_json: [],
          conditions_json: [],
          prework_triggers: [
            {
              trigger_type: 'missing_diagnostic',
              reason: 'Asbestos diagnostic required before renovation',
              urgency: 'high',
              source_check: 'asbestos_coverage',
            },
          ],
        },
      ],
      total: 1,
    });
    mockEcoClausesGet.mockResolvedValue({
      building_id: 'b1',
      context: 'renovation',
      generated_at: '2026-03-24T00:00:00Z',
      total_clauses: 1,
      detected_pollutants: ['asbestos'],
      sections: [
        {
          section_id: 'sec-decontam',
          title: 'Decontamination Requirements',
          clauses: [
            {
              clause_id: 'EC-010',
              title: 'Asbestos removal clause',
              body: 'Certified asbestos removal required.',
              legal_references: ['OTConst Art. 82'],
              applicability: 'All renovation projects with asbestos',
              pollutants: ['asbestos'],
            },
          ],
        },
      ],
    });

    render(<ReadinessWallet />, { wrapper });

    // Both cards coexist: prework triggers card
    expect(await screen.findByText('readiness.prework_triggers')).toBeInTheDocument();
    expect(screen.getByText('Asbestos diagnostic required before renovation')).toBeInTheDocument();
    // Eco clause card (wait for async data)
    expect(await screen.findByText('Decontamination Requirements')).toBeInTheDocument();
    expect(screen.getByText('eco_clause.title')).toBeInTheDocument();
    // Gate card also present (may appear in multiple places: card title + blocker badge)
    expect(screen.getAllByText('readiness.safe_to_start').length).toBeGreaterThanOrEqual(1);
  });

  it('renders PFAS prework trigger alongside eco clauses for multi-pollutant building', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          readiness_type: 'safe_to_start',
          status: 'not_ready',
          score: 0.2,
          assessed_at: '2026-03-08T00:00:00Z',
          checks_json: [],
          blockers_json: [],
          conditions_json: [],
          prework_triggers: [
            {
              trigger_type: 'pfas_check',
              reason: 'PFAS evaluation required before renovation',
              urgency: 'high',
              source_check: 'pfas_assessment',
            },
            {
              trigger_type: 'missing_diagnostic',
              reason: 'PCB diagnostic missing',
              urgency: 'medium',
              source_check: 'pcb_coverage',
            },
          ],
        },
      ],
      total: 1,
    });
    mockEcoClausesGet.mockResolvedValue({
      building_id: 'b1',
      context: 'renovation',
      generated_at: '2026-03-24T00:00:00Z',
      total_clauses: 1,
      detected_pollutants: ['pcb'],
      sections: [
        {
          section_id: 'sec-pcb',
          title: 'PCB Handling',
          clauses: [
            {
              clause_id: 'EC-020',
              title: 'PCB joint removal',
              body: 'PCB-contaminated joints must be removed by specialists.',
              legal_references: ['ORRChim Annexe 2.15'],
              applicability: 'Buildings with PCB > 50 mg/kg',
              pollutants: ['pcb'],
            },
          ],
        },
      ],
    });

    render(<ReadinessWallet />, { wrapper });

    // PFAS trigger present
    expect(await screen.findByText('readiness.prework_triggers')).toBeInTheDocument();
    expect(screen.getByText('PFAS evaluation required before renovation')).toBeInTheDocument();
    expect(screen.getByText('pfas_check')).toBeInTheDocument();
    // Other trigger also present
    expect(screen.getByText('PCB diagnostic missing')).toBeInTheDocument();
    // Eco clause card with PCB section (wait for async data)
    expect(await screen.findByText('pollutant.pcb')).toBeInTheDocument();
    expect(screen.getByText('eco_clause.title')).toBeInTheDocument();
  });

  it('does not render EcoClauseCard when no eco clauses exist', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          readiness_type: 'safe_to_start',
          status: 'ready',
          score: 1.0,
          assessed_at: '2026-03-08T00:00:00Z',
          checks_json: [{ label: 'All checks passed', passed: true, details: null }],
          blockers_json: [],
          conditions_json: [],
          prework_triggers: [],
        },
      ],
      total: 1,
    });
    // Default mock already returns total_clauses: 0

    render(<ReadinessWallet />, { wrapper });

    // Gate card renders
    expect(await screen.findByText('readiness.safe_to_start')).toBeInTheDocument();
    // Wait for eco clauses query to settle (loading state shows title briefly, then returns null)
    await waitFor(() => {
      // Once data loads with total_clauses=0, EcoClauseCard returns null and title disappears
      expect(screen.queryByText('eco_clause.title')).not.toBeInTheDocument();
    });
    // Prework trigger card should not appear either
    expect(screen.queryByText('readiness.prework_triggers')).not.toBeInTheDocument();
  });
});
