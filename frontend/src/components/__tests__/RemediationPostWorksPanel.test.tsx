import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { remediationPostWorksApi } from '@/api/remediationPostWorks';
import RemediationPostWorksPanel from '../building-detail/RemediationPostWorksPanel';

vi.mock('@/api/remediationPostWorks', () => ({
  remediationPostWorksApi: {
    getBuildingOutcomes: vi.fn().mockResolvedValue([
      {
        id: 'pwl-1',
        completion_confirmation_id: 'cc-1',
        intervention_id: 'int-1',
        status: 'finalized',
        grade_delta: { before: 'C', after: 'B', change: '+1' },
        trust_delta: { before: 0.52, after: 0.78, change: 0.26 },
        completeness_delta: { before: 0.65, after: 0.82, change: 0.17 },
        residual_risks: [{ risk_type: 'asbestos', description: 'Remaining encapsulated material', severity: 'low' }],
        drafted_at: '2026-03-20T10:00:00Z',
        finalized_at: '2026-03-22T14:30:00Z',
        reviewed_by_user_id: null,
        reviewed_at: null,
        created_at: '2026-03-20T10:00:00Z',
        updated_at: '2026-03-22T14:30:00Z',
      },
    ]),
    submitFeedback: vi.fn().mockResolvedValue({}),
    listDomainEvents: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('RemediationPostWorksPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders outcomes when data is present', async () => {
    renderWithProviders(<RemediationPostWorksPanel buildingId="b-1" />);
    await waitFor(() => {
      expect(screen.getByTestId('remediation-post-works-panel')).toBeTruthy();
    });
  });

  it('shows outcome card with grade delta', async () => {
    renderWithProviders(<RemediationPostWorksPanel buildingId="b-1" />);
    await waitFor(() => {
      expect(screen.getByTestId('remediation-outcome-card')).toBeTruthy();
    });
    expect(screen.getByText('C')).toBeTruthy();
    expect(screen.getByText('B')).toBeTruthy();
  });

  it('shows residual risks', async () => {
    renderWithProviders(<RemediationPostWorksPanel buildingId="b-1" />);
    await waitFor(() => {
      expect(screen.getByText('Remaining encapsulated material')).toBeTruthy();
    });
  });

  it('shows finalized status badge', async () => {
    renderWithProviders(<RemediationPostWorksPanel buildingId="b-1" />);
    await waitFor(() => {
      expect(screen.getByText('finalized')).toBeTruthy();
    });
  });

  it('shows empty state when no outcomes', async () => {
    vi.mocked(remediationPostWorksApi.getBuildingOutcomes).mockResolvedValueOnce([]);
    renderWithProviders(<RemediationPostWorksPanel buildingId="b-1" />);
    await waitFor(() => {
      expect(screen.getByTestId('no-outcomes')).toBeTruthy();
    });
  });
});
