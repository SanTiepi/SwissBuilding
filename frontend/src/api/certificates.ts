import { apiClient } from '@/api/client';

export interface CertificateContent {
  certificate_id: string;
  certificate_number: string;
  certificate_type: string;
  version: string;
  issued_at: string;
  valid_until: string;
  building: Record<string, unknown> | null;
  evidence_score: { score: number; grade: string } | null;
  passport_grade: string | null;
  completeness: number | null;
  trust_score: number | null;
  readiness_summary: Record<string, unknown> | null;
  key_findings: string[] | null;
  document_coverage: Record<string, number> | null;
  certification_chain: Record<string, unknown> | null;
  verification_url: string | null;
  verification_qr_data: string | null;
  issuer: string | null;
  disclaimer: string | null;
  integrity_hash: string | null;
}

export interface CertificateVerifyResponse {
  valid: boolean;
  certificate: Record<string, unknown> | null;
  reason: string;
}

export interface CertificateListItem {
  id: string;
  certificate_number: string;
  building_id: string;
  certificate_type: string;
  evidence_score: number | null;
  passport_grade: string | null;
  integrity_hash: string | null;
  issued_at: string | null;
  valid_until: string | null;
  status: string | null;
}

export interface CertificateListResponse {
  items: CertificateListItem[];
  total: number;
  page: number;
  size: number;
}

export const certificateApi = {
  generate: async (
    buildingId: string,
    certificateType: string = 'standard',
  ): Promise<CertificateContent> => {
    const response = await apiClient.post(`/buildings/${buildingId}/certificates`, {
      certificate_type: certificateType,
    });
    return response.data;
  },

  get: async (certificateId: string): Promise<CertificateContent> => {
    const response = await apiClient.get(`/certificates/${certificateId}`);
    return response.data;
  },

  verify: async (certificateId: string): Promise<CertificateVerifyResponse> => {
    const response = await apiClient.get(`/certificates/${certificateId}/verify`);
    return response.data;
  },

  listForBuilding: async (
    buildingId: string,
    page: number = 1,
    size: number = 20,
  ): Promise<CertificateListResponse> => {
    const response = await apiClient.get(`/buildings/${buildingId}/certificates`, {
      params: { page, size },
    });
    return response.data;
  },

  listPortfolio: async (page: number = 1, size: number = 20): Promise<CertificateListResponse> => {
    const response = await apiClient.get('/portfolio/certificates', {
      params: { page, size },
    });
    return response.data;
  },

  downloadJson: (certificate: CertificateContent): void => {
    const blob = new Blob([JSON.stringify(certificate, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `certificate-${certificate.certificate_number}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  },
};
