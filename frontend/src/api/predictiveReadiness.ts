import { apiClient } from '@/api/client';

export interface PredictiveAlert {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  building_id: string;
  building_name: string;
  alert_type:
    | 'diagnostic_expiring'
    | 'readiness_degradation'
    | 'obligation_due'
    | 'coverage_gap'
    | 'intervention_unready';
  title: string;
  description: string;
  deadline: string | null;
  days_remaining: number | null;
  recommended_action: string;
  estimated_lead_time_days: number | null;
}

export interface PredictiveProjection {
  building_id: string;
  building_name: string;
  current_readiness: 'ready' | 'partial' | 'not_ready';
  projected_readiness_30d: 'ready' | 'partial' | 'not_ready';
  projected_readiness_90d: 'ready' | 'partial' | 'not_ready';
  degradation_reason: string | null;
}

export interface PredictiveSummary {
  critical: number;
  warning: number;
  info: number;
  buildings_at_risk: number;
  diagnostics_expiring_90d: number;
}

export interface PredictiveReadinessResult {
  alerts: PredictiveAlert[];
  summary: PredictiveSummary;
  projections: PredictiveProjection[];
}

export interface PredictiveActionResult {
  created_count: number;
  actions: Array<{
    building_id: string;
    title: string;
    priority: string;
    due_date: string | null;
    alert_type: string;
  }>;
}

export const predictiveReadinessApi = {
  scanPortfolio: async (): Promise<PredictiveReadinessResult> => {
    const response = await apiClient.get<PredictiveReadinessResult>('/portfolio/predictive-readiness');
    return response.data;
  },

  scanBuilding: async (buildingId: string): Promise<PredictiveReadinessResult> => {
    const response = await apiClient.get<PredictiveReadinessResult>(`/buildings/${buildingId}/predictive-readiness`);
    return response.data;
  },

  generateActions: async (): Promise<PredictiveActionResult> => {
    const response = await apiClient.post<PredictiveActionResult>('/portfolio/predictive-actions');
    return response.data;
  },
};
