import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConfidenceBadge, type ConfidenceLevel } from '../ConfidenceBadge';

describe('ConfidenceBadge', () => {
  const levels: { level: ConfidenceLevel; label: string; dotClass: string }[] = [
    { level: 'raw', label: 'Source brute', dotClass: 'bg-gray-400' },
    { level: 'enriched', label: 'Enrichi', dotClass: 'bg-amber-400' },
    { level: 'validated', label: 'Valide', dotClass: 'bg-green-500' },
    { level: 'published', label: 'Publie', dotClass: 'bg-blue-500' },
    { level: 'inherited', label: 'Herite', dotClass: 'bg-purple-500' },
    { level: 'contradictory', label: 'Contradictoire', dotClass: 'bg-red-500' },
  ];

  it.each(levels)('renders correct label for level: $level', ({ level, label }) => {
    render(<ConfidenceBadge level={level} size="md" />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it.each(levels)('renders correct testid for level: $level', ({ level }) => {
    render(<ConfidenceBadge level={level} />);
    expect(screen.getByTestId(`confidence-badge-${level}`)).toBeInTheDocument();
  });

  it('sm size shows only dot (no label) by default', () => {
    const { container } = render(<ConfidenceBadge level="validated" size="sm" />);
    const badge = screen.getByTestId('confidence-badge-validated');
    // sm without showLabel renders a single dot span (no inner text)
    expect(badge.textContent).toBe('');
    expect(badge).toHaveClass('rounded-full', 'w-2', 'h-2');
    // No child spans (dot-only mode is a single span)
    expect(container.querySelectorAll('span span')).toHaveLength(0);
  });

  it('md size shows dot + label by default', () => {
    render(<ConfidenceBadge level="enriched" size="md" />);
    const badge = screen.getByTestId('confidence-badge-enriched');
    expect(badge).toHaveTextContent('Enrichi');
    // Should have an inner dot span
    const innerDot = badge.querySelector('span');
    expect(innerDot).toHaveClass('rounded-full');
  });

  it('sm with explicit showLabel=true shows the label', () => {
    render(<ConfidenceBadge level="raw" size="sm" showLabel />);
    expect(screen.getByText('Source brute')).toBeInTheDocument();
  });

  it('md with explicit showLabel=false shows only dot', () => {
    render(<ConfidenceBadge level="validated" size="md" showLabel={false} />);
    const badge = screen.getByTestId('confidence-badge-validated');
    expect(badge.textContent).toBe('');
  });

  it('inherited level includes source in tooltip', () => {
    render(<ConfidenceBadge level="inherited" size="md" source="Diagnostic 2022" date="2022-06-15" />);
    const badge = screen.getByTestId('confidence-badge-inherited');
    const title = badge.getAttribute('title');
    expect(title).toContain('Source: Diagnostic 2022');
    expect(title).toContain('Date: 2022-06-15');
  });

  it('inherited level without source/date uses default description', () => {
    render(<ConfidenceBadge level="inherited" size="md" />);
    const badge = screen.getByTestId('confidence-badge-inherited');
    expect(badge.getAttribute('title')).toBe('Reutilise depuis un cycle precedent');
  });

  it('custom tooltip overrides default description', () => {
    render(<ConfidenceBadge level="raw" tooltip="Custom info" />);
    const badge = screen.getByTestId('confidence-badge-raw');
    expect(badge.getAttribute('title')).toBe('Custom info');
  });
});
