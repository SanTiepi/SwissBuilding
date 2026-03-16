import { apiClient } from '@/api/client';
import type { BuildingQuality } from '@/types';

export const qualityApi = {
  get: async (buildingId: string): Promise<BuildingQuality> => {
    const response = await apiClient.get<BuildingQuality>(`/buildings/${buildingId}/quality`);
    return response.data;
  },
};
