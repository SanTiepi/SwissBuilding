import { apiClient } from '@/api/client';

export interface RegistryLookupResult {
  egid: number;
  source: string;
  address: string | null;
  postal_code: string | null;
  city: string | null;
  canton: string | null;
  construction_year: number | null;
  building_category: string | null;
  building_class: string | null;
  floors: number | null;
  area: number | null;
  heating_type: string | null;
  energy_source: string | null;
  renovation_year: number | null;
  coordinates: { lat: number; lng: number } | null;
  raw_attributes: Record<string, unknown>;
}

export interface AddressSearchResult {
  source: string;
  address: string | null;
  postal_code: string | null;
  city: string | null;
  canton: string | null;
  lat: number | null;
  lng: number | null;
  egid: number | null;
  feature_id: string | null;
}

export interface HazardLevel {
  level: string;
  description: string | null;
  source: string | null;
}

export interface NaturalHazardsResult {
  flood_risk: HazardLevel | null;
  landslide_risk: HazardLevel | null;
  avalanche_risk: HazardLevel | null;
  earthquake_risk: HazardLevel | null;
}

export interface EnrichmentResult {
  building_id: string;
  updated_fields: Record<string, unknown>;
  source: string;
  egid_found: boolean;
  hazards_fetched: boolean;
}

export const registryApi = {
  lookupByEgid: async (egid: number): Promise<RegistryLookupResult> => {
    const response = await apiClient.get<RegistryLookupResult>(`/registry/lookup/egid/${egid}`);
    return response.data;
  },

  searchByAddress: async (query: string, postalCode?: string): Promise<AddressSearchResult[]> => {
    const params: Record<string, string> = { q: query };
    if (postalCode) params.postal_code = postalCode;
    const response = await apiClient.get<AddressSearchResult[]>('/registry/lookup/address', {
      params,
    });
    return response.data;
  },

  getNaturalHazards: async (lat: number, lng: number): Promise<NaturalHazardsResult> => {
    const response = await apiClient.get<NaturalHazardsResult>('/registry/hazards', {
      params: { lat, lng },
    });
    return response.data;
  },

  enrichBuilding: async (buildingId: string): Promise<EnrichmentResult> => {
    const response = await apiClient.post<EnrichmentResult>(`/buildings/${buildingId}/enrich`);
    return response.data;
  },
};
