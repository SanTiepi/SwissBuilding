import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PollutantBadge } from '../PollutantBadge';
import type { PollutantType } from '@/types';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

describe('PollutantBadge', () => {
  const pollutantTypes: PollutantType[] = ['asbestos', 'pcb', 'lead', 'hap', 'radon'];

  it.each(pollutantTypes)('renders badge for pollutant type: %s', (type) => {
    render(<PollutantBadge type={type} />);

    expect(screen.getByText(`pollutant.short.${type}`)).toBeInTheDocument();
  });

  it('renders with default "md" size', () => {
    const { container } = render(<PollutantBadge type="asbestos" />);

    const badge = container.querySelector('span');
    expect(badge).toHaveClass('px-2.5', 'py-1', 'text-xs');
  });

  it('renders with "sm" size', () => {
    const { container } = render(<PollutantBadge type="pcb" size="sm" />);

    const badge = container.querySelector('span');
    expect(badge).toHaveClass('px-2', 'py-0.5');
  });

  it('applies the correct color for asbestos (purple)', () => {
    const { container } = render(<PollutantBadge type="asbestos" />);

    const badge = container.querySelector('span');
    expect(badge).toHaveStyle({ color: '#8b5cf6' });
  });

  it('applies the correct color for pcb (blue)', () => {
    const { container } = render(<PollutantBadge type="pcb" />);

    const badge = container.querySelector('span');
    expect(badge).toHaveStyle({ color: '#3b82f6' });
  });

  it('applies the correct color for lead (amber)', () => {
    const { container } = render(<PollutantBadge type="lead" />);

    const badge = container.querySelector('span');
    expect(badge).toHaveStyle({ color: '#f59e0b' });
  });

  it('applies the correct color for hap (pink)', () => {
    const { container } = render(<PollutantBadge type="hap" />);

    const badge = container.querySelector('span');
    expect(badge).toHaveStyle({ color: '#ec4899' });
  });

  it('applies the correct color for radon (teal)', () => {
    const { container } = render(<PollutantBadge type="radon" />);

    const badge = container.querySelector('span');
    expect(badge).toHaveStyle({ color: '#14b8a6' });
  });

  it('renders the colored dot indicator', () => {
    const { container } = render(<PollutantBadge type="asbestos" />);

    // The inner dot span
    const dots = container.querySelectorAll('span span');
    const dot = dots[0];
    expect(dot).toHaveClass('rounded-full');
    expect(dot).toHaveStyle({ backgroundColor: '#8b5cf6' });
  });
});
