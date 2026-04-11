import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock api client
const mockGet = vi.fn();
vi.mock('@/api/client', () => ({
  apiClient: { get: (...args: unknown[]) => mockGet(...args) },
}));

import IncidentAlertPanel from './IncidentAlertPanel';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('IncidentAlertPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state initially', () => {
    mockGet.mockReturnValue(new Promise(() => {})); // never resolves
    render(<IncidentAlertPanel buildingId="abc-123" />, { wrapper });
    expect(screen.getByText(/Analyse des correlations/)).toBeTruthy();
  });

  it('shows no alerts when predictions are empty', async () => {
    mockGet.mockResolvedValue({
      data: {
        building_id: 'abc-123',
        building_risk_level: 'none',
        predicted_incidents: [],
        forecast_available: true,
        correlation_data: 'available',
      },
    });
    render(<IncidentAlertPanel buildingId="abc-123" />, { wrapper });
    expect(await screen.findByTestId('no-alerts')).toBeTruthy();
    expect(screen.getByText(/Aucune alerte/)).toBeTruthy();
  });

  it('renders prediction cards when alerts exist', async () => {
    mockGet.mockResolvedValue({
      data: {
        building_id: 'abc-123',
        building_risk_level: 'high',
        predicted_incidents: [
          {
            type: 'leak',
            trigger: 'heavy_rain >40.0mm prevu (2026-04-03)',
            probability: 0.78,
            risk_level: 'high',
            recommended_action: 'Verifier gouttieres',
            forecast_day: '2026-04-03',
          },
        ],
        forecast_available: true,
        correlation_data: 'available',
      },
    });
    render(<IncidentAlertPanel buildingId="abc-123" />, { wrapper });
    expect(await screen.findByTestId('risk-banner')).toBeTruthy();
    expect(screen.getByTestId('prediction-card')).toBeTruthy();
    expect(screen.getByText('78%')).toBeTruthy();
    expect(screen.getByText('Infiltration')).toBeTruthy();
  });

  it('shows error state on failure', async () => {
    mockGet.mockRejectedValue(new Error('Network error'));
    render(<IncidentAlertPanel buildingId="abc-123" />, { wrapper });
    expect(await screen.findByText(/Network error/)).toBeTruthy();
  });

  it('shows no-history hint when correlation_data is no_history', async () => {
    mockGet.mockResolvedValue({
      data: {
        building_id: 'abc-123',
        building_risk_level: 'none',
        predicted_incidents: [],
        forecast_available: false,
        correlation_data: 'no_history',
      },
    });
    render(<IncidentAlertPanel buildingId="abc-123" />, { wrapper });
    expect(await screen.findByText(/historique/)).toBeTruthy();
  });
});
