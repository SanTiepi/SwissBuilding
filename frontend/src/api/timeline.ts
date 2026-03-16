import { apiClient } from '@/api/client';
import type { TimelineEntry, PaginatedResponse, EnrichedTimeline } from '@/types';

export const timelineApi = {
  list: async (
    buildingId: string,
    params?: { page?: number; size?: number; event_type?: string },
  ): Promise<PaginatedResponse<TimelineEntry>> => {
    const response = await apiClient.get<PaginatedResponse<TimelineEntry>>(`/buildings/${buildingId}/timeline`, {
      params,
    });
    return response.data;
  },

  enriched: async (buildingId: string): Promise<EnrichedTimeline> => {
    const response = await apiClient.get<EnrichedTimeline>(`/buildings/${buildingId}/timeline/enriched`);
    return response.data;
  },
};
