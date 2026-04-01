import { apiClient } from '@/api/client';

export interface EvidenceScoreBreakdown {
  trust_weighted: number;
  completeness_weighted: number;
  freshness_weighted: number;
  gap_penalty_weighted: number;
}

export interface EvidenceScore {
  building_id: string;
  score: number;
  grade: string;
  trust: number;
  completeness: number;
  freshness: number;
  gap_penalty: number;
  breakdown: EvidenceScoreBreakdown;
  computed_at: string;
}

export const evidenceScoreApi = {
  getEvidenceScore: async (buildingId: string): Promise<EvidenceScore> => {
    const response = await apiClient.get<EvidenceScore>(`/buildings/${buildingId}/evidence-score`);
    return response.data;
  },
  getPortfolioEvidenceScores: async (): Promise<EvidenceScore[]> => {
    const response = await apiClient.get<EvidenceScore[]>('/portfolio/evidence-scores');
    return response.data;
  },
};
