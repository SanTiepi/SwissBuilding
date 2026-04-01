import { apiClient, type ApiRequestConfig } from '@/api/client';

export interface PollutantDetail {
  probability: number;
  reason: string;
}

export interface MaterialRecognitionResult {
  material_type: string;
  material_name: string;
  estimated_year_range: string;
  identified_materials: string[];
  likely_pollutants: Record<string, PollutantDetail>;
  confidence_overall: number;
  recommendations: string[];
  description: string;
  has_high_risk: boolean;
}

export const materialRecognitionApi = {
  recognize: async (
    buildingId: string,
    file: File,
    options?: { zoneId?: string; elementId?: string; save?: boolean },
  ): Promise<MaterialRecognitionResult> => {
    const formData = new FormData();
    formData.append('file', file);
    if (options?.zoneId) formData.append('zone_id', options.zoneId);
    if (options?.elementId) formData.append('element_id', options.elementId);
    if (options?.save) formData.append('save', 'true');

    const requestConfig: ApiRequestConfig = {
      headers: { 'Content-Type': 'multipart/form-data' },
      skipRetry: true,
      timeout: 30000,
    };

    const response = await apiClient.post<MaterialRecognitionResult>(
      `/buildings/${buildingId}/materials/recognize`,
      formData,
      requestConfig,
    );
    return response.data;
  },
};
