import { apiClient } from '@/api/client';
import axios from 'axios';

export interface IntakeRequest {
  id: string;
  name: string;
  email: string;
  phone: string | null;
  company: string | null;
  building_address: string;
  city: string | null;
  postal_code: string | null;
  egid: string | null;
  request_type: string;
  urgency: string;
  description: string | null;
  status: 'new' | 'qualified' | 'converted' | 'rejected';
  created_at: string;
  updated_at: string;
}

export interface IntakeRequestCreate {
  name: string;
  email: string;
  phone?: string;
  company?: string;
  building_address: string;
  city?: string;
  postal_code?: string;
  egid?: string;
  request_type: string;
  urgency: string;
  description?: string;
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
    const response = await apiClient.get<IntakeListResponse>('/admin/intake', { params });
    return response.data;
  },

  /** Admin: update intake status */
  updateStatus: async (id: string, status: string): Promise<IntakeRequest> => {
    const response = await apiClient.patch<IntakeRequest>(`/admin/intake/${id}`, { status });
    return response.data;
  },

  /** Admin: convert intake to contact + building */
  convert: async (id: string): Promise<IntakeRequest> => {
    const response = await apiClient.post<IntakeRequest>(`/admin/intake/${id}/convert`);
    return response.data;
  },
};
