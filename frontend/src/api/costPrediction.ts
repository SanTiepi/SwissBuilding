import { apiClient } from '@/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CostPredictionRequest {
  pollutant_type: string;
  material_type: string;
  condition: string;
  surface_m2: number;
  canton: string;
  accessibility: string;
}

export interface CostBreakdownItem {
  label: string;
  percentage: number;
  amount_min: number;
  amount_median: number;
  amount_max: number;
}

export interface CostPredictionResponse {
  pollutant_type: string;
  material_type: string;
  surface_m2: number;
  cost_min: number;
  cost_median: number;
  cost_max: number;
  duration_days: number;
  complexity: string;
  method: string;
  canton_coefficient: number;
  accessibility_coefficient: number;
  breakdown: CostBreakdownItem[];
  disclaimer: string;
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

export const costPredictionApi = {
  predict: (data: CostPredictionRequest): Promise<CostPredictionResponse> =>
    apiClient.post('/predict/cost', data),
};
