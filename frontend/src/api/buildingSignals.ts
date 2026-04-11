/**
 * BatiConnect - Canonical Building Signals API client
 *
 * Reads from the building_changes API (BuildingSignal model).
 * This replaces the legacy changeSignals API for signal reads.
 */

import { apiClient } from '@/api/client';

export interface BuildingSignal {
  id: string;
  building_id: string;
  signal_type: string;
  detected_at: string;
  severity: string;
  confidence: number | null;
  title: string;
  description: string;
  recommended_action: string | null;
  based_on_type: string;
  based_on_ids: string[] | null;
  status: string;
  resolved_at: string | null;
  resolved_by_id: string | null;
  resolution_note: string | null;
  created_at: string;
  updated_at: string | null;
}

export const buildingSignalsApi = {
  /** List active signals for a building (canonical endpoint). */
  listActive: async (buildingId: string): Promise<BuildingSignal[]> => {
    const response = await apiClient.get<BuildingSignal[]>(`/buildings/${buildingId}/signals`);
    return response.data;
  },

  /** List recent signals across all buildings (portfolio-level). */
  listPortfolio: async (severity?: string, status?: string, limit = 20): Promise<BuildingSignal[]> => {
    const params: Record<string, string | number> = { limit };
    if (severity) params.severity = severity;
    if (status) params.status = status;
    const response = await apiClient.get<BuildingSignal[]>('/portfolio/signals', { params });
    return response.data;
  },

  /** Acknowledge a signal. */
  acknowledge: async (signalId: string): Promise<BuildingSignal> => {
    const response = await apiClient.post<BuildingSignal>(`/signals/${signalId}/acknowledge`);
    return response.data;
  },

  /** Resolve a signal. */
  resolve: async (signalId: string, resolutionNote?: string): Promise<BuildingSignal> => {
    const response = await apiClient.post<BuildingSignal>(`/signals/${signalId}/resolve`, {
      resolution_note: resolutionNote ?? null,
    });
    return response.data;
  },
};
