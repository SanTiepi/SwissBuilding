import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGet = vi.fn();
const mockRefresh = vi.fn();

vi.mock('@/api/geoContext', () => ({
  geoContextApi: {
    get: (...args: unknown[]) => mockGet(...args),
    refresh: (...args: unknown[]) => mockRefresh(...args),
  },
}));

// Must import after mocks
import GeoContextPanel from '../building-detail/GeoContextPanel';

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('GeoContextPanel', () => {
  it('shows loading state', () => {
    mockGet.mockReturnValue(new Promise(() => {})); // never resolves
    render(<GeoContextPanel buildingId="test-id" />, { wrapper });
    expect(screen.getByText('geo_context.loading')).toBeInTheDocument();
  });

  it('shows error state', async () => {
    mockGet.mockRejectedValue(new Error('fail'));
    render(<GeoContextPanel buildingId="test-id" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('geo_context.error')).toBeInTheDocument();
    });
  });

  it('renders 7 category headers when data is present', async () => {
    mockGet.mockResolvedValue({
      context: {
        radon: { source: 'ch.bag.radonkarte', label: 'Radon', raw_attributes: {}, zone: 'moderate' },
        noise_road: { source: 'ch.bafu.laerm-strassenlaerm_tag', label: 'Bruit routier', raw_attributes: {}, level_db: 55 },
        seismic: { source: 'ch.bafu.erdbeben-erdbebenzonen', label: 'Zone sismique', raw_attributes: {}, zone: 'Z2' },
      },
      fetched_at: '2026-04-01T10:00:00Z',
      source_version: 'geo.admin-v1',
      cached: false,
      risk_score: { score: 22, inondation: 4, seismic: 4, grele: 0, contamination: 0, radon: 3 },
    });

    render(<GeoContextPanel buildingId="test-id" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('geo_context.cat_natural_risks')).toBeInTheDocument();
    });

    expect(screen.getByText('geo_context.cat_environment')).toBeInTheDocument();
    expect(screen.getByText('geo_context.cat_noise')).toBeInTheDocument();
    expect(screen.getByText('geo_context.cat_heritage')).toBeInTheDocument();
    expect(screen.getByText('geo_context.cat_energy')).toBeInTheDocument();
    expect(screen.getByText('geo_context.cat_infrastructure')).toBeInTheDocument();
    expect(screen.getByText('geo_context.cat_geology')).toBeInTheDocument();
  });

  it('renders risk score when present', async () => {
    mockGet.mockResolvedValue({
      context: {
        radon: { source: 'ch.bag.radonkarte', label: 'Radon', raw_attributes: {}, zone: 'hoch' },
      },
      fetched_at: '2026-04-01T10:00:00Z',
      source_version: 'geo.admin-v1',
      cached: false,
      risk_score: { score: 42, inondation: 4, seismic: 6, grele: 2, contamination: 5, radon: 4 },
    });

    render(<GeoContextPanel buildingId="test-id" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('42/100')).toBeInTheDocument();
    });
  });

  it('renders layer count badge', async () => {
    mockGet.mockResolvedValue({
      context: {
        radon: { source: 'ch.bag.radonkarte', label: 'Radon', raw_attributes: {}, zone: 'low' },
        solar: { source: 'ch.bfe.solarenergie-eignung-daecher', label: 'Solaire', raw_attributes: {}, potential_kwh: 1200 },
      },
      fetched_at: '2026-04-01T10:00:00Z',
      source_version: 'geo.admin-v1',
      cached: false,
    });

    render(<GeoContextPanel buildingId="test-id" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('2/24')).toBeInTheDocument();
    });
  });

  it('shows no data message when context is empty', async () => {
    mockGet.mockResolvedValue({
      context: {},
      fetched_at: null,
      source_version: null,
      cached: false,
    });

    render(<GeoContextPanel buildingId="test-id" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('geo_context.no_data')).toBeInTheDocument();
    });
  });
});
