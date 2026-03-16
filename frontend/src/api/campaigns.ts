import { apiClient } from '@/api/client';
import type {
  ActionItem,
  Campaign,
  CampaignRecommendation,
  CampaignTracking,
  CampaignTrackingProgress,
  PaginatedResponse,
} from '@/types';

export interface CampaignImpact {
  buildings_affected: number;
  actions_total: number;
  actions_completed: number;
  actions_in_progress: number;
  completion_rate: number;
  velocity: number;
  budget_utilization: number;
  estimated_completion_date: string | null;
  days_remaining: number | null;
  is_at_risk: boolean;
}

export const campaignsApi = {
  list: async (params?: {
    status?: string;
    campaign_type?: string;
    organization_id?: string;
    page?: number;
    size?: number;
  }): Promise<PaginatedResponse<Campaign>> => {
    const response = await apiClient.get<PaginatedResponse<Campaign>>('/campaigns', { params });
    return response.data;
  },
  get: async (id: string): Promise<Campaign> => {
    const response = await apiClient.get<Campaign>(`/campaigns/${id}`);
    return response.data;
  },
  create: async (data: Partial<Campaign>): Promise<Campaign> => {
    const response = await apiClient.post<Campaign>('/campaigns', data);
    return response.data;
  },
  update: async (id: string, data: Partial<Campaign>): Promise<Campaign> => {
    const response = await apiClient.put<Campaign>(`/campaigns/${id}`, data);
    return response.data;
  },
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/campaigns/${id}`);
  },
  listActions: async (id: string): Promise<ActionItem[]> => {
    const response = await apiClient.get<ActionItem[]>(`/campaigns/${id}/actions`);
    return response.data;
  },
  linkActions: async (id: string, actionIds: string[]): Promise<void> => {
    await apiClient.post(`/campaigns/${id}/actions`, { action_item_ids: actionIds });
  },
  getProgress: async (id: string): Promise<{ target_count: number; completed_count: number; progress_pct: number }> => {
    const response = await apiClient.get(`/campaigns/${id}/progress`);
    return response.data;
  },
  getImpact: async (id: string): Promise<CampaignImpact> => {
    const response = await apiClient.get<CampaignImpact>(`/campaigns/${id}/impact`);
    return response.data;
  },
  getRecommendations: async (limit?: number): Promise<CampaignRecommendation[]> => {
    const response = await apiClient.get<CampaignRecommendation[]>('/campaigns/recommendations', {
      params: { limit: limit ?? 5 },
    });
    return response.data;
  },
  getTracking: async (campaignId: string): Promise<CampaignTracking[]> => {
    const response = await apiClient.get<CampaignTracking[]>(`/campaigns/${campaignId}/tracking`);
    return response.data;
  },
  updateBuildingStatus: async (
    campaignId: string,
    buildingId: string,
    data: { status: string; blocker_reason?: string; notes?: string; progress_pct?: number },
  ): Promise<CampaignTracking> => {
    const response = await apiClient.put<CampaignTracking>(`/campaigns/${campaignId}/tracking/${buildingId}`, data);
    return response.data;
  },
  getTrackingProgress: async (campaignId: string): Promise<CampaignTrackingProgress> => {
    const response = await apiClient.get<CampaignTrackingProgress>(`/campaigns/${campaignId}/tracking/progress`);
    return response.data;
  },
  getBlockedBuildings: async (campaignId: string): Promise<CampaignTracking[]> => {
    const response = await apiClient.get<CampaignTracking[]>(`/campaigns/${campaignId}/tracking/blocked`);
    return response.data;
  },
};
