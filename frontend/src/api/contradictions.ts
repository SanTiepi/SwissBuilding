import { apiClient } from '@/api/client';
import type { PaginatedResponse } from '@/types';

export interface ContradictionSummary {
  total: number;
  by_type: Record<string, number>;
  resolved: number;
  unresolved: number;
}

export interface ContradictionIssue {
  id: string;
  building_id: string;
  issue_type: string;
  severity: string;
  status: string;
  entity_type: string | null;
  entity_id: string | null;
  field_name: string | null;
  description: string;
  suggestion: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  resolution_notes: string | null;
  detected_by: string | null;
  created_at: string;
}

/** @deprecated Use ContradictionIssue instead */
export interface DataQualityIssue {
  id: string;
  building_id: string;
  issue_type: string;
  severity: string;
  field_name: string;
  current_value: string | null;
  expected_value: string | null;
  description: string | null;
  source: string | null;
  resolved: boolean;
  detected_at: string;
}

export interface ContradictionUpdatePayload {
  status?: string;
  severity?: string;
  resolution_notes?: string;
  resolved_at?: string;
  resolved_by?: string;
}

export const contradictionsApi = {
  summary: async (buildingId: string): Promise<ContradictionSummary> => {
    const response = await apiClient.get(`/buildings/${buildingId}/contradictions/summary`);
    return response.data;
  },

  detect: async (buildingId: string): Promise<ContradictionIssue[]> => {
    const response = await apiClient.post(`/buildings/${buildingId}/contradictions/detect`);
    return response.data;
  },

  list: async (
    buildingId: string,
    params?: {
      page?: number;
      size?: number;
      issue_type?: string;
      severity?: string;
      status?: string;
    },
  ): Promise<PaginatedResponse<ContradictionIssue>> => {
    const response = await apiClient.get(`/buildings/${buildingId}/data-quality-issues`, {
      params: { issue_type: 'contradiction', ...params },
    });
    return response.data;
  },

  get: async (buildingId: string, issueId: string): Promise<ContradictionIssue> => {
    const response = await apiClient.get(`/buildings/${buildingId}/data-quality-issues/${issueId}`);
    return response.data;
  },

  update: async (
    buildingId: string,
    issueId: string,
    data: ContradictionUpdatePayload,
  ): Promise<ContradictionIssue> => {
    const response = await apiClient.put(`/buildings/${buildingId}/data-quality-issues/${issueId}`, data);
    return response.data;
  },
};
