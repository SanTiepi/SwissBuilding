import { apiClient } from '@/api/client';

export interface LeaseData {
  id: string;
  building_id: string;
  unit_id: string | null;
  zone_id: string | null;
  lease_type: string;
  reference_code: string;
  tenant_type: string;
  tenant_id: string;
  date_start: string;
  date_end: string | null;
  notice_period_months: number | null;
  rent_monthly_chf: number | null;
  charges_monthly_chf: number | null;
  deposit_chf: number | null;
  surface_m2: number | null;
  rooms: number | null;
  status: string;
  notes: string | null;
  source_type: string | null;
  confidence: string | null;
  source_ref: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  tenant_display_name: string | null;
  unit_label: string | null;
  zone_name: string | null;
}

export interface LeaseListData {
  id: string;
  building_id: string;
  lease_type: string;
  reference_code: string;
  tenant_type: string;
  tenant_id: string;
  date_start: string;
  date_end: string | null;
  rent_monthly_chf: number | null;
  status: string;
  tenant_display_name: string | null;
  unit_label: string | null;
  zone_name: string | null;
}

export interface ContactOption {
  id: string;
  name: string;
  email: string | null;
  contact_type: string;
}

export interface LeaseCreatePayload {
  lease_type: string;
  reference_code: string;
  tenant_type: string;
  tenant_id: string;
  date_start: string;
  date_end?: string | null;
  unit_id?: string | null;
  zone_id?: string | null;
  notice_period_months?: number | null;
  rent_monthly_chf?: number | null;
  charges_monthly_chf?: number | null;
  deposit_chf?: number | null;
  surface_m2?: number | null;
  rooms?: number | null;
  status?: string;
  notes?: string | null;
}

export interface LeaseUpdatePayload {
  lease_type?: string;
  reference_code?: string;
  date_end?: string | null;
  notice_period_months?: number | null;
  rent_monthly_chf?: number | null;
  charges_monthly_chf?: number | null;
  deposit_chf?: number | null;
  surface_m2?: number | null;
  rooms?: number | null;
  status?: string;
  notes?: string | null;
}

export interface LeaseSummary {
  building_id: string;
  total_leases: number;
  active_leases: number;
  monthly_rent_chf: number;
  monthly_charges_chf: number;
  expiring_90d: number;
  disputed_count: number;
}

export interface PaginatedLeases {
  items: LeaseListData[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export const leasesApi = {
  listByBuilding: async (
    buildingId: string,
    params?: { page?: number; size?: number; status?: string; lease_type?: string },
  ): Promise<PaginatedLeases> => {
    const response = await apiClient.get<PaginatedLeases>(`/buildings/${buildingId}/leases`, { params });
    return response.data;
  },

  get: async (_buildingId: string, leaseId: string): Promise<LeaseData> => {
    const response = await apiClient.get<LeaseData>(`/leases/${leaseId}`);
    return response.data;
  },

  create: async (buildingId: string, data: LeaseCreatePayload): Promise<LeaseData> => {
    const response = await apiClient.post<LeaseData>(`/buildings/${buildingId}/leases`, data);
    return response.data;
  },

  update: async (leaseId: string, data: LeaseUpdatePayload): Promise<LeaseData> => {
    const response = await apiClient.put<LeaseData>(`/leases/${leaseId}`, data);
    return response.data;
  },

  getSummary: async (buildingId: string): Promise<LeaseSummary> => {
    const response = await apiClient.get<LeaseSummary>(`/buildings/${buildingId}/lease-summary`);
    return response.data;
  },

  lookupContacts: async (buildingId: string, query?: string): Promise<ContactOption[]> => {
    const response = await apiClient.get<ContactOption[]>(`/buildings/${buildingId}/contacts/lookup`, {
      params: { q: query || '' },
    });
    return response.data;
  },
};
