import { apiClient } from '@/api/client';
import type { Building, PaginatedResponse, ActivityItem } from '@/types';

export interface BuildingFilters {
  page?: number;
  size?: number;
  canton?: string;
  city?: string;
  postal_code?: string;
  building_type?: string;
  year_from?: number;
  year_to?: number;
  search?: string;
}

export const buildingsApi = {
  list: async (filters?: BuildingFilters): Promise<PaginatedResponse<Building>> => {
    const response = await apiClient.get<PaginatedResponse<Building>>('/buildings', {
      params: filters,
    });
    return response.data;
  },

  get: async (id: string): Promise<Building> => {
    const response = await apiClient.get<Building>(`/buildings/${id}`);
    return response.data;
  },

  create: async (data: Partial<Building>): Promise<Building> => {
    const response = await apiClient.post<Building>('/buildings', data);
    return response.data;
  },

  update: async (id: string, data: Partial<Building>): Promise<Building> => {
    const response = await apiClient.put<Building>(`/buildings/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/buildings/${id}`);
  },

  getActivity: async (id: string, limit = 50, offset = 0): Promise<ActivityItem[]> => {
    const response = await apiClient.get<ActivityItem[]>(`/buildings/${id}/activity`, {
      params: { limit, offset },
    });
    return response.data;
  },
};
