import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReadinessSummary } from '../ReadinessSummary';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockList = vi.fn();
vi.mock('@/api/readiness', () => ({
  readinessApi: {
    list: (...args: unknown[]) => mockList(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('ReadinessSummary', () => {
  beforeEach(() => {
    mockList.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when API fails', async () => {
    mockList.mockRejectedValue(new Error('boom'));
    render(<ReadinessSummary buildingId="b1" />, { wrapper });

    expect(await screen.findByText('readiness.title')).toBeInTheDocument();
    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders empty state when there are no assessments', async () => {
    mockList.mockResolvedValue({ items: [] });
    render(<ReadinessSummary buildingId="b1" />, { wrapper });

    expect(await screen.findByText('readiness.no_assessment')).toBeInTheDocument();
  });
});
