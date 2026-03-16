import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { snapshotsApi } from '@/api/snapshots';
import type { BuildingSnapshot, SnapshotComparison } from '@/api/snapshots';
import { formatDate, formatDateTime, cn } from '@/utils/formatters';
import { toast } from '@/store/toastStore';
import {
  Camera,
  GitCompareArrows,
  Loader2,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Eye,
  X,
  ChevronDown,
  ChevronUp,
  Clock,
  Zap,
  FileText,
  Shield,
  Activity,
  TrendingUp,
  AlertTriangle,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  B: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  C: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  D: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  E: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  F: 'bg-red-200 text-red-900 dark:bg-red-950/40 dark:text-red-500',
};

const TRIGGER_ICONS: Record<string, typeof Camera> = {
  manual: Camera,
  automatic: Zap,
  intervention: Activity,
};

function triggerLabel(trigger: string | null, snapshotType: string): string {
  if (trigger) return trigger;
  return snapshotType;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function GradeBadge({ grade, size = 'sm' }: { grade: string | null; size?: 'sm' | 'lg' }) {
  if (!grade) return <span className="text-gray-400 dark:text-slate-500">--</span>;
  const color = GRADE_COLORS[grade] || 'bg-gray-100 text-gray-800 dark:bg-slate-700 dark:text-slate-300';
  const sizeClass = size === 'lg' ? 'w-10 h-10 text-lg' : 'w-7 h-7 text-sm';
  return (
    <span className={cn('inline-flex items-center justify-center rounded-full font-bold', sizeClass, color)}>
      {grade}
    </span>
  );
}

function DeltaIndicator({ value, suffix = '' }: { value: number; suffix?: string }) {
  if (value === 0) return <Minus className="w-4 h-4 text-gray-400 dark:text-slate-500" />;
  const isPositive = value > 0;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 text-sm font-medium',
        isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400',
      )}
    >
      {isPositive ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
      {isPositive ? '+' : ''}
      {(value * 100).toFixed(1)}%{suffix}
    </span>
  );
}

function MetricCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: string;
  icon: typeof Camera;
  color?: string;
}) {
  return (
    <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg p-3 text-center">
      <Icon className={cn('w-4 h-4 mx-auto mb-1', color || 'text-gray-500 dark:text-slate-400')} />
      <p className="text-xs text-gray-500 dark:text-slate-400">{label}</p>
      <p className="text-sm font-semibold text-gray-900 dark:text-white mt-0.5">{value}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Snapshot Detail View
// ---------------------------------------------------------------------------

function SnapshotDetailView({
  snapshot,
  onClose,
  t,
}: {
  snapshot: BuildingSnapshot;
  onClose: () => void;
  t: (key: string) => string;
}) {
  const passport = snapshot.passport_state_json as Record<string, unknown> | null;
  const readinessState = snapshot.readiness_state_json as Record<string, unknown> | null;
  const evidenceCounts = snapshot.evidence_counts_json as Record<string, unknown> | null;

  // Extract pollutant data from passport
  const blindspots = passport?.blindspots as Record<string, unknown> | null;
  const pollutantCoverage = blindspots?.coverage_by_pollutant as Record<string, unknown> | null;

  // Extract readiness statuses
  const readinessEntries = readinessState
    ? Object.entries(readinessState).filter(([, v]) => typeof v === 'object' && v !== null)
    : [];

  return (
    <div className="border border-gray-200 dark:border-slate-700 rounded-lg bg-gray-50 dark:bg-slate-900/50 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Eye className="w-4 h-4 text-red-600" />
          {t('time_machine.snapshot_detail') || 'Snapshot Detail'}
        </h4>
        <button onClick={onClose} className="p-1 rounded hover:bg-gray-200 dark:hover:bg-slate-700 transition-colors">
          <X className="w-4 h-4 text-gray-500 dark:text-slate-400" />
        </button>
      </div>

      {/* Header info */}
      <div className="flex items-center gap-3 text-sm text-gray-600 dark:text-slate-300">
        <Clock className="w-4 h-4" />
        <span>{formatDateTime(snapshot.captured_at)}</span>
        <span className="text-gray-400 dark:text-slate-500">|</span>
        <span className="capitalize">{triggerLabel(snapshot.trigger_event, snapshot.snapshot_type)}</span>
        {snapshot.notes && (
          <>
            <span className="text-gray-400 dark:text-slate-500">|</span>
            <span className="italic text-gray-500 dark:text-slate-400 truncate max-w-48">{snapshot.notes}</span>
          </>
        )}
      </div>

      {/* Key metrics grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <MetricCard
          label={t('time_machine.grade') || 'Grade'}
          value={snapshot.passport_grade || '--'}
          icon={Shield}
          color={
            snapshot.passport_grade && GRADE_COLORS[snapshot.passport_grade]
              ? 'text-red-600'
              : 'text-gray-500 dark:text-slate-400'
          }
        />
        <MetricCard
          label={t('time_machine.trust') || 'Trust'}
          value={snapshot.overall_trust != null ? `${(snapshot.overall_trust * 100).toFixed(0)}%` : '--'}
          icon={TrendingUp}
          color="text-blue-600 dark:text-blue-400"
        />
        <MetricCard
          label={t('time_machine.completeness') || 'Completeness'}
          value={snapshot.completeness_score != null ? `${(snapshot.completeness_score * 100).toFixed(0)}%` : '--'}
          icon={FileText}
          color="text-green-600 dark:text-green-400"
        />
        <MetricCard
          label={t('time_machine.evidence_count') || 'Evidence'}
          value={
            evidenceCounts
              ? String(
                  Object.values(evidenceCounts).reduce((acc: number, v) => acc + (typeof v === 'number' ? v : 0), 0),
                )
              : '--'
          }
          icon={Activity}
          color="text-purple-600 dark:text-purple-400"
        />
      </div>

      {/* Readiness statuses */}
      {readinessEntries.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">
            {t('time_machine.readiness_at_snapshot') || 'Readiness at time of snapshot'}
          </p>
          <div className="flex flex-wrap gap-2">
            {readinessEntries.map(([key, val]) => {
              const entry = val as Record<string, unknown>;
              const status = (entry?.status as string) || 'unknown';
              const statusColor =
                status === 'ready'
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                  : status === 'conditionally_ready'
                    ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                    : status === 'not_ready'
                      ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      : 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-400';
              return (
                <span
                  key={key}
                  className={cn(
                    'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                    statusColor,
                  )}
                >
                  {key.replace(/_/g, ' ')}
                  <span className="font-normal">({status.replace(/_/g, ' ')})</span>
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Pollutant coverage */}
      {pollutantCoverage && Object.keys(pollutantCoverage).length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">
            {t('time_machine.pollutant_status') || 'Pollutant status'}
          </p>
          <div className="grid grid-cols-5 gap-2">
            {Object.entries(pollutantCoverage).map(([pollutant, data]) => {
              const info = data as Record<string, unknown>;
              const covered = (info?.covered as boolean) ?? false;
              return (
                <div
                  key={pollutant}
                  className={cn(
                    'text-center p-2 rounded-lg text-xs font-medium',
                    covered
                      ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                      : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400',
                  )}
                >
                  <p className="capitalize">{pollutant}</p>
                  <p className="text-[10px] font-normal mt-0.5">{covered ? 'Covered' : 'Missing'}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Compare Mode Side-by-Side
// ---------------------------------------------------------------------------

function deltaColor(delta: number): string {
  if (delta > 0) return 'text-green-600 dark:text-green-400';
  if (delta < 0) return 'text-red-600 dark:text-red-400';
  return 'text-gray-400 dark:text-slate-500';
}

function CompareRow({ label, valA, valB, delta }: { label: string; valA: string; valB: string; delta?: number }) {
  const bg =
    delta != null && delta > 0
      ? 'bg-green-50/50 dark:bg-green-900/10'
      : delta != null && delta < 0
        ? 'bg-red-50/50 dark:bg-red-900/10'
        : '';
  return (
    <div className={cn('grid grid-cols-4 gap-2 items-center py-2 px-3 rounded', bg)}>
      <span className="text-xs font-medium text-gray-600 dark:text-slate-400">{label}</span>
      <span className="text-sm text-center text-gray-900 dark:text-white">{valA}</span>
      <span className="text-sm text-center text-gray-900 dark:text-white">{valB}</span>
      <span className={cn('text-sm text-center font-medium', delta != null ? deltaColor(delta) : '')}>
        {delta != null ? <DeltaIndicator value={delta} /> : '--'}
      </span>
    </div>
  );
}

function ComparisonView({
  comparison,
  snapshots,
  t,
}: {
  comparison: SnapshotComparison;
  snapshots: BuildingSnapshot[];
  t: (key: string) => string;
}) {
  const snapA = snapshots.find((s) => s.id === comparison.snapshot_a.id);
  const snapB = snapshots.find((s) => s.id === comparison.snapshot_b.id);

  return (
    <div className="border border-gray-200 dark:border-slate-700 rounded-lg bg-gray-50 dark:bg-slate-900/50 p-4 space-y-3">
      <h4 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
        <GitCompareArrows className="w-4 h-4 text-red-600" />
        {t('time_machine.comparison_result') || 'Comparison'}
      </h4>

      {/* Column headers */}
      <div className="grid grid-cols-4 gap-2 items-center px-3 pb-1 border-b border-gray-200 dark:border-slate-700">
        <span className="text-xs font-medium text-gray-500 dark:text-slate-500">
          {t('time_machine.metric') || 'Metric'}
        </span>
        <span className="text-xs font-medium text-center text-gray-500 dark:text-slate-500">
          {snapA ? formatDate(snapA.captured_at) : 'A'}
        </span>
        <span className="text-xs font-medium text-center text-gray-500 dark:text-slate-500">
          {snapB ? formatDate(snapB.captured_at) : 'B'}
        </span>
        <span className="text-xs font-medium text-center text-gray-500 dark:text-slate-500">
          {t('time_machine.delta') || 'Delta'}
        </span>
      </div>

      {/* Trust */}
      <CompareRow
        label={t('time_machine.trust') || 'Trust'}
        valA={`${(comparison.snapshot_a.overall_trust * 100).toFixed(0)}%`}
        valB={`${(comparison.snapshot_b.overall_trust * 100).toFixed(0)}%`}
        delta={comparison.changes.trust_delta}
      />

      {/* Completeness */}
      <CompareRow
        label={t('time_machine.completeness') || 'Completeness'}
        valA={`${(comparison.snapshot_a.completeness_score * 100).toFixed(0)}%`}
        valB={`${(comparison.snapshot_b.completeness_score * 100).toFixed(0)}%`}
        delta={comparison.changes.completeness_delta}
      />

      {/* Grade */}
      <div className="grid grid-cols-4 gap-2 items-center py-2 px-3">
        <span className="text-xs font-medium text-gray-600 dark:text-slate-400">
          {t('time_machine.grade') || 'Grade'}
        </span>
        <div className="flex justify-center">
          <GradeBadge grade={comparison.snapshot_a.passport_grade} />
        </div>
        <div className="flex justify-center">
          <GradeBadge grade={comparison.snapshot_b.passport_grade} />
        </div>
        <span className="text-sm text-center font-medium text-gray-900 dark:text-white">
          {comparison.changes.grade_change || <Minus className="w-4 h-4 mx-auto text-gray-400 dark:text-slate-500" />}
        </span>
      </div>

      {/* Readiness changes */}
      {comparison.changes.readiness_changes.length > 0 && (
        <div className="space-y-1 px-3">
          <p className="text-xs font-medium text-gray-500 dark:text-slate-400">
            {t('time_machine.readiness_changes') || 'Readiness changes'}
          </p>
          {comparison.changes.readiness_changes.map((rc, i) => {
            const improved = rc.to === 'ready' || (rc.from === 'not_ready' && rc.to === 'conditionally_ready');
            return (
              <div
                key={i}
                className={cn(
                  'flex items-center gap-2 text-xs py-1 px-2 rounded',
                  improved
                    ? 'bg-green-50 dark:bg-green-900/10 text-green-700 dark:text-green-400'
                    : 'bg-red-50 dark:bg-red-900/10 text-red-700 dark:text-red-400',
                )}
              >
                <span className="font-medium capitalize">{rc.type.replace(/_/g, ' ')}</span>
                <span>{rc.from || '--'}</span>
                <span>&rarr;</span>
                <span>{rc.to || '--'}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Contradiction changes */}
      {(comparison.changes.new_contradictions > 0 || comparison.changes.resolved_contradictions > 0) && (
        <div className="flex gap-4 text-xs px-3">
          {comparison.changes.new_contradictions > 0 && (
            <span className="text-red-600 dark:text-red-400 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />+{comparison.changes.new_contradictions}{' '}
              {t('time_machine.new_contradictions') || 'new contradictions'}
            </span>
          )}
          {comparison.changes.resolved_contradictions > 0 && (
            <span className="text-green-600 dark:text-green-400">
              -{comparison.changes.resolved_contradictions} {t('time_machine.resolved_contradictions') || 'resolved'}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Timeline Visualization
// ---------------------------------------------------------------------------

function SnapshotTimeline({
  snapshots,
  selectedIds,
  detailId,
  onSelect,
  onViewDetail,
  t,
}: {
  snapshots: BuildingSnapshot[];
  selectedIds: string[];
  detailId: string | null;
  onSelect: (id: string) => void;
  onViewDetail: (id: string) => void;
  t: (key: string) => string;
}) {
  // Chronological order (oldest first) for the timeline
  const chronological = useMemo(() => [...snapshots].reverse(), [snapshots]);

  if (chronological.length === 0) return null;

  return (
    <div className="relative">
      <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-3">
        {t('time_machine.timeline') || 'Timeline'}
      </p>
      <div className="flex items-start gap-0 overflow-x-auto pb-2">
        {chronological.map((snap, idx) => {
          const isSelected = selectedIds.includes(snap.id);
          const isDetailView = detailId === snap.id;
          const isLatest = idx === chronological.length - 1;
          const TriggerIcon = TRIGGER_ICONS[snap.trigger_event || snap.snapshot_type] || Camera;
          return (
            <div key={snap.id} className="flex items-start shrink-0">
              {/* Node */}
              <div className="flex flex-col items-center gap-1">
                <button
                  onClick={() => onSelect(snap.id)}
                  title={t('time_machine.select_for_compare') || 'Select for compare'}
                  className={cn(
                    'relative w-10 h-10 rounded-full border-2 flex items-center justify-center transition-all',
                    isSelected
                      ? 'border-red-500 bg-red-50 dark:bg-red-900/30 ring-2 ring-red-300 dark:ring-red-700'
                      : isDetailView
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30'
                        : 'border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 hover:border-gray-400 dark:hover:border-slate-500',
                  )}
                >
                  <GradeBadge grade={snap.passport_grade} />
                  {isLatest && (
                    <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white dark:border-slate-800" />
                  )}
                </button>
                {/* Trust bar */}
                <div className="w-8 h-1 rounded-full bg-gray-200 dark:bg-slate-700 overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full"
                    style={{ width: `${(snap.overall_trust || 0) * 100}%` }}
                  />
                </div>
                {/* Date + detail button */}
                <div className="flex flex-col items-center gap-0.5">
                  <span className="text-[10px] text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    {formatDate(snap.captured_at, 'dd.MM.yy')}
                  </span>
                  <div className="flex items-center gap-1">
                    <TriggerIcon className="w-3 h-3 text-gray-400 dark:text-slate-500" />
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onViewDetail(snap.id);
                      }}
                      className="text-[10px] text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      {t('time_machine.view') || 'View'}
                    </button>
                  </div>
                </div>
              </div>
              {/* Connector line */}
              {idx < chronological.length - 1 && (
                <div className="flex items-center self-center mt-0 mx-1" style={{ marginTop: '12px' }}>
                  <div className="w-8 h-0.5 bg-gray-300 dark:bg-slate-600" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Create Snapshot Form
// ---------------------------------------------------------------------------

function CreateSnapshotForm({
  buildingId,
  t,
  queryClient,
}: {
  buildingId: string;
  t: (key: string) => string;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const [showForm, setShowForm] = useState(false);
  const [notes, setNotes] = useState('');

  const captureMutation = useMutation({
    mutationFn: () =>
      snapshotsApi.capture(buildingId, {
        snapshot_type: 'manual',
        notes: notes.trim() || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['snapshots', buildingId] });
      setNotes('');
      setShowForm(false);
    },
    onError: (err: any) => {
      toast(err?.response?.data?.detail || err?.message || t('app.error') || 'An error occurred');
    },
  });

  if (!showForm) {
    return (
      <button
        onClick={() => setShowForm(true)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors"
      >
        <Camera className="w-3.5 h-3.5" />
        {t('time_machine.capture') || 'Capture Snapshot'}
      </button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder={t('time_machine.notes_placeholder') || 'Optional notes...'}
        className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
      />
      <button
        onClick={() => captureMutation.mutate()}
        disabled={captureMutation.isPending}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
      >
        {captureMutation.isPending ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <Camera className="w-3.5 h-3.5" />
        )}
        {t('time_machine.save') || 'Save'}
      </button>
      <button
        onClick={() => {
          setShowForm(false);
          setNotes('');
        }}
        className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
      >
        <X className="w-4 h-4 text-gray-500 dark:text-slate-400" />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

interface TimeMachinePanelProps {
  buildingId: string;
}

export function TimeMachinePanel({ buildingId }: TimeMachinePanelProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<SnapshotComparison | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);

  const {
    data: snapshotData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['snapshots', buildingId],
    queryFn: () => snapshotsApi.list(buildingId),
  });

  const snapshots = useMemo(() => snapshotData?.items ?? [], [snapshotData]);

  const detailSnapshot = useMemo(
    () => (detailId ? snapshots.find((s) => s.id === detailId) || null : null),
    [detailId, snapshots],
  );

  const toggleSelection = (id: string) => {
    setComparison(null);
    setSelectedIds((prev) => {
      if (prev.includes(id)) return prev.filter((s) => s !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  };

  const handleViewDetail = (id: string) => {
    setDetailId((prev) => (prev === id ? null : id));
  };

  const handleCompare = async () => {
    if (selectedIds.length !== 2) return;
    setIsComparing(true);
    try {
      const result = await snapshotsApi.compare(buildingId, selectedIds[0], selectedIds[1]);
      setComparison(result);
    } catch (err: any) {
      toast(err?.response?.data?.detail || err?.message || t('app.error') || 'An error occurred');
    } finally {
      setIsComparing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
        <div className="flex items-center gap-2 text-gray-500 dark:text-slate-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          {t('app.loading') || 'Loading...'}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
        <p className="text-red-600 dark:text-red-400">{t('app.error') || 'An error occurred'}</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white hover:text-gray-700 dark:hover:text-slate-200 transition-colors"
        >
          <Camera className="w-5 h-5 text-red-600" />
          {t('time_machine.title') || 'Time Machine'}
          <span className="text-sm font-normal text-gray-500 dark:text-slate-400">({snapshots.length})</span>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </button>
        {isExpanded && <CreateSnapshotForm buildingId={buildingId} t={t} queryClient={queryClient} />}
      </div>

      {!isExpanded && null}

      {isExpanded && (
        <>
          {/* Empty state */}
          {snapshots.length === 0 && (
            <p className="text-gray-500 dark:text-slate-400 text-sm">
              {t('time_machine.no_snapshots') || 'No snapshots yet'}
            </p>
          )}

          {snapshots.length > 0 && (
            <>
              {/* Timeline Visualization */}
              <SnapshotTimeline
                snapshots={snapshots}
                selectedIds={selectedIds}
                detailId={detailId}
                onSelect={toggleSelection}
                onViewDetail={handleViewDetail}
                t={t}
              />

              {/* Snapshot List */}
              <div>
                <p className="text-xs text-gray-500 dark:text-slate-400 mb-2">
                  {t('time_machine.select_to_compare') || 'Select two snapshots to compare'}
                </p>
                <div className="space-y-2 max-h-72 overflow-y-auto">
                  {snapshots.map((snap: BuildingSnapshot, idx: number) => {
                    const isSelected = selectedIds.includes(snap.id);
                    const isLatest = idx === 0;
                    const TriggerIcon = TRIGGER_ICONS[snap.trigger_event || snap.snapshot_type] || Camera;

                    return (
                      <div
                        key={snap.id}
                        className={cn(
                          'flex items-center justify-between gap-3 p-3 rounded-lg border transition-colors',
                          isSelected
                            ? 'border-red-400 bg-red-50 dark:border-red-600 dark:bg-red-900/20'
                            : 'border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700/50',
                        )}
                      >
                        <button
                          onClick={() => toggleSelection(snap.id)}
                          className="flex items-center gap-3 min-w-0 flex-1 text-left"
                        >
                          <div className="relative">
                            <GradeBadge grade={snap.passport_grade} />
                            {isLatest && (
                              <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-green-500 rounded-full border border-white dark:border-slate-800" />
                            )}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                {formatDateTime(snap.captured_at)}
                              </p>
                              {isLatest && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 font-medium">
                                  {t('time_machine.current') || 'Current'}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-slate-400">
                              <TriggerIcon className="w-3 h-3" />
                              <span className="capitalize">{triggerLabel(snap.trigger_event, snap.snapshot_type)}</span>
                              {snap.notes && (
                                <>
                                  <span className="text-gray-300 dark:text-slate-600">|</span>
                                  <span className="truncate max-w-32 italic">{snap.notes}</span>
                                </>
                              )}
                            </div>
                          </div>
                        </button>

                        <div className="flex items-center gap-3 shrink-0">
                          <div className="flex items-center gap-3 text-xs text-gray-600 dark:text-slate-300">
                            <span title={t('time_machine.trust') || 'Trust'}>
                              {snap.overall_trust != null ? `${(snap.overall_trust * 100).toFixed(0)}%` : '--'}
                            </span>
                            <span title={t('time_machine.completeness') || 'Completeness'}>
                              {snap.completeness_score != null
                                ? `${(snap.completeness_score * 100).toFixed(0)}%`
                                : '--'}
                            </span>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleViewDetail(snap.id);
                            }}
                            className={cn(
                              'p-1.5 rounded-lg transition-colors',
                              detailId === snap.id
                                ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                                : 'hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 dark:text-slate-500',
                            )}
                            title={t('time_machine.view') || 'View'}
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Compare button */}
              {selectedIds.length === 2 && !comparison && (
                <button
                  onClick={handleCompare}
                  disabled={isComparing}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100 disabled:opacity-50 transition-colors"
                >
                  {isComparing ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <GitCompareArrows className="w-3.5 h-3.5" />
                  )}
                  {t('time_machine.compare') || 'Compare'}
                </button>
              )}

              {/* Snapshot Detail */}
              {detailSnapshot && (
                <SnapshotDetailView snapshot={detailSnapshot} onClose={() => setDetailId(null)} t={t} />
              )}

              {/* Comparison Result */}
              {comparison && <ComparisonView comparison={comparison} snapshots={snapshots} t={t} />}
            </>
          )}
        </>
      )}
    </div>
  );
}
