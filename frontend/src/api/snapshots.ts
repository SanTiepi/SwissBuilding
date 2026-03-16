import { apiClient } from '@/api/client';

export interface BuildingSnapshot {
  id: string;
  building_id: string;
  snapshot_type: string;
  trigger_event: string | null;
  passport_state_json: Record<string, unknown> | null;
  trust_state_json: Record<string, unknown> | null;
  readiness_state_json: Record<string, unknown> | null;
  evidence_counts_json: Record<string, unknown> | null;
  passport_grade: string | null;
  overall_trust: number | null;
  completeness_score: number | null;
  captured_at: string;
  captured_by: string | null;
  notes: string | null;
}

export interface SnapshotComparisonSide {
  id: string;
  captured_at: string | null;
  passport_grade: string | null;
  overall_trust: number;
  completeness_score: number;
}

export interface SnapshotComparison {
  building_id: string;
  snapshot_a: SnapshotComparisonSide;
  snapshot_b: SnapshotComparisonSide;
  changes: {
    trust_delta: number;
    completeness_delta: number;
    grade_change: string | null;
    readiness_changes: Array<{ type: string; from: string | null; to: string | null }>;
    new_contradictions: number;
    resolved_contradictions: number;
  };
}

export interface SnapshotCreatePayload {
  snapshot_type?: string;
  trigger_event?: string | null;
  notes?: string | null;
}

export const snapshotsApi = {
  list: async (buildingId: string): Promise<{ items: BuildingSnapshot[]; total: number }> => {
    const response = await apiClient.get(`/buildings/${buildingId}/snapshots`);
    return response.data;
  },

  get: async (buildingId: string, snapshotId: string): Promise<BuildingSnapshot> => {
    const response = await apiClient.get(`/buildings/${buildingId}/snapshots/${snapshotId}`);
    return response.data;
  },

  capture: async (buildingId: string, data: SnapshotCreatePayload): Promise<BuildingSnapshot> => {
    const response = await apiClient.post(`/buildings/${buildingId}/snapshots`, data);
    return response.data;
  },

  compare: async (buildingId: string, snapshotAId: string, snapshotBId: string): Promise<SnapshotComparison> => {
    const response = await apiClient.get(`/buildings/${buildingId}/snapshots/compare`, {
      params: { a: snapshotAId, b: snapshotBId },
    });
    return response.data;
  },
};
