import { apiClient } from '@/api/client';

export interface BuildingActivityItem {
  id: string;
  building_id: string;
  actor_id: string;
  actor_role: string;
  actor_name: string;
  activity_type: string;
  entity_type: string;
  entity_id: string;
  title: string;
  description: string | null;
  reason: string | null;
  metadata_json: Record<string, unknown> | null;
  previous_hash: string | null;
  activity_hash: string;
  created_at: string;
}

export interface BuildingActivityList {
  items: BuildingActivityItem[];
  total: number;
  page: number;
  size: number;
}

export interface ChainIntegrity {
  valid: boolean;
  total_entries: number;
  first_break_at: number | null;
}

export interface ActivityListParams {
  page?: number;
  size?: number;
  actor_id?: string;
  activity_type?: string;
  date_from?: string;
  date_to?: string;
}

export const buildingActivitiesApi = {
  list: async (buildingId: string, params?: ActivityListParams): Promise<BuildingActivityList> => {
    const response = await apiClient.get<BuildingActivityList>(`/buildings/${buildingId}/activities`, {
      params,
    });
    return response.data;
  },

  verifyChain: async (buildingId: string): Promise<ChainIntegrity> => {
    const response = await apiClient.get<ChainIntegrity>(`/buildings/${buildingId}/activities/verify-chain`);
    return response.data;
  },
};
