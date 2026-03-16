import { apiClient } from '@/api/client';
import type { EvidenceLink } from '@/types';

export const evidenceApi = {
  list: async (params?: {
    source_type?: string;
    source_id?: string;
    target_type?: string;
    target_id?: string;
  }): Promise<EvidenceLink[]> => {
    const response = await apiClient.get<EvidenceLink[]>('/evidence', { params });
    return response.data;
  },
  create: async (data: Partial<EvidenceLink>): Promise<EvidenceLink> => {
    const response = await apiClient.post<EvidenceLink>('/evidence', data);
    return response.data;
  },
  forRiskScore: async (riskScoreId: string): Promise<EvidenceLink[]> => {
    const response = await apiClient.get<EvidenceLink[]>(`/risk-scores/${riskScoreId}/evidence`);
    return response.data;
  },
};
