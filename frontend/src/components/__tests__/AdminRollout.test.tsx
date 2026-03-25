import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { rolloutApi } from '@/api/rollout';
import AdminRollout from '@/pages/AdminRollout';

vi.mock('@/api/rollout', () => ({
  rolloutApi: {
    listGrants: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'g-1',
          building_id: 'b-1',
          building_address: '10 Rue du Lac',
          grantee_email: 'alice@example.ch',
          grantee_org_id: null,
          grantee_org_name: null,
          grant_type: 'viewer',
          scope: 'read',
          expires_at: '2026-12-31T00:00:00Z',
          revoked_at: null,
          created_at: '2026-03-01T00:00:00Z',
          created_by: 'admin',
        },
        {
          id: 'g-2',
          building_id: 'b-2',
          building_address: '5 Avenue des Alpes',
          grantee_email: 'bob@example.ch',
          grantee_org_id: 'org-1',
          grantee_org_name: 'DiagSwiss',
          grant_type: 'collaborator',
          scope: 'write',
          expires_at: null,
          revoked_at: null,
          created_at: '2026-03-02T00:00:00Z',
          created_by: 'admin',
        },
      ],
      total: 2,
      page: 1,
      size: 50,
      pages: 1,
    }),
    listEvents: vi.fn().mockResolvedValue([
      {
        id: 'ev-1',
        grant_id: 'g-1',
        event_type: 'grant_created',
        actor_email: 'admin@example.ch',
        detail: 'Access granted to alice@example.ch',
        created_at: '2026-03-01T00:00:00Z',
      },
    ]),
    createGrant: vi.fn().mockResolvedValue({ id: 'g-new' }),
    revokeGrant: vi.fn().mockResolvedValue(undefined),
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

describe('AdminRollout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page title', async () => {
    render(<AdminRollout />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('rollout.title')).toBeInTheDocument();
    });
  });

  it('renders grants table with addresses', async () => {
    render(<AdminRollout />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('10 Rue du Lac')).toBeInTheDocument();
      expect(screen.getByText('5 Avenue des Alpes')).toBeInTheDocument();
    });
  });

  it('renders grantee emails', async () => {
    render(<AdminRollout />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('alice@example.ch')).toBeInTheDocument();
      expect(screen.getByText('bob@example.ch')).toBeInTheDocument();
    });
  });

  it('renders org name for org-level grants', async () => {
    render(<AdminRollout />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('DiagSwiss')).toBeInTheDocument();
    });
  });

  it('renders grant type badges', async () => {
    render(<AdminRollout />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('viewer')).toBeInTheDocument();
      expect(screen.getByText('collaborator')).toBeInTheDocument();
    });
  });

  it('renders event log', async () => {
    render(<AdminRollout />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('Access granted to alice@example.ch')).toBeInTheDocument();
    });
  });

  it('shows create form on button click', async () => {
    render(<AdminRollout />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('rollout-create-button')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('rollout-create-button'));
    expect(screen.getByTestId('rollout-create-form')).toBeInTheDocument();
  });

  it('calls revokeGrant on revoke click', async () => {
    render(<AdminRollout />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('revoke-g-1')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('revoke-g-1'));
    await waitFor(() => {
      expect(rolloutApi.revokeGrant).toHaveBeenCalledWith('g-1');
    });
  });
});
