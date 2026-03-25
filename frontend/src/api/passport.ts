import { apiClient } from '@/api/client';

export interface ImportedDossierSummary {
  source_system: string;
  mission_ref: string;
  published_at: string | null;
  local_ingestion_status: string;
  building_match_status: string;
  report_readiness_status: string | null;
  snapshot_version: number;
  snapshot_ref: null;
  payload_hash: string;
  sample_count: number | null;
  positive_sample_count: number | null;
  ai_summary_text: string | null;
  flags: string[];
}

export interface PassportSummary {
  building_id: string;
  knowledge_state: {
    proven_pct: number;
    inferred_pct: number;
    declared_pct: number;
    obsolete_pct: number;
    contradictory_pct: number;
    overall_trust: number;
    total_data_points: number;
    trend: string | null;
  };
  completeness: { overall_score: number; category_scores: Record<string, number> };
  readiness: Record<string, { status: string; score: number; blockers_count: number }>;
  blind_spots: { total_open: number; blocking: number; by_type: Record<string, number> };
  contradictions: { total: number; unresolved: number; by_type: Record<string, number> };
  evidence_coverage: {
    diagnostics_count: number;
    samples_count: number;
    documents_count: number;
    interventions_count: number;
    latest_diagnostic_date: string | null;
    latest_document_date: string | null;
  };
  diagnostic_publications: {
    count: number;
    pollutants_covered: string[];
    latest_published_at: string | null;
    latest_imported_summary?: ImportedDossierSummary;
  };
  pollutant_coverage: {
    total_pollutants: number;
    covered_count: number;
    missing_count: number;
    covered: Record<string, number>;
    missing: string[];
    coverage_ratio: number;
  };
  passport_grade: string;
  assessed_at: string;
}

export const passportApi = {
  summary: async (buildingId: string): Promise<PassportSummary> => {
    const response = await apiClient.get(`/buildings/${buildingId}/passport/summary`);
    return response.data;
  },
};
