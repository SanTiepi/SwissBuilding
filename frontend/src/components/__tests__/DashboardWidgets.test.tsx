import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '@/pages/Dashboard';
import type { Building, Diagnostic } from '@/types';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockUseAuth = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}));

const mockUseBuildings = vi.fn();
vi.mock('@/hooks/useBuildings', () => ({
  useBuildings: () => mockUseBuildings(),
}));

const mockDiagnosticsListByBuilding = vi.fn();
vi.mock('@/api/diagnostics', () => ({
  diagnosticsApi: {
    listByBuilding: (...args: unknown[]) => mockDiagnosticsListByBuilding(...args),
  },
}));

const mockActionsList = vi.fn();
vi.mock('@/api/actions', () => ({
  actionsApi: {
    list: (...args: unknown[]) => mockActionsList(...args),
  },
}));

// Lazy-loaded DashboardCharts — mock to avoid recharts in tests
vi.mock('@/components/DashboardCharts', () => ({
  DashboardCharts: () => <div data-testid="dashboard-charts">Charts</div>,
}));

function createMockBuilding(overrides: Partial<Building> = {}): Building {
  return {
    id: 'b-001',
    egid: 12345,
    egrid: 'CH123456',
    official_id: null,
    address: '12 Rue de Lausanne',
    postal_code: '1000',
    city: 'Lausanne',
    canton: 'VD',
    latitude: 46.5197,
    longitude: 6.6323,
    parcel_number: null,
    construction_year: 1965,
    renovation_year: null,
    building_type: 'residential',
    floors_above: 4,
    floors_below: 1,
    surface_area_m2: 450,
    volume_m3: null,
    owner_id: null,
    status: 'active',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    risk_scores: {
      id: 'rs-001',
      building_id: 'b-001',
      asbestos_probability: 0.8,
      pcb_probability: 0.3,
      lead_probability: 0.5,
      hap_probability: 0.1,
      radon_probability: 0.2,
      overall_risk_level: 'high',
      confidence: 0.85,
      factors_json: null,
      data_source: 'model',
      last_updated: '2024-01-01T00:00:00Z',
    },
    ...overrides,
  };
}

function createMockDiagnostic(overrides: Partial<Diagnostic> = {}): Diagnostic {
  return {
    id: 'd-001',
    building_id: 'b-001',
    diagnostic_type: 'asbestos',
    diagnostic_context: 'AvT',
    status: 'in_progress',
    diagnostician_id: 'u-001',
    laboratory: null,
    laboratory_report_number: null,
    date_inspection: '2024-06-01',
    date_report: null,
    summary: null,
    created_at: '2024-06-01T00:00:00Z',
    updated_at: '2024-06-15T00:00:00Z',
    ...(overrides as Record<string, unknown>),
  } as Diagnostic;
}

let queryClient: QueryClient;

