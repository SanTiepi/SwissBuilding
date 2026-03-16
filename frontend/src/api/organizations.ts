import { apiClient } from '@/api/client';
import type { Organization, PaginatedResponse, User } from '@/types';

export interface OrganizationFilters {
  page?: number;
  size?: number;
  type?: string;
}

export interface OrganizationFormData {
  name: string;
  type: string;
  address: string;
  postal_code: string;
  city: string;
  canton: string;
  phone: string;
  email: string;
  suva_recognized: boolean;
  fach_approved: boolean;
}

export const organizationsApi = {
  list: async (params?: OrganizationFilters): Promise<PaginatedResponse<Organization>> => {
    const response = await apiClient.get<PaginatedResponse<Organization>>('/organizations', { params });
    return response.data;
  },

  get: async (id: string): Promise<Organization> => {
    const response = await apiClient.get<Organization>(`/organizations/${id}`);
    return response.data;
  },

  create: async (data: OrganizationFormData): Promise<Organization> => {
    const response = await apiClient.post<Organization>('/organizations', data);
    return response.data;
  },

  update: async (id: string, data: Partial<OrganizationFormData>): Promise<Organization> => {
    const response = await apiClient.put<Organization>(`/organizations/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/organizations/${id}`);
  },

  listMembers: async (id: string): Promise<User[]> => {
    const response = await apiClient.get<User[]>(`/organizations/${id}/members`);
    return response.data;
  },
};
