import { apiClient } from '@/api/client';

export type FreshnessState = 'current' | 'aging' | 'stale' | 'unknown';
export type WatchTier = 'daily' | 'weekly' | 'monthly' | 'quarterly';

export interface RuleSource {
  id: string;
  source_code: string;
  source_name: string;
  source_url: string | null;
  watch_tier: WatchTier;
  last_checked_at: string | null;
  last_changed_at: string | null;
  freshness_state: FreshnessState;
  change_types_detected: string[] | null;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface RuleChangeEvent {
  id: string;
  source_id: string;
  event_type: string;
  title: string;
  description: string | null;
  impact_summary: string | null;
  detected_at: string;
  reviewed: boolean;
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  affects_buildings: boolean;
  created_at: string;
}

export interface CommunalAdapter {
  id: string;
  commune_code: string;
  commune_name: string;
  canton_code: string;
  adapter_status: string;
  supports_procedure_projection: boolean;
  supports_rule_projection: boolean;
  fallback_mode: string;
  source_ids: string[] | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CommunalOverride {
  id: string;
  commune_code: string;
  canton_code: string;
  override_type: string;
  rule_reference: string | null;
  impact_summary: string;
  review_required: boolean;
  confidence_level: string;
  source_id: string | null;
  effective_from: string | null;
  effective_to: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BuildingCommuneContext {
  building_id: string;
  city: string;
  canton: string;
  adapter: CommunalAdapter | null;
  overrides: CommunalOverride[];
}

export const swissRulesWatchApi = {
  async listSources(tier?: string): Promise<RuleSource[]> {
    const params = tier ? { tier } : {};
    const res = await apiClient.get<RuleSource[]>('/swiss-rules/sources', { params });
    return res.data;
  },

  async getUnreviewedChanges(): Promise<RuleChangeEvent[]> {
    const res = await apiClient.get<RuleChangeEvent[]>('/swiss-rules/changes/unreviewed');
    return res.data;
  },

  async getBuildingCommuneContext(buildingId: string): Promise<BuildingCommuneContext> {
    const res = await apiClient.get<BuildingCommuneContext>(`/buildings/${buildingId}/commune-context`);
    return res.data;
  },
};
