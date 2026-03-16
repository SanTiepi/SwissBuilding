import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { contradictionsApi, type ContradictionIssue, type ContradictionSummary } from '@/api/contradictions';
import { useTranslation } from '@/i18n';
import { cn, formatDate } from '@/utils/formatters';
import { toast } from '@/store/toastStore';
import { useAuthStore } from '@/store/authStore';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Filter,
  Loader2,
  Search,
  ShieldAlert,
  X,
  ArrowUpDown,
  XCircle,
  Microscope,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CONTRADICTION_TYPES = [
  'conflicting_sample_results',
  'inconsistent_risk_levels',
  'pollutant_type_discrepancy',
  'duplicate_samples',
  'construction_year_conflict',
] as const;

const STATUS_VALUES = ['open', 'investigating', 'resolved', 'dismissed'] as const;

const SEVERITY_VALUES = ['low', 'medium', 'high', 'critical'] as const;

const TYPE_COLORS: Record<string, string> = {
  conflicting_sample_results: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  inconsistent_risk_levels: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  pollutant_type_discrepancy: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  duplicate_samples: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  construction_year_conflict: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
};

const SEVERITY_BADGE: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  low: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
};

const SEVERITY_DOT: Record<string, string> = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-yellow-500',
  low: 'bg-green-500',
};

const STATUS_BADGE: Record<string, string> = {
  open: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  investigating: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  resolved: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  dismissed: 'bg-gray-100 text-gray-600 dark:bg-slate-600 dark:text-slate-300',
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  open: <ShieldAlert className="w-3.5 h-3.5" />,
  investigating: <Microscope className="w-3.5 h-3.5" />,
  resolved: <CheckCircle2 className="w-3.5 h-3.5" />,
  dismissed: <XCircle className="w-3.5 h-3.5" />,
};

const SEVERITY_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

