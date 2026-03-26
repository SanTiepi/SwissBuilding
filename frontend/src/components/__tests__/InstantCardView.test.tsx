import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import InstantCardView from '../building-detail/InstantCardView';
import type { InstantCardResult } from '@/api/intelligence';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

function makeCard(overrides: Partial<InstantCardResult> = {}): InstantCardResult {
  return {
    building_id: 'b-1',
    passport_grade: 'C',
    what_we_know: {
      identity: { address: 'Rue du Midi 15', egid: 12345 },
      physical: { floors: 4, dwellings: 12, surface_m2: 800 },
      environment: {},
      energy: {},
      diagnostics: {},
      residual_materials: [],
    },
    what_is_risky: {
      pollutant_risk: { asbestos: 0.85, pcb: 0.6, lead: 0.3 },
      environmental_risk: { score: 6.5 },
      compliance_gaps: [{ description: 'Diagnostic amiante manquant' }],
    },
    what_blocks: {
      procedural_blockers: [{ description: 'AvT requis' }],
      missing_proof: [],
      overdue_obligations: [],
    },
    what_to_do_next: {
      top_3_actions: [
        { action: 'Commander diagnostic amiante', priority: 'high', estimated_cost: 3500, evidence_needed: null },
        { action: "Etablir plan d'assainissement", priority: 'medium', estimated_cost: 8000, evidence_needed: null },
        { action: 'Evaluer potentiel solaire', priority: 'low', estimated_cost: null, evidence_needed: null },
      ],
    },
    what_is_reusable: {
      diagnostic_publications: [{ id: 'pub-1' }],
      packs_generated: [],
      proof_deliveries: [{ id: 'del-1' }, { id: 'del-2' }],
    },
    execution: {
      renovation_plan_10y: {},
      subsidies: [],
      roi_renovation: {},
      insurance_impact: {},
      co2_impact: {},
      energy_savings: {},
      sequence_recommendation: {},
      next_concrete_step: {},
    },
    trust: {
      freshness: 'current',
      confidence: 'high',
      overall_trust: 0.78,
      trend: 'improving',
    },
    neighbor_signals: [],
    ...overrides,
  };
}

describe('InstantCardView', () => {
  it('renders all 5 sections', () => {
    render(<InstantCardView data={makeCard()} />);
    expect(screen.getByTestId('section-what-we-know')).toBeInTheDocument();
    expect(screen.getByTestId('section-what-is-risky')).toBeInTheDocument();
    expect(screen.getByTestId('section-what-blocks')).toBeInTheDocument();
    expect(screen.getByTestId('section-what-to-do')).toBeInTheDocument();
    expect(screen.getByTestId('section-what-is-reusable')).toBeInTheDocument();
  });

  it('shows grade badge with correct grade', () => {
    render(<InstantCardView data={makeCard({ passport_grade: 'B' })} />);
    expect(screen.getByTestId('grade-badge')).toHaveTextContent('B');
  });

  it('renders risk bars for pollutant predictions', () => {
    render(<InstantCardView data={makeCard()} />);
    const bars = screen.getAllByTestId('risk-bar');
    expect(bars.length).toBe(3);
    expect(bars[0]).toHaveTextContent('asbestos');
    expect(bars[0]).toHaveTextContent('85%');
  });

  it('renders action items', () => {
    render(<InstantCardView data={makeCard()} />);
    const actions = screen.getAllByTestId('action-item');
    expect(actions.length).toBe(3);
    expect(actions[0]).toHaveTextContent('Commander diagnostic amiante');
  });

  it('shows blocker count badge when blockers exist', () => {
    render(<InstantCardView data={makeCard()} />);
    const blockSection = screen.getByTestId('section-what-blocks');
    expect(blockSection).toHaveTextContent('1'); // badge with count
  });

  it('shows trust metadata in footer', () => {
    render(<InstantCardView data={makeCard()} />);
    const footer = screen.getByTestId('instant-card-footer');
    expect(footer).toHaveTextContent('78%');
    expect(footer).toHaveTextContent('current');
  });

  it('shows OK badge when no blockers', () => {
    const card = makeCard({
      what_blocks: {
        procedural_blockers: [],
        missing_proof: [],
        overdue_obligations: [],
      },
    });
    render(<InstantCardView data={card} />);
    expect(screen.getByTestId('section-what-blocks')).toHaveTextContent('intelligence.clear');
  });

  it('shows compliance gaps in risk section', () => {
    render(<InstantCardView data={makeCard()} />);
    expect(screen.getByTestId('section-what-is-risky')).toHaveTextContent('Diagnostic amiante manquant');
  });

  it('sections can be collapsed and expanded', () => {
    render(<InstantCardView data={makeCard()} />);
    const toggle = screen.getByTestId('section-what-we-know-toggle');
    // Click to collapse
    fireEvent.click(toggle);
    // Identity row should no longer be visible
    expect(screen.queryByText('Rue du Midi 15')).not.toBeInTheDocument();
    // Click to expand again
    fireEvent.click(toggle);
    expect(screen.getByText('Rue du Midi 15')).toBeInTheDocument();
  });

  it('shows reusable data counts', () => {
    render(<InstantCardView data={makeCard()} />);
    // Expand reusable section (defaults to closed)
    fireEvent.click(screen.getByTestId('section-what-is-reusable-toggle'));
    expect(screen.getByTestId('section-what-is-reusable')).toHaveTextContent('1');
    expect(screen.getByTestId('section-what-is-reusable')).toHaveTextContent('2');
  });
});
