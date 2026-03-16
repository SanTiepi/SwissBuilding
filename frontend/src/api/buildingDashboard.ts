import { apiClient } from '@/api/client';

export interface DashboardTrustSummary {
  score: number | null;
  level: string | null;
  trend: string | null;
}

export interface DashboardReadinessSummary {
  overall_status: string | null;
  blocked_count: number;
  gate_count: number;
}

export interface DashboardCompletenessSummary {
  overall_score: number | null;
  category_scores: Record<string, number> | null;
  missing_count: number;
}

export interface DashboardRiskSummary {
  risk_level: string | null;
  risk_score: number | null;
  pollutant_risks: Record<string, string> | null;
}

export interface DashboardComplianceSummary {
  status: string | null;
  overdue_count: number;
  upcoming_deadlines: number;
  gap_count: number;
}

export interface DashboardActivitySummary {
  total_diagnostics: number;
  completed_diagnostics: number;
  total_interventions: number;
  active_interventions: number;
  open_actions: number;
  total_documents: number;
  total_zones: number;
  total_samples: number;
}

export interface DashboardAlertsSummary {
  weak_signals: number;
  constraint_blockers: number;
  quality_issues: number;
  open_unknowns: number;
}

export interface BuildingDashboard {
  building_id: string;
  address: string;
  city: string;
  canton: string;
  passport_grade: string | null;
  trust: DashboardTrustSummary;
  readiness: DashboardReadinessSummary;
  completeness: DashboardCompletenessSummary;
  risk: DashboardRiskSummary;
  compliance: DashboardComplianceSummary;
  activity: DashboardActivitySummary;
  alerts: DashboardAlertsSummary;
  last_updated: string | null;
}

export const buildingDashboardApi = {
  get: async (buildingId: string): Promise<BuildingDashboard> => {
    const { data } = await apiClient.get<BuildingDashboard>(`/buildings/${buildingId}/dashboard`);
    return data;
  },
};
