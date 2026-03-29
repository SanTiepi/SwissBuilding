import { apiClient } from '@/api/client';

export interface RiskDistribution {
  grade_a: number;
  grade_b: number;
  grade_c: number;
  grade_d: number;
  grade_f: number;
}

export interface BuildingRiskPoint {
  building_id: string;
  address: string;
  city: string;
  canton: string;
  latitude: number | null;
  longitude: number | null;
  score: number;
  grade: string;
  risk_level: string;
  open_actions_count: number;
  critical_actions_count: number;
}

export interface PortfolioRiskOverview {
  total_buildings: number;
  avg_evidence_score: number;
  buildings_at_risk: number;
  buildings_ok: number;
  worst_building_id: string | null;
  distribution: RiskDistribution;
  buildings: BuildingRiskPoint[];
}

export const portfolioRiskApi = {
  getOverview: async (): Promise<PortfolioRiskOverview> => {
    const response = await apiClient.get<PortfolioRiskOverview>('/portfolio/risk-overview');
    return response.data;
  },

  getHeatmap: async (): Promise<BuildingRiskPoint[]> => {
    const response = await apiClient.get<BuildingRiskPoint[]>('/portfolio/risk-heatmap');
    return response.data;
  },
};
