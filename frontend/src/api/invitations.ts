import { apiClient } from '@/api/client';
import type { Invitation, PaginatedResponse } from '@/types';

export interface InvitationFilters {
  page?: number;
  size?: number;
  status?: string;
}

export interface CreateInvitationData {
  email: string;
  role: string;
  organization_id?: string;
}

export const invitationsApi = {
  list: async (params?: InvitationFilters): Promise<PaginatedResponse<Invitation>> => {
    const response = await apiClient.get<PaginatedResponse<Invitation>>('/invitations', { params });
    return response.data;
  },

  create: async (data: CreateInvitationData): Promise<Invitation> => {
    const payload: Record<string, string> = { email: data.email, role: data.role };
    if (data.organization_id) payload.organization_id = data.organization_id;
    const response = await apiClient.post<Invitation>('/invitations', payload);
    return response.data;
  },

  revoke: async (id: string): Promise<void> => {
    await apiClient.delete(`/invitations/${id}`);
  },
};
