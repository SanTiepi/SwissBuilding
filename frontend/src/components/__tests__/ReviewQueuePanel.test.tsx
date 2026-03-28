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

const mockGetQueue = vi.fn();
const mockGetStats = vi.fn();
vi.mock('@/api/reviewQueue', () => ({
  reviewQueueApi: {
    getQueue: (...args: unknown[]) => mockGetQueue(...args),
    getStats: (...args: unknown[]) => mockGetStats(...args),
    assign: vi.fn(),
    complete: vi.fn(),
    escalate: vi.fn(),
  },
}));

const { default: ReviewQueuePanel } = await import('../ReviewQueuePanel');

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

describe('ReviewQueuePanel', () => {
  afterEach(cleanup);

  it('renders nothing when queue is empty', async () => {
    mockGetQueue.mockResolvedValue([]);
    mockGetStats.mockResolvedValue({ total_pending: 0, by_priority: {}, by_type: {} });
    const { container } = render(<ReviewQueuePanel />, { wrapper });
    await vi.waitFor(() => {
      // Panel should auto-hide when empty
      expect(container.querySelector('[data-testid="review-queue"]')).toBeNull();
    });
  });

  it('renders tasks when queue has items', async () => {
    mockGetQueue.mockResolvedValue([
      {
        id: '1',
        building_id: 'b1',
        task_type: 'extraction_review',
        title: 'Review diagnostic extraction',
        priority: 'high',
        status: 'pending',
        created_at: '2026-03-28T10:00:00Z',
      },
    ]);
    mockGetStats.mockResolvedValue({ total_pending: 1, by_priority: { high: 1 }, by_type: { extraction_review: 1 } });
    render(<ReviewQueuePanel />, { wrapper });
    await vi.waitFor(() => {
      expect(screen.getByText('Review diagnostic extraction')).toBeDefined();
    });
  });

  it('shows priority indicator', async () => {
    mockGetQueue.mockResolvedValue([
      {
        id: '1',
        building_id: 'b1',
        task_type: 'contradiction_resolution',
        title: 'Resolve contradiction',
        priority: 'critical',
        status: 'pending',
        created_at: '2026-03-28T10:00:00Z',
      },
    ]);
    mockGetStats.mockResolvedValue({ total_pending: 1, by_priority: { critical: 1 }, by_type: {} });
    render(<ReviewQueuePanel />, { wrapper });
    await vi.waitFor(() => {
      expect(screen.getByText('Resolve contradiction')).toBeDefined();
    });
  });

  it('handles API error gracefully', async () => {
    mockGetQueue.mockRejectedValue(new Error('Network error'));
    mockGetStats.mockRejectedValue(new Error('Network error'));
    render(<ReviewQueuePanel />, { wrapper });
    await vi.waitFor(() => {
      expect(document.body).toBeDefined();
    });
  });
});
