import { apiClient } from '@/api/client';

export interface FormTemplateField {
  name: string;
  label: string;
  type: string;
  required: boolean;
  source_mapping: string;
  options?: string[];
}

export interface FormTemplate {
  id: string;
  name: string;
  description: string | null;
  form_type: string;
  jurisdiction_id: string | null;
  canton: string | null;
  fields_schema: FormTemplateField[];
  required_attachments: string[];
  version: string | null;
  source_url: string | null;
  active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ApplicableForm {
  template: FormTemplate;
  reason: string;
}

export interface FormFieldValue {
  value: string | null;
  confidence: string;
  source: string;
  manual_override: boolean;
}

export interface FormInstance {
  id: string;
  template_id: string;
  building_id: string;
  organization_id: string | null;
  created_by_id: string | null;
  intervention_id: string | null;
  status: string;
  field_values: Record<string, FormFieldValue> | null;
  attached_document_ids: string[] | null;
  missing_fields: string[] | null;
  missing_attachments: string[] | null;
  prefill_confidence: number | null;
  submitted_at: string | null;
  submission_reference: string | null;
  complement_details: string | null;
  acknowledged_at: string | null;
  created_at: string;
  updated_at: string | null;
  template_name: string | null;
  template_form_type: string | null;
}

export const formsApi = {
  getApplicable: async (buildingId: string, interventionType?: string): Promise<ApplicableForm[]> => {
    const params: Record<string, string> = {};
    if (interventionType) params.intervention_type = interventionType;
    const response = await apiClient.get<ApplicableForm[]>(
      `/buildings/${buildingId}/forms/applicable`,
      { params },
    );
    return response.data;
  },

  prefill: async (buildingId: string, templateId: string, interventionId?: string): Promise<FormInstance> => {
    const params: Record<string, string> = {};
    if (interventionId) params.intervention_id = interventionId;
    const response = await apiClient.post<FormInstance>(
      `/buildings/${buildingId}/forms/${templateId}/prefill`,
      null,
      { params },
    );
    return response.data;
  },

  list: async (buildingId: string): Promise<FormInstance[]> => {
    const response = await apiClient.get<FormInstance[]>(`/buildings/${buildingId}/forms`);
    return response.data;
  },

  get: async (formId: string): Promise<FormInstance> => {
    const response = await apiClient.get<FormInstance>(`/forms/${formId}`);
    return response.data;
  },

  update: async (
    formId: string,
    data: { field_values?: Record<string, { value: string | null }>; attached_document_ids?: string[] },
  ): Promise<FormInstance> => {
    const response = await apiClient.put<FormInstance>(`/forms/${formId}`, data);
    return response.data;
  },

  submit: async (formId: string, submissionReference?: string): Promise<FormInstance> => {
    const response = await apiClient.post<FormInstance>(`/forms/${formId}/submit`, {
      submission_reference: submissionReference || null,
    });
    return response.data;
  },

  complement: async (formId: string, details: string): Promise<FormInstance> => {
    const response = await apiClient.post<FormInstance>(`/forms/${formId}/complement`, {
      complement_details: details,
    });
    return response.data;
  },

  acknowledge: async (formId: string): Promise<FormInstance> => {
    const response = await apiClient.post<FormInstance>(`/forms/${formId}/acknowledge`);
    return response.data;
  },
};