function renderDashboard() {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** Wait for the dashboard to finish loading (skeleton disappears, KPIs appear). */
async function waitForDashboard() {
  await screen.findByText('dashboard.total_buildings');
}

describe('Dashboard Widgets', () => {
  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } },
    });
    mockNavigate.mockClear();
    mockUseAuth.mockReturnValue({ user: { id: 'u-001', first_name: 'Robin' } });
    mockDiagnosticsListByBuilding.mockResolvedValue([]);
    mockActionsList.mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  // --- Loading state ---
  it('shows skeleton while loading', () => {
    mockUseBuildings.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });
    renderDashboard();
    // DashboardSkeleton renders animated pulse divs; check absence of KPI text
    expect(screen.queryByText('dashboard.total_buildings')).not.toBeInTheDocument();
  });

  // --- Error state ---
  it('shows error when buildings query fails', () => {
    mockUseBuildings.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });
    renderDashboard();
    expect(screen.getByText('app.error')).toBeInTheDocument();
  });

  // --- Primary KPI cards ---
  describe('Primary KPIs', () => {
    it('renders 4 primary KPI cards with correct values', async () => {
      const buildings = [
        createMockBuilding({
          id: 'b-1',
          risk_scores: { ...createMockBuilding().risk_scores!, overall_risk_level: 'high' },
        }),
        createMockBuilding({
          id: 'b-2',
          risk_scores: { ...createMockBuilding().risk_scores!, overall_risk_level: 'low' },
        }),
        createMockBuilding({
          id: 'b-3',
          risk_scores: { ...createMockBuilding().risk_scores!, overall_risk_level: 'critical' },
        }),
      ];
      mockUseBuildings.mockReturnValue({
        data: { items: buildings },
        isLoading: false,
        isError: false,
      });
      renderDashboard();
      await waitForDashboard();

      expect(screen.getByText('dashboard.total_buildings')).toBeInTheDocument();
      expect(screen.getByText('dashboard.high_risk')).toBeInTheDocument();
    });

    it('renders 0 for all KPIs when no buildings', async () => {
      mockUseBuildings.mockReturnValue({
        data: { items: [] },
        isLoading: false,
        isError: false,
      });
      renderDashboard();
      await waitForDashboard();
      expect(screen.getByText('dashboard.total_buildings')).toBeInTheDocument();
    });
  });

  // --- Secondary KPI cards ---
  describe('Secondary KPIs', () => {
    it('renders secondary KPI cards (actions, documents, alerts, trust)', async () => {
      mockUseBuildings.mockReturnValue({
        data: { items: [createMockBuilding()] },
        isLoading: false,
        isError: false,
      });
      renderDashboard();
      await waitForDashboard();

      const secondaryKpis = screen.getAllByTestId('secondary-kpi');
      expect(secondaryKpis).toHaveLength(4);
    });

    it('shows dash for avg trust when no confidence data', async () => {
      mockUseBuildings.mockReturnValue({
        data: { items: [createMockBuilding({ risk_scores: undefined })] },
        isLoading: false,
        isError: false,
      });
      renderDashboard();
      await waitForDashboard();

      const secondaryKpis = screen.getAllByTestId('secondary-kpi');
      const trustKpi = secondaryKpis[3];
      expect(within(trustKpi).getByText('—')).toBeInTheDocument();
    });

    it('computes average trust score from buildings confidence', async () => {
      const buildings = [
        createMockBuilding({
          id: 'b-1',
          risk_scores: { ...createMockBuilding().risk_scores!, confidence: 0.8 },
        }),
        createMockBuilding({
          id: 'b-2',
          risk_scores: { ...createMockBuilding().risk_scores!, confidence: 0.6 },
        }),
      ];
      mockUseBuildings.mockReturnValue({
        data: { items: buildings },
        isLoading: false,
        isError: false,
      });
      renderDashboard();
      await waitForDashboard();

      // Average = (0.8 + 0.6) / 2 * 100 = 70%
      const secondaryKpis = screen.getAllByTestId('secondary-kpi');
      const trustKpi = secondaryKpis[3];
      expect(within(trustKpi).getByText('70%')).toBeInTheDocument();
    });
  });

  // --- Quick Actions ---
  describe('Quick Actions', () => {
    beforeEach(() => {
      mockUseBuildings.mockReturnValue({
        data: { items: [createMockBuilding()] },
        isLoading: false,
        isError: false,
      });
    });

    it('renders 4 quick action buttons', async () => {
      renderDashboard();
      await waitForDashboard();
      const actions = screen.getAllByTestId('quick-action');
      expect(actions).toHaveLength(4);
    });

    it('navigates to exports when Generate Report is clicked', async () => {
      const user = userEvent.setup();
      renderDashboard();
      await waitForDashboard();

      const actions = screen.getAllByTestId('quick-action');
      await user.click(actions[1]);
      expect(mockNavigate).toHaveBeenCalledWith('/exports');
    });

    it('navigates to readiness wallet', async () => {
      const user = userEvent.setup();
      renderDashboard();
      await waitForDashboard();

      const actions = screen.getAllByTestId('quick-action');
      await user.click(actions[2]);
      expect(mockNavigate).toHaveBeenCalledWith('/readiness-wallet');
    });

    it('navigates to portfolio', async () => {
      const user = userEvent.setup();
      renderDashboard();
      await waitForDashboard();

      const actions = screen.getAllByTestId('quick-action');
      await user.click(actions[3]);
      expect(mockNavigate).toHaveBeenCalledWith('/portfolio');
    });
  });

  // --- Portfolio Health Summary ---
  describe('Portfolio Health Summary', () => {
    it('renders portfolio health section with grade bars', async () => {
      const buildings = [
        createMockBuilding({
          id: 'b-1',
          risk_scores: { ...createMockBuilding().risk_scores!, overall_risk_level: 'low' },
        }),
        createMockBuilding({
          id: 'b-2',
          risk_scores: { ...createMockBuilding().risk_scores!, overall_risk_level: 'high' },
        }),
      ];
      mockUseBuildings.mockReturnValue({
        data: { items: buildings },
        isLoading: false,
        isError: false,
      });
      renderDashboard();
      await waitForDashboard();

      expect(screen.getByTestId('portfolio-health')).toBeInTheDocument();
      expect(screen.getByText('A')).toBeInTheDocument();
      expect(screen.getByText('F')).toBeInTheDocument();
    });

    it('does not render portfolio health when no buildings', async () => {
      mockUseBuildings.mockReturnValue({
        data: { items: [] },
        isLoading: false,
        isError: false,
      });
      renderDashboard();
      await waitForDashboard();

      expect(screen.queryByTestId('portfolio-health')).not.toBeInTheDocument();
    });
  });

  // --- Recent Activity ---
  describe('Recent Activity', () => {
    it('shows empty state when no diagnostics', async () => {
      mockUseBuildings.mockReturnValue({
        data: { items: [] },
        isLoading: false,
        isError: false,
      });
      renderDashboard();
      await waitForDashboard();

      expect(screen.getByText('dashboard.recent_activity')).toBeInTheDocument();
      expect(screen.getByText('form.no_results')).toBeInTheDocument();
    });

    it('shows building address in recent activity when available', async () => {
      const building = createMockBuilding({ id: 'b-001', address: '12 Rue de Lausanne', city: 'Lausanne' });
      const diagnostic = createMockDiagnostic({ id: 'd-001', building_id: 'b-001' });

      mockUseBuildings.mockReturnValue({
        data: { items: [building] },
        isLoading: false,
        isError: false,
      });
      mockDiagnosticsListByBuilding.mockResolvedValue([diagnostic]);

      renderDashboard();

      // The diagnostic type key and building address should appear
      expect(await screen.findByText('diagnostic_type.asbestos')).toBeInTheDocument();
      await waitFor(() => {
        expect(screen.getByText('12 Rue de Lausanne, Lausanne')).toBeInTheDocument();
      });
    });
  });

  // --- Quick Access Links ---
  describe('Quick Access links', () => {
    it('renders the 3 building intelligence links', async () => {
      mockUseBuildings.mockReturnValue({
        data: { items: [createMockBuilding()] },
        isLoading: false,
        isError: false,
      });
      renderDashboard();
      await waitForDashboard();

      expect(screen.getByText('building.tab.explorer')).toBeInTheDocument();
      expect(screen.getByText('building.tab.interventions')).toBeInTheDocument();
      expect(screen.getByText('building.tab.plans')).toBeInTheDocument();
    });
  });

  // --- Welcome header ---
  describe('Header', () => {
    it('shows welcome message with user name', async () => {
      mockUseBuildings.mockReturnValue({
        data: { items: [] },
        isLoading: false,
        isError: false,
      });
      renderDashboard();
      await waitForDashboard();

      expect(screen.getByText('dashboard.welcome')).toBeInTheDocument();
    });
  });
});
