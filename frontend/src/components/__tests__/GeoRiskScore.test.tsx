import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GeoRiskScore } from '../GeoRiskScore';
import type { GeoRiskScore as GeoRiskScoreType } from '@/api/geoContext';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

describe('GeoRiskScore', () => {
  const lowRisk: GeoRiskScoreType = {
    score: 12,
    inondation: 4,
    seismic: 2,
    grele: 0,
    contamination: 0,
    radon: 0,
  };

  const highRisk: GeoRiskScoreType = {
    score: 78,
    inondation: 10,
    seismic: 8,
    grele: 6,
    contamination: 10,
    radon: 5,
  };

  it('renders composite score', () => {
    render(<GeoRiskScore riskScore={lowRisk} />);
    expect(screen.getByText('12/100')).toBeInTheDocument();
  });

  it('renders all 5 sub-dimensions', () => {
    render(<GeoRiskScore riskScore={lowRisk} />);
    expect(screen.getByText('geo_context.risk_inondation')).toBeInTheDocument();
    expect(screen.getByText('geo_context.risk_seismic')).toBeInTheDocument();
    expect(screen.getByText('geo_context.risk_grele')).toBeInTheDocument();
    expect(screen.getByText('geo_context.risk_contamination')).toBeInTheDocument();
    expect(screen.getByText('geo_context.risk_radon')).toBeInTheDocument();
  });

  it('renders high risk score', () => {
    render(<GeoRiskScore riskScore={highRisk} />);
    expect(screen.getByText('78/100')).toBeInTheDocument();
  });

  it('displays sub-score values', () => {
    render(<GeoRiskScore riskScore={lowRisk} />);
    expect(screen.getByText('4/10')).toBeInTheDocument();
    expect(screen.getByText('2/10')).toBeInTheDocument();
  });

  it('renders zero risk score', () => {
    const zeroRisk: GeoRiskScoreType = {
      score: 0,
      inondation: 0,
      seismic: 0,
      grele: 0,
      contamination: 0,
      radon: 0,
    };
    render(<GeoRiskScore riskScore={zeroRisk} />);
    expect(screen.getByText('0/100')).toBeInTheDocument();
  });
});
