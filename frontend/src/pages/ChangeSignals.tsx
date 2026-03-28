/**
 * MIGRATION: DEPRECATE
 * This page is scheduled for removal. Do not add new features.
 * Its functionality is covered by BuildingDetail activity tab + building_changes API.
 * Not routed in App.tsx — orphaned page file. Frozen per ADR-004.
 */
// COMPATIBILITY SURFACE — ChangeSignal reads are frozen per ADR-004.
// New change consumers should use building_changes API.

import { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { changeSignalsApi } from '@/api/changeSignals';
import type { ChangeSignal } from '@/api/changeSignals';
import { cn } from '@/utils/formatters';
import { AsyncStateWrapper } from '@/components/AsyncStateWrapper';
import { DashboardSkeleton } from '@/components/Skeleton';
import {
  Bell,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Eye,
  ExternalLink,
  Stethoscope,
  RefreshCw,
  FileText,
  FlaskConical,
  Wrench,
  Shield,
  ShieldCheck,
  BarChart3,
  Calendar,
  Filter,
  CheckSquare,
  Square,
  ArrowLeft,
} from 'lucide-react';
import { formatDistanceToNow, differenceInDays, isWithinInterval, subDays } from 'date-fns';

// -- Signal type config --
const SIGNAL_TYPES = [
  'new_diagnostic',
  'status_change',
  'document_added',
  'sample_result',
  'intervention_complete',
  'trust_change',
  'readiness_change',
] as const;

const SIGNAL_TYPE_ICON: Record<string, typeof Bell> = {
  new_diagnostic: Stethoscope,
  status_change: RefreshCw,
  document_added: FileText,
  sample_result: FlaskConical,
  intervention_complete: Wrench,
  trust_change: Shield,
  readiness_change: ShieldCheck,
};

const SIGNAL_TYPE_COLOR: Record<string, { dot: string; bg: string; text: string }> = {
  new_diagnostic: {
    dot: 'bg-green-500',
    bg: 'bg-green-100 dark:bg-green-900/30',
    text: 'text-green-700 dark:text-green-300',
  },
  status_change: {
    dot: 'bg-blue-500',
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-700 dark:text-blue-300',
  },
  document_added: {
    dot: 'bg-purple-500',
    bg: 'bg-purple-100 dark:bg-purple-900/30',
    text: 'text-purple-700 dark:text-purple-300',
  },
  sample_result: {
    dot: 'bg-red-500',
    bg: 'bg-red-100 dark:bg-red-900/30',
    text: 'text-red-700 dark:text-red-300',
  },
  intervention_complete: {
    dot: 'bg-teal-500',
    bg: 'bg-teal-100 dark:bg-teal-900/30',
    text: 'text-teal-700 dark:text-teal-300',
  },
  trust_change: {
    dot: 'bg-amber-500',
    bg: 'bg-amber-100 dark:bg-amber-900/30',
    text: 'text-amber-700 dark:text-amber-300',
  },
  readiness_change: {
    dot: 'bg-indigo-500',
    bg: 'bg-indigo-100 dark:bg-indigo-900/30',
    text: 'text-indigo-700 dark:text-indigo-300',
  },
};

const SEVERITY_COLORS: Record<string, { dot: string; bg: string; text: string }> = {
  critical: {
    dot: 'bg-red-500',
    bg: 'bg-red-100 dark:bg-red-900/30',
    text: 'text-red-700 dark:text-red-300',
  },
  warning: {
    dot: 'bg-orange-500',
    bg: 'bg-orange-100 dark:bg-orange-900/30',
    text: 'text-orange-700 dark:text-orange-300',
  },
  info: {
    dot: 'bg-blue-400',
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-700 dark:text-blue-300',
  },
};

const STATUS_BADGE: Record<string, { bg: string; text: string }> = {
  active: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-700 dark:text-red-300' },
  acknowledged: { bg: 'bg-yellow-100 dark:bg-yellow-900/30', text: 'text-yellow-700 dark:text-yellow-300' },
  resolved: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-300' },
};

const DATE_RANGES = ['all', 'today', 'week', 'month'] as const;

function getEntityLink(signal: ChangeSignal): string | null {
  if (!signal.entity_type || !signal.entity_id) return null;
  const buildingBase = `/buildings/${signal.building_id}`;
  switch (signal.entity_type) {
    case 'diagnostic':
      return `${buildingBase}/diagnostics/${signal.entity_id}`;
    case 'document':
      return `${buildingBase}?tab=documents`;
    case 'intervention':
      return `${buildingBase}/interventions`;
    case 'sample':
      return `${buildingBase}/diagnostics`;
    case 'trust_score':
      return buildingBase;
    case 'readiness':
      return `${buildingBase}/readiness`;
    default:
      return buildingBase;
  }
}

export default function ChangeSignals() {
  const { t } = useTranslation();
  const { buildingId } = useParams<{ buildingId: string }>();
  const queryClient = useQueryClient();

  // Filters
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined);
  const [severityFilter, setSeverityFilter] = useState<string | undefined>(undefined);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [dateRange, setDateRange] = useState<string>('all');
  const [expandedSignal, setExpandedSignal] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Fetch signals
  const {
    data: signalsData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['building-change-signals-full', buildingId, typeFilter, severityFilter, statusFilter],
    queryFn: () =>
      changeSignalsApi.list(buildingId!, {
        size: 200,
        signal_type: typeFilter,
        severity: severityFilter,
        status: statusFilter,
      }),
    enabled: !!buildingId,
  });

  const allSignals = useMemo(() => signalsData?.items ?? [], [signalsData]);

  // Apply client-side date range filter
  const signals = useMemo(() => {
    if (dateRange === 'all') return allSignals;
    const now = new Date();
    const daysBack = dateRange === 'today' ? 1 : dateRange === 'week' ? 7 : 30;
    const start = subDays(now, daysBack);
    return allSignals.filter((s) => isWithinInterval(new Date(s.detected_at), { start, end: now }));
  }, [allSignals, dateRange]);

  // Computed aggregates
  const totalSignals = allSignals.length;
  const unacknowledgedCount = allSignals.filter((s) => s.status === 'active').length;
  const signalsThisWeek = useMemo(() => {
    const now = new Date();
    return allSignals.filter((s) => differenceInDays(now, new Date(s.detected_at)) <= 7).length;
  }, [allSignals]);
  const signalsThisMonth = useMemo(() => {
    const now = new Date();
    return allSignals.filter((s) => differenceInDays(now, new Date(s.detected_at)) <= 30).length;
  }, [allSignals]);
  const byType = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const s of allSignals) {
      counts[s.signal_type] = (counts[s.signal_type] || 0) + 1;
    }
    return counts;
  }, [allSignals]);

  // Mutations
  const acknowledgeMutation = useMutation({
    mutationFn: ({ signalId }: { signalId: string }) => changeSignalsApi.acknowledge(buildingId!, signalId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['building-change-signals-full', buildingId] }),
  });

  const bulkAcknowledge = useCallback(async () => {
    if (selectedIds.size === 0) return;
    const promises = Array.from(selectedIds).map((signalId) => changeSignalsApi.acknowledge(buildingId!, signalId));
    await Promise.allSettled(promises);
    setSelectedIds(new Set());
    queryClient.invalidateQueries({ queryKey: ['building-change-signals-full', buildingId] });
  }, [buildingId, selectedIds, queryClient]);

  const toggleSelection = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    const activeSignals = signals.filter((s) => s.status === 'active');
    if (selectedIds.size === activeSignals.length && activeSignals.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(activeSignals.map((s) => s.id)));
    }
  }, [signals, selectedIds]);

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Deprecation banner — migrated to canonical BuildingSignal (2026-03-28, Rail 1) */}
      <div className="rounded-xl border-2 border-amber-400 dark:border-amber-600 bg-amber-50 dark:bg-amber-900/20 p-4">
        <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
          Cette page est obsolete. Les signaux sont disponibles dans Changements du batiment.
        </p>
        <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
          This page reads from the legacy ChangeSignal API and will be retired. Use the Building Changes timeline
          instead.
        </p>
      </div>

      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          to={`/buildings/${buildingId}`}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-500 dark:text-slate-400" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Bell className="w-7 h-7 text-blue-500" />
            {t('change_signal.title')}
          </h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('change_signal.subtitle')}</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm">
          <p className="text-sm text-gray-500 dark:text-slate-400">{t('change_signal.total_signals')}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{totalSignals}</p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm">
          <p className="text-sm text-gray-500 dark:text-slate-400">{t('change_signal.unacknowledged')}</p>
          <p
            className={cn(
              'text-3xl font-bold mt-1',
              unacknowledgedCount > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400',
            )}
          >
            {unacknowledgedCount}
          </p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm">
          <p className="text-sm text-gray-500 dark:text-slate-400">{t('change_signal.this_week')}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{signalsThisWeek}</p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm">
          <p className="text-sm text-gray-500 dark:text-slate-400">{t('change_signal.this_month')}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{signalsThisMonth}</p>
        </div>
      </div>

      {/* Type Distribution */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-gray-500 dark:text-slate-400" />
          {t('change_signal.type_distribution')}
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {SIGNAL_TYPES.map((type) => {
            const count = byType[type] || 0;
            const colors = SIGNAL_TYPE_COLOR[type];
            const Icon = SIGNAL_TYPE_ICON[type] || Bell;
            const isActive = typeFilter === type;
            return (
              <button
                key={type}
                onClick={() => setTypeFilter(isActive ? undefined : type)}
                className={cn(
                  'flex flex-col items-center gap-1 p-3 rounded-lg transition-all text-center',
                  isActive
                    ? `${colors.bg} ring-2 ring-offset-1 ring-current ${colors.text}`
                    : 'hover:bg-gray-50 dark:hover:bg-slate-700/50',
                )}
              >
                <Icon className={cn('w-5 h-5', isActive ? colors.text : 'text-gray-400 dark:text-slate-500')} />
                <span className="text-lg font-bold text-gray-900 dark:text-white">{count}</span>
                <span className="text-[10px] text-gray-500 dark:text-slate-400 leading-tight">
                  {t(`change_signal.type_${type}`) || type.replace(/_/g, ' ')}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Filter Bar + Bulk Actions */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm">
        <div className="p-4 border-b border-gray-200 dark:border-slate-700">
          <div className="flex items-center gap-2 mb-3">
            <Filter className="w-4 h-4 text-gray-500 dark:text-slate-400" />
            <span className="text-sm font-medium text-gray-700 dark:text-slate-300">{t('change_signal.filters')}</span>
          </div>
          <div className="flex flex-wrap gap-3">
            {/* Severity filter */}
            <div className="flex gap-1">
              {['all', 'critical', 'warning', 'info'].map((sev) => {
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
                    {sev === 'all' ? t('change_signal.filter_all') : t(`change_signal.severity_${sev}`)}
                  </button>
                );
              })}
            </div>

            {/* Status filter */}
            <div className="flex gap-1">
              {['all', 'active', 'acknowledged', 'resolved'].map((st) => {
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
                    {st === 'all' ? t('change_signal.filter_all') : t(`change_signal.status_${st}`)}
                  </button>
                );
              })}
            </div>

            {/* Date range */}
            <div className="flex gap-1 ml-auto">
              <Calendar className="w-4 h-4 text-gray-400 dark:text-slate-500 mt-1" />
              {DATE_RANGES.map((range) => {
                const isActive = dateRange === range;
                return (
                  <button
                    key={range}
                    onClick={() => setDateRange(range)}
                    className={cn(
                      'px-3 py-1 text-xs font-medium rounded-full transition-colors',
                      isActive
                        ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                        : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-400 hover:bg-gray-200 dark:hover:bg-slate-600',
                    )}
                  >
                    {t(`change_signal.range_${range}`)}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Bulk actions */}
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-3 mt-3 pt-3 border-t border-gray-100 dark:border-slate-700">
              <span className="text-xs text-gray-500 dark:text-slate-400">
                {selectedIds.size} {t('change_signal.selected')}
              </span>
              <button
                onClick={bulkAcknowledge}
                className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 hover:bg-yellow-200 dark:hover:bg-yellow-900/50 transition-colors"
              >
                <CheckCircle2 className="w-3 h-3" />
                {t('change_signal.bulk_acknowledge')}
              </button>
              <button
                onClick={() => setSelectedIds(new Set())}
                className="text-xs text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300"
              >
                {t('change_signal.clear_selection')}
              </button>
            </div>
          )}
        </div>

        {/* Signal list header */}
        <div className="px-6 py-2 bg-gray-50 dark:bg-slate-700/30 border-b border-gray-100 dark:border-slate-700 flex items-center gap-3">
          <button
            onClick={toggleSelectAll}
            className="text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300"
            title={t('change_signal.select_all')}
          >
            {selectedIds.size > 0 && selectedIds.size === signals.filter((s) => s.status === 'active').length ? (
              <CheckSquare className="w-4 h-4" />
            ) : (
              <Square className="w-4 h-4" />
            )}
          </button>
          <span className="text-xs font-medium text-gray-500 dark:text-slate-400 flex-1">
            {signals.length} {t('change_signal.signals_shown')}
          </span>
        </div>

        {/* Signals list */}
        <div className="divide-y divide-gray-100 dark:divide-slate-700 max-h-[600px] overflow-y-auto">
          <AsyncStateWrapper
            isLoading={isLoading}
            isError={isError}
            data={signals}
            variant="inline"
            emptyMessage={t('change_signal.none')}
          >
            {signals.map((signal) => (
              <SignalRow
                key={signal.id}
                signal={signal}
                expanded={expandedSignal === signal.id}
                selected={selectedIds.has(signal.id)}
                onToggle={() => setExpandedSignal(expandedSignal === signal.id ? null : signal.id)}
                onSelect={() => toggleSelection(signal.id)}
                onAcknowledge={() => acknowledgeMutation.mutate({ signalId: signal.id })}
                t={t}
              />
            ))}
          </AsyncStateWrapper>
        </div>
      </div>
    </div>
  );
}

// -- Signal Row Component --
function SignalRow({
  signal,
  expanded,
  selected,
  onToggle,
  onSelect,
  onAcknowledge,
  t,
}: {
  signal: ChangeSignal;
  expanded: boolean;
  selected: boolean;
  onToggle: () => void;
  onSelect: () => void;
  onAcknowledge: () => void;
  t: (key: string) => string;
}) {
  const typeColors = SIGNAL_TYPE_COLOR[signal.signal_type] ?? {
    dot: 'bg-gray-400',
    bg: 'bg-gray-100 dark:bg-slate-700',
    text: 'text-gray-600 dark:text-slate-400',
  };
  const sevColors = SEVERITY_COLORS[signal.severity] ?? SEVERITY_COLORS.info;
  const statusStyle = STATUS_BADGE[signal.status] ?? STATUS_BADGE.active;
  const Icon = SIGNAL_TYPE_ICON[signal.signal_type] || Bell;
  const entityLink = getEntityLink(signal);

  return (
    <div className={cn('px-6 py-3', expanded && 'bg-gray-50/50 dark:bg-slate-700/20')}>
      <div className="flex items-start gap-3">
        {/* Checkbox */}
        {signal.status === 'active' && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelect();
            }}
            className="mt-1 text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300"
          >
            {selected ? <CheckSquare className="w-4 h-4 text-blue-500" /> : <Square className="w-4 h-4" />}
          </button>
        )}
        {signal.status !== 'active' && <div className="w-4" />}

        {/* Icon */}
        <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5', typeColors.bg)}>
          <Icon className={cn('w-4 h-4', typeColors.text)} />
        </div>

        {/* Expand toggle */}
        <button onClick={onToggle} className="mt-1 text-gray-400 dark:text-slate-500 flex-shrink-0">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        {/* Content */}
        <div
          className="min-w-0 flex-1 cursor-pointer"
          onClick={onToggle}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') onToggle();
          }}
        >
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-medium text-gray-800 dark:text-slate-200">{signal.title}</p>
            {/* Status badge */}
            <span
              className={cn(
                'inline-block px-2 py-0.5 text-[10px] font-medium rounded-full',
                statusStyle.bg,
                statusStyle.text,
              )}
            >
              {t(`change_signal.status_${signal.status}`)}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {/* Type badge */}
            <span
              className={cn(
                'inline-block px-2 py-0.5 text-[10px] font-medium rounded-full',
                typeColors.bg,
                typeColors.text,
              )}
            >
              {t(`change_signal.type_${signal.signal_type}`) || signal.signal_type.replace(/_/g, ' ')}
            </span>
            {/* Severity badge */}
            <span
              className={cn(
                'inline-block px-2 py-0.5 text-[10px] font-medium rounded-full',
                sevColors.bg,
                sevColors.text,
              )}
            >
              {t(`change_signal.severity_${signal.severity}`) || signal.severity}
            </span>
            {/* Relative time */}
            <span className="text-[10px] text-gray-400 dark:text-slate-500">
              {formatDistanceToNow(new Date(signal.detected_at), { addSuffix: true })}
            </span>
            {/* Entity link */}
            {entityLink && (
              <Link
                to={entityLink}
                onClick={(e) => e.stopPropagation()}
                className="text-[10px] text-red-600 hover:text-red-700 dark:text-red-400 flex items-center gap-0.5"
              >
                <ExternalLink className="w-2.5 h-2.5" />
                {signal.entity_type
                  ? t(`change_signal.entity_${signal.entity_type}`) || signal.entity_type.replace(/_/g, ' ')
                  : t('change_signal.view_entity')}
              </Link>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {signal.status === 'active' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAcknowledge();
              }}
              className="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-lg bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 hover:bg-yellow-200 dark:hover:bg-yellow-900/50 transition-colors"
              title={t('change_signal.acknowledge')}
            >
              <Eye className="w-3 h-3" />
            </button>
          )}
          {signal.status === 'acknowledged' && <CheckCircle2 className="w-4 h-4 text-yellow-500" />}
          {signal.status === 'resolved' && <CheckCircle2 className="w-4 h-4 text-green-500" />}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="ml-16 mt-3 space-y-3">
          {/* Description */}
          {signal.description && (
            <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2">
              <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-0.5">
                {t('change_signal.description')}
              </p>
              <p className="text-sm text-gray-700 dark:text-slate-200">{signal.description}</p>
            </div>
          )}

          {/* Source */}
          {signal.source && (
            <div className="text-xs text-gray-500 dark:text-slate-400">
              {t('change_signal.source')}: <span className="font-mono">{signal.source}</span>
            </div>
          )}

          {/* Affected entity */}
          {signal.entity_type && (
            <div className="text-xs text-gray-500 dark:text-slate-400 flex items-center gap-2">
              <span>
                {t('change_signal.affected_entity')}:{' '}
                {t(`change_signal.entity_${signal.entity_type}`) || signal.entity_type.replace(/_/g, ' ')}
              </span>
              {signal.entity_id && (
                <span className="font-mono text-[10px] bg-gray-100 dark:bg-slate-700 px-1.5 py-0.5 rounded">
                  {signal.entity_id.substring(0, 8)}
                </span>
              )}
              {entityLink && (
                <Link
                  to={entityLink}
                  className="text-red-600 hover:text-red-700 dark:text-red-400 flex items-center gap-0.5"
                >
                  <ExternalLink className="w-3 h-3" />
                  {t('change_signal.go_to_entity')}
                </Link>
              )}
            </div>
          )}

          {/* Metadata */}
          {signal.metadata_json && Object.keys(signal.metadata_json).length > 0 && (
            <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2">
              <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                {t('change_signal.metadata')}
              </p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                {Object.entries(signal.metadata_json).map(([key, value]) => (
                  <div key={key} className="text-xs">
                    <span className="text-gray-500 dark:text-slate-400 font-mono">{key}:</span>{' '}
                    <span className="text-gray-700 dark:text-slate-200">
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Acknowledgment info */}
          {signal.acknowledged_at && (
            <div className="text-xs text-gray-500 dark:text-slate-400 flex items-center gap-2">
              <CheckCircle2 className="w-3 h-3 text-yellow-500" />
              {t('change_signal.acknowledged_at')}:{' '}
              {formatDistanceToNow(new Date(signal.acknowledged_at), { addSuffix: true })}
            </div>
          )}

          {/* Timeline position */}
          <div className="text-xs text-gray-400 dark:text-slate-500">
            {t('change_signal.detected_at')}: {new Date(signal.detected_at).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  );
}
