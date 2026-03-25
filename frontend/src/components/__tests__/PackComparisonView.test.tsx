import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { PackComparisonView } from '../PackComparisonView';
import type { PackComparisonData } from '@/api/audiencePacks';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockComparison: PackComparisonData = {
  pack_1: {
    id: 'pack-1',
    building_id: 'b-1',
    pack_type: 'insurer',
    pack_version: 1,
    status: 'draft',
    generated_by_user_id: null,
    sections: {
      diagnostics: { name: 'diagnostics', included: true, blocked: false },
      financial: { name: 'financial', included: true, blocked: false },
      ownership: { name: 'ownership', included: false, blocked: true },
    },
    unknowns_summary: null,
    contradictions_summary: null,
    residual_risk_summary: null,
    trust_refs: null,
    proof_refs: null,
    content_hash: 'abc123',
    generated_at: '2026-03-01T10:00:00Z',
    superseded_by_id: null,
    created_at: '2026-03-01T10:00:00Z',
    updated_at: '2026-03-01T10:00:00Z',
    caveats: [{ caveat_type: 'freshness_warning', severity: 'medium', message: 'Stale data', applies_when: {} }],
  },
  pack_2: {
    id: 'pack-2',
    building_id: 'b-1',
    pack_type: 'fiduciary',
    pack_version: 2,
    status: 'ready',
    generated_by_user_id: null,
    sections: {
      diagnostics: { name: 'diagnostics', included: true, blocked: false },
      financial: { name: 'financial', included: false, blocked: true },
    },
    unknowns_summary: null,
    contradictions_summary: null,
    residual_risk_summary: null,
    trust_refs: null,
    proof_refs: null,
    content_hash: 'def456',
    generated_at: '2026-03-15T10:00:00Z',
    superseded_by_id: null,
    created_at: '2026-03-15T10:00:00Z',
    updated_at: '2026-03-15T10:00:00Z',
    caveats: [],
  },
  section_diff: {
    financial: { only_in_1: ['included'], only_in_2: ['blocked'], changed: [] },
    ownership: { only_in_1: ['blocked'], changed: [] },
  },
  caveat_diff: {
    only_in_1: [{ caveat_type: 'freshness_warning', severity: 'medium', message: 'Stale data', applies_when: {} }],
    only_in_2: [],
  },
};

describe('PackComparisonView', () => {
  it('renders comparison view with two columns', () => {
    render(<PackComparisonView comparison={mockComparison} />);
    expect(screen.getByTestId('pack-comparison-view')).toBeInTheDocument();
    expect(screen.getByTestId('comparison-columns')).toBeInTheDocument();
  });

  it('displays sections from both packs', () => {
    render(<PackComparisonView comparison={mockComparison} />);
    const sections = screen.getAllByTestId('comparison-section');
    expect(sections.length).toBeGreaterThanOrEqual(4); // 3 from pack1 + 2 from pack2 (minus shared display)
  });

  it('shows diff summary when differences exist', () => {
    render(<PackComparisonView comparison={mockComparison} />);
    expect(screen.getByTestId('diff-summary')).toBeInTheDocument();
    expect(screen.getAllByTestId('diff-section').length).toBeGreaterThan(0);
  });

  it('shows caveat diff', () => {
    render(<PackComparisonView comparison={mockComparison} />);
    expect(screen.getByTestId('caveat-diff')).toBeInTheDocument();
    expect(screen.getAllByText('Stale data').length).toBeGreaterThanOrEqual(1);
  });

  it('displays pack caveats within columns', () => {
    render(<PackComparisonView comparison={mockComparison} />);
    const caveats = screen.getAllByTestId('comparison-caveat');
    expect(caveats.length).toBe(1); // only pack_1 has caveats
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    render(<PackComparisonView comparison={mockComparison} onClose={onClose} />);
    fireEvent.click(screen.getByTestId('close-comparison'));
    expect(onClose).toHaveBeenCalled();
  });

  it('renders without diff summary when no diffs', () => {
    const noDiffComparison: PackComparisonData = {
      ...mockComparison,
      section_diff: {},
      caveat_diff: { only_in_1: [], only_in_2: [] },
    };
    render(<PackComparisonView comparison={noDiffComparison} />);
    expect(screen.queryByTestId('diff-summary')).not.toBeInTheDocument();
  });
});
