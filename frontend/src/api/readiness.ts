import { apiClient } from '@/api/client';
import type { ReadinessAssessment, PaginatedResponse } from '@/types';

export const readinessApi = {
  list: async (buildingId: string): Promise<PaginatedResponse<ReadinessAssessment>> => {
    const response = await apiClient.get<PaginatedResponse<ReadinessAssessment>>(`/buildings/${buildingId}/readiness`, {
      params: { size: 50 },
    });
    return response.data;
  },

  evaluateAll: async (buildingId: string): Promise<ReadinessAssessment[]> => {
    const response = await apiClient.post<ReadinessAssessment[]>(`/buildings/${buildingId}/readiness/evaluate-all`);
    return response.data;
  },
};
