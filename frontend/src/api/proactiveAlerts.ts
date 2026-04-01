import { apiClient } from '@/api/client';

export interface ProactiveAlert {
  alert_type: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  message: string;
  building_id: string;
  entity_type: string | null;
  entity_id: string | null;
  recommended_action: string;
  notification_id: string | null;
}

export interface AlertSummary {
  total_alerts: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  buildings_with_alerts: number;
}

export const proactiveAlertsApi = {
  scanBuilding: async (buildingId: string): Promise<ProactiveAlert[]> => {
    const response = await apiClient.post<ProactiveAlert[]>(`/buildings/${buildingId}/alerts/scan`);
    return response.data;
  },

  scanPortfolio: async (): Promise<ProactiveAlert[]> => {
    const response = await apiClient.post<ProactiveAlert[]>('/portfolio/alerts/scan');
    return response.data;
  },

  getSummary: async (): Promise<AlertSummary> => {
    const response = await apiClient.get<AlertSummary>('/portfolio/alerts/summary');
    return response.data;
  },
};
