import { apiClient } from '@/api/client';

export interface CostEstimate {
  min: number;
  max: number;
  currency: string;
  confidence: string;
}

export interface RelatedEntity {
  entity_type: string;
  entity_id: string | null;
}

export interface Recommendation {
  id: string;
  priority: number;
  category: string;
  title: string;
  description: string;
  why: string;
  impact_score: number;
  cost_estimate: CostEstimate | null;
  urgency_days: number | null;
  source: string;
  related_entity: RelatedEntity | null;
}

export interface RecommendationList {
  building_id: string;
  recommendations: Recommendation[];
  total: number;
}

export const recommendationsApi = {
  list: async (buildingId: string, limit?: number): Promise<RecommendationList> => {
    const response = await apiClient.get<RecommendationList>(
      `/buildings/${buildingId}/recommendations`,
      { params: { limit: limit ?? 10 } },
    );
    return response.data;
  },
};
