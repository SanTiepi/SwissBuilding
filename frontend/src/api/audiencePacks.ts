import { apiClient } from '@/api/client';

// --- Types ---

export interface AudiencePackSection {
  name: string;
  included: boolean;
  blocked: boolean;
}

export interface UnknownSummaryItem {
  category: string;
  description: string;
  severity: string;
}

export interface ContradictionSummaryItem {
  type: string;
  description: string;
  severity: string;
}

export interface ResidualRiskItem {
  source: string;
  description: string;
  level: string;
}

export interface TrustRef {
  source: string;
  confidence: number;
  freshness: string;
}

export interface ProofRef {
  document_id: string;
  title: string;
  version: number;
  freshness: string;
}

export interface CaveatEvaluation {
  caveat_type: string;
  severity: string;
  message: string;
  applies_when: Record<string, unknown>;
}

export interface AudiencePackData {
  id: string;
  building_id: string;
  pack_type: string;
  pack_version: number;
  status: string;
  generated_by_user_id: string | null;
  sections: Record<string, AudiencePackSection>;
  unknowns_summary: UnknownSummaryItem[] | null;
  contradictions_summary: ContradictionSummaryItem[] | null;
  residual_risk_summary: ResidualRiskItem[] | null;
  trust_refs: TrustRef[] | null;
  proof_refs: ProofRef[] | null;
  content_hash: string;
  generated_at: string;
  superseded_by_id: string | null;
  created_at: string;
  updated_at: string;
  caveats: CaveatEvaluation[] | null;
}

export interface AudiencePackListItem {
  id: string;
  building_id: string;
  pack_type: string;
  pack_version: number;
  status: string;
  generated_at: string;
  content_hash: string;
  created_at: string;
}

export interface PackComparisonData {
  pack_1: AudiencePackData;
  pack_2: AudiencePackData;
  section_diff: Record<string, { only_in_1?: string[]; only_in_2?: string[]; changed?: string[] }>;
  caveat_diff: Record<string, CaveatEvaluation[]>;
}

export const audiencePacksApi = {
  listByBuilding: async (buildingId: string, type?: string): Promise<AudiencePackListItem[]> => {
    const params: Record<string, string> = {};
    if (type) params.type = type;
    const response = await apiClient.get<AudiencePackListItem[]>(`/buildings/${buildingId}/audience-packs`, { params });
    return response.data;
  },

  get: async (packId: string): Promise<AudiencePackData> => {
    const response = await apiClient.get<AudiencePackData>(`/audience-packs/${packId}`);
    return response.data;
  },

  generate: async (buildingId: string, packType: string): Promise<AudiencePackData> => {
    const response = await apiClient.post<AudiencePackData>(`/buildings/${buildingId}/audience-packs`, {
      pack_type: packType,
    });
    return response.data;
  },

  share: async (packId: string): Promise<AudiencePackData> => {
    const response = await apiClient.post<AudiencePackData>(`/audience-packs/${packId}/share`);
    return response.data;
  },

  compare: async (packId1: string, packId2: string): Promise<PackComparisonData> => {
    const response = await apiClient.get<PackComparisonData>('/audience-packs/compare', {
      params: { pack1: packId1, pack2: packId2 },
    });
    return response.data;
  },

  getCaveats: async (buildingId: string, audience: string): Promise<CaveatEvaluation[]> => {
    const response = await apiClient.get<CaveatEvaluation[]>(`/buildings/${buildingId}/caveats`, {
      params: { audience },
    });
    return response.data;
  },
};
