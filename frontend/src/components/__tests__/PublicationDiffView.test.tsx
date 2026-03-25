import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PublicationDiffView from '../building-detail/PublicationDiffView';
import { exchangeHardeningApi, type PassportStateDiff } from '@/api/exchangeHardening';

vi.mock('@/utils/formatters', () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(' '),
  formatDate: (d: string) => d,
}));

vi.mock('@/api/exchangeHardening', () => ({
  exchangeHardeningApi: {
    getPublicationDiff: vi.fn(),
  },
}));

const mockDiff: PassportStateDiff = {
  id: 'diff-1',
  publication_id: 'pub-1',
  prior_publication_id: 'pub-0',
  diff_summary: {
    added_sections: ['new_section'],
    removed_sections: ['old_section'],
    changed_sections: [
      { section: 'content', field: 'hash', old: 'abc', new: 'def' },
    ],
  },
  sections_changed_count: 3,
  computed_at: '2026-03-25T10:00:00Z',
  created_at: '2026-03-25T10:00:00Z',
};

function renderWithQuery(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('PublicationDiffView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    vi.mocked(exchangeHardeningApi.getPublicationDiff).mockReturnValue(new Promise(() => {}));
    renderWithQuery(<PublicationDiffView publicationId="pub-1" />);
    expect(screen.getByTestId('diff-loading')).toBeTruthy();
  });

  it('renders diff summary with added sections', async () => {
    vi.mocked(exchangeHardeningApi.getPublicationDiff).mockResolvedValue(mockDiff);
    renderWithQuery(<PublicationDiffView publicationId="pub-1" />);

    await waitFor(() => {
      expect(screen.getByTestId('publication-diff-view')).toBeTruthy();
    });
    expect(screen.getByTestId('diff-added')).toBeTruthy();
    expect(screen.getByText('new_section')).toBeTruthy();
  });

  it('renders removed sections', async () => {
    vi.mocked(exchangeHardeningApi.getPublicationDiff).mockResolvedValue(mockDiff);
    renderWithQuery(<PublicationDiffView publicationId="pub-1" />);

    await waitFor(() => {
      expect(screen.getByTestId('diff-removed')).toBeTruthy();
    });
    expect(screen.getByText('old_section')).toBeTruthy();
  });

  it('renders changed sections', async () => {
    vi.mocked(exchangeHardeningApi.getPublicationDiff).mockResolvedValue(mockDiff);
    renderWithQuery(<PublicationDiffView publicationId="pub-1" />);

    await waitFor(() => {
      expect(screen.getByTestId('diff-changed')).toBeTruthy();
    });
    expect(screen.getByText(/content/)).toBeTruthy();
  });

  it('shows sections changed count', async () => {
    vi.mocked(exchangeHardeningApi.getPublicationDiff).mockResolvedValue(mockDiff);
    renderWithQuery(<PublicationDiffView publicationId="pub-1" />);

    await waitFor(() => {
      expect(screen.getByText(/section\(s\) changed/)).toBeTruthy();
    });
  });

  it('shows prior publication reference', async () => {
    vi.mocked(exchangeHardeningApi.getPublicationDiff).mockResolvedValue(mockDiff);
    renderWithQuery(<PublicationDiffView publicationId="pub-1" />);

    await waitFor(() => {
      expect(screen.getByText(/pub-0/)).toBeTruthy();
    });
  });

  it('renders error state when API fails', async () => {
    vi.mocked(exchangeHardeningApi.getPublicationDiff).mockRejectedValue(new Error('fail'));
    renderWithQuery(<PublicationDiffView publicationId="pub-1" />);

    await waitFor(() => {
      expect(screen.getByTestId('diff-error')).toBeTruthy();
    });
  });

  it('renders initial publication diff', async () => {
    const initialDiff: PassportStateDiff = {
      ...mockDiff,
      prior_publication_id: null,
      diff_summary: {
        added_sections: ['initial_publication'],
        removed_sections: [],
        changed_sections: [],
      },
      sections_changed_count: 1,
    };
    vi.mocked(exchangeHardeningApi.getPublicationDiff).mockResolvedValue(initialDiff);
    renderWithQuery(<PublicationDiffView publicationId="pub-1" />);

    await waitFor(() => {
      expect(screen.getByText('initial_publication')).toBeTruthy();
    });
  });
});
