import { apiClient } from '@/api/client';

export interface InsightEvidence {
  layer: string;
  signal: string;
  value: unknown;
}

export interface CrossLayerInsight {
  insight_id: string;
  insight_type: string;
  severity: 'critical' | 'warning' | 'info' | 'opportunity';
  title: string;
  description: string;
  evidence: InsightEvidence[];
  recommendation: string;
  confidence: number;
  estimated_impact: string;
}

export interface IntelligenceSummary {
  total_insights: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  top_critical: CrossLayerInsight[];
  computed_at: string;
}

export const crossLayerIntelligenceApi = {
  getBuildingIntelligence: async (buildingId: string): Promise<CrossLayerInsight[]> => {
    const response = await apiClient.get<CrossLayerInsight[]>(`/buildings/${buildingId}/intelligence`);
    return response.data;
  },

  getPortfolioIntelligence: async (): Promise<CrossLayerInsight[]> => {
    const response = await apiClient.get<CrossLayerInsight[]>('/portfolio/intelligence');
    return response.data;
  },

  getIntelligenceSummary: async (buildingId?: string): Promise<IntelligenceSummary> => {
    const params = buildingId ? { building_id: buildingId } : {};
    const response = await apiClient.get<IntelligenceSummary>('/intelligence/summary', { params });
    return response.data;
  },
};
