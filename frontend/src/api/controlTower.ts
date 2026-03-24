import { apiClient } from '@/api/client';
import type { Obligation } from '@/api/obligations';
import type { DocumentInboxSummary } from '@/api/documentInbox';
import type { IntakeListResponse } from '@/api/intake';
import type { DiagnosticPublication } from '@/components/building-detail/DiagnosticPublicationCard';
import type { Building } from '@/types';

export interface ControlTowerSummary {
  overdueObligations: Obligation[];
  dueSoonObligations: Obligation[];
  pendingInboxCount: number;
  unmatchedPublications: DiagnosticPublication[];
  newIntakeRequests: number;
  buildings: Building[];
}

export interface NextBestAction {
  id: string;
  type: 'overdue_obligation' | 'unmatched_publication' | 'pending_inbox' | 'intake_request' | 'due_soon_obligation';
  priority: number; // 1=highest
  title: string;
  description: string | null;
  buildingId: string | null;
  buildingAddress: string | null;
  link: string;
  dueDate: string | null;
}

function isOverdue(dateStr: string | null): boolean {
  if (!dateStr) return false;
  return new Date(dateStr) < new Date();
}

function isDueSoon(dateStr: string | null, days = 30): boolean {
  if (!dateStr) return false;
  const d = new Date(dateStr);
  const now = new Date();
  const limit = new Date();
  limit.setDate(now.getDate() + days);
  return d >= now && d <= limit;
}

export async function fetchControlTowerData(buildingFilter?: string): Promise<ControlTowerSummary> {
  // Fetch all data sources in parallel
  const [buildingsRes, inboxRes, unmatchedRes, intakeRes] = await Promise.all([
    apiClient.get<{ items: Building[]; total: number }>('/buildings', { params: { limit: 200 } }),
    apiClient.get<DocumentInboxSummary>('/document-inbox').catch(() => ({
      data: { total: 0, pending: 0, linked: 0, classified: 0, rejected: 0, items: [] } as DocumentInboxSummary,
    })),
    apiClient.get<DiagnosticPublication[]>('/diagnostic-publications/unmatched').catch(() => ({ data: [] as DiagnosticPublication[] })),
    apiClient.get<IntakeListResponse>('/admin/intake', { params: { status: 'new' } }).catch(() => ({
      data: { items: [], total: 0 } as IntakeListResponse,
    })),
  ]);

  const buildings = buildingsRes.data.items ?? [];
  const targetBuildings = buildingFilter ? buildings.filter((b) => b.id === buildingFilter) : buildings;

  // Fetch obligations for all target buildings (cap at 50 to avoid too many requests)
  const obligationResults = await Promise.all(
    targetBuildings.slice(0, 50).map((b) =>
      apiClient
        .get<Obligation[]>(`/buildings/${b.id}/obligations`)
        .then((r) => r.data.map((o) => ({ ...o, building_id: b.id })))
        .catch(() => [] as Obligation[]),
    ),
  );

  const allObligations = obligationResults.flat();
  const activeObligations = allObligations.filter((o) => o.status !== 'completed' && o.status !== 'cancelled');
  const overdueObligations = activeObligations.filter((o) => isOverdue(o.due_date));
  const dueSoonObligations = activeObligations.filter((o) => isDueSoon(o.due_date));

  return {
    overdueObligations,
    dueSoonObligations,
    pendingInboxCount: inboxRes.data.pending,
    unmatchedPublications: unmatchedRes.data,
    newIntakeRequests: intakeRes.data.total,
    buildings,
  };
}

export function buildNextBestActions(summary: ControlTowerSummary): NextBestAction[] {
  const actions: NextBestAction[] = [];

  // Priority 1: Overdue obligations
  for (const obl of summary.overdueObligations) {
    const building = summary.buildings.find((b) => b.id === obl.building_id);
    actions.push({
      id: `overdue-${obl.id}`,
      type: 'overdue_obligation',
      priority: 1,
      title: obl.title,
      description: obl.description,
      buildingId: obl.building_id,
      buildingAddress: building?.address ?? null,
      link: `/buildings/${obl.building_id}`,
      dueDate: obl.due_date,
    });
  }

  // Priority 2: Unmatched publications
  for (const pub of summary.unmatchedPublications) {
    actions.push({
      id: `unmatched-${pub.id}`,
      type: 'unmatched_publication',
      priority: 2,
      title: `${pub.source_system} — ${pub.source_mission_id}`,
      description: null,
      buildingId: null,
      buildingAddress: null,
      link: '/admin/diagnostic-review',
      dueDate: null,
    });
  }

  // Priority 3: Pending inbox (single action representing all pending)
  if (summary.pendingInboxCount > 0) {
    actions.push({
      id: 'inbox-pending',
      type: 'pending_inbox',
      priority: 3,
      title: `${summary.pendingInboxCount} document(s) en attente`,
      description: null,
      buildingId: null,
      buildingAddress: null,
      link: '/documents',
      dueDate: null,
    });
  }

  // Priority 4: Intake requests
  if (summary.newIntakeRequests > 0) {
    actions.push({
      id: 'intake-new',
      type: 'intake_request',
      priority: 4,
      title: `${summary.newIntakeRequests} demande(s) entrante(s)`,
      description: null,
      buildingId: null,
      buildingAddress: null,
      link: '/admin/intake',
      dueDate: null,
    });
  }

  // Priority 5: Due soon obligations
  for (const obl of summary.dueSoonObligations) {
    const building = summary.buildings.find((b) => b.id === obl.building_id);
    actions.push({
      id: `due-soon-${obl.id}`,
      type: 'due_soon_obligation',
      priority: 5,
      title: obl.title,
      description: obl.description,
      buildingId: obl.building_id,
      buildingAddress: building?.address ?? null,
      link: `/buildings/${obl.building_id}`,
      dueDate: obl.due_date,
    });
  }

  // Sort by priority
  actions.sort((a, b) => a.priority - b.priority);

  return actions;
}
