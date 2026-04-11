/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view under PortfolioCommand.
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { campaignsApi } from '@/api/campaigns';
import type { CampaignImpact } from '@/api/campaigns';
import type { Campaign, CampaignStatus, CampaignType, CampaignRecommendation, CampaignTrackingStatus } from '@/types';
import { toast } from '@/store/toastStore';
import {
  Loader2,
  Plus,
  Megaphone,
  Calendar,
  Building2,
  ChevronRight,
  ChevronDown,
  Trash2,
  Edit2,
  X,
  AlertTriangle,
  TrendingUp,
  Clock,
  Target,
  Sparkles,
  Play,
  CheckCircle2,
  Ban,
  SkipForward,
} from 'lucide-react';
import { cn } from '@/utils/formatters';

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
  active: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  paused: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  completed: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  cancelled: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const priorityColors: Record<string, string> = {
  low: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const typeIcons: Record<string, string> = {
  diagnostic: '\uD83D\uDD2C',
  remediation: '\uD83D\uDEE0\uFE0F',
  inspection: '\uD83D\uDD0D',
  maintenance: '\u2699\uFE0F',
  documentation: '\uD83D\uDCC4',
  other: '\uD83D\uDCCB',
};

const trackingStatusColors: Record<CampaignTrackingStatus, string> = {
  not_started: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
  in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  blocked: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  skipped: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
};

const trackingBarColors: Record<CampaignTrackingStatus, string> = {
  not_started: 'bg-gray-300 dark:bg-gray-600',
  in_progress: 'bg-blue-500',
  blocked: 'bg-red-500',
  completed: 'bg-green-500',
  skipped: 'bg-yellow-500',
};

function getProgressColor(impact: CampaignImpact | undefined): string {
  if (!impact) return 'bg-indigo-600';
  if (impact.is_at_risk) return 'bg-red-500';
  if (impact.completion_rate < 0.5 && impact.days_remaining !== null && impact.days_remaining < 60)
    return 'bg-amber-500';
  return 'bg-green-500';
}

function ProgressRing({
  completed,
  inProgress,
  total,
  size = 80,
}: {
  completed: number;
  inProgress: number;
  total: number;
  size?: number;
}) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const completedPct = total > 0 ? completed / total : 0;
  const inProgressPct = total > 0 ? inProgress / total : 0;
  const completedDash = completedPct * circumference;
  const inProgressDash = inProgressPct * circumference;

  return (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={6}
        className="text-gray-200 dark:text-gray-700"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={6}
        strokeDasharray={`${inProgressDash} ${circumference - inProgressDash}`}
        strokeDashoffset={-completedDash}
        className="text-amber-400"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={6}
        strokeDasharray={`${completedDash} ${circumference - completedDash}`}
        className="text-green-500"
      />
    </svg>
  );
}

function TimelineBar({ dateStart, dateEnd }: { dateStart: string | null; dateEnd: string | null }) {
  const [now] = useState(() => Date.now());

  if (!dateStart) return null;

  const start = new Date(dateStart).getTime();
  const end = dateEnd ? new Date(dateEnd).getTime() : now + 30 * 24 * 60 * 60 * 1000;
  const total = end - start;
  const elapsed = now - start;
  const pct = total > 0 ? Math.min(100, Math.max(0, (elapsed / total) * 100)) : 0;

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>{new Date(dateStart).toLocaleDateString()}</span>
        {dateEnd && <span>{new Date(dateEnd).toLocaleDateString()}</span>}
      </div>
      <div className="relative mt-1 h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
        <div className="h-2 rounded-full bg-indigo-500 transition-all" style={{ width: `${pct}%` }} />
        <div
          className="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border-2 border-white bg-indigo-600 dark:border-gray-800"
          style={{ left: `${pct}%`, marginLeft: '-6px' }}
        />
      </div>
    </div>
  );
}

// ─── Recommendations Section ────────────────────────────────────────────────

