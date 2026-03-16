import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UnknownIssuesList } from '../UnknownIssuesList';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockList = vi.fn();
vi.mock('@/api/unknowns', () => ({
  unknownsApi: {
    list: (...args: unknown[]) => mockList(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('UnknownIssuesList', () => {
  beforeEach(() => {
    mockList.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when API fails', async () => {
    mockList.mockRejectedValue(new Error('boom'));
    render(<UnknownIssuesList buildingId="b1" />, { wrapper });

    expect(await screen.findByText('unknown_issue.title')).toBeInTheDocument();
    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders empty state when there are no open issues', async () => {
    mockList.mockResolvedValue({ items: [] });
    render(<UnknownIssuesList buildingId="b1" />, { wrapper });

    expect(await screen.findByText('unknown_issue.none')).toBeInTheDocument();
  });
});
