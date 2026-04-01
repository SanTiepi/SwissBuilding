import { apiClient } from '@/api/client';

export interface TodayFeedItem {
  building_name: string;
  building_id: string | null;
  type?: string;
  title?: string;
  description?: string | null;
  deadline?: string | null;
  priority?: string;
  source?: string;
  action_id?: string | null;
}

export interface TodayDeadline {
  building_name: string;
  building_id: string | null;
  type: string;
  description: string;
  deadline: string | null;
  days_remaining: number;
}

export interface TodayBlocked {
  building_name: string;
  building_id: string | null;
  action_id?: string;
  blocker_description: string;
  blocked_since: string | null;
  impact: string;
}

export interface TodayExpiring {
  building_name: string;
  building_id: string | null;
  document_type: string;
  expiry_date: string;
  days_remaining: number;
}

export interface TodayActivity {
  building_name: string;
  building_id: string | null;
  action: string;
  actor: string;
  timestamp: string | null;
}

export interface TodayStats {
  total_buildings: number;
  buildings_ready: number;
  buildings_blocked: number;
  open_actions: number;
  overdue_actions: number;
  diagnostics_expiring_90d: number;
}

export interface TodayFeed {
  urgent: TodayFeedItem[];
  this_week: TodayFeedItem[];
  upcoming_deadlines: TodayDeadline[];
  blocked: TodayBlocked[];
  expiring_soon: TodayExpiring[];
  recent_activity: TodayActivity[];
  stats: TodayStats;
}

export const todayApi = {
  getFeed: async (): Promise<TodayFeed> => {
    const response = await apiClient.get<TodayFeed>('/today');
    return response.data;
  },
};
