import { apiClient } from '@/api/client';
import type { BuildingElement, PaginatedResponse } from '@/types';

export const elementsApi = {
  list: async (
    buildingId: string,
    zoneId: string,
    params?: { page?: number; size?: number; element_type?: string },
  ): Promise<PaginatedResponse<BuildingElement>> => {
    const response = await apiClient.get<PaginatedResponse<BuildingElement>>(
      `/buildings/${buildingId}/zones/${zoneId}/elements`,
      { params },
    );
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
