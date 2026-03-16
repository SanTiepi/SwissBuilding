import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { buildingsApi } from '@/api/buildings';
import { dataQualityApi } from '@/api/dataQuality';
import type { DataQualityIssue } from '@/api/dataQuality';
import { changeSignalsApi } from '@/api/changeSignals';
import type { ChangeSignal } from '@/api/changeSignals';
import { portfolioApi } from '@/api/portfolio';
import { cn } from '@/utils/formatters';
import { AsyncStateWrapper } from '@/components/AsyncStateWrapper';
import { DashboardSkeleton } from '@/components/Skeleton';
import {
  ShieldAlert,
  AlertTriangle,
  Bell,
  Clock,
  Building2,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Eye,
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
  ExternalLink,
} from 'lucide-react';
import { formatDistanceToNow, differenceInDays } from 'date-fns';

// -- Severity config --
const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low'] as const;
const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-yellow-500',
  low: 'bg-blue-400',
};
const SEVERITY_TEXT: Record<string, string> = {
  critical: 'text-red-700 dark:text-red-300',
  high: 'text-orange-700 dark:text-orange-300',
  medium: 'text-yellow-700 dark:text-yellow-300',
  low: 'text-blue-700 dark:text-blue-300',
};
const SEVERITY_BG: Record<string, string> = {
  critical: 'bg-red-100 dark:bg-red-900/30',
  high: 'bg-orange-100 dark:bg-orange-900/30',
  medium: 'bg-yellow-100 dark:bg-yellow-900/30',
  low: 'bg-blue-100 dark:bg-blue-900/30',
};

const STATUS_BADGE: Record<string, { bg: string; text: string }> = {
  open: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-700 dark:text-red-300' },
  acknowledged: { bg: 'bg-yellow-100 dark:bg-yellow-900/30', text: 'text-yellow-700 dark:text-yellow-300' },
  resolved: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-300' },
};

const SIGNAL_TYPE_COLORS: Record<string, string> = {
  diagnostic_completed: 'bg-green-500',
  new_positive_sample: 'bg-red-500',
  intervention_completed: 'bg-blue-500',
  document_uploaded: 'bg-purple-500',
  risk_level_change: 'bg-orange-500',
  diagnostic_expiring: 'bg-yellow-500',
  action_overdue: 'bg-red-400',
};

// -- Freshness helpers --
function freshnessColor(daysSince: number): string {
  if (daysSince <= 30) return 'text-green-600 dark:text-green-400';
  if (daysSince <= 90) return 'text-yellow-600 dark:text-yellow-400';
  if (daysSince <= 365) return 'text-orange-600 dark:text-orange-400';
  return 'text-red-600 dark:text-red-400';
}

function freshnessBg(daysSince: number): string {
  if (daysSince <= 30) return 'bg-green-50 dark:bg-green-900/20';
  if (daysSince <= 90) return 'bg-yellow-50 dark:bg-yellow-900/20';
  if (daysSince <= 365) return 'bg-orange-50 dark:bg-orange-900/20';
  return 'bg-red-50 dark:bg-red-900/20';
}

