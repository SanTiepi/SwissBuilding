import { apiClient } from '@/api/client';
import type { Diagnostic, Sample, ParseReportResponse, ParsedSampleData } from '@/types';

export const diagnosticsApi = {
  listByBuilding: async (buildingId: string): Promise<Diagnostic[]> => {
    const response = await apiClient.get<Diagnostic[]>(`/buildings/${buildingId}/diagnostics`);
    return response.data;
  },

  get: async (id: string): Promise<Diagnostic> => {
    const response = await apiClient.get<Diagnostic>(`/diagnostics/${id}`);
    return response.data;
  },

  create: async (buildingId: string, data: Partial<Diagnostic>): Promise<Diagnostic> => {
    const response = await apiClient.post<Diagnostic>(`/buildings/${buildingId}/diagnostics`, data);
    return response.data;
  },

  update: async (id: string, data: Partial<Diagnostic>): Promise<Diagnostic> => {
    const response = await apiClient.put<Diagnostic>(`/diagnostics/${id}`, data);
    return response.data;
  },

  validate: async (id: string): Promise<Diagnostic> => {
    const response = await apiClient.patch<Diagnostic>(`/diagnostics/${id}/validate`);
    return response.data;
  },

  uploadReport: async (id: string, file: File): Promise<{ samples: Sample[] }> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<{ samples: Sample[] }>(`/diagnostics/${id}/upload-report`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  listSamples: async (diagnosticId: string): Promise<Sample[]> => {
    const response = await apiClient.get<Sample[]>(`/diagnostics/${diagnosticId}/samples`);
    return response.data;
  },

  createSample: async (diagnosticId: string, data: Partial<Sample>): Promise<Sample> => {
    const response = await apiClient.post<Sample>(`/diagnostics/${diagnosticId}/samples`, data);
    return response.data;
  },

  updateSample: async (id: string, data: Partial<Sample>): Promise<Sample> => {
    const response = await apiClient.put<Sample>(`/samples/${id}`, data);
    return response.data;
  },

  deleteSample: async (id: string): Promise<void> => {
    await apiClient.delete(`/samples/${id}`);
  },

  parseReport: async (id: string, file: File): Promise<ParseReportResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<ParseReportResponse>(`/diagnostics/${id}/parse-report`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  applyReport: async (
    id: string,
    data: {
      samples: ParsedSampleData[];
      laboratory?: string;
      laboratory_report_number?: string;
      date_report?: string;
      summary?: string;
      conclusion?: string;
    },
  ): Promise<Sample[]> => {
    const response = await apiClient.post<Sample[]>(`/diagnostics/${id}/apply-report`, data);
    return response.data;
  },
};
