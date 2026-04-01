import { apiClient } from '@/api/client';
import type { ActionItem } from '@/types';

export interface ActionQueueItem {
  id: string;
  title: string;
  description: string | null;
  priority: string;
  status: string;
  source_type: string;
  action_type: string;
  deadline: string | null;
  linked_entity: { type: string; id: string } | null;
  suggested_resolution: string;
  estimated_effort: 'quick' | 'medium' | 'heavy';
  created_at: string | null;
  completed_at: string | null;
  snoozed_until: string | null;
  metadata_json: Record<string, unknown> | null;
}

export interface ActionQueueSummary {
  overdue: number;
  this_week: number;
  this_month: number;
  backlog: number;
  snoozed: number;
  total: number;
}

export interface ActionQueueResponse {
  building_id: string;
  summary: ActionQueueSummary;
  overdue: ActionQueueItem[];
  this_week: ActionQueueItem[];
  this_month: ActionQueueItem[];
  backlog: ActionQueueItem[];
  snoozed: ActionQueueItem[];
}

export interface WeeklySummaryResponse {
  building_id: string;
  period_start: string;
  period_end: string;
  completed_count: number;
  created_count: number;
  completed: ActionQueueItem[];
  created: ActionQueueItem[];
  readiness_trend: 'improved' | 'stable' | 'degraded';
  open_count: number;
  next_priorities: ActionQueueItem[];
}

export const actionQueueApi = {
  getQueue: async (buildingId: string, status = 'open'): Promise<ActionQueueResponse> => {
    const response = await apiClient.get<ActionQueueResponse>(`/buildings/${buildingId}/action-queue`, {
      params: { status },
    });
    return response.data;
  },

  complete: async (actionId: string, resolutionNote?: string): Promise<ActionItem> => {
    const response = await apiClient.post<ActionItem>(`/actions/${actionId}/complete`, {
      resolution_note: resolutionNote || null,
    });
    return response.data;
  },

  snooze: async (actionId: string, snoozeUntil: string): Promise<ActionItem> => {
    const response = await apiClient.post<ActionItem>(`/actions/${actionId}/snooze`, {
      snooze_until: snoozeUntil,
    });
    return response.data;
  },

  getWeeklySummary: async (buildingId: string): Promise<WeeklySummaryResponse> => {
    const response = await apiClient.get<WeeklySummaryResponse>(`/buildings/${buildingId}/weekly-summary`);
    return response.data;
  },
};
