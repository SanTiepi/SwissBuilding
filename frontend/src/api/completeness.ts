import { apiClient } from '@/api/client';
import type { CompletenessResult } from '@/types';

export const completenessApi = {
  evaluate: async (buildingId: string, stage: string = 'avt'): Promise<CompletenessResult> => {
    const response = await apiClient.get<CompletenessResult>(`/buildings/${buildingId}/completeness`, {
      params: { stage },
    });
    return response.data;
  },
};
