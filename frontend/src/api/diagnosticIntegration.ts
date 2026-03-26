import { apiClient } from '@/api/client';
import type { DiagnosticPublication } from '@/components/building-detail/DiagnosticPublicationCard';
import type { DiagnosticMissionOrder } from '@/components/building-detail/MissionOrderCard';

export type { DiagnosticPublication, DiagnosticMissionOrder };

export interface ImportedDiagnosticSummaryDto {
  source_system: string;
  mission_ref: string;
  published_at: string;
  consumer_state: string | null;
  match_state: string;
  match_key_type: string | null;
  building_id: string | null;
  report_readiness_status: string | null;
  snapshot_version: number;
  payload_hash: string;
  contract_version: string | null;
  sample_count: number | null;
  positive_count: number | null;
  review_count: number | null;
  not_analyzed_count: number | null;
  ai_summary_text: string | null;
  has_ai: boolean;
  has_remediation: boolean;
  is_partial: boolean;
  flags: string[];
}

export interface CreateMissionOrderRequest {
  building_id: string;
  requester_org_id?: string | null;
  mission_type: string;
  context_notes?: string | null;
  attachments?: Record<string, unknown>[];
}

export const diagnosticIntegrationApi = {
  getImportedDiagnosticSummaries: async (buildingId: string): Promise<ImportedDiagnosticSummaryDto[]> => {
    const response = await apiClient.get<ImportedDiagnosticSummaryDto[]>(
      `/buildings/${buildingId}/imported-diagnostic-summary`,
    );
    return response.data;
  },

  getPublicationsForBuilding: async (buildingId: string): Promise<DiagnosticPublication[]> => {
    const response = await apiClient.get<DiagnosticPublication[]>(`/buildings/${buildingId}/diagnostic-publications`);
    return response.data;
  },

  getMissionOrdersForBuilding: async (buildingId: string): Promise<DiagnosticMissionOrder[]> => {
    const response = await apiClient.get<DiagnosticMissionOrder[]>(`/buildings/${buildingId}/mission-orders`);
    return response.data;
  },

  createMissionOrder: async (data: CreateMissionOrderRequest): Promise<DiagnosticMissionOrder> => {
    const response = await apiClient.post<DiagnosticMissionOrder>('/diagnostic-mission-orders', data);
    return response.data;
  },
};
