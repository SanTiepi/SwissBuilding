import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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
  overdueObligations: [
    {
      id: 'obl-1',
      building_id: 'b-1',
      title: 'Controle amiante annuel',
      description: 'Overdue check',
      obligation_type: 'regulatory',
      priority: 'high',
      status: 'pending',
      due_date: '2025-01-01',
      completed_at: null,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ],
  dueSoonObligations: [
    {
      id: 'obl-2',
      building_id: 'b-1',
      title: 'Renouvellement contrat',
      description: null,
      obligation_type: 'contractual',
      priority: 'medium',
      status: 'pending',
      due_date: '2026-04-10',
      completed_at: null,
      created_at: '2024-02-01T00:00:00Z',
      updated_at: '2024-02-01T00:00:00Z',
    },
  ],
  pendingInboxCount: 3,
  unmatchedPublications: [
    {
      id: 'pub-1',
      building_id: null,
      source_system: 'Batiscan',
      source_mission_id: 'M-001',
      current_version: 1,
      match_state: 'unmatched',
      match_key: null,
      match_key_type: null,
      mission_type: 'amiante',
      report_pdf_url: null,
      structured_summary: null,
      annexes: [],
      payload_hash: 'abc',
      published_at: '2026-01-01T00:00:00Z',
      is_immutable: false,
      versions: [],
    },
  ] as any,
  newIntakeRequests: 2,
  buildings: [
    {
      id: 'b-1',
      egid: 1234,
      egrid: null,
      official_id: null,
      address: 'Rue du Test 1',
      postal_code: '1000',
      city: 'Lausanne',
      canton: 'VD',
      latitude: null,
      longitude: null,
      parcel_number: null,
      construction_year: 1960,
      renovation_year: null,
      building_type: 'residential',
      floors_above: 3,
    },
  ] as any,
};

vi.mock('@/api/controlTower', async () => {
  return {
    fetchControlTowerData: vi.fn(),
    buildNextBestActions: (await vi.importActual('@/api/controlTower') as any).buildNextBestActions,
  };
});

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
    vi.mocked(controlTowerApi.fetchControlTowerData).mockResolvedValue(mockSummary);
  });

  it('renders loading state initially', () => {
    vi.mocked(controlTowerApi.fetchControlTowerData).mockReturnValue(new Promise(() => {}));
    render(<ControlTower />, { wrapper: createWrapper() });
    expect(screen.getByTestId('control-tower-loading')).toBeInTheDocument();
  });

  it('renders the page title', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('control-tower-page')).toBeInTheDocument();
    });
    expect(screen.getByText('control_tower.title')).toBeInTheDocument();
  });

  it('renders all 5 summary cards', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('card-overdue')).toBeInTheDocument();
    });
    expect(screen.getByTestId('card-due-soon')).toBeInTheDocument();
    expect(screen.getByTestId('card-inbox')).toBeInTheDocument();
    expect(screen.getByTestId('card-unmatched')).toBeInTheDocument();
    expect(screen.getByTestId('card-intake')).toBeInTheDocument();
  });

  it('displays correct counts on summary cards', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('card-overdue')).toBeInTheDocument();
    });
    // Overdue: 1
    expect(screen.getByTestId('card-overdue')).toHaveTextContent('1');
    // Due soon: 1
    expect(screen.getByTestId('card-due-soon')).toHaveTextContent('1');
    // Inbox: 3
    expect(screen.getByTestId('card-inbox')).toHaveTextContent('3');
    // Unmatched: 1
    expect(screen.getByTestId('card-unmatched')).toHaveTextContent('1');
    // Intake: 2
    expect(screen.getByTestId('card-intake')).toHaveTextContent('2');
  });

  it('renders next best actions list', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('control-tower-actions')).toBeInTheDocument();
    });
  });

  it('renders action rows with correct types', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('action-row-overdue-obl-1')).toBeInTheDocument();
    });
    expect(screen.getByTestId('action-row-unmatched-pub-1')).toBeInTheDocument();
    expect(screen.getByTestId('action-row-inbox-pending')).toBeInTheDocument();
    expect(screen.getByTestId('action-row-intake-new')).toBeInTheDocument();
    expect(screen.getByTestId('action-row-due-soon-obl-2')).toBeInTheDocument();
  });

  it('renders refresh button', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('control-tower-refresh')).toBeInTheDocument();
    });
  });

  it('renders building filter dropdown', async () => {
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('control-tower-filter')).toBeInTheDocument();
    });
  });

  it('shows empty state when no actions', async () => {
    vi.mocked(controlTowerApi.fetchControlTowerData).mockResolvedValue({
      overdueObligations: [],
      dueSoonObligations: [],
      pendingInboxCount: 0,
      unmatchedPublications: [],
      newIntakeRequests: 0,
      buildings: [],
    });
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('control-tower-empty')).toBeInTheDocument();
    });
  });

  it('renders error state on fetch failure', async () => {
    vi.mocked(controlTowerApi.fetchControlTowerData).mockRejectedValue(new Error('fail'));
    render(<ControlTower />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('control-tower-error')).toBeInTheDocument();
    });
  });
});

describe('buildNextBestActions', () => {
  it('sorts actions by priority', () => {
    const actions = controlTowerApi.buildNextBestActions(mockSummary);
    expect(actions.length).toBe(5);
    expect(actions[0].type).toBe('overdue_obligation');
    expect(actions[1].type).toBe('unmatched_publication');
    expect(actions[2].type).toBe('pending_inbox');
    expect(actions[3].type).toBe('intake_request');
    expect(actions[4].type).toBe('due_soon_obligation');
  });

  it('returns empty array when no actions', () => {
    const actions = controlTowerApi.buildNextBestActions({
      overdueObligations: [],
      dueSoonObligations: [],
      pendingInboxCount: 0,
      unmatchedPublications: [],
      newIntakeRequests: 0,
      buildings: [],
    });
    expect(actions).toEqual([]);
  });
});
