import { apiClient } from '@/api/client';

export interface ArtifactVersion {
  id: string;
  artifact_type: string;
  artifact_id: string;
  version_number: number;
  content_hash: string | null;
  status: 'current' | 'superseded' | 'archived' | 'withdrawn';
  superseded_by_id: string | null;
  created_by_user_id: string | null;
  created_at: string;
  archived_at: string | null;
  archive_reason: string | null;
}

export interface CustodyEvent {
  id: string;
  artifact_version_id: string;
  event_type: string;
  actor_type: string;
  actor_id: string | null;
  actor_name: string | null;
  recipient_org_id: string | null;
  details: Record<string, unknown> | null;
  occurred_at: string;
  created_at: string;
}

export interface CustodyChain {
  artifact_type: string;
  artifact_id: string;
  current_version: ArtifactVersion | null;
  versions: ArtifactVersion[];
  events: CustodyEvent[];
}

export interface ArchivePosture {
  building_id: string;
  total_artifacts: number;
  total_versions: number;
  superseded_count: number;
  archived_count: number;
  withdrawn_count: number;
  current_count: number;
  last_custody_event: CustodyEvent | null;
}

export const artifactCustodyApi = {
  getArchivePosture: async (buildingId: string): Promise<ArchivePosture> => {
    const { data } = await apiClient.get(`/buildings/${buildingId}/archive-posture`);
    return data;
  },

  getChain: async (artifactType: string, artifactId: string): Promise<CustodyChain> => {
    const { data } = await apiClient.get(`/artifacts/${artifactType}/${artifactId}/chain`);
    return data;
  },

  getCurrentVersion: async (artifactType: string, artifactId: string): Promise<ArtifactVersion | null> => {
    const { data } = await apiClient.get(`/artifacts/${artifactType}/${artifactId}/current`);
    return data;
  },

  getVersionEvents: async (versionId: string): Promise<CustodyEvent[]> => {
    const { data } = await apiClient.get(`/artifacts/versions/${versionId}/events`);
    return data;
  },

  archiveVersion: async (versionId: string, reason: string): Promise<ArtifactVersion> => {
    const { data } = await apiClient.post(`/artifacts/versions/${versionId}/archive`, { reason });
    return data;
  },

  withdrawVersion: async (versionId: string): Promise<ArtifactVersion> => {
    const { data } = await apiClient.post(`/artifacts/versions/${versionId}/withdraw`);
    return data;
  },
};
