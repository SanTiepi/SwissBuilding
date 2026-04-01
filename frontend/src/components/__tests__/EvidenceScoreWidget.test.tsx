import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { EvidenceScoreWidget } from '../EvidenceScoreWidget';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGetEvidenceScore = vi.fn();
vi.mock('@/api/evidenceScore', () => ({
  evidenceScoreApi: {
    getEvidenceScore: (...args: unknown[]) => mockGetEvidenceScore(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('EvidenceScoreWidget', () => {
  beforeEach(() => {
    mockGetEvidenceScore.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders score and grade when data loads', async () => {
    mockGetEvidenceScore.mockResolvedValue({
      building_id: 'b1',
      score: 72,
      grade: 'B',
      trust: 0.8,
      completeness: 0.65,
      freshness: 1.0,
      gap_penalty: 0.9,
      breakdown: {
        trust_weighted: 0.28,
        completeness_weighted: 0.195,
        freshness_weighted: 0.2,
        gap_penalty_weighted: 0.135,
      },
      computed_at: '2026-03-30T10:00:00+00:00',
    });

    render(<EvidenceScoreWidget buildingId="b1" />, { wrapper });

    expect(await screen.findByText('72')).toBeInTheDocument();
    expect(await screen.findByText('B')).toBeInTheDocument();
    expect(screen.getByText('evidence_score.title')).toBeInTheDocument();
    expect(screen.getByText('evidence_score.trust')).toBeInTheDocument();
    expect(screen.getByText('evidence_score.completeness')).toBeInTheDocument();
    expect(screen.getByText('evidence_score.freshness')).toBeInTheDocument();
    expect(screen.getByText('evidence_score.gaps')).toBeInTheDocument();
  });

  it('renders loading state', () => {
    mockGetEvidenceScore.mockReturnValue(new Promise(() => {})); // never resolves
    render(<EvidenceScoreWidget buildingId="b1" />, { wrapper });

    expect(screen.getByText('evidence_score.title')).toBeInTheDocument();
  });

  it('renders error state when API fails', async () => {
    mockGetEvidenceScore.mockRejectedValue(new Error('boom'));
    render(<EvidenceScoreWidget buildingId="b1" />, { wrapper });

    expect(await screen.findByText('evidence_score.title')).toBeInTheDocument();
    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });
});
