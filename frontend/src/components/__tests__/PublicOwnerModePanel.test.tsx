import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { publicSectorApi } from '@/api/publicSector';
import { PublicOwnerModePanel } from '../building-detail/PublicOwnerModePanel';

vi.mock('@/api/publicSector', () => ({
  publicSectorApi: {
    getPublicOwnerMode: vi.fn(),
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

const mockMode = {
  id: 'mode-1',
  organization_id: 'org-1',
  mode_type: 'municipal',
  is_active: true,
  governance_level: 'enhanced',
  requires_committee_review: true,
  requires_review_pack: true,
  default_review_audience: ['Finance Dept', 'Legal Dept'],
  notes: null,
  activated_at: '2026-01-01T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

describe('PublicOwnerModePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders mode badge when mode is configured', async () => {
    vi.mocked(publicSectorApi.getPublicOwnerMode).mockResolvedValue(mockMode);
    render(<PublicOwnerModePanel orgId="org-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('public-owner-mode-panel')).toBeInTheDocument();
      expect(screen.getByTestId('public-owner-mode-badge')).toBeInTheDocument();
    });
  });

  it('renders governance level badge', async () => {
    vi.mocked(publicSectorApi.getPublicOwnerMode).mockResolvedValue(mockMode);
    render(<PublicOwnerModePanel orgId="org-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('governance-level-badge')).toBeInTheDocument();
    });
  });

  it('shows committee review requirement', async () => {
    vi.mocked(publicSectorApi.getPublicOwnerMode).mockResolvedValue(mockMode);
    render(<PublicOwnerModePanel orgId="org-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('requires-committee-review')).toBeInTheDocument();
    });
  });

  it('shows review pack requirement', async () => {
    vi.mocked(publicSectorApi.getPublicOwnerMode).mockResolvedValue(mockMode);
    render(<PublicOwnerModePanel orgId="org-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('requires-review-pack')).toBeInTheDocument();
    });
  });

  it('renders default review audience list', async () => {
    vi.mocked(publicSectorApi.getPublicOwnerMode).mockResolvedValue(mockMode);
    render(<PublicOwnerModePanel orgId="org-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('review-audience')).toBeInTheDocument();
      expect(screen.getByText('Finance Dept')).toBeInTheDocument();
      expect(screen.getByText('Legal Dept')).toBeInTheDocument();
    });
  });

  it('renders nothing when API returns 404', async () => {
    vi.mocked(publicSectorApi.getPublicOwnerMode).mockRejectedValue(new Error('Not found'));
    const { container } = render(<PublicOwnerModePanel orgId="org-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(container.querySelector('[data-testid="public-owner-mode-panel"]')).not.toBeInTheDocument();
    });
  });

  it('hides committee review when not required', async () => {
    vi.mocked(publicSectorApi.getPublicOwnerMode).mockResolvedValue({
      ...mockMode,
      requires_committee_review: false,
    });
    render(<PublicOwnerModePanel orgId="org-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('public-owner-mode-panel')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('requires-committee-review')).not.toBeInTheDocument();
  });
});
