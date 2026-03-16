import { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { requalificationApi } from '@/api/requalification';
import type { RequalificationEntry } from '@/api/requalification';
import { cn } from '@/utils/formatters';
import { formatDate } from '@/utils/formatters';
import {
  Camera,
  Wrench,
  AlertTriangle,
  ArrowRightLeft,
  Play,
  X,
  ChevronLeft,
  ChevronRight,
  Filter,
  Columns,
  TrendingUp,
  Clock,
  Activity,
  ArrowDown,
  ArrowUp,
  Minus,
} from 'lucide-react';

// ─── Grade colors ───────────────────────────────────────────────────
const GRADE_COLORS: Record<string, string> = {
  A: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  B: 'bg-lime-100 text-lime-800 dark:bg-lime-900/30 dark:text-lime-400',
  C: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  D: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  E: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  F: 'bg-red-200 text-red-900 dark:bg-red-950/40 dark:text-red-500',
};

const GRADE_ORDER = ['A', 'B', 'C', 'D', 'E', 'F'];

const DOT_COLORS: Record<string, string> = {
  signal: 'border-amber-400 bg-amber-50 dark:border-amber-500 dark:bg-amber-900/30',
  snapshot: 'border-blue-400 bg-blue-50 dark:border-blue-500 dark:bg-blue-900/30',
  grade_change: 'border-purple-400 bg-purple-50 dark:border-purple-500 dark:bg-purple-900/30',
  intervention: 'border-green-400 bg-green-50 dark:border-green-500 dark:bg-green-900/30',
};

const ENTRY_ICONS: Record<string, React.ElementType> = {
  signal: AlertTriangle,
  snapshot: Camera,
  grade_change: ArrowRightLeft,
  intervention: Wrench,
};

type EntryType = RequalificationEntry['entry_type'];
type FilterType = 'all' | EntryType;

// ─── GradeBadge ─────────────────────────────────────────────────────
function GradeBadge({ grade, size = 'sm' }: { grade: string | null; size?: 'sm' | 'lg' }) {
  if (!grade) return <span className="text-gray-400 dark:text-slate-500">--</span>;
  const color = GRADE_COLORS[grade] || 'bg-gray-100 text-gray-800 dark:bg-slate-700 dark:text-slate-300';
  const sizeClass = size === 'lg' ? 'w-10 h-10 text-base' : 'w-6 h-6 text-xs';
  return (
    <span className={cn('inline-flex items-center justify-center rounded-full font-bold', sizeClass, color)}>
      {grade}
    </span>
  );
}

// ─── Grade direction arrow ──────────────────────────────────────────
function GradeArrow({ before, after }: { before: string | null; after: string | null }) {
  if (!before || !after) return <ArrowRightLeft className="w-4 h-4 text-gray-400 dark:text-slate-500" />;
  const bIdx = GRADE_ORDER.indexOf(before);
  const aIdx = GRADE_ORDER.indexOf(after);
  if (bIdx < 0 || aIdx < 0) return <ArrowRightLeft className="w-4 h-4 text-gray-400 dark:text-slate-500" />;
  if (aIdx < bIdx)
    return <ArrowUp className="w-4 h-4 text-green-500" aria-label="improved" data-testid="grade-arrow-up" />;
  if (aIdx > bIdx)
    return <ArrowDown className="w-4 h-4 text-red-500" aria-label="declined" data-testid="grade-arrow-down" />;
  return <Minus className="w-4 h-4 text-gray-400 dark:text-slate-500" aria-label="unchanged" />;
}

// ─── SeverityBadge ──────────────────────────────────────────────────
function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    warning: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    info: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    low: 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
  };
  const color = colors[severity] || colors.info;
  return <span className={cn('px-1.5 py-0.5 text-xs font-medium rounded', color)}>{severity}</span>;
}

// ─── SignalTypeBadge ────────────────────────────────────────────────
function SignalTypeBadge({ signalType }: { signalType: string }) {
  return (
    <span className="px-1.5 py-0.5 text-xs font-medium bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 rounded border border-amber-200 dark:border-amber-800">
      {signalType.replace(/_/g, ' ')}
    </span>
  );
}

