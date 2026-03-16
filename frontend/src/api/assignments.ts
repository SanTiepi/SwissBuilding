import { apiClient } from '@/api/client';
import type { Assignment, PaginatedResponse } from '@/types';

export interface AssignmentFilters {
  page?: number;
  size?: number;
  target_type?: string;
  target_id?: string;
  user_id?: string;
  role?: string;
}

export interface CreateAssignmentData {
  target_type: string;
  target_id: string;
  user_id: string;
  role: string;
}

export const assignmentsApi = {
  list: async (params?: AssignmentFilters): Promise<PaginatedResponse<Assignment>> => {
    const response = await apiClient.get<PaginatedResponse<Assignment>>('/assignments', { params });
    return response.data;
  },

  create: async (data: CreateAssignmentData): Promise<Assignment> => {
    const response = await apiClient.post<Assignment>('/assignments', data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/assignments/${id}`);
  },
};
