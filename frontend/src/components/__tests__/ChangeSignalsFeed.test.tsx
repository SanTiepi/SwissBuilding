// MIGRATED to canonical BuildingSignal API (2026-03-28, Rail 1)
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { ChangeSignalsFeed } from '../ChangeSignalsFeed';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockListActive = vi.fn();
vi.mock('@/api/buildingSignals', () => ({
  buildingSignalsApi: {
    listActive: (...args: unknown[]) => mockListActive(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <MemoryRouter>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </MemoryRouter>
  );
}

describe('ChangeSignalsFeed', () => {
  beforeEach(() => {
    mockListActive.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when API fails', async () => {
    mockListActive.mockRejectedValue(new Error('boom'));
    render(<ChangeSignalsFeed buildingId="b1" />, { wrapper });

    expect(await screen.findByText('change_signal.title')).toBeInTheDocument();
    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders empty state when there are no active signals', async () => {
    // Canonical API returns array directly, not paginated
    mockListActive.mockResolvedValue([]);
    render(<ChangeSignalsFeed buildingId="b1" />, { wrapper });

    expect(await screen.findByText('change_signal.none')).toBeInTheDocument();
  });
});
