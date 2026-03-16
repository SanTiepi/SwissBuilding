import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProofHeatmapOverlay } from '../ProofHeatmapOverlay';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGetHeatmap = vi.fn();
vi.mock('@/api/planHeatmap', () => ({
  planHeatmapApi: {
    getHeatmap: (...args: unknown[]) => mockGetHeatmap(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('ProofHeatmapOverlay', () => {
  beforeEach(() => {
    mockGetHeatmap.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders error state when API fails', async () => {
    mockGetHeatmap.mockRejectedValue(new Error('boom'));
    render(<ProofHeatmapOverlay planId="p1" imageUrl="/plan.png" />, { wrapper });

    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders empty state when there are no heatmap points', async () => {
    mockGetHeatmap.mockResolvedValue({
      plan_id: 'p1',
      building_id: 'b1',
      total_points: 0,
      coverage_score: 0.2,
      points: [],
      summary: {},
    });

    render(<ProofHeatmapOverlay planId="p1" imageUrl="/plan.png" />, { wrapper });

    expect(await screen.findByText('heatmap.no_data')).toBeInTheDocument();
  });

  it('renders legend with trust gradient when points exist', async () => {
    mockGetHeatmap.mockResolvedValue({
      plan_id: 'p1',
      building_id: 'b1',
      total_points: 2,
      coverage_score: 0.5,
      points: [
        { x: 0.3, y: 0.4, intensity: 0.8, category: 'trust', label: 'Zone A', annotation_id: 'a1', zone_id: 'z1' },
        { x: 0.6, y: 0.7, intensity: 0.5, category: 'sample', label: 'Sample 1', annotation_id: 'a2', zone_id: null },
      ],
      summary: { trust: 1, sample: 1 },
    });

    render(<ProofHeatmapOverlay planId="p1" imageUrl="/plan.png" />, { wrapper });

    expect(await screen.findByText('heatmap.legend_title')).toBeInTheDocument();
    expect(screen.getByText('heatmap.high_trust')).toBeInTheDocument();
    expect(screen.getByText('heatmap.medium_trust')).toBeInTheDocument();
    expect(screen.getByText('heatmap.low_trust')).toBeInTheDocument();
    expect(screen.getByText('heatmap.sample')).toBeInTheDocument();
  });

  it('renders contradiction marker in legend when contradictions exist', async () => {
    mockGetHeatmap.mockResolvedValue({
      plan_id: 'p1',
      building_id: 'b1',
      total_points: 1,
      coverage_score: 0.3,
      points: [
        {
          x: 0.5,
          y: 0.5,
          intensity: 0.85,
          category: 'contradiction',
          label: 'Contradiction on sample',
          annotation_id: 'a1',
          zone_id: null,
        },
      ],
      summary: { contradiction: 1 },
    });

    render(<ProofHeatmapOverlay planId="p1" imageUrl="/plan.png" />, { wrapper });

    const contradictionLabels = await screen.findAllByText('heatmap.contradiction');
    expect(contradictionLabels.length).toBeGreaterThanOrEqual(1);
  });
});
