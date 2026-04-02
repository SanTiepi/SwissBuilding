import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock apiClient
const mockPost = vi.fn();
vi.mock('@/api/client', () => ({
  apiClient: { post: (...args: unknown[]) => mockPost(...args) },
}));

// Mock i18n
vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (_k: string) => '' }),
}));

import ReportGenerationPanel from './ReportGenerationPanel';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const mockReportResult = {
  building_id: 'b1',
  status: 'generated',
  report_type: 'authority',
  html_payload: '<html><body>Test report content</body></html>',
  html_payload_length: 5000,
  sha256: 'abc123def456abc123def456abc123def456abc123def456abc123def456abcd',
  generated_at: '2026-04-02T10:00:00Z',
  version: '1.0.0',
  language: 'fr',
  sections_count: 9,
  include_photos: true,
  include_plans: true,
  metadata: {
    address: 'Rue du Test 42',
    egid: '12345',
    canton: 'VD',
    completeness_pct: 83,
    diagnostics_count: 2,
    samples_count: 5,
    documents_count: 3,
    disclaimer: 'Test disclaimer',
    emitter: 'BatiConnect',
  },
};

describe('ReportGenerationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders panel with generate button', () => {
    render(<ReportGenerationPanel buildingId="b1" />, { wrapper });
    expect(screen.getByText(/Generer le rapport PDF/)).toBeTruthy();
  });

  it('shows loading state while generating', async () => {
    // Never-resolving promise to keep loading state
    mockPost.mockReturnValue(new Promise(() => {}));
    render(<ReportGenerationPanel buildingId="b1" />, { wrapper });

    fireEvent.click(screen.getByText(/Generer le rapport PDF/));

    await waitFor(() => {
      expect(screen.getByText(/Generation en cours/)).toBeTruthy();
    });
  });

  it('shows success state after generation', async () => {
    mockPost.mockResolvedValue({ data: mockReportResult });
    render(<ReportGenerationPanel buildingId="b1" />, { wrapper });

    fireEvent.click(screen.getByText(/Generer le rapport PDF/));

    await waitFor(() => {
      expect(screen.getByText(/Rapport genere avec succes/)).toBeTruthy();
    });

    // Shows metadata
    expect(screen.getByText(/9 sections/)).toBeTruthy();
    expect(screen.getByText(/2 diagnostics/)).toBeTruthy();
    expect(screen.getByText(/83%/)).toBeTruthy();
  });

  it('shows error state on failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    render(<ReportGenerationPanel buildingId="b1" />, { wrapper });

    fireEvent.click(screen.getByText(/Generer le rapport PDF/));

    await waitFor(() => {
      expect(screen.getByText(/Erreur/)).toBeTruthy();
    });
  });

  it('shows download button after generation', async () => {
    mockPost.mockResolvedValue({ data: mockReportResult });
    render(<ReportGenerationPanel buildingId="b1" />, { wrapper });

    fireEvent.click(screen.getByText(/Generer le rapport PDF/));

    await waitFor(() => {
      expect(screen.getByText(/Telecharger le rapport HTML/)).toBeTruthy();
    });
  });

  it('toggles options when expanded', () => {
    render(<ReportGenerationPanel buildingId="b1" />, { wrapper });

    // Options not visible by default
    expect(screen.queryByText(/Inclure les photos terrain/)).toBeNull();

    // Click chevron to expand
    const buttons = screen.getAllByRole('button');
    const chevronBtn = buttons.find((b) => !b.textContent?.includes('Generer'));
    if (chevronBtn) {
      fireEvent.click(chevronBtn);
      expect(screen.getByText(/Inclure les photos terrain/)).toBeTruthy();
      expect(screen.getByText(/Inclure les plans techniques/)).toBeTruthy();
    }
  });

  it('shows regenerate label after first generation', async () => {
    mockPost.mockResolvedValue({ data: mockReportResult });
    render(<ReportGenerationPanel buildingId="b1" />, { wrapper });

    fireEvent.click(screen.getByText(/Generer le rapport PDF/));

    await waitFor(() => {
      expect(screen.getByText(/Regenerer le rapport/)).toBeTruthy();
    });
  });
});
