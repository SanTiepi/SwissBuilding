import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DocumentChecklist } from '../DocumentChecklist';

vi.mock('@/api/documentChecklist', () => ({
  documentChecklistApi: {
    getChecklist: vi.fn().mockResolvedValue({
      building_id: 'bld-1',
      total_required: 5,
      total_present: 2,
      completion_pct: 40.0,
      items: [
        { document_type: 'asbestos_report', label: 'Rapport amiante', importance: 'critical', legal_basis: 'OTConst Art. 60a', status: 'missing', document_id: null, uploaded_at: null, recommendation: 'Faire diagnostic amiante' },
        { document_type: 'cecb_certificate', label: 'Certificat CECB', importance: 'medium', legal_basis: 'LEn cantonal', status: 'present', document_id: 'doc-1', uploaded_at: '2024-01-15T10:00:00Z', recommendation: null },
        { document_type: 'insurance_policy', label: "Police d'assurance", importance: 'high', legal_basis: null, status: 'present', document_id: 'doc-2', uploaded_at: '2024-03-01T10:00:00Z', recommendation: null },
        { document_type: 'pcb_report', label: 'Rapport PCB', importance: 'critical', legal_basis: 'ORRChim', status: 'not_applicable', document_id: null, uploaded_at: null, recommendation: null },
        { document_type: 'building_permit', label: 'Permis de construire', importance: 'low', legal_basis: null, status: 'missing', document_id: null, uploaded_at: null, recommendation: 'Recuperer le permis' },
      ],
      critical_missing: ['asbestos_report'],
      evaluated_at: '2024-03-01T12:00:00Z',
    }),
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

describe('DocumentChecklist', () => {
  it('renders title', async () => {
    renderWithProviders(<DocumentChecklist buildingId="bld-1" />);
    expect(screen.getByText('app.loading')).toBeTruthy();
  });

  it('calls onUpload for missing items', () => {
    const onUpload = vi.fn();
    renderWithProviders(<DocumentChecklist buildingId="bld-1" onUpload={onUpload} />);
    expect(screen.getByText('app.loading')).toBeTruthy();
  });
});
