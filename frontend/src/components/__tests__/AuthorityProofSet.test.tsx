import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import AuthorityProofSet from '../building-detail/AuthorityProofSet';
import type { ProofRequirement } from '../building-detail/AuthorityProofSet';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const linkedReq: ProofRequirement = { label: 'Rapport diagnostic amiante', document_id: 'doc-1' };
const missingReq: ProofRequirement = { label: "Plan d'execution", document_id: null };

describe('AuthorityProofSet', () => {
  it('renders with correct test id', () => {
    render(<AuthorityProofSet requirements={[linkedReq]} stepName="Review" />);
    expect(screen.getByTestId('authority-proof-set')).toBeInTheDocument();
  });

  it('shows step name', () => {
    render(<AuthorityProofSet requirements={[linkedReq]} stepName="Examen preliminaire" />);
    expect(screen.getByText('Examen preliminaire')).toBeInTheDocument();
  });

  it('displays linked count / total', () => {
    render(<AuthorityProofSet requirements={[linkedReq, missingReq]} stepName="Review" />);
    expect(screen.getByTestId('proof-set-count')).toHaveTextContent('1/2');
  });

  it('shows linked indicator for available documents', () => {
    render(<AuthorityProofSet requirements={[linkedReq]} stepName="Review" />);
    expect(screen.getByText('authority_room.linked')).toBeInTheDocument();
  });

  it('shows missing indicator for unavailable documents', () => {
    render(<AuthorityProofSet requirements={[missingReq]} stepName="Review" />);
    expect(screen.getByText('authority_room.missing')).toBeInTheDocument();
  });

  it('shows warning when documents are missing', () => {
    render(<AuthorityProofSet requirements={[missingReq]} stepName="Review" />);
    expect(screen.getByTestId('proof-set-warning')).toBeInTheDocument();
  });

  it('does not show warning when all documents are linked', () => {
    render(<AuthorityProofSet requirements={[linkedReq]} stepName="Review" />);
    expect(screen.queryByTestId('proof-set-warning')).not.toBeInTheDocument();
  });

  it('shows empty state when no requirements', () => {
    render(<AuthorityProofSet requirements={[]} stepName="Review" />);
    expect(screen.getByTestId('proof-set-empty')).toBeInTheDocument();
  });

  it('renders individual proof items', () => {
    render(<AuthorityProofSet requirements={[linkedReq, missingReq]} stepName="Review" />);
    expect(screen.getByTestId('proof-item-0')).toBeInTheDocument();
    expect(screen.getByTestId('proof-item-1')).toBeInTheDocument();
  });
});
