import { apiClient } from '@/api/client';

export interface ComplianceArtefacts {
  total: number;
  by_status: Record<string, number>;
  pending_submissions: number;
}

export interface ReadinessGate {
  status: string;
  score: number;
  blockers_count: number;
}

export interface RegulatoryCheckCategory {
  total: number;
  complete: number;
  missing: number;
}

export interface ComplianceSummary {
  building_id: string;
  completeness_score: number;
  completeness_ready: boolean;
  missing_items: string[];
  artefacts: ComplianceArtefacts;
  readiness: Record<string, ReadinessGate>;
  regulatory_checks: Record<string, RegulatoryCheckCategory>;
}

export const complianceSummaryApi = {
  get: async (buildingId: string): Promise<ComplianceSummary> => {
    const { data } = await apiClient.get<ComplianceSummary>(`/buildings/${buildingId}/compliance/summary`);
    return data;
  },
};
