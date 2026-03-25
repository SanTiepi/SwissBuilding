import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { demoPilotApi } from '@/api/demoPilot';
import PilotDashboard from '@/pages/PilotDashboard';

vi.mock('@/api/demoPilot', () => ({
  demoPilotApi: {
    listPilots: vi.fn().mockResolvedValue([
      {
        id: 'p-1',
        pilot_name: 'VD Gerance Alpha',
        pilot_code: 'vd-alpha',
        status: 'active',
        start_date: '2026-01-01',
        end_date: '2026-06-30',
        target_buildings: 10,
        target_users: 5,
        exit_state: null,
        exit_notes: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
      {
        id: 'p-2',
        pilot_name: 'GE Pilot Beta',
        pilot_code: 'ge-beta',
        status: 'completed',
        start_date: '2025-07-01',
        end_date: '2025-12-31',
        target_buildings: 20,
        target_users: 8,
        exit_state: 'scale',
        exit_notes: null,
        created_at: '2025-07-01T00:00:00Z',
        updated_at: '2025-12-31T00:00:00Z',
      },
    ]),
    getScorecard: vi.fn().mockResolvedValue({
      id: 'p-1',
      pilot_name: 'VD Gerance Alpha',
      pilot_code: 'vd-alpha',
      status: 'active',
      start_date: '2026-01-01',
      end_date: '2026-06-30',
      target_buildings: 10,
      target_users: 5,
      exit_state: null,
      exit_notes: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      metrics: [
        {
          id: 'm-1',
          scorecard_id: 'p-1',
          dimension: 'completeness',
          target_value: 95,
          current_value: 82,
          evidence_source: 'completeness_engine',
          notes: null,
          measured_at: '2026-03-01T00:00:00Z',
          created_at: '2026-03-01T00:00:00Z',
        },
        {
          id: 'm-2',
          scorecard_id: 'p-1',
          dimension: 'rework_reduction',
          target_value: 50,
          current_value: 55,
          evidence_source: 'roi_calculator',
          notes: null,
          measured_at: '2026-03-01T00:00:00Z',
          created_at: '2026-03-01T00:00:00Z',
        },
      ],
    }),
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
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

describe('PilotDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    render(<PilotDashboard />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('pilot_dashboard.title')).toBeInTheDocument();
    });
  });

  it('renders pilot list with names', async () => {
    render(<PilotDashboard />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('VD Gerance Alpha')).toBeInTheDocument();
      expect(screen.getByText('GE Pilot Beta')).toBeInTheDocument();
    });
  });

  it('renders pilot status badges', async () => {
    render(<PilotDashboard />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('active')).toBeInTheDocument();
      expect(screen.getByText('completed')).toBeInTheDocument();
    });
  });

  it('expands pilot to show metrics with progress bars', async () => {
    render(<PilotDashboard />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('pilot-vd-alpha')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('pilot-vd-alpha'));

    await waitFor(() => {
      expect(screen.getByText('completeness')).toBeInTheDocument();
      expect(screen.getByText('rework_reduction')).toBeInTheDocument();
    });
  });

  it('shows target vs current values', async () => {
    render(<PilotDashboard />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('pilot-vd-alpha')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('pilot-vd-alpha'));

    await waitFor(() => {
      expect(screen.getByText('82 / 95')).toBeInTheDocument();
      expect(screen.getByText('55 / 50')).toBeInTheDocument();
    });
  });

  it('shows exit recommendation', async () => {
    render(<PilotDashboard />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('pilot-vd-alpha')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('pilot-vd-alpha'));

    await waitFor(() => {
      expect(screen.getByTestId('exit-recommendation')).toBeInTheDocument();
    });
  });

  it('renders empty state when no pilots', async () => {
    vi.mocked(demoPilotApi.listPilots).mockResolvedValueOnce([]);
    render(<PilotDashboard />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('pilot_dashboard.empty')).toBeInTheDocument();
    });
  });
});
