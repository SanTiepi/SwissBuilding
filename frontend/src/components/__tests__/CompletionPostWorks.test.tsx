import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { remediationPostWorksApi } from '@/api/remediationPostWorks';
import CompletionPostWorks from '../marketplace/CompletionPostWorks';

vi.mock('@/api/remediationPostWorks', () => ({
  remediationPostWorksApi: {
    getPostWorks: vi.fn(),
    draftPostWorks: vi.fn().mockResolvedValue({ id: 'pwl-1', status: 'drafted' }),
    reviewPostWorks: vi.fn().mockResolvedValue({ id: 'pwl-1', status: 'review_required' }),
    finalizePostWorks: vi.fn().mockResolvedValue({ id: 'pwl-1', status: 'finalized' }),
    submitFeedback: vi.fn().mockResolvedValue({ id: 'fb-1' }),
    getBuildingOutcomes: vi.fn().mockResolvedValue([]),
    listDomainEvents: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

vi.mock('@/store/toastStore', () => ({
  toast: vi.fn(),
}));

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('CompletionPostWorks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows draft button when completion is fully_confirmed and no post-works exist', async () => {
    vi.mocked(remediationPostWorksApi.getPostWorks).mockRejectedValueOnce(new Error('not found'));
    renderWithProviders(<CompletionPostWorks completionId="cc-1" completionStatus="fully_confirmed" />);
    await waitFor(() => {
      expect(screen.getByTestId('pw-draft-action')).toBeTruthy();
    });
  });

  it('shows not-ready message when completion is pending', async () => {
    vi.mocked(remediationPostWorksApi.getPostWorks).mockRejectedValueOnce(new Error('not found'));
    renderWithProviders(<CompletionPostWorks completionId="cc-1" completionStatus="pending" />);
    await waitFor(() => {
      expect(screen.getByTestId('pw-not-ready')).toBeTruthy();
    });
  });

  it('shows review button when status is drafted', async () => {
    vi.mocked(remediationPostWorksApi.getPostWorks).mockResolvedValueOnce({
      id: 'pwl-1',
      completion_confirmation_id: 'cc-1',
      intervention_id: 'int-1',
      before_snapshot_id: null,
      after_snapshot_id: null,
      status: 'drafted',
      grade_delta: null,
      trust_delta: null,
      completeness_delta: null,
      residual_risks: null,
      drafted_at: '2026-03-20T10:00:00Z',
      finalized_at: null,
      reviewed_by_user_id: null,
      reviewed_at: null,
      created_at: '2026-03-20T10:00:00Z',
      updated_at: '2026-03-20T10:00:00Z',
    });
    renderWithProviders(<CompletionPostWorks completionId="cc-1" completionStatus="fully_confirmed" />);
    await waitFor(() => {
      expect(screen.getByTestId('review-post-works-btn')).toBeTruthy();
    });
  });

  it('shows finalize button when status is review_required', async () => {
    vi.mocked(remediationPostWorksApi.getPostWorks).mockResolvedValueOnce({
      id: 'pwl-1',
      completion_confirmation_id: 'cc-1',
      intervention_id: 'int-1',
      before_snapshot_id: null,
      after_snapshot_id: null,
      status: 'review_required',
      grade_delta: null,
      trust_delta: null,
      completeness_delta: null,
      residual_risks: null,
      drafted_at: '2026-03-20T10:00:00Z',
      finalized_at: null,
      reviewed_by_user_id: null,
      reviewed_at: null,
      created_at: '2026-03-20T10:00:00Z',
      updated_at: '2026-03-20T10:00:00Z',
    });
    renderWithProviders(<CompletionPostWorks completionId="cc-1" completionStatus="fully_confirmed" />);
    await waitFor(() => {
      expect(screen.getByTestId('finalize-post-works-btn')).toBeTruthy();
    });
  });

  it('shows feedback buttons when drafted', async () => {
    vi.mocked(remediationPostWorksApi.getPostWorks).mockResolvedValueOnce({
      id: 'pwl-1',
      completion_confirmation_id: 'cc-1',
      intervention_id: 'int-1',
      before_snapshot_id: null,
      after_snapshot_id: null,
      status: 'drafted',
      grade_delta: null,
      trust_delta: null,
      completeness_delta: null,
      residual_risks: null,
      drafted_at: '2026-03-20T10:00:00Z',
      finalized_at: null,
      reviewed_by_user_id: null,
      reviewed_at: null,
      created_at: '2026-03-20T10:00:00Z',
      updated_at: '2026-03-20T10:00:00Z',
    });
    renderWithProviders(<CompletionPostWorks completionId="cc-1" completionStatus="fully_confirmed" />);
    await waitFor(() => {
      expect(screen.getByTestId('feedback-confirm-btn')).toBeTruthy();
      expect(screen.getByTestId('feedback-correct-btn')).toBeTruthy();
      expect(screen.getByTestId('feedback-reject-btn')).toBeTruthy();
    });
  });

  it('shows finalized state with deltas', async () => {
    vi.mocked(remediationPostWorksApi.getPostWorks).mockResolvedValueOnce({
      id: 'pwl-1',
      completion_confirmation_id: 'cc-1',
      intervention_id: 'int-1',
      before_snapshot_id: null,
      after_snapshot_id: null,
      status: 'finalized',
      grade_delta: { before: 'C', after: 'B', change: '+1' },
      trust_delta: { before: 0.52, after: 0.78, change: 0.26 },
      completeness_delta: { before: 0.65, after: 0.82, change: 0.17 },
      residual_risks: [
        { risk_type: 'asbestos', description: 'Remaining material', severity: 'low' },
      ],
      drafted_at: '2026-03-20T10:00:00Z',
      finalized_at: '2026-03-22T14:30:00Z',
      reviewed_by_user_id: null,
      reviewed_at: null,
      created_at: '2026-03-20T10:00:00Z',
      updated_at: '2026-03-22T14:30:00Z',
    });
    renderWithProviders(<CompletionPostWorks completionId="cc-1" completionStatus="fully_confirmed" />);
    await waitFor(() => {
      expect(screen.getByTestId('completion-post-works')).toBeTruthy();
    });
    // Grade delta
    expect(screen.getByText(/C → B/)).toBeTruthy();
  });
});
