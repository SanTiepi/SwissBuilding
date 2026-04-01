import { apiClient } from '@/api/client';

export interface GeoLayerResult {
  source: string;
  label: string;
  raw_attributes: Record<string, unknown>;
  zone?: string | null;
  value?: string | null;
  level_db?: number | string | null;
  suitability?: string | null;
  potential_kwh?: number | string | null;
  hazard_level?: string | null;
  zone_type?: string | null;
  status?: string | null;
  category?: string | null;
  name?: string | null;
  quality_class?: string | null;
  network_name?: string | null;
}

export interface GeoContextResponse {
  context: Record<string, GeoLayerResult>;
  fetched_at: string | null;
  source_version: string | null;
  cached: boolean;
  error?: string | null;
  detail?: string | null;
}

export const geoContextApi = {
  get: async (buildingId: string): Promise<GeoContextResponse> => {
    const response = await apiClient.get<GeoContextResponse>(`/buildings/${buildingId}/geo-context`);
    return response.data;
  },

  refresh: async (buildingId: string): Promise<GeoContextResponse> => {
    const response = await apiClient.post<GeoContextResponse>(`/buildings/${buildingId}/geo-context/refresh`);
    return response.data;
  },
};
