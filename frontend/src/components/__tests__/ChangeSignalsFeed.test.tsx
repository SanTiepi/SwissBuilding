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

const mockList = vi.fn();
vi.mock('@/api/changeSignals', () => ({
  changeSignalsApi: {
    list: (...args: unknown[]) => mockList(...args),
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
    mockList.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when API fails', async () => {
    mockList.mockRejectedValue(new Error('boom'));
    render(<ChangeSignalsFeed buildingId="b1" />, { wrapper });

    expect(await screen.findByText('change_signal.title')).toBeInTheDocument();
    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders empty state when there are no active signals', async () => {
    mockList.mockResolvedValue({ items: [] });
    render(<ChangeSignalsFeed buildingId="b1" />, { wrapper });

    expect(await screen.findByText('change_signal.none')).toBeInTheDocument();
  });
});
