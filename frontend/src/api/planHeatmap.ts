import { apiClient } from '@/api/client';

export interface HeatmapPoint {
  x: number;
  y: number;
  intensity: number;
  category: string;
  label: string | null;
  annotation_id: string | null;
  zone_id: string | null;
}

export interface PlanHeatmap {
  plan_id: string;
  building_id: string;
  total_points: number;
  coverage_score: number;
  points: HeatmapPoint[];
  summary: Record<string, number>;
}

export const planHeatmapApi = {
  getHeatmap: async (planId: string): Promise<PlanHeatmap> => {
    const response = await apiClient.get<PlanHeatmap>(`/plans/${planId}/heatmap`);
    return response.data;
  },
};
