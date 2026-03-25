import { apiClient } from '@/api/client';

// ---- Public Owner Mode ----

export interface PublicOwnerModeData {
  id: string;
  organization_id: string;
  mode_type: string;
  is_active: boolean;
  governance_level: string;
  requires_committee_review: boolean;
  requires_review_pack: boolean;
  default_review_audience: string[] | null;
  notes: string | null;
  activated_at: string | null;
  created_at: string;
  updated_at: string;
}

// ---- Review Packs ----

export interface ReviewPackData {
  id: string;
  building_id: string;
  generated_by_user_id: string | null;
  pack_version: number;
  status: string;
  sections: Record<string, unknown> | unknown[] | null;
  content_hash: string | null;
  review_deadline: string | null;
  circulated_to: Array<{ org_name?: string; role?: string; sent_at?: string }> | null;
  notes: string | null;
  generated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewPackCreatePayload {
  notes?: string | null;
  review_deadline?: string | null;
}

export interface CirculatePayload {
  recipients: Array<{ org_name: string; role: string; sent_at: string }>;
}

// ---- Committee Packs ----

export interface CommitteePackData {
  id: string;
  building_id: string;
  committee_name: string;
  committee_type: string;
  pack_version: number;
  status: string;
  sections: Record<string, unknown> | unknown[] | null;
  procurement_clauses: Array<{ clause: string; [key: string]: unknown }> | null;
  content_hash: string | null;
  decision_deadline: string | null;
  submitted_at: string | null;
  decided_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CommitteePackCreatePayload {
  committee_name: string;
  committee_type: string;
  decision_deadline?: string | null;
  procurement_clauses?: Array<{ clause: string; [key: string]: unknown }> | null;
}

// ---- Decision Traces ----

export interface DecisionTraceData {
  id: string;
  pack_type: string;
  pack_id: string;
  reviewer_name: string;
  reviewer_role: string | null;
  reviewer_org_id: string | null;
  decision: string;
  conditions: string | null;
  notes: string | null;
  evidence_refs: Array<Record<string, unknown>> | null;
  confidence_level: string | null;
  decided_at: string;
  created_at: string;
}

export interface DecisionTraceCreatePayload {
  reviewer_name: string;
  reviewer_role?: string | null;
  reviewer_org_id?: string | null;
  decision: string;
  conditions?: string | null;
  notes?: string | null;
  evidence_refs?: Array<Record<string, unknown>> | null;
  confidence_level?: string | null;
  decided_at: string;
}

// ---- Governance Signals ----

export interface GovernanceSignalData {
  id: string;
  organization_id: string;
  building_id: string | null;
  signal_type: string;
  severity: string;
  title: string;
  description: string | null;
  source_entity_type: string | null;
  source_entity_id: string | null;
  resolved: boolean;
  resolved_at: string | null;
  created_at: string;
}

// ---- API ----

export const publicSectorApi = {
  // Public Owner Mode
  getPublicOwnerMode: async (orgId: string): Promise<PublicOwnerModeData> => {
    const response = await apiClient.get<PublicOwnerModeData>(`/organizations/${orgId}/public-owner-mode`);
    return response.data;
  },

  // Review Packs
  listReviewPacks: async (buildingId: string): Promise<ReviewPackData[]> => {
    const response = await apiClient.get<ReviewPackData[]>(`/buildings/${buildingId}/review-packs`);
    return response.data;
  },

  generateReviewPack: async (buildingId: string, payload: ReviewPackCreatePayload): Promise<ReviewPackData> => {
    const response = await apiClient.post<ReviewPackData>(`/buildings/${buildingId}/review-packs`, payload);
    return response.data;
  },

  circulateReviewPack: async (packId: string, payload: CirculatePayload): Promise<ReviewPackData> => {
    const response = await apiClient.post<ReviewPackData>(`/review-packs/${packId}/circulate`, payload);
    return response.data;
  },

  // Committee Packs
  listCommitteePacks: async (buildingId: string): Promise<CommitteePackData[]> => {
    const response = await apiClient.get<CommitteePackData[]>(`/buildings/${buildingId}/committee-packs`);
    return response.data;
  },

  generateCommitteePack: async (
    buildingId: string,
    payload: CommitteePackCreatePayload,
  ): Promise<CommitteePackData> => {
    const response = await apiClient.post<CommitteePackData>(`/buildings/${buildingId}/committee-packs`, payload);
    return response.data;
  },

  // Decision Traces
  listDecisionTraces: async (packType: string, packId: string): Promise<DecisionTraceData[]> => {
    const response = await apiClient.get<DecisionTraceData[]>(`/decision-traces/${packType}/${packId}`);
    return response.data;
  },

  recordDecision: async (packId: string, payload: DecisionTraceCreatePayload): Promise<DecisionTraceData> => {
    const response = await apiClient.post<DecisionTraceData>(`/committee-packs/${packId}/decide`, payload);
    return response.data;
  },

  // Governance Signals
  listGovernanceSignals: async (orgId: string, buildingId?: string): Promise<GovernanceSignalData[]> => {
    const response = await apiClient.get<GovernanceSignalData[]>(`/organizations/${orgId}/governance-signals`, {
      params: buildingId ? { building_id: buildingId } : undefined,
    });
    return response.data;
  },

  resolveGovernanceSignal: async (signalId: string): Promise<GovernanceSignalData> => {
    const response = await apiClient.post<GovernanceSignalData>(`/governance-signals/${signalId}/resolve`);
    return response.data;
  },
};
