import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PortfolioSignalsFeed } from '../PortfolioSignalsFeed';
import { changeSignalsApi } from '@/api/changeSignals';

vi.mock('@/api/changeSignals', () => ({
  changeSignalsApi: {
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
    vi.mocked(changeSignalsApi.listPortfolio).mockRejectedValueOnce(new Error('boom'));

    render(<PortfolioSignalsFeed />, { wrapper: createWrapper() });

    expect(await screen.findByText('portfolio.signals_title')).toBeInTheDocument();
    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders empty state when there are no signals', async () => {
    vi.mocked(changeSignalsApi.listPortfolio).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      size: 20,
      pages: 1,
    });

    render(<PortfolioSignalsFeed />, { wrapper: createWrapper() });

    expect(await screen.findByText('portfolio.no_signals')).toBeInTheDocument();
  });
});
