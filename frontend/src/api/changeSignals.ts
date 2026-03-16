import { apiClient } from '@/api/client';
import type { PaginatedResponse } from '@/types';

export interface ChangeSignal {
  id: string;
  building_id: string;
  signal_type: string;
  severity: string;
  status: string;
  title: string;
  description: string | null;
  source: string | null;
  entity_type: string | null;
  entity_id: string | null;
  metadata_json: Record<string, unknown> | null;
  detected_at: string;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
}

export type ChangeSignalType =
  | 'new_diagnostic'
  | 'status_change'
  | 'document_added'
  | 'sample_result'
  | 'intervention_complete'
  | 'trust_change'
  | 'readiness_change';

export type ChangeSignalSeverity = 'critical' | 'warning' | 'info';
export type ChangeSignalStatus = 'active' | 'acknowledged' | 'resolved';

export interface ChangeSignalListParams {
  page?: number;
  size?: number;
  signal_type?: string;
  severity?: string;
  status?: string;
}

export const changeSignalsApi = {
  list: async (buildingId: string, params?: ChangeSignalListParams): Promise<PaginatedResponse<ChangeSignal>> => {
    const queryParams: Record<string, string | number> = { size: params?.size ?? 50 };
    if (params?.page) queryParams.page = params.page;
    if (params?.signal_type) queryParams.signal_type = params.signal_type;
    if (params?.severity) queryParams.severity = params.severity;
    if (params?.status) queryParams.status = params.status;
    const response = await apiClient.get<PaginatedResponse<ChangeSignal>>(`/buildings/${buildingId}/change-signals`, {
      params: queryParams,
    });
    return response.data;
  },

  listPortfolio: async (severity?: string, status?: string): Promise<PaginatedResponse<ChangeSignal>> => {
    const params: Record<string, string | number> = { size: 20 };
    if (severity) params.severity = severity;
    if (status) params.status = status;
    const response = await apiClient.get<PaginatedResponse<ChangeSignal>>('/portfolio/change-signals', { params });
    return response.data;
  },

  get: async (buildingId: string, signalId: string): Promise<ChangeSignal> => {
    const response = await apiClient.get<ChangeSignal>(`/buildings/${buildingId}/change-signals/${signalId}`);
    return response.data;
  },

  acknowledge: async (buildingId: string, signalId: string): Promise<ChangeSignal> => {
    const response = await apiClient.put<ChangeSignal>(`/buildings/${buildingId}/change-signals/${signalId}`, {
      status: 'acknowledged',
      acknowledged_at: new Date().toISOString(),
    });
    return response.data;
  },

  resolve: async (buildingId: string, signalId: string): Promise<ChangeSignal> => {
    const response = await apiClient.put<ChangeSignal>(`/buildings/${buildingId}/change-signals/${signalId}`, {
      status: 'resolved',
    });
    return response.data;
  },
};
