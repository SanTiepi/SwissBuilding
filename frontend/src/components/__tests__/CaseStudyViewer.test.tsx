import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CaseStudyViewer } from '@/components/CaseStudyViewer';
import type { CaseStudyTemplate } from '@/api/demoPilot';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockTemplate: CaseStudyTemplate = {
  id: 'cs-1',
  template_code: 'amiante-pilot',
  title: 'Amiante Pilot Case Study',
  persona_target: 'property_manager',
  workflow_type: 'diagnostic_to_remediation',
  narrative_structure: {
    before: 'Unknown asbestos status across 15 buildings.',
    trigger: 'Regulatory deadline for VD canton compliance.',
    after: 'Full evidence chain, safe-to-start for all buildings.',
    proof_points: [
      'Completeness improved from 40% to 98%',
      'Rework reduced by 65%',
      'Authority pack generated in 2h vs 3 days',
    ],
  },
  evidence_requirements: [
    { label: 'Diagnostic report', source: 'diagnostics' },
    { label: 'Evidence chain', source: 'evidence_links' },
  ],
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
};

describe('CaseStudyViewer', () => {
  it('renders the template title and badges', () => {
    render(<CaseStudyViewer template={mockTemplate} />);
    expect(screen.getByText('Amiante Pilot Case Study')).toBeInTheDocument();
    expect(screen.getByText('property_manager')).toBeInTheDocument();
    expect(screen.getByText('diagnostic_to_remediation')).toBeInTheDocument();
  });

  it('renders before/trigger/after narrative', () => {
    render(<CaseStudyViewer template={mockTemplate} />);
    expect(screen.getByTestId('narrative-before')).toBeInTheDocument();
    expect(screen.getByText(/Unknown asbestos status/)).toBeInTheDocument();
    expect(screen.getByTestId('narrative-trigger')).toBeInTheDocument();
    expect(screen.getByText(/Regulatory deadline/)).toBeInTheDocument();
    expect(screen.getByTestId('narrative-after')).toBeInTheDocument();
    expect(screen.getByText(/Full evidence chain/)).toBeInTheDocument();
  });

  it('renders proof points', () => {
    render(<CaseStudyViewer template={mockTemplate} />);
    expect(screen.getByText('Completeness improved from 40% to 98%')).toBeInTheDocument();
    expect(screen.getByText('Rework reduced by 65%')).toBeInTheDocument();
    expect(screen.getByText(/Authority pack generated/)).toBeInTheDocument();
  });

  it('renders evidence requirements', () => {
    render(<CaseStudyViewer template={mockTemplate} />);
    expect(screen.getByText('Diagnostic report')).toBeInTheDocument();
    expect(screen.getByText('Evidence chain')).toBeInTheDocument();
  });
});
