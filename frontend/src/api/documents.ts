import { apiClient } from '@/api/client';
import type { BuildingEvent, Document } from '@/types';

export const documentsApi = {
  listByBuilding: async (buildingId: string): Promise<Document[]> => {
    const response = await apiClient.get<Document[]>(`/buildings/${buildingId}/documents`);
    return response.data;
  },

  upload: async (
    buildingId: string,
    file: File,
    documentType: string = 'other',
    description?: string,
  ): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    if (description) {
      formData.append('description', description);
    }
    const response = await apiClient.post<Document>(`/buildings/${buildingId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  getDownloadUrl: async (id: string): Promise<string> => {
    const response = await apiClient.get<{ url: string }>(`/documents/${id}/download`);
    return response.data.url;
  },

  listEvents: async (buildingId: string): Promise<BuildingEvent[]> => {
    const response = await apiClient.get<BuildingEvent[]>(`/buildings/${buildingId}/events`);
    return response.data;
  },

  createEvent: async (buildingId: string, data: Partial<BuildingEvent>): Promise<BuildingEvent> => {
    const response = await apiClient.post<BuildingEvent>(`/buildings/${buildingId}/events`, data);
    return response.data;
  },
};
