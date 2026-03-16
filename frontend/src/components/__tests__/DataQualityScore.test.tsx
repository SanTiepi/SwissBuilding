import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DataQualityScore } from '../DataQualityScore';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGet = vi.fn();
vi.mock('@/api/quality', () => ({
  qualityApi: { get: (...args: unknown[]) => mockGet(...args) },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const qualityData = {
  overall_score: 0.75,
  sections: {
    identification: { score: 0.9, details: '' },
    diagnostics: { score: 0.6, details: '' },
    documents: { score: 0.4, details: '' },
  },
  missing: ['floor_plan', 'asbestos_report', 'pcb_analysis', 'lead_test'],
};

describe('DataQualityScore', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders loading skeleton when data is loading', async () => {
    mockGet.mockReturnValue(new Promise(() => {})); // never resolves
    const { container } = render(<DataQualityScore buildingId="b1" />, { wrapper });
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders overall score as percentage', async () => {
    mockGet.mockResolvedValue(qualityData);
    render(<DataQualityScore buildingId="b1" />, { wrapper });
    expect(await screen.findByText('75%')).toBeInTheDocument();
  });

  it('shows green color for score >= 80%', async () => {
    mockGet.mockResolvedValue({ ...qualityData, overall_score: 0.85 });
    render(<DataQualityScore buildingId="b1" />, { wrapper });
    const score = await screen.findByText('85%');
    expect(score.className).toContain('text-green-600');
  });

  it('shows yellow color for score >= 50% but < 80%', async () => {
    mockGet.mockResolvedValue({ ...qualityData, overall_score: 0.65 });
    render(<DataQualityScore buildingId="b1" />, { wrapper });
    const score = await screen.findByText('65%');
    expect(score.className).toContain('text-yellow-600');
  });

  it('shows red color for score < 50%', async () => {
    mockGet.mockResolvedValue({ ...qualityData, overall_score: 0.3 });
    render(<DataQualityScore buildingId="b1" />, { wrapper });
    const score = await screen.findByText('30%');
    expect(score.className).toContain('text-red-600');
  });

  it('renders section details with scores', async () => {
    mockGet.mockResolvedValue(qualityData);
    render(<DataQualityScore buildingId="b1" />, { wrapper });
    expect(await screen.findByText('90%')).toBeInTheDocument();
    expect(screen.getByText('60%')).toBeInTheDocument();
    expect(screen.getByText('40%')).toBeInTheDocument();
    expect(screen.getByText('quality.section.identification')).toBeInTheDocument();
    expect(screen.getByText('quality.section.diagnostics')).toBeInTheDocument();
    expect(screen.getByText('quality.section.documents')).toBeInTheDocument();
  });

  it('shows missing items when quality.missing has entries', async () => {
    mockGet.mockResolvedValue(qualityData);
    render(<DataQualityScore buildingId="b1" />, { wrapper });
    // Shows first 3 + count of remaining
    expect(await screen.findByText(/quality\.missing/)).toBeInTheDocument();
    expect(screen.getByText(/\+1/)).toBeInTheDocument();
  });

  it('renders null when no data', async () => {
    mockGet.mockResolvedValue(null);
    const { container } = render(<DataQualityScore buildingId="b1" />, { wrapper });
    // Wait for loading to finish
    await waitFor(() => {
      expect(container.querySelector('.animate-pulse')).not.toBeInTheDocument();
    });
    expect(container.innerHTML).toBe('');
  });

  it('renders explicit error state when API fails', async () => {
    mockGet.mockRejectedValue(new Error('boom'));
    render(<DataQualityScore buildingId="b1" />, { wrapper });

    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('SVG circle progress renders correctly', async () => {
    mockGet.mockResolvedValue(qualityData);
    render(<DataQualityScore buildingId="b1" />, { wrapper });
    await screen.findByText('75%');
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
    // Only count circles within the progress SVG (lucide icons also have circles)
    const circles = svg!.querySelectorAll('circle');
    expect(circles).toHaveLength(2);
    // Second circle has strokeDasharray set
    expect(circles[1]).toHaveAttribute('stroke-dasharray');
  });
});
