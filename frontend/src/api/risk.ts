import { apiClient } from '@/api/client';
import type { BuildingRiskScore, MapBuildingsResponse, RenovationSimulation } from '@/types';

export const riskApi = {
  simulate: async (data: { building_id: string; renovation_type: string }): Promise<RenovationSimulation> => {
    const response = await apiClient.post<RenovationSimulation>('/risk-analysis/simulate', data);
    return response.data;
  },

  getBuildingRisk: async (buildingId: string): Promise<BuildingRiskScore> => {
    const response = await apiClient.get<BuildingRiskScore>(`/risk-analysis/building/${buildingId}`);
    return response.data;
  },

  getMapBuildings: async (params?: {
    bbox?: string;
    pollutant?: string;
    risk_level?: string;
  }): Promise<MapBuildingsResponse> => {
    const response = await apiClient.get<MapBuildingsResponse>('/pollutant-map/buildings', {
      params,
    });
    return response.data;
  },

  getHeatmap: async (params?: { pollutant?: string; canton?: string }): Promise<{ data: any[] }> => {
    const response = await apiClient.get<{ data: any[] }>('/pollutant-map/heatmap', { params });
    return response.data;
  },

  getClusters: async (params?: { bbox?: string; zoom?: number }): Promise<{ data: any[] }> => {
    const response = await apiClient.get<{ data: any[] }>('/pollutant-map/clusters', { params });
    return response.data;
  },
};
