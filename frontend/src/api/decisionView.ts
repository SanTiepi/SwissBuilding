import { apiClient } from '@/api/client';

export interface DecisionBlocker {
  id: string;
  category: string;
  title: string;
  description: string;
  source_type: string | null;
  source_id: string | null;
  link_hint: string | null;
}

export interface DecisionCondition {
  id: string;
  category: string;
  title: string;
  description: string;
  source_type: string | null;
  source_id: string | null;
  link_hint: string | null;
}

export interface DecisionClearItem {
  id: string;
  category: string;
  title: string;
  description: string;
}

export interface AudienceReadiness {
  audience: string;
  has_pack: boolean;
  latest_pack_version: number | null;
  latest_pack_status: string | null;
  latest_pack_generated_at: string | null;
  included_sections: string[];
  excluded_sections: string[];
  unknowns_count: number;
  contradictions_count: number;
  residual_risks_count: number;
  caveats: string[];
  trust_refs_count: number;
  proof_refs_count: number;
}

export interface ProofChainItem {
  label: string;
  entity_type: string;
  entity_id: string | null;
  version: number | null;
  content_hash: string | null;
  status: string | null;
  delivery_status: string | null;
  occurred_at: string | null;
  custody_chain_length: number;
}

export interface CustodyPosture {
  total_artifact_versions: number;
  current_versions: number;
  total_custody_events: number;
  latest_custody_event_at: string | null;
}

export interface ROISummary {
  time_saved_hours: number;
  rework_avoided: number;
  blocker_days_saved: number;
  pack_reuse_count: number;
  evidence_sources: string[];
}

export interface DecisionView {
  building_id: string;
  building_name: string;
  building_address: string | null;
  passport_grade: string;
  overall_trust: number;
  overall_completeness: number;
  readiness_status: string;
  last_updated: string | null;
  custody_posture: CustodyPosture;
  blockers: DecisionBlocker[];
  conditions: DecisionCondition[];
  clear_items: DecisionClearItem[];
  audience_readiness: AudienceReadiness[];
  proof_chain: ProofChainItem[];
  roi: ROISummary;
}

export const decisionViewApi = {
  get: async (buildingId: string): Promise<DecisionView> => {
    const response = await apiClient.get<DecisionView>(`/buildings/${buildingId}/decision-view`);
    return response.data;
  },
};
