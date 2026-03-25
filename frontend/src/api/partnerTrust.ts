import { apiClient } from '@/api/client';

export type TrustLevel = 'strong' | 'adequate' | 'review' | 'weak' | 'unknown';

export interface PartnerTrustProfile {
  id: string;
  partner_org_id: string;
  delivery_reliability_score: number | null;
  evidence_quality_score: number | null;
  responsiveness_score: number | null;
  overall_trust_level: TrustLevel;
  signal_count: number;
  last_evaluated_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export const partnerTrustApi = {
  async getProfile(orgId: string): Promise<PartnerTrustProfile> {
    const res = await apiClient.get<PartnerTrustProfile>(`/partner-trust/profiles/${orgId}`);
    return res.data;
  },
};
