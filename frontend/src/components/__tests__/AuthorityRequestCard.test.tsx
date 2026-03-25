import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import AuthorityRequestCard from '../building-detail/AuthorityRequestCard';
import type { AuthorityRequest } from '@/api/permitProcedures';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const baseRequest: AuthorityRequest = {
  id: 'req-1',
  procedure_id: 'proc-1',
  request_type: 'complement',
  subject: 'Plan de securite incendie manquant',
  body: 'Veuillez fournir le plan de securite incendie conforme aux normes AEAI.',
  response_deadline: '2026-04-15',
  response_text: null,
  responded_at: null,
  status: 'open',
  linked_document_ids: [],
  created_at: '2026-03-01',
};

describe('AuthorityRequestCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-03-20'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders request subject and body', () => {
    render(<AuthorityRequestCard request={baseRequest} />);
    expect(screen.getByText('Plan de securite incendie manquant')).toBeInTheDocument();
    expect(screen.getByText(/Veuillez fournir/)).toBeInTheDocument();
  });

  it('renders request type badge', () => {
    render(<AuthorityRequestCard request={baseRequest} />);
    expect(screen.getByText('complement')).toBeInTheDocument();
  });

  it('renders open status badge', () => {
    render(<AuthorityRequestCard request={baseRequest} />);
    expect(screen.getByTestId('request-status-open')).toBeInTheDocument();
  });

  it('renders deadline', () => {
    render(<AuthorityRequestCard request={baseRequest} />);
    expect(screen.getByTestId('request-deadline')).toBeInTheDocument();
    expect(screen.getByText('2026-04-15')).toBeInTheDocument();
  });

  it('shows overdue indicator when past deadline', () => {
    const overdue = { ...baseRequest, response_deadline: '2026-03-10' };
    render(<AuthorityRequestCard request={overdue} />);
    expect(screen.getByTestId('request-status-overdue')).toBeInTheDocument();
  });

  it('shows respond button when open and handler provided', () => {
    const onRespond = vi.fn();
    render(<AuthorityRequestCard request={baseRequest} onRespond={onRespond} />);
    expect(screen.getByTestId('respond-button')).toBeInTheDocument();
  });

  it('opens response form on respond click', () => {
    const onRespond = vi.fn();
    render(<AuthorityRequestCard request={baseRequest} onRespond={onRespond} />);
    fireEvent.click(screen.getByTestId('respond-button'));
    expect(screen.getByTestId('response-textarea')).toBeInTheDocument();
  });

  it('calls onRespond with text on submit', () => {
    const onRespond = vi.fn();
    render(<AuthorityRequestCard request={baseRequest} onRespond={onRespond} />);
    fireEvent.click(screen.getByTestId('respond-button'));
    fireEvent.change(screen.getByTestId('response-textarea'), {
      target: { value: 'Document joint ci-apres.' },
    });
    fireEvent.click(screen.getByTestId('submit-response'));
    expect(onRespond).toHaveBeenCalledWith('req-1', 'Document joint ci-apres.');
  });

  it('shows existing response for responded requests', () => {
    const responded = {
      ...baseRequest,
      status: 'responded' as const,
      response_text: 'Plan envoye par email.',
      responded_at: '2026-03-18',
    };
    render(<AuthorityRequestCard request={responded} />);
    expect(screen.getByText('Plan envoye par email.')).toBeInTheDocument();
  });

  it('renders linked documents count', () => {
    const withDocs = { ...baseRequest, linked_document_ids: ['d-1', 'd-2'] };
    render(<AuthorityRequestCard request={withDocs} />);
    expect(screen.getByText(/2.*procedure.linked_docs/)).toBeInTheDocument();
  });
});
