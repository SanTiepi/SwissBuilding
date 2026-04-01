import { apiClient } from '@/api/client';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface InsuranceItem {
  label: string;
  severity?: string;
  details: string | null;
}

export interface InsuranceAssessment {
  building_id: string;
  verdict: 'not_insurable' | 'conditional' | 'insurable';
  verdict_summary: string;
  safe_to_insure: { verdict: string; blockers: InsuranceItem[]; conditions: InsuranceItem[] };
  risk_profile: {
    overall_rating: string;
    incident_count: number;
    unresolved_incidents: number;
    recurring_patterns: number;
    total_claim_cost_chf: number;
  };
  completeness: { score_pct: number; documented: string[]; missing: string[] };
  pollutant_status: {
    asbestos: string;
    pcb: string;
    lead: string;
    radon: string;
    overall: string;
  };
  contradictions: { count: number; items: InsuranceItem[] };
  unknowns: { count: number; critical: InsuranceItem[]; blocking_insurance: InsuranceItem[] };
  caveats: {
    count: number;
    insurer_exclusions: InsuranceItem[];
    coverage_gaps: InsuranceItem[];
    implied_conditions: InsuranceItem[];
  };
  incidents: {
    total: number;
    unresolved: InsuranceItem[];
    recurring: InsuranceItem[];
    recent: InsuranceItem[];
  };
  insurer_summary: {
    building_grade: string;
    year: number;
    address: string;
    risk_rating: string;
    key_risks: string[];
    key_strengths: string[];
    recommended_inspections: string[];
  };
  next_actions: { title: string; priority: string; action_type: string }[];
  pack_ready: boolean;
  pack_blockers: string[];
}

export interface InsurancePackResult {
  pack_id: string;
  building_id: string;
  generated_at: string;
  sections: string[];
  redacted_financials: boolean;
}

export interface InsurerSummary {
  building_id: string;
  building_grade: string;
  year: number;
  address: string;
  risk_rating: string;
  key_risks: string[];
  key_strengths: string[];
  recommended_inspections: string[];
}

/* ------------------------------------------------------------------ */
/*  API                                                                */
/* ------------------------------------------------------------------ */

export const insuranceReadinessApi = {
  /** Full insurance readiness assessment */
  assess: async (buildingId: string): Promise<InsuranceAssessment> => {
    const response = await apiClient.get<InsuranceAssessment>(`/buildings/${buildingId}/insurance-readiness`);
    return response.data;
  },

  /** Generate an insurer pack */
  generatePack: async (buildingId: string, redactFinancials = false): Promise<InsurancePackResult> => {
    const response = await apiClient.post<InsurancePackResult>(`/buildings/${buildingId}/insurance-readiness/pack`, {
      redact_financials: redactFinancials,
    });
    return response.data;
  },

  /** Insurer-facing summary */
  getSummary: async (buildingId: string): Promise<InsurerSummary> => {
    const response = await apiClient.get<InsurerSummary>(`/buildings/${buildingId}/insurance-readiness/summary`);
    return response.data;
  },
};
