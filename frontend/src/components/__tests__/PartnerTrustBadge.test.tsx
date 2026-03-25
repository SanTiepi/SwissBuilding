import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PartnerTrustBadge } from '../PartnerTrustBadge';
import { partnerTrustApi, type PartnerTrustProfile } from '@/api/partnerTrust';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/utils/formatters', () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(' '),
}));

vi.mock('@/api/partnerTrust', () => ({
  partnerTrustApi: {
    getProfile: vi.fn(),
  },
}));

const mockProfile: PartnerTrustProfile = {
  id: 'pt-1',
  partner_org_id: 'org-1',
  delivery_reliability_score: 0.85,
  evidence_quality_score: 0.72,
  responsiveness_score: 0.91,
  overall_trust_level: 'strong',
  signal_count: 12,
  last_evaluated_at: '2026-03-20T10:00:00Z',
  notes: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-03-20T10:00:00Z',
};

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('PartnerTrustBadge', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(partnerTrustApi.getProfile).mockResolvedValue(mockProfile);
  });

  it('renders loading state when fetching by orgId', () => {
    vi.mocked(partnerTrustApi.getProfile).mockReturnValue(new Promise(() => {}));
    render(<PartnerTrustBadge orgId="org-1" />, { wrapper: createWrapper() });
    expect(screen.getByTestId('partner-trust-badge-loading')).toBeInTheDocument();
  });

  it('renders badge with trust level from fetched profile', async () => {
    render(<PartnerTrustBadge orgId="org-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('partner-trust-badge')).toBeInTheDocument();
    });
    expect(screen.getByTestId('partner-trust-badge')).toHaveAttribute('data-trust-level', 'strong');
    expect(screen.getByText('partner_trust.level_strong')).toBeInTheDocument();
  });

  it('renders badge from trustProfile prop without fetching', async () => {
    const weakProfile: PartnerTrustProfile = {
      ...mockProfile,
      overall_trust_level: 'weak',
      delivery_reliability_score: 0.2,
    };
    render(<PartnerTrustBadge trustProfile={weakProfile} />, { wrapper: createWrapper() });
    expect(screen.getByTestId('partner-trust-badge')).toHaveAttribute('data-trust-level', 'weak');
    expect(partnerTrustApi.getProfile).not.toHaveBeenCalled();
  });

  it('shows tooltip with sub-scores on hover', async () => {
    render(<PartnerTrustBadge trustProfile={mockProfile} />, { wrapper: createWrapper() });
    const badge = screen.getByTestId('partner-trust-badge');
    fireEvent.mouseEnter(badge.parentElement!);
    await waitFor(() => {
      expect(screen.getByTestId('partner-trust-tooltip')).toBeInTheDocument();
    });
    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('72%')).toBeInTheDocument();
    expect(screen.getByText('91%')).toBeInTheDocument();
  });

  it('hides tooltip on mouse leave', async () => {
    render(<PartnerTrustBadge trustProfile={mockProfile} />, { wrapper: createWrapper() });
    const badge = screen.getByTestId('partner-trust-badge');
    fireEvent.mouseEnter(badge.parentElement!);
    await waitFor(() => {
      expect(screen.getByTestId('partner-trust-tooltip')).toBeInTheDocument();
    });
    fireEvent.mouseLeave(badge.parentElement!);
    await waitFor(() => {
      expect(screen.queryByTestId('partner-trust-tooltip')).not.toBeInTheDocument();
    });
  });

  it('calls API with correct org ID', async () => {
    render(<PartnerTrustBadge orgId="org-42" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(partnerTrustApi.getProfile).toHaveBeenCalledWith('org-42');
    });
  });
});
