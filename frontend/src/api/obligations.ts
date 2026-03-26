import { apiClient } from '@/api/client';

export interface Obligation {
  id: string;
  building_id: string;
  title: string;
  description: string | null;
  obligation_type: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled' | 'overdue';
  due_date: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ObligationCreatePayload {
  title: string;
  description?: string | null;
  obligation_type: string;
  priority?: string;
  due_date?: string | null;
}

export const obligationsApi = {
  listByBuilding: async (buildingId: string): Promise<Obligation[]> => {
    const response = await apiClient.get<Obligation[]>(`/buildings/${buildingId}/obligations`);
    return response.data;
  },

  create: async (buildingId: string, data: ObligationCreatePayload): Promise<Obligation> => {
    const response = await apiClient.post<Obligation>(`/buildings/${buildingId}/obligations`, data);
    return response.data;
  },

  complete: async (buildingId: string, obligationId: string): Promise<Obligation> => {
    const response = await apiClient.post<Obligation>(`/buildings/${buildingId}/obligations/${obligationId}/complete`);
    return response.data;
  },

  cancel: async (buildingId: string, obligationId: string): Promise<Obligation> => {
    const response = await apiClient.post<Obligation>(`/buildings/${buildingId}/obligations/${obligationId}/cancel`);
    return response.data;
  },
};
