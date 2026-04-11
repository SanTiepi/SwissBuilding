import { apiClient } from '@/api/client';

export interface EgidLookupResult {
  found: boolean;
  egid: number;
  address: string | null;
  postal_code: string | null;
  city: string | null;
  canton: string | null;
  municipality_ofs: number | null;
  latitude: number | null;
  longitude: number | null;
  construction_year: number | null;
  building_type: string | null;
  floors_above: number | null;
  surface_area_m2: number | null;
  source_metadata: Record<string, unknown> | null;
  has_address: boolean;
  has_coordinates: boolean;
  has_construction_year: boolean;
  has_building_type: boolean;
  has_floors: boolean;
  has_surface_area: boolean;
}

export interface OnboardingCreateRequest {
  egid: number;
  address: string;
  postal_code: string;
  city: string;
  canton: string;
  municipality_ofs?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  construction_year?: number | null;
  building_type?: string;
  floors_above?: number | null;
  surface_area_m2?: number | null;
  source_metadata?: Record<string, unknown> | null;
}

export interface OnboardingCreateResult {
  id: string;
  address: string;
  city: string;
  canton: string;
  egid: number;
}

export const onboardingApi = {
  lookupEgid: async (egid: number): Promise<EgidLookupResult> => {
    const response = await apiClient.post<EgidLookupResult>('/onboarding/egid-lookup', { egid });
    return response.data;
  },

  createBuilding: async (data: OnboardingCreateRequest): Promise<OnboardingCreateResult> => {
    const response = await apiClient.post<OnboardingCreateResult>('/onboarding/create-building', data);
    return response.data;
  },
};
