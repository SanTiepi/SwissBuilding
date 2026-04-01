import { apiClient } from '@/api/client';

export interface DefectTimeline {
  id: string;
  building_id: string;
  defect_type: 'construction' | 'pollutant' | 'structural' | 'installation' | 'other';
  description: string;
  discovery_date: string;
  purchase_date: string;
  notification_deadline: string;
  guarantee_type: 'standard' | 'new_build_rectification';
  status: 'active' | 'notified' | 'expired' | 'resolved';
  days_remaining?: number;
  created_at: string;
  updated_at: string;
}

export interface DefectAlert {
  building_id: string;
  defect_id: string;
  days_remaining: number;
  urgency: 'critical' | 'high' | 'medium' | 'low';
}

export interface DefectCreatePayload {
  defect_type: string;
  description: string;
  discovery_date: string;
  purchase_date: string;
}

export const defectTimelineApi = {
  list: async (buildingId: string): Promise<DefectTimeline[]> => {
    const response = await apiClient.get<DefectTimeline[]>(`/buildings/${buildingId}/defects/timeline`);
    return response.data;
  },

  create: async (buildingId: string, data: DefectCreatePayload): Promise<DefectTimeline> => {
    const response = await apiClient.post<DefectTimeline>(`/buildings/${buildingId}/defects/timeline`, data);
    return response.data;
  },

  alerts: async (): Promise<DefectAlert[]> => {
    const response = await apiClient.get<DefectAlert[]>('/defects/alerts');
    return response.data;
  },
};
