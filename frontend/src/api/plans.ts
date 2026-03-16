import { apiClient } from '@/api/client';
import type { TechnicalPlan, PlanAnnotation, PlanAnnotationCreate, PlanAnnotationType } from '@/types';

export const plansApi = {
  list: async (buildingId: string, params?: { plan_type?: string }): Promise<TechnicalPlan[]> => {
    const response = await apiClient.get<TechnicalPlan[]>(`/buildings/${buildingId}/plans`, { params });
    return response.data;
  },
  get: async (buildingId: string, planId: string): Promise<TechnicalPlan> => {
    const response = await apiClient.get<TechnicalPlan>(`/buildings/${buildingId}/plans/${planId}`);
    return response.data;
  },
  upload: async (buildingId: string, formData: FormData): Promise<TechnicalPlan> => {
    const response = await apiClient.post<TechnicalPlan>(`/buildings/${buildingId}/plans`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  delete: async (buildingId: string, planId: string): Promise<void> => {
    await apiClient.delete(`/buildings/${buildingId}/plans/${planId}`);
  },

  // Annotations
  listAnnotations: async (
    buildingId: string,
    planId: string,
    annotationType?: PlanAnnotationType,
  ): Promise<PlanAnnotation[]> => {
    const params = annotationType ? { annotation_type: annotationType } : undefined;
    const response = await apiClient.get<PlanAnnotation[]>(`/buildings/${buildingId}/plans/${planId}/annotations`, {
      params,
    });
    return response.data;
  },
  createAnnotation: async (buildingId: string, planId: string, data: PlanAnnotationCreate): Promise<PlanAnnotation> => {
    const response = await apiClient.post<PlanAnnotation>(`/buildings/${buildingId}/plans/${planId}/annotations`, data);
    return response.data;
  },
  updateAnnotation: async (
    buildingId: string,
    planId: string,
    annotationId: string,
    data: Partial<PlanAnnotationCreate>,
  ): Promise<PlanAnnotation> => {
    const response = await apiClient.put<PlanAnnotation>(
      `/buildings/${buildingId}/plans/${planId}/annotations/${annotationId}`,
      data,
    );
    return response.data;
  },
  deleteAnnotation: async (buildingId: string, planId: string, annotationId: string): Promise<void> => {
    await apiClient.delete(`/buildings/${buildingId}/plans/${planId}/annotations/${annotationId}`);
  },
};
