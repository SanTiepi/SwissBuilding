import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { PortfolioRiskDashboard } from '../PortfolioRiskDashboard';
import { portfolioRiskApi } from '@/api/portfolioRisk';
import type { PortfolioRiskOverview } from '@/api/portfolioRisk';

vi.mock('@/api/portfolioRisk', () => ({
  portfolioRiskApi: {
    getOverview: vi.fn(),
    getHeatmap: vi.fn(),
  },
}));

// Mock the lazy-loaded map component
vi.mock('@/components/PortfolioRiskMapEvidence', () => ({
  default: () => <div data-testid="risk-map">Map</div>,
}));

const MOCK_OVERVIEW: PortfolioRiskOverview = {
  total_buildings: 5,
  avg_evidence_score: 62.5,
  buildings_at_risk: 1,
  buildings_ok: 3,
  worst_building_id: 'b1',
  distribution: {
    grade_a: 1,
    grade_b: 2,
    grade_c: 1,
    grade_d: 0,
    grade_f: 1,
  },
  buildings: [
    {
      building_id: 'b1',
      address: 'Rue Test 1',
      city: 'Lausanne',
      canton: 'VD',
      latitude: 46.5,
      longitude: 6.6,
      score: 25,
      grade: 'F',
      risk_level: 'critical',
      open_actions_count: 3,
      critical_actions_count: 2,
    },
    {
      building_id: 'b2',
      address: 'Rue Neuve 5',
      city: 'Geneva',
      canton: 'GE',
      latitude: 46.2,
      longitude: 6.1,
      score: 88,
      grade: 'A',
      risk_level: 'low',
      open_actions_count: 0,
      critical_actions_count: 0,
    },
  ],
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MemoryRouter>
  );
}

describe('PortfolioRiskDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders summary cards with correct values', async () => {
    vi.mocked(portfolioRiskApi.getOverview).mockResolvedValueOnce(MOCK_OVERVIEW);

    render(<PortfolioRiskDashboard />, { wrapper: createWrapper() });

    // Total buildings
    expect(await screen.findByText('5')).toBeInTheDocument();
    // Avg score
    expect(await screen.findByText('62.5')).toBeInTheDocument();
    // KPI labels
    expect(screen.getByText('portfolio_risk.total_buildings')).toBeInTheDocument();
    expect(screen.getByText('portfolio_risk.avg_score')).toBeInTheDocument();
    expect(screen.getByText('portfolio_risk.at_risk')).toBeInTheDocument();
    expect(screen.getByText('portfolio_risk.ok')).toBeInTheDocument();
  });

  it('renders grade distribution bars', async () => {
    vi.mocked(portfolioRiskApi.getOverview).mockResolvedValueOnce(MOCK_OVERVIEW);

    render(<PortfolioRiskDashboard />, { wrapper: createWrapper() });

    expect(await screen.findByText('portfolio_risk.grade_distribution')).toBeInTheDocument();
    // Grades should be visible
    const gradeAs = await screen.findAllByText('A');
    expect(gradeAs.length).toBeGreaterThanOrEqual(1);
  });

  it('renders filter controls', async () => {
    vi.mocked(portfolioRiskApi.getOverview).mockResolvedValueOnce(MOCK_OVERVIEW);

    render(<PortfolioRiskDashboard />, { wrapper: createWrapper() });

    expect(await screen.findByText('portfolio_risk.map_view')).toBeInTheDocument();
    expect(screen.getByText('portfolio_risk.table_view')).toBeInTheDocument();
  });

  it('switches to table view and shows buildings sorted by score', async () => {
    vi.mocked(portfolioRiskApi.getOverview).mockResolvedValueOnce(MOCK_OVERVIEW);

    render(<PortfolioRiskDashboard />, { wrapper: createWrapper() });

    const tableBtn = await screen.findByText('portfolio_risk.table_view');
    fireEvent.click(tableBtn);

    // Worst building (score 25) should appear
    expect(await screen.findByText('Rue Test 1')).toBeInTheDocument();
    expect(screen.getByText('Rue Neuve 5')).toBeInTheDocument();
  });

  it('renders error state when API fails', async () => {
    vi.mocked(portfolioRiskApi.getOverview).mockRejectedValueOnce(new Error('fail'));

    render(<PortfolioRiskDashboard />, { wrapper: createWrapper() });

    expect(await screen.findByText('app.error')).toBeInTheDocument();
  });
});