function RecommendationsSection({
  t,
  onCreateFromRecommendation,
}: {
  t: (key: string) => string;
  onCreateFromRecommendation: (rec: CampaignRecommendation) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const { data: recommendations, isLoading } = useQuery({
    queryKey: ['campaign-recommendations'],
    queryFn: () => campaignsApi.getRecommendations(5),
  });

  if (isLoading || !recommendations || recommendations.length === 0) return null;

  return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50/50 dark:border-indigo-800 dark:bg-indigo-900/20">
      <button onClick={() => setExpanded(!expanded)} className="flex w-full items-center justify-between px-5 py-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          <span className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">
            {t('campaign.recommendations')}
          </span>
          <span className="rounded-full bg-indigo-200 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-800 dark:text-indigo-300">
            {recommendations.length}
          </span>
        </div>
        <ChevronDown className={cn('h-4 w-4 text-indigo-500 transition-transform', expanded && 'rotate-180')} />
      </button>

      {expanded && (
        <div className="grid gap-3 px-5 pb-5 md:grid-cols-2 lg:grid-cols-3">
          {recommendations.map((rec, idx) => (
            <div
              key={idx}
              className="rounded-lg border border-indigo-200 bg-white p-4 dark:border-indigo-700 dark:bg-gray-800"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm">{typeIcons[rec.campaign_type] || '\uD83D\uDCCB'}</span>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{rec.title}</h4>
                </div>
                <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', priorityColors[rec.priority])}>
                  {t(`action_priority.${rec.priority}`)}
                </span>
              </div>

              {rec.description && (
                <p className="mt-2 text-xs text-gray-600 line-clamp-2 dark:text-gray-400">{rec.description}</p>
              )}

              <div className="mt-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">{t('campaign.rationale')}</p>
                <p className="mt-0.5 text-xs text-gray-700 line-clamp-2 dark:text-gray-300">{rec.rationale}</p>
              </div>

              <div className="mt-3 flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span>{t('campaign.impact_score')}</span>
                    <span>{Math.round(rec.impact_score * 100)}%</span>
                  </div>
                  <div className="mt-1 h-1.5 w-full rounded-full bg-gray-200 dark:bg-gray-700">
                    <div
                      className="h-1.5 rounded-full bg-indigo-500"
                      style={{ width: `${Math.round(rec.impact_score * 100)}%` }}
                    />
                  </div>
                </div>
                <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                  <Building2 className="h-3 w-3" />
                  {rec.building_count}
                </span>
              </div>

              <button
                onClick={() => onCreateFromRecommendation(rec)}
                className="mt-3 w-full rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
              >
                {t('campaign.create_from_recommendation')}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Tracking Tab ───────────────────────────────────────────────────────────

function TrackingTab({ campaignId, t }: { campaignId: string; t: (key: string) => string }) {
  const queryClient = useQueryClient();

  const { data: trackingList, isLoading: loadingTracking } = useQuery({
    queryKey: ['campaign-tracking', campaignId],
    queryFn: () => campaignsApi.getTracking(campaignId),
  });

  const { data: progress } = useQuery({
    queryKey: ['campaign-tracking-progress', campaignId],
    queryFn: () => campaignsApi.getTrackingProgress(campaignId),
  });

  const updateMutation = useMutation({
    mutationFn: ({ buildingId, data }: { buildingId: string; data: { status: string; blocker_reason?: string } }) =>
      campaignsApi.updateBuildingStatus(campaignId, buildingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign-tracking', campaignId] });
      queryClient.invalidateQueries({ queryKey: ['campaign-tracking-progress', campaignId] });
    },
  });

  const handleStatusChange = (buildingId: string, newStatus: CampaignTrackingStatus) => {
    if (newStatus === 'blocked') {
      const reason = prompt(t('campaign.blocker_reason'));
      if (reason === null) return;
      updateMutation.mutate({ buildingId, data: { status: newStatus, blocker_reason: reason } });
    } else {
      updateMutation.mutate({ buildingId, data: { status: newStatus } });
    }
  };

  if (loadingTracking) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
      </div>
    );
  }

  const buildings = trackingList ?? [];
  const allStatuses: CampaignTrackingStatus[] = ['not_started', 'in_progress', 'blocked', 'completed', 'skipped'];
  const trackingStatusKeys: Record<CampaignTrackingStatus, string> = {
    not_started: 'campaign.not_started',
    in_progress: 'campaign.in_progress_tracking',
    blocked: 'campaign.blocked',
    completed: 'campaign.completed_tracking',
    skipped: 'campaign.skipped',
  };

  return (
    <div className="space-y-4">
      {/* Progress summary */}
      {progress && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-gray-700 dark:text-gray-300">{t('campaign.tracking_progress')}</span>
            <span className="text-gray-500 dark:text-gray-400">{Math.round(progress.overall_progress_pct)}%</span>
          </div>
          {/* Stacked status bar */}
          <div className="flex h-3 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
            {allStatuses.map((status) => {
              const count = progress.by_status[status] ?? 0;
              const pct = progress.total > 0 ? (count / progress.total) * 100 : 0;
              if (pct === 0) return null;
              return (
                <div
                  key={status}
                  className={cn('h-full transition-all', trackingBarColors[status])}
                  style={{ width: `${pct}%` }}
                  title={`${t(trackingStatusKeys[status])}: ${count}`}
                />
              );
            })}
          </div>
          {/* Legend */}
          <div className="flex flex-wrap gap-3 text-xs text-gray-500 dark:text-gray-400">
            {allStatuses.map((status) => {
              const count = progress.by_status[status] ?? 0;
              if (count === 0) return null;
              return (
                <span key={status} className="flex items-center gap-1">
                  <span className={cn('inline-block h-2 w-2 rounded-full', trackingBarColors[status])} />
                  {t(trackingStatusKeys[status])}: {count}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Building list */}
      {buildings.length === 0 ? (
        <p className="py-4 text-center text-sm text-gray-500 dark:text-gray-400">{t('campaign.empty')}</p>
      ) : (
        <div className="space-y-2">
          {buildings.map((b) => (
            <div
              key={b.building_id}
              className={cn(
                'rounded-lg border p-3',
                b.status === 'blocked'
                  ? 'border-red-300 bg-red-50 dark:border-red-700 dark:bg-red-900/20'
                  : 'border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800',
              )}
            >
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <Building2 className="h-3.5 w-3.5 flex-shrink-0 text-gray-400" />
                    <span className="truncate text-sm font-medium text-gray-900 dark:text-white">
                      {b.building_address || b.building_id.slice(0, 8)}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <span
                      className={cn('rounded-full px-2 py-0.5 text-xs font-medium', trackingStatusColors[b.status])}
                    >
                      {t(trackingStatusKeys[b.status])}
                    </span>
                    <span className="text-xs text-gray-400 dark:text-gray-500">{Math.round(b.progress_pct)}%</span>
                  </div>
                  {b.status === 'blocked' && b.blocker_reason && (
                    <p className="mt-1 flex items-center gap-1 text-xs text-red-600 dark:text-red-400">
                      <AlertTriangle className="h-3 w-3" />
                      {b.blocker_reason}
                    </p>
                  )}
                </div>

                {/* Quick status buttons */}
                <div className="ml-2 flex flex-shrink-0 items-center gap-1">
                  {b.status !== 'in_progress' && b.status !== 'completed' && (
                    <button
                      onClick={() => handleStatusChange(b.building_id, 'in_progress')}
                      title={t('campaign.start_building')}
                      className="rounded p-1 text-blue-600 hover:bg-blue-100 dark:text-blue-400 dark:hover:bg-blue-900/30"
                    >
                      <Play className="h-3.5 w-3.5" />
                    </button>
                  )}
                  {b.status !== 'completed' && (
                    <button
                      onClick={() => handleStatusChange(b.building_id, 'completed')}
                      title={t('campaign.complete_building')}
                      className="rounded p-1 text-green-600 hover:bg-green-100 dark:text-green-400 dark:hover:bg-green-900/30"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                  {b.status !== 'blocked' && (
                    <button
                      onClick={() => handleStatusChange(b.building_id, 'blocked')}
                      title={t('campaign.block_building')}
                      className="rounded p-1 text-red-600 hover:bg-red-100 dark:text-red-400 dark:hover:bg-red-900/30"
                    >
                      <Ban className="h-3.5 w-3.5" />
                    </button>
                  )}
                  {b.status !== 'skipped' && b.status !== 'completed' && (
                    <button
                      onClick={() => handleStatusChange(b.building_id, 'skipped')}
                      title={t('campaign.skip_building')}
                      className="rounded p-1 text-yellow-600 hover:bg-yellow-100 dark:text-yellow-400 dark:hover:bg-yellow-900/30"
                    >
                      <SkipForward className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Edit Modal ─────────────────────────────────────────────────────────────

function EditCampaignModal({
  campaign,
  onClose,
  onSave,
  t,
  types,
  statuses,
}: {
  campaign: Campaign;
  onClose: () => void;
  onSave: (data: Partial<Campaign>) => void;
  t: (key: string) => string;
  types: CampaignType[];
  statuses: CampaignStatus[];
}) {
  const [title, setTitle] = useState(campaign.title);
  const [description, setDescription] = useState(campaign.description ?? '');
  const [campaignType, setCampaignType] = useState<CampaignType>(campaign.campaign_type);
  const [status, setStatus] = useState<CampaignStatus>(campaign.status);
  const [priority, setPriority] = useState<'low' | 'medium' | 'high' | 'critical'>(campaign.priority);
  const [dateStart, setDateStart] = useState(campaign.date_start?.slice(0, 10) ?? '');
  const [dateEnd, setDateEnd] = useState(campaign.date_end?.slice(0, 10) ?? '');
  const [budgetChf, setBudgetChf] = useState(campaign.budget_chf?.toString() ?? '');
  const [notes, setNotes] = useState(campaign.notes ?? '');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onSave({
      title: title.trim(),
      description: description.trim() || null,
      campaign_type: campaignType,
      status,
      priority,
      date_start: dateStart || null,
      date_end: dateEnd || null,
      budget_chf: budgetChf ? Number(budgetChf) : null,
      notes: notes.trim() || null,
    });
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t('campaign.edit')}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">{t('campaign.name')}</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('campaign.description')}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">{t('campaign.type')}</label>
              <select
                value={campaignType}
                onChange={(e) => setCampaignType(e.target.value as CampaignType)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                {types.map((tp) => (
                  <option key={tp} value={tp}>
                    {t(`campaign_type.${tp}`)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('campaign.status')}
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as CampaignStatus)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                {statuses.map((s) => (
                  <option key={s} value={s}>
                    {t(`campaign_status.${s}`)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('campaign.priority')}
            </label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value as 'low' | 'medium' | 'high' | 'critical')}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
              {(['low', 'medium', 'high', 'critical'] as const).map((p) => (
                <option key={p} value={p}>
                  {t(`action_priority.${p}`)}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('campaign.date_start')}
              </label>
              <input
                type="date"
                value={dateStart}
                onChange={(e) => setDateStart(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('campaign.date_end')}
              </label>
              <input
                type="date"
                value={dateEnd}
                onChange={(e) => setDateEnd(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">{t('campaign.budget')}</label>
            <input
              type="number"
              value={budgetChf}
              onChange={(e) => setBudgetChf(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              min={0}
              step={100}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">{t('campaign.notes')}</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              {t('common.save') || 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Create Modal ───────────────────────────────────────────────────────────

function CreateCampaignModal({
  onClose,
  onSubmit,
  t,
  types,
  initialData,
}: {
  onClose: () => void;
  onSubmit: (data: Partial<Campaign>) => void;
  t: (key: string) => string;
  types: CampaignType[];
  initialData?: Partial<Campaign>;
}) {
  const [title, setTitle] = useState(initialData?.title ?? '');
  const [description, setDescription] = useState(initialData?.description ?? '');
  const [campaignType, setCampaignType] = useState<CampaignType>(initialData?.campaign_type ?? 'diagnostic');
  const [priority, setPriority] = useState<'low' | 'medium' | 'high' | 'critical'>(initialData?.priority ?? 'medium');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onSubmit({
      title: title.trim(),
      description: description.trim() || null,
      campaign_type: campaignType,
      priority,
      status: 'draft',
      building_ids: initialData?.building_ids ?? null,
      criteria_json: initialData?.criteria_json ?? null,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t('campaign.create')}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">{t('campaign.name')}</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('campaign.description')}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">{t('campaign.type')}</label>
              <select
                value={campaignType}
                onChange={(e) => setCampaignType(e.target.value as CampaignType)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                {types.map((tp) => (
                  <option key={tp} value={tp}>
                    {t(`campaign_type.${tp}`)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('campaign.priority')}
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as 'low' | 'medium' | 'high' | 'critical')}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                {(['low', 'medium', 'high', 'critical'] as const).map((p) => (
                  <option key={p} value={p}>
                    {t(`action_priority.${p}`)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              {t('campaign.create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Main Page ──────────────────────────────────────────────────────────────

export default function Campaigns() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createInitialData, setCreateInitialData] = useState<Partial<Campaign> | undefined>(undefined);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [detailTab, setDetailTab] = useState<'details' | 'tracking'>('details');

  const {
    data: campaignsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['campaigns', statusFilter, typeFilter],
    queryFn: () =>
      campaignsApi.list({
        status: statusFilter || undefined,
        campaign_type: typeFilter || undefined,
        page: 1,
        size: 50,
      }),
  });

  const campaigns = campaignsData?.items ?? [];

  // Fetch impact for active campaigns to get at-risk count and completion rates
  const activeCampaigns = campaigns.filter((c) => c.status === 'active');
  const impactQueries = useQuery({
    queryKey: ['campaign-impacts', activeCampaigns.map((c) => c.id).join(',')],
    queryFn: async () => {
      const results: Record<string, CampaignImpact> = {};
      await Promise.all(
        activeCampaigns.map(async (c) => {
          try {
            results[c.id] = await campaignsApi.getImpact(c.id);
          } catch {
            // skip failed fetches
          }
        }),
      );
      return results;
    },
    enabled: activeCampaigns.length > 0,
  });

  const impactMap = impactQueries.data ?? {};

  // Fetch impact for selected campaign
  const selectedImpactQuery = useQuery({
    queryKey: ['campaign-impact', selectedCampaign?.id],
    queryFn: () => campaignsApi.getImpact(selectedCampaign!.id),
    enabled: !!selectedCampaign,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => campaignsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      setSelectedCampaign(null);
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: Partial<Campaign>) => campaignsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      setShowCreateModal(false);
      setCreateInitialData(undefined);
    },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Campaign> }) => campaignsApi.update(id, data),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast(t('campaign.edit_success'), 'success');
      setShowEditModal(false);
      setSelectedCampaign(updated);
    },
    onError: () => {
      toast(t('campaign.edit_error'), 'error');
    },
  });

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '\u2014';
    try {
      return new Date(dateStr).toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  const handleCreateFromRecommendation = (rec: CampaignRecommendation) => {
    setCreateInitialData({
      title: rec.title,
      description: rec.description,
      campaign_type: rec.campaign_type,
      priority: rec.priority,
      building_ids: rec.building_ids,
      criteria_json: rec.criteria_json,
    });
    setShowCreateModal(true);
  };

  const isAdmin = user?.role === 'admin' || user?.role === 'owner';
  const statuses: CampaignStatus[] = ['draft', 'active', 'paused', 'completed', 'cancelled'];
  const types: CampaignType[] = ['diagnostic', 'remediation', 'inspection', 'maintenance', 'documentation', 'other'];

  // Enhanced KPI calculations
  const atRiskCount = Object.values(impactMap).filter((i) => i.is_at_risk).length;
  const overallCompletionRate =
    activeCampaigns.length > 0
      ? Math.round(
          (Object.values(impactMap).reduce((sum, i) => sum + i.completion_rate, 0) /
            Math.max(1, Object.values(impactMap).length)) *
            100,
        )
      : 0;

  if (error) {
    return (
      <div className="flex items-center justify-center p-8">
        <p className="text-red-600 dark:text-red-400">{t('app.error')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Megaphone className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('campaign.title')}</h1>
        </div>
        {isAdmin && (
          <button
            onClick={() => {
              setCreateInitialData(undefined);
              setShowCreateModal(true);
            }}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            {t('campaign.create')}
          </button>
        )}
      </div>

      {/* Campaign KPIs */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          <p className="text-xs text-gray-500 dark:text-slate-400">{t('campaign.kpi.total') || 'Total Campaigns'}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{campaigns.length}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          <p className="text-xs text-gray-500 dark:text-slate-400">{t('campaign.kpi.active') || 'Active'}</p>
          <p className="mt-1 text-2xl font-bold text-blue-600 dark:text-blue-400">{activeCampaigns.length}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          <p className="text-xs text-gray-500 dark:text-slate-400">{t('campaign.completion_rate')}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{overallCompletionRate}%</p>
        </div>
        <div
          className={cn(
            'rounded-xl border p-4',
            atRiskCount > 0
              ? 'border-red-300 bg-red-50 dark:border-red-700 dark:bg-red-900/20'
              : 'border-gray-200 bg-white dark:border-slate-700 dark:bg-slate-800',
          )}
        >
          <p className="flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400">
            {atRiskCount > 0 && <AlertTriangle className="h-3 w-3 text-red-500" />}
            {t('campaign.at_risk')}
          </p>
          <p
            className={cn(
              'mt-1 text-2xl font-bold',
              atRiskCount > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-white',
            )}
          >
            {atRiskCount}
          </p>
        </div>
      </div>

      {/* Recommendations */}
      {isAdmin && <RecommendationsSection t={t} onCreateFromRecommendation={handleCreateFromRecommendation} />}

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        >
          <option value="">
            {t('campaign.status')}: {t('common.all')}
          </option>
          {statuses.map((s) => (
            <option key={s} value={s}>
              {t(`campaign_status.${s}`)}
            </option>
          ))}
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        >
          <option value="">
            {t('campaign.type')}: {t('common.all')}
          </option>
          {types.map((tp) => (
            <option key={tp} value={tp}>
              {t(`campaign_type.${tp}`)}
            </option>
          ))}
        </select>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center p-12">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
        </div>
      ) : campaigns.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center dark:border-gray-600">
          <Megaphone className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">{t('campaign.empty')}</h3>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t('campaign.empty_desc')}</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {campaigns.map((campaign) => {
            const impact = impactMap[campaign.id];
            const progressBarColor = getProgressColor(impact);
            return (
              <div
                key={campaign.id}
                onClick={() => {
                  setSelectedCampaign(campaign);
                  setDetailTab('details');
                }}
                className="cursor-pointer rounded-lg border border-gray-200 bg-white p-5 shadow-sm transition hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{typeIcons[campaign.campaign_type] || '\uD83D\uDCCB'}</span>
                    <h3 className="font-semibold text-gray-900 dark:text-white">{campaign.title}</h3>
                  </div>
                  <div className="flex items-center gap-1">
                    {impact?.is_at_risk && (
                      <span className="rounded-full bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400">
                        {t('campaign.at_risk')}
                      </span>
                    )}
                    <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', statusColors[campaign.status])}>
                      {t(`campaign_status.${campaign.status}`)}
                    </span>
                  </div>
                </div>

                {campaign.description && (
                  <p className="mt-2 text-sm text-gray-600 line-clamp-2 dark:text-gray-400">{campaign.description}</p>
                )}

                <div className="mt-4 space-y-2">
                  {/* Progress bar */}
                  <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span>{t('campaign.progress')}</span>
                    <span>
                      {campaign.completed_count}/{campaign.target_count}
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
                    <div
                      className={cn('h-2 rounded-full transition-all', progressBarColor)}
                      style={{
                        width: `${campaign.target_count > 0 ? (campaign.completed_count / campaign.target_count) * 100 : 0}%`,
                      }}
                    />
                  </div>

                  {impact && impact.velocity > 0 && (
                    <p className="text-xs text-gray-400 dark:text-gray-500">
                      <TrendingUp className="mr-1 inline h-3 w-3" />
                      {impact.velocity.toFixed(2)} {t('campaign.velocity').toLowerCase()}/
                      {t('campaign.days_remaining').split(' ')[0]?.toLowerCase() || 'd'}
                    </p>
                  )}

                  {campaign.budget_chf != null && campaign.budget_chf > 0 && (
                    <div className="mt-2">
                      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-slate-400">
                        <span>{t('campaign.budget_used') || 'Budget used'}</span>
                        <span>{Math.round(((campaign.spent_chf ?? 0) / campaign.budget_chf) * 100)}%</span>
                      </div>
                      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-gray-200 dark:bg-slate-600">
                        <div
                          className="h-full rounded-full bg-blue-500"
                          style={{
                            width: `${Math.min(100, Math.round(((campaign.spent_chf ?? 0) / campaign.budget_chf) * 100))}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                    <span className="flex items-center gap-1">
                      <Building2 className="h-3 w-3" />
                      {impact?.buildings_affected ?? campaign.target_count}{' '}
                      {t('campaign.buildings_affected').toLowerCase()}
                    </span>
                    {campaign.date_start && (
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {formatDate(campaign.date_start)}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <span
                      className={cn('rounded-full px-2 py-0.5 text-xs font-medium', priorityColors[campaign.priority])}
                    >
                      {t(`action_priority.${campaign.priority}`)}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {t(`campaign_type.${campaign.campaign_type}`)}
                    </span>
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-end text-indigo-600 dark:text-indigo-400">
                  <ChevronRight className="h-4 w-4" />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detail Modal */}
      {selectedCampaign && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setSelectedCampaign(null)}
        >
          <div
            className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">{selectedCampaign.title}</h2>
              <button onClick={() => setSelectedCampaign(null)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Tab bar */}
            <div className="mt-4 flex gap-1 border-b border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setDetailTab('details')}
                className={cn(
                  'px-4 py-2 text-sm font-medium transition-colors',
                  detailTab === 'details'
                    ? 'border-b-2 border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300',
                )}
              >
                {t('campaign.details_tab')}
              </button>
              <button
                onClick={() => setDetailTab('tracking')}
                className={cn(
                  'px-4 py-2 text-sm font-medium transition-colors',
                  detailTab === 'tracking'
                    ? 'border-b-2 border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300',
                )}
              >
                {t('campaign.tracking')}
              </button>
            </div>

            {detailTab === 'details' ? (
              <div className="mt-4 space-y-4">
                <div className="flex gap-2">
                  <span
                    className={cn(
                      'rounded-full px-2 py-0.5 text-xs font-medium',
                      statusColors[selectedCampaign.status],
                    )}
                  >
                    {t(`campaign_status.${selectedCampaign.status}`)}
                  </span>
                  <span
                    className={cn(
                      'rounded-full px-2 py-0.5 text-xs font-medium',
                      priorityColors[selectedCampaign.priority],
                    )}
                  >
                    {t(`action_priority.${selectedCampaign.priority}`)}
                  </span>
                  {selectedImpactQuery.data?.is_at_risk && (
                    <span className="flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400">
                      <AlertTriangle className="h-3 w-3" />
                      {t('campaign.at_risk')}
                    </span>
                  )}
                  {selectedImpactQuery.data && !selectedImpactQuery.data.is_at_risk && (
                    <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
                      {t('campaign.on_track')}
                    </span>
                  )}
                </div>

                {selectedCampaign.description && (
                  <p className="text-sm text-gray-600 dark:text-gray-400">{selectedCampaign.description}</p>
                )}

                {/* Impact section */}
                {selectedImpactQuery.data && (
                  <div className="space-y-4">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                      {t('campaign.impact_title')}
                    </h3>

                    {/* Progress ring + metrics row */}
                    <div className="flex items-center gap-6 rounded-lg bg-gray-50 p-4 dark:bg-gray-700/50">
                      <div className="relative flex-shrink-0">
                        <ProgressRing
                          completed={selectedImpactQuery.data.actions_completed}
                          inProgress={selectedImpactQuery.data.actions_in_progress}
                          total={selectedImpactQuery.data.actions_total}
                          size={80}
                        />
                        <div className="absolute inset-0 flex items-center justify-center">
                          <span className="text-sm font-bold text-gray-900 dark:text-white">
                            {Math.round(selectedImpactQuery.data.completion_rate * 100)}%
                          </span>
                        </div>
                      </div>

                      <div className="grid flex-1 grid-cols-2 gap-3 sm:grid-cols-4">
                        <div>
                          <p className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                            <Building2 className="h-3 w-3" />
                            {t('campaign.buildings_affected')}
                          </p>
                          <p className="text-lg font-bold text-gray-900 dark:text-white">
                            {selectedImpactQuery.data.buildings_affected}
                          </p>
                        </div>
                        <div>
                          <p className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                            <Target className="h-3 w-3" />
                            {t('campaign.completion_rate')}
                          </p>
                          <p className="text-lg font-bold text-gray-900 dark:text-white">
                            {selectedImpactQuery.data.actions_completed}/{selectedImpactQuery.data.actions_total}
                          </p>
                        </div>
                        <div>
                          <p className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                            <TrendingUp className="h-3 w-3" />
                            {t('campaign.velocity')}
                          </p>
                          <p className="text-lg font-bold text-gray-900 dark:text-white">
                            {selectedImpactQuery.data.velocity.toFixed(2)}/d
                          </p>
                        </div>
                        <div>
                          <p className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                            <Clock className="h-3 w-3" />
                            {t('campaign.days_remaining')}
                          </p>
                          <p className="text-lg font-bold text-gray-900 dark:text-white">
                            {selectedImpactQuery.data.days_remaining ?? '\u2014'}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Budget burn */}
                    {selectedCampaign.budget_chf != null && selectedCampaign.budget_chf > 0 && (
                      <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
                        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                          <span>{t('campaign.budget_used') || 'Budget used'}</span>
                          <span>{Math.round(selectedImpactQuery.data.budget_utilization * 100)}%</span>
                        </div>
                        <div className="mt-1 h-2 rounded-full bg-gray-200 dark:bg-gray-600">
                          <div
                            className="h-2 rounded-full bg-blue-500"
                            style={{
                              width: `${Math.min(100, Math.round(selectedImpactQuery.data.budget_utilization * 100))}%`,
                            }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Estimated completion */}
                    {selectedImpactQuery.data.estimated_completion_date && (
                      <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                        <Calendar className="h-4 w-4" />
                        <span>{t('campaign.estimated_completion')}:</span>
                        <span className="font-medium text-gray-900 dark:text-white">
                          {formatDate(selectedImpactQuery.data.estimated_completion_date)}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Timeline bar */}
                <TimelineBar dateStart={selectedCampaign.date_start} dateEnd={selectedCampaign.date_end} />

                <div className="grid grid-cols-2 gap-4 rounded-lg bg-gray-50 p-4 dark:bg-gray-700/50">
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{t('campaign.type')}</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {typeIcons[selectedCampaign.campaign_type]} {t(`campaign_type.${selectedCampaign.campaign_type}`)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{t('campaign.progress')}</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {selectedCampaign.completed_count}/{selectedCampaign.target_count}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{t('campaign.date_start')}</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {formatDate(selectedCampaign.date_start)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{t('campaign.date_end')}</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {formatDate(selectedCampaign.date_end)}
                    </p>
                  </div>
                  {selectedCampaign.budget_chf != null && (
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{t('campaign.budget')}</p>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        CHF {selectedCampaign.budget_chf.toLocaleString()}
                      </p>
                    </div>
                  )}
                  {selectedCampaign.spent_chf != null && (
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{t('campaign.spent')}</p>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        CHF {selectedCampaign.spent_chf.toLocaleString()}
                      </p>
                    </div>
                  )}
                </div>

                {selectedCampaign.notes && (
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{t('campaign.notes')}</p>
                    <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">{selectedCampaign.notes}</p>
                  </div>
                )}

                {/* Progress bar */}
                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500 dark:text-gray-400">{t('campaign.progress')}</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {selectedCampaign.target_count > 0
                        ? Math.round((selectedCampaign.completed_count / selectedCampaign.target_count) * 100)
                        : 0}
                      %
                    </span>
                  </div>
                  <div className="mt-1 h-3 w-full rounded-full bg-gray-200 dark:bg-gray-700">
                    <div
                      className={cn('h-3 rounded-full transition-all', getProgressColor(selectedImpactQuery.data))}
                      style={{
                        width: `${selectedCampaign.target_count > 0 ? (selectedCampaign.completed_count / selectedCampaign.target_count) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-4">
                <TrackingTab campaignId={selectedCampaign.id} t={t} />
              </div>
            )}

            {isAdmin && (
              <div className="mt-6 flex gap-2 border-t border-gray-200 pt-4 dark:border-gray-700">
                <button
                  onClick={() => setShowEditModal(true)}
                  className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  <Edit2 className="h-3.5 w-3.5" />
                  {t('campaign.edit')}
                </button>
                <button
                  onClick={() => {
                    if (confirm(t('campaign.confirm_delete'))) {
                      deleteMutation.mutate(selectedCampaign.id);
                    }
                  }}
                  className="inline-flex items-center gap-1 rounded-lg border border-red-300 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  {t('campaign.delete')}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && selectedCampaign && (
        <EditCampaignModal
          campaign={selectedCampaign}
          onClose={() => setShowEditModal(false)}
          onSave={(data) => editMutation.mutate({ id: selectedCampaign.id, data })}
          t={t}
          types={types}
          statuses={statuses}
        />
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateCampaignModal
          onClose={() => {
            setShowCreateModal(false);
            setCreateInitialData(undefined);
          }}
          onSubmit={(data) => createMutation.mutate(data)}
          t={t}
          types={types}
          initialData={createInitialData}
        />
      )}
    </div>
  );
}
