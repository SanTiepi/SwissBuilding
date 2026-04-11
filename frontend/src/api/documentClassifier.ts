import { apiClient } from '@/api/client';

export interface ClassificationCandidate {
  type: string;
  confidence: number;
}

export interface ClassificationResult {
  document_id: string | null;
  document_type: string;
  confidence: number;
  method: 'filename' | 'content' | 'hybrid';
  candidates: ClassificationCandidate[];
  ai_generated: boolean;
  keywords_found: string[];
}

export interface BatchClassificationResult {
  building_id: string;
  total_processed: number;
  classified_count: number;
  unclassified_count: number;
  results: ClassificationResult[];
}

export interface DocumentTypeInfo {
  type_key: string;
  label_fr: string;
  label_en: string;
  label_de: string;
  label_it: string;
  keywords: string[];
}

export const documentClassifierApi = {
  classifySingle: async (documentId: string): Promise<ClassificationResult> => {
    const response = await apiClient.post<ClassificationResult>(`/documents/${documentId}/classify`);
    return response.data;
  },

  batchClassify: async (buildingId: string): Promise<BatchClassificationResult> => {
    const response = await apiClient.post<BatchClassificationResult>(
      `/buildings/${buildingId}/documents/classify-all`,
    );
    return response.data;
  },

  listTypes: async (): Promise<DocumentTypeInfo[]> => {
    const response = await apiClient.get<DocumentTypeInfo[]>('/documents/types');
    return response.data;
  },
};
