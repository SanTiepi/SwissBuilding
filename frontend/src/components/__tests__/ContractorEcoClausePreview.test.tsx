import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  ContractorEcoClausePreview,
  type EcoClauseSummary,
} from '../building-detail/ContractorEcoClausePreview';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const SAMPLE_ECO_CLAUSES: EcoClauseSummary = {
  total_clauses: 3,
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
        },
        {
          clause_id: 'AMI-02',
          title: 'Mesures de protection',
          body: 'Les travaux doivent etre realises conformement a la directive CFST 6503.',
          legal_references: ['CFST 6503'],
        },
      ],
    },
  ],
};

describe('ContractorEcoClausePreview', () => {
  it('renders the preview title and clause count', () => {
    render(<ContractorEcoClausePreview ecoClauses={SAMPLE_ECO_CLAUSES} />);

    expect(screen.getByText('eco_clause.contractor_preview_title')).toBeInTheDocument();
    expect(screen.getByText(/3/)).toBeInTheDocument();
  });

  it('shows contractor notice banner', () => {
    render(<ContractorEcoClausePreview ecoClauses={SAMPLE_ECO_CLAUSES} />);

    expect(screen.getByText('eco_clause.contractor_notice')).toBeInTheDocument();
  });

  it('displays detected pollutant badges', () => {
    render(<ContractorEcoClausePreview ecoClauses={SAMPLE_ECO_CLAUSES} />);

    expect(screen.getByText('pollutant.asbestos')).toBeInTheDocument();
    expect(screen.getByText('pollutant.pcb')).toBeInTheDocument();
  });

  it('renders section headers', () => {
    render(<ContractorEcoClausePreview ecoClauses={SAMPLE_ECO_CLAUSES} />);

    expect(screen.getByText('Obligations generales')).toBeInTheDocument();
    expect(screen.getByText('Clauses amiante')).toBeInTheDocument();
  });

  it('expands a section to show clause details and legal references', () => {
    render(<ContractorEcoClausePreview ecoClauses={SAMPLE_ECO_CLAUSES} />);

    // Clause body not visible initially
    expect(
      screen.queryByText('Avant le debut des travaux, un diagnostic polluants complet doit etre realise.'),
    ).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(screen.getByText('Obligations generales'));

    expect(screen.getByText('Diagnostic prealable obligatoire')).toBeInTheDocument();
    expect(
      screen.getByText('Avant le debut des travaux, un diagnostic polluants complet doit etre realise.'),
    ).toBeInTheDocument();
    expect(screen.getByText('OTConst Art. 60a')).toBeInTheDocument();
    expect(screen.getByText('GEN-01')).toBeInTheDocument();
  });

  it('collapses an expanded section on second click', () => {
    render(<ContractorEcoClausePreview ecoClauses={SAMPLE_ECO_CLAUSES} />);

    const sectionButton = screen.getByText('Obligations generales');
    fireEvent.click(sectionButton);
    expect(screen.getByText('Diagnostic prealable obligatoire')).toBeInTheDocument();

    fireEvent.click(sectionButton);
    expect(screen.queryByText('Diagnostic prealable obligatoire')).not.toBeInTheDocument();
  });

  it('returns null when total_clauses is 0', () => {
    const emptyClauses: EcoClauseSummary = {
      total_clauses: 0,
      detected_pollutants: [],
      sections: [],
    };

    const { container } = render(<ContractorEcoClausePreview ecoClauses={emptyClauses} />);
    expect(container.firstChild).toBeNull();
  });

  it('has the correct test id', () => {
    render(<ContractorEcoClausePreview ecoClauses={SAMPLE_ECO_CLAUSES} />);
    expect(screen.getByTestId('contractor-eco-clause-preview')).toBeInTheDocument();
  });

  it('shows multiple legal references for a clause', () => {
    render(<ContractorEcoClausePreview ecoClauses={SAMPLE_ECO_CLAUSES} />);

    fireEvent.click(screen.getByText('Clauses amiante'));

    expect(screen.getByText('OTConst Art. 82-86')).toBeInTheDocument();
    // CFST 6503 appears in both AMI-01 and AMI-02
    const cfstRefs = screen.getAllByText('CFST 6503');
    expect(cfstRefs.length).toBe(2);
  });
});
