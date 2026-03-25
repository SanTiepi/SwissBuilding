import { apiClient } from '@/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ClientRequest {
  id: string;
  building_id: string;
  requester_user_id: string;
  requester_org_id: string | null;
  title: string;
  description: string | null;
  pollutant_types: string[] | null;
  work_category: string;
  estimated_area_m2: number | null;
  deadline: string | null;
  status: string;
  diagnostic_publication_id: string | null;
  budget_indication: string | null;
  site_access_notes: string | null;
  published_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface QuoteData {
  id: string;
  client_request_id: string;
  company_profile_id: string;
  invitation_id: string | null;
  amount_chf: string;
  currency: string;
  validity_days: number;
  description: string | null;
  work_plan: string | null;
  timeline_weeks: number | null;
  includes: string[] | null;
  excludes: string[] | null;
  status: string;
  submitted_at: string | null;
  content_hash: string | null;
  created_at: string;
  updated_at: string;
}

export interface AwardConfirmation {
  id: string;
  client_request_id: string;
  quote_id: string;
  company_profile_id: string;
  awarded_by_user_id: string;
  award_amount_chf: string | null;
  conditions: string | null;
  content_hash: string | null;
  awarded_at: string | null;
  created_at: string;
}

export interface CompletionConfirmation {
  id: string;
  award_confirmation_id: string;
  client_confirmed: boolean;
  client_confirmed_at: string | null;
  client_confirmed_by_user_id: string | null;
  company_confirmed: boolean;
  company_confirmed_at: string | null;
  company_confirmed_by_user_id: string | null;
  status: string;
  completion_notes: string | null;
  final_amount_chf: string | null;
  content_hash: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewData {
  id: string;
  completion_confirmation_id: string;
  client_request_id: string;
  company_profile_id: string;
  reviewer_user_id: string;
  reviewer_type: string;
  rating: number;
  quality_score: number | null;
  timeliness_score: number | null;
  communication_score: number | null;
  comment: string | null;
  status: string;
  moderated_by_user_id: string | null;
  moderated_at: string | null;
  moderation_notes: string | null;
  rejection_reason: string | null;
  submitted_at: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export const marketplaceRfqApi = {
  // RFQ
  listRequests: async (params?: {
    page?: number;
    size?: number;
    building_id?: string;
    status?: string;
  }): Promise<PaginatedResponse<ClientRequest>> => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.size) searchParams.set('size', String(params.size));
    if (params?.building_id) searchParams.set('building_id', params.building_id);
    if (params?.status) searchParams.set('status', params.status);
    const query = searchParams.toString();
    return apiClient.get(`/marketplace/requests${query ? `?${query}` : ''}`);
  },

  getRequest: async (id: string): Promise<ClientRequest> => {
    return apiClient.get(`/marketplace/requests/${id}`);
  },

  createRequest: async (data: {
    building_id: string;
    title: string;
    work_category: string;
    description?: string;
    pollutant_types?: string[];
    deadline?: string;
    budget_indication?: string;
  }): Promise<ClientRequest> => {
    return apiClient.post('/marketplace/requests', data);
  },

  // Quotes
  listQuotes: async (requestId: string): Promise<QuoteData[]> => {
    return apiClient.get(`/marketplace/requests/${requestId}/quotes`);
  },

  // Award
  awardQuote: async (
    requestId: string,
    data: { quote_id: string; conditions?: string },
  ): Promise<AwardConfirmation> => {
    return apiClient.post(`/marketplace/requests/${requestId}/award`, data);
  },

  getAward: async (awardId: string): Promise<AwardConfirmation> => {
    return apiClient.get(`/marketplace/awards/${awardId}`);
  },

  // Completion
  getCompletion: async (completionId: string): Promise<CompletionConfirmation> => {
    return apiClient.get(`/marketplace/completions/${completionId}`);
  },

  confirmClient: async (
    completionId: string,
    data?: { notes?: string },
  ): Promise<CompletionConfirmation> => {
    return apiClient.post(`/marketplace/completions/${completionId}/confirm-client`, data ?? {});
  },

  confirmCompany: async (
    completionId: string,
    data?: { notes?: string },
  ): Promise<CompletionConfirmation> => {
    return apiClient.post(`/marketplace/completions/${completionId}/confirm-company`, data ?? {});
  },

  // Reviews
  submitReview: async (data: {
    completion_confirmation_id: string;
    client_request_id: string;
    company_profile_id: string;
    reviewer_type: string;
    rating: number;
    quality_score?: number;
    timeliness_score?: number;
    communication_score?: number;
    comment?: string;
  }): Promise<ReviewData> => {
    return apiClient.post('/marketplace/reviews', data);
  },

  getCompanyReviews: async (companyId: string): Promise<ReviewData[]> => {
    return apiClient.get(`/marketplace/companies/${companyId}/reviews`);
  },

  getPendingReviews: async (): Promise<ReviewData[]> => {
    return apiClient.get('/marketplace/reviews/pending');
  },

  moderateReview: async (
    reviewId: string,
    data: { decision: string; notes?: string; rejection_reason?: string },
  ): Promise<ReviewData> => {
    return apiClient.post(`/marketplace/reviews/${reviewId}/moderate`, data);
  },

  // Building linkage
  linkBuilding: async (awardId: string): Promise<{ award_id: string; building_id: string; event_id: string }> => {
    return apiClient.post(`/marketplace/awards/${awardId}/link-building`, {});
  },
};
