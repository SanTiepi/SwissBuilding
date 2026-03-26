import { apiClient } from '@/api/client';
import axios from 'axios';

export interface IntakeRequest {
  id: string;
  requester_name: string;
  requester_email: string;
  requester_phone: string | null;
  requester_company: string | null;
  building_address: string;
  building_city: string | null;
  building_postal_code: string | null;
  building_egid: string | null;
  request_type: string;
  urgency: string;
  description: string | null;
  status: 'new' | 'qualified' | 'converted' | 'rejected';
  source: string;
  created_at: string;
  updated_at: string;
}

export interface IntakeRequestCreate {
  requester_name: string;
  requester_email: string;
  requester_phone?: string;
  requester_company?: string;
  building_address: string;
  building_city?: string;
  building_postal_code?: string;
  building_egid?: string;
  request_type: string;
  urgency: string;
  description?: string;
  source?: string;
}

export interface IntakeListResponse {
  items: IntakeRequest[];
  total: number;
}

// Public endpoint — no auth token needed
const publicClient = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

export const intakeApi = {
  /** Public: submit an intake request (no auth) */
  submit: async (data: IntakeRequestCreate): Promise<IntakeRequest> => {
    const response = await publicClient.post<IntakeRequest>('/public/intake', data);
    return response.data;
  },

  /** Admin: list intake requests */
  list: async (params?: { status?: string; page?: number; size?: number }): Promise<IntakeListResponse> => {
    const response = await apiClient.get<IntakeListResponse>('/intake-requests', { params });
    return response.data;
  },

  /** Admin: qualify intake */
  qualify: async (id: string, notes?: string): Promise<IntakeRequest> => {
    const response = await apiClient.post<IntakeRequest>(`/intake-requests/${id}/qualify`, { notes });
    return response.data;
  },

  /** Admin: reject intake */
  reject: async (id: string, reason?: string): Promise<IntakeRequest> => {
    const response = await apiClient.post<IntakeRequest>(`/intake-requests/${id}/reject`, { reason });
    return response.data;
  },

  /** Admin: convert intake to contact + building */
  convert: async (id: string): Promise<IntakeRequest> => {
    const response = await apiClient.post<IntakeRequest>(`/intake-requests/${id}/convert`, {});
    return response.data;
  },
};
