import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import AuthoritySubmissionRoom from '@/pages/AuthoritySubmissionRoom';
import type { Procedure } from '@/api/permitProcedures';

// Mock i18n
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

// Mock proof delivery API
vi.mock('@/api/proofDelivery', () => ({
  proofDeliveryApi: {
    listByBuilding: vi.fn().mockResolvedValue([]),
  },
}));

const mockProcedure: Procedure = {
  id: 'proc-100',
  building_id: 'b-1',
  procedure_type: 'construction_permit',
  title: 'Permis de construire — desamiantage',
  status: 'submitted',
  authority_name: 'Service urbanisme Lausanne',
  reference_number: 'PC-2026-00198',
  blocks_activities: false,
  submitted_at: '2026-03-15',
  approved_at: null,
  rejected_at: null,
  rejection_reason: null,
  created_at: '2026-03-10',
  updated_at: '2026-03-15',
  steps: [
    {
      id: 'step-1',
      procedure_id: 'proc-100',
      step_order: 1,
      name: 'Depot du dossier',
      status: 'completed',
      due_date: null,
      completed_at: '2026-03-10',
      required_documents: [],
      linked_document_ids: [],
      notes: null,
    },
    {
      id: 'step-2',
      procedure_id: 'proc-100',
      step_order: 2,
      name: 'Examen preliminaire',
      status: 'active',
      due_date: '2026-04-01',
      completed_at: null,
      required_documents: ['Rapport diagnostic', 'Plan execution', 'Formulaire SUVA'],
      linked_document_ids: ['doc-1'],
      notes: null,
    },
    {
      id: 'step-3',
      procedure_id: 'proc-100',
      step_order: 3,
      name: 'Decision',
      status: 'pending',
      due_date: null,
      completed_at: null,
      required_documents: [],
      linked_document_ids: [],
      notes: null,
    },
  ],
  authority_requests: [],
};

const mockProcedureWithRequest: Procedure = {
  ...mockProcedure,
  authority_requests: [
    {
      id: 'req-1',
      procedure_id: 'proc-100',
      request_type: 'complement_request',
      subject: 'Documents manquants',
      body: 'Veuillez fournir le rapport complet.',
      response_deadline: '2026-04-10',
      response_text: null,
      responded_at: null,
      status: 'open',
      linked_document_ids: [],
      created_at: '2026-03-20',
    },
  ],
};

// Mock permit API
const mockGetProcedure = vi.fn();
vi.mock('@/api/permitProcedures', () => ({
  permitProceduresApi: {
    getProcedure: (...args: unknown[]) => mockGetProcedure(...args),
  },
}));

function renderRoom(procedureId = 'proc-100') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/buildings/b-1/procedures/${procedureId}/authority-room`]}>
        <Routes>
          <Route
            path="/buildings/:buildingId/procedures/:procedureId/authority-room"
            element={<AuthoritySubmissionRoom />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AuthoritySubmissionRoom', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state initially', () => {
    mockGetProcedure.mockReturnValue(new Promise(() => {})); // never resolves
    renderRoom();
    expect(screen.getByTestId('authority-room-loading')).toBeInTheDocument();
  });

  it('shows error state on fetch failure', async () => {
    mockGetProcedure.mockRejectedValue(new Error('Network error'));
    renderRoom();
    expect(await screen.findByTestId('authority-room-error')).toBeInTheDocument();
  });

  it('renders the room with submission summary', async () => {
    mockGetProcedure.mockResolvedValue(mockProcedure);
    renderRoom();
    expect(await screen.findByTestId('authority-submission-room')).toBeInTheDocument();
    expect(screen.getByTestId('submission-summary')).toBeInTheDocument();
  });

  it('renders current active step section', async () => {
    mockGetProcedure.mockResolvedValue(mockProcedure);
    renderRoom();
    expect(await screen.findByTestId('current-step')).toBeInTheDocument();
    // Step name appears multiple times (in ProcedureCard timeline + current step + proof set)
    const matches = screen.getAllByText('Examen preliminaire');
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it('renders authority proof set', async () => {
    mockGetProcedure.mockResolvedValue(mockProcedure);
    renderRoom();
    expect(await screen.findByTestId('authority-proof-set')).toBeInTheDocument();
  });

  it('renders next move section', async () => {
    mockGetProcedure.mockResolvedValue(mockProcedure);
    renderRoom();
    expect(await screen.findByTestId('next-move')).toBeInTheDocument();
  });

  it('shows next action as send_proof when docs missing', async () => {
    mockGetProcedure.mockResolvedValue(mockProcedure);
    renderRoom();
    const btn = await screen.findByTestId('next-action-button');
    expect(btn).toHaveTextContent('authority_room.action_send_proof');
  });

  it('shows complement loop when open requests exist', async () => {
    mockGetProcedure.mockResolvedValue(mockProcedureWithRequest);
    renderRoom();
    expect(await screen.findByTestId('complement-loop')).toBeInTheDocument();
  });

  it('shows respond action when open requests exist', async () => {
    mockGetProcedure.mockResolvedValue(mockProcedureWithRequest);
    renderRoom();
    const btn = await screen.findByTestId('next-action-button');
    expect(btn).toHaveTextContent('authority_room.action_respond_request');
  });

  it('renders page title', async () => {
    mockGetProcedure.mockResolvedValue(mockProcedure);
    renderRoom();
    expect(await screen.findByText('authority_room.title')).toBeInTheDocument();
  });

  it('renders procedure title as subtitle', async () => {
    mockGetProcedure.mockResolvedValue(mockProcedure);
    renderRoom();
    // Title appears in page subtitle and in ProcedureCard
    const matches = await screen.findAllByText('Permis de construire — desamiantage');
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });
});
