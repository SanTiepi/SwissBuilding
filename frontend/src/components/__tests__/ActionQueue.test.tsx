import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGetQueue = vi.fn();
const mockGetWeeklySummary = vi.fn();
vi.mock('@/api/actionQueue', () => ({
  actionQueueApi: {
    getQueue: (...args: unknown[]) => mockGetQueue(...args),
    getWeeklySummary: (...args: unknown[]) => mockGetWeeklySummary(...args),
    complete: vi.fn(),
    snooze: vi.fn(),
  },
}));

// Import after mocks
const { ActionQueue } = await import('../building-detail/ActionQueue');

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const emptyResponse = {
  building_id: 'b1',
  summary: { overdue: 0, this_week: 0, this_month: 0, backlog: 0, snoozed: 0, total: 0 },
  overdue: [],
  this_week: [],
  this_month: [],
  backlog: [],
  snoozed: [],
};

const populatedResponse = {
  building_id: 'b1',
  summary: { overdue: 1, this_week: 1, this_month: 0, backlog: 1, snoozed: 0, total: 3 },
  overdue: [
    {
      id: 'a1',
      title: 'Diagnostic expire',
      description: null,
      priority: 'critical',
      status: 'open',
      source_type: 'diagnostic',
      action_type: 'review',
      deadline: '2026-03-01',
      linked_entity: null,
      suggested_resolution: 'Renouveler',
      estimated_effort: 'medium' as const,
      created_at: null,
      completed_at: null,
      snoozed_until: null,
      metadata_json: null,
    },
  ],
  this_week: [
    {
      id: 'a2',
      title: 'Upload document',
      description: null,
      priority: 'medium',
      status: 'open',
      source_type: 'document',
      action_type: 'upload',
      deadline: null,
      linked_entity: null,
      suggested_resolution: 'Telecharger',
      estimated_effort: 'quick' as const,
      created_at: null,
      completed_at: null,
      snoozed_until: null,
      metadata_json: null,
    },
  ],
  this_month: [],
  backlog: [
    {
      id: 'a3',
      title: 'Low priority cleanup',
      description: null,
      priority: 'low',
      status: 'open',
      source_type: 'manual',
      action_type: 'review',
      deadline: null,
      linked_entity: null,
      suggested_resolution: 'Nettoyer',
      estimated_effort: 'heavy' as const,
      created_at: null,
      completed_at: null,
      snoozed_until: null,
      metadata_json: null,
    },
  ],
  snoozed: [],
};

describe('ActionQueue', () => {
  beforeEach(() => {
    mockGetQueue.mockReset();
    mockGetWeeklySummary.mockReset();
    mockGetWeeklySummary.mockResolvedValue(null);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders summary bar with urgency counts', async () => {
    mockGetQueue.mockResolvedValue(populatedResponse);
    render(<ActionQueue buildingId="b1" />, { wrapper });

    // Wait for actual action title to appear (proves data loaded, not skeleton)
    expect(await screen.findByText('Diagnostic expire')).toBeInTheDocument();
    // Total badge in header
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('shows empty state when no actions', async () => {
    mockGetQueue.mockResolvedValue(emptyResponse);
    render(<ActionQueue buildingId="b1" />, { wrapper });

    expect(await screen.findByText('Aucune action en attente')).toBeInTheDocument();
  });

  it('renders urgency group labels', async () => {
    mockGetQueue.mockResolvedValue(populatedResponse);
    render(<ActionQueue buildingId="b1" />, { wrapper });

    // Wait for actual action to appear (proves data loaded)
    await screen.findByText('Diagnostic expire');
    // Labels appear in both summary bar and urgency group headers
    const overdueLabels = screen.getAllByText('En retard');
    expect(overdueLabels.length).toBeGreaterThanOrEqual(2);
    const weekLabels = screen.getAllByText('Cette semaine');
    expect(weekLabels.length).toBeGreaterThanOrEqual(2);
    const backlogLabels = screen.getAllByText('Backlog');
    expect(backlogLabels.length).toBeGreaterThanOrEqual(2);
  });

  it('shows action titles within groups', async () => {
    mockGetQueue.mockResolvedValue(populatedResponse);
    render(<ActionQueue buildingId="b1" />, { wrapper });

    expect(await screen.findByText('Diagnostic expire')).toBeInTheDocument();
    expect(screen.getByText('Upload document')).toBeInTheDocument();
    expect(screen.getByText('Low priority cleanup')).toBeInTheDocument();
  });

  it('shows error state when API fails', async () => {
    mockGetQueue.mockRejectedValue(new Error('boom'));
    render(<ActionQueue buildingId="b1" />, { wrapper });

    expect(await screen.findByText('common.error')).toBeInTheDocument();
  });
});
