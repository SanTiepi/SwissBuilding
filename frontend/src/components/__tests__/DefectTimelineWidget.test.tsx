import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
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

const MOCK_DEFECTS: DefectTimeline[] = [
  {
    id: 'd-1',
    building_id: 'b-1',
    defect_type: 'construction',
    description: 'Fissure mur porteur',
    discovery_date: '2026-03-01',
    purchase_date: '2025-01-01',
    notification_deadline: '2026-04-30',
    guarantee_type: 'standard',
    status: 'active',
    days_remaining: 10,
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-01T00:00:00Z',
  },
  {
    id: 'd-2',
    building_id: 'b-1',
    defect_type: 'pollutant',
    description: 'Amiante detecte dans isolation',
    discovery_date: '2026-02-01',
    purchase_date: '2025-01-01',
    notification_deadline: '2026-06-01',
    guarantee_type: 'standard',
    status: 'notified',
    days_remaining: 50,
    created_at: '2026-02-01T00:00:00Z',
    updated_at: '2026-03-15T00:00:00Z',
  },
  {
    id: 'd-3',
    building_id: 'b-1',
    defect_type: 'structural',
    description: 'Defaut resolu',
    discovery_date: '2025-12-01',
    purchase_date: '2025-01-01',
    notification_deadline: '2026-01-30',
    guarantee_type: 'standard',
    status: 'resolved',
    days_remaining: undefined,
    created_at: '2025-12-01T00:00:00Z',
    updated_at: '2026-01-20T00:00:00Z',
  },
];

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('DefectTimelineWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(defectTimelineApi.list).mockResolvedValue(MOCK_DEFECTS);
    vi.mocked(defectTimelineApi.create).mockResolvedValue(MOCK_DEFECTS[0]);
    vi.mocked(defectTimelineApi.update).mockResolvedValue({ ...MOCK_DEFECTS[0], status: 'notified' });
    vi.mocked(defectTimelineApi.delete).mockResolvedValue(undefined);
    vi.mocked(defectTimelineApi.generateLetter).mockResolvedValue(new Blob(['pdf'], { type: 'application/pdf' }));
  });

  it('renders the widget with title', async () => {
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('defect-timeline-widget')).toBeInTheDocument();
      expect(screen.getByText('defect.title')).toBeInTheDocument();
    });
  });

  it('renders defect list with status badges and urgency', async () => {
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      const items = screen.getAllByTestId('defect-item');
      expect(items.length).toBe(2); // active + notified shown in active section
    });
    expect(screen.getAllByTestId('defect-status-badge').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByTestId('defect-countdown-badge').length).toBeGreaterThanOrEqual(1);
  });

  it('shows urgent count badge when defects < 30 days', async () => {
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('defect-urgent-count')).toBeInTheDocument();
      expect(screen.getByTestId('defect-urgent-count').textContent).toBe('1');
    });
  });

  it('shows active and resolved sections', async () => {
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('defect-active-section')).toBeInTheDocument();
      expect(screen.getByTestId('defect-resolved-section')).toBeInTheDocument();
    });
  });

  it('opens create form when clicking add button', async () => {
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('defect-add-btn')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('defect-add-btn'));
    expect(screen.getByTestId('defect-add-form')).toBeInTheDocument();
    expect(screen.getByTestId('defect-type-select')).toBeInTheDocument();
    expect(screen.getByTestId('defect-description-input')).toBeInTheDocument();
    expect(screen.getByTestId('defect-discovery-date-input')).toBeInTheDocument();
    expect(screen.getByTestId('defect-purchase-date-input')).toBeInTheDocument();
  });

  it('submits create form and calls API', async () => {
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => screen.getByTestId('defect-add-btn'));
    fireEvent.click(screen.getByTestId('defect-add-btn'));

    fireEvent.change(screen.getByTestId('defect-description-input'), { target: { value: 'Test defect' } });
    fireEvent.change(screen.getByTestId('defect-discovery-date-input'), { target: { value: '2026-03-15' } });
    fireEvent.change(screen.getByTestId('defect-purchase-date-input'), { target: { value: '2025-06-01' } });
    fireEvent.click(screen.getByTestId('defect-submit-btn'));

    await waitFor(() => {
      expect(defectTimelineApi.create).toHaveBeenCalledWith('b-1', {
        defect_type: 'construction',
        description: 'Test defect',
        discovery_date: '2026-03-15',
        purchase_date: '2025-06-01',
      });
    });
  });

  it('cancels create form', async () => {
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => screen.getByTestId('defect-add-btn'));
    fireEvent.click(screen.getByTestId('defect-add-btn'));
    expect(screen.getByTestId('defect-add-form')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('defect-cancel-btn'));
    expect(screen.queryByTestId('defect-add-form')).not.toBeInTheDocument();
  });

  it('renders status transition dropdown for active defects', async () => {
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getAllByTestId('defect-status-select').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('calls update API on status change', async () => {
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => screen.getAllByTestId('defect-status-select'));

    const select = screen.getAllByTestId('defect-status-select')[0];
    fireEvent.change(select, { target: { value: 'notified' } });

    await waitFor(() => {
      expect(defectTimelineApi.update).toHaveBeenCalledWith('d-1', { status: 'notified' });
    });
  });

  it('renders generate letter button for active defects', async () => {
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getAllByTestId('defect-letter-btn').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('calls generate letter API on click', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).URL.createObjectURL = vi.fn().mockReturnValue('blob:test');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).URL.revokeObjectURL = vi.fn();

    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => screen.getAllByTestId('defect-letter-btn'));

    fireEvent.click(screen.getAllByTestId('defect-letter-btn')[0]);

    await waitFor(() => {
      expect(defectTimelineApi.generateLetter).toHaveBeenCalledWith('d-1');
    });
  });

  it('shows delete confirmation on click', async () => {
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => screen.getAllByTestId('defect-delete-btn'));

    fireEvent.click(screen.getAllByTestId('defect-delete-btn')[0]);
    expect(screen.getByTestId('defect-confirm-delete-btn')).toBeInTheDocument();
    expect(screen.getByTestId('defect-cancel-delete-btn')).toBeInTheDocument();
  });

  it('calls delete API on confirm', async () => {
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => screen.getAllByTestId('defect-delete-btn'));

    fireEvent.click(screen.getAllByTestId('defect-delete-btn')[0]);
    fireEvent.click(screen.getByTestId('defect-confirm-delete-btn'));

    await waitFor(() => {
      expect(defectTimelineApi.delete).toHaveBeenCalledWith('d-1');
    });
  });

  it('cancels delete on cancel button', async () => {
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => screen.getAllByTestId('defect-delete-btn'));

    fireEvent.click(screen.getAllByTestId('defect-delete-btn')[0]);
    expect(screen.getByTestId('defect-confirm-delete-btn')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('defect-cancel-delete-btn'));
    expect(screen.queryByTestId('defect-confirm-delete-btn')).not.toBeInTheDocument();
  });

  it('renders loading state', () => {
    vi.mocked(defectTimelineApi.list).mockReturnValue(new Promise(() => {}));
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    expect(screen.getByTestId('defect-loading')).toBeInTheDocument();
  });

  it('renders error state', async () => {
    vi.mocked(defectTimelineApi.list).mockRejectedValue(new Error('fail'));
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('defect-error')).toBeInTheDocument();
    });
  });

  it('renders empty state when no defects', async () => {
    vi.mocked(defectTimelineApi.list).mockResolvedValue([]);
    render(<DefectTimelineWidget buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('defect-empty')).toBeInTheDocument();
    });
  });
});
