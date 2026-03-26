import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import BuildingDetail from '@/pages/BuildingDetail';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'u1', role: 'admin' },
    token: 'tok',
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
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

const mockListDocuments = vi.fn();
vi.mock('@/api/documents', () => ({
  documentsApi: {
    listByBuilding: (...args: unknown[]) => mockListDocuments(...args),
    upload: vi.fn(),
    getDownloadUrl: vi.fn(),
  },
}));

const mockGetActivity = vi.fn();
vi.mock('@/api/buildings', () => ({
  buildingsApi: {
    getActivity: (...args: unknown[]) => mockGetActivity(...args),
  },
}));

const mockListActions = vi.fn();
vi.mock('@/api/actions', () => ({
  actionsApi: {
    listByBuilding: (...args: unknown[]) => mockListActions(...args),
  },
}));

const mockToast = vi.fn();
vi.mock('@/store/toastStore', () => ({
  toast: (...args: unknown[]) => mockToast(...args),
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

describe('BuildingDetail page', () => {
  beforeEach(() => {
    mockUseBuilding.mockReset();
    mockUseUpdateBuilding.mockReset();
    mockUseDeleteBuilding.mockReset();
    mockUseDiagnostics.mockReset();
    mockUseCreateDiagnostic.mockReset();
    mockUseBuildingRisk.mockReset();
    mockListDocuments.mockReset();
    mockGetActivity.mockReset();
    mockListActions.mockReset();
    mockToast.mockReset();

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
    mockListDocuments.mockResolvedValue([]);
    mockGetActivity.mockResolvedValue([]);
    mockListActions.mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when open actions fail to load', async () => {
    mockListActions.mockRejectedValue(new Error('boom'));

    renderPage();

    expect(await screen.findByText('app.error')).toBeInTheDocument();
  });

  it('renders explicit error state in the activity tab when activity fails to load', async () => {
    mockGetActivity.mockRejectedValue(new Error('boom'));

    renderPage();
    fireEvent.click(screen.getByRole('tab', { name: 'building.tab.activity' }));

    expect(await screen.findByText('app.error')).toBeInTheDocument();
  });

  it.skip('renders explicit error state in the documents tab when documents fail to load', async () => {
    mockListDocuments.mockRejectedValue(new Error('boom'));

    renderPage();
    await waitFor(() => expect(mockToast).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('tab', { name: /building\.tab\.documents/i }));

    expect(await screen.findByText('app.error')).toBeInTheDocument();
    expect(mockToast).toHaveBeenCalled();
  });
});
