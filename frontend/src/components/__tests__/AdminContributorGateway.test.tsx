import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AdminContributorGateway from '@/pages/AdminContributorGateway';
import { exchangeHardeningApi, type ContributorSubmission, type ContributorRequest } from '@/api/exchangeHardening';

vi.mock('@/utils/formatters', () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(' '),
  formatDate: (d: string) => d,
}));

vi.mock('@/api/exchangeHardening', () => ({
  exchangeHardeningApi: {
    listContributorRequests: vi.fn(),
    listPendingSubmissions: vi.fn(),
    acceptSubmission: vi.fn(),
    rejectSubmission: vi.fn(),
  },
}));

const mockSubmissions: ContributorSubmission[] = [
  {
    id: 'sub-1',
    request_id: 'req-1',
    contributor_org_id: null,
    contributor_name: 'Sanacore AG',
    submission_type: 'completion_report',
    file_url: null,
    structured_data: null,
    notes: 'All zones treated',
    status: 'pending_review',
    reviewed_by_user_id: null,
    reviewed_at: null,
    review_notes: null,
    created_at: '2026-03-25T10:00:00Z',
  },
];

const mockRequests: ContributorRequest[] = [
  {
    id: 'req-1',
    building_id: 'b-1',
    contributor_type: 'contractor',
    scope_description: 'Asbestos removal report',
    access_token: 'tok-123',
    expires_at: '2026-03-28T10:00:00Z',
    status: 'open',
    created_by_user_id: 'u-1',
    created_at: '2026-03-25T10:00:00Z',
    updated_at: '2026-03-25T10:00:00Z',
  },
];

function renderWithQuery(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('AdminContributorGateway', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(exchangeHardeningApi.listPendingSubmissions).mockResolvedValue(mockSubmissions);
    vi.mocked(exchangeHardeningApi.listContributorRequests).mockResolvedValue(mockRequests);
  });

  it('renders page title', async () => {
    renderWithQuery(<AdminContributorGateway />);
    expect(screen.getByTestId('admin-contributor-gateway')).toBeTruthy();
    expect(screen.getByText('Contributor Gateway')).toBeTruthy();
  });

  it('renders tabs', async () => {
    renderWithQuery(<AdminContributorGateway />);
    await waitFor(() => {
      expect(screen.getByTestId('tab-submissions')).toBeTruthy();
      expect(screen.getByTestId('tab-requests')).toBeTruthy();
    });
  });

  it('shows pending submissions by default', async () => {
    renderWithQuery(<AdminContributorGateway />);
    await waitFor(() => {
      expect(screen.getByTestId('submissions-list')).toBeTruthy();
    });
  });

  it('renders submission with contributor name', async () => {
    renderWithQuery(<AdminContributorGateway />);
    await waitFor(() => {
      expect(screen.getByText(/Sanacore AG/)).toBeTruthy();
    });
  });

  it('renders submission notes', async () => {
    renderWithQuery(<AdminContributorGateway />);
    await waitFor(() => {
      expect(screen.getByText(/All zones treated/)).toBeTruthy();
    });
  });

  it('renders accept and reject buttons for submissions', async () => {
    renderWithQuery(<AdminContributorGateway />);
    await waitFor(() => {
      expect(screen.getByTestId('accept-sub-1')).toBeTruthy();
      expect(screen.getByTestId('reject-sub-1')).toBeTruthy();
    });
  });

  it('switches to requests tab', async () => {
    renderWithQuery(<AdminContributorGateway />);
    await waitFor(() => {
      expect(screen.getByTestId('tab-requests')).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId('tab-requests'));
    await waitFor(() => {
      expect(screen.getByTestId('requests-list')).toBeTruthy();
    });
  });

  it('shows contributor type in requests', async () => {
    renderWithQuery(<AdminContributorGateway />);
    fireEvent.click(screen.getByTestId('tab-requests'));
    await waitFor(() => {
      expect(screen.getByText('contractor')).toBeTruthy();
    });
  });

  it('shows scope description in requests', async () => {
    renderWithQuery(<AdminContributorGateway />);
    fireEvent.click(screen.getByTestId('tab-requests'));
    await waitFor(() => {
      expect(screen.getByText('Asbestos removal report')).toBeTruthy();
    });
  });

  it('shows empty state when no submissions', async () => {
    vi.mocked(exchangeHardeningApi.listPendingSubmissions).mockResolvedValue([]);
    renderWithQuery(<AdminContributorGateway />);
    await waitFor(() => {
      expect(screen.getByTestId('no-submissions')).toBeTruthy();
    });
  });

  it('shows empty state when no requests', async () => {
    vi.mocked(exchangeHardeningApi.listContributorRequests).mockResolvedValue([]);
    renderWithQuery(<AdminContributorGateway />);
    fireEvent.click(screen.getByTestId('tab-requests'));
    await waitFor(() => {
      expect(screen.getByTestId('no-requests')).toBeTruthy();
    });
  });
});
