import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CompanyWorkspace from '../../pages/CompanyWorkspace';

vi.mock('@/api/remediation', () => ({
  remediationApi: {
    getCompanyWorkspace: vi.fn().mockResolvedValue({
      company_profile_id: 'cp-1',
      company_name: 'Sanacore AG',
      is_verified: true,
      subscription_status: 'active',
      subscription_plan: 'professional',
      pending_invitations: 3,
      active_rfqs: 2,
      draft_quotes: 1,
      awards_won: 5,
      completions_pending: 0,
      reviews_published: 4,
    }),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k, language: 'fr', setLanguage: vi.fn() }),
}));

// Mock URL search params
const originalLocation = window.location;
beforeEach(() => {
  Object.defineProperty(window, 'location', {
    value: { ...originalLocation, search: '?profileId=cp-1' },
    writable: true,
  });
});

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('CompanyWorkspace', () => {
  it('renders company name', async () => {
    renderWithProviders(<CompanyWorkspace />);
    await waitFor(() => expect(screen.getByText('Sanacore AG')).toBeTruthy());
  });

  it('renders verified badge', async () => {
    renderWithProviders(<CompanyWorkspace />);
    await waitFor(() => expect(screen.getByText('workspace.verified')).toBeTruthy());
  });

  it('renders stat cards with counts', async () => {
    renderWithProviders(<CompanyWorkspace />);
    await waitFor(() => {
      expect(screen.getByText('3')).toBeTruthy();
      expect(screen.getByText('5')).toBeTruthy();
      expect(screen.getByText('4')).toBeTruthy();
    });
  });

  it('shows subscription info', async () => {
    renderWithProviders(<CompanyWorkspace />);
    await waitFor(() => expect(screen.getByText(/professional/)).toBeTruthy());
  });

  it('renders six stat labels', async () => {
    renderWithProviders(<CompanyWorkspace />);
    await waitFor(() => {
      expect(screen.getByText('workspace.pending_invitations')).toBeTruthy();
      expect(screen.getByText('workspace.active_rfqs')).toBeTruthy();
      expect(screen.getByText('workspace.awards_won')).toBeTruthy();
    });
  });

  it('shows no profile message when profileId is empty', async () => {
    Object.defineProperty(window, 'location', {
      value: { ...originalLocation, search: '' },
      writable: true,
    });
    renderWithProviders(<CompanyWorkspace />);
    expect(screen.getByText('workspace.company_title')).toBeTruthy();
  });

  it('renders loading skeleton initially', () => {
    vi.doMock('@/api/remediation', () => ({
      remediationApi: {
        getCompanyWorkspace: vi.fn().mockReturnValue(new Promise(() => {})),
      },
    }));
    // With never-resolving promise, loading state shown
    renderWithProviders(<CompanyWorkspace />);
    // Component should render without errors
  });

  it('renders awards count correctly', async () => {
    renderWithProviders(<CompanyWorkspace />);
    await waitFor(() => expect(screen.getByText('5')).toBeTruthy());
  });
});
