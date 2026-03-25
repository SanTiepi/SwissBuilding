import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import ProcedureCard from '../building-detail/ProcedureCard';
import type { Procedure } from '@/api/permitProcedures';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const baseProcedure: Procedure = {
  id: 'proc-1',
  building_id: 'b-1',
  procedure_type: 'building_permit',
  title: 'Renovation Facade Nord',
  status: 'submitted',
  authority_name: 'CAMAC Vaud',
  reference_number: 'REF-2026-001',
  blocks_activities: false,
  submitted_at: '2026-01-15',
  approved_at: null,
  rejected_at: null,
  rejection_reason: null,
  created_at: '2026-01-10',
  updated_at: '2026-01-15',
  steps: [
    {
      id: 'step-1',
      procedure_id: 'proc-1',
      step_order: 1,
      name: 'Depot du dossier',
      status: 'completed',
      due_date: null,
      completed_at: '2026-01-15',
      required_documents: ['Plan de situation', 'Formulaire'],
      linked_document_ids: ['doc-1', 'doc-2'],
      notes: null,
    },
    {
      id: 'step-2',
      procedure_id: 'proc-1',
      step_order: 2,
      name: 'Enquete publique',
      status: 'active',
      due_date: '2026-03-01',
      completed_at: null,
      required_documents: ['Avis de mise a enquete'],
      linked_document_ids: [],
      notes: null,
    },
    {
      id: 'step-3',
      procedure_id: 'proc-1',
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

describe('ProcedureCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders procedure title and status', () => {
    render(<ProcedureCard procedure={baseProcedure} />);
    expect(screen.getByText('Renovation Facade Nord')).toBeInTheDocument();
    expect(screen.getByTestId('badge-submitted')).toBeInTheDocument();
  });

  it('renders reference number', () => {
    render(<ProcedureCard procedure={baseProcedure} />);
    expect(screen.getByText('#REF-2026-001')).toBeInTheDocument();
  });

  it('renders procedure type badge', () => {
    render(<ProcedureCard procedure={baseProcedure} />);
    expect(screen.getByText('procedure.type.building_permit')).toBeInTheDocument();
  });

  it('starts collapsed by default', () => {
    render(<ProcedureCard procedure={baseProcedure} />);
    expect(screen.queryByTestId('step-timeline')).not.toBeInTheDocument();
  });

  it('expands when header is clicked', () => {
    render(<ProcedureCard procedure={baseProcedure} />);
    fireEvent.click(screen.getByTestId('procedure-card-toggle'));
    expect(screen.getByTestId('step-timeline')).toBeInTheDocument();
  });

  it('starts expanded when defaultExpanded is true', () => {
    render(<ProcedureCard procedure={baseProcedure} defaultExpanded />);
    expect(screen.getByTestId('step-timeline')).toBeInTheDocument();
  });

  it('renders step timeline with correct steps', () => {
    render(<ProcedureCard procedure={baseProcedure} defaultExpanded />);
    expect(screen.getByTestId('step-step-1')).toBeInTheDocument();
    expect(screen.getByTestId('step-step-2')).toBeInTheDocument();
    expect(screen.getByTestId('step-step-3')).toBeInTheDocument();
  });

  it('renders step names', () => {
    render(<ProcedureCard procedure={baseProcedure} defaultExpanded />);
    expect(screen.getByText('Depot du dossier')).toBeInTheDocument();
    expect(screen.getByText('Enquete publique')).toBeInTheDocument();
    expect(screen.getByText('Decision')).toBeInTheDocument();
  });

  it('shows blocker badge when blocks_activities is true', () => {
    const blocker = { ...baseProcedure, blocks_activities: true };
    render(<ProcedureCard procedure={blocker} />);
    expect(screen.getByTestId('blocker-badge')).toBeInTheDocument();
  });

  it('shows blocker alert when expanded and blocking', () => {
    const blocker = { ...baseProcedure, blocks_activities: true };
    render(<ProcedureCard procedure={blocker} defaultExpanded />);
    expect(screen.getByTestId('blocker-alert')).toBeInTheDocument();
  });

  it('shows submit button for draft procedures', () => {
    const draft = { ...baseProcedure, status: 'draft' as const };
    const onSubmit = vi.fn();
    render(<ProcedureCard procedure={draft} defaultExpanded onSubmit={onSubmit} />);
    const btn = screen.getByTestId('procedure-submit-button');
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(onSubmit).toHaveBeenCalledWith('proc-1');
  });

  it('shows rejection reason for rejected procedures', () => {
    const rejected = {
      ...baseProcedure,
      status: 'rejected' as const,
      rejection_reason: 'Missing fire safety report',
    };
    render(<ProcedureCard procedure={rejected} defaultExpanded />);
    expect(screen.getByText('Missing fire safety report')).toBeInTheDocument();
  });

  it('shows required documents with linked/missing indicators', () => {
    render(<ProcedureCard procedure={baseProcedure} defaultExpanded />);
    expect(screen.getByText('Plan de situation')).toBeInTheDocument();
    expect(screen.getByText('Formulaire')).toBeInTheDocument();
    expect(screen.getByText('Avis de mise a enquete')).toBeInTheDocument();
    // Step 2 has 1 required but 0 linked = 1 missing
    expect(screen.getByText(/1.*procedure.missing_docs/)).toBeInTheDocument();
  });

  it('shows authority name when expanded', () => {
    render(<ProcedureCard procedure={baseProcedure} defaultExpanded />);
    expect(screen.getByText('CAMAC Vaud')).toBeInTheDocument();
  });

  it('shows open requests count badge', () => {
    const withReqs = {
      ...baseProcedure,
      authority_requests: [
        {
          id: 'req-1',
          procedure_id: 'proc-1',
          request_type: 'complement',
          subject: 'Missing plan',
          body: 'Please provide plan',
          response_deadline: '2026-04-01',
          response_text: null,
          responded_at: null,
          status: 'open' as const,
          linked_document_ids: [],
          created_at: '2026-03-01',
        },
      ],
    };
    render(<ProcedureCard procedure={withReqs} />);
    expect(screen.getByText(/1.*procedure.open_requests/)).toBeInTheDocument();
  });
});
