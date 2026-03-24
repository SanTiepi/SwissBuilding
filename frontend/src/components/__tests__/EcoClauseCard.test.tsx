import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { EcoClauseCard } from '../building-detail/EcoClauseCard';

vi.mock('@/api/ecoclauses', () => ({
  ecoClausesApi: {
    get: vi.fn().mockResolvedValue({
      building_id: 'b-1',
      context: 'renovation',
      generated_at: '2026-03-24T10:00:00Z',
      total_clauses: 4,
      detected_pollutants: ['asbestos', 'pcb'],
      sections: [
        {
          section_id: 'SEC-GEN',
          title: 'Obligations generales',
          clauses: [
            {
              clause_id: 'GEN-01',
              title: 'Diagnostic prealable obligatoire',
              body: 'Avant le debut des travaux, un diagnostic polluants complet doit etre realise.',
              legal_references: ['OTConst Art. 60a'],
              applicability: 'Toujours applicable avant travaux',
              pollutants: [],
            },
          ],
        },
        {
          section_id: 'SEC-AMI',
          title: 'Clauses amiante',
          clauses: [
            {
              clause_id: 'AMI-01',
              title: 'Notification SUVA obligatoire',
              body: "L'entrepreneur doit notifier la SUVA.",
              legal_references: ['OTConst Art. 82-86', 'CFST 6503'],
              applicability: "Presence d'amiante confirmee par diagnostic",
              pollutants: ['asbestos'],
            },
            {
              clause_id: 'AMI-02',
              title: 'Mesures de protection des travailleurs',
              body: "Les travaux en presence d'amiante doivent etre realises conformement a la directive CFST 6503.",
              legal_references: ['CFST 6503'],
              applicability: "Presence d'amiante confirmee par diagnostic",
              pollutants: ['asbestos'],
            },
          ],
        },
        {
          section_id: 'SEC-PCB',
          title: 'Clauses PCB',
          clauses: [
            {
              clause_id: 'PCB-01',
              title: 'Gestion des materiaux contenant des PCB',
              body: 'Les materiaux contenant des PCB doivent etre retires.',
              legal_references: ['ORRChim Annexe 2.15'],
              applicability: 'Presence de PCB confirmee (> 50 mg/kg)',
              pollutants: ['pcb'],
            },
          ],
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
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('EcoClauseCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the card title and clause count', async () => {
    render(<EcoClauseCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('eco_clause.title')).toBeInTheDocument();
      expect(screen.getByText(/4/)).toBeInTheDocument();
    });
  });

  it('shows detected pollutant badges', async () => {
    render(<EcoClauseCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('pollutant.asbestos')).toBeInTheDocument();
      expect(screen.getByText('pollutant.pcb')).toBeInTheDocument();
    });
  });

  it('renders section headers', async () => {
    render(<EcoClauseCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Obligations generales')).toBeInTheDocument();
      expect(screen.getByText('Clauses amiante')).toBeInTheDocument();
      expect(screen.getByText('Clauses PCB')).toBeInTheDocument();
    });
  });

  it('expands a section to show clause details', async () => {
    render(<EcoClauseCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Obligations generales')).toBeInTheDocument();
    });

    // Clauses should not be visible initially
    expect(screen.queryByText('Diagnostic prealable obligatoire')).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(screen.getByText('Obligations generales'));

    await waitFor(() => {
      expect(screen.getByText('Diagnostic prealable obligatoire')).toBeInTheDocument();
      expect(screen.getByText('OTConst Art. 60a')).toBeInTheDocument();
    });
  });

  it('shows context toggle buttons', async () => {
    render(<EcoClauseCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('eco_clause.context_renovation')).toBeInTheDocument();
      expect(screen.getByText('eco_clause.context_demolition')).toBeInTheDocument();
    });
  });

  it('returns null when payload has zero clauses', async () => {
    const { ecoClausesApi } = await import('@/api/ecoclauses');
    vi.mocked(ecoClausesApi.get).mockResolvedValueOnce({
      building_id: 'b-1',
      context: 'renovation',
      generated_at: '2026-03-24T10:00:00Z',
      total_clauses: 0,
      sections: [],
      detected_pollutants: [],
    });

    const { container } = render(<EcoClauseCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(container.firstChild).toBeNull();
    });
  });
});
