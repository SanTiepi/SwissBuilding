import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { audiencePacksApi } from '@/api/audiencePacks';
import CaveatSummary from '../building-detail/CaveatSummary';

vi.mock('@/api/audiencePacks', () => ({
  audiencePacksApi: {
    getCaveats: vi.fn().mockResolvedValue([
      {
        caveat_type: 'freshness_warning',
        severity: 'medium',
        message: 'Diagnostic data is older than 6 months',
        applies_when: {},
      },
      { caveat_type: 'freshness_warning', severity: 'low', message: 'Some documents need refresh', applies_when: {} },
      {
        caveat_type: 'confidence_caveat',
        severity: 'high',
        message: 'Low confidence on asbestos assessment',
        applies_when: {},
      },
      {
        caveat_type: 'unknown_disclosure',
        severity: 'medium',
        message: 'Basement zones not surveyed',
        applies_when: {},
      },
    ]),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('CaveatSummary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders caveat items grouped by type', async () => {
    render(<CaveatSummary buildingId="b-1" audienceType="insurer" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('caveat-summary')).toBeInTheDocument();
    });
    expect(screen.getAllByTestId('caveat-item')).toHaveLength(4);
  });

  it('displays severity badges', async () => {
    render(<CaveatSummary buildingId="b-1" audienceType="insurer" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getAllByTestId('caveat-severity').length).toBeGreaterThan(0);
    });
  });

  it('calls API with correct params', async () => {
    render(<CaveatSummary buildingId="b-1" audienceType="lender" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(audiencePacksApi.getCaveats).toHaveBeenCalledWith('b-1', 'lender');
    });
  });

  it('shows empty state when no caveats', async () => {
    vi.mocked(audiencePacksApi.getCaveats).mockResolvedValueOnce([]);
    render(<CaveatSummary buildingId="b-1" audienceType="insurer" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('caveat-empty')).toBeInTheDocument();
    });
  });

  it('shows caveat messages', async () => {
    render(<CaveatSummary buildingId="b-1" audienceType="insurer" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('Diagnostic data is older than 6 months')).toBeInTheDocument();
      expect(screen.getByText('Low confidence on asbestos assessment')).toBeInTheDocument();
      expect(screen.getByText('Basement zones not surveyed')).toBeInTheDocument();
    });
  });

  it('groups caveats by caveat_type', async () => {
    render(<CaveatSummary buildingId="b-1" audienceType="insurer" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('caveat-summary')).toBeInTheDocument();
    });
    // freshness_warning group has 2 items, confidence_caveat has 1, unknown_disclosure has 1
    const groups = screen.getByTestId('caveat-summary').children;
    expect(groups.length).toBe(3); // 3 distinct caveat types
  });
});
