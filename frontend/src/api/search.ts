import { apiClient } from '@/api/client';
import type { SearchResponse } from '@/types';

export const searchApi = {
  search: async (query: string, type?: string, limit?: number): Promise<SearchResponse> => {
    const response = await apiClient.get<SearchResponse>('/search', {
      params: { q: query, type, limit },
    });
    return response.data;
  },
};
