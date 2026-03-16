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
});
