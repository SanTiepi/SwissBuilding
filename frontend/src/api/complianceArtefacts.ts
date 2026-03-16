import { apiClient } from '@/api/client';
import type {
  ComplianceArtefact,
  ComplianceArtefactCreate,
  ComplianceArtefactUpdate,
  ComplianceRequiredArtefact,
  PaginatedResponse,
} from '@/types';

export interface ComplianceArtefactListParams {
  page?: number;
  size?: number;
  artefact_type?: string;
  status?: string;
}

export interface ComplianceSummaryResponse {
  total: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  pending_submissions: number;
  expired: number;
}

export const complianceArtefactsApi = {
  list: async (
    buildingId: string,
    params?: ComplianceArtefactListParams,
  ): Promise<PaginatedResponse<ComplianceArtefact>> => {
    const response = await apiClient.get<PaginatedResponse<ComplianceArtefact>>(
      `/buildings/${buildingId}/compliance-artefacts`,
      { params },
    );
    return response.data;
  },

  get: async (buildingId: string, artefactId: string): Promise<ComplianceArtefact> => {
    const response = await apiClient.get<ComplianceArtefact>(
      `/buildings/${buildingId}/compliance-artefacts/${artefactId}`,
    );
    return response.data;
  },

  create: async (buildingId: string, data: ComplianceArtefactCreate): Promise<ComplianceArtefact> => {
    const response = await apiClient.post<ComplianceArtefact>(`/buildings/${buildingId}/compliance-artefacts`, data);
    return response.data;
  },

  update: async (
    buildingId: string,
    artefactId: string,
    data: ComplianceArtefactUpdate,
  ): Promise<ComplianceArtefact> => {
    const response = await apiClient.put<ComplianceArtefact>(
      `/buildings/${buildingId}/compliance-artefacts/${artefactId}`,
      data,
    );
    return response.data;
  },

  delete: async (buildingId: string, artefactId: string): Promise<void> => {
    await apiClient.delete(`/buildings/${buildingId}/compliance-artefacts/${artefactId}`);
  },

  submit: async (buildingId: string, artefactId: string): Promise<ComplianceArtefact> => {
    const response = await apiClient.post<ComplianceArtefact>(
      `/buildings/${buildingId}/compliance-artefacts/${artefactId}/submit`,
    );
    return response.data;
  },

  acknowledge: async (
    buildingId: string,
    artefactId: string,
    referenceNumber?: string,
  ): Promise<ComplianceArtefact> => {
    const response = await apiClient.post<ComplianceArtefact>(
      `/buildings/${buildingId}/compliance-artefacts/${artefactId}/acknowledge`,
      undefined,
      { params: referenceNumber ? { reference_number: referenceNumber } : undefined },
    );
    return response.data;
  },

  summary: async (buildingId: string): Promise<ComplianceSummaryResponse> => {
    const response = await apiClient.get<ComplianceSummaryResponse>(`/buildings/${buildingId}/compliance-summary`);
    return response.data;
  },

  required: async (buildingId: string): Promise<ComplianceRequiredArtefact[]> => {
    const response = await apiClient.get<ComplianceRequiredArtefact[]>(`/buildings/${buildingId}/compliance-required`);
    return response.data;
  },
};
