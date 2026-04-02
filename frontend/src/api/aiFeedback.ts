import { apiClient } from './client';

export interface AIFeedbackCreate {
  entity_type: string;
  entity_id?: string;
  field_name: string;
  original_value: string;
  corrected_value: string;
  model_version?: string;
  notes?: string;
}

export interface AIFeedbackRead {
  id: string;
  feedback_type: string;
  entity_type: string;
  entity_id: string;
  field_name: string | null;
  original_value: string | null;
  corrected_value: string | null;
  confidence_delta: number | null;
  model_version: string | null;
  user_id: string;
  notes: string | null;
  created_at: string;
}

export interface CommonErrorEntry {
  original: string;
  corrected: string;
  count: number;
}

export interface AIMetricsRead {
  id: string;
  entity_type: string;
  field_name: string;
  total_extractions: number;
  total_corrections: number;
  error_rate: number;
  common_errors: CommonErrorEntry[];
  updated_at: string;
}

export interface AIMetricsSummary {
  overall_accuracy: number;
  total_extractions: number;
  total_corrections: number;
  metrics: AIMetricsRead[];
}

export const aiFeedbackApi = {
  recordFeedback: (diagnosticId: string, data: AIFeedbackCreate) =>
    apiClient.post<AIFeedbackRead>(`/diagnostics/${diagnosticId}/feedback`, data),

  getMetrics: (entityType?: string) =>
    apiClient.get<AIMetricsSummary>('/analytics/ai-metrics', {
      params: entityType ? { entity_type: entityType } : undefined,
    }),

  getMetricsByType: (entityType: string) =>
    apiClient.get<AIMetricsRead[]>(`/analytics/ai-metrics/${entityType}`),

  listFeedback: (params?: { entity_type?: string; entity_id?: string; limit?: number }) =>
    apiClient.get<AIFeedbackRead[]>('/analytics/ai-feedback', { params }),
};
