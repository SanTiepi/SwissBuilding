import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockScanPortfolio = vi.fn();
const mockGenerateActions = vi.fn();
vi.mock('@/api/predictiveReadiness', () => ({
  predictiveReadinessApi: {
    scanPortfolio: (...args: unknown[]) => mockScanPortfolio(...args),
    generateActions: (...args: unknown[]) => mockGenerateActions(...args),
    scanBuilding: vi.fn(),
  },
}));

// Import after mocks
const { PredictiveAlertsPortfolio } = await import('../PredictiveAlerts');

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

const emptyResult = {
  alerts: [],
  summary: { critical: 0, warning: 0, info: 0, buildings_at_risk: 0, diagnostics_expiring_90d: 0 },
  projections: [],
};

const populatedResult = {
  alerts: [
    {
      id: 'al1',
      severity: 'critical' as const,
      building_id: 'b1',
      building_name: 'Batiment A',
      alert_type: 'diagnostic_expiring' as const,
      title: 'Diagnostic amiante expire',
      description: 'Le diagnostic expire dans 15 jours',
      deadline: '2026-04-15',
      days_remaining: 15,
      recommended_action: 'Renouveler le diagnostic',
      estimated_lead_time_days: 10,
    },
    {
      id: 'al2',
      severity: 'warning' as const,
      building_id: 'b2',
      building_name: 'Batiment B',
      alert_type: 'readiness_degradation' as const,
      title: 'Readiness en baisse',
      description: 'Score projetee en baisse a 90 jours',
      deadline: null,
      days_remaining: 90,
      recommended_action: 'Completer le dossier',
      estimated_lead_time_days: null,
    },
    {
      id: 'al3',
      severity: 'info' as const,
      building_id: 'b3',
      building_name: 'Batiment C',
      alert_type: 'obligation_due' as const,
      title: 'Obligation a venir',
      description: 'Controle periodique requis',
      deadline: '2026-09-01',
      days_remaining: 150,
      recommended_action: 'Planifier le controle',
      estimated_lead_time_days: 30,
    },
  ],
  summary: { critical: 1, warning: 1, info: 1, buildings_at_risk: 2, diagnostics_expiring_90d: 1 },
  projections: [],
};

describe('PredictiveAlertsPortfolio', () => {
  beforeEach(() => {
    mockScanPortfolio.mockReset();
    mockGenerateActions.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('shows "no alerts" message when empty', async () => {
    mockScanPortfolio.mockResolvedValue(emptyResult);
    render(<PredictiveAlertsPortfolio />, { wrapper });

    expect(await screen.findByText('predictive.no_alerts')).toBeInTheDocument();
  });

  it('renders alert cards with titles', async () => {
    mockScanPortfolio.mockResolvedValue(populatedResult);
    render(<PredictiveAlertsPortfolio />, { wrapper });

    expect(await screen.findByText('Diagnostic amiante expire')).toBeInTheDocument();
    expect(screen.getByText('Readiness en baisse')).toBeInTheDocument();
    expect(screen.getByText('Obligation a venir')).toBeInTheDocument();
  });

  it('shows severity summary counts', async () => {
    mockScanPortfolio.mockResolvedValue(populatedResult);
    render(<PredictiveAlertsPortfolio />, { wrapper });

    await screen.findByText('Diagnostic amiante expire');
    expect(screen.getByText('critiques')).toBeInTheDocument();
    expect(screen.getByText('avertissements')).toBeInTheDocument();
    expect(screen.getByText('infos')).toBeInTheDocument();
  });

  it('shows recommended actions on alert cards', async () => {
    mockScanPortfolio.mockResolvedValue(populatedResult);
    render(<PredictiveAlertsPortfolio />, { wrapper });

    await screen.findByText('Diagnostic amiante expire');
    expect(screen.getByText('Renouveler le diagnostic')).toBeInTheDocument();
    expect(screen.getByText('Completer le dossier')).toBeInTheDocument();
  });

  it('shows days remaining badge', async () => {
    mockScanPortfolio.mockResolvedValue(populatedResult);
    render(<PredictiveAlertsPortfolio />, { wrapper });

    await screen.findByText('Diagnostic amiante expire');
    expect(screen.getByText('15j')).toBeInTheDocument();
  });

  it('renders null when API fails', async () => {
    mockScanPortfolio.mockRejectedValue(new Error('boom'));
    const { container } = render(<PredictiveAlertsPortfolio />, { wrapper });

    // Wait for loading to finish, then check it renders nothing
    await vi.waitFor(() => {
      expect(container.querySelector('.animate-pulse')).toBeNull();
    });
    // isError returns null
    expect(container.firstChild).toBeNull();
  });
});
