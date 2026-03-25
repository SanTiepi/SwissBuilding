import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import RemediationIntelligence from '@/pages/RemediationIntelligence';

vi.mock('@/api/remediationIntelligence', () => ({
  remediationIntelligenceApi: {
    getRemediationBenchmark: vi.fn().mockResolvedValue({
      org_id: 'org-1',
      benchmarks: [
        { pollutant: 'asbestos_removal', avg_cost_chf: 45000, avg_cycle_days: 30, completion_rate: 0.85, sample_size: 10 },
      ],
      overall_avg_cost_chf: 45000,
      overall_avg_cycle_days: 30,
      overall_completion_rate: 0.85,
      generated_at: '2026-03-25T10:00:00Z',
    }),
    getFlywheelTrends: vi.fn().mockResolvedValue([
      { date: '2026-W10', extraction_quality: 0.82, correction_rate: 0.15, cycle_time_days: null, knowledge_density: 0.6 },
      { date: '2026-W11', extraction_quality: 0.85, correction_rate: 0.12, cycle_time_days: null, knowledge_density: 0.65 },
    ]),
    getModuleLearningOverview: vi.fn().mockResolvedValue({
      total_patterns: 15,
      extraction_success_rate: 0.92,
      avg_confidence: 0.83,
      top_correction_categories: [{ category: 'extraction', count: 5 }],
      total_extractions: 100,
      total_feedbacks: 30,
    }),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'u-1', role: 'admin', organization_id: 'org-1' },
  }),
}));

describe('RemediationIntelligence Page', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    vi.clearAllMocks();
  });

  const renderPage = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <RemediationIntelligence />
        </MemoryRouter>
      </QueryClientProvider>,
    );

  it('renders page title', () => {
    renderPage();
    expect(screen.getByText('intelligence.title')).toBeTruthy();
  });

  it('renders benchmark card', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Remediation Benchmark')).toBeTruthy();
    });
  });

  it('shows overall stats', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Remediation Benchmark')).toBeTruthy();
      expect(screen.getAllByText(/45.*000/).length).toBeGreaterThan(0);
    });
  });

  it('renders flywheel trends', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Flywheel Trends')).toBeTruthy();
    });
  });

  it('renders learning overview for admin', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Module Learning Overview')).toBeTruthy();
    });
  });

  it('shows pattern count', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('15')).toBeTruthy(); // total patterns
    });
  });
});
