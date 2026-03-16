import { apiClient } from '@/api/client';
import type { PaginatedResponse, Jurisdiction, RegulatoryPack } from '@/types';

export interface PackFilters {
  jurisdiction_id?: string;
  pollutant_type?: string;
  is_active?: boolean;
}

export interface PackWithJurisdiction extends RegulatoryPack {
  jurisdiction_name?: string;
  jurisdiction_code?: string;
}

export interface PackDiff {
  field: string;
  pack_a: string | number | boolean | null;
  pack_b: string | number | boolean | null;
  changed: boolean;
}

const COMPARABLE_FIELDS: (keyof RegulatoryPack)[] = [
  'pollutant_type',
  'version',
  'is_active',
  'threshold_value',
  'threshold_unit',
  'threshold_action',
  'risk_year_start',
  'risk_year_end',
  'base_probability',
  'legal_reference',
  'notification_required',
  'notification_authority',
  'notification_delay_days',
];

export const regulatoryPacksApi = {
  /** List all packs across jurisdictions by fetching jurisdiction tree and flattening */
  listAll: async (filters?: PackFilters): Promise<PackWithJurisdiction[]> => {
    const resp = await apiClient.get<PaginatedResponse<Jurisdiction>>('/jurisdictions', {
      params: { size: 200 },
    });
    const jurisdictions = resp.data.items;

    // For each jurisdiction, fetch packs
    const allPacks: PackWithJurisdiction[] = [];
    for (const j of jurisdictions) {
      const packsResp = await apiClient.get<Jurisdiction>(`/jurisdictions/${j.id}`);
      const packs = packsResp.data.regulatory_packs ?? [];
      for (const p of packs) {
        if (filters?.pollutant_type && p.pollutant_type !== filters.pollutant_type) continue;
        if (filters?.jurisdiction_id && p.jurisdiction_id !== filters.jurisdiction_id) continue;
        if (filters?.is_active !== undefined && p.is_active !== filters.is_active) continue;
        allPacks.push({
          ...p,
          jurisdiction_name: j.name,
          jurisdiction_code: j.code,
        });
      }
    }
    return allPacks;
  },

  /** Get a single pack detail via its jurisdiction */
  get: async (jurisdictionId: string, packId: string): Promise<RegulatoryPack | undefined> => {
    const resp = await apiClient.get<Jurisdiction>(`/jurisdictions/${jurisdictionId}`);
    return resp.data.regulatory_packs?.find((p) => p.id === packId);
  },

  /** Client-side diff of two packs */
  comparePacks: (a: RegulatoryPack, b: RegulatoryPack): PackDiff[] => {
    return COMPARABLE_FIELDS.map((field) => {
      const va = a[field] ?? null;
      const vb = b[field] ?? null;
      return {
        field,
        pack_a: va as string | number | boolean | null,
        pack_b: vb as string | number | boolean | null,
        changed: JSON.stringify(va) !== JSON.stringify(vb),
      };
    });
  },
};
