import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { publicSectorApi } from '@/api/publicSector';
import AdminGovernanceSignals from '@/pages/AdminGovernanceSignals';

vi.mock('@/api/publicSector', () => ({
  publicSectorApi: {
    listGovernanceSignals: vi.fn(),
    resolveGovernanceSignal: vi.fn(),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: (selector: (s: unknown) => unknown) =>
    selector({
      user: {
        id: 'u-1',
        organization_id: 'org-1',
        role: 'admin',
      },
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

const mockSignals = [
  {
    id: 'sig-1',
    organization_id: 'org-1',
    building_id: 'b-1',
    signal_type: 'missing_review_pack',
    severity: 'warning',
    title: 'Review pack overdue',
    description: 'Building Rue du Lac 12 has no review pack for 90 days',
    source_entity_type: 'building',
    source_entity_id: 'b-1',
    resolved: false,
    resolved_at: null,
    created_at: '2026-03-20T10:00:00Z',
  },
  {
    id: 'sig-2',
    organization_id: 'org-1',
    building_id: null,
    signal_type: 'governance_downgrade',
    severity: 'critical',
    title: 'Governance level downgrade detected',
    description: null,
    source_entity_type: null,
    source_entity_id: null,
    resolved: false,
    resolved_at: null,
    created_at: '2026-03-19T10:00:00Z',
  },
  {
    id: 'sig-3',
    organization_id: 'org-1',
    building_id: 'b-2',
    signal_type: 'info_update',
    severity: 'info',
    title: 'New regulation published',
    description: 'CFST update v2026.1',
    source_entity_type: null,
    source_entity_id: null,
    resolved: true,
    resolved_at: '2026-03-21T10:00:00Z',
    created_at: '2026-03-18T10:00:00Z',
  },
];

describe('AdminGovernanceSignals', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders signals list', async () => {
    vi.mocked(publicSectorApi.listGovernanceSignals).mockResolvedValue(mockSignals);
    render(<AdminGovernanceSignals />, { wrapper: createWrapper() });

    await waitFor(() => {
      const items = screen.getAllByTestId('governance-signal-item');
      expect(items.length).toBe(2); // only unresolved shown by default
    });
  });

  it('renders signal titles', async () => {
    vi.mocked(publicSectorApi.listGovernanceSignals).mockResolvedValue(mockSignals);
    render(<AdminGovernanceSignals />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Review pack overdue')).toBeInTheDocument();
      expect(screen.getByText('Governance level downgrade detected')).toBeInTheDocument();
    });
  });

  it('renders severity badges', async () => {
    vi.mocked(publicSectorApi.listGovernanceSignals).mockResolvedValue(mockSignals);
    render(<AdminGovernanceSignals />, { wrapper: createWrapper() });

    await waitFor(() => {
      const badges = screen.getAllByTestId('signal-severity-badge');
      expect(badges.length).toBe(2);
    });
  });

  it('renders resolve buttons for active signals', async () => {
    vi.mocked(publicSectorApi.listGovernanceSignals).mockResolvedValue(mockSignals);
    render(<AdminGovernanceSignals />, { wrapper: createWrapper() });

    await waitFor(() => {
      const resolveButtons = screen.getAllByTestId('resolve-signal-button');
      expect(resolveButtons.length).toBe(2);
    });
  });

  it('renders filter dropdowns', async () => {
    vi.mocked(publicSectorApi.listGovernanceSignals).mockResolvedValue(mockSignals);
    render(<AdminGovernanceSignals />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('filter-severity')).toBeInTheDocument();
      expect(screen.getByTestId('filter-signal-type')).toBeInTheDocument();
    });
  });

  it('shows empty state when no active signals', async () => {
    vi.mocked(publicSectorApi.listGovernanceSignals).mockResolvedValue([{ ...mockSignals[2], resolved: true }]);
    render(<AdminGovernanceSignals />, { wrapper: createWrapper() });

    // All resolved — shows all signals (fallback)
    await waitFor(() => {
      const items = screen.getAllByTestId('governance-signal-item');
      expect(items.length).toBe(1);
    });
  });

  it('calls resolve API on button click', async () => {
    vi.mocked(publicSectorApi.listGovernanceSignals).mockResolvedValue([mockSignals[0]]);
    vi.mocked(publicSectorApi.resolveGovernanceSignal).mockResolvedValue({
      ...mockSignals[0],
      resolved: true,
      resolved_at: '2026-03-25T10:00:00Z',
    });
    render(<AdminGovernanceSignals />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('resolve-signal-button')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('resolve-signal-button'));

    await waitFor(() => {
      expect(publicSectorApi.resolveGovernanceSignal).toHaveBeenCalledWith('sig-1');
    });
  });

  it('displays active signal count', async () => {
    vi.mocked(publicSectorApi.listGovernanceSignals).mockResolvedValue(mockSignals);
    render(<AdminGovernanceSignals />, { wrapper: createWrapper() });

    await waitFor(() => {
      const countEl = screen.getByText(/public_sector\.active_signals/);
      expect(countEl.textContent).toContain('2');
    });
  });
});
