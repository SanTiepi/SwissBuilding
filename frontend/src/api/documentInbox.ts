import { apiClient } from '@/api/client';

export interface DocumentInboxItem {
  id: string;
  building_id: string | null;
  filename: string;
  source: string;
  status: 'pending' | 'linked' | 'classified' | 'rejected';
  document_type: string | null;
  uploaded_at: string;
  processed_at: string | null;
}

export interface DocumentInboxSummary {
  total: number;
  pending: number;
  linked: number;
  classified: number;
  rejected: number;
  items: DocumentInboxItem[];
}

export const documentInboxApi = {
  list: async (buildingId?: string): Promise<DocumentInboxSummary> => {
    const url = buildingId ? `/buildings/${buildingId}/document-inbox` : '/document-inbox';
    const response = await apiClient.get<DocumentInboxSummary>(url);
    return response.data;
  },

  link: async (itemId: string, buildingId: string): Promise<DocumentInboxItem> => {
    const response = await apiClient.post<DocumentInboxItem>(`/document-inbox/${itemId}/link`, {
      building_id: buildingId,
    });
    return response.data;
  },

  classify: async (itemId: string, documentType: string): Promise<DocumentInboxItem> => {
    const response = await apiClient.post<DocumentInboxItem>(`/document-inbox/${itemId}/classify`, {
      document_type: documentType,
    });
    return response.data;
  },

  reject: async (itemId: string): Promise<DocumentInboxItem> => {
    const response = await apiClient.post<DocumentInboxItem>(`/document-inbox/${itemId}/reject`);
    return response.data;
  },
};
