import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import SafeToXCockpit from '@/pages/SafeToXCockpit';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/hooks/useBuildings', () => ({
  useBuilding: () => ({
    data: { address: 'Rue du Test 1' },
  }),
}));

const mockEvaluateAll = vi.fn();
vi.mock('@/api/transactionReadiness', () => ({
  transactionReadinessApi: {
    evaluateAll: (...args: unknown[]) => mockEvaluateAll(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter
        initialEntries={['/buildings/b1/safe-to-x']}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/buildings/:buildingId/safe-to-x" element={children} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('SafeToXCockpit', () => {
  beforeEach(() => {
    mockEvaluateAll.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when transaction readiness fails to load', async () => {
    mockEvaluateAll.mockRejectedValue(new Error('boom'));

    render(<SafeToXCockpit />, { wrapper });

    expect(await screen.findByText('safe_to.error')).toBeInTheDocument();
  });

  it('renders readiness cards when assessments load', async () => {
    mockEvaluateAll.mockResolvedValue([
      {
        building_id: 'b1',
        transaction_type: 'sell',
        overall_status: 'ready',
        score: 0.9,
        checks: [{ label: 'Documents complete', passed: true, details: null }],
        blockers: [],
        conditions: [],
        recommendations: [],
        evaluated_at: '2026-03-08T00:00:00Z',
      },
    ]);

    render(<SafeToXCockpit />, { wrapper });

    expect(await screen.findByText('safe_to.sell')).toBeInTheDocument();
    expect(screen.getByText('90%')).toBeInTheDocument();
    expect(screen.getByText('safe_to.ready')).toBeInTheDocument();
  });
});
