import { apiClient } from '@/api/client';
import type { BuildingTrustScore, PaginatedResponse } from '@/types';

export const trustScoresApi = {
  list: async (buildingId: string): Promise<PaginatedResponse<BuildingTrustScore>> => {
    const response = await apiClient.get<PaginatedResponse<BuildingTrustScore>>(
      `/buildings/${buildingId}/trust-scores`,
      { params: { size: 1 } },
    );
    return response.data;
  },
  latest: async (buildingId: string): Promise<BuildingTrustScore | null> => {
    const response = await apiClient.get<PaginatedResponse<BuildingTrustScore>>(
      `/buildings/${buildingId}/trust-scores`,
      { params: { size: 1 } },
    );
    return response.data.items[0] ?? null;
  },
  history: async (buildingId: string, count = 6): Promise<BuildingTrustScore[]> => {
    const response = await apiClient.get<PaginatedResponse<BuildingTrustScore>>(
      `/buildings/${buildingId}/trust-scores`,
      { params: { size: count } },
    );
    return response.data.items.reverse();
  },
};
