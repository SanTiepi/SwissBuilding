import { apiClient } from '@/api/client';

export interface RenovationOption {
  work_type: string;
  label_fr: string;
  pollutant: string | null;
  regulatory_basis: string;
  authorities: string[];
}

export interface ReadinessVerdict {
  verdict: string;
  score: number;
  blockers: string[];
  conditions: string[];
}

export interface CompletenessEntry {
  id: string;
  label: string;
  status: string;
  details: string;
}

export interface SubsidyEntry {
  name: string;
  category: string;
  max_amount: number;
  conditions: string;
}

export interface UnknownEntry {
  subject: string;
  type: string;
  severity: string;
}

export interface NextAction {
  title: string;
  priority: string;
  source?: string;
}

export interface CaveatEntry {
  title: string;
  severity: string;
  description: string;
}

export interface ProcedureEntry {
  name: string;
  type: string;
  authority: string;
  steps_count: number;
}

export interface RenovationReadinessAssessment {
  building_id: string;
  work_type: string;
  work_type_label: string;
  error?: string;
  readiness: {
    verdict: string;
    safe_to_start: ReadinessVerdict;
    safe_to_tender: ReadinessVerdict;
  };
  completeness: {
    score_pct: number;
    documented: CompletenessEntry[];
    missing: CompletenessEntry[];
  };
  procedures: {
    applicable: ProcedureEntry[];
    forms_needed: string[];
  };
  subsidies: {
    eligible: SubsidyEntry[];
    total_potential_chf: number;
  };
  unknowns: {
    count: number;
    critical: UnknownEntry[];
    blocking_safe_to_x: UnknownEntry[];
  };
  caveats: CaveatEntry[];
  next_actions: NextAction[];
  pack_ready: boolean;
  pack_blockers: string[];
  passport_grade: string;
  assessed_at: string;
}

export interface RenovationPackResult {
  building_id: string;
  work_type: string;
  work_type_label: string;
  error?: string;
  pack?: {
    pack_id: string;
    version: string;
    sections_count: number;
    generated_at: string;
  };
  assessment_summary?: {
    verdict: string;
    completeness_pct: number;
    passport_grade: string;
  };
}

export const renovationReadinessApi = {
  listOptions: async (buildingId: string): Promise<RenovationOption[]> => {
    const response = await apiClient.get<RenovationOption[]>(
      `/buildings/${buildingId}/renovation-readiness`,
    );
    return response.data;
  },

  assess: async (buildingId: string, workType: string): Promise<RenovationReadinessAssessment> => {
    const response = await apiClient.get<RenovationReadinessAssessment>(
      `/buildings/${buildingId}/renovation-readiness/${workType}`,
    );
    return response.data;
  },

  generatePack: async (buildingId: string, workType: string): Promise<RenovationPackResult> => {
    const response = await apiClient.post<RenovationPackResult>(
      `/buildings/${buildingId}/renovation-readiness/${workType}/pack`,
    );
    return response.data;
  },
};
