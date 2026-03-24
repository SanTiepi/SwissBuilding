import { apiClient } from '@/api/client';

export interface EcoClause {
  clause_id: string;
  title: string;
  body: string;
  legal_references: string[];
  applicability: string;
  pollutants: string[];
}

export interface EcoClauseSection {
  section_id: string;
  title: string;
  clauses: EcoClause[];
}

export interface EcoClausePayload {
  building_id: string;
  context: 'renovation' | 'demolition';
  generated_at: string;
  total_clauses: number;
  detected_pollutants: string[];
  sections: EcoClauseSection[];
}

export const ecoClausesApi = {
  get: async (buildingId: string, context: 'renovation' | 'demolition' = 'renovation'): Promise<EcoClausePayload> => {
    const response = await apiClient.get<EcoClausePayload>(`/buildings/${buildingId}/eco-clauses`, {
      params: { context },
    });
    return response.data;
  },
};
