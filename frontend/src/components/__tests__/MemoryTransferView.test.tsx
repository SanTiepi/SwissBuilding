import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { MemoryTransfer } from '@/api/intelligence';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGetContinuityScore = vi.fn();
const mockGetTransferReadiness = vi.fn();
const mockGetTransferHistory = vi.fn();
const mockInitiateTransfer = vi.fn();
vi.mock('@/api/intelligence', () => ({
  intelligenceApi: {
    getContinuityScore: (...args: unknown[]) => mockGetContinuityScore(...args),
    getTransferReadiness: (...args: unknown[]) => mockGetTransferReadiness(...args),
    getTransferHistory: (...args: unknown[]) => mockGetTransferHistory(...args),
    initiateTransfer: (...args: unknown[]) => mockInitiateTransfer(...args),
  },
}));

import MemoryTransferView from '../building-detail/MemoryTransferView';

function makeTransfer(overrides: Partial<MemoryTransfer> = {}): MemoryTransfer {
  return {
    id: 'tr-1',
    building_id: 'b-1',
    transfer_type: 'sale',
    transfer_label: 'Vente Q1 2026',
    status: 'completed',
    from_org_id: 'org-1',
    to_org_id: 'org-2',
    sections_count: 11,
    documents_count: 24,
    engagements_count: 8,
    timeline_events_count: 45,
    integrity_verified: true,
    initiated_at: '2026-01-15T00:00:00Z',
    completed_at: '2026-02-01T00:00:00Z',
    ...overrides,
  };
}

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('MemoryTransferView', () => {
  it('shows continuity score gauge', async () => {
    mockGetContinuityScore.mockResolvedValue({
      building_id: 'b-1',
      score: 85,
      transfers_completed: 2,
      gaps: 0,
      coverage_pct: 90,
      integrity_pct: 95,
    });
    mockGetTransferReadiness.mockResolvedValue({
      building_id: 'b-1',
      ready: true,
      missing_sections: [],
      open_gates: 0,
      incomplete_engagements: [],
      documents_without_hash: 0,
    });
    mockGetTransferHistory.mockResolvedValue([]);
    wrap(<MemoryTransferView buildingId="b-1" />);

    const view = await screen.findByTestId('memory-transfer-view');
    expect(view).toBeInTheDocument();
    // Continuity score displayed
    expect(screen.getByText('85')).toBeInTheDocument();
  });

  it('shows transfer readiness checklist with missing items', async () => {
    mockGetContinuityScore.mockResolvedValue({
      building_id: 'b-1',
      score: 40,
      transfers_completed: 0,
      gaps: 2,
      coverage_pct: 50,
      integrity_pct: 60,
    });
    mockGetTransferReadiness.mockResolvedValue({
      building_id: 'b-1',
      ready: false,
      missing_sections: ['Diagnostics', 'Plans'],
      open_gates: 1,
      incomplete_engagements: ['eng-1'],
      documents_without_hash: 3,
    });
    mockGetTransferHistory.mockResolvedValue([]);
    wrap(<MemoryTransferView buildingId="b-1" />);

    await screen.findByTestId('memory-transfer-view');
    expect(screen.getByText('memory_transfer.not_ready')).toBeInTheDocument();
    expect(screen.getByText('Diagnostics')).toBeInTheDocument();
    expect(screen.getByText('Plans')).toBeInTheDocument();
  });

  it('shows transfer history when transfers exist', async () => {
    mockGetContinuityScore.mockResolvedValue({
      building_id: 'b-1',
      score: 85,
      transfers_completed: 1,
      gaps: 0,
      coverage_pct: 90,
      integrity_pct: 95,
    });
    mockGetTransferReadiness.mockResolvedValue({
      building_id: 'b-1',
      ready: true,
      missing_sections: [],
      open_gates: 0,
      incomplete_engagements: [],
      documents_without_hash: 0,
    });
    mockGetTransferHistory.mockResolvedValue([makeTransfer()]);
    wrap(<MemoryTransferView buildingId="b-1" />);

    await screen.findByTestId('memory-transfer-view');
    expect(screen.getByTestId('transfer-tr-1')).toBeInTheDocument();
    expect(screen.getByText('Vente Q1 2026')).toBeInTheDocument();
  });
});
