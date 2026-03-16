import axios from 'axios';
import { apiClient } from '@/api/client';
import type { PassportSummary } from '@/api/passport';

// Public client (no auth interceptors)
const publicClient = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

export interface SharedLinkValidation {
  is_valid: boolean;
  resource_type: string | null;
  resource_id: string | null;
  allowed_sections: string[] | null;
  audience_type: string | null;
}

export interface SharedPassportResponse {
  building_address: string;
  building_city: string;
  building_canton: string;
  building_postal_code: string;
  passport: PassportSummary;
  shared_by_org: string | null;
  expires_at: string;
  audience_type: string;
}

export interface CreateSharedLinkRequest {
  resource_type: string;
  resource_id: string;
  audience_type: string;
  audience_email?: string;
  expires_in_days?: number;
  max_views?: number;
  allowed_sections?: string[];
}

export interface SharedLinkRead {
  id: string;
  token: string;
  resource_type: string;
  resource_id: string;
  created_by: string;
  organization_id: string | null;
  audience_type: string;
  audience_email: string | null;
  expires_at: string;
  max_views: number | null;
  view_count: number;
  allowed_sections: string[] | null;
  is_active: boolean;
  created_at: string;
  last_accessed_at: string | null;
}

export const sharedLinksApi = {
  /** Public: validate a shared link token */
  validate: async (token: string): Promise<SharedLinkValidation> => {
    const response = await publicClient.get(`/shared/${token}`);
    return response.data;
  },

  /** Public: get passport data via shared link */
  passport: async (token: string): Promise<SharedPassportResponse> => {
    const response = await publicClient.get(`/shared/${token}/passport`);
    return response.data;
  },

  /** Authenticated: create a shared link */
  create: async (data: CreateSharedLinkRequest): Promise<SharedLinkRead> => {
    const response = await apiClient.post('/shared-links', data);
    return response.data;
  },

  /** Authenticated: list shared links */
  list: async (params?: {
    resource_type?: string;
    resource_id?: string;
  }): Promise<{
    items: SharedLinkRead[];
    count: number;
  }> => {
    const response = await apiClient.get('/shared-links', { params });
    return response.data;
  },

  /** Authenticated: revoke a shared link */
  revoke: async (linkId: string): Promise<SharedLinkRead> => {
    const response = await apiClient.delete(`/shared-links/${linkId}`);
    return response.data;
  },
};
