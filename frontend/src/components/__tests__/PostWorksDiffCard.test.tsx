import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { PostWorksDiffCard } from '../PostWorksDiffCard';
import { postWorksApi } from '@/api/postWorks';
import { interventionsApi } from '@/api/interventions';
import type { InterventionType, InterventionStatus } from '@/types';

vi.mock('@/api/postWorks', () => ({
  postWorksApi: {
    compare: vi.fn(),
    summary: vi.fn(),
    list: vi.fn(),
    verify: vi.fn(),
  },
}));

vi.mock('@/api/interventions', () => ({
  interventionsApi: {
    list: vi.fn(),
  },
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: unknown) => unknown) =>
    selector({
      user: { id: 'u1', role: 'admin', email: 'a@b.ch', first_name: 'A', last_name: 'B' },
    }),
  ),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MemoryRouter>
  );
}

const EMPTY_COMPARISON = {
  building_id: 'b1',
  intervention_id: null,
  before: { total_positive_samples: 0, by_pollutant: {}, risk_areas: [] },
  after: {
    removed: 0,
    remaining: 0,
    encapsulated: 0,
    treated: 0,
    unknown_after_intervention: 0,
    recheck_needed: 0,
    by_pollutant: {},
  },
  summary: { remediation_rate: 0, verification_rate: 0, residual_risk_count: 0 },
};

const FULL_COMPARISON = {
  building_id: 'b1',
  intervention_id: null,
  before: {
    total_positive_samples: 5,
    by_pollutant: { asbestos: 3, pcb: 2 },
    risk_areas: [
      { pollutant: 'asbestos', location: 'Room A', risk_level: 'high' },
      { pollutant: 'pcb', location: 'Room B', risk_level: 'medium' },
    ],
  },
  after: {
    removed: 3,
    remaining: 1,
    encapsulated: 0,
    treated: 1,
    unknown_after_intervention: 0,
    recheck_needed: 0,
    by_pollutant: {
      asbestos: {
        removed: 2,
        remaining: 1,
        encapsulated: 0,
        treated: 0,
        unknown_after_intervention: 0,
        recheck_needed: 0,
      },
      pcb: { removed: 1, remaining: 0, encapsulated: 0, treated: 1, unknown_after_intervention: 0, recheck_needed: 0 },
    },
  },
  summary: { remediation_rate: 0.8, verification_rate: 0.6, residual_risk_count: 1 },
};

const SUMMARY = {
  building_id: 'b1',
  total_states: 5,
  by_state_type: { removed: 3, treated: 1, remaining: 1 },
  by_pollutant: { asbestos: 3, pcb: 2 },
  verification_progress: { verified: 3, unverified: 2, rate: 0.6 },
  interventions_covered: 1,
};

const STATES_LIST = {
  items: [
    {
      id: 's1',
      building_id: 'b1',
      intervention_id: 'iv1',
      state_type: 'removed',
      pollutant_type: 'asbestos',
      title: 'Removed - asbestos - Room A',
      description: null,
      zone_id: null,
      element_id: null,
      material_id: null,
      verified: true,
      verified_by: 'u1',
      verified_at: '2026-01-15T10:00:00Z',
      evidence_json: null,
      recorded_by: 'u1',
      recorded_at: '2026-01-10T10:00:00Z',
      notes: null,
    },
    {
      id: 's2',
      building_id: 'b1',
      intervention_id: 'iv1',
      state_type: 'remaining',
      pollutant_type: 'asbestos',
      title: 'Remaining - asbestos - Room B',
      description: null,
      zone_id: null,
      element_id: null,
      material_id: null,
      verified: false,
      verified_by: null,
      verified_at: null,
      evidence_json: null,
      recorded_by: 'u1',
      recorded_at: '2026-01-10T10:00:00Z',
      notes: 'Needs follow-up',
    },
  ],
  total: 2,
  page: 1,
  size: 50,
  pages: 1,
};

const INTERVENTIONS_LIST = {
  items: [
    {
      id: 'iv1',
      building_id: 'b1',
      intervention_type: 'asbestos_removal' as InterventionType,
      title: 'Asbestos Removal Phase 1',
      description: null,
      status: 'completed' as InterventionStatus,
      date_start: '2026-01-01',
      date_end: '2026-01-05',
      contractor_name: 'SafeBuild AG',
      contractor_id: null,
      cost_chf: 15000,
      zones_affected: null,
      materials_used: null,
      diagnostic_id: null,
      notes: null,
      created_by: null,
      created_at: '2025-12-01T00:00:00Z',
      updated_at: '2026-01-05T00:00:00Z',
    },
  ],
  total: 1,
  page: 1,
  size: 50,
  pages: 1,
};

