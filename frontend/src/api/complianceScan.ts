import { apiClient } from '@/api/client';

export interface ComplianceFindingData {
  type: 'non_conformity' | 'warning' | 'unknown';
  rule: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  deadline: string | null;
  references: string[];
}

export interface FindingsCount {
  non_conformities: number;
  warnings: number;
  unknowns: number;
}

export interface ComplianceScanResponse {
  building_id: string;
  canton: string;
  total_checks_executed: number;
  findings_count: FindingsCount;
  findings: ComplianceFindingData[];
  compliance_score: number;
  scanned_at: string;
}

export const complianceScanApi = {
  scan: async (buildingId: string, force = false): Promise<ComplianceScanResponse> => {
    const response = await apiClient.get<ComplianceScanResponse>(
      `/buildings/${buildingId}/compliance-scan`,
      { params: force ? { force: true } : undefined },
    );
    return response.data;
  },
};
