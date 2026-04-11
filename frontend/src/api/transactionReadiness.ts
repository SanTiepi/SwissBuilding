import { apiClient } from '@/api/client';

export type TransactionType = 'sell' | 'insure' | 'finance' | 'lease';
export type TransactionStatus = 'ready' | 'conditional' | 'not_ready';

export interface TransactionCheck {
  label: string;
  passed: boolean;
  details: string | null;
}

export interface TransactionItem {
  label: string;
  severity?: string;
  details: string | null;
}

export interface TransactionReadiness {
  building_id: string;
  transaction_type: TransactionType;
  overall_status: TransactionStatus;
  score: number;
  checks: TransactionCheck[];
  blockers: TransactionItem[];
  conditions: TransactionItem[];
  recommendations: TransactionItem[];
  evaluated_at: string;
}

/* ------------------------------------------------------------------ */
/*  Transaction Assessment (full panel model)                          */
/* ------------------------------------------------------------------ */

export interface TransactionAssessment {
  building_id: string;
  verdict: 'not_ready' | 'conditional' | 'ready';
  verdict_summary: string;
  safe_to_sell: { verdict: string; blockers: TransactionItem[]; conditions: TransactionItem[] };
  completeness: {
    score_pct: number;
    documented: string[];
    missing: string[];
    critical_missing: string[];
  };
  trust: { score_pct: number; level: string };
  contradictions: { count: number; items: TransactionItem[] };
  unknowns: {
    count: number;
    critical: TransactionItem[];
    blocking_transaction: TransactionItem[];
  };
  caveats: {
    count: number;
    items: TransactionItem[];
    seller_caveats: TransactionItem[];
    buyer_risks: TransactionItem[];
  };
  incidents: {
    unresolved_count: number;
    recurring_count: number;
    risk_rating: string;
  };
  ownership: { documented: boolean; current_owner: string | null };
  buyer_summary: {
    building_grade: string;
    year: number;
    address: string;
    pollutant_status: string;
    key_facts: string[];
    key_risks: string[];
    key_strengths: string[];
  };
  next_actions: { title: string; priority: string; action_type: string }[];
  pack_ready: boolean;
  pack_blockers: string[];
}

export interface TransactionPackResult {
  pack_id: string;
  building_id: string;
  generated_at: string;
  sections: string[];
  redacted_financials: boolean;
}

export interface BuyerSummary {
  building_id: string;
  building_grade: string;
  year: number;
  address: string;
  pollutant_status: string;
  key_facts: string[];
  key_risks: string[];
  key_strengths: string[];
}

export const transactionReadinessApi = {
  evaluateAll: async (buildingId: string): Promise<TransactionReadiness[]> => {
    const response = await apiClient.get<TransactionReadiness[]>(`/buildings/${buildingId}/transaction-readiness`);
    return response.data;
  },

  evaluate: async (buildingId: string, type: TransactionType): Promise<TransactionReadiness> => {
    const response = await apiClient.get<TransactionReadiness>(
      `/buildings/${buildingId}/transaction-readiness/${type}`,
    );
    return response.data;
  },

  /** Full transaction assessment for the panel */
  assess: async (buildingId: string): Promise<TransactionAssessment> => {
    const response = await apiClient.get<TransactionAssessment>(`/buildings/${buildingId}/transaction-readiness`);
    return response.data;
  },

  /** Generate a transfer pack for the transaction */
  generatePack: async (buildingId: string, redactFinancials = true): Promise<TransactionPackResult> => {
    const response = await apiClient.post<TransactionPackResult>(
      `/buildings/${buildingId}/transaction-readiness/pack`,
      { redact_financials: redactFinancials },
    );
    return response.data;
  },

  /** Buyer-facing summary */
  getBuyerSummary: async (buildingId: string): Promise<BuyerSummary> => {
    const response = await apiClient.get<BuyerSummary>(`/buildings/${buildingId}/transaction-readiness/buyer-summary`);
    return response.data;
  },
};