export default function DataQuality() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  // State
  const [severityFilter, setSeverityFilter] = useState<string | undefined>(undefined);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [buildingFilter, setBuildingFilter] = useState<string | undefined>(undefined);
  const [expandedIssue, setExpandedIssue] = useState<string | null>(null);

  // -- Fetch buildings --
  const { data: buildingsData, isLoading: buildingsLoading } = useQuery({
    queryKey: ['buildings', 'all-for-dq'],
    queryFn: () => buildingsApi.list({ size: 200 }),
  });
  const buildings = useMemo(() => buildingsData?.items ?? [], [buildingsData]);
  const buildingMap = useMemo(() => {
    const map: Record<string, { address: string; city: string; updated_at: string }> = {};
    for (const b of buildings) {
      map[b.id] = { address: b.address, city: b.city, updated_at: b.updated_at };
    }
    return map;
  }, [buildings]);

  // -- Fetch data quality issues for all buildings (or filtered building) --
  const buildingIds = useMemo(
    () => (buildingFilter ? [buildingFilter] : buildings.map((b) => b.id)),
    [buildingFilter, buildings],
  );
  const issueQueries = useQuery({
    queryKey: ['data-quality-issues', buildingIds, severityFilter, statusFilter],
    queryFn: async () => {
      if (buildingIds.length === 0) return [];
      const targetIds = buildingIds.slice(0, 50); // limit to avoid too many requests
      const results = await Promise.allSettled(
        targetIds.map((id) =>
          dataQualityApi.list(id, {
            severity: severityFilter,
            status: statusFilter,
            size: 100,
          }),
        ),
      );
      const allIssues: DataQualityIssue[] = [];
      for (const r of results) {
        if (r.status === 'fulfilled') {
          allIssues.push(...r.value.items);
        }
      }
      return allIssues;
    },
    enabled: buildings.length > 0,
  });
  const issues = useMemo(() => issueQueries.data ?? [], [issueQueries.data]);

  // -- Change signals (portfolio-level) --
  const {
    data: signalsData,
    isLoading: signalsLoading,
    isError: signalsError,
  } = useQuery({
    queryKey: ['portfolio', 'change-signals', 'dq-page'],
    queryFn: () => changeSignalsApi.listPortfolio(),
  });
  const signals = useMemo(() => signalsData?.items ?? [], [signalsData]);

  // -- Portfolio health score --
  const { data: healthScore } = useQuery({
    queryKey: ['portfolio', 'health-score'],
    queryFn: portfolioApi.getHealthScore,
  });

  // -- Mutations --
  const acknowledgeIssue = useMutation({
    mutationFn: ({ buildingId, issueId }: { buildingId: string; issueId: string }) =>
      dataQualityApi.update(buildingId, issueId, { status: 'acknowledged' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['data-quality-issues'] }),
  });

  const resolveIssue = useMutation({
    mutationFn: ({ buildingId, issueId, notes }: { buildingId: string; issueId: string; notes: string }) =>
      dataQualityApi.update(buildingId, issueId, { status: 'resolved', resolution_notes: notes }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['data-quality-issues'] }),
  });

  // -- Computed aggregates --
  const issueBySeverity = useMemo(() => {
    const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const issue of issues) {
      counts[issue.severity] = (counts[issue.severity] || 0) + 1;
    }
    return counts;
  }, [issues]);

  const openIssues = issues.filter((i) => i.status !== 'resolved');

  const signalsThisWeek = useMemo(() => {
    const now = new Date();
    return signals.filter((s) => differenceInDays(now, new Date(s.detected_at)) <= 7).length;
  }, [signals]);

  const buildingsWithIssues = useMemo(() => {
    const set = new Set(openIssues.map((i) => i.building_id));
    return set.size;
  }, [openIssues]);

  const staleBuildings = useMemo(() => {
    const now = new Date();
    return buildings.filter((b) => differenceInDays(now, new Date(b.updated_at)) > 90).length;
  }, [buildings]);

  // -- Freshness data --
  const freshnessData = useMemo(() => {
    const now = new Date();
    return buildings
      .map((b) => ({
        id: b.id,
        address: b.address,
        city: b.city,
        daysSinceUpdate: differenceInDays(now, new Date(b.updated_at)),
      }))
      .sort((a, b) => b.daysSinceUpdate - a.daysSinceUpdate)
      .slice(0, 10);
  }, [buildings]);

  // -- Score display --
  const overallScore = healthScore?.score ?? null;
  const scorePct = overallScore != null ? Math.round(overallScore * 100) : null;
  const scoreColor =
    scorePct != null
      ? scorePct >= 70
        ? 'text-green-600 dark:text-green-400'
        : scorePct >= 40
          ? 'text-yellow-600 dark:text-yellow-400'
          : 'text-red-600 dark:text-red-400'
      : '';
  const scoreTrend = openIssues.length === 0 ? 'improving' : openIssues.length > 10 ? 'declining' : 'stable';

  if (buildingsLoading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <ShieldAlert className="w-7 h-7 text-red-500" />
          {t('data_quality.title')}
        </h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('data_quality.subtitle')}</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Quality Score */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm">
          <p className="text-sm text-gray-500 dark:text-slate-400">{t('data_quality.overall_score')}</p>
          <div className="flex items-center gap-2 mt-1">
            <span className={cn('text-3xl font-bold', scoreColor)}>{scorePct != null ? `${scorePct}%` : '--'}</span>
            {scoreTrend === 'improving' && <TrendingUp className="w-5 h-5 text-green-500" />}
            {scoreTrend === 'declining' && <TrendingDown className="w-5 h-5 text-red-500" />}
            {scoreTrend === 'stable' && <Minus className="w-5 h-5 text-gray-400" />}
          </div>
        </div>

        {/* Issues by severity */}
        {SEVERITY_ORDER.map((sev) => (
          <div
            key={sev}
            className={cn(
              'bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm cursor-pointer hover:shadow-md transition-shadow',
              severityFilter === sev && 'ring-2 ring-red-400 dark:ring-red-600',
            )}
            onClick={() => setSeverityFilter(severityFilter === sev ? undefined : sev)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') setSeverityFilter(severityFilter === sev ? undefined : sev);
            }}
          >
            <div className="flex items-center gap-2">
              <span className={cn('w-3 h-3 rounded-full', SEVERITY_COLORS[sev])} />
              <p className="text-sm text-gray-500 dark:text-slate-400">{t(`data_quality.severity_${sev}`)}</p>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{issueBySeverity[sev] || 0}</p>
          </div>
        ))}
      </div>

      {/* Secondary summary row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <Bell className="w-4 h-4 text-blue-500" />
            <p className="text-sm text-gray-500 dark:text-slate-400">{t('data_quality.signals_this_week')}</p>
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{signalsThisWeek}</p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-orange-500" />
            <p className="text-sm text-gray-500 dark:text-slate-400">{t('data_quality.buildings_needing_attention')}</p>
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{buildingsWithIssues}</p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-red-500" />
            <p className="text-sm text-gray-500 dark:text-slate-400">{t('data_quality.stale_data_count')}</p>
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{staleBuildings}</p>
        </div>
      </div>

      {/* Main content: Issues + Signals */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Issues Panel (2/3 width) */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm">
          <div className="p-6 border-b border-gray-200 dark:border-slate-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-orange-500" />
              {t('data_quality.issues_title')}
              <span className="text-sm font-normal text-gray-400 dark:text-slate-500 ml-1">({openIssues.length})</span>
            </h2>

            {/* Filters */}
            <div className="flex flex-wrap gap-2">
              {/* Severity pills */}
              <div className="flex gap-1">
                {['all', ...SEVERITY_ORDER].map((sev) => {
                  const isActive = sev === 'all' ? !severityFilter : severityFilter === sev;
                  return (
                    <button
                      key={sev}
                      onClick={() => setSeverityFilter(sev === 'all' ? undefined : sev)}
                      className={cn(
                        'px-3 py-1 text-xs font-medium rounded-full transition-colors',
                        isActive
                          ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                          : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-400 hover:bg-gray-200 dark:hover:bg-slate-600',
                      )}
                    >
                      {sev === 'all' ? t('data_quality.filter_all') : t(`data_quality.severity_${sev}`)}
                    </button>
                  );
                })}
              </div>

              {/* Status pills */}
              <div className="flex gap-1 ml-2">
                {['all', 'open', 'acknowledged', 'resolved'].map((st) => {
                  const isActive = st === 'all' ? !statusFilter : statusFilter === st;
                  return (
                    <button
                      key={st}
                      onClick={() => setStatusFilter(st === 'all' ? undefined : st)}
                      className={cn(
                        'px-3 py-1 text-xs font-medium rounded-full transition-colors',
                        isActive
                          ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                          : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-400 hover:bg-gray-200 dark:hover:bg-slate-600',
                      )}
                    >
                      {st === 'all' ? t('data_quality.filter_all') : t(`data_quality.status_${st}`)}
                    </button>
                  );
                })}
              </div>

              {/* Building filter */}
              <select
                value={buildingFilter || ''}
                onChange={(e) => setBuildingFilter(e.target.value || undefined)}
                className="ml-auto px-3 py-1 text-xs rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-700 dark:text-slate-200"
              >
                <option value="">{t('data_quality.all_buildings')}</option>
                {buildings.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.address}, {b.city}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Issues list */}
          <div className="divide-y divide-gray-100 dark:divide-slate-700 max-h-[600px] overflow-y-auto">
            <AsyncStateWrapper
              isLoading={issueQueries.isLoading}
              isError={issueQueries.isError}
              data={issues}
              variant="inline"
              emptyMessage={t('data_quality.no_issues')}
            >
              {issues.map((issue) => (
                <IssueRow
                  key={issue.id}
                  issue={issue}
                  buildingLabel={
                    buildingMap[issue.building_id]
                      ? `${buildingMap[issue.building_id].address}, ${buildingMap[issue.building_id].city}`
                      : issue.building_id.substring(0, 8)
                  }
                  expanded={expandedIssue === issue.id}
                  onToggle={() => setExpandedIssue(expandedIssue === issue.id ? null : issue.id)}
                  onAcknowledge={() => acknowledgeIssue.mutate({ buildingId: issue.building_id, issueId: issue.id })}
                  onResolve={(notes) =>
                    resolveIssue.mutate({ buildingId: issue.building_id, issueId: issue.id, notes })
                  }
                  t={t}
                />
              ))}
            </AsyncStateWrapper>
          </div>
        </div>

        {/* Change Signals Feed (1/3 width) */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm">
          <div className="p-6 border-b border-gray-200 dark:border-slate-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-500" />
              {t('data_quality.signals_title')}
            </h2>
          </div>
          <div className="max-h-[600px] overflow-y-auto">
            <AsyncStateWrapper
              isLoading={signalsLoading}
              isError={signalsError}
              data={signals}
              variant="inline"
              emptyMessage={t('data_quality.no_signals')}
            >
              <ul className="divide-y divide-gray-100 dark:divide-slate-700">
                {signals.slice(0, 30).map((signal: ChangeSignal) => (
                  <li key={signal.id} className="px-6 py-3 hover:bg-gray-50 dark:hover:bg-slate-700/50">
                    <div className="flex items-start gap-3">
                      <span
                        className={cn(
                          'w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0',
                          SIGNAL_TYPE_COLORS[signal.signal_type] ?? 'bg-gray-400',
                        )}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-gray-700 dark:text-slate-200 truncate">{signal.title}</p>
                        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                          <span
                            className={cn(
                              'inline-block px-2 py-0.5 text-[10px] font-medium rounded-full',
                              'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-400',
                            )}
                          >
                            {t(`data_quality.signal_type_${signal.signal_type}`) ||
                              signal.signal_type.replace(/_/g, ' ')}
                          </span>
                          {signal.severity && (
                            <span
                              className={cn(
                                'inline-block px-2 py-0.5 text-[10px] font-medium rounded-full',
                                SEVERITY_BG[signal.severity] ?? 'bg-gray-100 dark:bg-slate-700',
                                SEVERITY_TEXT[signal.severity] ?? 'text-gray-600 dark:text-slate-400',
                              )}
                            >
                              {signal.severity}
                            </span>
                          )}
                          <Link
                            to={`/buildings/${signal.building_id}`}
                            className="text-[10px] text-red-600 hover:text-red-700 dark:text-red-400 flex items-center gap-0.5"
                          >
                            <ExternalLink className="w-2.5 h-2.5" />
                            {buildingMap[signal.building_id]?.address?.substring(0, 25) ||
                              signal.building_id.substring(0, 8)}
                          </Link>
                        </div>
                        <span className="text-[10px] text-gray-400 dark:text-slate-500 mt-0.5 block">
                          {formatDistanceToNow(new Date(signal.detected_at), { addSuffix: true })}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </AsyncStateWrapper>
          </div>
        </div>
      </div>

      {/* Freshness Indicators */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
          <Clock className="w-5 h-5 text-amber-500" />
          {t('data_quality.freshness_title')}
        </h2>
        <p className="text-sm text-gray-500 dark:text-slate-400 mb-4">{t('data_quality.freshness_description')}</p>

        {freshnessData.length === 0 ? (
          <p className="text-sm text-gray-400 dark:text-slate-500">{t('app.no_data')}</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {freshnessData.map((item) => (
              <Link
                key={item.id}
                to={`/buildings/${item.id}`}
                className={cn(
                  'rounded-lg p-3 border border-gray-100 dark:border-slate-700 hover:shadow-md transition-shadow',
                  freshnessBg(item.daysSinceUpdate),
                )}
              >
                <p className="text-sm font-medium text-gray-800 dark:text-slate-200 truncate">{item.address}</p>
                <p className="text-xs text-gray-500 dark:text-slate-400 truncate">{item.city}</p>
                <p className={cn('text-sm font-bold mt-1', freshnessColor(item.daysSinceUpdate))}>
                  {item.daysSinceUpdate} {t('data_quality.days_ago')}
                </p>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// -- Issue Row Component --
function IssueRow({
  issue,
  buildingLabel,
  expanded,
  onToggle,
  onAcknowledge,
  onResolve,
  t,
}: {
  issue: DataQualityIssue;
  buildingLabel: string;
  expanded: boolean;
  onToggle: () => void;
  onAcknowledge: () => void;
  onResolve: (notes: string) => void;
  t: (key: string) => string;
}) {
  const [resolutionNotes, setResolutionNotes] = useState('');
  const statusStyle = STATUS_BADGE[issue.status] ?? STATUS_BADGE.open;

  return (
    <div className="px-6 py-3">
      <div
        className="flex items-start gap-3 cursor-pointer"
        onClick={onToggle}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') onToggle();
        }}
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 mt-1 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 mt-1 text-gray-400 flex-shrink-0" />
        )}
        <span className={cn('w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0', SEVERITY_COLORS[issue.severity])} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-medium text-gray-800 dark:text-slate-200">{issue.description}</p>
            <span
              className={cn(
                'inline-block px-2 py-0.5 text-[10px] font-medium rounded-full',
                statusStyle.bg,
                statusStyle.text,
              )}
            >
              {t(`data_quality.status_${issue.status}`)}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-500 dark:text-slate-400">
            <Link
              to={`/buildings/${issue.building_id}`}
              className="text-red-600 hover:text-red-700 dark:text-red-400 flex items-center gap-0.5"
              onClick={(e) => e.stopPropagation()}
            >
              <Building2 className="w-3 h-3" />
              {buildingLabel}
            </Link>
            <span className="font-mono">{issue.issue_type}</span>
            {issue.detected_by && <span>{issue.detected_by}</span>}
            <span>{formatDistanceToNow(new Date(issue.created_at), { addSuffix: true })}</span>
          </div>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="ml-10 mt-3 space-y-3">
          {/* Suggestion */}
          {issue.suggestion && (
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/50 rounded-lg px-3 py-2">
              <p className="text-xs font-medium text-blue-700 dark:text-blue-300 mb-0.5">
                {t('data_quality.suggestion')}
              </p>
              <p className="text-sm text-blue-800 dark:text-blue-200">{issue.suggestion}</p>
            </div>
          )}

          {/* Entity info */}
          {issue.entity_type && (
            <div className="text-xs text-gray-500 dark:text-slate-400">
              {t('data_quality.related_entity')}: {issue.entity_type}
              {issue.field_name && ` / ${issue.field_name}`}
            </div>
          )}

          {/* Resolution notes if resolved */}
          {issue.status === 'resolved' && issue.resolution_notes && (
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800/50 rounded-lg px-3 py-2">
              <p className="text-xs font-medium text-green-700 dark:text-green-300 mb-0.5">
                {t('data_quality.resolution_notes')}
              </p>
              <p className="text-sm text-green-800 dark:text-green-200">{issue.resolution_notes}</p>
            </div>
          )}

          {/* Actions */}
          {issue.status !== 'resolved' && (
            <div className="flex items-center gap-2 flex-wrap">
              {issue.status === 'open' && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onAcknowledge();
                  }}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 hover:bg-yellow-200 dark:hover:bg-yellow-900/50 transition-colors"
                >
                  <Eye className="w-3 h-3" />
                  {t('data_quality.acknowledge')}
                </button>
              )}
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <input
                  type="text"
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder={t('data_quality.resolution_notes_placeholder')}
                  className="flex-1 min-w-0 px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-700 dark:text-slate-200"
                  onClick={(e) => e.stopPropagation()}
                />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onResolve(resolutionNotes);
                    setResolutionNotes('');
                  }}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors"
                >
                  <CheckCircle2 className="w-3 h-3" />
                  {t('data_quality.resolve')}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
