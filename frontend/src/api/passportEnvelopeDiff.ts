import { apiClient } from '@/api/client';

// --- Types ---

export interface EnvelopeDiffChange {
  section: string;
  field: string;
  old_value: string | null;
  new_value: string | null;
  change_type: 'added' | 'removed' | 'modified';
}

export interface EnvelopeDiffSummary {
  sections_added: string[];
  sections_removed: string[];
  sections_changed: string[];
  unchanged: string[];
  total_changes: number;
}

export interface EnvelopeDiffResult {
  envelope_a_id: string;
  envelope_b_id: string;
  envelope_a_version: number;
  envelope_b_version: number;
  summary: EnvelopeDiffSummary;
  changes: EnvelopeDiffChange[];
  trust_delta: {
    old_trust: number | null;
    new_trust: number | null;
    trust_change: number | null;
  };
  completeness_delta: {
    old_pct: number | null;
    new_pct: number | null;
  };
  readiness_delta: {
    old_verdicts: Record<string, string>;
    new_verdicts: Record<string, string>;
  };
  grade_delta: {
    old_grade: string | null;
    new_grade: string | null;
  };
}

export interface EnvelopeExportJson {
  schema_version: string;
  format: string;
  exported_at: string;
  source_system: string;
  envelope: {
    id: string;
    building_id: string;
    organization_id: string;
    version: number;
    version_label: string | null;
    status: string;
    content_hash: string;
    is_sovereign: boolean;
    created_at: string | null;
  };
  provenance: Record<string, string | null>;
  redaction: {
    profile: string | null;
    financials_redacted: boolean;
    personal_data_redacted: boolean;
  };
  sections_included: string[];
  passport_data: Record<string, unknown>;
  reimport: {
    reimportable: boolean;
    reimport_format: string;
  };
}

export interface EnvelopeExportCsv {
  format: 'csv-summary';
  content: string;
}

export type EnvelopeExportResult = EnvelopeExportJson | EnvelopeExportCsv;

export interface TransferManifest {
  envelope_id: string;
  building_id: string;
  version: number;
  version_label: string | null;
  status: string;
  is_sovereign: boolean;
  redaction: {
    profile: string | null;
    redacted_categories: string[];
    financials_redacted: boolean;
    personal_data_redacted: boolean;
  };
  recipient_receives: {
    sections: string[];
    section_count: number;
    has_passport_grade: boolean;
    has_knowledge_state: boolean;
    has_completeness: boolean;
    has_readiness: boolean;
    has_evidence_coverage: boolean;
    content_hash: string;
  };
  acknowledgment_required: {
    must_acknowledge_receipt: boolean;
    must_verify_hash: boolean;
    delivery_method: string;
    envelope_status: string;
  };
  generated_at: string;
}

export interface ReimportValidation {
  valid: boolean;
  issues: string[];
  warnings: string[];
  sections_found: string[];
}

// --- API ---

export const passportEnvelopeDiffApi = {
  async diffEnvelopes(envelopeIdA: string, envelopeIdB: string): Promise<EnvelopeDiffResult> {
    const res = await apiClient.get<EnvelopeDiffResult>(
      `/passport-envelope/${envelopeIdA}/diff/${envelopeIdB}`,
    );
    return res.data;
  },

  async exportMachineReadable(
    envelopeId: string,
    format: 'json' | 'csv-summary' = 'json',
  ): Promise<EnvelopeExportResult> {
    const res = await apiClient.get<EnvelopeExportResult>(`/passport-envelope/${envelopeId}/export`, {
      params: { format },
    });
    return res.data;
  },

  async getTransferManifest(envelopeId: string): Promise<TransferManifest> {
    const res = await apiClient.get<TransferManifest>(`/passport-envelope/${envelopeId}/transfer-manifest`);
    return res.data;
  },

  async validateReimport(envelopeData: Record<string, unknown>): Promise<ReimportValidation> {
    const res = await apiClient.post<ReimportValidation>('/passport-envelope/validate-reimport', {
      envelope_data: envelopeData,
    });
    return res.data;
  },
};
