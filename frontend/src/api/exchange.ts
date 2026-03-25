import { apiClient } from '@/api/client';

export interface ExchangeContract {
  id: string;
  contract_code: string;
  version: number;
  status: string;
  audience_type: string;
  payload_type: string;
  schema_reference: string | null;
  effective_from: string;
  effective_to: string | null;
  compatibility_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Publication {
  id: string;
  building_id: string;
  contract_version_id: string;
  audience_type: string;
  publication_type: string;
  pack_id: string | null;
  content_hash: string;
  published_at: string;
  published_by_org_id: string | null;
  published_by_user_id: string | null;
  delivery_state: string;
  superseded_by_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImportReceipt {
  id: string;
  building_id: string | null;
  source_system: string;
  contract_code: string;
  contract_version: number;
  import_reference: string | null;
  imported_at: string;
  status: string;
  content_hash: string;
  rejection_reason: string | null;
  matched_publication_id: string | null;
  notes: string | null;
  created_at: string;
}

export const exchangeApi = {
  async listPublications(buildingId: string): Promise<Publication[]> {
    const res = await apiClient.get<Publication[]>(`/buildings/${buildingId}/passport-publications`);
    return res.data;
  },

  async listImportReceipts(buildingId: string): Promise<ImportReceipt[]> {
    const res = await apiClient.get<ImportReceipt[]>(`/buildings/${buildingId}/import-receipts`);
    return res.data;
  },

  async listContracts(): Promise<ExchangeContract[]> {
    const res = await apiClient.get<ExchangeContract[]>('/exchange/contracts');
    return res.data;
  },
};
