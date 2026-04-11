import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import FlywheelDashboard from '@/components/FlywheelDashboard';

vi.mock('@/api/flywheel', () => ({
  flywheelApi: {
    getDashboard: vi.fn(),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        'flywheel.title': 'Flywheel Learning',
        'flywheel.accuracy': 'Classification accuracy',
        'flywheel.extraction_accuracy': 'Extraction accuracy',
        'flywheel.total_processed': 'Total processed',
        'flywheel.correction_rate': 'Correction rate',
        'flywheel.corrections': 'Corrections',
        'flywheel.confusion': 'Top confusion pairs',
        'flywheel.learned_rules': 'Learned rules',
        'flywheel.trend_improving': 'Improving',
        'flywheel.trend_stable': 'Stable',
        'flywheel.trend_declining': 'Declining',
        'common.loading': 'Loading...',
        'common.no_data': 'No data yet',
      };
      return map[key] || key;
    },
  }),
}));

import { flywheelApi } from '@/api/flywheel';

const mockDashboard = {
  classification_accuracy: 0.85,
  extraction_accuracy: 0.92,
  total_documents_processed: 120,
  total_corrections: 15,
  correction_rate: 0.125,
  top_confusion_pairs: [
    { predicted: 'pcb_report', actual: 'lead_report', count: 4 },
  ],
  learned_rules_count: 1,
  learned_rules: [
    {
      predicted_type: 'pcb_report',
      corrected_type: 'lead_report',
      occurrence_count: 7,
      confidence: 0.47,
      suggestion: "Documents classified as 'pcb_report' are frequently corrected to 'lead_report' (7 times).",
    },
  ],
  improvement_trend: 'improving',
};

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('FlywheelDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders metrics when data is available', async () => {
    vi.mocked(flywheelApi.getDashboard).mockResolvedValue(mockDashboard);

    renderWithProviders(<FlywheelDashboard />);

    await waitFor(() => {
      expect(screen.getByTestId('flywheel-dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('92%')).toBeInTheDocument();
    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText('13%')).toBeInTheDocument();
  });

  it('renders empty state when no data', async () => {
    vi.mocked(flywheelApi.getDashboard).mockRejectedValue(new Error('No data'));

    renderWithProviders(<FlywheelDashboard />);

    await waitFor(() => {
      expect(screen.getByTestId('flywheel-empty')).toBeInTheDocument();
    });
  });

  it('shows improving trend indicator', async () => {
    vi.mocked(flywheelApi.getDashboard).mockResolvedValue(mockDashboard);

    renderWithProviders(<FlywheelDashboard />);

    await waitFor(() => {
      expect(screen.getByTestId('trend-improving')).toBeInTheDocument();
    });
  });

  it('shows stable trend indicator', async () => {
    vi.mocked(flywheelApi.getDashboard).mockResolvedValue({
      ...mockDashboard,
      improvement_trend: 'stable',
    });

    renderWithProviders(<FlywheelDashboard />);

    await waitFor(() => {
      expect(screen.getByTestId('trend-stable')).toBeInTheDocument();
    });
  });

  it('renders learned rules', async () => {
    vi.mocked(flywheelApi.getDashboard).mockResolvedValue(mockDashboard);

    renderWithProviders(<FlywheelDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/frequently corrected/)).toBeInTheDocument();
    });
  });

  it('renders confusion pairs', async () => {
    vi.mocked(flywheelApi.getDashboard).mockResolvedValue(mockDashboard);

    renderWithProviders(<FlywheelDashboard />);

    await waitFor(() => {
      expect(screen.getByText('pcb_report')).toBeInTheDocument();
      expect(screen.getByText('lead_report')).toBeInTheDocument();
    });
  });
});
