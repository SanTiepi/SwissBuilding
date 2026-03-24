import { apiClient } from '@/api/client';
import type { DiagnosticPublication } from '@/components/building-detail/DiagnosticPublicationCard';
import type { DiagnosticMissionOrder } from '@/components/building-detail/MissionOrderCard';

export type { DiagnosticPublication, DiagnosticMissionOrder };

export interface CreateMissionOrderRequest {
  building_id: string;
  requester_org_id?: string | null;
  mission_type: string;
  context_notes?: string | null;
  attachments?: Record<string, unknown>[];
}

export const diagnosticIntegrationApi = {
  getPublicationsForBuilding: async (buildingId: string): Promise<DiagnosticPublication[]> => {
    const response = await apiClient.get<DiagnosticPublication[]>(
      `/buildings/${buildingId}/diagnostic-publications`,
    );
    return response.data;
  },

  getMissionOrdersForBuilding: async (buildingId: string): Promise<DiagnosticMissionOrder[]> => {
    const response = await apiClient.get<DiagnosticMissionOrder[]>(
      `/buildings/${buildingId}/mission-orders`,
    );
    return response.data;
  },

  createMissionOrder: async (data: CreateMissionOrderRequest): Promise<DiagnosticMissionOrder> => {
    const response = await apiClient.post<DiagnosticMissionOrder>('/diagnostic-mission-orders', data);
    return response.data;
  },
};
