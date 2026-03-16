import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import BuildingComparisonPage from '@/pages/BuildingComparison';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockList = vi.fn();
vi.mock('@/api/buildings', () => ({
  buildingsApi: {
    list: (...args: unknown[]) => mockList(...args),
  },
}));

const mockCompare = vi.fn();
vi.mock('@/api/buildingComparison', () => ({
  buildingComparisonApi: {
    compare: (...args: unknown[]) => mockCompare(...args),
  },
}));

const MOCK_BUILDINGS = [
  { id: 'b1', address: 'Rue du Marche 12', postal_code: '1003' },
  { id: 'b2', address: 'Quai du Mont-Blanc 5', postal_code: '1201' },
  { id: 'b3', address: 'Zone Industrielle 8', postal_code: '1400' },
];

const MOCK_COMPARISON = {
  buildings: [
    {
      building_id: 'b1',
      building_name: 'Immeuble Lausanne',
      address: 'Rue du Marche 12',
      passport_grade: 'B',
      passport_score: 0.78,
      trust_score: 0.85,
      completeness_score: 0.9,
      readiness_summary: { safe_to_start: true, safe_to_tender: true, safe_to_reopen: false, safe_to_requalify: false },
      open_actions_count: 3,
      open_unknowns_count: 1,
      contradictions_count: 0,
      diagnostic_count: 4,
      last_diagnostic_date: '2026-02-15T10:00:00Z',
    },
    {
      building_id: 'b2',
      building_name: 'Residence Geneve',
      address: 'Quai du Mont-Blanc 5',
      passport_grade: 'C',
      passport_score: 0.55,
      trust_score: 0.62,
      completeness_score: 0.7,
      readiness_summary: {
        safe_to_start: false,
        safe_to_tender: true,
        safe_to_reopen: false,
        safe_to_requalify: false,
      },
      open_actions_count: 7,
      open_unknowns_count: 4,
      contradictions_count: 2,
      diagnostic_count: 2,
      last_diagnostic_date: '2025-11-20T10:00:00Z',
    },
    {
      building_id: 'b3',
      building_name: 'Batiment Yverdon',
      address: 'Zone Industrielle 8',
      passport_grade: 'A',
      passport_score: 0.92,
      trust_score: 0.95,
      completeness_score: 0.98,
      readiness_summary: {
        safe_to_start: true,
        safe_to_tender: true,
        safe_to_reopen: true,
        safe_to_requalify: true,
      },
      open_actions_count: 0,
      open_unknowns_count: 0,
      contradictions_count: 0,
      diagnostic_count: 6,
      last_diagnostic_date: '2026-03-01T10:00:00Z',
    },
  ],
  comparison_dimensions: ['passport_grade', 'trust_score', 'completeness_score'],
  best_passport: 'Batiment Yverdon',
  worst_passport: 'Residence Geneve',
  average_trust: 0.807,
  average_completeness: 0.86,
};

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('BuildingComparisonPage', () => {
  beforeEach(() => {
    mockList.mockReset();
    mockCompare.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when buildings fail to load', async () => {
    mockList.mockRejectedValue(new Error('boom'));
    render(<BuildingComparisonPage />, { wrapper });

    expect(await screen.findByText('app.error')).toBeInTheDocument();
  });

  it('renders explicit empty state when no buildings are available', async () => {
    mockList.mockResolvedValue({ items: [] });
    render(<BuildingComparisonPage />, { wrapper });

    expect(await screen.findByText('form.no_results')).toBeInTheDocument();
  });

  describe('mobile card layout', () => {
    it('renders mobile comparison cards container when results are present', async () => {
      mockList.mockResolvedValue({ items: MOCK_BUILDINGS });
      mockCompare.mockResolvedValue(MOCK_COMPARISON);

      render(<BuildingComparisonPage />, { wrapper });

      // Wait for buildings to load, select 2, and compare
      await screen.findByText('Rue du Marche 12');

      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);
      fireEvent.click(checkboxes[1]);

      const compareBtn = screen.getByText('comparison.compare_button');
      fireEvent.click(compareBtn);

      await waitFor(() => {
        expect(screen.getByTestId('comparison-mobile-cards')).toBeInTheDocument();
      });
    });

    it('renders one mobile card per building in comparison results', async () => {
      mockList.mockResolvedValue({ items: MOCK_BUILDINGS });
      mockCompare.mockResolvedValue(MOCK_COMPARISON);

      render(<BuildingComparisonPage />, { wrapper });

      await screen.findByText('Rue du Marche 12');

      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);
      fireEvent.click(checkboxes[1]);
      fireEvent.click(checkboxes[2]);

      fireEvent.click(screen.getByText('comparison.compare_button'));

      await waitFor(() => {
        const cards = screen.getAllByTestId('comparison-mobile-card');
        expect(cards).toHaveLength(3);
      });
    });

    it('displays building name and address on mobile cards', async () => {
      mockList.mockResolvedValue({ items: MOCK_BUILDINGS });
      mockCompare.mockResolvedValue(MOCK_COMPARISON);

      render(<BuildingComparisonPage />, { wrapper });

      await screen.findByText('Rue du Marche 12');

      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);
      fireEvent.click(checkboxes[1]);

      fireEvent.click(screen.getByText('comparison.compare_button'));

      await waitFor(() => {
        // Names appear in both desktop table and mobile cards (JSDOM does not hide via CSS)
        const lausanneEls = screen.getAllByText('Immeuble Lausanne');
        expect(lausanneEls.length).toBeGreaterThanOrEqual(2); // table header + mobile card
        const geneveEls = screen.getAllByText('Residence Geneve');
        expect(geneveEls.length).toBeGreaterThanOrEqual(2);
      });
    });

    it('shows dimension labels on each mobile card', async () => {
      mockList.mockResolvedValue({ items: MOCK_BUILDINGS });
      mockCompare.mockResolvedValue(MOCK_COMPARISON);

      render(<BuildingComparisonPage />, { wrapper });

      await screen.findByText('Rue du Marche 12');

      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);
      fireEvent.click(checkboxes[1]);

      fireEvent.click(screen.getByText('comparison.compare_button'));

      await waitFor(() => {
        // Each card should show dimension labels — there are 2 cards so labels appear twice
        const gradeLabels = screen.getAllByText('comparison.passport_grade');
        expect(gradeLabels.length).toBeGreaterThanOrEqual(2);
      });
    });
  });
});