type SortField = 'severity' | 'date' | 'type';
type SortDir = 'asc' | 'desc';

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SummaryCards({ summary, issues }: { summary: ContradictionSummary; issues: ContradictionIssue[] }) {
  const { t } = useTranslation();

  const bySeverity = useMemo(() => {
    const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const i of issues) counts[i.severity] = (counts[i.severity] || 0) + 1;
    return counts;
  }, [issues]);

  const resolutionRate = summary.total > 0 ? Math.round((summary.resolved / summary.total) * 100) : 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {/* By Type */}
      <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-4">
        <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">{t('contradiction.by_type')}</p>
        <div className="flex flex-wrap gap-1">
          {CONTRADICTION_TYPES.map((tp) => {
            const count = summary.by_type[tp] ?? 0;
            if (count === 0) return null;
            return (
              <span
                key={tp}
                className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs', TYPE_COLORS[tp])}
              >
                {t(`contradiction.type.${tp}`)} <span className="font-bold">{count}</span>
              </span>
            );
          })}
          {summary.total === 0 && <span className="text-xs text-gray-400 dark:text-slate-500">{t('common.none')}</span>}
        </div>
      </div>

      {/* By Severity */}
      <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-4">
        <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">{t('contradiction.by_severity')}</p>
        <div className="space-y-1">
          {SEVERITY_VALUES.map((sev) => {
            const count = bySeverity[sev] ?? 0;
            if (count === 0) return null;
            return (
              <div key={sev} className="flex items-center gap-2">
                <span className={cn('w-2 h-2 rounded-full', SEVERITY_DOT[sev])} />
                <span className="text-xs text-gray-700 dark:text-slate-200 capitalize">
                  {t(`contradiction.severity.${sev}`)}
                </span>
                <span className="text-xs font-bold text-gray-900 dark:text-white">{count}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Resolution Rate */}
      <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-4">
        <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">
          {t('contradiction.resolution_rate')}
        </p>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{resolutionRate}%</p>
        <div className="h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden mt-2">
          <div
            className={cn(
              'h-full rounded-full transition-all',
              resolutionRate >= 80 ? 'bg-green-500' : resolutionRate >= 50 ? 'bg-yellow-500' : 'bg-red-500',
            )}
            style={{ width: `${resolutionRate}%` }}
          />
        </div>
      </div>

      {/* Open vs Resolved */}
      <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-4">
        <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">
          {t('contradiction.open_vs_resolved')}
        </p>
        <div className="flex items-baseline gap-3">
          <div>
            <p className="text-xl font-bold text-red-600 dark:text-red-400">{summary.unresolved}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('contradiction.open_label')}</p>
          </div>
          <div>
            <p className="text-xl font-bold text-green-600 dark:text-green-400">{summary.resolved}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('contradiction.resolved_label')}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ContradictionDetail({
  issue,
  buildingId,
  onClose,
}: {
  issue: ContradictionIssue;
  buildingId: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [selectedAction, setSelectedAction] = useState<'resolve' | 'dismiss' | 'investigate' | null>(null);

  const updateMutation = useMutation({
    mutationFn: (data: { status: string; resolution_notes?: string; resolved_at?: string; resolved_by?: string }) =>
      contradictionsApi.update(buildingId, issue.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contradictions'] });
      queryClient.invalidateQueries({ queryKey: ['contradiction-issues'] });
      toast(t('contradiction.update_success'));
      onClose();
    },
    onError: (err: any) => {
      toast(err?.response?.data?.detail || err?.message || t('app.error'));
    },
  });

  const handleAction = (action: 'resolve' | 'dismiss' | 'investigate') => {
    if (action === 'investigate') {
      updateMutation.mutate({ status: 'investigating' });
      return;
    }
    const status = action === 'resolve' ? 'resolved' : 'dismissed';
    updateMutation.mutate({
      status,
      resolution_notes: resolutionNotes || undefined,
      resolved_at: new Date().toISOString(),
      resolved_by: user?.id,
    });
  };

  const fieldName = issue.field_name || 'unknown';
  const isTerminal = issue.status === 'resolved' || issue.status === 'dismissed';

  return (
    <div className="border border-gray-200 dark:border-slate-600 rounded-xl p-5 bg-white dark:bg-slate-800 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', TYPE_COLORS[fieldName])}>
              {t(`contradiction.type.${fieldName}`)}
            </span>
            <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', SEVERITY_BADGE[issue.severity])}>
              {t(`contradiction.severity.${issue.severity}`)}
            </span>
            <span
              className={cn(
                'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                STATUS_BADGE[issue.status],
              )}
            >
              {STATUS_ICON[issue.status]}
              {t(`contradiction.status.${issue.status}`)}
            </span>
          </div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{issue.description}</h4>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Visual Diff / Conflicting Data */}
      <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-4 space-y-3">
        <h5 className="text-xs font-semibold uppercase text-gray-500 dark:text-slate-400">
          {t('contradiction.conflicting_data')}
        </h5>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 border border-red-200 dark:border-red-800/40">
            <p className="text-xs font-medium text-red-600 dark:text-red-400 mb-1">{t('contradiction.side_a')}</p>
            <p className="text-sm text-gray-800 dark:text-slate-200">{issue.description}</p>
            {issue.entity_type && (
              <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">
                {t('contradiction.entity')}: {issue.entity_type}
                {issue.entity_id ? ` (${issue.entity_id.slice(0, 8)}...)` : ''}
              </p>
            )}
          </div>
          <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 border border-amber-200 dark:border-amber-800/40">
            <p className="text-xs font-medium text-amber-600 dark:text-amber-400 mb-1">
              {t('contradiction.suggestion_label')}
            </p>
            <p className="text-sm text-gray-800 dark:text-slate-200">
              {issue.suggestion || t('contradiction.no_suggestion')}
            </p>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-slate-400">
        <div className="flex items-center gap-1">
          <Clock className="w-3.5 h-3.5" />
          <span>
            {t('contradiction.detected_at')}: {formatDate(issue.created_at)}
          </span>
        </div>
        {issue.resolved_at && (
          <div className="flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
            <span>
              {t('contradiction.resolved_at')}: {formatDate(issue.resolved_at)}
            </span>
          </div>
        )}
      </div>

      {/* Resolution Notes (if already resolved) */}
      {issue.resolution_notes && (
        <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 border border-green-200 dark:border-green-800/40">
          <p className="text-xs font-medium text-green-600 dark:text-green-400 mb-1">
            {t('contradiction.resolution_notes')}
          </p>
          <p className="text-sm text-gray-800 dark:text-slate-200">{issue.resolution_notes}</p>
        </div>
      )}

      {/* Resolution Workflow */}
      {!isTerminal && (
        <div className="border-t border-gray-200 dark:border-slate-600 pt-4 space-y-3">
          <h5 className="text-xs font-semibold uppercase text-gray-500 dark:text-slate-400">
            {t('contradiction.resolution_workflow')}
          </h5>

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-2">
            {issue.status === 'open' && (
              <button
                onClick={() => {
                  setSelectedAction(null);
                  handleAction('investigate');
                }}
                disabled={updateMutation.isPending}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                  'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
                  'hover:bg-blue-200 dark:hover:bg-blue-900/50',
                  'disabled:opacity-50',
                )}
              >
                <Microscope className="w-3.5 h-3.5" />
                {t('contradiction.action_investigate')}
              </button>
            )}
            <button
              onClick={() => setSelectedAction('resolve')}
              disabled={updateMutation.isPending}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                selectedAction === 'resolve'
                  ? 'bg-green-500 text-white'
                  : 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50',
                'disabled:opacity-50',
              )}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              {t('contradiction.action_resolve')}
            </button>
            <button
              onClick={() => setSelectedAction('dismiss')}
              disabled={updateMutation.isPending}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                selectedAction === 'dismiss'
                  ? 'bg-gray-500 text-white'
                  : 'bg-gray-100 dark:bg-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-500',
                'disabled:opacity-50',
              )}
            >
              <XCircle className="w-3.5 h-3.5" />
              {t('contradiction.action_dismiss')}
            </button>
          </div>

          {/* Resolution Form */}
          {(selectedAction === 'resolve' || selectedAction === 'dismiss') && (
            <div className="space-y-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-slate-200">
                {selectedAction === 'resolve'
                  ? t('contradiction.resolve_notes_label')
                  : t('contradiction.dismiss_reason_label')}
              </label>
              <textarea
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                rows={3}
                className={cn(
                  'w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 text-sm',
                  'bg-white dark:bg-slate-700 text-gray-900 dark:text-white',
                  'focus:ring-2 focus:ring-red-500 focus:border-transparent',
                  'placeholder:text-gray-400 dark:placeholder:text-slate-500',
                )}
                placeholder={
                  selectedAction === 'resolve'
                    ? t('contradiction.resolve_notes_placeholder')
                    : t('contradiction.dismiss_reason_placeholder')
                }
              />
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleAction(selectedAction)}
                  disabled={updateMutation.isPending}
                  className={cn(
                    'flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-colors',
                    selectedAction === 'resolve'
                      ? 'bg-green-600 hover:bg-green-700 text-white'
                      : 'bg-gray-600 hover:bg-gray-700 text-white',
                    'disabled:opacity-50',
                  )}
                >
                  {updateMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {selectedAction === 'resolve'
                    ? t('contradiction.confirm_resolve')
                    : t('contradiction.confirm_dismiss')}
                </button>
                <button
                  onClick={() => {
                    setSelectedAction(null);
                    setResolutionNotes('');
                  }}
                  className="px-3 py-2 text-xs text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
                >
                  {t('common.cancel')}
                </button>
              </div>
            </div>
          )}

          {/* Impact Preview */}
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 border border-blue-200 dark:border-blue-800/40">
            <p className="text-xs font-medium text-blue-600 dark:text-blue-400 mb-1">
              {t('contradiction.impact_preview')}
            </p>
            <p className="text-xs text-gray-600 dark:text-slate-300">
              {t('contradiction.impact_description', {
                type: t(`contradiction.type.${fieldName}`),
              })}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

