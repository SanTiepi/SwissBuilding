import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BuyerCounterproofCard } from '@/components/BuyerCounterproofCard';
import type { CounterproofObjection } from '@/components/BuyerCounterproofCard';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockObjections: CounterproofObjection[] = [
  {
    objection: 'Too expensive',
    workflow: 'Full diagnostic',
    proof_surface: 'ROI dashboard',
    evidence_available: true,
  },
  {
    objection: 'Not needed',
    workflow: 'Regulatory check',
    proof_surface: 'Readiness wallet',
    evidence_available: false,
  },
  {
    objection: 'Already done manually',
    workflow: 'Evidence pack',
    proof_surface: 'Completeness score',
    evidence_available: true,
  },
];

describe('BuyerCounterproofCard', () => {
  it('renders nothing when no objections', () => {
    const { container } = render(<BuyerCounterproofCard objections={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders card with title', () => {
    render(<BuyerCounterproofCard objections={mockObjections} />);
    expect(screen.getByTestId('buyer-counterproof-card')).toBeInTheDocument();
    expect(screen.getByText('counterproof.title')).toBeInTheDocument();
  });

  it('renders all objection rows', () => {
    render(<BuyerCounterproofCard objections={mockObjections} />);
    expect(screen.getByTestId('counterproof-row-0')).toBeInTheDocument();
    expect(screen.getByTestId('counterproof-row-1')).toBeInTheDocument();
    expect(screen.getByTestId('counterproof-row-2')).toBeInTheDocument();
  });

  it('renders objection text', () => {
    render(<BuyerCounterproofCard objections={mockObjections} />);
    expect(screen.getByText('Too expensive')).toBeInTheDocument();
    expect(screen.getByText('Not needed')).toBeInTheDocument();
    expect(screen.getByText('Already done manually')).toBeInTheDocument();
  });

  it('renders workflow and proof surface', () => {
    render(<BuyerCounterproofCard objections={mockObjections} />);
    expect(screen.getByText('Full diagnostic')).toBeInTheDocument();
    expect(screen.getByText('ROI dashboard')).toBeInTheDocument();
    expect(screen.getByText('Readiness wallet')).toBeInTheDocument();
  });

  it('renders evidence availability icons', () => {
    render(<BuyerCounterproofCard objections={mockObjections} />);
    const yesIcons = screen.getAllByTestId('evidence-yes');
    const noIcons = screen.getAllByTestId('evidence-no');
    expect(yesIcons.length).toBe(2);
    expect(noIcons.length).toBe(1);
  });

  it('renders table headers', () => {
    render(<BuyerCounterproofCard objections={mockObjections} />);
    expect(screen.getByText('counterproof.objection')).toBeInTheDocument();
    expect(screen.getByText('counterproof.workflow')).toBeInTheDocument();
    expect(screen.getByText('counterproof.proof_surface')).toBeInTheDocument();
    expect(screen.getByText('counterproof.available')).toBeInTheDocument();
  });
});
