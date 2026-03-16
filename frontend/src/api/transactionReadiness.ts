import { apiClient } from '@/api/client';

export type TransactionType = 'sell' | 'insure' | 'finance' | 'lease';
export type TransactionStatus = 'ready' | 'conditional' | 'not_ready';

export interface TransactionCheck {
  label: string;
  passed: boolean;
  details: string | null;
}

export interface TransactionItem {
  label: string;
  severity?: string;
  details: string | null;
}

export interface TransactionReadiness {
  building_id: string;
  transaction_type: TransactionType;
  overall_status: TransactionStatus;
  score: number;
  checks: TransactionCheck[];
  blockers: TransactionItem[];
  conditions: TransactionItem[];
  recommendations: TransactionItem[];
  evaluated_at: string;
}

export const transactionReadinessApi = {
  evaluateAll: async (buildingId: string): Promise<TransactionReadiness[]> => {
    const response = await apiClient.get<TransactionReadiness[]>(`/buildings/${buildingId}/transaction-readiness`);
    return response.data;
  },

  evaluate: async (buildingId: string, type: TransactionType): Promise<TransactionReadiness> => {
    const response = await apiClient.get<TransactionReadiness>(
      `/buildings/${buildingId}/transaction-readiness/${type}`,
    );
    return response.data;
  },
};
