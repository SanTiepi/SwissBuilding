import { apiClient } from '@/api/client';

export interface SamplesByPollutant {
  positive: number;
  negative: number;
  total: number;
}

export interface EvidenceSummary {
  building_id: string;
  diagnostics_count: number;
  diagnostics_by_status: Record<string, number>;
  samples_count: number;
  samples_positive: number;
  samples_negative: number;
  samples_by_pollutant: Record<string, SamplesByPollutant>;
  documents_count: number;
  evidence_links_count: number;
  coverage_ratio: number;
}

export const evidenceSummaryApi = {
  get: async (buildingId: string): Promise<EvidenceSummary> => {
    const { data } = await apiClient.get<EvidenceSummary>(`/buildings/${buildingId}/evidence/summary`);
    return data;
  },
};
