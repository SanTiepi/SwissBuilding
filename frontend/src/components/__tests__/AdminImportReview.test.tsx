import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AdminImportReview from '@/pages/AdminImportReview';

vi.mock('@/utils/formatters', () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(' '),
  formatDate: (d: string) => d,
}));

vi.mock('@/api/exchange', () => ({
  exchangeApi: {
    listPublications: vi.fn().mockResolvedValue([]),
    listImportReceipts: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock('@/api/exchangeHardening', () => ({
  exchangeHardeningApi: {
    validateImport: vi.fn(),
    reviewImport: vi.fn(),
    integrateImport: vi.fn(),
  },
}));

function renderWithQuery(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('AdminImportReview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', () => {
    renderWithQuery(<AdminImportReview />);
    expect(screen.getByTestId('admin-import-review')).toBeTruthy();
    expect(screen.getByText('Import Validation & Review')).toBeTruthy();
  });

  it('renders receipt ID input', () => {
    renderWithQuery(<AdminImportReview />);
    expect(screen.getByTestId('receipt-id-input')).toBeTruthy();
  });

  it('renders validate button', () => {
    renderWithQuery(<AdminImportReview />);
    expect(screen.getByTestId('validate-btn')).toBeTruthy();
  });

  it('disables validate button when no receipt ID', () => {
    renderWithQuery(<AdminImportReview />);
    const btn = screen.getByTestId('validate-btn') as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it('enables validate button when receipt ID entered', async () => {
    renderWithQuery(<AdminImportReview />);
    const input = screen.getByTestId('receipt-id-input') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'some-uuid' } });
    const btn = screen.getByTestId('validate-btn') as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });

  it('shows validation report on successful validate', async () => {
    const { exchangeHardeningApi } = await import('@/api/exchangeHardening');
    vi.mocked(exchangeHardeningApi.validateImport).mockResolvedValue({
      id: 'report-1',
      import_receipt_id: 'receipt-1',
      schema_valid: true,
      contract_valid: true,
      version_valid: true,
      hash_valid: true,
      identity_safe: true,
      validation_errors: null,
      overall_status: 'passed',
      validated_at: '2026-03-25T10:00:00Z',
      validated_by_user_id: null,
      created_at: '2026-03-25T10:00:00Z',
    });

    renderWithQuery(<AdminImportReview />);
    const input = screen.getByTestId('receipt-id-input') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'receipt-1' } });
    fireEvent.click(screen.getByTestId('validate-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('validation-report')).toBeTruthy();
    });
    expect(screen.getByTestId('validation-status')).toBeTruthy();
    expect(screen.getByText('passed')).toBeTruthy();
  });

  it('shows validation checks', async () => {
    const { exchangeHardeningApi } = await import('@/api/exchangeHardening');
    vi.mocked(exchangeHardeningApi.validateImport).mockResolvedValue({
      id: 'report-2',
      import_receipt_id: 'receipt-2',
      schema_valid: true,
      contract_valid: false,
      version_valid: true,
      hash_valid: true,
      identity_safe: false,
      validation_errors: [{ check: 'contract', message: 'Too short', severity: 'error' }],
      overall_status: 'failed',
      validated_at: '2026-03-25T10:00:00Z',
      validated_by_user_id: null,
      created_at: '2026-03-25T10:00:00Z',
    });

    renderWithQuery(<AdminImportReview />);
    fireEvent.change(screen.getByTestId('receipt-id-input'), { target: { value: 'receipt-2' } });
    fireEvent.click(screen.getByTestId('validate-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('validation-errors')).toBeTruthy();
    });
    expect(screen.getByText('Too short')).toBeTruthy();
  });

  it('renders approve and reject buttons after validation', async () => {
    const { exchangeHardeningApi } = await import('@/api/exchangeHardening');
    vi.mocked(exchangeHardeningApi.validateImport).mockResolvedValue({
      id: 'r-3',
      import_receipt_id: 'rec-3',
      schema_valid: true,
      contract_valid: true,
      version_valid: true,
      hash_valid: true,
      identity_safe: true,
      validation_errors: null,
      overall_status: 'passed',
      validated_at: '2026-03-25',
      validated_by_user_id: null,
      created_at: '2026-03-25',
    });

    renderWithQuery(<AdminImportReview />);
    fireEvent.change(screen.getByTestId('receipt-id-input'), { target: { value: 'rec-3' } });
    fireEvent.click(screen.getByTestId('validate-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('approve-btn')).toBeTruthy();
      expect(screen.getByTestId('reject-btn')).toBeTruthy();
      expect(screen.getByTestId('integrate-btn')).toBeTruthy();
    });
  });
});
