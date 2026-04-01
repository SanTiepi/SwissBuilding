import { apiClient } from '@/api/client';

export interface ProofOfStateMetadata {
  export_id: string;
  generated_at: string;
  generated_by: string;
  format_version: string;
  building_id: string;
  summary_only?: boolean;
}

export interface ProofOfStateIntegrity {
  algorithm: string;
  hash: string;
}

export interface ProofOfStateResponse {
  metadata: ProofOfStateMetadata;
  building: Record<string, unknown> | null;
  evidence_score: Record<string, unknown> | null;
  passport: Record<string, unknown> | null;
  completeness: Record<string, unknown> | null;
  trust: Record<string, unknown> | null;
  diagnostics: Record<string, unknown>[] | null;
  samples: Record<string, unknown>[] | null;
  documents: Record<string, unknown>[] | null;
  actions: Record<string, unknown>[] | null;
  timeline: Record<string, unknown>[] | null;
  readiness: Record<string, unknown> | null;
  unknowns: Record<string, unknown>[] | null;
  contradictions: Record<string, unknown> | null;
  integrity: ProofOfStateIntegrity;
}

export interface ProofOfStateSummaryResponse {
  metadata: ProofOfStateMetadata;
  evidence_score: Record<string, unknown> | null;
  passport: Record<string, unknown> | null;
  readiness: Record<string, unknown> | null;
  integrity: ProofOfStateIntegrity;
}

export const proofOfStateApi = {
  getProofOfState: async (buildingId: string): Promise<ProofOfStateResponse> => {
    const response = await apiClient.get(`/buildings/${buildingId}/proof-of-state`);
    return response.data;
  },

  getProofOfStateSummary: async (buildingId: string): Promise<ProofOfStateSummaryResponse> => {
    const response = await apiClient.get(`/buildings/${buildingId}/proof-of-state/summary`);
    return response.data;
  },

  downloadProofOfState: async (buildingId: string, summary = false): Promise<void> => {
    const endpoint = summary
      ? `/buildings/${buildingId}/proof-of-state/summary`
      : `/buildings/${buildingId}/proof-of-state`;
    const response = await apiClient.get(endpoint);
    const data = response.data;

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = summary
      ? `proof-of-state-summary-${buildingId}.json`
      : `proof-of-state-${buildingId}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  },
};
