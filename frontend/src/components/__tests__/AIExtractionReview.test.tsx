import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AIExtractionReview } from '../marketplace/AIExtractionReview';

vi.mock('@/api/remediation', () => ({
  remediationApi: {
    confirmExtraction: vi.fn().mockResolvedValue({ id: 'log-1', status: 'confirmed' }),
    correctExtraction: vi.fn().mockResolvedValue({ id: 'log-1', status: 'corrected' }),
    rejectExtraction: vi.fn().mockResolvedValue({ id: 'log-1', status: 'rejected' }),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k, language: 'fr', setLanguage: vi.fn() }),
}));

vi.mock('@/utils/formatters', () => ({
  cn: (...args: (string | undefined | null | false)[]) => args.filter(Boolean).join(' '),
}));

const mockExtraction = {
  id: 'log-1',
  extraction_type: 'quote_pdf',
  source_document_id: null,
  source_filename: 'quote.pdf',
  input_hash: 'a'.repeat(64),
  output_data: {
    scope_items: ['asbestos_removal'],
    amount_chf: 45000,
    confidence_per_field: { scope_items: 0.85, amount_chf: 0.9 },
  },
  confidence_score: 0.8,
  ai_model: 'stub-v0',
  ambiguous_fields: [{ field: 'timeline', reason: 'Multiple timelines' }],
  unknown_fields: [{ field: 'payment_terms' }],
  status: 'draft' as const,
  confirmed_by_user_id: null,
  confirmed_at: null,
  created_at: '2026-03-25T10:00:00Z',
};

describe('AIExtractionReview', () => {
  it('renders extraction type and model', () => {
    render(<AIExtractionReview extraction={mockExtraction} />);
    expect(screen.getByText(/quote_pdf/)).toBeTruthy();
    expect(screen.getByText(/stub-v0/)).toBeTruthy();
  });

  it('renders status badge', () => {
    render(<AIExtractionReview extraction={mockExtraction} />);
    expect(screen.getByText('draft')).toBeTruthy();
  });

  it('renders overall confidence', () => {
    render(<AIExtractionReview extraction={mockExtraction} />);
    expect(screen.getByText('80%')).toBeTruthy();
  });

  it('renders per-field confidence', () => {
    render(<AIExtractionReview extraction={mockExtraction} />);
    expect(screen.getByText(/scope_items: 85%/)).toBeTruthy();
    expect(screen.getByText(/amount_chf: 90%/)).toBeTruthy();
  });

  it('renders ambiguous field warnings', () => {
    render(<AIExtractionReview extraction={mockExtraction} />);
    expect(screen.getByText('extraction.ambiguous_fields')).toBeTruthy();
    expect(screen.getByText(/Multiple timelines/)).toBeTruthy();
  });

  it('renders unknown fields', () => {
    render(<AIExtractionReview extraction={mockExtraction} />);
    expect(screen.getByText('extraction.unknown_fields')).toBeTruthy();
    expect(screen.getByText('payment_terms')).toBeTruthy();
  });

  it('renders action buttons for draft', () => {
    render(<AIExtractionReview extraction={mockExtraction} />);
    expect(screen.getByText('extraction.confirm')).toBeTruthy();
    expect(screen.getByText('extraction.correct')).toBeTruthy();
    expect(screen.getByText('extraction.reject')).toBeTruthy();
  });

  it('hides action buttons for confirmed status', () => {
    const confirmed = { ...mockExtraction, status: 'confirmed' as const };
    render(<AIExtractionReview extraction={confirmed} />);
    expect(screen.queryByText('extraction.confirm')).toBeNull();
  });

  it('switches to edit mode on correct click', async () => {
    render(<AIExtractionReview extraction={mockExtraction} />);
    fireEvent.click(screen.getByText('extraction.correct'));
    await waitFor(() => {
      expect(screen.getByText('extraction.save_correction')).toBeTruthy();
      expect(screen.getByText('common.cancel')).toBeTruthy();
    });
  });

  it('calls onUpdate after confirm', async () => {
    const onUpdate = vi.fn();
    render(<AIExtractionReview extraction={mockExtraction} onUpdate={onUpdate} />);
    fireEvent.click(screen.getByText('extraction.confirm'));
    await waitFor(() => expect(onUpdate).toHaveBeenCalledWith({ id: 'log-1', status: 'confirmed' }));
  });

  it('renders output data as JSON', () => {
    render(<AIExtractionReview extraction={mockExtraction} />);
    expect(screen.getByText(/asbestos_removal/)).toBeTruthy();
  });
});
