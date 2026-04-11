import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import RegistryEnrichment from '@/components/RegistryEnrichment';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/api/registry', () => ({
  registryApi: {
    lookupByEgid: vi.fn().mockResolvedValue({
      egid: 123456,
      source: 'regbl',
      address: 'Rue du Midi 15',
      postal_code: '1003',
      city: 'Lausanne',
      canton: 'VD',
      construction_year: 1965,
      floors: 4,
      coordinates: { lat: 46.519, lng: 6.632 },
    }),
    searchByAddress: vi.fn().mockResolvedValue([
      { source: 'swisstopo', address: 'Rue du Midi 15, 1003 Lausanne', egid: 123456 },
    ]),
    getNaturalHazards: vi.fn().mockResolvedValue({
      flood_risk: { level: 'low', description: 'Low risk' },
      landslide_risk: null,
      avalanche_risk: null,
      earthquake_risk: null,
    }),
    enrichBuilding: vi.fn().mockResolvedValue({
      building_id: 'b-1',
      updated_fields: { construction_year: 1965 },
      source: 'regbl+geo.admin',
      egid_found: true,
      hazards_fetched: true,
    }),
  },
}));

describe('RegistryEnrichment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders lookup fields and enrich button', () => {
    render(<RegistryEnrichment buildingId="b-1" />);

    expect(screen.getByText('registry.title')).toBeTruthy();
    expect(screen.getByText('registry.lookup_egid')).toBeTruthy();
    expect(screen.getByPlaceholderText('e.g. 1234567')).toBeTruthy();
    expect(screen.getByPlaceholderText('Rue du Midi 15, Lausanne')).toBeTruthy();
    expect(screen.getByText('registry.enrich')).toBeTruthy();
  });

  it('performs EGID search and shows preview', async () => {
    const { registryApi } = await import('@/api/registry');
    render(<RegistryEnrichment buildingId="b-1" />);

    const egidInput = screen.getByPlaceholderText('e.g. 1234567');
    fireEvent.change(egidInput, { target: { value: '123456' } });

    // Find the first search button (EGID section)
    const buttons = screen.getAllByText('registry.search_address');
    fireEvent.click(buttons[0]);

    await waitFor(() => {
      expect(registryApi.lookupByEgid).toHaveBeenCalledWith(123456);
    });

    await waitFor(() => {
      expect(screen.getByText('registry.preview')).toBeTruthy();
      expect(screen.getByText('Rue du Midi 15')).toBeTruthy();
    });
  });

  it('triggers enrichment on button click', async () => {
    const { registryApi } = await import('@/api/registry');
    render(<RegistryEnrichment buildingId="b-1" />);

    const enrichBtn = screen.getByText('registry.enrich');
    fireEvent.click(enrichBtn);

    await waitFor(() => {
      expect(registryApi.enrichBuilding).toHaveBeenCalledWith('b-1');
    });

    await waitFor(() => {
      expect(screen.getByText(/registry\.enriched/)).toBeTruthy();
    });
  });
});
