import { apiClient } from '@/api/client';
import type {
  FieldObservation,
  FieldObservationCreate,
  FieldObservationSummary,
  PaginatedResponse,
  PatternInsight,
} from '@/types';

export const fieldObservationsApi = {
  list: async (
    buildingId: string,
    params?: {
      page?: number;
      size?: number;
      observation_type?: string;
      severity?: string;
      status?: string;
      zone_id?: string;
    },
  ): Promise<PaginatedResponse<FieldObservation>> => {
    const response = await apiClient.get<PaginatedResponse<FieldObservation>>(
      `/buildings/${buildingId}/field-observations`,
      { params },
    );
    return response.data;
  },

  create: async (buildingId: string, data: FieldObservationCreate): Promise<FieldObservation> => {
    const response = await apiClient.post<FieldObservation>(`/buildings/${buildingId}/field-observations`, data);
    return response.data;
  },

  createGeneral: async (data: FieldObservationCreate): Promise<FieldObservation> => {
    const response = await apiClient.post<FieldObservation>('/observations', data);
    return response.data;
  },

  get: async (observationId: string): Promise<FieldObservation> => {
    const response = await apiClient.get<FieldObservation>(`/field-observations/${observationId}`);
    return response.data;
  },

  update: async (observationId: string, data: Partial<FieldObservation>): Promise<FieldObservation> => {
    const response = await apiClient.put<FieldObservation>(`/field-observations/${observationId}`, data);
    return response.data;
  },

  verify: async (observationId: string, data: { verified: boolean }): Promise<FieldObservation> => {
    const response = await apiClient.post<FieldObservation>(`/field-observations/${observationId}/verify`, data);
    return response.data;
  },

  summary: async (buildingId: string): Promise<FieldObservationSummary> => {
    const response = await apiClient.get<FieldObservationSummary>(
      `/buildings/${buildingId}/field-observations/summary`,
    );
    return response.data;
  },

  search: async (params: {
    page?: number;
    size?: number;
    tags?: string;
    canton?: string;
    construction_year_min?: number;
    construction_year_max?: number;
    pollutant?: string;
    material?: string;
    observation_type?: string;
  }): Promise<PaginatedResponse<FieldObservation>> => {
    const response = await apiClient.get<PaginatedResponse<FieldObservation>>('/observations/search', { params });
    return response.data;
  },

  patterns: async (buildingId?: string): Promise<PatternInsight[]> => {
    const params = buildingId ? { building_id: buildingId } : {};
    const response = await apiClient.get<PatternInsight[]>('/observations/patterns', { params });
    return response.data;
  },

  upvote: async (observationId: string): Promise<FieldObservation> => {
    const response = await apiClient.post<FieldObservation>(`/observations/${observationId}/upvote`);
    return response.data;
  },

  verifyAdmin: async (observationId: string): Promise<FieldObservation> => {
    const response = await apiClient.post<FieldObservation>(`/observations/${observationId}/verify`);
    return response.data;
  },
};