describe('PostWorksDiffCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders explicit error state when comparison fails', async () => {
    vi.mocked(postWorksApi.compare).mockRejectedValueOnce(new Error('boom'));
    vi.mocked(postWorksApi.summary).mockResolvedValueOnce(SUMMARY);
    vi.mocked(postWorksApi.list).mockResolvedValueOnce(STATES_LIST);

    render(<PostWorksDiffCard buildingId="b1" />, { wrapper: createWrapper() });

    expect(await screen.findByText('post_works.diff_title')).toBeInTheDocument();
    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders no-data state when there are no positive samples before works', async () => {
    vi.mocked(postWorksApi.compare).mockResolvedValueOnce(EMPTY_COMPARISON);
    vi.mocked(postWorksApi.summary).mockResolvedValueOnce({ ...SUMMARY, total_states: 0 });
    vi.mocked(postWorksApi.list).mockResolvedValueOnce({ items: [], total: 0, page: 1, size: 50, pages: 0 });

    render(<PostWorksDiffCard buildingId="b1" />, { wrapper: createWrapper() });

    expect(await screen.findByText('post_works.no_data')).toBeInTheDocument();
  });

  it('renders full comparison with summary header, before/after, and timeline', async () => {
    vi.mocked(postWorksApi.compare).mockResolvedValueOnce(FULL_COMPARISON);
    vi.mocked(postWorksApi.summary).mockResolvedValueOnce(SUMMARY);
    vi.mocked(postWorksApi.list).mockResolvedValueOnce(STATES_LIST);
    vi.mocked(interventionsApi.list).mockResolvedValueOnce(INTERVENTIONS_LIST);

    render(<PostWorksDiffCard buildingId="b1" />, { wrapper: createWrapper() });

    // Summary header - total_states appears in header card
    const totalElements = await screen.findAllByText('5');
    expect(totalElements.length).toBeGreaterThanOrEqual(1);

    // Before section
    expect(screen.getByText('post_works.before')).toBeInTheDocument();

    // After section
    expect(screen.getByText('post_works.after')).toBeInTheDocument();

    // Linked intervention
    expect(await screen.findByText('Asbestos Removal Phase 1')).toBeInTheDocument();

    // Timeline entries (also appear in verification section, so use getAllByText)
    expect(screen.getAllByText('Removed - asbestos - Room A').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Remaining - asbestos - Room B').length).toBeGreaterThanOrEqual(1);
  });

  it('renders verification section with pending and verified states', async () => {
    vi.mocked(postWorksApi.compare).mockResolvedValueOnce(FULL_COMPARISON);
    vi.mocked(postWorksApi.summary).mockResolvedValueOnce(SUMMARY);
    vi.mocked(postWorksApi.list).mockResolvedValueOnce(STATES_LIST);
    vi.mocked(interventionsApi.list).mockResolvedValueOnce(INTERVENTIONS_LIST);

    render(<PostWorksDiffCard buildingId="b1" />, { wrapper: createWrapper() });

    // Verification section header
    expect(await screen.findByText('post_works.verification')).toBeInTheDocument();

    // Pending state has verify button (admin role)
    expect(screen.getByText('post_works.verify_action')).toBeInTheDocument();

    // Verified badge
    const verifiedBadges = screen.getAllByText('post_works.verified');
    expect(verifiedBadges.length).toBeGreaterThanOrEqual(1);
  });

  it('calls verify API when verify button is clicked', async () => {
    // Initial load mocks
    vi.mocked(postWorksApi.compare).mockResolvedValue(FULL_COMPARISON);
    vi.mocked(postWorksApi.summary).mockResolvedValue(SUMMARY);
    vi.mocked(postWorksApi.list).mockResolvedValue(STATES_LIST);
    vi.mocked(interventionsApi.list).mockResolvedValue(INTERVENTIONS_LIST);
    vi.mocked(postWorksApi.verify).mockResolvedValueOnce({ ...STATES_LIST.items[1], verified: true });

    const user = userEvent.setup();
    render(<PostWorksDiffCard buildingId="b1" />, { wrapper: createWrapper() });

    const verifyButton = await screen.findByText('post_works.verify_action');
    await user.click(verifyButton);

    await waitFor(() => {
      expect(postWorksApi.verify).toHaveBeenCalledWith('b1', 's2');
    });
  });

  it('shows pollutant breakdown with diff indicators', async () => {
    vi.mocked(postWorksApi.compare).mockResolvedValueOnce(FULL_COMPARISON);
    vi.mocked(postWorksApi.summary).mockResolvedValueOnce(SUMMARY);
    vi.mocked(postWorksApi.list).mockResolvedValueOnce(STATES_LIST);
    vi.mocked(interventionsApi.list).mockResolvedValueOnce(INTERVENTIONS_LIST);

    render(<PostWorksDiffCard buildingId="b1" />, { wrapper: createWrapper() });

    // Per pollutant section
    expect(await screen.findByText('post_works.pollutant_breakdown')).toBeInTheDocument();
  });
});
