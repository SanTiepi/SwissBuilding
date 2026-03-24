import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PassportCard } from '../PassportCard';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockSummary = vi.fn();
vi.mock('@/api/passport', () => ({
  passportApi: {
    summary: (...args: unknown[]) => mockSummary(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

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
  blind_spots: { total_open: 3, blocking: 1, by_type: {} },
  contradictions: { total: 2, unresolved: 1, by_type: {} },
  evidence_coverage: {
    diagnostics_count: 2,
    samples_count: 5,
    documents_count: 4,
    interventions_count: 1,
    latest_diagnostic_date: null,
    latest_document_date: null,
  },
  diagnostic_publications: {
    count: 0,
    pollutants_covered: [],
    latest_published_at: null,
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

describe('PassportCard', () => {
  beforeEach(() => {
    mockSummary.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders passport metrics when data loads', async () => {
    mockSummary.mockResolvedValue(passportData);
    render(<PassportCard buildingId="b1" />, { wrapper });

    expect(await screen.findByText('passport.title')).toBeInTheDocument();
    expect(screen.getByText('72%')).toBeInTheDocument();
    expect(screen.getByText('81%')).toBeInTheDocument();
    expect(screen.getByText('42 pts')).toBeInTheDocument();
    expect(screen.getByText('B')).toBeInTheDocument();
  });

  it('renders explicit error state when API fails', async () => {
    mockSummary.mockRejectedValue(new Error('boom'));
    render(<PassportCard buildingId="b1" />, { wrapper });

    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders no-data state when API returns null', async () => {
    mockSummary.mockResolvedValue(null);
    render(<PassportCard buildingId="b1" />, { wrapper });

    expect(await screen.findByText('passport.no_data')).toBeInTheDocument();
  });

  it('renders pollutant coverage section with covered and missing indicators', async () => {
    mockSummary.mockResolvedValue(passportData);
    render(<PassportCard buildingId="b1" />, { wrapper });

    // Wait for load
    await screen.findByText('passport.title');

    // Coverage ratio text (ratio + label in same element)
    expect(screen.getByText(/4\/6.*passport\.pollutants_evaluated/)).toBeInTheDocument();

    // Covered pollutants present
    expect(screen.getByTestId('pollutant-asbestos')).toBeInTheDocument();
    expect(screen.getByTestId('pollutant-pcb')).toBeInTheDocument();
    expect(screen.getByTestId('pollutant-lead')).toBeInTheDocument();
    expect(screen.getByTestId('pollutant-radon')).toBeInTheDocument();

    // Missing pollutants present
    expect(screen.getByTestId('pollutant-hap')).toBeInTheDocument();
    expect(screen.getByTestId('pollutant-pfas')).toBeInTheDocument();
  });

  it('shows PFAS emerging regulation note when PFAS is missing', async () => {
    mockSummary.mockResolvedValue(passportData);
    render(<PassportCard buildingId="b1" />, { wrapper });

    await screen.findByText('passport.title');
    expect(screen.getByText('passport.pfas_note')).toBeInTheDocument();
  });

  it('shows emerging badge on PFAS when missing', async () => {
    mockSummary.mockResolvedValue(passportData);
    render(<PassportCard buildingId="b1" />, { wrapper });

    await screen.findByText('passport.title');
    const pfasEl = screen.getByTestId('pollutant-pfas');
    expect(pfasEl).toHaveTextContent('passport.emerging');
  });

  it('does not show PFAS note when all pollutants are covered', async () => {
    const fullCoverage = {
      ...passportData,
      pollutant_coverage: {
        total_pollutants: 6,
        covered_count: 6,
        missing_count: 0,
        covered: { asbestos: 2, pcb: 1, lead: 1, hap: 1, radon: 1, pfas: 1 },
        missing: [],
        coverage_ratio: 1.0,
      },
    };
    mockSummary.mockResolvedValue(fullCoverage);
    render(<PassportCard buildingId="b1" />, { wrapper });

    await screen.findByText('passport.title');
    expect(screen.queryByText('passport.pfas_note')).not.toBeInTheDocument();
  });
});
