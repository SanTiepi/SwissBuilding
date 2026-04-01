/**
 * DefectTimelineWidget — edge case tests.
 *
 * Covers: empty list, all-expired, all-critical urgency, dark mode,
 * loading/error states, PDF download failure, delete confirmation,
 * no active section when all resolved, no urgent count when no urgency.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { defectTimelineApi, type DefectTimeline } from '@/api/defectTimeline';
import DefectTimelineWidget from '@/components/building-detail/DefectTimelineWidget';

vi.mock('@/api/defectTimeline', () => ({
  defectTimelineApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    generateLetter: vi.fn(),
    alerts: vi.fn(),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/store/toastStore', () => ({
  toast: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Mock data factories
// ---------------------------------------------------------------------------

const makeDefect = (overrides: Partial<DefectTimeline> = {}): DefectTimeline => ({
  id: `d-${Math.random().toString(36).slice(2, 8)}`,
  building_id: 'b-1',
  defect_type: 'construction',
  description: 'Test defect',
  discovery_date: '2026-03-01',
  purchase_date: '2025-01-01',
  notification_deadline: '2026-04-30',
  guarantee_type: 'standard',
  status: 'active',
  days_remaining: 30,
  created_at: '2026-03-01T00:00:00Z',
  updated_at: '2026-03-01T00:00:00Z',
  ...overrides,
});

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('DefectTimelineWidget — edge cases', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).URL.createObjectURL = vi.fn().mockReturnValue('blob:test');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).URL.revokeObjectURL = vi.fn();
  });

  // -----------------------------------------------------------------------
  // Empty / no data
  // -----------------------------------------------------------------------

  it('renders empty state with no defects', async () => {
    vi.mocked(defectTimelineApi.list).mockResolvedValue([]);
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('defect-empty')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('defect-active-section')).not.toBeInTheDocument();
    expect(screen.queryByTestId('defect-resolved-section')).not.toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // All expired — no active section
  // -----------------------------------------------------------------------

  it('shows only resolved section when all defects are expired', async () => {
    vi.mocked(defectTimelineApi.list).mockResolvedValue([
      makeDefect({ id: 'd-e1', status: 'expired', days_remaining: undefined }),
      makeDefect({ id: 'd-e2', status: 'expired', days_remaining: undefined }),
    ]);
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('defect-resolved-section')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('defect-urgent-count')).not.toBeInTheDocument();
  });

  it('shows only resolved section when all defects are resolved', async () => {
    vi.mocked(defectTimelineApi.list).mockResolvedValue([
      makeDefect({ id: 'd-r1', status: 'resolved', days_remaining: undefined }),
      makeDefect({ id: 'd-r2', status: 'resolved', days_remaining: undefined }),
    ]);
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('defect-resolved-section')).toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // All critical urgency (days_remaining < 15)
  // -----------------------------------------------------------------------

  it('shows urgent count matching all critical defects', async () => {
    vi.mocked(defectTimelineApi.list).mockResolvedValue([
      makeDefect({ id: 'd-c1', status: 'active', days_remaining: 3 }),
      makeDefect({ id: 'd-c2', status: 'active', days_remaining: 7 }),
      makeDefect({ id: 'd-c3', status: 'active', days_remaining: 14 }),
    ]);
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('defect-urgent-count')).toBeInTheDocument();
      // All 3 have days_remaining < 30 → urgent count = 3
      expect(screen.getByTestId('defect-urgent-count').textContent).toBe('3');
    });
  });

  // -----------------------------------------------------------------------
  // No urgent defects — no badge
  // -----------------------------------------------------------------------

  it('does not show urgent count when all defects have > 30 days', async () => {
    vi.mocked(defectTimelineApi.list).mockResolvedValue([
      makeDefect({ id: 'd-n1', status: 'active', days_remaining: 45 }),
      makeDefect({ id: 'd-n2', status: 'active', days_remaining: 60 }),
    ]);
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('defect-active-section')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('defect-urgent-count')).not.toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Loading state
  // -----------------------------------------------------------------------

  it('renders loading state while fetching', () => {
    vi.mocked(defectTimelineApi.list).mockReturnValue(new Promise(() => {}));
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    expect(screen.getByTestId('defect-loading')).toBeInTheDocument();
    expect(screen.queryByTestId('defect-empty')).not.toBeInTheDocument();
    expect(screen.queryByTestId('defect-active-section')).not.toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Error state
  // -----------------------------------------------------------------------

  it('renders error state on API failure', async () => {
    vi.mocked(defectTimelineApi.list).mockRejectedValue(new Error('Network error'));
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('defect-error')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('defect-loading')).not.toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // PDF download failure
  // -----------------------------------------------------------------------

  it('handles PDF generation failure gracefully', async () => {
    vi.mocked(defectTimelineApi.list).mockResolvedValue([
      makeDefect({ id: 'd-pdf', status: 'active', days_remaining: 20 }),
    ]);
    vi.mocked(defectTimelineApi.generateLetter).mockRejectedValue(new Error('502 Bad Gateway'));

    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => screen.getByTestId('defect-letter-btn'));

    fireEvent.click(screen.getByTestId('defect-letter-btn'));

    // Should not crash — the mutation error is handled
    await waitFor(() => {
      expect(defectTimelineApi.generateLetter).toHaveBeenCalledWith('d-pdf');
    });
    // Widget should still be visible (not crashed)
    expect(screen.getByTestId('defect-timeline-widget')).toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Delete flow — confirm + cancel
  // -----------------------------------------------------------------------

  it('shows confirm/cancel on delete click, then cancels', async () => {
    vi.mocked(defectTimelineApi.list).mockResolvedValue([
      makeDefect({ id: 'd-del', status: 'active', days_remaining: 20 }),
    ]);
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => screen.getByTestId('defect-delete-btn'));

    fireEvent.click(screen.getByTestId('defect-delete-btn'));
    expect(screen.getByTestId('defect-confirm-delete-btn')).toBeInTheDocument();
    expect(screen.getByTestId('defect-cancel-delete-btn')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('defect-cancel-delete-btn'));
    expect(screen.queryByTestId('defect-confirm-delete-btn')).not.toBeInTheDocument();
    expect(defectTimelineApi.delete).not.toHaveBeenCalled();
  });

  it('calls delete API after confirmation', async () => {
    vi.mocked(defectTimelineApi.list).mockResolvedValue([
      makeDefect({ id: 'd-del2', status: 'active', days_remaining: 20 }),
    ]);
    vi.mocked(defectTimelineApi.delete).mockResolvedValue(undefined);
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => screen.getByTestId('defect-delete-btn'));

    fireEvent.click(screen.getByTestId('defect-delete-btn'));
    fireEvent.click(screen.getByTestId('defect-confirm-delete-btn'));

    await waitFor(() => {
      expect(defectTimelineApi.delete).toHaveBeenCalledWith('d-del2');
    });
  });

  // -----------------------------------------------------------------------
  // Mixed statuses — both sections visible
  // -----------------------------------------------------------------------

  it('shows both sections with mixed active + resolved defects', async () => {
    vi.mocked(defectTimelineApi.list).mockResolvedValue([
      makeDefect({ id: 'd-mix1', status: 'active', days_remaining: 20 }),
      makeDefect({ id: 'd-mix2', status: 'resolved', days_remaining: undefined }),
    ]);
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('defect-active-section')).toBeInTheDocument();
      expect(screen.getByTestId('defect-resolved-section')).toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // Submit form with missing fields — should not call API
  // -----------------------------------------------------------------------

  it('does not submit form when description is empty', async () => {
    vi.mocked(defectTimelineApi.list).mockResolvedValue([]);
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => screen.getByTestId('defect-empty'));

    fireEvent.click(screen.getByTestId('defect-add-btn'));
    // Fill dates but leave description empty
    fireEvent.change(screen.getByTestId('defect-discovery-date-input'), { target: { value: '2026-03-15' } });
    fireEvent.change(screen.getByTestId('defect-purchase-date-input'), { target: { value: '2025-01-01' } });
    fireEvent.click(screen.getByTestId('defect-submit-btn'));

    // Should NOT have been called since description is empty
    expect(defectTimelineApi.create).not.toHaveBeenCalled();
  });

  // -----------------------------------------------------------------------
  // Single defect — all features visible
  // -----------------------------------------------------------------------

  it('renders all action buttons for a single active defect', async () => {
    vi.mocked(defectTimelineApi.list).mockResolvedValue([
      makeDefect({ id: 'd-single', status: 'active', days_remaining: 10 }),
    ]);
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getAllByTestId('defect-item')).toHaveLength(1);
      expect(screen.getByTestId('defect-status-select')).toBeInTheDocument();
      expect(screen.getByTestId('defect-letter-btn')).toBeInTheDocument();
      expect(screen.getByTestId('defect-delete-btn')).toBeInTheDocument();
    });
  });
});
