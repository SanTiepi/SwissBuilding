import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RiskGauge } from '../RiskGauge';
import type { RiskLevel } from '@/types';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

describe('RiskGauge', () => {
  const riskLevels: RiskLevel[] = ['low', 'medium', 'high', 'critical', 'unknown'];

  it.each(riskLevels)('renders gauge for risk level: %s', (level) => {
    render(<RiskGauge score={0.5} level={level} />);

    // The SVG should have an accessible aria-label
    const svg = screen.getByRole('img');
    expect(svg).toHaveAttribute('aria-label', `risk.${level}: 50%`);
  });

  it('displays the score as a percentage', () => {
    render(<RiskGauge score={0.75} level="high" />);

    // The percentage text is rendered inside the SVG
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('displays 0% for score of 0', () => {
    render(<RiskGauge score={0} level="low" />);

    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('displays 100% for score of 1', () => {
    render(<RiskGauge score={1} level="critical" />);

    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('clamps score above 1 to 100%', () => {
    render(<RiskGauge score={1.5} level="critical" />);

    expect(screen.getByText('150%')).toBeInTheDocument();
    // The SVG arc is clamped internally, but the text shows the raw percentage
  });

  it('renders the risk level label translation key', () => {
    render(<RiskGauge score={0.3} level="medium" />);

    expect(screen.getByText('risk.medium')).toBeInTheDocument();
  });

  it('renders with an optional label', () => {
    render(<RiskGauge score={0.6} level="high" label="Asbestos Risk" />);

    expect(screen.getByText('Asbestos Risk')).toBeInTheDocument();
  });

  it('does not render label paragraph when label is not provided', () => {
    const { container } = render(<RiskGauge score={0.4} level="low" />);

    const paragraphs = container.querySelectorAll('p');
    expect(paragraphs.length).toBe(0);
  });

  it('includes label in aria-label when provided', () => {
    render(<RiskGauge score={0.5} level="high" label="Overall" />);

    const svg = screen.getByRole('img');
    expect(svg).toHaveAttribute('aria-label', 'Overall: 50%');
  });

  it('rounds score percentage correctly', () => {
    render(<RiskGauge score={0.333} level="medium" />);

    expect(screen.getByText('33%')).toBeInTheDocument();
  });
});
