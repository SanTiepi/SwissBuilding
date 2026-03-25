import { apiClient } from '@/api/client';

// ─── Types ───────────────────────────────────────────────────────────

export type ProcedureStatus =
  | 'draft'
  | 'submitted'
  | 'under_review'
  | 'complement_requested'
  | 'approved'
  | 'rejected'
  | 'expired'
  | 'withdrawn';

export type StepStatus = 'pending' | 'active' | 'completed' | 'skipped' | 'blocked';

export type RequestStatus = 'open' | 'responded' | 'overdue' | 'closed';

export interface ProcedureStep {
  id: string;
  procedure_id: string;
  step_order: number;
  name: string;
  status: StepStatus;
  due_date: string | null;
  completed_at: string | null;
  required_documents: string[];
  linked_document_ids: string[];
  notes: string | null;
}

export interface AuthorityRequest {
  id: string;
  procedure_id: string;
  request_type: string;
  subject: string;
  body: string;
  response_deadline: string | null;
  response_text: string | null;
  responded_at: string | null;
  status: RequestStatus;
  linked_document_ids: string[];
  created_at: string;
}

export interface Procedure {
  id: string;
  building_id: string;
  procedure_type: string;
  title: string;
  status: ProcedureStatus;
  authority_name: string;
  reference_number: string | null;
  blocks_activities: boolean;
  submitted_at: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
  steps: ProcedureStep[];
  authority_requests: AuthorityRequest[];
}

export interface ProcedureListItem {
  id: string;
  building_id: string;
  building_address: string | null;
  procedure_type: string;
  title: string;
  status: ProcedureStatus;
  authority_name: string;
  reference_number: string | null;
  blocks_activities: boolean;
  submitted_at: string | null;
  created_at: string;
  days_pending: number;
  open_requests: number;
}

export interface ProcedureCreatePayload {
  procedure_type: string;
  title: string;
  authority_name: string;
  blocks_activities?: boolean;
}

export interface ComplementRequestPayload {
  request_type: string;
  subject: string;
  body: string;
  response_deadline?: string | null;
}

export interface ComplementResponsePayload {
  response_text: string;
}

export interface ProceduralBlocker {
  procedure_id: string;
  procedure_title: string;
  status: ProcedureStatus;
  authority_name: string;
}

export interface AdminProcedureFilters {
  status?: ProcedureStatus;
  procedure_type?: string;
  building_id?: string;
  page?: number;
  size?: number;
}

export interface PaginatedProcedures {
  items: ProcedureListItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// ─── API ─────────────────────────────────────────────────────────────

export const permitProceduresApi = {
  /** List procedures for a building */
  getProcedures: async (buildingId: string): Promise<Procedure[]> => {
    const response = await apiClient.get<Procedure[]>(`/buildings/${buildingId}/procedures`);
    return response.data;
  },

  /** Get a single procedure with steps + requests */
  getProcedure: async (id: string): Promise<Procedure> => {
    const response = await apiClient.get<Procedure>(`/procedures/${id}`);
    return response.data;
  },

  /** Create a new procedure */
  createProcedure: async (buildingId: string, data: ProcedureCreatePayload): Promise<Procedure> => {
    const response = await apiClient.post<Procedure>(`/buildings/${buildingId}/procedures`, data);
    return response.data;
  },

  /** Submit a draft procedure */
  submitProcedure: async (id: string): Promise<Procedure> => {
    const response = await apiClient.post<Procedure>(`/procedures/${id}/submit`);
    return response.data;
  },

  /** Complete a step */
  completeStep: async (procedureId: string, stepId: string): Promise<ProcedureStep> => {
    const response = await apiClient.post<ProcedureStep>(`/procedures/${procedureId}/steps/${stepId}/complete`);
    return response.data;
  },

  /** Create a complement/information request */
  createComplementRequest: async (procedureId: string, data: ComplementRequestPayload): Promise<AuthorityRequest> => {
    const response = await apiClient.post<AuthorityRequest>(`/procedures/${procedureId}/requests`, data);
    return response.data;
  },

  /** Respond to an authority request */
  respondToRequest: async (requestId: string, data: ComplementResponsePayload): Promise<AuthorityRequest> => {
    const response = await apiClient.post<AuthorityRequest>(`/authority-requests/${requestId}/respond`, data);
    return response.data;
  },

  /** Approve a procedure */
  approveProcedure: async (id: string, reference: string): Promise<Procedure> => {
    const response = await apiClient.post<Procedure>(`/procedures/${id}/approve`, { reference_number: reference });
    return response.data;
  },

  /** Reject a procedure */
  rejectProcedure: async (id: string, reason: string): Promise<Procedure> => {
    const response = await apiClient.post<Procedure>(`/procedures/${id}/reject`, { reason });
    return response.data;
  },

  /** Get procedural blockers for a building */
  getProceduralBlockers: async (buildingId: string): Promise<ProceduralBlocker[]> => {
    const response = await apiClient.get<ProceduralBlocker[]>(`/buildings/${buildingId}/procedural-blockers`);
    return response.data;
  },

  /** Admin: list all procedures across buildings */
  getAdminProcedures: async (filters?: AdminProcedureFilters): Promise<PaginatedProcedures> => {
    const response = await apiClient.get<PaginatedProcedures>('/admin/procedures', { params: filters });
    return response.data;
  },
};
