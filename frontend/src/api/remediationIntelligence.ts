import { apiClient } from '@/api/client';

export interface ReadinessAdvisorSuggestion {
  type: string;
  title: string;
  description: string;
  evidence_refs: string[];
  confidence: number;
  recommended_action: string | null;
}

export interface ReadinessAdvisorResponse {
  building_id: string;
  suggestions: ReadinessAdvisorSuggestion[];
  generated_at: string;
}

export interface NarrativeSection {
  title: string;
  body: string;
  evidence_refs: string[];
  caveats: string[];
  audience_specific: boolean;
}

export interface PassportNarrativeResponse {
  building_id: string;
  audience: string;
  sections: NarrativeSection[];
  generated_at: string;
}

export interface ScopeCoverageItem {
  item: string;
  present_in: string[];
  missing_from: string[];
}

export interface QuoteComparisonInsight {
  request_id: string;
  scope_coverage_matrix: ScopeCoverageItem[];
  price_spread: { min: number; max: number; median: number; range_pct: number };
  timeline_spread: { min_weeks: number; max_weeks: number; median_weeks: number };
  common_exclusions: string[];
  ambiguity_flags: { field: string; quotes_affected: string[]; description: string }[];
  quote_count: number;
}

export interface PollutantBenchmark {
  pollutant: string;
  avg_cost_chf: number;
  avg_cycle_days: number;
  completion_rate: number;
  sample_size: number;
}

export interface RemediationBenchmarkSnapshot {
  org_id: string;
  benchmarks: PollutantBenchmark[];
  overall_avg_cost_chf: number;
  overall_avg_cycle_days: number;
  overall_completion_rate: number;
  generated_at: string;
}

export interface FlywheelTrendPoint {
  date: string;
  extraction_quality: number;
  correction_rate: number;
  cycle_time_days: number | null;
  knowledge_density: number;
}

export interface ModuleLearningOverview {
  total_patterns: number;
  extraction_success_rate: number;
  avg_confidence: number;
  top_correction_categories: { category: string; count: number }[];
  total_extractions: number;
  total_feedbacks: number;
}

export const remediationIntelligenceApi = {
  getReadinessAdvisor: (buildingId: string) =>
    apiClient.get<ReadinessAdvisorResponse>(`/buildings/${buildingId}/readiness-advisor`).then((r) => r.data),

  getPassportNarrative: (buildingId: string, audience: string = 'owner') =>
    apiClient
      .get<PassportNarrativeResponse>(`/buildings/${buildingId}/passport-narrative`, { params: { audience } })
      .then((r) => r.data),

  getComparisonInsights: (requestId: string) =>
    apiClient.get<QuoteComparisonInsight>(`/marketplace/requests/${requestId}/comparison-insights`).then((r) => r.data),

  getRemediationBenchmark: (orgId: string) =>
    apiClient.get<RemediationBenchmarkSnapshot>(`/organizations/${orgId}/remediation-benchmark`).then((r) => r.data),

  getFlywheelTrends: (orgId: string, days: number = 90) =>
    apiClient.get<FlywheelTrendPoint[]>(`/organizations/${orgId}/flywheel-trends`, { params: { days } }).then((r) => r.data),

  getModuleLearningOverview: () =>
    apiClient.get<ModuleLearningOverview>('/admin/module-learning-overview').then((r) => r.data),
};
