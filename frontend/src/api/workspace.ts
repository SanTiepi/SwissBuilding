import { apiClient } from '@/api/client';

export interface WorkspaceMember {
  id: string;
  building_id: string;
  user_id: string | null;
  organization_id: string | null;
  role: string;
  access_scope: string;
  user_name: string | null;
  user_email: string | null;
  org_name: string | null;
  created_at: string;
}

export interface WorkspaceMemberCreatePayload {
  user_id?: string | null;
  organization_id?: string | null;
  role: string;
  access_scope?: string;
}

export const workspaceApi = {
  listMembers: async (buildingId: string): Promise<WorkspaceMember[]> => {
    const response = await apiClient.get<WorkspaceMember[]>(`/buildings/${buildingId}/workspace/members`);
    return response.data;
  },

  addMember: async (buildingId: string, data: WorkspaceMemberCreatePayload): Promise<WorkspaceMember> => {
    const response = await apiClient.post<WorkspaceMember>(`/buildings/${buildingId}/workspace/members`, data);
    return response.data;
  },

  removeMember: async (buildingId: string, memberId: string): Promise<void> => {
    await apiClient.delete(`/buildings/${buildingId}/workspace/members/${memberId}`);
  },
};
