import { apiClient } from '@/api/client';

export type DeliveryStatus = 'queued' | 'sent' | 'delivered' | 'viewed' | 'acknowledged';
export type DeliveryMethod = 'email' | 'api' | 'download' | 'portal';

export interface ProofDelivery {
  id: string;
  building_id: string;
  target_type: string; // 'document' | 'pack'
  target_id: string;
  target_name: string;
  audience: string;
  method: DeliveryMethod;
  status: DeliveryStatus;
  content_hash: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export const proofDeliveryApi = {
  async listByBuilding(buildingId: string): Promise<ProofDelivery[]> {
    const res = await apiClient.get<{ items: ProofDelivery[] }>(`/buildings/${buildingId}/proof-deliveries`);
    return res.data.items;
  },
};
