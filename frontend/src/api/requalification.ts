import { apiClient } from '@/api/client';

export interface RequalificationEntry {
  timestamp: string;
  entry_type: 'signal' | 'snapshot' | 'grade_change' | 'intervention';
  title: string;
  description: string | null;
  severity: string | null;
  signal_type: string | null;
  grade_before: string | null;
  grade_after: string | null;
  metadata: Record<string, unknown> | null;
}

export interface RequalificationTimeline {
  building_id: string;
  entries: RequalificationEntry[];
  current_grade: string | null;
  grade_history: Record<string, unknown>[];
}

export interface RequalificationSummary {
  total_entries: number;
  grade_changes: number;
  active_signals: number;
  current_grade: string | null;
}

export const requalificationApi = {
  getTimeline: async (buildingId: string): Promise<RequalificationTimeline> => {
    const response = await apiClient.get<RequalificationTimeline>(`/buildings/${buildingId}/requalification/timeline`);
    return response.data;
  },

  getSummary: async (buildingId: string): Promise<RequalificationSummary> => {
    const response = await apiClient.get<RequalificationSummary>(`/buildings/${buildingId}/requalification/summary`);
    return response.data;
  },
};
