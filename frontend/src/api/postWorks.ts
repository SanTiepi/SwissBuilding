import { apiClient } from '@/api/client';
import type { PaginatedResponse } from '@/types';

export interface PostWorksState {
  id: string;
  building_id: string;
  intervention_id: string | null;
  state_type: string;
  pollutant_type: string | null;
  title: string;
  description: string | null;
  zone_id: string | null;
  element_id: string | null;
  material_id: string | null;
  verified: boolean;
  verified_by: string | null;
  verified_at: string | null;
  evidence_json: string | null;
  recorded_by: string | null;
  recorded_at: string;
  notes: string | null;
}

export interface BeforeAfterComparison {
  building_id: string;
  intervention_id: string | null;
  before: {
    total_positive_samples: number;
    by_pollutant: Record<string, number>;
    risk_areas: Array<{ pollutant: string; location: string; risk_level: string }>;
  };
  after: {
    removed: number;
    remaining: number;
    encapsulated: number;
    treated: number;
    unknown_after_intervention: number;
    recheck_needed: number;
    by_pollutant: Record<string, Record<string, number>>;
  };
  summary: {
    remediation_rate: number;
    verification_rate: number;
    residual_risk_count: number;
  };
}

export interface PostWorksSummary {
  building_id: string;
  total_states: number;
  by_state_type: Record<string, number>;
  by_pollutant: Record<string, number>;
  verification_progress: {
    verified: number;
    unverified: number;
    rate: number;
  };
  interventions_covered: number;
}

export const postWorksApi = {
  list: async (buildingId: string): Promise<PaginatedResponse<PostWorksState>> => {
    const response = await apiClient.get<PaginatedResponse<PostWorksState>>(`/buildings/${buildingId}/post-works`, {
      params: { size: 50 },
    });
    return response.data;
  },
  compare: async (buildingId: string, interventionId?: string): Promise<BeforeAfterComparison> => {
    const params: Record<string, string> = {};
    if (interventionId) params.intervention_id = interventionId;
    const response = await apiClient.get<BeforeAfterComparison>(`/buildings/${buildingId}/post-works/compare`, {
      params,
    });
    return response.data;
  },
  summary: async (buildingId: string): Promise<PostWorksSummary> => {
    const response = await apiClient.get<PostWorksSummary>(`/buildings/${buildingId}/post-works/summary`);
    return response.data;
  },
  verify: async (buildingId: string, stateId: string, notes?: string): Promise<PostWorksState> => {
    const response = await apiClient.put<PostWorksState>(`/buildings/${buildingId}/post-works/${stateId}`, {
      verified: true,
      notes,
    });
    return response.data;
  },
};
