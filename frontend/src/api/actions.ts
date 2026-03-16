import { apiClient } from '@/api/client';
import type { ActionItem } from '@/types';

export interface ActionFilters {
  status?: string;
  priority?: string;
  assigned_to?: string;
  building_id?: string;
  limit?: number;
  offset?: number;
}

export const actionsApi = {
  list: async (filters?: ActionFilters): Promise<ActionItem[]> => {
    const response = await apiClient.get<ActionItem[]>('/actions', { params: filters });
    return response.data;
  },

  listByBuilding: async (buildingId: string): Promise<ActionItem[]> => {
    const response = await apiClient.get<ActionItem[]>(`/buildings/${buildingId}/actions`);
    return response.data;
  },

  create: async (buildingId: string, data: Partial<ActionItem>): Promise<ActionItem> => {
    const response = await apiClient.post<ActionItem>(`/buildings/${buildingId}/actions`, data);
    return response.data;
  },

  update: async (id: string, data: Partial<ActionItem>): Promise<ActionItem> => {
    const response = await apiClient.put<ActionItem>(`/actions/${id}`, data);
    return response.data;
  },
};
