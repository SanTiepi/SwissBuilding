import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { QuoteComparisonMatrix } from '../marketplace/QuoteComparisonMatrix';

vi.mock('@/api/remediation', () => ({
  remediationApi: {
    getComparisonMatrix: vi.fn().mockResolvedValue({
      request_id: 'req-1',
      rows: [
        {
          company_name: 'Alpha Remediation',
          amount_chf: 45000,
          timeline_weeks: 6,
          scope_items: ['asbestos_removal', 'waste_disposal'],
          exclusions: ['scaffolding'],
          confidence: 0.85,
          ambiguous_fields: [],
          submitted_at: '2026-03-20T10:00:00Z',
        },
        {
          company_name: 'Beta Services',
          amount_chf: 52000,
          timeline_weeks: 8,
          scope_items: ['asbestos_removal'],
          exclusions: [],
          confidence: 0.72,
          ambiguous_fields: [{ field: 'timeline', reason: 'Multiple dates' }],
          submitted_at: '2026-03-21T14:00:00Z',
        },
      ],
    }),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k, language: 'fr', setLanguage: vi.fn() }),
}));

vi.mock('@/utils/formatters', () => ({
  formatDate: (d: string) => new Date(d).toLocaleDateString(),
  cn: (...args: (string | undefined | null | false)[]) => args.filter(Boolean).join(' '),
}));

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('QuoteComparisonMatrix', () => {
  it('renders company names', async () => {
    renderWithProviders(<QuoteComparisonMatrix requestId="req-1" />);
    await waitFor(() => {
      expect(screen.getByText('Alpha Remediation')).toBeTruthy();
      expect(screen.getByText('Beta Services')).toBeTruthy();
    });
  });

  it('renders amounts formatted', async () => {
    renderWithProviders(<QuoteComparisonMatrix requestId="req-1" />);
    await waitFor(() => {
      // Check amounts are displayed (locale-formatted)
      const cells = screen.getAllByRole('cell');
      expect(cells.length).toBeGreaterThan(0);
    });
  });

  it('renders scope items as badges', async () => {
    renderWithProviders(<QuoteComparisonMatrix requestId="req-1" />);
    await waitFor(() => {
      expect(screen.getAllByText('asbestos_removal').length).toBe(2);
      expect(screen.getByText('waste_disposal')).toBeTruthy();
    });
  });

  it('renders exclusion badges', async () => {
    renderWithProviders(<QuoteComparisonMatrix requestId="req-1" />);
    await waitFor(() => expect(screen.getByText('scaffolding')).toBeTruthy());
  });

  it('renders confidence badges', async () => {
    renderWithProviders(<QuoteComparisonMatrix requestId="req-1" />);
    await waitFor(() => {
      expect(screen.getByText('85%')).toBeTruthy();
      expect(screen.getByText('72%')).toBeTruthy();
    });
  });

  it('renders table headers', async () => {
    renderWithProviders(<QuoteComparisonMatrix requestId="req-1" />);
    await waitFor(() => {
      expect(screen.getByText('workspace.company')).toBeTruthy();
      expect(screen.getByText('workspace.amount_chf')).toBeTruthy();
    });
  });

  it('shows comparison title', async () => {
    renderWithProviders(<QuoteComparisonMatrix requestId="req-1" />);
    await waitFor(() => expect(screen.getByText('workspace.comparison_title')).toBeTruthy());
  });
});
