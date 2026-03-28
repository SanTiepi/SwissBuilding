import { apiClient } from '@/api/client';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface DossierReadiness {
  verdict: string;
  safe_to_start: { verdict: string; blockers: any[]; conditions: any[] };
  blockers: any[];
  conditions: any[];
}

export interface DossierCompleteness {
  score_pct: number;
  documented: string[];
  missing: string[];
  expired: string[];
}

export interface DossierStepProgress {
  name: string;
  status: 'done' | 'in_progress' | 'pending';
}

export interface DossierNextAction {
  title: string;
  description: string;
  action_type: string;
}

export interface DossierStatus {
  building_id: string;
  work_type: string;
  lifecycle_stage:
    | 'not_assessed'
    | 'not_ready'
    | 'partially_ready'
    | 'ready'
    | 'pack_generated'
    | 'submitted'
    | 'complement_requested'
    | 'resubmitted'
    | 'acknowledged';
  readiness: DossierReadiness;
  completeness: DossierCompleteness;
  unknowns: { count: number; critical: any[] };
  actions: { total_open: number; high_priority: any[] };
  pack: {
    status: string;
    pack_id: string | null;
    conformance: any | null;
    submitted_at: string | null;
    complement_details: string | null;
  };
  progress: {
    steps_completed: number;
    steps_total: number;
    steps: DossierStepProgress[];
  };
  next_action: DossierNextAction;
}

export interface DossierSubmitData {
  pack_id: string;
  submission_reference?: string;
}

export interface DossierComplementData {
  pack_id: string;
  complement_details: string;
}

export interface DossierAcknowledgeData {
  pack_id: string;
}

/* ------------------------------------------------------------------ */
/*  API                                                                */
/* ------------------------------------------------------------------ */

export const dossierWorkflowApi = {
  getStatus: async (buildingId: string, workType: string): Promise<DossierStatus> => {
    const response = await apiClient.get<DossierStatus>(`/buildings/${buildingId}/dossier/${workType}/status`);
    return response.data;
  },

  generatePack: async (buildingId: string, workType: string): Promise<DossierStatus> => {
    const response = await apiClient.post<DossierStatus>(`/buildings/${buildingId}/dossier/${workType}/generate-pack`);
    return response.data;
  },

  submit: async (buildingId: string, workType: string, data: DossierSubmitData): Promise<DossierStatus> => {
    const response = await apiClient.post<DossierStatus>(`/buildings/${buildingId}/dossier/${workType}/submit`, data);
    return response.data;
  },

  handleComplement: async (
    buildingId: string,
    workType: string,
    data: DossierComplementData,
  ): Promise<DossierStatus> => {
    const response = await apiClient.post<DossierStatus>(
      `/buildings/${buildingId}/dossier/${workType}/complement`,
      data,
    );
    return response.data;
  },

  resubmit: async (buildingId: string, workType: string): Promise<DossierStatus> => {
    const response = await apiClient.post<DossierStatus>(`/buildings/${buildingId}/dossier/${workType}/resubmit`);
    return response.data;
  },

  acknowledge: async (buildingId: string, workType: string, data: DossierAcknowledgeData): Promise<DossierStatus> => {
    const response = await apiClient.post<DossierStatus>(
      `/buildings/${buildingId}/dossier/${workType}/acknowledge`,
      data,
    );
    return response.data;
  },
};
