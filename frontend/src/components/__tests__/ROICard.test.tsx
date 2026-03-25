import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { demoPilotApi } from '@/api/demoPilot';
import { ROICard } from '@/components/building-detail/ROICard';

vi.mock('@/api/demoPilot', () => ({
  demoPilotApi: {
    getBuildingROI: vi.fn().mockResolvedValue({
      building_id: 'b-1',
      time_saved_hours: 12.5,
      rework_avoided: 3,
      blocker_days_saved: 7.0,
      pack_reuse_count: 2,
      breakdown: [
        { label: 'time_saved_hours', value: 12.5, unit: 'hours', evidence_count: 8 },
        { label: 'rework_avoided', value: 3, unit: 'count', evidence_count: 3 },
        { label: 'blocker_days_saved', value: 7.0, unit: 'days', evidence_count: 5 },
        { label: 'pack_reuse_count', value: 2, unit: 'count', evidence_count: 2 },
      ],
      evidence_sources: ['diagnostics', 'actions', 'evidence_links'],
    }),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('ROICard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the ROI card with title', async () => {
    render(<ROICard buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('roi-card')).toBeInTheDocument();
      expect(screen.getByText('roi.title')).toBeInTheDocument();
    });
  });

  it('renders time saved metric', async () => {
    render(<ROICard buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('roi-metric-time_saved_hours')).toBeInTheDocument();
      expect(screen.getByText('12.5')).toBeInTheDocument();
    });
  });

  it('renders rework avoided metric', async () => {
    render(<ROICard buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('roi-metric-rework_avoided')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
    });
  });

  it('renders blocker days saved metric', async () => {
    render(<ROICard buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('roi-metric-blocker_days_saved')).toBeInTheDocument();
    });
  });

  it('renders evidence source labels', async () => {
    render(<ROICard buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('diagnostics')).toBeInTheDocument();
      expect(screen.getByText('actions')).toBeInTheDocument();
      expect(screen.getByText('evidence_links')).toBeInTheDocument();
    });
  });

  it('renders disclaimer', async () => {
    render(<ROICard buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('roi.disclaimer')).toBeInTheDocument();
    });
  });

  it('renders nothing when API errors', async () => {
    vi.mocked(demoPilotApi.getBuildingROI).mockRejectedValueOnce(new Error('fail'));
    const { container } = render(<ROICard buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      // Should be empty after error (graceful hide)
      expect(container.querySelector('[data-testid="roi-card"]')).toBeNull();
    });
  });
});
