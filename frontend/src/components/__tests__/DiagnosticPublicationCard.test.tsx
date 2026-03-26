import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DiagnosticPublicationCard, type DiagnosticPublication } from '../building-detail/DiagnosticPublicationCard';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

function makePub(overrides: Partial<DiagnosticPublication> = {}): DiagnosticPublication {
  return {
    id: 'pub-1',
    building_id: 'b-1',
    source_system: 'Batiscan',
    source_mission_id: 'M-001',
    current_version: 1,
    match_state: 'auto_matched',
    match_key: 'EGID-123',
    match_key_type: 'egid',
    mission_type: 'asbestos_full',
    report_pdf_url: 'https://example.com/report.pdf',
    structured_summary: {
      pollutants_found: 'asbestos, pcb',
      fach_urgency: 'high',
      zones: 'Sous-sol, 1er etage',
    },
    annexes: [
      { path: '/files/annex1.pdf', type: 'pdf', name: 'Plan amiante' },
      { path: '/files/annex2.jpg', type: 'image', name: 'Photo prelev. 3' },
    ],
    payload_hash: 'abc123def456ghi789',
    published_at: '2026-03-20T10:00:00Z',
    is_immutable: true,
    created_at: '2026-03-20T09:00:00Z',
    versions: [
      { version: 1, published_at: '2026-03-18T08:00:00Z', payload_hash: 'aaa111bbb222ccc333' },
      { version: 2, published_at: '2026-03-20T10:00:00Z', payload_hash: 'abc123def456ghi789' },
    ],
    ...overrides,
  };
}

describe('DiagnosticPublicationCard', () => {
  it('renders empty state when no publications', () => {
    render(<DiagnosticPublicationCard publications={[]} />);

    expect(screen.getByTestId('diagnostic-publication-card')).toBeInTheDocument();
    expect(screen.getByTestId('diag-pub-empty')).toBeInTheDocument();
    expect(screen.getByText('diag_pub.title')).toBeInTheDocument();
    expect(screen.getByText('diag_pub.empty')).toBeInTheDocument();
  });

  it('renders header with count badge', () => {
    render(<DiagnosticPublicationCard publications={[makePub(), makePub({ id: 'pub-2' })]} />);

    expect(screen.getByText('diag_pub.title')).toBeInTheDocument();
    expect(screen.getByTestId('diag-pub-count')).toHaveTextContent('2');
  });

  it('renders mission type, source, and match state badges', () => {
    render(<DiagnosticPublicationCard publications={[makePub()]} />);

    expect(screen.getByTestId('diag-pub-mission-type')).toHaveTextContent('diag_pub.mission_asbestos_full');
    expect(screen.getByTestId('diag-pub-source')).toHaveTextContent('Batiscan');
    expect(screen.getByTestId('diag-pub-match-state')).toHaveTextContent('diag_pub.match_auto_matched');
  });

  it('renders structured summary fields', () => {
    render(<DiagnosticPublicationCard publications={[makePub()]} />);

    const summary = screen.getByTestId('diag-pub-summary');
    expect(summary).toBeInTheDocument();
    expect(summary).toHaveTextContent('asbestos, pcb');
    expect(summary).toHaveTextContent('high');
    expect(summary).toHaveTextContent('Sous-sol, 1er etage');
  });

  it('renders PDF download link when url present', () => {
    render(<DiagnosticPublicationCard publications={[makePub()]} />);

    const link = screen.getByTestId('diag-pub-pdf-link');
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', 'https://example.com/report.pdf');
  });

  it('does not render PDF link when url is null', () => {
    render(<DiagnosticPublicationCard publications={[makePub({ report_pdf_url: null })]} />);

    expect(screen.queryByTestId('diag-pub-pdf-link')).not.toBeInTheDocument();
  });

  it('renders immutable indicator', () => {
    render(<DiagnosticPublicationCard publications={[makePub()]} />);

    expect(screen.getByTestId('diag-pub-immutable')).toBeInTheDocument();
    expect(screen.getByText('diag_pub.immutable')).toBeInTheDocument();
  });

  it('does not render immutable indicator when is_immutable is false', () => {
    render(<DiagnosticPublicationCard publications={[makePub({ is_immutable: false })]} />);

    expect(screen.queryByTestId('diag-pub-immutable')).not.toBeInTheDocument();
  });

  it('toggles annexes list on click', () => {
    render(<DiagnosticPublicationCard publications={[makePub()]} />);

    // Annexes list not visible initially
    expect(screen.queryByTestId('diag-pub-annexes-list')).not.toBeInTheDocument();

    // Click toggle
    fireEvent.click(screen.getByTestId('diag-pub-annexes-toggle'));
    expect(screen.getByTestId('diag-pub-annexes-list')).toBeInTheDocument();
    expect(screen.getByText('Plan amiante')).toBeInTheDocument();

    // Click again to collapse
    fireEvent.click(screen.getByTestId('diag-pub-annexes-toggle'));
    expect(screen.queryByTestId('diag-pub-annexes-list')).not.toBeInTheDocument();
  });

  it('toggles version history on click', () => {
    render(<DiagnosticPublicationCard publications={[makePub()]} />);

    expect(screen.queryByTestId('diag-pub-versions-list')).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('diag-pub-versions-toggle'));
    expect(screen.getByTestId('diag-pub-versions-list')).toBeInTheDocument();
    expect(screen.getByText('v1')).toBeInTheDocument();
    expect(screen.getByText('v2')).toBeInTheDocument();
    // Hash snippet
    expect(screen.getByText('aaa111bbb222')).toBeInTheDocument();
  });

  it('does not render annexes toggle when annexes are empty', () => {
    render(<DiagnosticPublicationCard publications={[makePub({ annexes: [] })]} />);

    expect(screen.queryByTestId('diag-pub-annexes-toggle')).not.toBeInTheDocument();
  });

  it('does not render versions toggle when versions are absent', () => {
    render(<DiagnosticPublicationCard publications={[makePub({ versions: undefined })]} />);

    expect(screen.queryByTestId('diag-pub-versions-toggle')).not.toBeInTheDocument();
  });

  it('renders different match state styles', () => {
    const { rerender } = render(
      <DiagnosticPublicationCard publications={[makePub({ match_state: 'needs_review' })]} />,
    );
    expect(screen.getByTestId('diag-pub-match-state')).toHaveTextContent('diag_pub.match_needs_review');

    rerender(<DiagnosticPublicationCard publications={[makePub({ match_state: 'unmatched' })]} />);
    expect(screen.getByTestId('diag-pub-match-state')).toHaveTextContent('diag_pub.match_unmatched');
  });

  it('renders without structured summary when null', () => {
    render(<DiagnosticPublicationCard publications={[makePub({ structured_summary: null })]} />);

    expect(screen.queryByTestId('diag-pub-summary')).not.toBeInTheDocument();
    // Card should still render
    expect(screen.getByTestId('diagnostic-publication-card')).toBeInTheDocument();
  });
});
