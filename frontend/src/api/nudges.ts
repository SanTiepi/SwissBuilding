import { apiClient } from '@/api/client';

export interface CostOfInaction {
  description: string;
  estimated_chf_min: number;
  estimated_chf_max: number;
  confidence: string;
}

export interface NudgeRelatedEntity {
  entity_type: string;
  entity_id: string | null;
}

export interface Nudge {
  id: string;
  nudge_type: string;
  severity: 'critical' | 'warning' | 'info';
  headline: string;
  loss_framing: string;
  gain_framing: string;
  cost_of_inaction: CostOfInaction | null;
  deadline_pressure: number | null;
  social_proof: string | null;
  call_to_action: string;
  related_entity: NudgeRelatedEntity | null;
}

export interface NudgeList {
  entity_id: string;
  nudges: Nudge[];
  total: number;
  context: string;
}

export type NudgeContext = 'dashboard' | 'detail' | 'email';

export const nudgesApi = {
  listForBuilding: async (buildingId: string, context?: NudgeContext): Promise<NudgeList> => {
    const response = await apiClient.get<NudgeList>(`/buildings/${buildingId}/nudges`, {
      params: { context: context ?? 'dashboard' },
    });
    return response.data;
  },

  listForPortfolio: async (context?: NudgeContext): Promise<NudgeList> => {
    const response = await apiClient.get<NudgeList>('/portfolio/nudges', {
      params: { context: context ?? 'dashboard' },
    });
    return response.data;
  },
};
