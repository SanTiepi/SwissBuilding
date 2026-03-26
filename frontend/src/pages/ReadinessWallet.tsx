import { useState, useMemo, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useBuilding } from '@/hooks/useBuildings';
import { readinessApi } from '@/api/readiness';
import { snapshotsApi } from '@/api/snapshots';
import type { BuildingSnapshot } from '@/api/snapshots';
import { formatDate } from '@/utils/formatters';
import { BuildingSubNav } from '@/components/BuildingSubNav';
import type {
  ReadinessAssessment,
  ReadinessType,
  ReadinessStatus,
  ReadinessCheck,
  ReadinessBlocker,
  PreworkTrigger,
} from '@/types';
import { PreworkDiagnosticTriggerCard } from '@/components/PreworkDiagnosticTriggerCard';
import { EcoClauseCard } from '@/components/building-detail/EcoClauseCard';
import {
  ArrowLeft,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Minus,
  Loader2,
  RefreshCw,
  AlertTriangle,
  Info,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  X,
  FileText,
  Clock,
  Zap,
  Target,
  Shield,
  History,
} from 'lucide-react';

const READINESS_TYPES: ReadinessType[] = ['safe_to_start', 'safe_to_tender', 'safe_to_reopen', 'safe_to_requalify'];

const GATE_ICONS: Record<ReadinessType, typeof ShieldCheck> = {
  safe_to_start: Zap,
  safe_to_tender: FileText,
  safe_to_reopen: Shield,
  safe_to_requalify: Target,
};

const GATE_REGULATORY_REFS: Record<ReadinessType, string> = {
  safe_to_start: 'OTConst Art. 60a, 82-86 / CFST 6503',
  safe_to_tender: 'OTConst Art. 60a / ORRChim Annexe 2.15, 2.18',
  safe_to_reopen: 'ORaP Art. 110 / OLED / CFST 6503',
  safe_to_requalify: 'OTConst / ORRChim / ORaP',
};

function statusColor(status: ReadinessStatus): string {
  switch (status) {
    case 'ready':
      return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
    case 'blocked':
      return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
    case 'conditionally_ready':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
    case 'not_ready':
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
    default:
      return 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400';
  }
}

function statusBorderColor(status: ReadinessStatus | undefined): string {
  switch (status) {
    case 'ready':
      return 'border-green-300 dark:border-green-700';
    case 'blocked':
      return 'border-red-300 dark:border-red-700';
    case 'conditionally_ready':
      return 'border-yellow-300 dark:border-yellow-700';
    default:
      return 'border-gray-200 dark:border-slate-700';
  }
}

function ProgressRing({ score, size = 72 }: { score: number | null; size?: number }) {
  if (score === null || score === undefined) return null;
  const pct = Math.round(score * 100);
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - score * circumference;
  const color = pct >= 80 ? 'text-green-500' : pct >= 50 ? 'text-yellow-500' : 'text-red-500';

  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <svg className="transform -rotate-90" viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          className="text-gray-200 dark:text-slate-600"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={color}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-gray-900 dark:text-white">
        {pct}%
      </span>
    </div>
  );
}