// ─── Grade Transition Card ──────────────────────────────────────────
function GradeTransitionCard({ entry, t }: { entry: RequalificationEntry; t: (key: string) => string }) {
  const reason = (entry.metadata?.reason as string) || entry.description;
  const linkedIntervention = entry.metadata?.intervention_id as string | undefined;

  return (
    <div className="bg-purple-50/50 dark:bg-purple-900/10 border border-purple-200 dark:border-purple-800/40 rounded-lg p-4 space-y-3">
      {/* Before / After */}
      <div className="flex items-center gap-4">
        <div className="flex flex-col items-center gap-1">
          <span className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400">
            {t('requalification.grade_before') || 'Before'}
          </span>
          <GradeBadge grade={entry.grade_before} size="lg" />
        </div>
        <div className="flex flex-col items-center">
          <GradeArrow before={entry.grade_before} after={entry.grade_after} />
        </div>
        <div className="flex flex-col items-center gap-1">
          <span className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400">
            {t('requalification.grade_after') || 'After'}
          </span>
          <GradeBadge grade={entry.grade_after} size="lg" />
        </div>
        <div className="ml-auto text-xs text-gray-400 dark:text-slate-500">{formatDate(entry.timestamp)}</div>
      </div>

      {/* Reason */}
      {reason && (
        <div className="text-xs text-gray-600 dark:text-slate-300">
          <span className="font-medium text-gray-700 dark:text-slate-200">
            {t('requalification.reason') || 'Reason'}:
          </span>{' '}
          {reason}
        </div>
      )}

      {/* Linked intervention */}
      {linkedIntervention && (
        <div className="text-xs text-gray-500 dark:text-slate-400 flex items-center gap-1">
          <Wrench className="w-3 h-3" />
          <span className="font-medium">{t('requalification.linked_intervention') || 'Linked intervention'}:</span>{' '}
          <span className="font-mono">{linkedIntervention.slice(0, 8)}</span>
        </div>
      )}
    </div>
  );
}

