import { apiClient } from '@/api/client';
import type { AuthorityPackListItem, AuthorityPackResult } from '@/types';

export interface GenerateAuthorityPackParams {
  canton?: string;
  include_sections?: string[];
  include_photos?: boolean;
  language?: string;
}

export const authorityPacksApi = {
  list: async (buildingId: string): Promise<AuthorityPackListItem[]> => {
    const response = await apiClient.get<AuthorityPackListItem[]>(`/buildings/${buildingId}/authority-packs`);
    return response.data;
  },
  get: async (packId: string): Promise<AuthorityPackResult> => {
    const response = await apiClient.get<AuthorityPackResult>(`/authority-packs/${packId}`);
    return response.data;
  },
  generate: async (buildingId: string, params?: GenerateAuthorityPackParams): Promise<AuthorityPackResult> => {
    const response = await apiClient.post<AuthorityPackResult>(
      `/buildings/${buildingId}/authority-packs/generate`,
      params ?? {},
    );
    return response.data;
  },
};
