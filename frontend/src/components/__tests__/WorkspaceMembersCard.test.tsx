import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { workspaceApi } from '@/api/workspace';
import WorkspaceMembersCard from '../building-detail/WorkspaceMembersCard';

vi.mock('@/api/workspace', () => ({
  workspaceApi: {
    listMembers: vi.fn().mockResolvedValue([
      {
        id: 'wm-1',
        building_id: 'b-1',
        user_id: 'u-1',
        organization_id: 'org-1',
        role: 'manager',
        access_scope: 'full',
        user_name: 'Jean Dupont',
        user_email: 'jean@example.ch',
        org_name: 'Regie Romande',
        created_at: '2025-01-01T00:00:00Z',
      },
      {
        id: 'wm-2',
        building_id: 'b-1',
        user_id: 'u-2',
        organization_id: null,
        role: 'viewer',
        access_scope: 'read_only',
        user_name: 'Marie Martin',
        user_email: 'marie@example.ch',
        org_name: null,
        created_at: '2025-02-01T00:00:00Z',
      },
    ]),
    addMember: vi.fn().mockResolvedValue({ id: 'wm-3' }),
    removeMember: vi.fn().mockResolvedValue(undefined),
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

describe('WorkspaceMembersCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders member list with names', async () => {
    render(<WorkspaceMembersCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Jean Dupont')).toBeInTheDocument();
      expect(screen.getByText('Marie Martin')).toBeInTheDocument();
    });
  });

  it('renders role badges', async () => {
    render(<WorkspaceMembersCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const badges = screen.getAllByTestId('member-role-badge');
      expect(badges.length).toBe(2);
    });
  });

  it('renders scope badges', async () => {
    render(<WorkspaceMembersCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const badges = screen.getAllByTestId('member-scope-badge');
      expect(badges.length).toBe(2);
    });
  });

  it('shows organization name for members with both user and org', async () => {
    render(<WorkspaceMembersCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Regie Romande')).toBeInTheDocument();
    });
  });

  it('renders add member button', async () => {
    render(<WorkspaceMembersCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('workspace-add-member-btn')).toBeInTheDocument();
    });
  });

  it('opens add form when button clicked', async () => {
    render(<WorkspaceMembersCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('workspace-add-member-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('workspace-add-member-btn'));
    expect(screen.getByTestId('workspace-add-form')).toBeInTheDocument();
    expect(screen.getByTestId('workspace-role-select')).toBeInTheDocument();
  });

  it('renders remove buttons for each member', async () => {
    render(<WorkspaceMembersCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const removeBtns = screen.getAllByTestId('workspace-remove-btn');
      expect(removeBtns.length).toBe(2);
    });
  });

  it('shows empty state when no members', async () => {
    vi.mocked(workspaceApi.listMembers).mockResolvedValueOnce([]);
    render(<WorkspaceMembersCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('workspace-empty')).toBeInTheDocument();
    });
  });
});