function ProgressBar({ score }: { score: number | null }) {
  const pct = score !== null && score !== undefined ? Math.round(score * 100) : 0;
  const color = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="w-full bg-gray-200 dark:bg-slate-600 rounded-full h-2">
      <div className={`h-2 rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

interface AllBlocker {
  gate: ReadinessType;
  blocker: ReadinessBlocker;
  index: number;
  checkLabel?: string;
}

export default function ReadinessWallet() {
  const { buildingId } = useParams<{ buildingId: string }>();
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { data: building } = useBuilding(buildingId || '');
  const [evaluating, setEvaluating] = useState(false);
  const [expandedGates, setExpandedGates] = useState<Set<ReadinessType>>(new Set());
  const [selectedGate, setSelectedGate] = useState<ReadinessType | null>(null);
  const [dismissedBlockers, setDismissedBlockers] = useState<Set<string>>(new Set());

  const {
    data: readinessData,
    isLoading,
    isError: readinessError,
  } = useQuery({
    queryKey: ['readiness', buildingId],
    queryFn: () => readinessApi.list(buildingId!),
    enabled: !!buildingId,
  });

  const { data: snapshotsData } = useQuery({
    queryKey: ['snapshots', buildingId],
    queryFn: () => snapshotsApi.list(buildingId!),
    enabled: !!buildingId,
  });

  const evaluateAllMutation = useMutation({
    mutationFn: () => readinessApi.evaluateAll(buildingId!),
    onMutate: () => setEvaluating(true),
    onSettled: () => setEvaluating(false),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['readiness', buildingId] });
    },
  });

  const assessments = useMemo(() => readinessData?.items || [], [readinessData?.items]);
  const snapshots: BuildingSnapshot[] = useMemo(() => snapshotsData?.items || [], [snapshotsData?.items]);

  const getAssessment = useCallback(
    (type: ReadinessType): ReadinessAssessment | undefined => {
      return assessments.find((a) => a.readiness_type === type);
    },
    [assessments],
  );

  // Collect all blockers across gates, sorted by severity
  const allBlockers: AllBlocker[] = useMemo(() => {
    const blockers: AllBlocker[] = [];
    const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

    for (const type of READINESS_TYPES) {
      const assessment = getAssessment(type);
      if (!assessment) continue;

      const gateBlockers = assessment.blockers_json || [];
      gateBlockers.forEach((blocker, index) => {
        const failedChecks = (assessment.checks_json || []).filter((c) => !c.passed);
        blockers.push({
          gate: type,
          blocker,
          index,
          checkLabel: failedChecks[index]?.label,
        });
      });
    }

    blockers.sort((a, b) => {
      const sa = severityOrder[a.blocker.severity] ?? 99;
      const sb = severityOrder[b.blocker.severity] ?? 99;
      return sa - sb;
    });

    return blockers;
  }, [getAssessment]);

  const visibleBlockers = allBlockers.filter((b) => !dismissedBlockers.has(`${b.gate}-${b.index}`));

  // Collect all prework triggers across assessments
  const allPreworkTriggers: PreworkTrigger[] = useMemo(() => {
    const triggers: PreworkTrigger[] = [];
    for (const type of READINESS_TYPES) {
      const assessment = getAssessment(type);
      if (assessment?.prework_triggers) {
        triggers.push(...assessment.prework_triggers);
      }
    }
    return triggers;
  }, [getAssessment]);

  // Compute progress trend from snapshots
  const progressTrend = useMemo(() => {
    if (snapshots.length < 2) return null;
    const sorted = [...snapshots].sort((a, b) => new Date(b.captured_at).getTime() - new Date(a.captured_at).getTime());
    const latest = sorted[0];
    const previous = sorted[1];
    if (latest.completeness_score === null || previous.completeness_score === null) return null;
    const delta = latest.completeness_score - previous.completeness_score;
    if (delta > 0.01) return 'improving' as const;
    if (delta < -0.01) return 'declining' as const;
    return 'stable' as const;
  }, [snapshots]);

  // Top 3 actions to unlock next gate
  const topActions = useMemo(() => {
    const actions: { label: string; gate: ReadinessType; details: string | null }[] = [];

    for (const type of READINESS_TYPES) {
      const assessment = getAssessment(type);
      if (!assessment || assessment.status === 'ready') continue;

      const failedChecks = (assessment.checks_json || []).filter((c) => !c.passed);
      for (const check of failedChecks) {
        actions.push({ label: check.label, gate: type, details: check.details });
        if (actions.length >= 3) break;
      }
      if (actions.length >= 3) break;
    }

    return actions;
  }, [getAssessment]);

  const toggleGate = (type: ReadinessType) => {
    setExpandedGates((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  const handleCreateAction = (blocker: AllBlocker) => {
    navigate(`/buildings/${buildingId}?tab=actions&create=true&title=${encodeURIComponent(blocker.blocker.label)}`);
  };

  const handleDismissBlocker = (blocker: AllBlocker) => {
    setDismissedBlockers((prev) => {
      const next = new Set(prev);
      next.add(`${blocker.gate}-${blocker.index}`);
      return next;
    });
  };

  const selectedAssessment = selectedGate ? getAssessment(selectedGate) : null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <Link
            to={`/buildings/${buildingId}`}
            className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
          >
            <ArrowLeft className="w-4 h-4" />
            {building?.address || t('building.back')}
          </Link>
        </div>
        <div className="w-full">
          <BuildingSubNav buildingId={buildingId!} />
        </div>
        <div className="flex items-center gap-3">
          <ShieldCheck className="w-6 h-6 text-red-600" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('readiness.wallet_title') || 'Readiness Wallet'}
          </h1>
        </div>
        <button
          onClick={() => evaluateAllMutation.mutate()}
          disabled={evaluating}
          className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
        >
          {evaluating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              {t('readiness.evaluating') || 'Evaluating...'}
            </>
          ) : (
            <>
              <RefreshCw className="w-4 h-4" />
              {t('readiness.evaluate_all') || 'Evaluate All'}
            </>
          )}
        </button>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      )}

      {!isLoading && readinessError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center dark:border-red-900/50 dark:bg-red-950/20">
          <AlertTriangle className="mx-auto mb-2 h-6 w-6 text-red-500" />
          <p className="text-sm font-medium text-red-700 dark:text-red-300">{t('app.error') || 'An error occurred'}</p>
          <p className="mt-1 text-xs text-red-600 dark:text-red-400">
            {t('readiness.no_assessment') || 'No assessment available'}
          </p>
        </div>
      )}

      {!isLoading && !readinessError && (
        <>
          {/* 1. Gate progress overview - 2x2 Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {READINESS_TYPES.map((type) => {
              const assessment = getAssessment(type);
              const isExpanded = expandedGates.has(type);
              return (
                <GateCard
                  key={type}
                  type={type}
                  assessment={assessment}
                  t={t}
                  isExpanded={isExpanded}
                  onToggle={() => toggleGate(type)}
                  onOpenDetail={() => setSelectedGate(type)}
                  buildingId={buildingId!}
                />
              );
            })}
          </div>

          {/* 3. Blocker resolution panel */}
          {visibleBlockers.length > 0 && (
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-red-200 dark:border-red-900/50 p-6 space-y-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {t('readiness.blocker_resolution') || 'Blocker Resolution'}
                </h2>
                <span className="ml-auto text-sm text-gray-500 dark:text-slate-400">
                  {visibleBlockers.length} {t('readiness.blockers') || 'blockers'}
                </span>
              </div>

              <div className="space-y-3">
                {visibleBlockers.map((item) => {
                  const key = `${item.gate}-${item.index}`;
                  return (
                    <div
                      key={key}
                      className="flex items-start gap-3 p-3 bg-red-50 dark:bg-red-900/10 rounded-lg border border-red-100 dark:border-red-900/30"
                    >
                      <div className="flex-shrink-0 mt-0.5">
                        <SeverityDot severity={item.blocker.severity} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300">
                            {t(`readiness.${item.gate}`) || item.gate}
                          </span>
                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                            {item.blocker.label}
                          </span>
                        </div>
                        {item.blocker.details && (
                          <p className="mt-1 text-xs text-gray-600 dark:text-slate-400">{item.blocker.details}</p>
                        )}
                        <p className="mt-1 text-xs text-red-600 dark:text-red-400 italic">
                          {t('readiness.suggested_resolution') || 'Resolve this blocker to progress the gate.'}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <button
                          onClick={() => handleCreateAction(item)}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                        >
                          <Zap className="w-3 h-3" />
                          {t('readiness.create_action') || 'Create action'}
                        </button>
                        <button
                          onClick={() => handleDismissBlocker(item)}
                          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 transition-colors"
                          title={t('readiness.dismiss') || 'Dismiss'}
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Prework diagnostic triggers */}
          <PreworkDiagnosticTriggerCard triggers={allPreworkTriggers} />

          {/* Eco clause recommendations */}
          {buildingId && <EcoClauseCard buildingId={buildingId} />}

          {/* 4. Progress tracking */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Progress trend */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6 space-y-4">
              <div className="flex items-center gap-2">
                <History className="w-5 h-5 text-gray-500 dark:text-slate-400" />
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {t('readiness.progress_tracking') || 'Progress Tracking'}
                </h2>
              </div>

              {progressTrend && (
                <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-slate-700/50">
                  {progressTrend === 'improving' && (
                    <>
                      <TrendingUp className="w-5 h-5 text-green-500" />
                      <span className="text-sm font-medium text-green-700 dark:text-green-400">
                        {t('readiness.trend_improving') || 'Improving'}
                      </span>
                    </>
                  )}
                  {progressTrend === 'declining' && (
                    <>
                      <TrendingDown className="w-5 h-5 text-red-500" />
                      <span className="text-sm font-medium text-red-700 dark:text-red-400">
                        {t('readiness.trend_declining') || 'Declining'}
                      </span>
                    </>
                  )}
                  {progressTrend === 'stable' && (
                    <>
                      <Minus className="w-5 h-5 text-yellow-500" />
                      <span className="text-sm font-medium text-yellow-700 dark:text-yellow-400">
                        {t('readiness.trend_stable') || 'Stable'}
                      </span>
                    </>
                  )}
                </div>
              )}

              {snapshots.length > 0 ? (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-gray-700 dark:text-slate-300">
                    {t('readiness.recent_snapshots') || 'Recent snapshots'}
                  </h3>
                  <div className="space-y-1.5 max-h-40 overflow-y-auto">
                    {[...snapshots]
                      .sort((a, b) => new Date(b.captured_at).getTime() - new Date(a.captured_at).getTime())
                      .slice(0, 5)
                      .map((snap) => (
                        <div
                          key={snap.id}
                          className="flex items-center justify-between text-sm p-2 rounded bg-gray-50 dark:bg-slate-700/30"
                        >
                          <div className="flex items-center gap-2">
                            <Clock className="w-3.5 h-3.5 text-gray-400" />
                            <span className="text-gray-700 dark:text-slate-300">{formatDate(snap.captured_at)}</span>
                          </div>
                          <div className="flex items-center gap-3">
                            {snap.passport_grade && (
                              <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                                {snap.passport_grade}
                              </span>
                            )}
                            {snap.completeness_score !== null && (
                              <span className="text-xs text-gray-500 dark:text-slate-400">
                                {Math.round(snap.completeness_score * 100)}%
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-gray-400 dark:text-slate-500">
                  {t('readiness.no_snapshots') || 'No snapshots available yet.'}
                </p>
              )}
            </div>

            {/* What's needed */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6 space-y-4">
              <div className="flex items-center gap-2">
                <Target className="w-5 h-5 text-gray-500 dark:text-slate-400" />
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {t('readiness.whats_needed') || "What's Needed"}
                </h2>
              </div>

              {topActions.length > 0 ? (
                <div className="space-y-3">
                  <p className="text-sm text-gray-500 dark:text-slate-400">
                    {t('readiness.top_actions_desc') || 'Top actions to unlock the next gate:'}
                  </p>
                  {topActions.map((action, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30"
                    >
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-500 text-white text-xs font-bold flex items-center justify-center">
                        {i + 1}
                      </span>
                      <div className="min-w-0">
                        <span className="text-sm font-medium text-gray-900 dark:text-white">{action.label}</span>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300">
                            {t(`readiness.${action.gate}`) || action.gate}
                          </span>
                          {action.details && (
                            <span className="text-xs text-gray-500 dark:text-slate-400">{action.details}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : assessments.length > 0 ? (
                <div className="flex items-center gap-3 p-4 bg-green-50 dark:bg-green-900/10 rounded-lg">
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                  <span className="text-sm font-medium text-green-700 dark:text-green-400">
                    {t('readiness.all_gates_clear') || 'All gates are clear!'}
                  </span>
                </div>
              ) : (
                <p className="text-sm text-gray-400 dark:text-slate-500">
                  {t('readiness.evaluate_first') || 'Run an evaluation to see what is needed.'}
                </p>
              )}
            </div>
          </div>
        </>
      )}

      {/* Disclaimer */}
      <div className="flex items-start gap-2 p-4 bg-gray-50 dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700">
        <Info className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-gray-500 dark:text-slate-400">
          {t('disclaimer.readiness_wallet') || 'Regulatory readiness overview. Not legal advice.'}
        </p>
      </div>

      {/* 5. Gate detail modal */}
      {selectedGate && (
        <GateDetailModal
          type={selectedGate}
          assessment={selectedAssessment}
          t={t}
          buildingId={buildingId!}
          onClose={() => setSelectedGate(null)}
        />
      )}
    </div>
  );
}

/* ========================================================================
   Gate Card with expandable checklist
   ======================================================================== */

function GateCard({
  type,
  assessment,
  t,
  isExpanded,
  onToggle,
  onOpenDetail,
  buildingId,
}: {
  type: ReadinessType;
  assessment: ReadinessAssessment | undefined;
  t: (key: string) => string;
  isExpanded: boolean;
  onToggle: () => void;
  onOpenDetail: () => void;
  buildingId: string;
}) {
  const Icon = GATE_ICONS[type];
  const typeLabel = t(`readiness.${type}`) || type;

  if (!assessment) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Icon className="w-5 h-5 text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{typeLabel}</h3>
          </div>
          <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400">
            {t('readiness.not_evaluated') || 'Not evaluated'}
          </span>
        </div>
        <p className="text-sm text-gray-400 dark:text-slate-500">
          {t('readiness.no_assessment') || 'No assessment available'}
        </p>
      </div>
    );
  }

  const checks = assessment.checks_json || [];
  const blockers = assessment.blockers_json || [];
  const conditions = assessment.conditions_json || [];
  const passedCount = checks.filter((c) => c.passed).length;
  const totalChecks = checks.length;

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-xl shadow-sm border-2 ${statusBorderColor(assessment.status)} p-6 space-y-4 transition-all`}
    >
      {/* Header with progress ring */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Icon className="w-5 h-5 text-gray-500 dark:text-slate-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{typeLabel}</h3>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`inline-block px-2.5 py-1 text-xs font-medium rounded-full ${statusColor(assessment.status)}`}
            >
              {t(`readiness.status.${assessment.status}`) || assessment.status}
            </span>
            {totalChecks > 0 && (
              <span className="text-xs text-gray-500 dark:text-slate-400">
                {passedCount}/{totalChecks} {t('readiness.checks') || 'checks'}
              </span>
            )}
          </div>
          {/* Progress bar */}
          <div className="mt-3">
            <ProgressBar score={assessment.score} />
          </div>
        </div>
        <ProgressRing score={assessment.score} />
      </div>

      {/* Blockers count badge */}
      {blockers.length > 0 && (
        <div className="flex items-center gap-2">
          <XCircle className="w-4 h-4 text-red-500" />
          <span className="text-sm text-red-600 dark:text-red-400 font-medium">
            {blockers.length} {t('readiness.blockers') || 'blockers'}
          </span>
        </div>
      )}

      {/* Conditions count badge */}
      {conditions.length > 0 && (
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-yellow-500" />
          <span className="text-sm text-yellow-600 dark:text-yellow-400 font-medium">
            {conditions.length} {t('readiness.conditions') || 'conditions'}
          </span>
        </div>
      )}

      {/* Expand/Collapse button */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-slate-700">
        <button
          onClick={onToggle}
          className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 transition-colors"
        >
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          {isExpanded ? t('readiness.hide_checks') || 'Hide checks' : t('readiness.show_checks') || 'Show checks'}
        </button>
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenDetail}
            className="flex items-center gap-1 text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 transition-colors"
          >
            {t('readiness.view_detail') || 'Detail'}
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
          <span className="text-xs text-gray-400 dark:text-slate-500">{formatDate(assessment.assessed_at)}</span>
        </div>
      </div>

      {/* 2. Expandable checklist view */}
      {isExpanded && (
        <div className="space-y-3 pt-2 animate-in fade-in duration-200">
          {/* Individual checks */}
          {checks.length > 0 && (
            <ul className="space-y-2">
              {checks.map((check, i) => (
                <CheckItem key={i} check={check} t={t} buildingId={buildingId} />
              ))}
            </ul>
          )}

          {/* Blockers detail */}
          {blockers.length > 0 && (
            <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3">
              <h4 className="text-sm font-medium text-red-800 dark:text-red-300 mb-2 flex items-center gap-1.5">
                <XCircle className="w-4 h-4" />
                {t('readiness.blockers') || 'Blockers'}
              </h4>
              <ul className="space-y-1.5">
                {blockers.map((blocker, i) => (
                  <li key={i} className="text-sm text-red-700 dark:text-red-300 flex items-start gap-2">
                    <SeverityDot severity={blocker.severity} />
                    <div className="min-w-0">
                      <span>{blocker.label}</span>
                      {blocker.details && (
                        <span className="block text-xs text-red-600 dark:text-red-400">{blocker.details}</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Conditions detail */}
          {conditions.length > 0 && (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3">
              <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-300 mb-2 flex items-center gap-1.5">
                <Info className="w-4 h-4" />
                {t('readiness.conditions') || 'Conditions'}
              </h4>
              <ul className="space-y-1">
                {conditions.map((condition, i) => (
                  <li key={i} className="text-sm text-yellow-700 dark:text-yellow-300 flex items-start gap-2">
                    <Minus className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                    <div>
                      <span>{condition.label}</span>
                      {condition.details && (
                        <span className="block text-xs text-yellow-600 dark:text-yellow-400">{condition.details}</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ========================================================================
   Check item with status icon and entity link
   ======================================================================== */

function CheckItem({
  check,
  t,
  buildingId,
}: {
  check: ReadinessCheck;
  t: (key: string) => string;
  buildingId: string;
}) {
  // Attempt to extract linked entity from details text (heuristic)
  const entityLink = useMemo(() => {
    if (!check.details) return null;
    const lower = check.details.toLowerCase();
    if (lower.includes('diagnostic')) {
      return {
        label: t('readiness.see_diagnostics') || 'See diagnostics',
        path: `/buildings/${buildingId}?tab=diagnostics`,
      };
    }
    if (lower.includes('document') || lower.includes('report')) {
      return { label: t('readiness.see_documents') || 'See documents', path: `/buildings/${buildingId}?tab=documents` };
    }
    if (lower.includes('sample') || lower.includes('analyse')) {
      return {
        label: t('readiness.see_diagnostics') || 'See diagnostics',
        path: `/buildings/${buildingId}?tab=diagnostics`,
      };
    }
    if (lower.includes('pfas')) {
      return {
        label: t('readiness.see_diagnostics') || 'See diagnostics',
        path: `/buildings/${buildingId}?tab=diagnostics`,
      };
    }
    return null;
  }, [check.details, buildingId, t]);

  return (
    <li className="flex items-start gap-2 text-sm p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700/30 transition-colors">
      {check.passed ? (
        <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
      ) : (
        <XCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <span
          className={check.passed ? 'text-gray-800 dark:text-slate-200' : 'text-red-700 dark:text-red-300 font-medium'}
        >
          {check.label}
        </span>
        {check.details && <span className="block text-xs text-gray-500 dark:text-slate-400">{check.details}</span>}
      </div>
      {!check.passed && entityLink && (
        <Link
          to={entityLink.path}
          className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400 hover:underline flex-shrink-0"
        >
          {entityLink.label}
          <ArrowRight className="w-3 h-3" />
        </Link>
      )}
    </li>
  );
}

/* ========================================================================
   Severity dot indicator
   ======================================================================== */

function SeverityDot({ severity }: { severity: string }) {
  const color =
    severity === 'critical'
      ? 'bg-red-600'
      : severity === 'high'
        ? 'bg-red-400'
        : severity === 'medium'
          ? 'bg-yellow-500'
          : 'bg-gray-400';

  return <span className={`inline-block w-2.5 h-2.5 rounded-full mt-1 flex-shrink-0 ${color}`} />;
}

/* ========================================================================
   5. Gate Detail Modal
   ======================================================================== */

function GateDetailModal({
  type,
  assessment,
  t,
  buildingId,
  onClose,
}: {
  type: ReadinessType;
  assessment: ReadinessAssessment | undefined | null;
  t: (key: string) => string;
  buildingId: string;
  onClose: () => void;
}) {
  const Icon = GATE_ICONS[type];
  const typeLabel = t(`readiness.${type}`) || type;
  const regulatoryRef = GATE_REGULATORY_REFS[type];
  const checks = assessment?.checks_json || [];
  const blockers = assessment?.blockers_json || [];
  const conditions = assessment?.conditions_json || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div
        className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal header */}
        <div className="sticky top-0 bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700 p-6 flex items-center justify-between rounded-t-2xl z-10">
          <div className="flex items-center gap-3">
            <Icon className="w-6 h-6 text-red-600" />
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">{typeLabel}</h2>
            {assessment && (
              <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${statusColor(assessment.status)}`}>
                {t(`readiness.status.${assessment.status}`) || assessment.status}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {!assessment ? (
            <p className="text-sm text-gray-400 dark:text-slate-500">
              {t('readiness.no_assessment') || 'No assessment available'}
            </p>
          ) : (
            <>
              {/* Score */}
              <div className="flex items-center gap-6">
                <ProgressRing score={assessment.score} size={96} />
                <div>
                  <p className="text-sm text-gray-500 dark:text-slate-400">
                    {t('readiness.overall_score') || 'Overall score'}
                  </p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white">
                    {assessment.score !== null ? `${Math.round(assessment.score * 100)}%` : '-'}
                  </p>
                  <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
                    {t('readiness.last_assessed') || 'Last assessed'}: {formatDate(assessment.assessed_at)}
                  </p>
                </div>
              </div>

              {/* Regulatory context */}
              <div className="bg-blue-50 dark:bg-blue-900/10 rounded-lg p-4 border border-blue-100 dark:border-blue-900/30">
                <h3 className="text-sm font-medium text-blue-800 dark:text-blue-300 flex items-center gap-2 mb-1">
                  <FileText className="w-4 h-4" />
                  {t('readiness.regulatory_context') || 'Regulatory context'}
                </h3>
                <p className="text-sm text-blue-700 dark:text-blue-400">{regulatoryRef}</p>
              </div>

              {/* All checks */}
              {checks.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-3">
                    {t('readiness.all_checks') || 'All checks'} ({checks.filter((c) => c.passed).length}/{checks.length}
                    )
                  </h3>
                  <ul className="space-y-2">
                    {checks.map((check, i) => (
                      <CheckItem key={i} check={check} t={t} buildingId={buildingId} />
                    ))}
                  </ul>
                </div>
              )}

              {/* Blockers */}
              {blockers.length > 0 && (
                <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-red-800 dark:text-red-300 mb-3 flex items-center gap-2">
                    <XCircle className="w-4 h-4" />
                    {t('readiness.blockers') || 'Blockers'} ({blockers.length})
                  </h3>
                  <ul className="space-y-2">
                    {blockers.map((blocker, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <SeverityDot severity={blocker.severity} />
                        <div>
                          <span className="text-red-700 dark:text-red-300 font-medium">{blocker.label}</span>
                          {blocker.details && (
                            <span className="block text-xs text-red-600 dark:text-red-400">{blocker.details}</span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Conditions */}
              {conditions.length > 0 && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-yellow-800 dark:text-yellow-300 mb-3 flex items-center gap-2">
                    <Info className="w-4 h-4" />
                    {t('readiness.conditions') || 'Conditions'} ({conditions.length})
                  </h3>
                  <ul className="space-y-2">
                    {conditions.map((condition, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <Minus className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-yellow-500" />
                        <div>
                          <span className="text-yellow-700 dark:text-yellow-300">{condition.label}</span>
                          {condition.details && (
                            <span className="block text-xs text-yellow-600 dark:text-yellow-400">
                              {condition.details}
                            </span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Notes */}
              {assessment.notes && (
                <div className="text-sm text-gray-600 dark:text-slate-400 p-3 bg-gray-50 dark:bg-slate-700/30 rounded-lg">
                  <span className="font-medium text-gray-700 dark:text-slate-300">
                    {t('readiness.notes') || 'Notes'}:
                  </span>{' '}
                  {assessment.notes}
                </div>
              )}

              {/* Export button */}
              <div className="flex justify-end pt-2">
                <button
                  onClick={() => {
                    window.print();
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
                >
                  <FileText className="w-4 h-4" />
                  {t('readiness.export_report') || 'Export report'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
