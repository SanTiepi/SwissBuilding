import { apiClient } from '@/api/client';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface FinanceItem {
  type?: string;
  subject?: string;
  label?: string;
  severity?: string;
  details?: string | null;
  description?: string;
}

export interface CollateralFactor {
  name: string;
  status: 'strong' | 'adequate' | 'weak' | 'insufficient';
  impact: 'positive' | 'neutral' | 'negative';
}

export interface CollateralConfidence {
  score_pct: number;
  level: 'strong' | 'adequate' | 'weak' | 'insufficient';
  factors: CollateralFactor[];
}

export interface FinanceAssessment {
  building_id: string;
  verdict: 'not_financeable' | 'conditional' | 'financeable';
  verdict_summary: string;
  safe_to_finance: { verdict: string; blockers: string[]; conditions: string[] };
  collateral_confidence: CollateralConfidence;
  completeness: { score_pct: number; documented: string[]; missing: string[] };
  trust: { score_pct: number; level: string };
  contradictions: { count: number; items: FinanceItem[] };
  unknowns: { count: number; critical: string[]; blocking_finance: string[] };
  caveats: {
    count: number;
    lender_conditions: FinanceItem[];
    collateral_risks: FinanceItem[];
    documentation_gaps: FinanceItem[];
  };
  incidents: {
    unresolved_count: number;
    recurring_count: number;
    risk_rating: string;
  };
  lender_summary: {
    building_grade: string;
    year: number;
    address: string;
    collateral_rating: string;
    key_risks: string[];
    key_strengths: string[];
    recommended_due_diligence: string[];
  };
  next_actions: { title: string; priority: string; action_type: string }[];
  pack_ready: boolean;
  pack_blockers: string[];
  assessed_at: string;
}

export interface LenderPackResult {
  pack_id: string;
  overall_completeness: number;
  total_sections: number;
  sha256_hash: string;
  financials_redacted: boolean;
  assessment: FinanceAssessment;
}

export interface LenderSummary {
  building_id: string;
  building_grade: string;
  year: number;
  address: string;
  city: string;
  canton: string;
  collateral_confidence: CollateralConfidence;
  incidents_unresolved: number;
  incidents_recurring: number;
  caveats_count: number;
  lender_conditions: FinanceItem[];
  collateral_risks: FinanceItem[];
  documentation_gaps: FinanceItem[];
  key_facts: string[];
  key_risks: string[];
  key_strengths: string[];
  trust_score_pct: number;
  completeness_pct: number;
  generated_at: string;
}

/* ------------------------------------------------------------------ */
/*  API                                                                */
/* ------------------------------------------------------------------ */

export const financeReadinessApi = {
  /** Full finance readiness assessment */
  assess: async (buildingId: string): Promise<FinanceAssessment> => {
    const response = await apiClient.get<FinanceAssessment>(`/buildings/${buildingId}/finance-readiness`);
    return response.data;
  },

  /** Generate a lender pack (redact_financials defaults to false for lenders) */
  generatePack: async (buildingId: string, redactFinancials = false): Promise<LenderPackResult> => {
    const response = await apiClient.post<LenderPackResult>(`/buildings/${buildingId}/finance-readiness/pack`, {
      redact_financials: redactFinancials,
    });
    return response.data;
  },

  /** Lender-facing summary */
  getSummary: async (buildingId: string): Promise<LenderSummary> => {
    const response = await apiClient.get<LenderSummary>(`/buildings/${buildingId}/finance-readiness/summary`);
    return response.data;
  },
};
