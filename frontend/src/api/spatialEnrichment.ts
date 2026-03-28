import { apiClient } from '@/api/client';

export interface SpatialEnrichmentResponse {
  footprint_wkt: string | null;
  height_m: number | null;
  roof_type: string | null;
  volume_m3: number | null;
  surface_m2: number | null;
  floors: number | null;
  source: string | null;
  source_version: string | null;
  fetched_at: string | null;
  cached: boolean;
  error?: string | null;
  detail?: string | null;
  raw_attributes: Record<string, unknown>;
}

export const spatialEnrichmentApi = {
  get: async (buildingId: string): Promise<SpatialEnrichmentResponse> => {
    const response = await apiClient.get<SpatialEnrichmentResponse>(
      `/buildings/${buildingId}/spatial-enrichment`,
    );
    return response.data;
  },

  refresh: async (buildingId: string): Promise<SpatialEnrichmentResponse> => {
    const response = await apiClient.post<SpatialEnrichmentResponse>(
      `/buildings/${buildingId}/spatial-enrichment/refresh`,
    );
    return response.data;
  },
};
