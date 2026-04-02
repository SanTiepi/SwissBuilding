import { apiClient } from '@/api/client';
import type { CompletenessResult } from '@/types';

/* ------------------------------------------------------------------ */
/*  Types — 16-dimension dashboard                                     */
/* ------------------------------------------------------------------ */

export interface MissingItem {
  field: string;
  importance: 'critical' | 'important' | 'nice_to_have';
}

export interface DimensionScore {
  key: string;
  label: string;
  score: number;
  max_weight: number;
  color: 'green' | 'yellow' | 'orange' | 'red';
  missing_items: MissingItem[];
  required_actions: Array<{ action: string; priority: string; effort: string }>;
}

export interface CompletenessDashboard {
  building_id: string;
  overall_score: number;
  overall_color: string;
  dimensions: DimensionScore[];
  missing_items_count: number;
  urgent_actions: number;
  recommended_actions: number;
  trend: 'improving' | 'stable' | 'declining';
  evaluated_at: string;
}

export interface MissingItemDetail {
  dimension: string;
  dimension_label: string;
  field: string;
  importance: string;
  status: string;
}

export interface MissingItemsResponse {
  building_id: string;
  items: MissingItemDetail[];
  total: number;
}

export interface RecommendedAction {
  dimension: string;
  dimension_label: string;
  action: string;
  priority: string;
  effort: string;
}

export interface RecommendedActionsResponse {
  building_id: string;
  actions: RecommendedAction[];
  total: number;
}

/* ------------------------------------------------------------------ */
/*  API functions                                                      */
/* ------------------------------------------------------------------ */

export const completenessApi = {
  /** Existing AvT/ApT workflow completeness. */
  evaluate: async (buildingId: string, stage: string = 'avt'): Promise<CompletenessResult> => {
    const response = await apiClient.get<CompletenessResult>(`/buildings/${buildingId}/completeness`, {
      params: { stage },
    });
    return response.data;
  },

  /** 16-dimension completeness dashboard. */
  getDashboard: async (buildingId: string): Promise<CompletenessDashboard> => {
    const { data } = await apiClient.get<CompletenessDashboard>(
      `/buildings/${buildingId}/completeness/dashboard`,
    );
    return data;
  },

  getMissingItems: async (buildingId: string): Promise<MissingItemsResponse> => {
    const { data } = await apiClient.get<MissingItemsResponse>(
      `/buildings/${buildingId}/completeness/missing-items`,
    );
    return data;
  },

  getRecommendedActions: async (buildingId: string): Promise<RecommendedActionsResponse> => {
    const { data } = await apiClient.get<RecommendedActionsResponse>(
      `/buildings/${buildingId}/completeness/recommended-actions`,
    );
    return data;
  },
};
