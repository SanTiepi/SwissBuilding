import { apiClient } from '@/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ExtractedSample {
  sample_id: string;
  location: string | null;
  material_type: string | null;
  result: 'positive' | 'negative' | 'trace' | 'not_tested';
  concentration: number | null;
  unit: string | null;
  threshold_exceeded: boolean | null;
  confidence: number;
}

export interface ExtractedScope {
  zones_covered: string[];
  zones_excluded: string[];
  elements_sampled: number;
  elements_positive: number;
}

export interface ExtractedConclusions {
  overall_result: 'presence' | 'absence' | 'partial';
  risk_level: 'low' | 'medium' | 'high' | 'critical' | 'unknown';
  recommendations: string[];
}

export interface ExtractedRegulatoryContext {
  regulation_ref: string | null;
  threshold_applied: string | null;
  work_category: 'minor' | 'medium' | 'major' | null;
}

export interface ExtractedData {
  report_type: string;
  lab_name: string | null;
  lab_reference: string | null;
  report_date: string | null;
  validity_date: string | null;
  scope: ExtractedScope;
  samples: ExtractedSample[];
  conclusions: ExtractedConclusions;
  regulatory_context: ExtractedRegulatoryContext;
}

export interface DiagnosticExtraction {
  id: string;
  document_id: string;
  building_id: string;
  created_by_id: string;
  status: 'draft' | 'reviewed' | 'applied' | 'rejected';
  confidence: number | null;
  extracted_data: ExtractedData | null;
  corrections: Array<{
    field_path: string;
    old_value: unknown;
    new_value: unknown;
    corrected_by_id: string;
    timestamp: string;
  }> | null;
  applied_at: string | null;
  reviewed_by_id: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ApplyExtractionResponse {
  diagnostic_id: string;
  sample_ids: string[];
  evidence_link_id: string;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function triggerExtraction(documentId: string): Promise<DiagnosticExtraction> {
  const response = await apiClient.post<DiagnosticExtraction>(`/documents/${documentId}/extract`);
  return response.data;
}

export async function getExtraction(extractionId: string): Promise<DiagnosticExtraction> {
  const response = await apiClient.get<DiagnosticExtraction>(`/extractions/${extractionId}`);
  return response.data;
}

export async function reviewExtraction(
  extractionId: string,
  data: Partial<ExtractedData>,
): Promise<DiagnosticExtraction> {
  const response = await apiClient.put<DiagnosticExtraction>(`/extractions/${extractionId}/review`, {
    extracted_data: data,
  });
  return response.data;
}

export async function applyExtraction(extractionId: string): Promise<ApplyExtractionResponse> {
  const response = await apiClient.post<ApplyExtractionResponse>(`/extractions/${extractionId}/apply`);
  return response.data;
}

export async function rejectExtraction(extractionId: string, reason: string): Promise<void> {
  await apiClient.post(`/extractions/${extractionId}/reject`, { reason });
}

export async function recordCorrection(
  extractionId: string,
  fieldPath: string,
  oldValue: unknown,
  newValue: unknown,
): Promise<void> {
  await apiClient.post(`/extractions/${extractionId}/corrections`, {
    field_path: fieldPath,
    old_value: oldValue,
    new_value: newValue,
  });
}
