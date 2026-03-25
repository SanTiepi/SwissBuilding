import { apiClient } from '@/api/client';

export interface AccessGrant {
  id: string;
  building_id: string;
  building_address: string;
  grantee_email: string;
  grantee_org_id: string | null;
  grantee_org_name: string | null;
  grant_type: string;
  scope: string;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
  created_by: string | null;
}

export interface AccessGrantCreate {
  building_id: string;
  grantee_email: string;
  grantee_org_id?: string | null;
  grant_type: string;
  scope: string;
  expires_at?: string | null;
}

export interface PrivilegedAccessEvent {
  id: string;
  grant_id: string | null;
  event_type: string;
  actor_email: string;
  detail: string;
  created_at: string;
}

export interface PaginatedGrants {
  items: AccessGrant[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface PackagePreset {
  code: string;
  label: string;
  description: string;
}

export interface PackagePresetPreviewData {
  preset_code: string;
  included: string[];
  excluded: string[];
  unknown: string[];
}

export const rolloutApi = {
  listGrants: async (params?: { page?: number; size?: number }): Promise<PaginatedGrants> => {
    const response = await apiClient.get<PaginatedGrants>('/rollout/grants', { params });
    return response.data;
  },

  createGrant: async (data: AccessGrantCreate): Promise<AccessGrant> => {
    const response = await apiClient.post<AccessGrant>('/rollout/grants', data);
    return response.data;
  },

  revokeGrant: async (grantId: string): Promise<void> => {
    await apiClient.post(`/rollout/grants/${grantId}/revoke`);
  },

  listEvents: async (params?: { limit?: number }): Promise<PrivilegedAccessEvent[]> => {
    const response = await apiClient.get<PrivilegedAccessEvent[]>('/rollout/events', { params });
    return response.data;
  },

  listPresets: async (): Promise<PackagePreset[]> => {
    const response = await apiClient.get<PackagePreset[]>('/rollout/package-presets');
    return response.data;
  },

  previewPreset: async (buildingId: string, presetCode: string): Promise<PackagePresetPreviewData> => {
    const response = await apiClient.get<PackagePresetPreviewData>(
      `/buildings/${buildingId}/package-preview/${presetCode}`,
    );
    return response.data;
  },
};
