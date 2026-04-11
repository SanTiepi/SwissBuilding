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

export interface DefectUpdatePayload {
  status?: string;
  description?: string;
  notified_at?: string;
  notification_pdf_url?: string;
}

export const defectTimelineApi = {
  list: async (buildingId: string): Promise<DefectTimeline[]> => {
    const response = await apiClient.get<DefectTimeline[]>(`/defects/timeline/${buildingId}`);
    return response.data;
  },

  create: async (buildingId: string, data: DefectCreatePayload): Promise<DefectTimeline> => {
    const response = await apiClient.post<DefectTimeline>('/defects/timeline', {
      ...data,
      building_id: buildingId,
    });
    return response.data;
  },

  update: async (timelineId: string, data: DefectUpdatePayload): Promise<DefectTimeline> => {
    const response = await apiClient.patch<DefectTimeline>(`/defects/timelines/${timelineId}`, data);
    return response.data;
  },

  delete: async (timelineId: string): Promise<void> => {
    await apiClient.delete(`/defects/timelines/${timelineId}`);
  },

  generateLetter: async (timelineId: string, lang: string = 'fr'): Promise<Blob> => {
    const response = await apiClient.post(`/defects/${timelineId}/generate-letter`, null, {
      params: { lang },
      responseType: 'blob',
    });
    return response.data as Blob;
  },

  alerts: async (): Promise<DefectAlert[]> => {
    const response = await apiClient.get<DefectAlert[]>('/defects/alerts');
    return response.data;
  },
};
