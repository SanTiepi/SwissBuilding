import { apiClient } from '@/api/client';
import type { BuildingElement } from '@/types';

export const elementsApi = {
  list: async (buildingId: string, zoneId: string): Promise<BuildingElement[]> => {
    const response = await apiClient.get<BuildingElement[]>(`/buildings/${buildingId}/zones/${zoneId}/elements`);
    return response.data;
  },
  get: async (buildingId: string, zoneId: string, elementId: string): Promise<BuildingElement> => {
    const response = await apiClient.get<BuildingElement>(
      `/buildings/${buildingId}/zones/${zoneId}/elements/${elementId}`,
    );
    return response.data;
  },
  create: async (buildingId: string, zoneId: string, data: Partial<BuildingElement>): Promise<BuildingElement> => {
    const response = await apiClient.post<BuildingElement>(`/buildings/${buildingId}/zones/${zoneId}/elements`, data);
    return response.data;
  },
  update: async (
    buildingId: string,
    zoneId: string,
    elementId: string,
    data: Partial<BuildingElement>,
  ): Promise<BuildingElement> => {
    const response = await apiClient.put<BuildingElement>(
      `/buildings/${buildingId}/zones/${zoneId}/elements/${elementId}`,
      data,
    );
    return response.data;
  },
  delete: async (buildingId: string, zoneId: string, elementId: string): Promise<void> => {
    await apiClient.delete(`/buildings/${buildingId}/zones/${zoneId}/elements/${elementId}`);
  },
};
