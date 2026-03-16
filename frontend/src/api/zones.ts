import { apiClient } from '@/api/client';
import type { Zone, PaginatedResponse } from '@/types';

export const zonesApi = {
  list: async (
    buildingId: string,
    params?: { zone_type?: string; parent_zone_id?: string; page?: number; size?: number },
  ): Promise<PaginatedResponse<Zone>> => {
    const response = await apiClient.get<PaginatedResponse<Zone>>(`/buildings/${buildingId}/zones`, { params });
    return response.data;
  },
  get: async (buildingId: string, zoneId: string): Promise<Zone> => {
    const response = await apiClient.get<Zone>(`/buildings/${buildingId}/zones/${zoneId}`);
    return response.data;
  },
  create: async (buildingId: string, data: Partial<Zone>): Promise<Zone> => {
    const response = await apiClient.post<Zone>(`/buildings/${buildingId}/zones`, data);
    return response.data;
  },
  update: async (buildingId: string, zoneId: string, data: Partial<Zone>): Promise<Zone> => {
    const response = await apiClient.put<Zone>(`/buildings/${buildingId}/zones/${zoneId}`, data);
    return response.data;
  },
  delete: async (buildingId: string, zoneId: string): Promise<void> => {
    await apiClient.delete(`/buildings/${buildingId}/zones/${zoneId}`);
  },
};
