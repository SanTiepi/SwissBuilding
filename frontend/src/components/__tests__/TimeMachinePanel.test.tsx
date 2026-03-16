import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TimeMachinePanel } from '../TimeMachinePanel';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockToast = vi.fn();
vi.mock('@/store/toastStore', () => ({
  toast: (...args: unknown[]) => mockToast(...args),
}));

const mockList = vi.fn();
const mockCapture = vi.fn();
const mockCompare = vi.fn();
const mockGet = vi.fn();
vi.mock('@/api/snapshots', () => ({
  snapshotsApi: {
    list: (...args: unknown[]) => mockList(...args),
    capture: (...args: unknown[]) => mockCapture(...args),
    compare: (...args: unknown[]) => mockCompare(...args),
    get: (...args: unknown[]) => mockGet(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const snapshots = {
  items: [
    {
      id: 's1',
      building_id: 'b1',
      snapshot_type: 'manual',
      trigger_event: null,
      passport_state_json: null,
      trust_state_json: null,
      readiness_state_json: null,
      evidence_counts_json: null,
      passport_grade: 'D',
      overall_trust: 0.5,
      completeness_score: 0.6,
      captured_at: '2026-01-01T00:00:00Z',
      captured_by: null,
      notes: null,
    },
    {
      id: 's2',
      building_id: 'b1',
      snapshot_type: 'automatic',
      trigger_event: 'intervention',
      passport_state_json: null,
      trust_state_json: null,
      readiness_state_json: null,
      evidence_counts_json: null,
      passport_grade: 'C',
      overall_trust: 0.7,
      completeness_score: 0.8,
      captured_at: '2026-02-01T00:00:00Z',
      captured_by: null,
      notes: null,
    },
  ],
  total: 2,
};

describe('TimeMachinePanel', () => {
  beforeEach(() => {
    mockList.mockReset();
    mockCapture.mockReset();
    mockCompare.mockReset();
    mockGet.mockReset();
    mockToast.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when snapshot list fails', async () => {
    mockList.mockRejectedValue(new Error('boom'));
    render(<TimeMachinePanel buildingId="b1" />, { wrapper });

    expect(await screen.findByText('app.error')).toBeInTheDocument();
  });

  it('renders empty state when no snapshots are available', async () => {
    mockList.mockResolvedValue({ items: [], total: 0 });
    render(<TimeMachinePanel buildingId="b1" />, { wrapper });

    expect(await screen.findByText('time_machine.no_snapshots')).toBeInTheDocument();
  });

  it('compares two snapshots and shows deltas', async () => {
    mockList.mockResolvedValue(snapshots);
    mockCompare.mockResolvedValue({
      building_id: 'b1',
      snapshot_a: { id: 's1', captured_at: null, passport_grade: 'D', overall_trust: 0.5, completeness_score: 0.6 },
      snapshot_b: { id: 's2', captured_at: null, passport_grade: 'C', overall_trust: 0.7, completeness_score: 0.8 },
      changes: {
        trust_delta: 0.2,
        completeness_delta: 0.2,
        grade_change: 'D -> C',
        readiness_changes: [],
        new_contradictions: 0,
        resolved_contradictions: 1,
      },
    });

    render(<TimeMachinePanel buildingId="b1" />, { wrapper });

    // Wait for snapshots to load, then find snapshot list buttons
    await screen.findByText('time_machine.select_to_compare');

    // Select both snapshots from the list (not timeline)
    const listItems = await screen.findAllByRole('button');
    // Find buttons that contain the grade badges for each snapshot in the list
    const selectButtons = listItems.filter(
      (btn) => btn.textContent && (btn.textContent.includes('01.01.2026') || btn.textContent.includes('01.02.2026')),
    );
    if (selectButtons.length >= 2) {
      fireEvent.click(selectButtons[0]);
      fireEvent.click(selectButtons[1]);
    }

    const compareBtn = await screen.findByText('time_machine.compare');
    fireEvent.click(compareBtn);

    expect(await screen.findByText('time_machine.comparison_result')).toBeInTheDocument();
    expect(screen.getAllByText('+20.0%')).toHaveLength(2);
    expect(screen.getByText('D -> C')).toBeInTheDocument();
  });

  it('toasts when compare fails', async () => {
    mockList.mockResolvedValue(snapshots);
    mockCompare.mockRejectedValue(new Error('compare failed'));

    render(<TimeMachinePanel buildingId="b1" />, { wrapper });

    await screen.findByText('time_machine.select_to_compare');

    const listItems = await screen.findAllByRole('button');
    const selectButtons = listItems.filter(
      (btn) => btn.textContent && (btn.textContent.includes('01.01.2026') || btn.textContent.includes('01.02.2026')),
    );
    if (selectButtons.length >= 2) {
      fireEvent.click(selectButtons[0]);
      fireEvent.click(selectButtons[1]);
    }

    const compareBtn = await screen.findByText('time_machine.compare');
    fireEvent.click(compareBtn);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith('compare failed');
    });
  });

  it('shows snapshot count in header', async () => {
    mockList.mockResolvedValue(snapshots);
    render(<TimeMachinePanel buildingId="b1" />, { wrapper });

    expect(await screen.findByText('(2)')).toBeInTheDocument();
  });

  it('shows current badge on latest snapshot', async () => {
    mockList.mockResolvedValue(snapshots);
    render(<TimeMachinePanel buildingId="b1" />, { wrapper });

    expect(await screen.findByText('time_machine.current')).toBeInTheDocument();
  });

  it('renders timeline with view buttons', async () => {
    mockList.mockResolvedValue(snapshots);
    render(<TimeMachinePanel buildingId="b1" />, { wrapper });

    expect(await screen.findByText('time_machine.timeline')).toBeInTheDocument();
    const viewButtons = await screen.findAllByText('time_machine.view');
    expect(viewButtons.length).toBeGreaterThanOrEqual(2);
  });

  it('opens snapshot detail on view click', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          ...snapshots.items[0],
          readiness_state_json: { safe_to_start: { status: 'ready' } },
          evidence_counts_json: { diagnostics: 3, documents: 5 },
        },
      ],
      total: 1,
    });
    render(<TimeMachinePanel buildingId="b1" />, { wrapper });

    const viewButtons = await screen.findAllByText('time_machine.view');
    fireEvent.click(viewButtons[0]);

    expect(await screen.findByText('time_machine.snapshot_detail')).toBeInTheDocument();
    expect(screen.getByText('time_machine.readiness_at_snapshot')).toBeInTheDocument();
  });

  it('shows capture form with notes input', async () => {
    mockList.mockResolvedValue({ items: [], total: 0 });
    render(<TimeMachinePanel buildingId="b1" />, { wrapper });

    const captureBtn = await screen.findByText('time_machine.capture');
    fireEvent.click(captureBtn);

    expect(screen.getByPlaceholderText('time_machine.notes_placeholder')).toBeInTheDocument();
    expect(screen.getByText('time_machine.save')).toBeInTheDocument();
  });
});
