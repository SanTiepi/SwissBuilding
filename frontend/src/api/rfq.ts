import { apiClient } from '@/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TenderRequest {
  id: string;
  building_id: string;
  organization_id: string | null;
  created_by_id: string;
  title: string;
  description: string | null;
  scope_summary: string | null;
  work_type: string;
  deadline_submission: string | null;
  planned_start_date: string | null;
  planned_end_date: string | null;
  status: 'draft' | 'sent' | 'collecting' | 'closed' | 'attributed' | 'cancelled';
  attachments_auto: string[] | null;
  attachments_manual: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface TenderInvitation {
  id: string;
  tender_id: string;
  contractor_org_id: string;
  sent_at: string | null;
  viewed_at: string | null;
  responded_at: string | null;
  status: string;
  access_token: string | null;
  created_at: string;
}

export interface TenderQuote {
  id: string;
  tender_id: string;
  invitation_id: string | null;
  contractor_org_id: string;
  total_amount_chf: number | null;
  currency: string;
  scope_description: string | null;
  exclusions: string | null;
  inclusions: string | null;
  estimated_duration_days: number | null;
  validity_date: string | null;
  document_id: string | null;
  extracted_data: Record<string, unknown> | null;
  status: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TenderComparisonEntry {
  quote_id: string;
  contractor_org_id: string;
  total_amount_chf: number | null;
  currency: string;
  estimated_duration_days: number | null;
  scope_description: string | null;
  inclusions: string | null;
  exclusions: string | null;
  validity_date: string | null;
  submitted_at: string | null;
  status: string;
}

export interface TenderComparisonStats {
  total_quotes: number;
  quotes_with_amount: number;
  amount_range_chf: { min: number | null; max: number | null };
  duration_range_days: { min: number | null; max: number | null };
}

export interface TenderComparisonData {
  entries: TenderComparisonEntry[];
  statistics: TenderComparisonStats;
  generated_at: string;
}

export interface TenderComparison {
  id: string;
  tender_id: string;
  created_by_id: string;
  comparison_data: TenderComparisonData | null;
  selected_quote_id: string | null;
  selection_reason: string | null;
  attributed_at: string | null;
  created_at: string;
}

export interface TenderCreatePayload {
  building_id: string;
  title: string;
  work_type: string;
  description?: string | null;
  deadline_submission?: string | null;
  planned_start_date?: string | null;
  planned_end_date?: string | null;
  attachments_manual?: string[] | null;
}

export interface TenderUpdatePayload {
  title?: string;
  description?: string | null;
  work_type?: string;
  deadline_submission?: string | null;
  planned_start_date?: string | null;
  planned_end_date?: string | null;
  attachments_manual?: string[] | null;
  status?: string;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export const rfqApi = {
  generateDraft: async (data: TenderCreatePayload): Promise<TenderRequest> => {
    const response = await apiClient.post<TenderRequest>('/rfq/generate', data);
    return response.data;
  },

  get: async (tenderId: string): Promise<TenderRequest> => {
    const response = await apiClient.get<TenderRequest>(`/rfq/${tenderId}`);
    return response.data;
  },

  update: async (tenderId: string, data: TenderUpdatePayload): Promise<TenderRequest> => {
    const response = await apiClient.put<TenderRequest>(`/rfq/${tenderId}`, data);
    return response.data;
  },

  send: async (tenderId: string, contractorOrgIds: string[]): Promise<TenderInvitation[]> => {
    const response = await apiClient.post<TenderInvitation[]>(`/rfq/${tenderId}/send`, {
      contractor_org_ids: contractorOrgIds,
    });
    return response.data;
  },

  submitQuote: async (
    tenderId: string,
    data: {
      contractor_org_id: string;
      invitation_id?: string;
      total_amount_chf?: number;
      scope_description?: string;
      exclusions?: string;
      inclusions?: string;
      estimated_duration_days?: number;
      validity_date?: string;
      document_id?: string;
    },
  ): Promise<TenderQuote> => {
    const response = await apiClient.post<TenderQuote>(`/rfq/${tenderId}/quotes`, data);
    return response.data;
  },

  extractQuoteData: async (tenderId: string, quoteId: string): Promise<TenderQuote> => {
    const response = await apiClient.post<TenderQuote>(`/rfq/${tenderId}/quotes/${quoteId}/extract`);
    return response.data;
  },

  generateComparison: async (tenderId: string): Promise<TenderComparison> => {
    const response = await apiClient.post<TenderComparison>(`/rfq/${tenderId}/compare`);
    return response.data;
  },

  attribute: async (tenderId: string, quoteId: string, reason?: string): Promise<TenderComparison> => {
    const response = await apiClient.post<TenderComparison>(`/rfq/${tenderId}/attribute`, {
      quote_id: quoteId,
      reason: reason ?? null,
    });
    return response.data;
  },

  listQuotes: async (tenderId: string): Promise<TenderQuote[]> => {
    const response = await apiClient.get<TenderQuote[]>(`/rfq/${tenderId}/quotes`);
    return response.data;
  },

  listByBuilding: async (buildingId: string): Promise<TenderRequest[]> => {
    const response = await apiClient.get<TenderRequest[]>(`/rfq/building/${buildingId}`);
    return response.data;
  },
};
