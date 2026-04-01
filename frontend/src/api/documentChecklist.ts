import { apiClient } from '@/api/client';

export interface ChecklistItem {
  document_type: string;
  label: string;
  importance: string;
  legal_basis: string | null;
  status: 'present' | 'missing' | 'expired' | 'not_applicable';
  document_id: string | null;
  uploaded_at: string | null;
  recommendation: string | null;
}

export interface DocumentChecklist {
  building_id: string;
  total_required: number;
  total_present: number;
  completion_pct: number;
  items: ChecklistItem[];
  critical_missing: string[];
  evaluated_at: string;
}

export const documentChecklistApi = {
  getChecklist: async (buildingId: string): Promise<DocumentChecklist> => {
    const response = await apiClient.get<DocumentChecklist>(`/buildings/${buildingId}/document-checklist`);
    return response.data;
  },
};
