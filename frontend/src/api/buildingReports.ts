import { apiClient } from '@/api/client';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface RadarAxis {
  name: string;
  score: number;
  grade: string;
  blockers: string[];
}

export interface ReadinessRadar {
  building_id: string;
  axes: RadarAxis[];
  overall_score: number;
  overall_grade: string;
  computed_at: string;
}

export interface PollutantRisk {
  pollutant: string;
  probability: number;
  level: string;
}

export interface ReportRecommendation {
  priority: string;
  action: string;
  detail: string;
  source: string;
}

export interface BuildingReport {
  building_id: string;
  identity: {
    address: string;
    postal_code: string;
    city: string;
    canton: string;
    egid: number | null;
    egrid: string | null;
    construction_year: number | null;
    renovation_year: number | null;
    building_type: string;
    floors_above: number | null;
    floors_below: number | null;
    surface_area_m2: number | null;
    volume_m3: number | null;
  };
  passport: {
    grade: string;
    completeness_pct: number;
    trust_score: number;
    trust_trend: string | null;
  };
  risks: {
    pollutants: PollutantRisk[];
    overall_grade: string;
    confidence: number;
  };
  compliance: {
    status: string;
    non_conformities_count: number;
    submitted_count: number;
    acknowledged_count: number;
    total_artefacts: number;
  };
  interventions: {
    completed: Array<{
      title: string;
      type: string;
      date_end: string;
      cost_chf: string;
      contractor: string | null;
    }>;
    planned: Array<{
      title: string;
      type: string;
      date_start: string;
      cost_chf: string;
    }>;
    total_cost_chf: number;
  };
  financial: {
    total_spent_chf: string;
    planned_capex_chf: string;
    intervention_count: number;
  };
  recommendations: ReportRecommendation[];
  metadata: {
    generated_at: string;
    data_completeness_pct: number;
    disclaimer: string;
  };
}

export interface PdfReportResult {
  building_id: string;
  status: string;
  html_payload_length: number;
  html_payload: string;
  message: string;
}

/* ------------------------------------------------------------------ */
/*  API functions                                                      */
/* ------------------------------------------------------------------ */

export const buildingReportsApi = {
  getFullReport: async (buildingId: string): Promise<BuildingReport> => {
    const { data } = await apiClient.get<BuildingReport>(`/reports/${buildingId}/full`);
    return data;
  },

  generatePdf: async (buildingId: string): Promise<PdfReportResult> => {
    const { data } = await apiClient.post<PdfReportResult>(`/reports/${buildingId}/pdf`);
    return data;
  },

  getReadinessRadar: async (buildingId: string): Promise<ReadinessRadar> => {
    const { data } = await apiClient.get<ReadinessRadar>(`/reports/${buildingId}/readiness-radar`);
    return data;
  },
};
