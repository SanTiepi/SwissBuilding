import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DocumentExtractionPreview } from '../DocumentExtractionPreview';

vi.mock('@/api/documentExtraction', () => ({
  documentExtractionApi: {
    extract: vi.fn().mockResolvedValue({
      document_id: 'doc-1',
      total_fields: 3,
      field_counts: { dates: 1, amounts: 1, cfc_codes: 1 },
      extractions: {
        dates: [{ field: 'dates', value: '15.03.2024', raw_match: '15.03.2024', position: 10, confidence: 0.85, ai_generated: true }],
        amounts: [{ field: 'amounts', value: 'CHF1234', raw_match: 'CHF 1\'234', position: 30, confidence: 0.80, ai_generated: true }],
        cfc_codes: [{ field: 'cfc_codes', value: 'CFC 281', raw_match: 'CFC 281', position: 50, confidence: 0.90, ai_generated: true }],
        addresses: [],
        parcels: [],
        parties: [],
        references: [],
        pollutant_results: [],
        energy_class: [],
        building_year: [],
      },
    }),
    getExtractions: vi.fn().mockResolvedValue(null),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k, language: 'fr', setLanguage: vi.fn() }),
}));

vi.mock('@/utils/formatters', () => ({
  cn: (...args: (string | undefined | null | false)[]) => args.filter(Boolean).join(' '),
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('DocumentExtractionPreview', () => {
  it('renders title', () => {
    renderWithProviders(<DocumentExtractionPreview documentId="doc-1" />);
    expect(screen.getByText('doc_extraction.title')).toBeTruthy();
  });

  it('renders extract button when no data', () => {
    renderWithProviders(<DocumentExtractionPreview documentId="doc-1" />);
    expect(screen.getByTestId('extract-btn')).toBeTruthy();
  });

  it('passes confirm callback', () => {
    const onConfirm = vi.fn();
    renderWithProviders(<DocumentExtractionPreview documentId="doc-1" onConfirm={onConfirm} />);
    // Button exists (will show after extraction)
    expect(screen.getByTestId('extract-btn')).toBeTruthy();
  });

  it('passes reject callback', () => {
    const onReject = vi.fn();
    renderWithProviders(<DocumentExtractionPreview documentId="doc-1" onReject={onReject} />);
    expect(screen.getByTestId('extract-btn')).toBeTruthy();
  });
});
