import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RecommendationList } from '../RecommendationList';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockList = vi.fn();
vi.mock('@/api/recommendations', () => ({
  recommendationsApi: {
    list: (...args: unknown[]) => mockList(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const MOCK_RECOMMENDATIONS = [
  {
    id: 'rec-1',
    priority: 1,
    category: 'remediation',
    title: 'Asbestos remediation required',
    description: 'Remove asbestos from building zones.',
    why: 'Critical health risk from asbestos exposure.',
    impact_score: 1.0,
    cost_estimate: { min: 15000, max: 80000, currency: 'CHF', confidence: 'market_data' },
    urgency_days: 7,
    source: 'action_generator',
    related_entity: { entity_type: 'action_item', entity_id: 'abc-123' },
  },
  {
    id: 'rec-2',
    priority: 3,
    category: 'documentation',
    title: 'Upload diagnostic report',
    description: 'Missing diagnostic report.',
    why: 'Required for compliance.',
    impact_score: 0.5,
    cost_estimate: null,
    urgency_days: null,
    source: 'unknown_generator',
    related_entity: null,
  },
];

describe('RecommendationList', () => {
  beforeEach(() => {
    mockList.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders title and loading state', async () => {
    mockList.mockReturnValue(new Promise(() => {})); // never resolves
    render(<RecommendationList buildingId="b1" />, { wrapper });

    expect(screen.getByText('recommendations.title')).toBeInTheDocument();
    expect(screen.getByText('app.loading')).toBeInTheDocument();
  });

  it('renders error state when API fails', async () => {
    mockList.mockRejectedValue(new Error('boom'));
    render(<RecommendationList buildingId="b1" />, { wrapper });

    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders empty state when no recommendations', async () => {
    mockList.mockResolvedValue({ building_id: 'b1', recommendations: [], total: 0 });
    render(<RecommendationList buildingId="b1" />, { wrapper });

    expect(await screen.findByText('recommendations.empty')).toBeInTheDocument();
  });

  it('renders recommendation cards with priority badges', async () => {
    mockList.mockResolvedValue({
      building_id: 'b1',
      recommendations: MOCK_RECOMMENDATIONS,
      total: 2,
    });
    render(<RecommendationList buildingId="b1" />, { wrapper });

    expect(await screen.findByText('Asbestos remediation required')).toBeInTheDocument();
    expect(screen.getByText('Upload diagnostic report')).toBeInTheDocument();
    expect(screen.getByText('recommendations.priority_critical')).toBeInTheDocument();
    expect(screen.getByText('recommendations.priority_medium')).toBeInTheDocument();
  });

  it('expands card to show why section', async () => {
    mockList.mockResolvedValue({
      building_id: 'b1',
      recommendations: [MOCK_RECOMMENDATIONS[0]],
      total: 1,
    });
    render(<RecommendationList buildingId="b1" />, { wrapper });

    await screen.findByText('Asbestos remediation required');

    // "why" text should not be visible before expand
    expect(screen.queryByText('Critical health risk from asbestos exposure.')).not.toBeInTheDocument();

    // Click expand
    const expandBtn = screen.getByLabelText('Expand');
    fireEvent.click(expandBtn);

    expect(screen.getByText('Critical health risk from asbestos exposure.')).toBeInTheDocument();
  });

  it('shows cost estimate when available', async () => {
    mockList.mockResolvedValue({
      building_id: 'b1',
      recommendations: [MOCK_RECOMMENDATIONS[0]],
      total: 1,
    });
    render(<RecommendationList buildingId="b1" />, { wrapper });

    await screen.findByText('Asbestos remediation required');

    // Expand to see cost
    const expandBtn = screen.getByLabelText('Expand');
    fireEvent.click(expandBtn);

    // Number formatting varies by locale (15,000 or 15 000)
    expect(screen.getByText(/15.000/)).toBeInTheDocument();
    expect(screen.getByText(/80.000/)).toBeInTheDocument();
  });

  it('shows urgency badge for time-bound recommendations', async () => {
    mockList.mockResolvedValue({
      building_id: 'b1',
      recommendations: [MOCK_RECOMMENDATIONS[0]],
      total: 1,
    });
    render(<RecommendationList buildingId="b1" />, { wrapper });

    await screen.findByText('Asbestos remediation required');
    // 7d urgency badge
    expect(screen.getByText(/7/)).toBeInTheDocument();
  });
});
