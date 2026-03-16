import { apiClient } from '@/api/client';
import type { AuditLog, PaginatedResponse } from '@/types';

export interface AuditLogFilters {
  page?: number;
  size?: number;
  user_id?: string;
  entity_type?: string;
  action?: string;
  date_from?: string;
  date_to?: string;
}

export const auditLogsApi = {
  list: async (params?: AuditLogFilters): Promise<PaginatedResponse<AuditLog>> => {
    const response = await apiClient.get<PaginatedResponse<AuditLog>>('/audit-logs', { params });
    return response.data;
  },
};
