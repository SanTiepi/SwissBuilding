import { apiClient } from '@/api/client';

/* ── Types ── */

export type ActionPriority = 'P0' | 'P1' | 'P2' | 'P3' | 'P4';
export type ActionSourceType =
  | 'procedural_blocker'
  | 'authority_request'
  | 'obligation'
  | 'inbox'
  | 'intake'
  | 'publication'
  | 'deadline';

export interface ControlTowerAction {
  id: string;
  priority: ActionPriority;
  source_type: ActionSourceType;
  title: string;
  description: string | null;
  building_id: string | null;
  building_address: string | null;
  due_date: string | null;
  assigned_org: string | null;
  assigned_user: string | null;
  link: string;
  confidence: number | null;
  freshness: string | null;
}

export interface ControlTowerSummary {
  p0_blockers: number;
  p1_authority: number;
  p2_overdue: number;
  p3_pending: number;
  p4_upcoming: number;
  total: number;
}

export interface ActionFeedFilters {
  building_id?: string;
  source_type?: ActionSourceType;
  priority?: ActionPriority;
  my_queue?: boolean;
}

/* ── API calls ── */

export async function getActionFeed(filters?: ActionFeedFilters): Promise<ControlTowerAction[]> {
  const params: Record<string, string> = {};
  if (filters?.building_id) params.building_id = filters.building_id;
  if (filters?.source_type) params.source_type = filters.source_type;
  if (filters?.priority) params.priority = filters.priority;
  if (filters?.my_queue) params.my_queue = 'true';

  const res = await apiClient.get<{ items: ControlTowerAction[] }>('/control-tower/actions', { params });
  return res.data.items;
}

export async function getActionSummary(): Promise<ControlTowerSummary> {
  const res = await apiClient.get<ControlTowerSummary>('/control-tower/summary');
  return res.data;
}

/* ── Snooze helpers (localStorage) ── */

const SNOOZE_KEY = 'ct_snoozed';

interface SnoozedEntry {
  until: string; // ISO date
}

function loadSnoozed(): Record<string, SnoozedEntry> {
  try {
    const raw = localStorage.getItem(SNOOZE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, SnoozedEntry>;
    // Purge expired entries
    const now = new Date().toISOString();
    const clean: Record<string, SnoozedEntry> = {};
    for (const [id, entry] of Object.entries(parsed)) {
      if (entry.until > now) clean[id] = entry;
    }
    return clean;
  } catch {
    return {};
  }
}

export function snoozeAction(actionId: string, days: number): void {
  const snoozed = loadSnoozed();
  const until = new Date();
  until.setDate(until.getDate() + days);
  snoozed[actionId] = { until: until.toISOString() };
  localStorage.setItem(SNOOZE_KEY, JSON.stringify(snoozed));
}

export function filterSnoozed(actions: ControlTowerAction[]): ControlTowerAction[] {
  const snoozed = loadSnoozed();
  return actions.filter((a) => !snoozed[a.id]);
}
