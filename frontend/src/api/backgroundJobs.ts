import { apiClient } from '@/api/client';
import type { BackgroundJob } from '@/types';

export const backgroundJobsApi = {
  list: async (params?: {
    job_type?: string;
    status?: string;
    building_id?: string;
    limit?: number;
  }): Promise<BackgroundJob[]> => {
    const response = await apiClient.get<BackgroundJob[]>('/jobs', { params });
    return response.data;
  },
  get: async (id: string): Promise<BackgroundJob> => {
    const response = await apiClient.get<BackgroundJob>(`/jobs/${id}`);
    return response.data;
  },
  cancel: async (id: string): Promise<void> => {
    await apiClient.post(`/jobs/${id}/cancel`);
  },
};
