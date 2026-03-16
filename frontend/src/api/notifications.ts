import { apiClient } from '@/api/client';
import type { Notification, PaginatedResponse } from '@/types';

export interface NotificationFilters {
  status?: string;
  type?: string;
  page?: number;
  size?: number;
}

export const notificationsApi = {
  list: async (filters?: NotificationFilters): Promise<PaginatedResponse<Notification>> => {
    const response = await apiClient.get<PaginatedResponse<Notification>>('/notifications', {
      params: filters,
    });
    return response.data;
  },

  getUnreadCount: async (): Promise<{ count: number }> => {
    const response = await apiClient.get<{ count: number }>('/notifications/unread-count');
    return response.data;
  },

  markRead: async (id: string): Promise<void> => {
    await apiClient.put(`/notifications/${id}/read`);
  },

  markUnread: async (id: string): Promise<void> => {
    await apiClient.put(`/notifications/${id}/unread`);
  },

  markAllRead: async (): Promise<void> => {
    await apiClient.put('/notifications/read-all');
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/notifications/${id}`);
  },

  deleteBatch: async (ids: string[]): Promise<void> => {
    await Promise.all(ids.map((id) => apiClient.delete(`/notifications/${id}`)));
  },
};
