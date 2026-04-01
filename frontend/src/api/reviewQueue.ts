import { apiClient } from '@/api/client';

export interface ReviewTask {
  id: string;
  building_id: string;
  organization_id: string;
  task_type: string;
  target_type: string;
  target_id: string;
  title: string;
  description: string | null;
  case_id: string | null;
  priority: string;
  assigned_to_id: string | null;
  status: string;
  completed_at: string | null;
  completed_by_id: string | null;
  resolution: string | null;
  resolution_note: string | null;
  escalation_reason: string | null;
  escalated_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ReviewQueueStats {
  total_pending: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  by_type: Record<string, number>;
  overdue_7d: number;
}

export const reviewQueueApi = {
  getQueue: async (params?: {
    status?: string;
    priority?: string;
    task_type?: string;
    building_id?: string;
    limit?: number;
  }): Promise<ReviewTask[]> => {
    const response = await apiClient.get<ReviewTask[]>('/review-queue', { params });
    return response.data;
  },

  getStats: async (): Promise<ReviewQueueStats> => {
    const response = await apiClient.get<ReviewQueueStats>('/review-queue/stats');
    return response.data;
  },

  assignTask: async (taskId: string, assignedToId: string): Promise<ReviewTask> => {
    const response = await apiClient.post<ReviewTask>(`/review-tasks/${taskId}/assign`, {
      assigned_to_id: assignedToId,
    });
    return response.data;
  },

  completeTask: async (taskId: string, resolution: string, resolutionNote?: string): Promise<ReviewTask> => {
    const response = await apiClient.post<ReviewTask>(`/review-tasks/${taskId}/complete`, {
      resolution,
      resolution_note: resolutionNote,
    });
    return response.data;
  },

  escalateTask: async (taskId: string, reason: string): Promise<ReviewTask> => {
    const response = await apiClient.post<ReviewTask>(`/review-tasks/${taskId}/escalate`, {
      escalation_reason: reason,
    });
    return response.data;
  },
};
