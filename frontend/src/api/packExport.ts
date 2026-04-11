import { apiClient } from '@/api/client';

export interface ShareLinkResponse {
  share_url: string;
  access_token: string;
  expires_at: string;
}

export interface SharedArtifactData {
  building_address: string;
  building_city: string;
  building_canton: string;
  building_postal_code: string;
  pack_type: string;
  pack_name: string;
  generated_at: string;
  expires_at: string;
  overall_completeness: number;
  passport_grade: string | null;
  readiness_verdict: string | null;
  sections: Array<{
    section_name: string;
    items_count: number;
    completeness: number;
  }>;
  caveats: string[];
  sha256_hash: string | null;
  shared_by_org: string | null;
}

export const packExportApi = {
  generateAuthorityPdf: async (buildingId: string, redactFinancials = false): Promise<Blob> => {
    const resp = await apiClient.post(
      `/buildings/${buildingId}/packs/authority/pdf`,
      { redact_financials: redactFinancials },
      { responseType: 'blob' },
    );
    return resp.data;
  },

  generateTransactionPdf: async (buildingId: string, redactFinancials = true): Promise<Blob> => {
    const resp = await apiClient.post(
      `/buildings/${buildingId}/packs/transaction/pdf`,
      { redact_financials: redactFinancials },
      { responseType: 'blob' },
    );
    return resp.data;
  },

  generatePackPdf: async (buildingId: string, packType: string, redactFinancials = false): Promise<Blob> => {
    const resp = await apiClient.post(
      `/buildings/${buildingId}/packs/${packType}/pdf`,
      { redact_financials: redactFinancials },
      { responseType: 'blob' },
    );
    return resp.data;
  },

  createShareLink: async (buildingId: string, packType: string, expiresDays = 7): Promise<ShareLinkResponse> => {
    const resp = await apiClient.post(`/buildings/${buildingId}/packs/${packType}/share`, {
      expires_days: expiresDays,
    });
    return resp.data;
  },

  viewShared: async (accessToken: string): Promise<SharedArtifactData> => {
    const resp = await apiClient.get(`/shared/${accessToken}/artifact`);
    return resp.data;
  },
};
