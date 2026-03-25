import { apiClient } from '@/api/client';

// --- Types ---

export interface PassportStateDiff {
  id: string;
  publication_id: string;
  prior_publication_id: string | null;
  diff_summary: {
    added_sections: string[];
    removed_sections: string[];
    changed_sections: { section: string; field: string; old: string | null; new: string | null }[];
  } | null;
  sections_changed_count: number;
  computed_at: string | null;
  created_at: string;
}

export interface ExchangeValidationReport {
  id: string;
  import_receipt_id: string;
  schema_valid: boolean | null;
  contract_valid: boolean | null;
  version_valid: boolean | null;
  hash_valid: boolean | null;
  identity_safe: boolean | null;
  validation_errors: { check: string; message: string; severity: string }[] | null;
  overall_status: string;
  validated_at: string | null;
  validated_by_user_id: string | null;
  created_at: string;
}

export interface ContributorRequest {
  id: string;
  building_id: string;
  contributor_type: string;
  scope_description: string | null;
  access_token: string;
  expires_at: string;
  status: string;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

export interface ContributorSubmission {
  id: string;
  request_id: string;
  contributor_org_id: string | null;
  contributor_name: string | null;
  submission_type: string;
  file_url: string | null;
  structured_data: Record<string, unknown> | null;
  notes: string | null;
  status: string;
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  created_at: string;
}

export interface ContributorReceipt {
  id: string;
  submission_id: string;
  document_id: string | null;
  receipt_hash: string;
  accepted_at: string;
  created_at: string;
}

export interface WebhookSubscription {
  id: string;
  partner_org_id: string;
  endpoint_url: string;
  subscribed_events: string[] | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// --- API ---

export const exchangeHardeningApi = {
  async getPublicationDiff(publicationId: string): Promise<PassportStateDiff> {
    const res = await apiClient.get<PassportStateDiff>(`/publications/${publicationId}/diff`);
    return res.data;
  },

  async validateImport(receiptId: string): Promise<ExchangeValidationReport> {
    const res = await apiClient.post<ExchangeValidationReport>(
      `/import-receipts/${receiptId}/validate`,
    );
    return res.data;
  },

  async reviewImport(receiptId: string, decision: string): Promise<unknown> {
    const res = await apiClient.post(`/import-receipts/${receiptId}/review`, { decision });
    return res.data;
  },

  async integrateImport(receiptId: string): Promise<unknown> {
    const res = await apiClient.post(`/import-receipts/${receiptId}/integrate`);
    return res.data;
  },

  async listContributorRequests(buildingId?: string): Promise<ContributorRequest[]> {
    const params = buildingId ? { building_id: buildingId } : {};
    const res = await apiClient.get<ContributorRequest[]>('/contributor-requests', { params });
    return res.data;
  },

  async createContributorRequest(data: {
    building_id: string;
    contributor_type: string;
    scope_description?: string;
  }): Promise<ContributorRequest> {
    const res = await apiClient.post<ContributorRequest>('/contributor-requests', data);
    return res.data;
  },

  async listPendingSubmissions(): Promise<ContributorSubmission[]> {
    const res = await apiClient.get<ContributorSubmission[]>('/contributor-submissions/pending');
    return res.data;
  },

  async acceptSubmission(submissionId: string): Promise<ContributorReceipt> {
    const res = await apiClient.post<ContributorReceipt>(
      `/contributor-submissions/${submissionId}/accept`,
    );
    return res.data;
  },

  async rejectSubmission(submissionId: string, notes?: string): Promise<ContributorSubmission> {
    const res = await apiClient.post<ContributorSubmission>(
      `/contributor-submissions/${submissionId}/reject`,
      { notes },
    );
    return res.data;
  },
};
