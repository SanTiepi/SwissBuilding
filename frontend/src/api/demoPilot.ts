import { apiClient } from '@/api/client';

// ---- Demo Scenario types ----

export interface DemoRunbookStep {
  id: string;
  scenario_id: string;
  step_order: number;
  title: string;
  description: string | null;
  expected_ui_state: string | null;
  fallback_notes: string | null;
  created_at: string;
}

export interface DemoScenario {
  id: string;
  scenario_code: string;
  title: string;
  persona_target: string;
  starting_state_description: string;
  reveal_surfaces: string[];
  proof_moment: string | null;
  action_moment: string | null;
  seed_key: string | null;
  is_active: boolean;
  created_at: string;
}

export interface DemoScenarioWithRunbook extends DemoScenario {
  runbook_steps: DemoRunbookStep[];
}

// ---- Pilot Scorecard types ----

export interface PilotMetric {
  id: string;
  scorecard_id: string;
  dimension: string;
  target_value: number | null;
  current_value: number | null;
  evidence_source: string | null;
  notes: string | null;
  measured_at: string;
  created_at: string;
}

export interface PilotScorecard {
  id: string;
  pilot_name: string;
  pilot_code: string;
  status: string;
  start_date: string;
  end_date: string | null;
  target_buildings: number | null;
  target_users: number | null;
  exit_state: string | null;
  exit_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PilotScorecardWithMetrics extends PilotScorecard {
  metrics: PilotMetric[];
}

// ---- ROI types ----

export interface ROIBreakdown {
  label: string;
  value: number;
  unit: string;
  evidence_count: number;
}

export interface ROIReport {
  building_id: string;
  time_saved_hours: number;
  rework_avoided: number;
  blocker_days_saved: number;
  pack_reuse_count: number;
  breakdown: ROIBreakdown[];
  evidence_sources: string[];
}

// ---- Case Study Template types ----

export interface CaseStudyTemplate {
  id: string;
  template_code: string;
  title: string;
  persona_target: string;
  workflow_type: string;
  narrative_structure: {
    before?: string;
    trigger?: string;
    after?: string;
    proof_points?: string[];
  };
  evidence_requirements: Array<{ label: string; source: string }>;
  is_active: boolean;
  created_at: string;
}

// ---- API client ----

export const demoPilotApi = {
  // Demo Scenarios
  listScenarios: async (): Promise<DemoScenario[]> => {
    const response = await apiClient.get<DemoScenario[]>('/demo/scenarios');
    return response.data;
  },

  getRunbook: async (code: string): Promise<DemoScenarioWithRunbook> => {
    const response = await apiClient.get<DemoScenarioWithRunbook>(`/demo/scenarios/${code}/runbook`);
    return response.data;
  },

  // Pilot Scorecards
  listPilots: async (): Promise<PilotScorecard[]> => {
    const response = await apiClient.get<PilotScorecard[]>('/pilots');
    return response.data;
  },

  getScorecard: async (code: string): Promise<PilotScorecardWithMetrics> => {
    const response = await apiClient.get<PilotScorecardWithMetrics>(`/pilots/${code}/scorecard`);
    return response.data;
  },

  // ROI
  getBuildingROI: async (buildingId: string): Promise<ROIReport> => {
    const response = await apiClient.get<ROIReport>(`/buildings/${buildingId}/roi`);
    return response.data;
  },

  // Case Study Templates
  listCaseStudyTemplates: async (): Promise<CaseStudyTemplate[]> => {
    const response = await apiClient.get<CaseStudyTemplate[]>('/case-study-templates');
    return response.data;
  },

  getCaseStudyTemplate: async (code: string): Promise<CaseStudyTemplate> => {
    const response = await apiClient.get<CaseStudyTemplate>(`/case-study-templates/${code}`);
    return response.data;
  },
};
