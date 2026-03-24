import { apiClient } from '@/api/client';

export interface EvidenceRequirement {
  document_type: string;
  description: string;
  mandatory: boolean;
  legal_ref?: string | null;
}

export interface MaterialRecommendation {
  original_material_type: string;
  original_pollutant: string;
  recommended_material: string;
  recommended_material_type: string;
  reason: string;
  risk_level: string;
  evidence_requirements: EvidenceRequirement[];
  risk_flags: string[];
}

export interface MaterialRecommendationReport {
  building_id: string;
  intervention_count: number;
  pollutant_material_count: number;
  recommendations: MaterialRecommendation[];
  summary: string;
}

export const materialRecommendationsApi = {
  get: async (buildingId: string): Promise<MaterialRecommendationReport> => {
    const response = await apiClient.get<MaterialRecommendationReport>(
      `/buildings/${buildingId}/material-recommendations`,
    );
    return response.data;
  },
};
