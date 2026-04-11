import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PassportDiffView } from '../building-detail/PassportDiffView';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockDiffEnvelopes = vi.fn();
vi.mock('@/api/passportEnvelopeDiff', () => ({
  passportEnvelopeDiffApi: {
    diffEnvelopes: (...args: unknown[]) => mockDiffEnvelopes(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const diffResult = {
  envelope_a_id: 'aaa',
  envelope_b_id: 'bbb',
  envelope_a_version: 1,
  envelope_b_version: 2,
  summary: {
    sections_added: ['blind_spots'],
    sections_removed: [],
    sections_changed: ['knowledge_state'],
    unchanged: ['completeness'],
    total_changes: 3,
  },
  changes: [
    {
      section: 'knowledge_state',
      field: 'overall_trust',
      old_value: '0.5',
      new_value: '0.8',
      change_type: 'modified' as const,
    },
    {
      section: 'blind_spots',
      field: 'blind_spots',
      old_value: null,
      new_value: "{'total_open': 3}",
      change_type: 'added' as const,
    },
    {
      section: 'knowledge_state',
      field: 'proven_pct',
      old_value: '30.0',
      new_value: '45.0',
      change_type: 'modified' as const,
    },
  ],
  trust_delta: { old_trust: 0.5, new_trust: 0.8, trust_change: 0.3 },
  completeness_delta: { old_pct: 65.0, new_pct: 80.0 },
  readiness_delta: { old_verdicts: {}, new_verdicts: {} },
  grade_delta: { old_grade: 'C', new_grade: 'B' },
};

describe('PassportDiffView', () => {
  beforeEach(() => {
    mockDiffEnvelopes.mockReset();
  });
  afterEach(() => cleanup());

  it('renders loading state', () => {
    mockDiffEnvelopes.mockReturnValue(new Promise(() => {})); // never resolves
    render(<PassportDiffView envelopeIdA="aaa" envelopeIdB="bbb" />, { wrapper });
    // Should show loading skeleton (animated pulse)
    expect(document.querySelector('.animate-pulse')).toBeTruthy();
  });

  it('renders diff results on success', async () => {
    mockDiffEnvelopes.mockResolvedValue(diffResult);
    render(<PassportDiffView envelopeIdA="aaa" envelopeIdB="bbb" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('passport_diff.title')).toBeTruthy();
    });

    // Grade delta
    expect(screen.getByText('C')).toBeTruthy();
    expect(screen.getByText('B')).toBeTruthy();

    // Changes count
    expect(screen.getByText('3')).toBeTruthy();

    // Section added badge
    expect(screen.getByText('+ blind_spots')).toBeTruthy();
  });

  it('renders error state on failure', async () => {
    mockDiffEnvelopes.mockRejectedValue(new Error('Network error'));
    render(<PassportDiffView envelopeIdA="aaa" envelopeIdB="bbb" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('passport_diff.error')).toBeTruthy();
    });
  });

  it('shows no-changes message when identical', async () => {
    mockDiffEnvelopes.mockResolvedValue({
      ...diffResult,
      summary: { ...diffResult.summary, total_changes: 0, sections_added: [], sections_changed: [] },
      changes: [],
    });
    render(<PassportDiffView envelopeIdA="aaa" envelopeIdB="bbb" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('passport_diff.no_changes')).toBeTruthy();
    });
  });
});
