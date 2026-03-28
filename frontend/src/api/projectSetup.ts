import { apiClient } from '@/api/client';

export interface ProjectDraftRequest {
  intervention_type: string;
}

export interface ProjectScope {
  zones: {
    id: string;
    name: string;
    zone_type: string;
    floor_number: number | null;
    surface_area_m2: number | null;
  }[];
  elements_to_treat: {
    sample_number: string;
    location: string;
    material: string;
    risk_level: string;
    concentration: number | null;
    unit: string | null;
    pollutant_type: string | null;
    cfst_work_category: string | null;
    waste_disposal_type: string | null;
  }[];
  materials_involved: Record<
    string,
    {
      count: number;
      items: {
        sample_id: string;
        material_description: string | null;
        material_state: string | null;
        concentration: number | null;
        unit: string | null;
        risk_level: string | null;
        location: string;
        pollutant_type: string | null;
      }[];
    }
  >;
  affected_floors: string[];
  affected_rooms: string[];
  total_positive_samples: number;
  pollutants_found: string[];
}

export interface DocumentChecklistItem {
  document_type: string;
  label: string;
  status: 'available' | 'missing';
}

export interface RegulatoryRequirement {
  ref: string;
  label: string;
}

export interface GapAnalysis {
  can_start: boolean;
  readiness_score: number;
  missing_documents_count: number;
  available_documents_count: number;
  total_required_documents: number;
  has_diagnostic: boolean;
  has_pollutant_diagnostic: boolean;
  has_positive_samples: boolean;
  blockers: string[];
  message: string;
}

export interface ProjectDraft {
  building_id: string;
  suggested_title: string;
  intervention_type: string;
  intervention_type_label: string;
  scope: ProjectScope;
  regulatory_requirements: RegulatoryRequirement[];
  document_checklist: DocumentChecklistItem[];
  relevant_diagnostics: {
    id: string;
    diagnostic_type: string | null;
    status: string;
    date_inspection: string | null;
    laboratory: string | null;
  }[];
  related_actions: {
    id: string;
    title: string;
    priority: string;
    action_type: string;
  }[];
  gap_analysis: GapAnalysis;
  generated_at: string;
}

export interface ProjectCreateRequest {
  intervention_type: string;
  title: string;
  description?: string;
  zones_affected?: string[];
  materials_used?: string[];
  gaps?: { label: string }[];
}

export const projectSetupApi = {
  generateDraft: async (buildingId: string, interventionType: string): Promise<ProjectDraft> => {
    const response = await apiClient.post<ProjectDraft>(`/buildings/${buildingId}/projects/generate`, {
      intervention_type: interventionType,
    });
    return response.data;
  },

  createProject: async (buildingId: string, data: ProjectCreateRequest): Promise<unknown> => {
    const response = await apiClient.post(`/buildings/${buildingId}/projects`, data);
    return response.data;
  },
};
