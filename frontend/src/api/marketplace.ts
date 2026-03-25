import { apiClient } from '@/api/client';

// ---------------------------------------------------------------------------
// Company Profile types
// ---------------------------------------------------------------------------

export interface CompanyProfile {
  id: string;
  organization_id: string;
  company_name: string;
  legal_form: string | null;
  uid_number: string | null;
  address: string | null;
  city: string | null;
  postal_code: string | null;
  canton: string | null;
  contact_email: string;
  contact_phone: string | null;
  website: string | null;
  description: string | null;
  work_categories: string[];
  certifications: Record<string, unknown>[] | null;
  regions_served: string[] | null;
  employee_count: number | null;
  years_experience: number | null;
  insurance_info: Record<string, unknown> | null;
  is_active: boolean;
  profile_completeness: number | null;
  created_at: string;
  updated_at: string;
}

export interface RatingSummary {
  company_profile_id: string;
  average_rating: number | null;
  total_reviews: number;
  rating_breakdown: Record<string, number>;
  average_quality: number | null;
  average_timeliness: number | null;
  average_communication: number | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export const marketplaceApi = {
  listCompanies: async (params?: {
    page?: number;
    size?: number;
    canton?: string;
    work_category?: string;
    verified_only?: boolean;
  }): Promise<PaginatedResponse<CompanyProfile>> => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.size) searchParams.set('size', String(params.size));
    if (params?.canton) searchParams.set('canton', params.canton);
    if (params?.work_category) searchParams.set('work_category', params.work_category);
    if (params?.verified_only) searchParams.set('verified_only', 'true');
    const query = searchParams.toString();
    return apiClient.get(`/marketplace/companies${query ? `?${query}` : ''}`);
  },

  getCompany: async (id: string): Promise<CompanyProfile> => {
    return apiClient.get(`/marketplace/companies/${id}`);
  },

  getRatingSummary: async (companyId: string): Promise<RatingSummary> => {
    return apiClient.get(`/marketplace/companies/${companyId}/rating-summary`);
  },
};
