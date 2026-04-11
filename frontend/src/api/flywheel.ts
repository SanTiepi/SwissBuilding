import { apiClient } from '@/api/client';

export interface ClassificationFeedbackCreate {
  document_id: string;
  predicted_type: string;
  corrected_type: string;
}

export interface ExtractionFeedbackCreate {
  document_id: string;
  field_name: string;
  predicted_value: string;
  corrected_value?: string | null;
  accepted: boolean;
}

export interface ConfusionPair {
  predicted: string;
  actual: string;
  count: number;
}

export interface PerTypeAccuracy {
  accuracy: number;
  total: number;
  correct: number;
}

export interface ClassificationAccuracy {
  overall_accuracy: number;
  per_type_accuracy: Record<string, PerTypeAccuracy>;
  confusion_matrix: ConfusionPair[];
  total_predictions: number;
  total_corrections: number;
  trend: string;
}

export interface ExtractionAccuracy {
  overall_accuracy: number;
  per_field_accuracy: Record<string, PerTypeAccuracy>;
  total_extractions: number;
  total_corrections: number;
  trend: string;
}

export interface LearnedRule {
  predicted_type: string;
  corrected_type: string;
  occurrence_count: number;
  confidence: number;
  suggestion: string;
}

export interface FlywheelDashboard {
  classification_accuracy: number;
  extraction_accuracy: number;
  total_documents_processed: number;
  total_corrections: number;
  correction_rate: number;
  top_confusion_pairs: ConfusionPair[];
  learned_rules_count: number;
  learned_rules: LearnedRule[];
  improvement_trend: string;
}

export const flywheelApi = {
  recordClassificationFeedback: async (data: ClassificationFeedbackCreate) => {
    const response = await apiClient.post('/flywheel/classification-feedback', data);
    return response.data;
  },

  recordExtractionFeedback: async (data: ExtractionFeedbackCreate) => {
    const response = await apiClient.post('/flywheel/extraction-feedback', data);
    return response.data;
  },

  getClassificationAccuracy: async (orgId?: string): Promise<ClassificationAccuracy> => {
    const params = orgId ? { org_id: orgId } : {};
    const response = await apiClient.get<ClassificationAccuracy>('/flywheel/accuracy/classification', { params });
    return response.data;
  },

  getExtractionAccuracy: async (orgId?: string): Promise<ExtractionAccuracy> => {
    const params = orgId ? { org_id: orgId } : {};
    const response = await apiClient.get<ExtractionAccuracy>('/flywheel/accuracy/extraction', { params });
    return response.data;
  },

  getLearnedRules: async (documentType?: string): Promise<LearnedRule[]> => {
    const params = documentType ? { document_type: documentType } : {};
    const response = await apiClient.get<LearnedRule[]>('/flywheel/learned-rules', { params });
    return response.data;
  },

  getDashboard: async (orgId?: string): Promise<FlywheelDashboard> => {
    const params = orgId ? { org_id: orgId } : {};
    const response = await apiClient.get<FlywheelDashboard>('/flywheel/dashboard', { params });
    return response.data;
  },
};
