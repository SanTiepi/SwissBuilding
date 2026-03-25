import { apiClient } from '@/api/client';

export interface ExpansionOpportunity {
  id: string;
  opportunity_type: string;
  priority: string;
  recommended_action: string;
  evidence: string;
  status: string;
  building_id: string | null;
  org_id: string | null;
  created_at: string;
  acted_at: string | null;
}

export interface ExpansionTrigger {
  id: string;
  trigger_type: string;
  source_entity: string;
  detail: string;
  created_at: string;
}

export interface DistributionSignal {
  id: string;
  signal_type: string;
  channel: string;
  reach: number;
  detail: string;
  created_at: string;
}

export interface PaginatedOpportunities {
  items: ExpansionOpportunity[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export const expansionApi = {
  listOpportunities: async (params?: { page?: number; size?: number }): Promise<PaginatedOpportunities> => {
    const response = await apiClient.get<PaginatedOpportunities>('/expansion/opportunities', { params });
    return response.data;
  },

  actOnOpportunity: async (opportunityId: string): Promise<ExpansionOpportunity> => {
    const response = await apiClient.post<ExpansionOpportunity>(`/expansion/opportunities/${opportunityId}/act`);
    return response.data;
  },

  dismissOpportunity: async (opportunityId: string): Promise<ExpansionOpportunity> => {
    const response = await apiClient.post<ExpansionOpportunity>(`/expansion/opportunities/${opportunityId}/dismiss`);
    return response.data;
  },

  listTriggers: async (params?: { limit?: number }): Promise<ExpansionTrigger[]> => {
    const response = await apiClient.get<ExpansionTrigger[]>('/expansion/triggers', { params });
    return response.data;
  },

  listDistributionSignals: async (params?: { limit?: number }): Promise<DistributionSignal[]> => {
    const response = await apiClient.get<DistributionSignal[]>('/expansion/distribution-signals', { params });
    return response.data;
  },
};
