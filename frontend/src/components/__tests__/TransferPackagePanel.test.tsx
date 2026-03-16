import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TransferPackagePanel } from '@/components/TransferPackagePanel';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGenerate = vi.fn();
vi.mock('@/api/transferPackage', async () => {
  const actual = await vi.importActual<typeof import('@/api/transferPackage')>('@/api/transferPackage');
  return {
    ...actual,
    transferPackageApi: {
      generate: (...args: unknown[]) => mockGenerate(...args),
    },
  };
});

const mockToast = vi.fn();
vi.mock('@/store/toastStore', () => ({
  toast: (...args: unknown[]) => mockToast(...args),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const MOCK_RESPONSE = {
  package_id: 'pkg-1',
  building_id: 'b1',
  generated_at: '2026-03-08T00:00:00Z',
  schema_version: '1.0',
  building_summary: { egid: 1234 },
  passport: { grade: 'A' },
  diagnostics_summary: { total: 2 },
  documents_summary: { total: 5 },
  interventions_summary: null,
  actions_summary: { total_open: 3 },
  evidence_coverage: { total: 8 },
  contradictions: { total_count: 1 },
  unknowns: null,
  snapshots: [{ id: 's1' }, { id: 's2' }],
  completeness: { score: 0.9 },
  readiness: { score: 0.8 },
  metadata: {},
};

describe('TransferPackagePanel', () => {
  beforeEach(() => {
    mockGenerate.mockReset();
    mockToast.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('toasts and shows explicit error state when generation fails', async () => {
    mockGenerate.mockRejectedValue(new Error('boom'));

    render(<TransferPackagePanel buildingId="b1" />, { wrapper });

    fireEvent.click(screen.getByRole('button', { name: 'transfer.generate' }));

    expect(await screen.findByText('transfer.error')).toBeInTheDocument();
    await waitFor(() => expect(mockToast).toHaveBeenCalledWith('boom'));
  });

  it('renders generated package summary cards on success', async () => {
    mockGenerate.mockResolvedValue(MOCK_RESPONSE);

    render(<TransferPackagePanel buildingId="b1" />, { wrapper });

    fireEvent.click(screen.getByRole('button', { name: 'transfer.generate' }));

    expect(await screen.findByText('transfer.version 1.0')).toBeInTheDocument();
    expect(screen.getAllByText('transfer.section_diagnostics').length).toBeGreaterThan(0);
    expect(screen.getAllByText('2').length).toBeGreaterThan(0);
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    // Download button shows format-specific label
    expect(screen.getByText(/transfer\.download/)).toBeInTheDocument();
  });

  it('renders section descriptions in the selector', () => {
    render(<TransferPackagePanel buildingId="b1" />, { wrapper });

    // Each section should show its description key
    expect(screen.getByText('transfer.desc_passport')).toBeInTheDocument();
    expect(screen.getByText('transfer.desc_diagnostics')).toBeInTheDocument();
    expect(screen.getByText('transfer.desc_readiness')).toBeInTheDocument();
  });

  it('shows section count in header', () => {
    render(<TransferPackagePanel buildingId="b1" />, { wrapper });

    // All 11 sections selected by default
    expect(screen.getByText('11/11 transfer.sections_selected')).toBeInTheDocument();
  });

  it('toggles format selector between JSON and PDF', () => {
    render(<TransferPackagePanel buildingId="b1" />, { wrapper });

    const pdfBtn = screen.getByText('transfer.format_pdf');
    fireEvent.click(pdfBtn);

    // PDF button should now be active (has red background)
    expect(pdfBtn.closest('button')).toHaveClass('bg-red-600');
  });

  it('shows recipient form when expand button is clicked', () => {
    render(<TransferPackagePanel buildingId="b1" />, { wrapper });

    // Recipient form should be hidden initially
    expect(screen.queryByPlaceholderText('Jean Dupont')).not.toBeInTheDocument();

    // Click expand button
    fireEvent.click(screen.getByText('transfer.expand_recipient'));

    // Now recipient fields should be visible
    expect(screen.getByPlaceholderText('Jean Dupont')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('jean@example.com')).toBeInTheDocument();
  });

  it('shows package preview when toggled', () => {
    render(<TransferPackagePanel buildingId="b1" />, { wrapper });

    fireEvent.click(screen.getByText('transfer.preview'));

    expect(screen.getByText('transfer.preview_desc')).toBeInTheDocument();
    // Should show included/excluded badges
    expect(screen.getAllByText('transfer.included').length).toBeGreaterThan(0);
  });

  it('shows package history after successful generation', async () => {
    mockGenerate.mockResolvedValue(MOCK_RESPONSE);

    render(<TransferPackagePanel buildingId="b1" />, { wrapper });

    fireEvent.click(screen.getByRole('button', { name: 'transfer.generate' }));

    // Wait for success
    await screen.findByText('transfer.version 1.0');

    // History section should appear
    expect(screen.getByText('transfer.history')).toBeInTheDocument();
  });

  it('shows success toast on generation', async () => {
    mockGenerate.mockResolvedValue(MOCK_RESPONSE);

    render(<TransferPackagePanel buildingId="b1" />, { wrapper });

    fireEvent.click(screen.getByRole('button', { name: 'transfer.generate' }));

    await screen.findByText('transfer.version 1.0');
    await waitFor(() => expect(mockToast).toHaveBeenCalledWith('transfer.success', 'success'));
  });

  it('deselects a section and updates the count', () => {
    render(<TransferPackagePanel buildingId="b1" />, { wrapper });

    // Click passport section to deselect it
    const passportButtons = screen.getAllByText('transfer.section_passport');
    fireEvent.click(passportButtons[0]);

    expect(screen.getByText('10/11 transfer.sections_selected')).toBeInTheDocument();
  });
});
