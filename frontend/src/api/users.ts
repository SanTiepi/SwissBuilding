import { apiClient } from '@/api/client';
import type { PaginatedResponse, User } from '@/types';

export interface UserFilters {
  page?: number;
  size?: number;
  search?: string;
  role?: string;
  is_active?: string;
}

export const usersApi = {
  list: async (params?: UserFilters): Promise<PaginatedResponse<User>> => {
    const response = await apiClient.get<PaginatedResponse<User>>('/users', { params });
    return response.data;
  },

  create: async (data: Partial<User> & { password: string }): Promise<User> => {
    const response = await apiClient.post<User>('/users', data);
    return response.data;
  },

  update: async (id: string, data: Partial<User>): Promise<User> => {
    const response = await apiClient.put<User>(`/users/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/users/${id}`);
  },
};
