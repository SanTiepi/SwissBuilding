import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PortfolioSignalsFeed } from '../PortfolioSignalsFeed';
import { buildingSignalsApi } from '@/api/buildingSignals';

vi.mock('@/api/buildingSignals', () => ({
  buildingSignalsApi: {
    listPortfolio: vi.fn(),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('PortfolioSignalsFeed', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders explicit error state when signal loading fails', async () => {
    vi.mocked(buildingSignalsApi.listPortfolio).mockRejectedValueOnce(new Error('boom'));

    render(<PortfolioSignalsFeed />, { wrapper: createWrapper() });

    expect(await screen.findByText('portfolio.signals_title')).toBeInTheDocument();
    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders empty state when there are no signals', async () => {
    vi.mocked(buildingSignalsApi.listPortfolio).mockResolvedValueOnce([]);

    render(<PortfolioSignalsFeed />, { wrapper: createWrapper() });

    expect(await screen.findByText('portfolio.no_signals')).toBeInTheDocument();
  });
});
