import { apiClient } from '@/api/client';
import type { UnknownIssue, UnknownSeverity, UnknownStatus, UnknownType, PaginatedResponse } from '@/types';

export interface UnknownIssueFilters {
  status?: UnknownStatus;
  severity?: UnknownSeverity;
  unknown_type?: UnknownType;
  page?: number;
  size?: number;
}

export interface UnknownIssueUpdatePayload {
  status?: UnknownStatus;
  resolution_notes?: string;
  resolved_by?: string;
  resolved_at?: string;
}

export const unknownsApi = {
  list: async (
    buildingId: string,
    statusOrFilters?: string | UnknownIssueFilters,
  ): Promise<PaginatedResponse<UnknownIssue>> => {
    const params: Record<string, string | number> = { size: 100 };
    if (typeof statusOrFilters === 'string') {
      params.status = statusOrFilters;
    } else if (statusOrFilters) {
      if (statusOrFilters.status) params.status = statusOrFilters.status;
      if (statusOrFilters.severity) params.severity = statusOrFilters.severity;
      if (statusOrFilters.unknown_type) params.unknown_type = statusOrFilters.unknown_type;
      if (statusOrFilters.page) params.page = statusOrFilters.page;
      if (statusOrFilters.size) params.size = statusOrFilters.size;
    }
    const response = await apiClient.get<PaginatedResponse<UnknownIssue>>(`/buildings/${buildingId}/unknowns`, {
      params,
    });
    return response.data;
  },

  get: async (buildingId: string, issueId: string): Promise<UnknownIssue> => {
    const response = await apiClient.get<UnknownIssue>(`/buildings/${buildingId}/unknowns/${issueId}`);
    return response.data;
  },

  update: async (buildingId: string, issueId: string, data: UnknownIssueUpdatePayload): Promise<UnknownIssue> => {
    const response = await apiClient.put<UnknownIssue>(`/buildings/${buildingId}/unknowns/${issueId}`, data);
    return response.data;
  },
};
