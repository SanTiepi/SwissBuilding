import { apiClient } from '@/api/client';

export interface PostWorksLinkData {
  id: string;
  completion_confirmation_id: string;
  intervention_id: string;
  before_snapshot_id: string | null;
  after_snapshot_id: string | null;
  status: string;
  grade_delta: { before: string; after: string; change: string } | null;
  trust_delta: { before: number; after: number; change: number } | null;
  completeness_delta: { before: number; after: number; change: number } | null;
  residual_risks: Array<{ risk_type: string; description: string; severity: string }> | null;
  drafted_at: string | null;
  finalized_at: string | null;
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface DomainEventData {
  id: string;
  event_type: string;
  aggregate_type: string;
  aggregate_id: string;
  payload: Record<string, unknown> | null;
  actor_user_id: string | null;
  occurred_at: string;
  created_at: string | null;
}

export interface AIFeedbackPayload {
  feedback_type: 'confirm' | 'correct' | 'reject';
  entity_type: string;
  entity_id: string;
  original_output?: Record<string, unknown> | null;
  corrected_output?: Record<string, unknown> | null;
  ai_model?: string | null;
  confidence?: number | null;
  notes?: string | null;
}

export interface AIFeedbackData extends AIFeedbackPayload {
  id: string;
  user_id: string;
  created_at: string | null;
}

export const remediationPostWorksApi = {
  draftPostWorks: async (completionId: string): Promise<PostWorksLinkData> => {
    const response = await apiClient.post<PostWorksLinkData>(
      `/marketplace/completions/${completionId}/draft-post-works`,
    );
    return response.data;
  },

  reviewPostWorks: async (completionId: string): Promise<PostWorksLinkData> => {
    const response = await apiClient.post<PostWorksLinkData>(
      `/marketplace/completions/${completionId}/review-post-works`,
    );
    return response.data;
  },

  finalizePostWorks: async (completionId: string): Promise<PostWorksLinkData> => {
    const response = await apiClient.post<PostWorksLinkData>(
      `/marketplace/completions/${completionId}/finalize-post-works`,
    );
    return response.data;
  },

  getPostWorks: async (completionId: string): Promise<PostWorksLinkData> => {
    const response = await apiClient.get<PostWorksLinkData>(`/marketplace/completions/${completionId}/post-works`);
    return response.data;
  },

  getBuildingOutcomes: async (buildingId: string): Promise<PostWorksLinkData[]> => {
    const response = await apiClient.get<PostWorksLinkData[]>(`/buildings/${buildingId}/remediation-outcomes`);
    return response.data;
  },

  submitFeedback: async (payload: AIFeedbackPayload): Promise<AIFeedbackData> => {
    const response = await apiClient.post<AIFeedbackData>('/ai-feedback', payload);
    return response.data;
  },

  listDomainEvents: async (params?: {
    aggregate_type?: string;
    aggregate_id?: string;
    limit?: number;
  }): Promise<DomainEventData[]> => {
    const response = await apiClient.get<DomainEventData[]>('/domain-events', { params });
    return response.data;
  },
};
