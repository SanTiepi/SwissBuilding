import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/api/readiness', () => ({
  readinessApi: {
    list: vi.fn().mockResolvedValue({ items: [] }),
  },
}));

// Import after mocks
const { DossierJourney } = await import('../building-detail/DossierJourney');

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const baseBuilding = {
  id: 'b1',
  address: '10 Rue du Lac',
  postal_code: '1000',
  city: 'Lausanne',
  construction_year: 1985,
  egid: null,
  official_id: null,
  latitude: 46.5,
  longitude: 6.6,
  canton: 'VD',
  municipality: 'Lausanne',
  organization_id: 'org1',
  created_at: '2024-01-01',
  updated_at: '2024-01-01',
} as any;

const baseDashboard = {
  passport_grade: 'C',
  readiness: { overall_status: 'partially_ready' },
  trust_score: 0.7,
  completeness_score: 0.6,
} as any;

describe('DossierJourney', () => {
  it('renders null when dashboard is undefined', () => {
    const { container } = render(
      <DossierJourney
        buildingId="b1"
        building={baseBuilding}
        dashboard={undefined}
        completenessItems={[]}
        completenessPct={0}
        openActions={[]}
        diagnostics={[]}
      />,
      { wrapper },
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders all 4 sections with title', () => {
    render(
      <DossierJourney
        buildingId="b1"
        building={baseBuilding}
        dashboard={baseDashboard}
        completenessItems={[
          { key: 'diagnostic', done: true },
          { key: 'documents', done: false },
        ]}
        completenessPct={60}
        openActions={[]}
        diagnostics={[{ diagnostic_type: 'asbestos' }]}
      />,
      { wrapper },
    );

    // Main title
    expect(screen.getByText('Parcours du dossier')).toBeInTheDocument();

    // 4 section headers
    expect(screen.getByText('Etat du batiment')).toBeInTheDocument();
    expect(screen.getByText('Completude du dossier')).toBeInTheDocument();
    expect(screen.getByText('Verdict de readiness')).toBeInTheDocument();
    expect(screen.getByText('Prochaines actions')).toBeInTheDocument();
  });

  it('shows documented items with green checks and missing items', () => {
    render(
      <DossierJourney
        buildingId="b1"
        building={baseBuilding}
        dashboard={baseDashboard}
        completenessItems={[
          { key: 'diagnostic', done: true },
          { key: 'validated_diagnostic', done: true },
          { key: 'documents', done: false },
          { key: 'risk_score', done: false },
        ]}
        completenessPct={50}
        openActions={[]}
        diagnostics={[]}
      />,
      { wrapper },
    );

    // Documented items
    expect(screen.getByText('Diagnostic')).toBeInTheDocument();
    expect(screen.getByText('Diagnostic valide')).toBeInTheDocument();

    // Missing items
    expect(screen.getByText('Documents')).toBeInTheDocument();
    expect(screen.getByText('Score de risque')).toBeInTheDocument();
  });

  it('shows grade badge when passport_grade is provided', () => {
    render(
      <DossierJourney
        buildingId="b1"
        building={baseBuilding}
        dashboard={{ ...baseDashboard, passport_grade: 'A' }}
        completenessItems={[]}
        completenessPct={95}
        openActions={[]}
        diagnostics={[]}
      />,
      { wrapper },
    );

    expect(screen.getByText('A')).toBeInTheDocument();
  });

  it('shows "?" when no grade is available', () => {
    render(
      <DossierJourney
        buildingId="b1"
        building={baseBuilding}
        dashboard={{ ...baseDashboard, passport_grade: null }}
        completenessItems={[]}
        completenessPct={0}
        openActions={[]}
        diagnostics={[]}
      />,
      { wrapper },
    );

    expect(screen.getByText('?')).toBeInTheDocument();
  });

  it('shows "Aucune action bloquante" when no open actions', () => {
    render(
      <DossierJourney
        buildingId="b1"
        building={baseBuilding}
        dashboard={baseDashboard}
        completenessItems={[]}
        completenessPct={80}
        openActions={[]}
        diagnostics={[]}
      />,
      { wrapper },
    );

    expect(screen.getByText('Aucune action bloquante')).toBeInTheDocument();
  });

  it('shows open actions with priority badges', () => {
    const actions = [
      { id: 'a1', title: 'Fix diagnostic', priority: 'critical', source_type: 'diagnostic' },
      { id: 'a2', title: 'Upload report', priority: 'medium', source_type: 'document' },
    ] as any[];

    render(
      <DossierJourney
        buildingId="b1"
        building={baseBuilding}
        dashboard={baseDashboard}
        completenessItems={[]}
        completenessPct={40}
        openActions={actions}
        diagnostics={[]}
      />,
      { wrapper },
    );

    expect(screen.getByText('Fix diagnostic')).toBeInTheDocument();
    expect(screen.getByText('Upload report')).toBeInTheDocument();
    expect(screen.getByText('critical')).toBeInTheDocument();
    expect(screen.getByText('medium')).toBeInTheDocument();
  });

  it('shows "Tout est documente" when all items are done', () => {
    render(
      <DossierJourney
        buildingId="b1"
        building={baseBuilding}
        dashboard={baseDashboard}
        completenessItems={[
          { key: 'diagnostic', done: true },
          { key: 'documents', done: true },
        ]}
        completenessPct={100}
        openActions={[]}
        diagnostics={[]}
      />,
      { wrapper },
    );

    expect(screen.getByText('Tout est documente')).toBeInTheDocument();
  });

  it('shows building address and construction year', () => {
    render(
      <DossierJourney
        buildingId="b1"
        building={baseBuilding}
        dashboard={baseDashboard}
        completenessItems={[]}
        completenessPct={50}
        openActions={[]}
        diagnostics={[]}
      />,
      { wrapper },
    );

    expect(screen.getByText('10 Rue du Lac, 1000 Lausanne')).toBeInTheDocument();
    expect(screen.getByText(/Batiment de 1985/)).toBeInTheDocument();
  });
});
