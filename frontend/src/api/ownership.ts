import { apiClient } from '@/api/client';

export interface OwnershipData {
  id: string;
  building_id: string;
  owner_type: string;
  owner_id: string;
  share_pct: number | null;
  ownership_type: string;
  acquisition_type: string | null;
  acquisition_date: string | null;
  disposal_date: string | null;
  acquisition_price_chf: number | null;
  land_register_ref: string | null;
  status: string;
  document_id: string | null;
  notes: string | null;
  source_type: string | null;
  confidence: string | null;
  source_ref: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  owner_display_name: string | null;
}

export interface OwnershipListData {
  id: string;
  building_id: string;
  owner_type: string;
  owner_id: string;
  share_pct: number | null;
  ownership_type: string;
  status: string;
  acquisition_date: string | null;
  owner_display_name: string | null;
}

export interface OwnershipCreatePayload {
  owner_type: string;
  owner_id: string;
  ownership_type: string;
  share_pct?: number | null;
  acquisition_type?: string | null;
  acquisition_date?: string | null;
  disposal_date?: string | null;
  acquisition_price_chf?: number | null;
  land_register_ref?: string | null;
  status?: string;
  document_id?: string | null;
  notes?: string | null;
}

export interface OwnershipUpdatePayload {
  share_pct?: number | null;
  ownership_type?: string;
  acquisition_type?: string | null;
  acquisition_date?: string | null;
  disposal_date?: string | null;
  acquisition_price_chf?: number | null;
  land_register_ref?: string | null;
  status?: string;
  document_id?: string | null;
  notes?: string | null;
}

export interface OwnershipSummary {
  building_id: string;
  total_records: number;
  active_records: number;
  total_share_pct: number;
  owner_count: number;
  co_ownership: boolean;
}

export interface PaginatedOwnership {
  items: OwnershipListData[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export const ownershipApi = {
  listByBuilding: async (
    buildingId: string,
    params?: { page?: number; size?: number; status?: string },
  ): Promise<PaginatedOwnership> => {
    const response = await apiClient.get<PaginatedOwnership>(`/buildings/${buildingId}/ownership`, { params });
    return response.data;
  },

  get: async (_buildingId: string, recordId: string): Promise<OwnershipData> => {
    const response = await apiClient.get<OwnershipData>(`/ownership/${recordId}`);
    return response.data;
  },

  create: async (buildingId: string, data: OwnershipCreatePayload): Promise<OwnershipData> => {
    const response = await apiClient.post<OwnershipData>(`/buildings/${buildingId}/ownership`, data);
    return response.data;
  },

  update: async (recordId: string, data: OwnershipUpdatePayload): Promise<OwnershipData> => {
    const response = await apiClient.put<OwnershipData>(`/ownership/${recordId}`, data);
    return response.data;
  },

  getSummary: async (buildingId: string): Promise<OwnershipSummary> => {
    const response = await apiClient.get<OwnershipSummary>(`/buildings/${buildingId}/ownership-summary`);
    return response.data;
  },
};
