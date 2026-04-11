import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import DocumentClassificationBadge from '../DocumentClassificationBadge';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        'doc_classifier.confidence': 'Confidence',
        'doc_classifier.correct': 'Correct',
        'doc_classifier.type.asbestos_report': 'Asbestos report',
        'doc_classifier.type.lead_report': 'Lead report',
        'doc_classifier.type.unclassified': 'Unclassified',
      };
      return map[key] || key;
    },
  }),
}));

describe('DocumentClassificationBadge', () => {
  it('renders badge with document type label', () => {
    render(<DocumentClassificationBadge documentType="asbestos_report" confidence={0.85} />);
    expect(screen.getByTestId('doc-classification-badge')).toBeInTheDocument();
    expect(screen.getByText('Asbestos report')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
  });

  it('shows green color for high confidence (>0.8)', () => {
    const { container } = render(<DocumentClassificationBadge documentType="asbestos_report" confidence={0.9} />);
    const badge = container.querySelector('[class*="bg-green"]');
    expect(badge).not.toBeNull();
  });

  it('shows amber color for medium confidence (0.6-0.8)', () => {
    const { container } = render(<DocumentClassificationBadge documentType="lead_report" confidence={0.65} />);
    const badge = container.querySelector('[class*="bg-amber"]');
    expect(badge).not.toBeNull();
  });

  it('shows red color for low confidence (<0.6)', () => {
    const { container } = render(<DocumentClassificationBadge documentType="unclassified" confidence={0.3} />);
    const badge = container.querySelector('[class*="bg-red"]');
    expect(badge).not.toBeNull();
  });

  it('shows correct button when onCorrect is provided', () => {
    const onCorrect = vi.fn();
    render(<DocumentClassificationBadge documentType="asbestos_report" confidence={0.85} onCorrect={onCorrect} />);
    expect(screen.getByTestId('doc-classification-correct-btn')).toBeInTheDocument();
  });

  it('does not show correct button when onCorrect is not provided', () => {
    render(<DocumentClassificationBadge documentType="asbestos_report" confidence={0.85} />);
    expect(screen.queryByTestId('doc-classification-correct-btn')).not.toBeInTheDocument();
  });

  it('opens correction dropdown on click and calls onCorrect', () => {
    const onCorrect = vi.fn();
    render(<DocumentClassificationBadge documentType="asbestos_report" confidence={0.85} onCorrect={onCorrect} />);

    fireEvent.click(screen.getByTestId('doc-classification-correct-btn'));
    expect(screen.getByTestId('doc-classification-correction-dropdown')).toBeInTheDocument();

    // Click a type in the dropdown
    const buttons = screen.getByTestId('doc-classification-correction-dropdown').querySelectorAll('button');
    expect(buttons.length).toBe(10); // 10 document types
    fireEvent.click(buttons[0]);
    expect(onCorrect).toHaveBeenCalledWith('asbestos_report');
  });
});
