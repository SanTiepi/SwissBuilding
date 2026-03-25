import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { publicSectorApi } from '@/api/publicSector';
import { CommitteePackCard } from '../building-detail/CommitteePackCard';

vi.mock('@/api/publicSector', () => ({
  publicSectorApi: {
    listCommitteePacks: vi.fn(),
    generateCommitteePack: vi.fn(),
    recordDecision: vi.fn(),
    listDecisionTraces: vi.fn().mockResolvedValue([]),
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

const mockPacks = [
  {
    id: 'cp-1',
    building_id: 'b-1',
    committee_name: 'Conseil municipal de Lausanne',
    committee_type: 'municipal_council',
    pack_version: 1,
    status: 'submitted',
    sections: null,
    procurement_clauses: [{ clause: 'Marche ouvert >150k CHF' }, { clause: 'Critere ecologique 20%' }],
    content_hash: 'xyz',
    decision_deadline: '2026-04-15',
    submitted_at: '2026-03-20T10:00:00Z',
    decided_at: null,
    created_at: '2026-03-20T10:00:00Z',
    updated_at: '2026-03-20T10:00:00Z',
  },
];

describe('CommitteePackCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(publicSectorApi.listDecisionTraces).mockResolvedValue([]);
  });

  it('renders committee pack with name and type', async () => {
    vi.mocked(publicSectorApi.listCommitteePacks).mockResolvedValue(mockPacks);
    render(<CommitteePackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('committee-name')).toHaveTextContent('Conseil municipal de Lausanne');
    });
  });

  it('renders status badge', async () => {
    vi.mocked(publicSectorApi.listCommitteePacks).mockResolvedValue(mockPacks);
    render(<CommitteePackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('committee-pack-status')).toBeInTheDocument();
    });
  });

  it('renders decision deadline', async () => {
    vi.mocked(publicSectorApi.listCommitteePacks).mockResolvedValue(mockPacks);
    render(<CommitteePackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('committee-deadline')).toBeInTheDocument();
    });
  });

  it('renders collapsible procurement clauses', async () => {
    vi.mocked(publicSectorApi.listCommitteePacks).mockResolvedValue(mockPacks);
    render(<CommitteePackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('toggle-clauses')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('toggle-clauses'));

    await waitFor(() => {
      expect(screen.getByTestId('clauses-list')).toBeInTheDocument();
      expect(screen.getByText('Marche ouvert >150k CHF')).toBeInTheDocument();
    });
  });

  it('shows empty state when no packs', async () => {
    vi.mocked(publicSectorApi.listCommitteePacks).mockResolvedValue([]);
    render(<CommitteePackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('committee-pack-empty')).toBeInTheDocument();
    });
  });

  it('shows record decision button', async () => {
    vi.mocked(publicSectorApi.listCommitteePacks).mockResolvedValue(mockPacks);
    render(<CommitteePackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('record-decision-button')).toBeInTheDocument();
    });
  });

  it('opens inline decision form on click', async () => {
    vi.mocked(publicSectorApi.listCommitteePacks).mockResolvedValue(mockPacks);
    render(<CommitteePackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('record-decision-button')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('record-decision-button'));

    await waitFor(() => {
      expect(screen.getByTestId('decision-form')).toBeInTheDocument();
      expect(screen.getByTestId('decision-reviewer-name')).toBeInTheDocument();
      expect(screen.getByTestId('decision-select')).toBeInTheDocument();
    });
  });

  it('renders decision traces when present', async () => {
    vi.mocked(publicSectorApi.listCommitteePacks).mockResolvedValue(mockPacks);
    vi.mocked(publicSectorApi.listDecisionTraces).mockResolvedValue([
      {
        id: 'dt-1',
        pack_type: 'committee',
        pack_id: 'cp-1',
        reviewer_name: 'Jean Dupont',
        reviewer_role: 'President',
        reviewer_org_id: null,
        decision: 'approved',
        conditions: 'Sous reserve budget',
        notes: null,
        evidence_refs: null,
        confidence_level: null,
        decided_at: '2026-03-22T14:00:00Z',
        created_at: '2026-03-22T14:00:00Z',
      },
    ]);
    render(<CommitteePackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('decision-traces-list')).toBeInTheDocument();
      expect(screen.getByText('Jean Dupont')).toBeInTheDocument();
    });
  });
});
