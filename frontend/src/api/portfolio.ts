import { apiClient } from '@/api/client';
import type { MapBuildingsResponse, PortfolioMetrics, PortfolioSummary, PortfolioHealthScore } from '@/types';

export const portfolioApi = {
  getMetrics: async (): Promise<PortfolioMetrics> => {
    const response = await apiClient.get<PortfolioMetrics>('/portfolio/metrics');
    return response.data;
  },

  getMapBuildings: async (params?: { risk_level?: string; canton?: string }): Promise<MapBuildingsResponse> => {
    const response = await apiClient.get<MapBuildingsResponse>('/portfolio/map-buildings', {
      params,
    });
    return response.data;
  },

  getSummary: async (): Promise<PortfolioSummary> => {
    const response = await apiClient.get<PortfolioSummary>('/portfolio/summary');
    return response.data;
  },

  getHealthScore: async (): Promise<PortfolioHealthScore> => {
    const response = await apiClient.get<PortfolioHealthScore>('/portfolio/health-score');
    return response.data;
  },
};
