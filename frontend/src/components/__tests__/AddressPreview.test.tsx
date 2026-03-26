import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { intelligenceApi } from '@/api/intelligence';
import AddressPreview from '@/pages/AddressPreview';

vi.mock('@/api/intelligence', () => ({
  intelligenceApi: {
    postAddressPreview: vi.fn(),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ user: { id: 'u-1', role: 'admin' }, isAuthenticated: true }),
}));

const mockResult = {
  identity: {
    egid: 12345,
    egrid: 'CH123',
    parcel: '1234',
    address_normalized: 'Rue du Midi 15 1003 Lausanne',
    lat: 46.519,
    lon: 6.632,
  },
  physical: {
    construction_year: 1965,
    floors: 4,
    dwellings: 12,
    surface_m2: 800,
    heating_type: 'gas',
  },
  environment: { radon: { level: 'medium' }, noise: null, hazards: null, seismic: null },
  energy: { solar_potential: { kwh: 15000 }, heating_type: 'gas', district_heating_available: false },
  transport: { quality_class: 'B', nearest_stops: [], ev_charging: null },
  risk: {
    pollutant_prediction: { asbestos: 0.85, pcb: 0.6 },
    environmental_score: 5.5,
  },
  scores: { neighborhood: 0.72, livability: 0.68, connectivity: 0.81, overall_grade: 'C' },
  lifecycle: { components: [], critical_count: 0, urgent_count: 0 },
  renovation: { plan_summary: 'Renovation facade + isolation', total_cost: 120000, total_subsidy: 30000, roi_years: 8 },
  compliance: { checks_count: 5, non_compliant_count: 1, summary: null },
  financial: { cost_of_inaction: 45000, energy_savings: 3500, value_increase: 8 },
  narrative: { summary_fr: 'Batiment de 1965 necessitant un diagnostic amiante.' },
  metadata: { sources_used: ['geo.admin.ch/geocode', 'geo.admin.ch/gwr'], freshness: 'current', run_id: null },
};

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AddressPreview />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AddressPreview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders hero title and address input', () => {
    renderPage();
    expect(screen.getByTestId('hero-title')).toBeInTheDocument();
    expect(screen.getByTestId('address-input')).toBeInTheDocument();
    expect(screen.getByTestId('discover-button')).toBeInTheDocument();
  });

  it('renders postal code and city inputs', () => {
    renderPage();
    expect(screen.getByTestId('postal-code-input')).toBeInTheDocument();
    expect(screen.getByTestId('city-input')).toBeInTheDocument();
  });

  it('discover button is disabled when address is empty', () => {
    renderPage();
    const btn = screen.getByTestId('discover-button');
    expect(btn).toBeDisabled();
  });

  it('shows result after successful search', async () => {
    vi.mocked(intelligenceApi.postAddressPreview).mockResolvedValue(mockResult);
    renderPage();

    fireEvent.change(screen.getByTestId('address-input'), { target: { value: 'Rue du Midi 15' } });
    fireEvent.click(screen.getByTestId('discover-button'));

    await waitFor(() => {
      expect(screen.getByTestId('preview-result')).toBeInTheDocument();
    });
    expect(screen.getByTestId('scores-dashboard')).toBeInTheDocument();
    expect(screen.getByTestId('grade-badge')).toHaveTextContent('C');
  });

  it('shows error message on API failure', async () => {
    vi.mocked(intelligenceApi.postAddressPreview).mockRejectedValue(new Error('fail'));
    renderPage();

    fireEvent.change(screen.getByTestId('address-input'), { target: { value: 'Bad Address' } });
    fireEvent.click(screen.getByTestId('discover-button'));

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
    });
  });

  it('shows create building CTA after result', async () => {
    vi.mocked(intelligenceApi.postAddressPreview).mockResolvedValue(mockResult);
    renderPage();

    fireEvent.change(screen.getByTestId('address-input'), { target: { value: 'Rue du Midi 15' } });
    fireEvent.click(screen.getByTestId('discover-button'));

    await waitFor(() => {
      expect(screen.getByTestId('create-building-cta')).toBeInTheDocument();
    });
  });

  it('shows risk bars in result', async () => {
    vi.mocked(intelligenceApi.postAddressPreview).mockResolvedValue(mockResult);
    renderPage();

    fireEvent.change(screen.getByTestId('address-input'), { target: { value: 'Rue du Midi 15' } });
    fireEvent.click(screen.getByTestId('discover-button'));

    await waitFor(() => {
      const bars = screen.getAllByTestId('risk-bar');
      expect(bars.length).toBe(2);
    });
  });

  it('shows score cards for neighborhood, livability, connectivity', async () => {
    vi.mocked(intelligenceApi.postAddressPreview).mockResolvedValue(mockResult);
    renderPage();

    fireEvent.change(screen.getByTestId('address-input'), { target: { value: 'Rue du Midi 15' } });
    fireEvent.click(screen.getByTestId('discover-button'));

    await waitFor(() => {
      const cards = screen.getAllByTestId('score-card');
      expect(cards.length).toBe(3);
    });
  });
});
