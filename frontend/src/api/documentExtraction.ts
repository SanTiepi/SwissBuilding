import { apiClient } from '@/api/client';

export interface ExtractionField {
  field: string;
  value: string;
  raw_match: string;
  position: number;
  confidence: number;
  ai_generated: boolean;
}

export interface ExtractionResult {
  document_id: string;
  total_fields: number;
  field_counts: Record<string, number>;
  extractions: Record<string, ExtractionField[]>;
}

export const documentExtractionApi = {
  extract: async (documentId: string): Promise<ExtractionResult> => {
    const response = await apiClient.post<ExtractionResult>(`/documents/${documentId}/extract-fields`);
    return response.data;
  },

  getExtractions: async (documentId: string): Promise<ExtractionResult | null> => {
    const response = await apiClient.get<ExtractionResult | null>(`/documents/${documentId}/extractions`);
    return response.data;
  },
};
