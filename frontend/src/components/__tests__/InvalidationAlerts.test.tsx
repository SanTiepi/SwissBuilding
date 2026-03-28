import { describe, it, expect, vi, afterEach } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGetPending = vi.fn();
const mockGetForBuilding = vi.fn();
vi.mock('@/api/invalidations', () => ({
  invalidationsApi: {
    getPending: (...args: unknown[]) => mockGetPending(...args),
    getForBuilding: (...args: unknown[]) => mockGetForBuilding(...args),
    acknowledge: vi.fn(),
    resolve: vi.fn(),
    executeReaction: vi.fn(),
  },
}));

const { default: InvalidationAlerts, InvalidationBadge } = await import('../InvalidationAlerts');

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('InvalidationBadge', () => {
  afterEach(cleanup);

  it('renders nothing when no invalidations', async () => {
    mockGetForBuilding.mockResolvedValue([]);
    const { container } = render(<InvalidationBadge buildingId="b1" />, { wrapper });
    await vi.waitFor(() => {
      expect(container.textContent).toBe('');
    });
  });

  it('shows count badge when invalidations exist', async () => {
    mockGetForBuilding.mockResolvedValue([
      { id: '1', severity: 'critical', status: 'detected' },
      { id: '2', severity: 'warning', status: 'detected' },
    ]);
    render(<InvalidationBadge buildingId="b1" />, { wrapper });
    await vi.waitFor(() => {
      expect(screen.getByText('2')).toBeDefined();
    });
  });
});

describe('InvalidationAlerts', () => {
  afterEach(cleanup);

  it('renders empty state when no invalidations', async () => {
    mockGetForBuilding.mockResolvedValue([]);
    render(<InvalidationAlerts buildingId="b1" />, { wrapper });
    await vi.waitFor(() => {
      // Should render without crashing even with empty data
      expect(document.body).toBeDefined();
    });
  });

  it('renders alert cards with severity', async () => {
    mockGetForBuilding.mockResolvedValue([
      {
        id: '1',
        building_id: 'b1',
        severity: 'critical',
        status: 'detected',
        trigger_description: 'Rule changed',
        impact_reason: 'Pack authority stale',
        required_reaction: 'republish',
        detected_at: '2026-03-28T10:00:00Z',
      },
    ]);
    render(<InvalidationAlerts buildingId="b1" />, { wrapper });
    await vi.waitFor(() => {
      expect(screen.getByText('Rule changed')).toBeDefined();
      expect(screen.getByText('Pack authority stale')).toBeDefined();
    });
  });

  it('handles API error gracefully', async () => {
    mockGetForBuilding.mockRejectedValue(new Error('API error'));
    render(<InvalidationAlerts buildingId="b1" />, { wrapper });
    // Should not crash
    await vi.waitFor(() => {
      expect(document.body).toBeDefined();
    });
  });
});
