import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SamplingQualityCard } from '../SamplingQualityCard';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGetDiagnostic = vi.fn();
vi.mock('@/api/samplingQuality', () => ({
  samplingQualityApi: {
    getDiagnostic: (...args: unknown[]) => mockGetDiagnostic(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const MOCK_DATA = {
  diagnostic_id: 'd1',
  overall_score: 72,
  grade: 'B',
  criteria: [
    { name: 'coverage', score: 8, max: 10, detail: '4/5 zones', recommendation: 'Good' },
    { name: 'density', score: 7, max: 10, detail: '3.2/zone', recommendation: 'Good' },
    { name: 'pollutant_breadth', score: 6, max: 10, detail: '3/5', recommendation: 'Test more' },
    { name: 'material_diversity', score: 8, max: 10, detail: '5 types', recommendation: 'Good' },
    { name: 'location_spread', score: 7, max: 10, detail: '3 floors', recommendation: 'Good' },
    { name: 'temporal_consistency', score: 10, max: 10, detail: '2 days', recommendation: 'Good' },
    { name: 'lab_turnaround', score: 9, max: 10, detail: 'All done', recommendation: 'Good' },
    { name: 'documentation', score: 6, max: 10, detail: '75%', recommendation: 'Fill gaps' },
    { name: 'negative_controls', score: 4, max: 10, detail: '0 controls', recommendation: 'Add controls' },
    { name: 'protocol_compliance', score: 7, max: 10, detail: '1 issue', recommendation: 'Fix category' },
  ],
  confidence_level: 'medium',
  warnings: ['Low negative controls'],
  evaluated_at: '2026-03-30T12:00:00',
};

describe('SamplingQualityCard', () => {
  beforeEach(() => {
    mockGetDiagnostic.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders score and grade on success', async () => {
    mockGetDiagnostic.mockResolvedValue(MOCK_DATA);
    render(<SamplingQualityCard diagnosticId="d1" />, { wrapper });

    expect(await screen.findByText('72')).toBeInTheDocument();
    expect(await screen.findByText(/B/)).toBeInTheDocument();
  });

  it('renders all 10 criteria', async () => {
    mockGetDiagnostic.mockResolvedValue(MOCK_DATA);
    render(<SamplingQualityCard diagnosticId="d1" />, { wrapper });

    // Criteria are rendered with their i18n keys
    expect(await screen.findByText('sampling_quality.criteria_coverage')).toBeInTheDocument();
    expect(screen.getByText('sampling_quality.criteria_density')).toBeInTheDocument();
    expect(screen.getByText('sampling_quality.criteria_compliance')).toBeInTheDocument();
  });

  it('renders warnings when present', async () => {
    mockGetDiagnostic.mockResolvedValue(MOCK_DATA);
    render(<SamplingQualityCard diagnosticId="d1" />, { wrapper });

    expect(await screen.findByText('Low negative controls')).toBeInTheDocument();
  });

  it('renders error state when API fails', async () => {
    mockGetDiagnostic.mockRejectedValue(new Error('boom'));
    render(<SamplingQualityCard diagnosticId="d1" />, { wrapper });

    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });
});
