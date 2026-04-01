import { apiClient } from '@/api/client';

export interface InvalidationEvent {
  id: string;
  building_id: string;
  trigger_type: string;
  trigger_id: string | null;
  trigger_description: string;
  affected_type: string;
  affected_id: string;
  impact_reason: string;
  severity: string;
  required_reaction: string;
  status: string;
  resolved_at: string | null;
  resolved_by_id: string | null;
  resolution_note: string | null;
  detected_at: string | null;
  created_at: string | null;
}

export interface InvalidationPendingResponse {
  items: InvalidationEvent[];
  total: number;
}

export const invalidationsApi = {
  getForBuilding: async (
    buildingId: string,
    params?: { status?: string; severity?: string; limit?: number },
  ): Promise<InvalidationEvent[]> => {
    const response = await apiClient.get<InvalidationEvent[]>(`/buildings/${buildingId}/invalidations`, { params });
    return response.data;
  },

  getPending: async (params?: {
    status?: string;
    severity?: string;
    limit?: number;
  }): Promise<InvalidationPendingResponse> => {
    const response = await apiClient.get<InvalidationPendingResponse>('/invalidations/pending', {
      params,
    });
    return response.data;
  },

  acknowledge: async (eventId: string): Promise<InvalidationEvent> => {
    const response = await apiClient.post<InvalidationEvent>(`/invalidations/${eventId}/acknowledge`);
    return response.data;
  },

  resolve: async (eventId: string, resolutionNote: string): Promise<InvalidationEvent> => {
    const response = await apiClient.post<InvalidationEvent>(`/invalidations/${eventId}/resolve`, {
      resolution_note: resolutionNote,
    });
    return response.data;
  },

  executeReaction: async (eventId: string): Promise<Record<string, unknown>> => {
    const response = await apiClient.post<Record<string, unknown>>(`/invalidations/${eventId}/execute-reaction`);
    return response.data;
  },
};
