import { apiClient } from '@/api/client';

export interface BuildingCaseRead {
  id: string;
  building_id: string;
  organization_id: string;
  created_by_id: string;
  case_type: string;
  title: string;
  description: string | null;
  state: string;
  spatial_scope_ids: string[] | null;
  pollutant_scope: string[] | null;
  planned_start: string | null;
  planned_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  intervention_id: string | null;
  tender_id: string | null;
  steps: Record<string, unknown>[] | null;
  canton: string | null;
  authority: string | null;
  priority: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface CaseContext {
  case_id: string;
  building_id: string;
  case_type: string;
  title: string;
  state: string;
  priority: string | null;
  spatial_scope_ids: string[] | null;
  pollutant_scope: string[] | null;
  planned_start: string | null;
  planned_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  steps: Record<string, unknown>[] | null;
  intervention_id: string | null;
  tender_id: string | null;
}

export interface CaseTimelineEvent {
  timestamp: string;
  event_type: string;
  label: string;
}

export interface BuildingCaseCreate {
  case_type: string;
  title: string;
  description?: string;
  priority?: string;
  planned_start?: string;
  planned_end?: string;
}

export const buildingCasesApi = {
  listForOrg: async (params?: { state?: string; case_type?: string }): Promise<BuildingCaseRead[]> => {
    const response = await apiClient.get<BuildingCaseRead[]>('/cases', { params });
    return response.data;
  },

  listForBuilding: async (
    buildingId: string,
    params?: { state?: string; case_type?: string },
  ): Promise<BuildingCaseRead[]> => {
    const response = await apiClient.get<BuildingCaseRead[]>(`/buildings/${buildingId}/cases`, { params });
    return response.data;
  },

  create: async (buildingId: string, data: BuildingCaseCreate): Promise<BuildingCaseRead> => {
    const response = await apiClient.post<BuildingCaseRead>(`/buildings/${buildingId}/cases`, data);
    return response.data;
  },

  getDetail: async (caseId: string): Promise<BuildingCaseRead> => {
    const response = await apiClient.get<BuildingCaseRead>(`/cases/${caseId}`);
    return response.data;
  },

  getContext: async (caseId: string): Promise<CaseContext> => {
    const response = await apiClient.get<CaseContext>(`/cases/${caseId}/context`);
    return response.data;
  },

  getTimeline: async (caseId: string): Promise<CaseTimelineEvent[]> => {
    const response = await apiClient.get<CaseTimelineEvent[]>(`/cases/${caseId}/timeline`);
    return response.data;
  },

  advance: async (caseId: string, newState: string): Promise<BuildingCaseRead> => {
    const response = await apiClient.post<BuildingCaseRead>(`/cases/${caseId}/advance`, {
      new_state: newState,
    });
    return response.data;
  },

  completeStep: async (caseId: string, stepName: string): Promise<BuildingCaseRead> => {
    const response = await apiClient.post<BuildingCaseRead>(
      `/cases/${caseId}/steps/${encodeURIComponent(stepName)}/complete`,
    );
    return response.data;
  },
};
