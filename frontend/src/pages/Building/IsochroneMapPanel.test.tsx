import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Set env before any module loads
(import.meta.env as Record<string, string>).VITE_MAPBOX_TOKEN = 'pk_test_fake';

// Mock mapbox-gl with proper constructor functions
vi.mock('mapbox-gl', () => {
  function MockMap() {
    return {
      addControl: vi.fn(),
      on: vi.fn(),
      remove: vi.fn(),
      isStyleLoaded: vi.fn().mockReturnValue(false),
      addSource: vi.fn(),
      addLayer: vi.fn(),
      getLayer: vi.fn().mockReturnValue(null),
      getSource: vi.fn().mockReturnValue(null),
      removeLayer: vi.fn(),
      removeSource: vi.fn(),
    };
  }
  function MockMarker() {
    return {
      setLngLat: vi.fn().mockReturnThis(),
      addTo: vi.fn().mockReturnThis(),
      remove: vi.fn(),
    };
  }
  function MockNavigationControl() {}
  return {
    default: {
      Map: MockMap,
      Marker: MockMarker,
      NavigationControl: MockNavigationControl,
      accessToken: '',
    },
  };
});

// Mock useIsochrone
const mockUseIsochrone = vi.fn();
vi.mock('@/hooks/useIsochrone', () => ({
  useIsochrone: (...args: unknown[]) => mockUseIsochrone(...args),
}));

import IsochroneMapPanel from './IsochroneMapPanel';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('IsochroneMapPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders header and controls', () => {
    mockUseIsochrone.mockReturnValue({ data: null, isLoading: false, isError: false, error: null });
    render(<IsochroneMapPanel buildingId="abc" latitude={46.52} longitude={6.63} />, { wrapper });

    expect(screen.getByText('Mobilité & Isochrones')).toBeInTheDocument();
    expect(screen.getByText('A pied')).toBeInTheDocument();
    expect(screen.getByText('5 min')).toBeInTheDocument();
    expect(screen.getByText('10 min')).toBeInTheDocument();
    expect(screen.getByText('15 min')).toBeInTheDocument();
  });

  it('shows loading spinner when fetching', () => {
    mockUseIsochrone.mockReturnValue({ data: null, isLoading: true, isError: false, error: null });
    render(<IsochroneMapPanel buildingId="abc" latitude={46.52} longitude={6.63} />, { wrapper });

    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeTruthy();
  });

  it('shows error message on failure', () => {
    mockUseIsochrone.mockReturnValue({
      data: null,
      isLoading: false,
      isError: true,
      error: new Error('Network failed'),
    });
    render(<IsochroneMapPanel buildingId="abc" latitude={46.52} longitude={6.63} />, { wrapper });

    expect(screen.getByText('Network failed')).toBeInTheDocument();
  });

  it('shows API-level error from data', () => {
    mockUseIsochrone.mockReturnValue({
      data: { error: 'MAPBOX_API_KEY not configured', contours: [], mobility_score: null },
      isLoading: false,
      isError: false,
      error: null,
    });
    render(<IsochroneMapPanel buildingId="abc" latitude={46.52} longitude={6.63} />, { wrapper });

    expect(screen.getByText('MAPBOX_API_KEY not configured')).toBeInTheDocument();
  });

  it('renders mobility score from API response', () => {
    mockUseIsochrone.mockReturnValue({
      data: {
        contours: [
          { minutes: 5, profile: 'walking', geometry: {} },
          { minutes: 10, profile: 'walking', geometry: {} },
          { minutes: 15, profile: 'walking', geometry: {} },
        ],
        mobility_score: 10,
        error: null,
        cached: false,
      },
      isLoading: false,
      isError: false,
      error: null,
    });
    render(<IsochroneMapPanel buildingId="abc" latitude={46.52} longitude={6.63} />, { wrapper });

    expect(screen.getByText('10/10')).toBeInTheDocument();
  });

  it('switches profile on click', () => {
    mockUseIsochrone.mockReturnValue({ data: null, isLoading: false, isError: false, error: null });
    render(<IsochroneMapPanel buildingId="abc" latitude={46.52} longitude={6.63} />, { wrapper });

    fireEvent.click(screen.getByText('Vélo'));
    // After click, useIsochrone is re-called with cycling profile
    const calls = mockUseIsochrone.mock.calls;
    const lastCall = calls[calls.length - 1];
    expect(lastCall[0]).toBe('abc');
    expect(lastCall[1]).toBe('cycling');
  });

  it('shows cached indicator', () => {
    mockUseIsochrone.mockReturnValue({
      data: {
        contours: [],
        error: null,
        cached: true,
        mobility_score: null,
      },
      isLoading: false,
      isError: false,
      error: null,
    });
    render(<IsochroneMapPanel buildingId="abc" latitude={46.52} longitude={6.63} />, { wrapper });

    expect(screen.getByText('Données en cache')).toBeInTheDocument();
  });
});
