import { apiClient } from '@/api/client';
import type { PaginatedResponse } from '@/types';

export type EvidencePackType = 'authority_pack' | 'contractor_pack' | 'owner_pack';
export type EvidencePackStatus = 'draft' | 'assembling' | 'complete' | 'submitted' | 'expired';
export type EvidencePackPurpose = 'authority_submission' | 'internal_audit' | 'handoff' | 'insurance';
export type RecipientType = 'authority' | 'contractor' | 'owner' | 'insurer';

export interface IncludedArtefact {
  artefact_type: string;
  artefact_id: string;
  status: string;
  title?: string;
}

export interface IncludedDocument {
  document_id: string;
  document_type: string;
  title?: string;
}

export interface RequiredSection {
  section_type: string;
  label: string;
  required: boolean;
  included: boolean;
}

export interface EvidencePack {
  id: string;
  building_id: string;
  pack_type: string;
  title: string;
  description: string | null;
  status: string;
  required_sections_json: RequiredSection[] | null;
  included_artefacts_json: IncludedArtefact[] | null;
  included_documents_json: IncludedDocument[] | null;
  recipient_name: string | null;
  recipient_type: string | null;
  recipient_organization_id: string | null;
  export_job_id: string | null;
  assembled_at: string | null;
  submitted_at: string | null;
  expires_at: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  notes: string | null;
}

export interface EvidencePackCreate {
  pack_type: string;
  title: string;
  description?: string;
  status?: string;
  required_sections_json?: RequiredSection[];
  included_artefacts_json?: IncludedArtefact[];
  included_documents_json?: IncludedDocument[];
  recipient_name?: string;
  recipient_type?: string;
  recipient_organization_id?: string;
  notes?: string;
}

export interface EvidencePackUpdate {
  pack_type?: string;
  title?: string;
  description?: string;
  status?: string;
  required_sections_json?: RequiredSection[];
  included_artefacts_json?: IncludedArtefact[];
  included_documents_json?: IncludedDocument[];
  recipient_name?: string;
  recipient_type?: string;
  notes?: string;
}

export const evidencePacksApi = {
  list: async (
    buildingId: string,
    params?: { page?: number; size?: number; pack_type?: string; status?: string },
  ): Promise<PaginatedResponse<EvidencePack>> => {
    const response = await apiClient.get<PaginatedResponse<EvidencePack>>(`/buildings/${buildingId}/evidence-packs`, {
      params,
    });
    return response.data;
  },

  get: async (buildingId: string, packId: string): Promise<EvidencePack> => {
    const response = await apiClient.get<EvidencePack>(`/buildings/${buildingId}/evidence-packs/${packId}`);
    return response.data;
  },

  create: async (buildingId: string, data: EvidencePackCreate): Promise<EvidencePack> => {
    const response = await apiClient.post<EvidencePack>(`/buildings/${buildingId}/evidence-packs`, data);
    return response.data;
  },

  update: async (buildingId: string, packId: string, data: EvidencePackUpdate): Promise<EvidencePack> => {
    const response = await apiClient.put<EvidencePack>(`/buildings/${buildingId}/evidence-packs/${packId}`, data);
    return response.data;
  },

  delete: async (buildingId: string, packId: string): Promise<void> => {
    await apiClient.delete(`/buildings/${buildingId}/evidence-packs/${packId}`);
  },
};
