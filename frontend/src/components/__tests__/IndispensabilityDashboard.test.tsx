import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}));

const mockUser = { organization_id: 'org-1', role: 'admin' };
vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: { user: typeof mockUser }) => unknown) => selector({ user: mockUser })),
}));

const mockGetPortfolioIndispensability = vi.fn();
const mockGetValueLedger = vi.fn();
const mockGetValueEvents = vi.fn();
vi.mock('@/api/intelligence', () => ({
  intelligenceApi: {
    getPortfolioIndispensability: (...args: unknown[]) => mockGetPortfolioIndispensability(...args),
    getValueLedger: (...args: unknown[]) => mockGetValueLedger(...args),
    getValueEvents: (...args: unknown[]) => mockGetValueEvents(...args),
  },
}));

import IndispensabilityDashboard from '@/pages/IndispensabilityDashboard';

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('IndispensabilityDashboard', () => {
  it('shows KPI summary cards when data loads', async () => {
    mockGetPortfolioIndispensability.mockResolvedValue({
      org_id: 'org-1',
      buildings_count: 20,
      avg_fragmentation_score: 55,
      avg_defensibility_score: 0.72,
      total_contradictions_resolved: 34,
      total_proof_chains: 89,
      total_cost_of_fragmentation_hours: 210,
      worst_buildings: [],
    });
    mockGetValueLedger.mockResolvedValue(null);
    mockGetValueEvents.mockResolvedValue([]);
    wrap(<IndispensabilityDashboard />);

    const kpis = await screen.findByTestId('portfolio-kpis');
    expect(kpis).toBeInTheDocument();
    // Check that KPI cards are rendered (5 total)
    const cards = screen.getAllByTestId('indispensability-kpi');
    expect(cards.length).toBe(5);
  });

  it('shows worst buildings list', async () => {
    mockGetPortfolioIndispensability.mockResolvedValue({
      org_id: 'org-1',
      buildings_count: 20,
      avg_fragmentation_score: 55,
      avg_defensibility_score: 0.72,
      total_contradictions_resolved: 34,
      total_proof_chains: 89,
      total_cost_of_fragmentation_hours: 210,
      worst_buildings: [
        { building_id: 'b-1', address: 'Rue du Midi 15', fragmentation_score: 85 },
        { building_id: 'b-2', address: 'Avenue de la Gare 3', fragmentation_score: 72 },
      ],
    });
    mockGetValueLedger.mockResolvedValue(null);
    mockGetValueEvents.mockResolvedValue([]);
    wrap(<IndispensabilityDashboard />);

    const worstSection = await screen.findByTestId('worst-buildings');
    expect(worstSection).toBeInTheDocument();
    const rows = screen.getAllByTestId('worst-building-row');
    expect(rows.length).toBe(2);
    expect(rows[0]).toHaveTextContent('Rue du Midi 15');
    expect(rows[0]).toHaveTextContent('85%');
  });
});
