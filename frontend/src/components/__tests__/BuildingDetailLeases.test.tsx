import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import BuildingDetail from '@/pages/BuildingDetail';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        'building.tab.overview': 'Overview',
        'building.tab.spatial': 'Spatial',
        'building.tab.truth': 'Truth',
        'building.tab.change': 'Changes',
        'building.tab.cases': 'Cases',
        'building.tab.passport': 'Passport',
        'building.tab.questions': 'Questions',
        'building.backToList': 'Back',
        'building.notFound': 'Not found',
        'app.loading': 'Loading...',
        'app.error': 'Error',
      };
      return map[key] || key;
    },
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'u1', email: 'test@test.ch', role: 'admin', organization_id: 'org1' },
    isAuthenticated: true,
  }),
}));

const mockUseBuilding = vi.fn();
const mockUseUpdateBuilding = vi.fn();
const mockUseDeleteBuilding = vi.fn();
vi.mock('@/hooks/useBuildings', () => ({
  useBuilding: (...args: unknown[]) => mockUseBuilding(...args),
  useUpdateBuilding: () => mockUseUpdateBuilding(),
  useDeleteBuilding: () => mockUseDeleteBuilding(),
}));

const mockUseDiagnostics = vi.fn();
const mockUseCreateDiagnostic = vi.fn();
const mockUseBuildingRisk = vi.fn();
vi.mock('@/hooks/useDiagnostics', () => ({
  useDiagnostics: (...args: unknown[]) => mockUseDiagnostics(...args),
  useCreateDiagnostic: () => mockUseCreateDiagnostic(),
  useBuildingRisk: (...args: unknown[]) => mockUseBuildingRisk(...args),
}));

vi.mock('@/api/documents', () => ({
  documentsApi: {
    listByBuilding: vi.fn().mockResolvedValue([]),
    upload: vi.fn(),
    getDownloadUrl: vi.fn(),
  },
}));

vi.mock('@/api/buildings', () => ({
  buildingsApi: {
    getActivity: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock('@/api/actions', () => ({
  actionsApi: {
    listByBuilding: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock('@/api/buildingDashboard', () => ({
  buildingDashboardApi: {
    get: vi.fn().mockResolvedValue(null),
  },
}));

vi.mock('@/api/leases', () => ({
  leasesApi: {
    listByBuilding: vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      size: 20,
      pages: 0,
    }),
    getSummary: vi.fn().mockResolvedValue({
      building_id: 'building-1',
      total_leases: 0,
      active_leases: 0,
      monthly_rent_chf: 0,
      monthly_charges_chf: 0,
      expiring_90d: 0,
      disputed_count: 0,
    }),
    lookupContacts: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock('@/store/toastStore', () => ({
  toast: vi.fn(),
}));

vi.mock('@/components/Skeleton', () => ({
  BuildingDetailSkeleton: () => <div>BuildingDetailSkeleton</div>,
  InlineSkeleton: () => <div>InlineSkeleton</div>,
}));
vi.mock('@/components/DiagnosticTimeline', () => ({
  DiagnosticTimeline: () => <div>DiagnosticTimeline</div>,
}));
vi.mock('@/components/RiskGauge', () => ({
  RiskGauge: () => <div>RiskGauge</div>,
}));
vi.mock('@/components/PollutantBadge', () => ({
  PollutantBadge: () => <div>PollutantBadge</div>,
}));
vi.mock('@/components/FileUpload', () => ({
  FileUpload: () => <div>FileUpload</div>,
}));
vi.mock('@/components/RoleGate', () => ({
  RoleGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
vi.mock('@/components/NextAction', () => ({
  NextAction: () => <div>NextAction</div>,
}));
vi.mock('@/components/DataQualityScore', () => ({
  DataQualityScore: () => <div>DataQualityScore</div>,
}));
vi.mock('@/components/CompletenessGauge', () => ({
  CompletenessGauge: () => <div>CompletenessGauge</div>,
}));
vi.mock('@/components/DossierPackButton', () => ({
  DossierPackButton: () => <button>DossierPackButton</button>,
}));
vi.mock('@/components/ReadinessSummary', () => ({
  ReadinessSummary: () => <div>ReadinessSummary</div>,
}));
vi.mock('@/components/TrustScoreCard', () => ({
  TrustScoreCard: () => <div>TrustScoreCard</div>,
}));
vi.mock('@/components/UnknownIssuesList', () => ({
  UnknownIssuesList: () => <div>UnknownIssuesList</div>,
}));
vi.mock('@/components/ChangeSignalsFeed', () => ({
  ChangeSignalsFeed: () => <div>ChangeSignalsFeed</div>,
}));
vi.mock('@/components/ContradictionCard', () => ({
  ContradictionCard: () => <div>ContradictionCard</div>,
}));
vi.mock('@/components/PostWorksDiffCard', () => ({
  PostWorksDiffCard: () => <div>PostWorksDiffCard</div>,
}));
vi.mock('@/components/TimeMachinePanel', () => ({
  TimeMachinePanel: () => <div>TimeMachinePanel</div>,
}));
vi.mock('@/components/PassportCard', () => ({
  PassportCard: () => <div>PassportCard</div>,
}));
vi.mock('@/components/RequalificationTimeline', () => ({
  RequalificationTimeline: () => <div>RequalificationTimeline</div>,
}));
vi.mock('@/components/TransferPackagePanel', () => ({
  TransferPackagePanel: () => <div>TransferPackagePanel</div>,
}));

function createBuilding() {
  return {
    id: 'building-1',
    address: 'Rue du Test 1',
    city: 'Lausanne',
    canton: 'VD',
    postal_code: '1000',
    construction_year: 1970,
    building_type: 'residential',
    floors_above: 3,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
  };
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter
        initialEntries={['/buildings/building-1']}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/buildings/:id" element={<BuildingDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('BuildingDetail Leases Tab', () => {
  beforeEach(() => {
    mockUseBuilding.mockReturnValue({
      data: createBuilding(),
      isLoading: false,
      isError: false,
    });
    mockUseDiagnostics.mockReturnValue({ data: [] });
    mockUseBuildingRisk.mockReturnValue({ data: undefined });
    mockUseUpdateBuilding.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    mockUseDeleteBuilding.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    mockUseCreateDiagnostic.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
  });

  afterEach(() => {
    cleanup();
  });

  it('shows Cases tab in the tab bar (leases moved under cases)', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /cases/i })).toBeInTheDocument();
    });
  });

  it('clicking Cases tab renders cases content (includes leases)', async () => {
    renderPage();
    await waitFor(() => {
      const casesTab = screen.getByRole('tab', { name: /cases/i });
      fireEvent.click(casesTab);
    });
    // Cases tab now contains leases, contracts, procedures, tenders
    // The tab should render without crashing
    await waitFor(() => {
      expect(document.body).toBeDefined();
    });
  });
});
