import { apiClient } from '@/api/client';

export interface SimulationInput {
  intervention_type: string;
  target_pollutant?: string | null;
  target_zone_id?: string | null;
  estimated_cost?: number | null;
}

export interface SimulationStateSnapshot {
  passport_grade: string;
  trust_score: number;
  completeness_score: number;
  blocker_count: number;
  open_actions_count: number;
}

export interface SimulationImpactSummary {
  actions_resolved: number;
  readiness_improvement: string;
  trust_delta: number;
  completeness_delta: number;
  grade_change: string | null;
  risk_reduction: Record<string, string>;
  estimated_total_cost: number | null;
}

export interface SimulationResult {
  current_state: SimulationStateSnapshot;
  projected_state: SimulationStateSnapshot;
  impact_summary: SimulationImpactSummary;
  recommendations: string[];
}

export const simulatorApi = {
  simulate: async (buildingId: string, interventions: SimulationInput[]): Promise<SimulationResult> => {
    const response = await apiClient.post<SimulationResult>(`/buildings/${buildingId}/interventions/simulate`, {
      interventions,
    });
    return response.data;
  },
};