export function ContradictionPanel({ buildingId }: { buildingId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  // State
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [filterSeverity, setFilterSeverity] = useState<string>('');
  const [sortField, setSortField] = useState<SortField>('severity');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [showFilters, setShowFilters] = useState(false);

  // Queries
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['contradictions', 'summary', buildingId],
    queryFn: () => contradictionsApi.summary(buildingId),
    enabled: !!buildingId,
  });

  const {
    data: issuesData,
    isLoading: issuesLoading,
    isError: issuesError,
  } = useQuery({
    queryKey: ['contradiction-issues', buildingId, filterType, filterStatus, filterSeverity],
    queryFn: () =>
      contradictionsApi.list(buildingId, {
        size: 100,
        ...(filterType ? { field_name: filterType } : {}),
        ...(filterStatus ? { status: filterStatus } : {}),
        ...(filterSeverity ? { severity: filterSeverity } : {}),
      }),
    enabled: !!buildingId,
  });

  const detectMutation = useMutation({
    mutationFn: () => contradictionsApi.detect(buildingId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['contradictions'] });
      queryClient.invalidateQueries({ queryKey: ['contradiction-issues'] });
      toast(
        data.length > 0 ? t('contradiction.scan_found', { count: String(data.length) }) : t('contradiction.scan_none'),
      );
    },
    onError: (err: any) => {
      toast(err?.response?.data?.detail || err?.message || t('app.error'));
    },
  });

  // Sort issues
  const sortedIssues = useMemo(() => {
    const items = [...(issuesData?.items ?? [])];
    items.sort((a, b) => {
      let cmp = 0;
      if (sortField === 'severity') {
        cmp = (SEVERITY_ORDER[a.severity] ?? 99) - (SEVERITY_ORDER[b.severity] ?? 99);
      } else if (sortField === 'date') {
        cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      } else if (sortField === 'type') {
        cmp = (a.field_name || '').localeCompare(b.field_name || '');
      }
      return sortDir === 'desc' ? -cmp : cmp;
    });
    return items;
  }, [issuesData, sortField, sortDir]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const isLoading = summaryLoading || issuesLoading;

  const hasActiveFilters = filterType || filterStatus || filterSeverity;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{t('contradiction.title')}</h2>
          {summary && summary.total > 0 && (
            <span
              className={cn(
                'inline-flex items-center justify-center min-w-[1.5rem] h-6 px-2 rounded-full text-xs font-bold',
                summary.unresolved > 0
                  ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'
                  : 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
              )}
            >
              {summary.total}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters((v) => !v)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
              showFilters || hasActiveFilters
                ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                : 'bg-gray-100 dark:bg-slate-600 text-gray-700 dark:text-slate-200 hover:bg-gray-200 dark:hover:bg-slate-500',
            )}
          >
            <Filter className="w-3.5 h-3.5" />
            {t('common.filter')}
          </button>
          <button
            onClick={() => detectMutation.mutate()}
            disabled={detectMutation.isPending}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
              'bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-slate-200',
              'hover:bg-gray-300 dark:hover:bg-slate-500',
              'disabled:opacity-50 disabled:cursor-not-allowed',
            )}
          >
            {detectMutation.isPending ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                {t('contradiction.scanning')}
              </>
            ) : (
              <>
                <Search className="w-3.5 h-3.5" />
                {t('contradiction.scan')}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && !summaryLoading && <SummaryCards summary={summary} issues={issuesData?.items ?? []} />}

      {/* Filters */}
      {showFilters && (
        <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-4 flex flex-wrap gap-3 items-end">
          {/* Type filter */}
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              {t('contradiction.filter_type')}
            </label>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="text-xs rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-2 py-1.5"
            >
              <option value="">{t('common.all')}</option>
              {CONTRADICTION_TYPES.map((tp) => (
                <option key={tp} value={tp}>
                  {t(`contradiction.type.${tp}`)}
                </option>
              ))}
            </select>
          </div>
          {/* Status filter */}
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              {t('contradiction.filter_status')}
            </label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="text-xs rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-2 py-1.5"
            >
              <option value="">{t('common.all')}</option>
              {STATUS_VALUES.map((s) => (
                <option key={s} value={s}>
                  {t(`contradiction.status.${s}`)}
                </option>
              ))}
            </select>
          </div>
          {/* Severity filter */}
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              {t('contradiction.filter_severity')}
            </label>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="text-xs rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-2 py-1.5"
            >
              <option value="">{t('common.all')}</option>
              {SEVERITY_VALUES.map((s) => (
                <option key={s} value={s}>
                  {t(`contradiction.severity.${s}`)}
                </option>
              ))}
            </select>
          </div>
          {hasActiveFilters && (
            <button
              onClick={() => {
                setFilterType('');
                setFilterStatus('');
                setFilterSeverity('');
              }}
              className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400 hover:underline"
            >
              <X className="w-3 h-3" />
              {t('common.clear_filters')}
            </button>
          )}
        </div>
      )}

      {/* Sort Bar */}
      <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-slate-400">
        <span>{t('contradiction.sort_by')}:</span>
        {(['severity', 'date', 'type'] as SortField[]).map((field) => (
          <button
            key={field}
            onClick={() => toggleSort(field)}
            className={cn(
              'flex items-center gap-1 px-2 py-1 rounded transition-colors',
              sortField === field
                ? 'bg-gray-200 dark:bg-slate-600 text-gray-900 dark:text-white font-medium'
                : 'hover:bg-gray-100 dark:hover:bg-slate-700',
            )}
          >
            {t(`contradiction.sort_${field}`)}
            {sortField === field && <ArrowUpDown className={cn('w-3 h-3', sortDir === 'desc' && 'rotate-180')} />}
          </button>
        ))}
        <span className="ml-auto text-xs text-gray-400 dark:text-slate-500">
          {sortedIssues.length} {t('contradiction.items_label')}
        </span>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400 dark:text-slate-500" />
        </div>
      )}

      {/* Error */}
      {issuesError && (
        <div className="text-center py-8">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-sm text-red-600 dark:text-red-400">{t('app.loading_error')}</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !issuesError && sortedIssues.length === 0 && (
        <div className="text-center py-12">
          <CheckCircle2 className="w-10 h-10 text-green-400 mx-auto mb-3" />
          <p className="text-sm text-gray-600 dark:text-slate-300">
            {hasActiveFilters ? t('contradiction.no_matches') : t('contradiction.none')}
          </p>
          {!hasActiveFilters && (
            <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">{t('contradiction.none_hint')}</p>
          )}
        </div>
      )}

      {/* Issue List */}
      {!isLoading && !issuesError && sortedIssues.length > 0 && (
        <div className="space-y-2">
          {sortedIssues.map((issue) => {
            const isExpanded = expandedId === issue.id;
            const fieldName = issue.field_name || 'unknown';

            return (
              <div key={issue.id}>
                {/* Row */}
                <button
                  onClick={() => setExpandedId(isExpanded ? null : issue.id)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left transition-colors',
                    'bg-gray-50 dark:bg-slate-700/50',
                    'hover:bg-gray-100 dark:hover:bg-slate-700',
                    isExpanded && 'ring-2 ring-red-300 dark:ring-red-600',
                  )}
                >
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-gray-400 dark:text-slate-500 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-400 dark:text-slate-500 flex-shrink-0" />
                  )}
                  <span className={cn('w-2 h-2 rounded-full flex-shrink-0', SEVERITY_DOT[issue.severity])} />
                  <span className={cn('px-2 py-0.5 rounded-full text-xs flex-shrink-0', TYPE_COLORS[fieldName])}>
                    {t(`contradiction.type.${fieldName}`)}
                  </span>
                  <span className="flex-1 text-sm text-gray-800 dark:text-slate-200 truncate">{issue.description}</span>
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs flex-shrink-0',
                      STATUS_BADGE[issue.status],
                    )}
                  >
                    {STATUS_ICON[issue.status]}
                    {t(`contradiction.status.${issue.status}`)}
                  </span>
                  <span className="text-xs text-gray-400 dark:text-slate-500 flex-shrink-0 hidden sm:block">
                    {formatDate(issue.created_at)}
                  </span>
                </button>

                {/* Expanded Detail */}
                {isExpanded && (
                  <div className="mt-2 ml-6">
                    <ContradictionDetail issue={issue} buildingId={buildingId} onClose={() => setExpandedId(null)} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
