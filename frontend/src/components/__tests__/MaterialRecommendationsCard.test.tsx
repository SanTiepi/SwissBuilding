import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MaterialRecommendationsCard } from '../building-detail/MaterialRecommendationsCard';
import type { MaterialRecommendation } from '../building-detail/MaterialRecommendationsCard';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const sampleRec: MaterialRecommendation = {
  original_material_type: 'floor_tile',
  original_pollutant: 'asbestos',
  recommended_material: 'Ceramic tile (asbestos-free)',
  recommended_material_type: 'ceramic',
  reason: 'Original floor tiles contain chrysotile asbestos fibres',
  risk_level: 'high',
  evidence_requirements: [
    {
      document_type: 'lab_analysis',
      description: 'Lab analysis confirming asbestos content',
      mandatory: true,
      legal_ref: 'OTConst Art. 60a',
    },
    {
      document_type: 'waste_plan',
      description: 'Waste disposal plan for asbestos materials',
      mandatory: false,
      legal_ref: null,
    },
  ],
  risk_flags: ['Friable material — special handling required', 'Requires certified contractor'],
};

const sampleRecLow: MaterialRecommendation = {
  original_material_type: 'pipe_insulation',
  original_pollutant: 'pcb',
  recommended_material: 'Mineral wool insulation',
  recommended_material_type: 'mineral_wool',
  reason: 'PCB contamination above threshold',
  risk_level: 'low',
  evidence_requirements: [],
  risk_flags: [],
};

describe('MaterialRecommendationsCard', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders empty state when recommendations array is empty', () => {
    render(<MaterialRecommendationsCard recommendations={[]} />);
    expect(screen.getByText('material_rec.title')).toBeInTheDocument();
    expect(screen.getByText('material_rec.empty')).toBeInTheDocument();
  });

  it('renders recommendation count and summary for each item', () => {
    render(<MaterialRecommendationsCard recommendations={[sampleRec, sampleRecLow]} />);
    expect(screen.getByText('2 material_rec.count')).toBeInTheDocument();
    expect(screen.getByText('floor_tile')).toBeInTheDocument();
    expect(screen.getByText('(asbestos)')).toBeInTheDocument();
    expect(screen.getByText('pipe_insulation')).toBeInTheDocument();
  });

  it('shows risk level badge', () => {
    render(<MaterialRecommendationsCard recommendations={[sampleRec]} />);
    expect(screen.getByText('high')).toBeInTheDocument();
  });

  it('shows suggested material in collapsed state', () => {
    render(<MaterialRecommendationsCard recommendations={[sampleRec]} />);
    expect(screen.getByText(/Ceramic tile \(asbestos-free\)/)).toBeInTheDocument();
  });

  it('expands to show details when clicked', () => {
    render(<MaterialRecommendationsCard recommendations={[sampleRec]} />);

    // Details should not be visible initially
    expect(screen.queryByText('Original floor tiles contain chrysotile asbestos fibres')).not.toBeInTheDocument();

    // Click to expand
    const button = screen.getByRole('button');
    fireEvent.click(button);

    // Now details should be visible
    expect(screen.getByText('Original floor tiles contain chrysotile asbestos fibres')).toBeInTheDocument();
    expect(screen.getByText('ceramic')).toBeInTheDocument();
  });

  it('shows risk flags when expanded', () => {
    render(<MaterialRecommendationsCard recommendations={[sampleRec]} />);
    fireEvent.click(screen.getByRole('button'));

    expect(screen.getByText('Friable material — special handling required')).toBeInTheDocument();
    expect(screen.getByText('Requires certified contractor')).toBeInTheDocument();
  });

  it('shows evidence requirements when expanded', () => {
    render(<MaterialRecommendationsCard recommendations={[sampleRec]} />);
    fireEvent.click(screen.getByRole('button'));

    expect(screen.getByText('lab_analysis')).toBeInTheDocument();
    expect(screen.getByText(/Lab analysis confirming asbestos content/)).toBeInTheDocument();
    expect(screen.getByText('[OTConst Art. 60a]')).toBeInTheDocument();
    // mandatory indicator
    expect(screen.getByText('(material_rec.mandatory)')).toBeInTheDocument();
  });

  it('collapses when clicked again', () => {
    render(<MaterialRecommendationsCard recommendations={[sampleRec]} />);
    const button = screen.getByRole('button');

    fireEvent.click(button);
    expect(screen.getByText('Original floor tiles contain chrysotile asbestos fibres')).toBeInTheDocument();

    fireEvent.click(button);
    expect(screen.queryByText('Original floor tiles contain chrysotile asbestos fibres')).not.toBeInTheDocument();
  });

  it('does not show risk flags section when empty', () => {
    render(<MaterialRecommendationsCard recommendations={[sampleRecLow]} />);
    fireEvent.click(screen.getByRole('button'));

    expect(screen.queryByText('material_rec.risk_flags')).not.toBeInTheDocument();
  });

  it('does not show evidence requirements section when empty', () => {
    render(<MaterialRecommendationsCard recommendations={[sampleRecLow]} />);
    fireEvent.click(screen.getByRole('button'));

    expect(screen.queryByText('material_rec.evidence_requirements')).not.toBeInTheDocument();
  });

  it('only expands one item at a time', () => {
    render(<MaterialRecommendationsCard recommendations={[sampleRec, sampleRecLow]} />);
    const buttons = screen.getAllByRole('button');

    // Expand first
    fireEvent.click(buttons[0]);
    expect(screen.getByText('Original floor tiles contain chrysotile asbestos fibres')).toBeInTheDocument();

    // Expand second — first should collapse
    fireEvent.click(buttons[1]);
    expect(screen.queryByText('Original floor tiles contain chrysotile asbestos fibres')).not.toBeInTheDocument();
    expect(screen.getByText('PCB contamination above threshold')).toBeInTheDocument();
  });
});
