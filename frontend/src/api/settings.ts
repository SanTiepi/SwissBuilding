import { apiClient } from '@/api/client';
import type { NotificationPreference, FullNotificationPreferences, User } from '@/types';

export const settingsApi = {
  updateProfile: async (data: { first_name: string }): Promise<User> => {
    const response = await apiClient.put<User>('/auth/me', data);
    return response.data;
  },

  changePassword: async (data: { current_password: string; new_password: string }): Promise<void> => {
    await apiClient.put('/auth/me/password', data);
  },

  getNotificationPreferences: async (): Promise<NotificationPreference> => {
    const response = await apiClient.get<NotificationPreference>('/notifications/preferences');
    return response.data;
  },

  updateNotificationPreferences: async (prefs: NotificationPreference): Promise<NotificationPreference> => {
    const response = await apiClient.put<NotificationPreference>('/notifications/preferences', prefs);
    return response.data;
  },

  getFullNotificationPreferences: async (): Promise<FullNotificationPreferences> => {
    const response = await apiClient.get<FullNotificationPreferences>('/notifications/preferences/full');
    return response.data;
  },

  updateFullNotificationPreferences: async (
    data: Partial<FullNotificationPreferences>,
  ): Promise<FullNotificationPreferences> => {
    const response = await apiClient.put<FullNotificationPreferences>('/notifications/preferences/full', data);
    return response.data;
  },

  getDigestPreview: async (period?: string): Promise<Record<string, unknown>> => {
    const params = period ? { period } : {};
    const response = await apiClient.get<Record<string, unknown>>('/notifications/digest/preview', {
      params,
    });
    return response.data;
  },
};
