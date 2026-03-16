import { apiClient } from '@/api/client';

export interface RemediationActions {
  total: number;
  open: number;
  done: number;
  blocked: number;
  by_priority: Record<string, number>;
}

export interface RemediationInterventions {
  total: number;
  by_status: Record<string, number>;
}

export interface RemediationSummary {
  building_id: string;
  actions: RemediationActions;
  interventions: RemediationInterventions;
  post_works_states_count: number;
  has_completed_remediation: boolean;
}

export const remediationSummaryApi = {
  get: async (buildingId: string): Promise<RemediationSummary> => {
    const { data } = await apiClient.get<RemediationSummary>(`/buildings/${buildingId}/remediation/summary`);
    return data;
  },
};
