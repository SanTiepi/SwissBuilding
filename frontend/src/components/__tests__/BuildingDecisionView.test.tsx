import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import BuildingDecisionView from '@/pages/BuildingDecisionView';
import type { DecisionView } from '@/api/decisionView';

const mockDecisionView: DecisionView = {
  building_id: '123e4567-e89b-12d3-a456-426614174000',
  building_name: 'Rue du Test 1',
  building_address: 'Rue du Test 1, 1000 Lausanne',
  passport_grade: 'B',
  overall_trust: 0.72,
  overall_completeness: 0.85,
  readiness_status: 'safe_to_start',
  last_updated: '2026-03-20T10:00:00Z',
  custody_posture: {
    total_artifact_versions: 3,
    current_versions: 2,
    total_custody_events: 5,
    latest_custody_event_at: '2026-03-20T10:00:00Z',
  },
  blockers: [
    {
      id: 'b1',
      category: 'procedure_blocked',
      title: 'Procedure blocked: SUVA notification',
      description: 'Status: complement_requested',
      source_type: 'permit_procedure',
      source_id: 'proc-1',
      link_hint: '/buildings/123/procedures/proc-1/authority-room',
    },
  ],
  conditions: [
    {
      id: 'c1',
      category: 'review_required',
      title: 'Pending review: Building permit',
      description: 'Status: under_review',
      source_type: 'permit_procedure',
      source_id: 'proc-2',
      link_hint: null,
    },
  ],
  clear_items: [
    {
      id: 'cl1',
      category: 'obligation_completed',
      title: 'Completed: Air monitoring',
      description: 'Completed at: 2026-03-15',
    },
  ],
  audience_readiness: [
    {
      audience: 'authority',
      has_pack: true,
      latest_pack_version: 1,
      latest_pack_status: 'ready',
      latest_pack_generated_at: '2026-03-18T10:00:00Z',
      included_sections: ['building_identity', 'diagnostics'],
      excluded_sections: [],
      unknowns_count: 0,
      contradictions_count: 0,
      residual_risks_count: 0,
      caveats: [],
      trust_refs_count: 2,
      proof_refs_count: 3,
    },
    {
      audience: 'insurer',
      has_pack: true,
      latest_pack_version: 1,
      latest_pack_status: 'ready',
      latest_pack_generated_at: '2026-03-18T10:00:00Z',
      included_sections: ['building_identity'],
      excluded_sections: [],
      unknowns_count: 1,
      contradictions_count: 0,
      residual_risks_count: 1,
      caveats: ['Data may be incomplete'],
      trust_refs_count: 1,
      proof_refs_count: 1,
    },
    {
      audience: 'lender',
      has_pack: false,
      latest_pack_version: null,
      latest_pack_status: null,
      latest_pack_generated_at: null,
      included_sections: [],
      excluded_sections: [],
      unknowns_count: 0,
      contradictions_count: 0,
      residual_risks_count: 0,
      caveats: [],
      trust_refs_count: 0,
      proof_refs_count: 0,
    },
    {
      audience: 'transaction',
      has_pack: false,
      latest_pack_version: null,
      latest_pack_status: null,
      latest_pack_generated_at: null,
      included_sections: [],
      excluded_sections: [],
      unknowns_count: 0,
      contradictions_count: 0,
      residual_risks_count: 0,
      caveats: [],
      trust_refs_count: 0,
      proof_refs_count: 0,
    },
  ],
  proof_chain: [
    {
      label: 'Diagnostic Publication',
      entity_type: 'diagnostic_publication',
      entity_id: 'dp-1',
      version: 1,
      content_hash: 'abcdef1234567890',
      status: 'auto_matched',
      delivery_status: null,
      occurred_at: '2026-03-10T10:00:00Z',
      custody_chain_length: 0,
    },
    {
      label: 'Proof Delivery (authority)',
      entity_type: 'proof_delivery',
      entity_id: 'pd-1',
      version: null,
      content_hash: 'hash123',
      status: 'acknowledged',
      delivery_status: 'acknowledged',
      occurred_at: '2026-03-15T10:00:00Z',
      custody_chain_length: 2,
    },
  ],
  roi: {
    time_saved_hours: 12.5,
    rework_avoided: 3,
    blocker_days_saved: 8.0,
    pack_reuse_count: 2,
    evidence_sources: ['obligations', 'permit_procedures'],
  },
};

const getMock = vi.fn();

vi.mock('@/api/decisionView', () => ({
  decisionViewApi: {
    get: (...args: unknown[]) => getMock(...args),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

function renderPage(buildingId = '123e4567-e89b-12d3-a456-426614174000') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/buildings/${buildingId}/decision`]}>
        <Routes>
          <Route path="/buildings/:buildingId/decision" element={<BuildingDecisionView />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('BuildingDecisionView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getMock.mockResolvedValue(mockDecisionView);
  });

  it('shows loading spinner initially', () => {
    getMock.mockReturnValue(new Promise(() => {})); // never resolves
    renderPage();
    expect(document.querySelector('.animate-spin')).toBeTruthy();
  });

  it('renders decision header with grade and trust', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('B')).toBeTruthy();
      expect(screen.getByText('Rue du Test 1')).toBeTruthy();
      expect(screen.getByText('72%')).toBeTruthy();
      expect(screen.getByText('85%')).toBeTruthy();
    });
  });

  it('renders blockers section', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Blockers \(1\)/)).toBeTruthy();
      expect(screen.getByText('Procedure blocked: SUVA notification')).toBeTruthy();
    });
  });

  it('renders conditions section', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Conditions \(1\)/)).toBeTruthy();
      expect(screen.getByText('Pending review: Building permit')).toBeTruthy();
    });
  });

  it('renders clear items section', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Clear \(1\)/)).toBeTruthy();
      expect(screen.getByText('Completed: Air monitoring')).toBeTruthy();
    });
  });

  it('renders audience readiness tabs and switches between them', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Authority')).toBeTruthy();
      expect(screen.getByText('Insurer')).toBeTruthy();
    });

    fireEvent.click(screen.getByText('Insurer'));
    await waitFor(() => {
      expect(screen.getByText('Data may be incomplete')).toBeTruthy();
    });
  });

  it('renders proof chain items', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Diagnostic Publication')).toBeTruthy();
      expect(screen.getByText('Proof Delivery (authority)')).toBeTruthy();
    });
  });

  it('renders ROI summary with values', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('12.5h')).toBeTruthy();
      expect(screen.getByText('8.0')).toBeTruthy();
    });
  });
});
