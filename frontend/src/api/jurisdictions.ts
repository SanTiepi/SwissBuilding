import { apiClient } from '@/api/client';
import type { PaginatedResponse, Jurisdiction, RegulatoryPack } from '@/types';

export interface JurisdictionFilters {
  page?: number;
  size?: number;
  parent_id?: string;
  level?: string;
  is_active?: string;
}

export const jurisdictionsApi = {
  list: async (params?: JurisdictionFilters): Promise<PaginatedResponse<Jurisdiction>> => {
    const response = await apiClient.get<PaginatedResponse<Jurisdiction>>('/jurisdictions', { params });
    return response.data;
  },

  get: async (id: string): Promise<Jurisdiction> => {
    const response = await apiClient.get<Jurisdiction>(`/jurisdictions/${id}`);
    return response.data;
  },

  create: async (data: Partial<Jurisdiction>): Promise<Jurisdiction> => {
    const response = await apiClient.post<Jurisdiction>('/jurisdictions', data);
    return response.data;
  },

  update: async (id: string, data: Partial<Jurisdiction>): Promise<Jurisdiction> => {
    const response = await apiClient.put<Jurisdiction>(`/jurisdictions/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/jurisdictions/${id}`);
  },

  listPacks: async (jurisdictionId: string): Promise<RegulatoryPack[]> => {
    const response = await apiClient.get<RegulatoryPack[]>(`/jurisdictions/${jurisdictionId}/regulatory-packs`);
    return response.data;
  },

  createPack: async (jurisdictionId: string, data: Partial<RegulatoryPack>): Promise<RegulatoryPack> => {
    const response = await apiClient.post<RegulatoryPack>(`/jurisdictions/${jurisdictionId}/regulatory-packs`, data);
    return response.data;
  },

  updatePack: async (
    jurisdictionId: string,
    packId: string,
    data: Partial<RegulatoryPack>,
  ): Promise<RegulatoryPack> => {
    const response = await apiClient.put<RegulatoryPack>(
      `/jurisdictions/${jurisdictionId}/regulatory-packs/${packId}`,
      data,
    );
    return response.data;
  },

  deletePack: async (jurisdictionId: string, packId: string): Promise<void> => {
    await apiClient.delete(`/jurisdictions/${jurisdictionId}/regulatory-packs/${packId}`);
  },
};
