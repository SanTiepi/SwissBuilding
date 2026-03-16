import { apiClient } from '@/api/client';

export interface BuildingComparisonEntry {
  building_id: string;
  building_name: string;
  address: string;
  passport_grade: string | null;
  passport_score: number | null;
  trust_score: number | null;
  completeness_score: number | null;
  readiness_summary: Record<string, boolean>;
  open_actions_count: number;
  open_unknowns_count: number;
  contradictions_count: number;
  diagnostic_count: number;
  last_diagnostic_date: string | null;
}

export interface BuildingComparison {
  buildings: BuildingComparisonEntry[];
  comparison_dimensions: string[];
  best_passport: string | null;
  worst_passport: string | null;
  average_trust: number;
  average_completeness: number;
}

export const buildingComparisonApi = {
  compare: async (buildingIds: string[]): Promise<BuildingComparison> => {
    const response = await apiClient.post<BuildingComparison>('/buildings/compare', {
      building_ids: buildingIds,
    });
    return response.data;
  },
};
