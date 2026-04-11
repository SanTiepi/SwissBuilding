import { apiClient } from '@/api/client';

export interface IsochroneContour {
  minutes: number;
  profile: string;
  geometry: GeoJSON.Polygon;
}

export interface IsochroneResponse {
  building_id: string;
  latitude: number;
  longitude: number;
  profile: string;
  contours: IsochroneContour[];
  mobility_score: number | null;
  cached: boolean;
  error: string | null;
}

export const isochroneApi = {
  get: async (buildingId: string, profile = 'walking', rangeList = '5,10,15'): Promise<IsochroneResponse> => {
    const response = await apiClient.get<IsochroneResponse>(`/buildings/${buildingId}/isochrone`, {
      params: { profile, range_list: rangeList },
    });
    return response.data;
  },
};
