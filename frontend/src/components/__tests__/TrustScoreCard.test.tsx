import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TrustScoreCard } from '../TrustScoreCard';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockLatest = vi.fn();
vi.mock('@/api/trustScores', () => ({
  trustScoresApi: {
    latest: (...args: unknown[]) => mockLatest(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('TrustScoreCard', () => {
  beforeEach(() => {
    mockLatest.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when API fails', async () => {
    mockLatest.mockRejectedValue(new Error('boom'));
    render(<TrustScoreCard buildingId="b1" />, { wrapper });

    expect(await screen.findByText('trust_score.title')).toBeInTheDocument();
    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders no-score state when API returns null', async () => {
    mockLatest.mockResolvedValue(null);
    render(<TrustScoreCard buildingId="b1" />, { wrapper });

    expect(await screen.findByText('trust_score.no_score')).toBeInTheDocument();
  });
});
