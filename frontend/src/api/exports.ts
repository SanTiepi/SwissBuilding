import { apiClient } from '@/api/client';
import type { ExportJob, PaginatedResponse } from '@/types';

export const exportsApi = {
  list: async (params?: { status?: string; page?: number; size?: number }): Promise<PaginatedResponse<ExportJob>> => {
    const response = await apiClient.get<PaginatedResponse<ExportJob>>('/exports', { params });
    return response.data;
  },
  get: async (id: string): Promise<ExportJob> => {
    const response = await apiClient.get<ExportJob>(`/exports/${id}`);
    return response.data;
  },
  create: async (data: { type: string; building_id?: string; organization_id?: string }): Promise<ExportJob> => {
    const response = await apiClient.post<ExportJob>('/exports', data);
    return response.data;
  },
  cancel: async (id: string): Promise<void> => {
    await apiClient.delete(`/exports/${id}`);
  },
};
