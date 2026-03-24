import { apiClient } from '@/api/client';
import type { DiagnosticPublication } from '@/components/building-detail/DiagnosticPublicationCard';

export const diagnosticReviewApi = {
  getUnmatched: async (): Promise<DiagnosticPublication[]> => {
    const response = await apiClient.get<DiagnosticPublication[]>('/diagnostic-publications/unmatched');
    return response.data;
  },

  matchToBuilding: async (publicationId: string, buildingId: string): Promise<DiagnosticPublication> => {
    const response = await apiClient.post<DiagnosticPublication>(
      `/diagnostic-publications/${publicationId}/match`,
      { building_id: buildingId },
    );
    return response.data;
  },
};
