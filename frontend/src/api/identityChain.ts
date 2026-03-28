import { apiClient } from '@/api/client';

export interface IdentityEgidDetail {
  value: number | null;
  source: string | null;
  confidence: number | null;
  resolved_at: string | null;
}

export interface IdentityEgridDetail {
  value: string | null;
  parcel_number: string | null;
  area_m2: number | null;
  source: string | null;
  resolved_at: string | null;
}

export interface RdppfRestriction {
  type: string;
  layer?: string | null;
  description?: string | null;
  authority?: string | null;
  in_force_since?: string | null;
}

export interface IdentityRdppfDetail {
  restrictions: RdppfRestriction[];
  themes: string[];
  source: string | null;
  resolved_at: string | null;
}

export interface IdentityChainResponse {
  egid: IdentityEgidDetail;
  egrid: IdentityEgridDetail;
  rdppf: IdentityRdppfDetail;
  chain_complete: boolean;
  chain_gaps: string[];
  cached: boolean;
}

export const identityChainApi = {
  get: async (buildingId: string): Promise<IdentityChainResponse> => {
    const response = await apiClient.get<IdentityChainResponse>(
      `/buildings/${buildingId}/identity-chain`
    );
    return response.data;
  },

  resolve: async (buildingId: string): Promise<IdentityChainResponse> => {
    const response = await apiClient.post<IdentityChainResponse>(
      `/buildings/${buildingId}/identity-chain/resolve`
    );
    return response.data;
  },

  getRdppf: async (buildingId: string): Promise<IdentityRdppfDetail> => {
    const response = await apiClient.get<IdentityRdppfDetail>(`/buildings/${buildingId}/rdppf`);
    return response.data;
  },
};
