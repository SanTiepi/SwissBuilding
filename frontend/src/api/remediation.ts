import { apiClient } from '@/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CompanyWorkspaceSummary {
  company_profile_id: string;
  company_name: string;
  is_verified: boolean;
  subscription_status: string | null;
  subscription_plan: string | null;
  pending_invitations: number;
  active_rfqs: number;
  draft_quotes: number;
  awards_won: number;
  completions_pending: number;
  reviews_published: number;
}

export interface OperatorRemediationQueue {
  active_rfqs: number;
  quotes_received: number;
  awards_pending: number;
  completions_awaiting: number;
  post_works_open: number;
}

export interface QuoteComparisonRow {
  company_name: string;
  amount_chf: number | null;
  timeline_weeks: number | null;
  scope_items: string[];
  exclusions: string[];
  confidence: number | null;
  ambiguous_fields: Record<string, unknown>[];
  submitted_at: string | null;
}

export interface QuoteComparisonMatrix {
  request_id: string;
  rows: QuoteComparisonRow[];
}

export interface AIExtractionLog {
  id: string;
  extraction_type: string;
  source_document_id: string | null;
  source_filename: string | null;
  input_hash: string;
  output_data: Record<string, unknown> | null;
  confidence_score: number | null;
  ai_model: string | null;
  ambiguous_fields: Record<string, unknown>[] | null;
  unknown_fields: Record<string, unknown>[] | null;
  status: string;
  confirmed_by_user_id: string | null;
  confirmed_at: string | null;
  created_at: string;
}

export interface FlywheelMetrics {
  total_extractions: number;
  confirmation_rate: number;
  correction_rate: number;
  rejection_rate: number;
  avg_cycle_time_days: number | null;
  total_completed_cycles: number;
  total_reviews_published: number;
  knowledge_density: number;
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

export const remediationApi = {
  getCompanyWorkspace: (profileId: string): Promise<CompanyWorkspaceSummary> =>
    apiClient.get(`/marketplace/companies/${profileId}/workspace`),

  getOperatorQueue: (): Promise<OperatorRemediationQueue> =>
    apiClient.get('/marketplace/operator/queue'),

  getComparisonMatrix: (requestId: string): Promise<QuoteComparisonMatrix> =>
    apiClient.get(`/marketplace/requests/${requestId}/comparison-matrix`),

  extractQuote: (data: { text?: string; source_filename?: string }): Promise<AIExtractionLog> =>
    apiClient.post('/marketplace/extractions/quote', data),

  extractCompletion: (data: { text?: string; source_filename?: string }): Promise<AIExtractionLog> =>
    apiClient.post('/marketplace/extractions/completion', data),

  confirmExtraction: (logId: string): Promise<AIExtractionLog> =>
    apiClient.post(`/marketplace/extractions/${logId}/confirm`, {}),

  correctExtraction: (logId: string, data: { corrected_data: Record<string, unknown>; notes?: string }): Promise<AIExtractionLog> =>
    apiClient.post(`/marketplace/extractions/${logId}/correct`, data),

  rejectExtraction: (logId: string, data: { reason: string }): Promise<AIExtractionLog> =>
    apiClient.post(`/marketplace/extractions/${logId}/reject`, data),

  getFlywheelMetrics: (): Promise<FlywheelMetrics> =>
    apiClient.get('/admin/remediation/flywheel-metrics'),
};
