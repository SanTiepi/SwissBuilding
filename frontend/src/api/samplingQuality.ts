import { apiClient } from '@/api/client';

export interface SamplingCriterion {
  name: string;
  score: number;
  max: number;
  detail: string;
  recommendation: string;
}

export interface SamplingQuality {
  diagnostic_id: string;
  overall_score: number;
  grade: string;
  criteria: SamplingCriterion[];
  confidence_level: string;
  warnings: string[];
  evaluated_at: string;
}

export interface BuildingSamplingQuality {
  building_id: string;
  avg_score: number;
  worst_diagnostic: string | null;
  best_diagnostic: string | null;
  diagnostics: SamplingQuality[];
  evaluated_at: string;
}

export const samplingQualityApi = {
  getDiagnostic: async (diagnosticId: string): Promise<SamplingQuality> => {
    const response = await apiClient.get<SamplingQuality>(
      `/diagnostics/${diagnosticId}/sampling-quality`,
    );
    return response.data;
  },

  getBuilding: async (buildingId: string): Promise<BuildingSamplingQuality> => {
    const response = await apiClient.get<BuildingSamplingQuality>(
      `/buildings/${buildingId}/sampling-quality`,
    );
    return response.data;
  },
};
