import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CompletenessGauge } from '../CompletenessGauge';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockEvaluate = vi.fn();
vi.mock('@/api/completeness', () => ({
  completenessApi: {
    evaluate: (...args: unknown[]) => mockEvaluate(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('CompletenessGauge', () => {
  beforeEach(() => {
    mockEvaluate.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when API fails', async () => {
    mockEvaluate.mockRejectedValue(new Error('boom'));
    render(<CompletenessGauge buildingId="b1" />, { wrapper });

    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders readiness state and score when data loads', async () => {
    mockEvaluate.mockResolvedValue({
      overall_score: 0.92,
      ready_to_proceed: true,
      checks: [
        {
          id: 'c1',
          category: 'diagnostic',
          status: 'complete',
          label_key: 'completeness.check.sample',
          details: 'ok',
        },
      ],
      missing_items: [],
    });

    render(<CompletenessGauge buildingId="b1" />, { wrapper });

    expect(await screen.findByText('92%')).toBeInTheDocument();
    expect(screen.getByText('completeness.ready')).toBeInTheDocument();
  });
});
