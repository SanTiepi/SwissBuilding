import { apiClient } from '@/api/client';
import type { SavedSimulation, PaginatedResponse } from '@/types';

export const savedSimulationsApi = {
  list: async (buildingId: string): Promise<PaginatedResponse<SavedSimulation>> => {
    const response = await apiClient.get<PaginatedResponse<SavedSimulation>>(`/buildings/${buildingId}/simulations`, {
      params: { size: 50 },
    });
    return response.data;
  },
  create: async (
    buildingId: string,
    data: {
      title: string;
      description?: string;
      simulation_type?: string;
      parameters_json?: Record<string, unknown>;
      results_json?: Record<string, unknown>;
      total_cost_chf?: number;
      total_duration_weeks?: number;
      risk_level_before?: string;
      risk_level_after?: string;
    },
  ): Promise<SavedSimulation> => {
    const response = await apiClient.post<SavedSimulation>(`/buildings/${buildingId}/simulations`, data);
    return response.data;
  },
  delete: async (buildingId: string, simulationId: string): Promise<void> => {
    await apiClient.delete(`/buildings/${buildingId}/simulations/${simulationId}`);
  },
};
