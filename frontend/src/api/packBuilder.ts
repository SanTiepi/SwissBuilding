import { apiClient } from '@/api/client';

export interface PackTypeInfo {
  pack_type: string;
  name: string;
  section_count: number;
  includes_trust: boolean;
  includes_provenance: boolean;
  readiness: 'ready' | 'partial' | 'not_ready';
  readiness_score: number;
}

export interface PackSection {
  section_name: string;
  section_type: string;
  items: Record<string, unknown>[];
  completeness: number;
  notes: string | null;
}

export interface PackConformanceResult {
  profile: string;
  result: 'pass' | 'fail' | 'partial';
  score: number;
  failed_checks: Array<{ check: string; status: string; reason?: string }>;
}

export interface PackResult {
  pack_id: string;
  building_id: string;
  pack_type: string;
  pack_name: string;
  sections: PackSection[];
  total_sections: number;
  overall_completeness: number;
  includes_trust: boolean;
  includes_provenance: boolean;
  generated_at: string;
  warnings: string[];
  caveats_count: number;
  pack_version: string;
  sha256_hash: string | null;
  financials_redacted?: boolean;
  conformance?: PackConformanceResult | null;
}

export interface AvailablePacksResponse {
  building_id: string;
  packs: PackTypeInfo[];
}

export const packBuilderApi = {
  listAvailable: async (buildingId: string): Promise<AvailablePacksResponse> => {
    const response = await apiClient.get<AvailablePacksResponse>(`/buildings/${buildingId}/packs`);
    return response.data;
  },
  generate: async (
    buildingId: string,
    packType: string,
    options?: { redact_financials?: boolean },
  ): Promise<PackResult> => {
    const response = await apiClient.post<PackResult>(`/buildings/${buildingId}/packs/${packType}`, {
      ...(options?.redact_financials !== undefined && { redact_financials: options.redact_financials }),
    });
    return response.data;
  },
};
