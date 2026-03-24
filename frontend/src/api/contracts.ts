import { apiClient } from '@/api/client';

export interface ContractData {
  id: string;
  building_id: string;
  contract_type: string;
  reference_code: string;
  title: string;
  counterparty_type: string;
  counterparty_id: string;
  date_start: string;
  date_end: string | null;
  annual_cost_chf: number | null;
  payment_frequency: string | null;
  auto_renewal: boolean;
  notice_period_months: number | null;
  status: string;
  notes: string | null;
  source_type: string | null;
  confidence: string | null;
  source_ref: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  counterparty_display_name: string | null;
}

export interface ContractListData {
  id: string;
  building_id: string;
  contract_type: string;
  reference_code: string;
  title: string;
  counterparty_type: string;
  date_start: string;
  date_end: string | null;
  annual_cost_chf: number | null;
  status: string;
  counterparty_display_name: string | null;
}

export interface ContractCreatePayload {
  contract_type: string;
  reference_code: string;
  title: string;
  counterparty_type: string;
  counterparty_id: string;
  date_start: string;
  date_end?: string | null;
  annual_cost_chf?: number | null;
  payment_frequency?: string | null;
  auto_renewal?: boolean;
  notice_period_months?: number | null;
  status?: string;
  notes?: string | null;
}

export interface ContractUpdatePayload {
  contract_type?: string;
  reference_code?: string;
  title?: string;
  date_end?: string | null;
  annual_cost_chf?: number | null;
  payment_frequency?: string | null;
  auto_renewal?: boolean;
  notice_period_months?: number | null;
  status?: string;
  notes?: string | null;
}

export interface ContractSummary {
  building_id: string;
  total_contracts: number;
  active_contracts: number;
  annual_cost_chf: number;
  expiring_90d: number;
  auto_renewal_count: number;
}

export interface PaginatedContracts {
  items: ContractListData[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export const contractsApi = {
  listByBuilding: async (
    buildingId: string,
    params?: { page?: number; size?: number; status?: string; contract_type?: string },
  ): Promise<PaginatedContracts> => {
    const response = await apiClient.get<PaginatedContracts>(`/buildings/${buildingId}/contracts`, { params });
    return response.data;
  },

  get: async (_buildingId: string, contractId: string): Promise<ContractData> => {
    const response = await apiClient.get<ContractData>(`/contracts/${contractId}`);
    return response.data;
  },

  create: async (buildingId: string, data: ContractCreatePayload): Promise<ContractData> => {
    const response = await apiClient.post<ContractData>(`/buildings/${buildingId}/contracts`, data);
    return response.data;
  },

  update: async (contractId: string, data: ContractUpdatePayload): Promise<ContractData> => {
    const response = await apiClient.put<ContractData>(`/contracts/${contractId}`, data);
    return response.data;
  },

  getSummary: async (buildingId: string): Promise<ContractSummary> => {
    const response = await apiClient.get<ContractSummary>(`/buildings/${buildingId}/contract-summary`);
    return response.data;
  },
};
