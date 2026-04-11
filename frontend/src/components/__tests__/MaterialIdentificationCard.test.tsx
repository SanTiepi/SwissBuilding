import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MaterialIdentificationCard } from '../MaterialIdentificationCard';
import type { MaterialRecognitionResult } from '@/api/materialRecognition';

describe('MaterialIdentificationCard', () => {
  const highRiskResult: MaterialRecognitionResult = {
    material_type: 'vinyl',
    material_name: 'Revêtement vinyle ancien',
    estimated_year_range: '1970-1980',
    identified_materials: ['vinyle', 'colle bitumineuse'],
    likely_pollutants: {
      asbestos: { probability: 0.75, reason: 'Vinyle pré-1980 contient fréquemment de l\'amiante' },
      pcb: { probability: 0.2, reason: 'Faible probabilité pour ce type' },
      lead: { probability: 0.05, reason: 'Pas typique pour du vinyle' },
    },
    confidence_overall: 0.82,
    recommendations: ['Recommande test laboratoire amiante avant travaux'],
    description: 'Revêtement de sol en vinyle typique des années 1970',
    has_high_risk: true,
  };

  const lowRiskResult: MaterialRecognitionResult = {
    material_type: 'beton',
    material_name: 'Béton moderne',
    estimated_year_range: '2010-2020',
    identified_materials: ['béton armé'],
    likely_pollutants: {
      asbestos: { probability: 0.01, reason: 'Construction récente' },
    },
    confidence_overall: 0.9,
    recommendations: ['Aucun risque polluant détecté'],
    description: 'Béton armé moderne sans risque pollutant',
    has_high_risk: false,
  };

  it('renders material name', () => {
    render(<MaterialIdentificationCard result={highRiskResult} />);
    expect(screen.getByText('Revêtement vinyle ancien')).toBeInTheDocument();
  });

  it('renders confidence badge', () => {
    render(<MaterialIdentificationCard result={highRiskResult} />);
    expect(screen.getByText(/82%/)).toBeInTheDocument();
  });

  it('renders description', () => {
    render(<MaterialIdentificationCard result={highRiskResult} />);
    expect(screen.getByText(/vinyle typique des années 1970/)).toBeInTheDocument();
  });

  it('renders estimated year range', () => {
    render(<MaterialIdentificationCard result={highRiskResult} />);
    expect(screen.getByText('1970-1980')).toBeInTheDocument();
  });

  it('renders identified materials', () => {
    render(<MaterialIdentificationCard result={highRiskResult} />);
    expect(screen.getByText('vinyle, colle bitumineuse')).toBeInTheDocument();
  });

  it('shows high risk alert when has_high_risk is true', () => {
    render(<MaterialIdentificationCard result={highRiskResult} />);
    expect(screen.getByText(/Risque polluant élevé/)).toBeInTheDocument();
  });

  it('does not show high risk alert when has_high_risk is false', () => {
    render(<MaterialIdentificationCard result={lowRiskResult} />);
    expect(screen.queryByText(/Risque polluant élevé/)).not.toBeInTheDocument();
  });

  it('renders pollutant labels sorted by probability', () => {
    render(<MaterialIdentificationCard result={highRiskResult} />);
    expect(screen.getByText(/Amiante 75%/)).toBeInTheDocument();
    expect(screen.getByText(/PCB 20%/)).toBeInTheDocument();
    expect(screen.getByText(/Plomb 5%/)).toBeInTheDocument();
  });

  it('renders recommendations', () => {
    render(<MaterialIdentificationCard result={highRiskResult} />);
    expect(screen.getByText('Recommande test laboratoire amiante avant travaux')).toBeInTheDocument();
  });

  it('renders high confidence badge for 90%', () => {
    render(<MaterialIdentificationCard result={lowRiskResult} />);
    expect(screen.getByText(/Haute/)).toBeInTheDocument();
  });

  it('renders pollutant reasons', () => {
    render(<MaterialIdentificationCard result={highRiskResult} />);
    expect(screen.getByText(/Vinyle pré-1980/)).toBeInTheDocument();
  });

  it('skips pollutants with 0% probability', () => {
    const withZero: MaterialRecognitionResult = {
      ...lowRiskResult,
      likely_pollutants: {
        asbestos: { probability: 0, reason: 'None' },
        pcb: { probability: 0.3, reason: 'Some risk' },
      },
    };
    render(<MaterialIdentificationCard result={withZero} />);
    expect(screen.queryByText(/Amiante 0%/)).not.toBeInTheDocument();
    expect(screen.getByText(/PCB 30%/)).toBeInTheDocument();
  });
});
