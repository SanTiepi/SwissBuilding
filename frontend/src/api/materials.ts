import { apiClient } from '@/api/client';
import type { Material } from '@/types';

export const materialsApi = {
  list: async (buildingId: string, zoneId: string, elementId: string): Promise<Material[]> => {
    const response = await apiClient.get<Material[]>(
      `/buildings/${buildingId}/zones/${zoneId}/elements/${elementId}/materials`,
    );
    return response.data;
  },
  create: async (buildingId: string, zoneId: string, elementId: string, data: Partial<Material>): Promise<Material> => {
    const response = await apiClient.post<Material>(
      `/buildings/${buildingId}/zones/${zoneId}/elements/${elementId}/materials`,
      data,
    );
    return response.data;
  },
  get: async (buildingId: string, zoneId: string, elementId: string, materialId: string): Promise<Material> => {
    const response = await apiClient.get<Material>(
      `/buildings/${buildingId}/zones/${zoneId}/elements/${elementId}/materials/${materialId}`,
    );
    return response.data;
  },
  update: async (
    buildingId: string,
    zoneId: string,
    elementId: string,
    materialId: string,
    data: Partial<Material>,
  ): Promise<Material> => {
    const response = await apiClient.put<Material>(
      `/buildings/${buildingId}/zones/${zoneId}/elements/${elementId}/materials/${materialId}`,
      data,
    );
    return response.data;
  },
  delete: async (buildingId: string, zoneId: string, elementId: string, materialId: string): Promise<void> => {
    await apiClient.delete(`/buildings/${buildingId}/zones/${zoneId}/elements/${elementId}/materials/${materialId}`);
  },
};