// ─── Snapshot Comparison Panel ──────────────────────────────────────
function SnapshotComparisonPanel({ snapshots, t }: { snapshots: RequalificationEntry[]; t: (key: string) => string }) {
  const [leftIdx, setLeftIdx] = useState(0);
  const [rightIdx, setRightIdx] = useState(Math.min(1, snapshots.length - 1));

  if (snapshots.length < 2) {
    return (
      <div className="text-center py-4 text-sm text-gray-500 dark:text-slate-400">
        {t('requalification.select_snapshots') || 'Select two snapshots to compare'}
      </div>
    );
  }

  const leftSnap = snapshots[leftIdx];
  const rightSnap = snapshots[rightIdx];
  const leftMeta = (leftSnap?.metadata || {}) as Record<string, unknown>;
  const rightMeta = (rightSnap?.metadata || {}) as Record<string, unknown>;

  const comparisonFields = ['trust', 'readiness', 'pollutant_status', 'grade'] as const;

  return (
    <div className="bg-white dark:bg-slate-800 border border-blue-200 dark:border-blue-800/40 rounded-lg p-4 space-y-4">
      <h4 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
        <Columns className="w-4 h-4 text-blue-600" />
        {t('requalification.snapshot_comparison') || 'Snapshot Comparison'}
      </h4>

      {/* Snapshot selectors */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-xs text-gray-500 dark:text-slate-400 block mb-1">
            {t('requalification.snapshot_left') || 'Snapshot A'}
          </label>
          <select
            value={leftIdx}
            onChange={(e) => setLeftIdx(Number(e.target.value))}
            className="w-full text-xs border border-gray-200 dark:border-slate-600 rounded px-2 py-1.5 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
          >
            {snapshots.map((s, i) => (
              <option key={i} value={i}>
                {formatDate(s.timestamp)} - {s.title}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 dark:text-slate-400 block mb-1">
            {t('requalification.snapshot_right') || 'Snapshot B'}
          </label>
          <select
            value={rightIdx}
            onChange={(e) => setRightIdx(Number(e.target.value))}
            className="w-full text-xs border border-gray-200 dark:border-slate-600 rounded px-2 py-1.5 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
          >
            {snapshots.map((s, i) => (
              <option key={i} value={i}>
                {formatDate(s.timestamp)} - {s.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Side-by-side comparison */}
      <div className="divide-y divide-gray-100 dark:divide-slate-700">
        {comparisonFields.map((field) => {
          const leftVal = leftMeta[field] as string | number | undefined;
          const rightVal = rightMeta[field] as string | number | undefined;
          const changed = String(leftVal ?? '') !== String(rightVal ?? '');
          return (
            <div key={field} className="flex items-center py-2 gap-2">
              <span className="text-xs font-medium text-gray-700 dark:text-slate-300 w-28 shrink-0">
                {t(`requalification.${field}`) || field}
              </span>
              <span className="text-xs text-gray-600 dark:text-slate-400 flex-1 text-center font-mono">
                {String(leftVal ?? '--')}
              </span>
              <span
                className={cn(
                  'text-xs text-center flex-1 font-mono',
                  changed ? 'text-amber-700 dark:text-amber-400 font-semibold' : 'text-gray-600 dark:text-slate-400',
                )}
              >
                {String(rightVal ?? '--')}
              </span>
              <span
                className={cn(
                  'text-[10px] w-16 text-center rounded px-1 py-0.5',
                  changed
                    ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
                    : 'bg-gray-50 dark:bg-slate-700 text-gray-400 dark:text-slate-500',
                )}
              >
                {changed
                  ? t('requalification.field_changed') || 'Changed'
                  : t('requalification.field_unchanged') || 'Unchanged'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Timeline Entry Row ─────────────────────────────────────────────
function TimelineEntryRow({
  entry,
  t,
  isHighlighted,
}: {
  entry: RequalificationEntry;
  t: (key: string) => string;
  isHighlighted: boolean;
}) {
  const IconComponent = ENTRY_ICONS[entry.entry_type] || AlertTriangle;
  const dotColor = DOT_COLORS[entry.entry_type] || DOT_COLORS.signal;
  const typeLabel = t(`requalification.${entry.entry_type}`) || entry.entry_type;

  return (
    <li
      className={cn(
        'relative pl-10 transition-all duration-300',
        isHighlighted && 'ring-2 ring-purple-400 dark:ring-purple-500 rounded-lg',
      )}
    >
      {/* Timeline dot */}
      <div
        className={cn(
          'absolute left-2 top-1.5 w-5 h-5 rounded-full border-2 flex items-center justify-center z-10',
          dotColor,
          isHighlighted && 'ring-2 ring-purple-300 dark:ring-purple-600',
        )}
      >
        <IconComponent className="w-3 h-3" />
      </div>

      <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium text-gray-900 dark:text-white">{entry.title}</span>
              <span className="px-1.5 py-0.5 text-xs font-medium bg-gray-100 dark:bg-slate-600 text-gray-600 dark:text-slate-300 rounded">
                {typeLabel}
              </span>
              {entry.severity && <SeverityBadge severity={entry.severity} />}
              {entry.entry_type === 'signal' && entry.signal_type && <SignalTypeBadge signalType={entry.signal_type} />}
            </div>

            {entry.description && <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{entry.description}</p>}

            {/* Grade transition card for grade_change entries */}
            {entry.entry_type === 'grade_change' && (entry.grade_before || entry.grade_after) && (
              <div className="mt-2">
                <GradeTransitionCard entry={entry} t={t} />
              </div>
            )}

            {/* Snapshot marker */}
            {entry.entry_type === 'snapshot' && (
              <div className="mt-2 flex items-center gap-2 text-xs text-blue-600 dark:text-blue-400">
                <Camera className="w-3 h-3" />
                <span>{formatDate(entry.timestamp)}</span>
              </div>
            )}

            {/* Intervention completion marker */}
            {entry.entry_type === 'intervention' && (
              <div className="mt-2 flex items-center gap-2 text-xs text-green-600 dark:text-green-400">
                <Wrench className="w-3 h-3" />
                <span>{formatDate(entry.timestamp)}</span>
                {entry.metadata && 'status' in entry.metadata && entry.metadata.status != null && (
                  <span className="px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded">
                    {String(entry.metadata.status)}
                  </span>
                )}
              </div>
            )}
          </div>
          <span className="text-xs text-gray-400 dark:text-slate-500 whitespace-nowrap">
            {formatDate(entry.timestamp)}
          </span>
        </div>
      </div>
    </li>
  );
}

// ─── Summary Header ─────────────────────────────────────────────────
function SummaryHeader({
  currentGrade,
  totalTransitions,
  lastRequalDate,
  activeSignals,
  t,
}: {
  currentGrade: string | null;
  totalTransitions: number;
  lastRequalDate: string | null;
  activeSignals: number;
  t: (key: string) => string;
}) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {/* Current grade */}
      <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3 flex flex-col items-center gap-1">
        <span className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400">
          {t('requalification.current_grade') || 'Current grade'}
        </span>
        <GradeBadge grade={currentGrade} size="lg" />
      </div>

      {/* Total transitions */}
      <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3 flex flex-col items-center gap-1">
        <span className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400">
          {t('requalification.total_transitions') || 'Transitions'}
        </span>
        <div className="flex items-center gap-1.5">
          <TrendingUp className="w-4 h-4 text-purple-500" />
          <span className="text-lg font-bold text-gray-900 dark:text-white">{totalTransitions}</span>
        </div>
      </div>

      {/* Last requalification */}
      <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3 flex flex-col items-center gap-1">
        <span className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400">
          {t('requalification.last_requalification') || 'Last requalification'}
        </span>
        <div className="flex items-center gap-1.5">
          <Clock className="w-4 h-4 text-blue-500" />
          <span className="text-xs font-medium text-gray-900 dark:text-white">
            {lastRequalDate ? formatDate(lastRequalDate) : t('requalification.never') || 'Never'}
          </span>
        </div>
      </div>

      {/* Active signals */}
      <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3 flex flex-col items-center gap-1">
        <span className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400">
          {t('requalification.active_signals') || 'Active signals'}
        </span>
        <div className="flex items-center gap-1.5">
          <Activity className="w-4 h-4 text-amber-500" />
          <span className="text-lg font-bold text-gray-900 dark:text-white">{activeSignals}</span>
        </div>
      </div>
    </div>
  );
}

// ─── Filter Bar ─────────────────────────────────────────────────────
function FilterBar({
  activeFilter,
  onFilterChange,
  entryCounts,
  t,
}: {
  activeFilter: FilterType;
  onFilterChange: (f: FilterType) => void;
  entryCounts: Record<string, number>;
  t: (key: string) => string;
}) {
  const filters: { key: FilterType; label: string }[] = [
    { key: 'all', label: t('requalification.filter_all') || 'All' },
    { key: 'grade_change', label: t('requalification.filter_grade_change') || 'Grades' },
    { key: 'signal', label: t('requalification.filter_signal') || 'Signals' },
    { key: 'snapshot', label: t('requalification.filter_snapshot') || 'Snapshots' },
    { key: 'intervention', label: t('requalification.filter_intervention') || 'Interventions' },
  ];

  return (
    <div className="flex items-center gap-1.5 flex-wrap" role="group" aria-label="Filter timeline events">
      <Filter className="w-3.5 h-3.5 text-gray-400 dark:text-slate-500" />
      {filters.map((f) => {
        const count = f.key === 'all' ? Object.values(entryCounts).reduce((a, b) => a + b, 0) : entryCounts[f.key] || 0;
        return (
          <button
            key={f.key}
            onClick={() => onFilterChange(f.key)}
            className={cn(
              'px-2 py-1 text-xs rounded-full transition-colors flex items-center gap-1',
              activeFilter === f.key
                ? 'bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 font-medium'
                : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-400 hover:bg-gray-200 dark:hover:bg-slate-600',
            )}
          >
            {f.label}
            <span className="text-[10px] opacity-70">({count})</span>
          </button>
        );
      })}
    </div>
  );
}

// ─── Replay Controls ────────────────────────────────────────────────
function ReplayControls({
  currentStep,
  totalSteps,
  onPrev,
  onNext,
  onExit,
  t,
}: {
  currentStep: number;
  totalSteps: number;
  onPrev: () => void;
  onNext: () => void;
  onExit: () => void;
  t: (key: string) => string;
}) {
  return (
    <div className="flex items-center gap-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800/40 rounded-lg px-4 py-2">
      <button
        onClick={onExit}
        className="p-1 rounded hover:bg-purple-100 dark:hover:bg-purple-800/30 text-purple-600 dark:text-purple-400"
        title={t('requalification.replay_exit') || 'Exit'}
      >
        <X className="w-4 h-4" />
      </button>
      <button
        onClick={onPrev}
        disabled={currentStep <= 0}
        className="p-1 rounded hover:bg-purple-100 dark:hover:bg-purple-800/30 text-purple-600 dark:text-purple-400 disabled:opacity-30"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>
      <span className="text-xs font-medium text-purple-700 dark:text-purple-300 min-w-[80px] text-center">
        {t('requalification.replay_step') || 'Step'} {currentStep + 1} {t('requalification.replay_of') || 'of'}{' '}
        {totalSteps}
      </span>
      <button
        onClick={onNext}
        disabled={currentStep >= totalSteps - 1}
        className="p-1 rounded hover:bg-purple-100 dark:hover:bg-purple-800/30 text-purple-600 dark:text-purple-400 disabled:opacity-30"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────
interface RequalificationTimelineProps {
  buildingId: string;
}

export function RequalificationTimeline({ buildingId }: RequalificationTimelineProps) {
  const { t } = useTranslation();
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');
  const [replayMode, setReplayMode] = useState(false);
  const [replayStep, setReplayStep] = useState(0);
  const [showComparison, setShowComparison] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['requalification-timeline', buildingId],
    queryFn: () => requalificationApi.getTimeline(buildingId),
    enabled: !!buildingId,
  });

  const entries = useMemo(() => data?.entries ?? [], [data?.entries]);

  // Compute counts per type
  const entryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const e of entries) {
      counts[e.entry_type] = (counts[e.entry_type] || 0) + 1;
    }
    return counts;
  }, [entries]);

  // Filter entries
  const filteredEntries = useMemo(
    () => (activeFilter === 'all' ? entries : entries.filter((e) => e.entry_type === activeFilter)),
    [entries, activeFilter],
  );

  // Summary stats
  const totalTransitions = entryCounts['grade_change'] || 0;
  const activeSignals = entryCounts['signal'] || 0;
  const lastGradeChange = useMemo(() => [...entries].reverse().find((e) => e.entry_type === 'grade_change'), [entries]);
  const lastRequalDate = lastGradeChange?.timestamp ?? null;

  // Snapshot entries for comparison
  const snapshotEntries = useMemo(() => entries.filter((e) => e.entry_type === 'snapshot'), [entries]);

  // Replay handlers
  const handleEnterReplay = useCallback(() => {
    setReplayMode(true);
    setReplayStep(0);
  }, []);

  const handleExitReplay = useCallback(() => {
    setReplayMode(false);
    setReplayStep(0);
  }, []);

  const handlePrevStep = useCallback(() => setReplayStep((s) => Math.max(0, s - 1)), []);
  const handleNextStep = useCallback(
    () => setReplayStep((s) => Math.min(filteredEntries.length - 1, s + 1)),
    [filteredEntries.length],
  );

  // ─── Loading ────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
        <div className="space-y-3">
          <div className="h-5 w-48 bg-gray-200 dark:bg-slate-700 rounded animate-pulse" />
          <div className="grid grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-16 bg-gray-100 dark:bg-slate-700 rounded-lg animate-pulse" />
            ))}
          </div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex gap-3">
                <div className="w-5 h-5 rounded-full bg-gray-200 dark:bg-slate-700 animate-pulse shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-3/4 bg-gray-200 dark:bg-slate-700 rounded animate-pulse" />
                  <div className="h-3 w-1/2 bg-gray-100 dark:bg-slate-600 rounded animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ─── Error ──────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
        <p className="text-red-600 dark:text-red-400">{t('app.error') || 'An error occurred'}</p>
      </div>
    );
  }

  // ─── Render ─────────────────────────────────────────────────────
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <ArrowRightLeft className="w-5 h-5 text-purple-600" />
          {t('requalification.timeline_title') || 'Requalification Timeline'}
        </h3>
        <div className="flex items-center gap-2">
          {/* Replay toggle */}
          {filteredEntries.length > 0 && !replayMode && (
            <button
              onClick={handleEnterReplay}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-lg hover:bg-purple-200 dark:hover:bg-purple-800/40 transition-colors"
            >
              <Play className="w-3.5 h-3.5" />
              {t('requalification.replay') || 'Replay'}
            </button>
          )}
          {/* Snapshot comparison toggle */}
          {snapshotEntries.length >= 2 && !replayMode && (
            <button
              onClick={() => setShowComparison((v) => !v)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                showComparison
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                  : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-400 hover:bg-gray-200 dark:hover:bg-slate-600',
              )}
            >
              <Columns className="w-3.5 h-3.5" />
              {t('requalification.compare_snapshots') || 'Compare'}
            </button>
          )}
        </div>
      </div>

      {/* Summary header */}
      <SummaryHeader
        currentGrade={data?.current_grade ?? null}
        totalTransitions={totalTransitions}
        lastRequalDate={lastRequalDate}
        activeSignals={activeSignals}
        t={t}
      />

      {/* Empty state */}
      {entries.length === 0 && (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <ArrowRightLeft className="w-8 h-8 text-gray-300 dark:text-slate-600 mb-2" />
          <p className="text-sm text-gray-500 dark:text-slate-400">
            {t('requalification.empty') || 'No requalification events yet'}
          </p>
        </div>
      )}

      {/* Filter bar + Replay controls */}
      {entries.length > 0 && (
        <div className="flex items-center justify-between flex-wrap gap-2">
          <FilterBar activeFilter={activeFilter} onFilterChange={setActiveFilter} entryCounts={entryCounts} t={t} />
          {replayMode && (
            <ReplayControls
              currentStep={replayStep}
              totalSteps={filteredEntries.length}
              onPrev={handlePrevStep}
              onNext={handleNextStep}
              onExit={handleExitReplay}
              t={t}
            />
          )}
        </div>
      )}

      {/* Snapshot comparison panel */}
      {showComparison && !replayMode && snapshotEntries.length >= 2 && (
        <SnapshotComparisonPanel snapshots={snapshotEntries} t={t} />
      )}

      {/* Timeline */}
      {filteredEntries.length > 0 && (
        <div className="relative">
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-slate-600" />
          <ul className="space-y-3">
            {replayMode
              ? filteredEntries
                  .filter((_, idx) => idx <= replayStep)
                  .map((entry, idx) => (
                    <TimelineEntryRow
                      key={`${entry.timestamp}-${idx}`}
                      entry={entry}
                      t={t}
                      isHighlighted={idx === replayStep}
                    />
                  ))
              : filteredEntries.map((entry, idx) => (
                  <TimelineEntryRow key={`${entry.timestamp}-${idx}`} entry={entry} t={t} isHighlighted={false} />
                ))}
          </ul>
        </div>
      )}

      {/* Filtered empty state */}
      {entries.length > 0 && filteredEntries.length === 0 && (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <Filter className="w-6 h-6 text-gray-300 dark:text-slate-600 mb-2" />
          <p className="text-sm text-gray-500 dark:text-slate-400">
            {t('requalification.empty') || 'No requalification events yet'}
          </p>
        </div>
      )}
    </div>
  );
}
