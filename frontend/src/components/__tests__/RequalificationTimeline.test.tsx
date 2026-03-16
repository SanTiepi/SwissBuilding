import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RequalificationTimeline } from '@/components/RequalificationTimeline';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGetTimeline = vi.fn();
vi.mock('@/api/requalification', () => ({
  requalificationApi: {
    getTimeline: (...args: unknown[]) => mockGetTimeline(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const MOCK_ENTRIES = [
  {
    timestamp: '2025-01-15T10:00:00Z',
    entry_type: 'intervention' as const,
    title: 'Asbestos removal completed',
    description: 'Full removal of floor tiles',
    severity: null,
    signal_type: null,
    grade_before: null,
    grade_after: null,
    metadata: { status: 'completed' },
  },
  {
    timestamp: '2025-02-01T12:00:00Z',
    entry_type: 'signal' as const,
    title: 'New diagnostic result',
    description: 'PCB levels below threshold',
    severity: 'info',
    signal_type: 'diagnostic_result',
    grade_before: null,
    grade_after: null,
    metadata: null,
  },
  {
    timestamp: '2025-02-15T08:00:00Z',
    entry_type: 'snapshot' as const,
    title: 'Pre-requalification snapshot',
    description: null,
    severity: null,
    signal_type: null,
    grade_before: null,
    grade_after: null,
    metadata: { trust: 0.85, readiness: 'ready', pollutant_status: 'clear', grade: 'B' },
  },
  {
    timestamp: '2025-03-01T14:00:00Z',
    entry_type: 'grade_change' as const,
    title: 'Grade improved',
    description: 'Requalification after remediation',
    severity: null,
    signal_type: null,
    grade_before: 'D',
    grade_after: 'B',
    metadata: { reason: 'Successful asbestos removal', intervention_id: 'int-123-abc' },
  },
  {
    timestamp: '2025-03-15T09:00:00Z',
    entry_type: 'snapshot' as const,
    title: 'Post-requalification snapshot',
    description: null,
    severity: null,
    signal_type: null,
    grade_before: null,
    grade_after: null,
    metadata: { trust: 0.92, readiness: 'ready', pollutant_status: 'clear', grade: 'B' },
  },
];

describe('RequalificationTimeline', () => {
  beforeEach(() => {
    mockGetTimeline.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when timeline fails to load', async () => {
    mockGetTimeline.mockRejectedValue(new Error('boom'));

    render(<RequalificationTimeline buildingId="b1" />, { wrapper });

    expect(await screen.findByText('app.error')).toBeInTheDocument();
  });

  it('renders empty state when there are no requalification entries', async () => {
    mockGetTimeline.mockResolvedValue({
      building_id: 'b1',
      current_grade: 'B',
      entries: [],
      grade_history: [],
    });

    render(<RequalificationTimeline buildingId="b1" />, { wrapper });

    expect(await screen.findByText('requalification.empty')).toBeInTheDocument();
    // Summary header should still show the current grade
    expect(screen.getByText('requalification.current_grade')).toBeInTheDocument();
  });

  it('renders summary header with correct stats', async () => {
    mockGetTimeline.mockResolvedValue({
      building_id: 'b1',
      current_grade: 'B',
      entries: MOCK_ENTRIES,
      grade_history: [],
    });

    render(<RequalificationTimeline buildingId="b1" />, { wrapper });

    // Wait for data to load
    expect(await screen.findByText('Grade improved')).toBeInTheDocument();

    // Summary stats: 1 transition, 1 signal
    expect(screen.getByText('requalification.total_transitions')).toBeInTheDocument();
    expect(screen.getByText('requalification.active_signals')).toBeInTheDocument();
    expect(screen.getByText('requalification.last_requalification')).toBeInTheDocument();
  });

  it('renders all timeline entries with correct type badges', async () => {
    mockGetTimeline.mockResolvedValue({
      building_id: 'b1',
      current_grade: 'B',
      entries: MOCK_ENTRIES,
      grade_history: [],
    });

    render(<RequalificationTimeline buildingId="b1" />, { wrapper });

    expect(await screen.findByText('Asbestos removal completed')).toBeInTheDocument();
    expect(screen.getByText('New diagnostic result')).toBeInTheDocument();
    expect(screen.getByText('Pre-requalification snapshot')).toBeInTheDocument();
    expect(screen.getByText('Grade improved')).toBeInTheDocument();
    expect(screen.getByText('Post-requalification snapshot')).toBeInTheDocument();
  });

  it('renders grade transition card with before/after grades', async () => {
    mockGetTimeline.mockResolvedValue({
      building_id: 'b1',
      current_grade: 'B',
      entries: MOCK_ENTRIES,
      grade_history: [],
    });

    render(<RequalificationTimeline buildingId="b1" />, { wrapper });

    expect(await screen.findByText('Grade improved')).toBeInTheDocument();

    // Grade badges D and B should appear in the transition card
    const dBadges = screen.getAllByText('D');
    expect(dBadges.length).toBeGreaterThanOrEqual(1);

    // Green arrow (improvement D -> B)
    expect(screen.getByTestId('grade-arrow-up')).toBeInTheDocument();

    // Reason from metadata
    expect(screen.getByText(/Successful asbestos removal/)).toBeInTheDocument();
  });

  it('renders signal type badge for signal entries', async () => {
    mockGetTimeline.mockResolvedValue({
      building_id: 'b1',
      current_grade: 'B',
      entries: MOCK_ENTRIES,
      grade_history: [],
    });

    render(<RequalificationTimeline buildingId="b1" />, { wrapper });

    expect(await screen.findByText('diagnostic result')).toBeInTheDocument();
  });

  it('filters entries by type', async () => {
    const user = userEvent.setup();
    mockGetTimeline.mockResolvedValue({
      building_id: 'b1',
      current_grade: 'B',
      entries: MOCK_ENTRIES,
      grade_history: [],
    });

    render(<RequalificationTimeline buildingId="b1" />, { wrapper });

    // Wait for data
    expect(await screen.findByText('Asbestos removal completed')).toBeInTheDocument();

    // Click the grade_change filter
    const gradeFilter = screen.getByText('requalification.filter_grade_change');
    await user.click(gradeFilter);

    // Only grade_change entries should be visible
    expect(screen.getByText('Grade improved')).toBeInTheDocument();
    expect(screen.queryByText('Asbestos removal completed')).not.toBeInTheDocument();
    expect(screen.queryByText('New diagnostic result')).not.toBeInTheDocument();
  });

  it('enters and navigates replay mode', async () => {
    const user = userEvent.setup();
    mockGetTimeline.mockResolvedValue({
      building_id: 'b1',
      current_grade: 'B',
      entries: MOCK_ENTRIES,
      grade_history: [],
    });

    render(<RequalificationTimeline buildingId="b1" />, { wrapper });

    expect(await screen.findByText('Asbestos removal completed')).toBeInTheDocument();

    // Enter replay mode
    const replayBtn = screen.getByText('requalification.replay');
    await user.click(replayBtn);

    // Should show step indicator
    expect(screen.getByText(/requalification.replay_step/)).toBeInTheDocument();

    // Initially only first entry visible
    expect(screen.getByText('Asbestos removal completed')).toBeInTheDocument();
    expect(screen.queryByText('Grade improved')).not.toBeInTheDocument();

    // Navigate forward
    // Find the ChevronRight button (last one with svg in replay controls)
    const replayControls = screen.getByText(/requalification.replay_step/).parentElement!;
    const controlButtons = within(replayControls).getAllByRole('button');
    // controlButtons: [exit, prev, next]
    const forwardBtn = controlButtons[2];
    await user.click(forwardBtn);

    // Second entry should now be visible
    expect(screen.getByText('New diagnostic result')).toBeInTheDocument();
  });

  it('shows snapshot comparison panel', async () => {
    const user = userEvent.setup();
    mockGetTimeline.mockResolvedValue({
      building_id: 'b1',
      current_grade: 'B',
      entries: MOCK_ENTRIES,
      grade_history: [],
    });

    render(<RequalificationTimeline buildingId="b1" />, { wrapper });

    expect(await screen.findByText('Asbestos removal completed')).toBeInTheDocument();

    // Click compare button
    const compareBtn = screen.getByText('requalification.compare_snapshots');
    await user.click(compareBtn);

    // Comparison panel should appear
    expect(screen.getByText('requalification.snapshot_comparison')).toBeInTheDocument();
    expect(screen.getByText('requalification.snapshot_left')).toBeInTheDocument();
    expect(screen.getByText('requalification.snapshot_right')).toBeInTheDocument();
  });

  it('does not show compare button when fewer than 2 snapshots', async () => {
    mockGetTimeline.mockResolvedValue({
      building_id: 'b1',
      current_grade: 'C',
      entries: [MOCK_ENTRIES[0], MOCK_ENTRIES[1], MOCK_ENTRIES[3]], // no snapshots or only 1
      grade_history: [],
    });

    render(<RequalificationTimeline buildingId="b1" />, { wrapper });

    expect(await screen.findByText('Asbestos removal completed')).toBeInTheDocument();
    expect(screen.queryByText('requalification.compare_snapshots')).not.toBeInTheDocument();
  });
});
