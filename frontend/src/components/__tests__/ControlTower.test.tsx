import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import ControlTower from '@/pages/ControlTower';
import * as controlTowerApi from '@/api/controlTower';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/utils/formatters', () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(' '),
  formatDate: (d: string) => d,
}));

const mockSummary: controlTowerApi.ControlTowerSummary = {
  p0_blockers: 2,
  p1_authority: 1,
  p2_overdue: 3,
  p3_pending: 5,
  p4_upcoming: 4,
  total: 15,
};

const mockActions: controlTowerApi.ControlTowerAction[] = [
  {
    id: 'act-1',
    priority: 'P0',
    source_type: 'procedural_blocker',
    title: 'Missing asbestos clearance',
    description: 'Cannot proceed without clearance',
    building_id: 'b-1',
    building_address: 'Rue du Test 1, Lausanne',
    due_date: '2026-03-01',
    assigned_org: 'DiagSwiss',
    assigned_user: 'Jean Muller',
    link: '/buildings/b-1',
    confidence: 0.92,
    freshness: '2h ago',
  },
  {
    id: 'act-2',
    priority: 'P1',
    source_type: 'authority_request',
    title: 'Canton VD review pending',
    description: null,
    building_id: 'b-2',
    building_address: 'Route de Berne 5',
    due_date: '2026-04-15',
    assigned_org: null,
    assigned_user: null,
    link: '/buildings/b-2',
    confidence: null,
    freshness: null,
  },
  {
    id: 'act-3',
    priority: 'P2',
    source_type: 'obligation',
    title: 'Annual check overdue',
    description: null,
    building_id: 'b-1',
    building_address: 'Rue du Test 1, Lausanne',
    due_date: '2026-01-01',
    assigned_org: null,
    assigned_user: null,
    link: '/buildings/b-1',
    confidence: null,
    freshness: null,
  },
];

vi.mock('@/api/controlTower', async () => {
  return {
    getActionFeed: vi.fn(),
    getActionSummary: vi.fn(),
    snoozeAction: vi.fn(),
    filterSnoozed: (actions: controlTowerApi.ControlTowerAction[]) => actions,
  };
});

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({
      data: {
        items: [
          { id: 'b-1', address: 'Rue du Test 1', city: 'Lausanne' },
          { id: 'b-2', address: 'Route de Berne 5', city: 'Bern' },
        ],
      },
    }),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MemoryRouter>
  );
};

describe('ControlTower', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(controlTowerApi.getActionSummary).mockResolvedValue(mockSummary);
    vi.mocked(controlTowerApi.getActionFeed).mockResolvedValue(mockActions);
  });

  it('renders loading state initially', () => {
    vi.mocked(controlTowerApi.getActionSummary).mockReturnValue(new Promise(() => {}));
    vi.mocked(controlTowerApi.getActionFeed).mockReturnValue(new Promise(() => {}));
    render(<ControlTower />, { wrapper: createWrapper() });
    expect(screen.getByTestId('control-tower-loading')).toBeInTheDocument();
  });

  it('renders the page title after loading', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('control-tower-page')).toBeInTheDocument();
    });
    expect(screen.getByText('control_tower.title')).toBeInTheDocument();
  });

  it('renders all 5 priority summary cards', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('card-p0')).toBeInTheDocument();
    });
    expect(screen.getByTestId('card-p1')).toBeInTheDocument();
    expect(screen.getByTestId('card-p2')).toBeInTheDocument();
    expect(screen.getByTestId('card-p3')).toBeInTheDocument();
    expect(screen.getByTestId('card-p4')).toBeInTheDocument();
  });

  it('displays correct counts on summary cards', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('card-p0')).toBeInTheDocument();
    });
    expect(screen.getByTestId('card-p0')).toHaveTextContent('2');
    expect(screen.getByTestId('card-p1')).toHaveTextContent('1');
    expect(screen.getByTestId('card-p2')).toHaveTextContent('3');
    expect(screen.getByTestId('card-p3')).toHaveTextContent('5');
    expect(screen.getByTestId('card-p4')).toHaveTextContent('4');
  });

  it('renders action rows with priority badges', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('action-row-act-1')).toBeInTheDocument();
    });
    expect(screen.getByTestId('priority-badge-act-1')).toHaveTextContent('control_tower.priority_p0');
    expect(screen.getByTestId('action-row-act-2')).toBeInTheDocument();
    expect(screen.getByTestId('action-row-act-3')).toBeInTheDocument();
  });

  it('shows confidence and freshness indicators when present', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('confidence-act-1')).toBeInTheDocument();
    });
    expect(screen.getByTestId('confidence-act-1')).toHaveTextContent('92%');
    expect(screen.getByTestId('freshness-act-1')).toHaveTextContent('2h ago');
  });

  it('renders filter controls', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('control-tower-filters')).toBeInTheDocument();
    });
    expect(screen.getByTestId('filter-source')).toBeInTheDocument();
    expect(screen.getByTestId('filter-priority')).toBeInTheDocument();
    expect(screen.getByTestId('filter-my-queue')).toBeInTheDocument();
  });

  it('renders snooze buttons on action rows', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('snooze-btn-act-1')).toBeInTheDocument();
    });
  });

  it('opens snooze menu on click', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('snooze-btn-act-1')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('snooze-btn-act-1'));
    expect(screen.getByTestId('snooze-menu-act-1')).toBeInTheDocument();
    expect(screen.getByTestId('snooze-7d-act-1')).toBeInTheDocument();
  });

  it('shows empty state when no actions', async () => {
    vi.mocked(controlTowerApi.getActionFeed).mockResolvedValue([]);
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('control-tower-empty')).toBeInTheDocument();
    });
  });

  it('renders error state on fetch failure', async () => {
    vi.mocked(controlTowerApi.getActionSummary).mockRejectedValue(new Error('fail'));
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('control-tower-error')).toBeInTheDocument();
    });
  });

  it('renders refresh button', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('control-tower-refresh')).toBeInTheDocument();
    });
  });
});
