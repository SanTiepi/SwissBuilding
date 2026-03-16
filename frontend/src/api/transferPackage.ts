import { apiClient } from '@/api/client';

export interface TransferPackageResponse {
  package_id: string;
  building_id: string;
  generated_at: string;
  schema_version: string;
  building_summary: Record<string, unknown>;
  passport: Record<string, unknown> | null;
  diagnostics_summary: Record<string, unknown> | null;
  documents_summary: Record<string, unknown> | null;
  interventions_summary: Record<string, unknown> | null;
  actions_summary: Record<string, unknown> | null;
  evidence_coverage: Record<string, unknown> | null;
  contradictions: Record<string, unknown> | null;
  unknowns: Record<string, unknown> | null;
  snapshots: Record<string, unknown>[] | null;
  completeness: Record<string, unknown> | null;
  readiness: Record<string, unknown> | null;
  metadata: Record<string, unknown>;
}

export interface TransferPackageRequest {
  include_sections?: string[];
}

export const TRANSFER_SECTIONS = [
  'passport',
  'diagnostics',
  'documents',
  'interventions',
  'actions',
  'evidence',
  'contradictions',
  'unknowns',
  'snapshots',
  'completeness',
  'readiness',
] as const;

export type TransferSection = (typeof TRANSFER_SECTIONS)[number];

/** Map section names to their keys in the response */
const SECTION_RESPONSE_KEY: Record<TransferSection, keyof TransferPackageResponse> = {
  passport: 'passport',
  diagnostics: 'diagnostics_summary',
  documents: 'documents_summary',
  interventions: 'interventions_summary',
  actions: 'actions_summary',
  evidence: 'evidence_coverage',
  contradictions: 'contradictions',
  unknowns: 'unknowns',
  snapshots: 'snapshots',
  completeness: 'completeness',
  readiness: 'readiness',
};

export function getSectionData(
  response: TransferPackageResponse,
  section: TransferSection,
): Record<string, unknown> | Record<string, unknown>[] | null {
  return response[SECTION_RESPONSE_KEY[section]] as Record<string, unknown> | Record<string, unknown>[] | null;
}

export const transferPackageApi = {
  generate: async (buildingId: string, sections?: string[]): Promise<TransferPackageResponse> => {
    const body: TransferPackageRequest = {};
    if (sections && sections.length > 0) {
      body.include_sections = sections;
    }
    const response = await apiClient.post(`/buildings/${buildingId}/transfer-package`, body);
    return response.data;
  },
};
