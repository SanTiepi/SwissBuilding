import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { EcosystemEngagement } from '@/api/intelligence';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: { user: null }) => unknown) => selector({ user: null })),
}));

const mockGetEngagementSummary = vi.fn();
const mockGetEngagementDepth = vi.fn();
const mockGetEngagementTimeline = vi.fn();
const mockCreateEngagement = vi.fn();
vi.mock('@/api/intelligence', () => ({
  intelligenceApi: {
    getEngagementSummary: (...args: unknown[]) => mockGetEngagementSummary(...args),
    getEngagementDepth: (...args: unknown[]) => mockGetEngagementDepth(...args),
    getEngagementTimeline: (...args: unknown[]) => mockGetEngagementTimeline(...args),
    createEngagement: (...args: unknown[]) => mockCreateEngagement(...args),
  },
}));

import EcosystemEngagementsView from '../building-detail/EcosystemEngagementsView';

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('EcosystemEngagementsView', () => {
  it('shows depth gauge with score', async () => {
    mockGetEngagementSummary.mockResolvedValue({
      building_id: 'b-1',
      total_engagements: 15,
      unique_actors: 5,
    });
    mockGetEngagementDepth.mockResolvedValue({
      building_id: 'b-1',
      depth_score: 72,
      unique_actors: 5,
      unique_orgs: 3,
      engagement_types_used: ['seen', 'accepted', 'confirmed'],
      actor_types_represented: ['diagnostician', 'contractor', 'owner'],
    });
    mockGetEngagementTimeline.mockResolvedValue([]);
    wrap(<EcosystemEngagementsView buildingId="b-1" />);

    const view = await screen.findByTestId('ecosystem-engagements-view');
    expect(view).toBeInTheDocument();
    expect(screen.getByText('72')).toBeInTheDocument(); // depth score
  });

  it('shows actor participation grid with represented actors', async () => {
    mockGetEngagementSummary.mockResolvedValue({
      building_id: 'b-1',
      total_engagements: 10,
      unique_actors: 3,
    });
    mockGetEngagementDepth.mockResolvedValue({
      building_id: 'b-1',
      depth_score: 50,
      unique_actors: 3,
      unique_orgs: 2,
      engagement_types_used: ['seen'],
      actor_types_represented: ['diagnostician', 'owner'],
    });
    mockGetEngagementTimeline.mockResolvedValue([]);
    wrap(<EcosystemEngagementsView buildingId="b-1" />);

    await screen.findByTestId('ecosystem-engagements-view');
    // All 6 actor types rendered; check that diagnostician and owner labels appear
    expect(screen.getByText('ecosystem_engagement.actor_diagnostician')).toBeInTheDocument();
    expect(screen.getByText('ecosystem_engagement.actor_owner')).toBeInTheDocument();
  });

  it('shows engagement timeline when events exist', async () => {
    const engagement: EcosystemEngagement = {
      id: 'eng-1',
      building_id: 'b-1',
      actor_type: 'diagnostician',
      actor_name: 'Jean Muller',
      subject_type: 'diagnostic',
      subject_label: 'Diagnostic amiante',
      engagement_type: 'accepted',
      status: 'active',
      comment: 'Resultat valide',
      engaged_at: '2026-03-01T10:00:00Z',
    };
    mockGetEngagementSummary.mockResolvedValue({
      building_id: 'b-1',
      total_engagements: 1,
      unique_actors: 1,
    });
    mockGetEngagementDepth.mockResolvedValue({
      building_id: 'b-1',
      depth_score: 30,
      unique_actors: 1,
      unique_orgs: 1,
      engagement_types_used: ['accepted'],
      actor_types_represented: ['diagnostician'],
    });
    mockGetEngagementTimeline.mockResolvedValue([engagement]);
    wrap(<EcosystemEngagementsView buildingId="b-1" />);

    await screen.findByTestId('ecosystem-engagements-view');
    expect(screen.getByText('Jean Muller')).toBeInTheDocument();
    expect(screen.getByText('Diagnostic amiante')).toBeInTheDocument();
  });
});
