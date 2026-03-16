import { apiClient } from '@/api/client';

export interface DossierCompletionReport {
  overall_status: 'complete' | 'near_complete' | 'incomplete' | 'critical_gaps';
  overall_score: number;
  top_blockers: Array<{ category: string; description: string; severity: string }>;
  recommended_actions: Array<{ action: string; priority: string; category: string }>;
  gap_categories: Record<string, number>;
  assessed_at: string;
}

export const dossierApi = {
  getCompletionReport: async (buildingId: string): Promise<DossierCompletionReport> => {
    const response = await apiClient.get<DossierCompletionReport>(`/buildings/${buildingId}/dossier-completion`);
    return response.data;
  },

  generate: async (buildingId: string, stage: string = 'avt'): Promise<Blob | { html: string }> => {
    const response = await apiClient.post(`/buildings/${buildingId}/dossier`, null, {
      params: { stage },
      responseType: 'blob',
      validateStatus: () => true,
    });

    // If Gotenberg returned PDF, we get a blob with application/pdf
    const contentType = response.headers['content-type'] || '';
    if (contentType.includes('application/pdf')) {
      return response.data as Blob;
    }

    // Otherwise parse as JSON (HTML fallback)
    const text = await (response.data as Blob).text();
    return JSON.parse(text) as { html: string };
  },

  preview: async (buildingId: string, stage: string = 'avt'): Promise<string> => {
    const response = await apiClient.get(`/buildings/${buildingId}/dossier/preview`, {
      params: { stage },
      responseType: 'text',
    });
    return response.data;
  },
};
