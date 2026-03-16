import { apiClient } from '@/api/client';
import type { Intervention, PaginatedResponse } from '@/types';

export const interventionsApi = {
  list: async (
    buildingId: string,
    params?: { status?: string; intervention_type?: string; page?: number; size?: number },
  ): Promise<PaginatedResponse<Intervention>> => {
    const response = await apiClient.get<PaginatedResponse<Intervention>>(`/buildings/${buildingId}/interventions`, {
      params,
    });
    return response.data;
  },
  get: async (buildingId: string, interventionId: string): Promise<Intervention> => {
    const response = await apiClient.get<Intervention>(`/buildings/${buildingId}/interventions/${interventionId}`);
    return response.data;
  },
  create: async (buildingId: string, data: Partial<Intervention>): Promise<Intervention> => {
    const response = await apiClient.post<Intervention>(`/buildings/${buildingId}/interventions`, data);
    return response.data;
  },
  update: async (buildingId: string, interventionId: string, data: Partial<Intervention>): Promise<Intervention> => {
    const response = await apiClient.put<Intervention>(
      `/buildings/${buildingId}/interventions/${interventionId}`,
      data,
    );
    return response.data;
  },
  delete: async (buildingId: string, interventionId: string): Promise<void> => {
    await apiClient.delete(`/buildings/${buildingId}/interventions/${interventionId}`);
  },
};
