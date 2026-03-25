import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import MarketplaceReviews from '@/pages/MarketplaceReviews';

vi.mock('@/api/marketplaceRfq', () => ({
  marketplaceRfqApi: {
    getPendingReviews: vi.fn().mockResolvedValue([
      {
        id: 'rev-1',
        completion_confirmation_id: 'cc-1',
        client_request_id: 'req-1',
        company_profile_id: 'cp-1',
        reviewer_user_id: 'u-1',
        reviewer_type: 'client',
        rating: 4,
        quality_score: 4,
        timeliness_score: 5,
        communication_score: 3,
        comment: 'Excellent work on the remediation project.',
        status: 'submitted',
        moderated_by_user_id: null,
        moderated_at: null,
        moderation_notes: null,
        rejection_reason: null,
        submitted_at: '2026-03-20T10:00:00Z',
        published_at: null,
        created_at: '2026-03-20T10:00:00Z',
        updated_at: '2026-03-20T10:00:00Z',
      },
    ]),
    moderateReview: vi.fn(),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

vi.mock('@/utils/formatters', () => ({
  cn: (...args: (string | undefined | false)[]) => args.filter(Boolean).join(' '),
  formatDateTime: (d: string) => d,
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>,
  );
}

describe('MarketplaceReviews', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page title', async () => {
    renderWithProviders(<MarketplaceReviews />);
    expect(screen.getByText('marketplace.review_moderation_title')).toBeInTheDocument();
  });

  it('displays pending review after loading', async () => {
    renderWithProviders(<MarketplaceReviews />);
    await waitFor(() => {
      expect(screen.getByText('Excellent work on the remediation project.')).toBeInTheDocument();
    });
  });

  it('shows rating display', async () => {
    renderWithProviders(<MarketplaceReviews />);
    await waitFor(() => {
      expect(screen.getByText('4/5')).toBeInTheDocument();
    });
  });

  it('shows approve and reject buttons', async () => {
    renderWithProviders(<MarketplaceReviews />);
    await waitFor(() => {
      expect(screen.getByText('marketplace.approve')).toBeInTheDocument();
      expect(screen.getByText('marketplace.reject')).toBeInTheDocument();
    });
  });

  it('shows reviewer type', async () => {
    renderWithProviders(<MarketplaceReviews />);
    await waitFor(() => {
      expect(screen.getByText(/client/)).toBeInTheDocument();
    });
  });

  it('shows sub-scores', async () => {
    renderWithProviders(<MarketplaceReviews />);
    await waitFor(() => {
      expect(screen.getAllByText(/4\/5/).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/5\/5/).length).toBeGreaterThanOrEqual(1);
    });
  });
});
