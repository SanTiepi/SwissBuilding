import { apiClient } from '@/api/client';

export interface FinancialEntryRead {
  id: string;
  building_id: string;
  entry_type: string;
  category: string;
  amount_chf: number;
  entry_date: string;
  period_start: string | null;
  period_end: string | null;
  fiscal_year: number | null;
  description: string | null;
  contract_id: string | null;
  lease_id: string | null;
  intervention_id: string | null;
  insurance_policy_id: string | null;
  document_id: string | null;
  external_ref: string | null;
  status: string;
  source_type: string | null;
  confidence: string | null;
  source_ref: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinancialSummary {
  total_expenses: number;
  total_income: number;
  net: number;
  entry_count: number;
  fiscal_year: number | null;
}

export const financialEntriesApi = {
  list: async (params?: {
    building_id?: string;
    entry_type?: string;
    category?: string;
    fiscal_year?: number;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<FinancialEntryRead[]> => {
    const response = await apiClient.get<FinancialEntryRead[]>('/financial-entries', { params });
    return response.data;
  },

  summary: async (params?: { fiscal_year?: number }): Promise<FinancialSummary> => {
    const response = await apiClient.get<FinancialSummary>('/financial-entries/summary', { params });
    return response.data;
  },
};
