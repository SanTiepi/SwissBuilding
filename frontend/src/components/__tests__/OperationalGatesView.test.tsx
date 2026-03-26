import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { OperationalGate } from '@/api/intelligence';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGetBuildingGates = vi.fn();
const mockGetBuildingGateStatus = vi.fn();
const mockOverrideGate = vi.fn();
vi.mock('@/api/intelligence', () => ({
  intelligenceApi: {
    getBuildingGates: (...args: unknown[]) => mockGetBuildingGates(...args),
    getBuildingGateStatus: (...args: unknown[]) => mockGetBuildingGateStatus(...args),
    overrideGate: (...args: unknown[]) => mockOverrideGate(...args),
  },
}));

import OperationalGatesView from '../building-detail/OperationalGatesView';

function makeGate(overrides: Partial<OperationalGate> = {}): OperationalGate {
  return {
    id: 'gate-1',
    building_id: 'b-1',
    gate_type: 'launch_rfq',
    gate_label: 'Lancer appel offres',
    status: 'blocked',
    prerequisites: [
      { type: 'diagnostic', label: 'Diagnostic amiante', satisfied: false, item_id: null },
      { type: 'document', label: 'Plan cadastral', satisfied: true, item_id: 'd-1' },
    ],
    overridden_by_id: null,
    override_reason: null,
    cleared_at: null,
    ...overrides,
  };
}

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('OperationalGatesView', () => {
  it('shows gate cards when gates exist', async () => {
    mockGetBuildingGates.mockResolvedValue([makeGate(), makeGate({ id: 'gate-2', gate_type: 'close_lot' })]);
    mockGetBuildingGateStatus.mockResolvedValue({
      building_id: 'b-1',
      total_gates: 2,
      blocked: 2,
      clearable: 0,
      cleared: 0,
      overridden: 0,
    });
    wrap(<OperationalGatesView buildingId="b-1" />);

    expect(await screen.findByTestId('operational-gates-view')).toBeInTheDocument();
    expect(screen.getByTestId('gate-card-launch_rfq')).toBeInTheDocument();
    expect(screen.getByTestId('gate-card-close_lot')).toBeInTheDocument();
  });

  it('blocked gates show red status badge and prerequisite checklist', async () => {
    mockGetBuildingGates.mockResolvedValue([makeGate()]);
    mockGetBuildingGateStatus.mockResolvedValue({
      building_id: 'b-1',
      total_gates: 1,
      blocked: 1,
      clearable: 0,
      cleared: 0,
      overridden: 0,
    });
    wrap(<OperationalGatesView buildingId="b-1" />);

    const card = await screen.findByTestId('gate-card-launch_rfq');
    expect(card).toHaveTextContent('operational_gates.status_blocked');
    // Prerequisites visible
    expect(card).toHaveTextContent('Diagnostic amiante');
    expect(card).toHaveTextContent('Plan cadastral');
  });

  it('cleared gates show green status', async () => {
    const clearedGate = makeGate({
      status: 'cleared',
      cleared_at: '2026-03-01T00:00:00Z',
      prerequisites: [{ type: 'diagnostic', label: 'Diagnostic amiante', satisfied: true, item_id: 'd-1' }],
    });
    mockGetBuildingGates.mockResolvedValue([clearedGate]);
    mockGetBuildingGateStatus.mockResolvedValue({
      building_id: 'b-1',
      total_gates: 1,
      blocked: 0,
      clearable: 0,
      cleared: 1,
      overridden: 0,
    });
    wrap(<OperationalGatesView buildingId="b-1" />);

    const card = await screen.findByTestId('gate-card-launch_rfq');
    expect(card).toHaveTextContent('operational_gates.status_cleared');
  });
});
