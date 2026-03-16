import { apiClient } from '@/api/client';
import type { PaginatedResponse } from '@/types';

export interface DataQualityIssue {
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

export interface DataQualityFilters {
  issue_type?: string;
  severity?: string;
  status?: string;
  page?: number;
  size?: number;
}

export const dataQualityApi = {
  list: async (buildingId: string, filters?: DataQualityFilters): Promise<PaginatedResponse<DataQualityIssue>> => {
    const params: Record<string, string | number> = { size: filters?.size ?? 50 };
    if (filters?.issue_type) params.issue_type = filters.issue_type;
    if (filters?.severity) params.severity = filters.severity;
    if (filters?.status) params.status = filters.status;
    if (filters?.page) params.page = filters.page;
    const response = await apiClient.get<PaginatedResponse<DataQualityIssue>>(
      `/buildings/${buildingId}/data-quality-issues`,
      { params },
    );
    return response.data;
  },

  update: async (
    buildingId: string,
    issueId: string,
    data: { status?: string; resolution_notes?: string },
  ): Promise<DataQualityIssue> => {
    const response = await apiClient.put<DataQualityIssue>(
      `/buildings/${buildingId}/data-quality-issues/${issueId}`,
      data,
    );
    return response.data;
  },
};
