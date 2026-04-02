import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TrustScorePanel } from '../TrustScorePanel';
import * as useTrustScoreHook from '@/hooks/useTrustScore';

vi.mock('@/hooks/useTrustScore');
vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

const baseMock = {
  breakdown: [],
  history: [],
  trend: null,
  isLoading: false,
  isError: false,
  raw: null,
};

describe('TrustScorePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    vi.spyOn(useTrustScoreHook, 'useTrustScore').mockReturnValue({
      ...baseMock,
      score: undefined,
      isLoading: true,
    });

    render(<TrustScorePanel buildingId="test-id" />);
    // AsyncStateWrapper shows loading indicator
    expect(document.querySelector('[class*="animate"]')).toBeTruthy();
  });

  it('renders empty state when no score', () => {
    vi.spyOn(useTrustScoreHook, 'useTrustScore').mockReturnValue({
      ...baseMock,
      score: undefined,
    });

    render(<TrustScorePanel buildingId="test-id" />);
    expect(screen.getByText(/trust_score.no_score/i)).toBeInTheDocument();
  });

  it('renders high trust score (green)', () => {
    vi.spyOn(useTrustScoreHook, 'useTrustScore').mockReturnValue({
      ...baseMock,
      score: 85,
      breakdown: [{ label: 'Source fiabilité', value: 20, max: 25, key: 'proven' }],
      history: [80, 82, 85],
      trend: 'improving',
    });

    render(<TrustScorePanel buildingId="test-id" />);
    expect(screen.getByText('85')).toBeInTheDocument();
    expect(screen.getByText(/Trust élevé/i)).toBeInTheDocument();
  });

  it('renders medium trust score (amber)', () => {
    vi.spyOn(useTrustScoreHook, 'useTrustScore').mockReturnValue({
      ...baseMock,
      score: 55,
      breakdown: [{ label: 'Source fiabilité', value: 15, max: 25, key: 'proven' }],
    });

    render(<TrustScorePanel buildingId="test-id" />);
    expect(screen.getByText('55')).toBeInTheDocument();
    expect(screen.getByText(/Trust modéré/i)).toBeInTheDocument();
  });

  it('renders low trust score (red)', () => {
    vi.spyOn(useTrustScoreHook, 'useTrustScore').mockReturnValue({
      ...baseMock,
      score: 35,
      breakdown: [{ label: 'Source fiabilité', value: 5, max: 25, key: 'proven' }],
    });

    render(<TrustScorePanel buildingId="test-id" />);
    expect(screen.getByText('35')).toBeInTheDocument();
    expect(screen.getByText(/Trust bas/i)).toBeInTheDocument();
  });

  it('displays breakdown components with progress bars', () => {
    vi.spyOn(useTrustScoreHook, 'useTrustScore').mockReturnValue({
      ...baseMock,
      score: 70,
      breakdown: [
        { label: 'Source fiabilité', value: 25, max: 30, key: 'proven' },
        { label: 'Récence données', value: 20, max: 25, key: 'recency' },
      ],
    });

    render(<TrustScorePanel buildingId="test-id" />);
    expect(screen.getByText('Source fiabilité')).toBeInTheDocument();
    expect(screen.getByText('Récence données')).toBeInTheDocument();
    expect(screen.getByText('25/30')).toBeInTheDocument();
    expect(screen.getByText('20/25')).toBeInTheDocument();
  });

  it('displays history sparkline bars', () => {
    vi.spyOn(useTrustScoreHook, 'useTrustScore').mockReturnValue({
      ...baseMock,
      score: 78,
      history: [72, 74, 75, 77, 78],
    });

    render(<TrustScorePanel buildingId="test-id" />);
    expect(screen.getByText(/Évolution/i)).toBeInTheDocument();
    // 5 sparkline bars rendered
    const bars = document.querySelectorAll('[title]');
    expect(bars.length).toBeGreaterThanOrEqual(5);
  });

  it('displays trend information', () => {
    vi.spyOn(useTrustScoreHook, 'useTrustScore').mockReturnValue({
      ...baseMock,
      score: 80,
      trend: 'improving',
    });

    render(<TrustScorePanel buildingId="test-id" />);
    expect(screen.getByText(/Amélioration/i)).toBeInTheDocument();
  });
});
