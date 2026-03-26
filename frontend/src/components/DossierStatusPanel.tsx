import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { completenessApi } from '@/api/completeness';
import { readinessApi } from '@/api/readiness';
import { dossierApi } from '@/api/dossier';
import type { DossierCompletionReport } from '@/api/dossier';
import type { CompletenessResult, ReadinessAssessment } from '@/types';
import { DossierPackButton } from '@/components/DossierPackButton';
import { AsyncStateWrapper } from '@/components/AsyncStateWrapper';
import {
  CheckCircle2,
  Circle,
  AlertTriangle,
  ShieldCheck,
  FileSearch,
  FileText,
  ClipboardCheck,
  ArrowRight,
} from 'lucide-react';
import { cn } from '@/utils/formatters';

interface DossierStatusPanelProps {
  buildingId: string;
  stage?: 'avt' | 'apt';
}

type StepStatus = 'done' | 'partial' | 'pending';

interface StepInfo {
  key: string;
  labelKey: string;
  icon: typeof CheckCircle2;
  status: StepStatus;
}

function deriveSteps(
  completeness: CompletenessResult | undefined,
  safeToStart: ReadinessAssessment | undefined,
): StepInfo[] {
  const hasCompletedDiag =
    completeness?.checks.some((c) => c.category === 'diagnostic' && c.status === 'complete') ?? false;
  const hasSomeDiag = completeness?.checks.some((c) => c.category === 'diagnostic' && c.status === 'partial') ?? false;

  const hasEvidence =
    completeness?.checks.some(
      (c) => (c.category === 'evidence' || c.category === 'document') && c.status === 'complete',
    ) ?? false;
  const hasSomeEvidence =
    completeness?.checks.some(
      (c) => (c.category === 'evidence' || c.category === 'document') && c.status === 'partial',
    ) ?? false;

  const score = completeness?.overall_score ?? 0;
  const isComplete = score >= 0.8;
  const isPartialComplete = score >= 0.5;

  const stsStatus = safeToStart?.status;
  const isSafeToStart = stsStatus === 'ready';
  const isConditional = stsStatus === 'conditionally_ready';

  return [
    {
      key: 'diagnosed',
      labelKey: 'dossier.step_diagnosed',
      icon: FileSearch,
      status: hasCompletedDiag ? 'done' : hasSomeDiag ? 'partial' : 'pending',
    },
    {
      key: 'documented',
      labelKey: 'dossier.step_documented',
      icon: FileText,
      status: hasEvidence ? 'done' : hasSomeEvidence ? 'partial' : 'pending',
    },
    {
      key: 'complete',
      labelKey: 'dossier.step_complete',
      icon: ClipboardCheck,
      status: isComplete ? 'done' : isPartialComplete ? 'partial' : 'pending',
    },
    {
      key: 'safe_to_start',
      labelKey: 'dossier.step_safe_to_start',
      icon: ShieldCheck,
      status: isSafeToStart ? 'done' : isConditional ? 'partial' : 'pending',
    },
  ];
}

const STATUS_ICON_CLASS: Record<StepStatus, string> = {
  done: 'text-green-500 dark:text-green-400',
  partial: 'text-amber-500 dark:text-amber-400',
  pending: 'text-gray-300 dark:text-slate-600',
};

const STATUS_CONNECTOR_CLASS: Record<StepStatus, string> = {
  done: 'bg-green-500 dark:bg-green-400',
  partial: 'bg-amber-400 dark:bg-amber-500',
  pending: 'bg-gray-200 dark:bg-slate-600',
};

function StepIndicator({ status }: { status: StepStatus }) {
  if (status === 'done') return <CheckCircle2 className={cn('w-5 h-5', STATUS_ICON_CLASS.done)} />;
  if (status === 'partial') return <AlertTriangle className={cn('w-5 h-5', STATUS_ICON_CLASS.partial)} />;
  return <Circle className={cn('w-5 h-5', STATUS_ICON_CLASS.pending)} />;
}

function OverallBanner({
  report,
  t,
}: {
  report: DossierCompletionReport;
  t: (key: string, params?: Record<string, string | number>) => string;
}) {
  const configs: Record<
    DossierCompletionReport['overall_status'],
    { bg: string; text: string; border: string; label: string }
  > = {
    complete: {
      bg: 'bg-green-50 dark:bg-green-900/20',
      text: 'text-green-700 dark:text-green-300',
      border: 'border-green-200 dark:border-green-800',
      label: t('dossier.status_complete'),
    },
    near_complete: {
      bg: 'bg-amber-50 dark:bg-amber-900/20',
      text: 'text-amber-700 dark:text-amber-300',
      border: 'border-amber-200 dark:border-amber-800',
      label: t('dossier.status_near_complete', { count: (report.top_blockers || []).length }),
    },
    incomplete: {
      bg: 'bg-red-50 dark:bg-red-900/20',
      text: 'text-red-700 dark:text-red-300',
      border: 'border-red-200 dark:border-red-800',
      label: t('dossier.status_incomplete'),
    },
    critical_gaps: {
      bg: 'bg-red-50 dark:bg-red-900/20',
      text: 'text-red-700 dark:text-red-300',
      border: 'border-red-200 dark:border-red-800',
      label: t('dossier.status_critical_gaps'),
    },
  };

  const cfg = configs[report.overall_status];

  return (
    <div className={cn('rounded-lg border px-4 py-3', cfg.bg, cfg.border)}>
      <p className={cn('text-sm font-semibold', cfg.text)}>{cfg.label}</p>
      <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
        {t('dossier.overall_progress')}: {Math.round(report.overall_score * 100)}%
      </p>
    </div>
  );
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-600 dark:text-red-400',
  high: 'text-orange-600 dark:text-orange-400',
  medium: 'text-amber-600 dark:text-amber-400',
  low: 'text-gray-600 dark:text-gray-400',
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
  high: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300',
  medium: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
  low: 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300',
};

export function DossierStatusPanel({ buildingId, stage = 'avt' }: DossierStatusPanelProps) {
  const { t } = useTranslation();

  const completenessQuery = useQuery({
    queryKey: ['building-completeness', buildingId, stage],
    queryFn: () => completenessApi.evaluate(buildingId, stage),
  });

  const readinessQuery = useQuery({
    queryKey: ['building-readiness', buildingId],
    queryFn: () => readinessApi.list(buildingId),
    enabled: !!buildingId,
  });

  const completionQuery = useQuery({
    queryKey: ['building-dossier-completion', buildingId],
    queryFn: () => dossierApi.getCompletionReport(buildingId),
    enabled: !!buildingId,
  });

  const isLoading = completenessQuery.isLoading || readinessQuery.isLoading || completionQuery.isLoading;
  const isError = completenessQuery.isError && readinessQuery.isError && completionQuery.isError;

  // Extract latest safe_to_start assessment
  const assessments = readinessQuery.data?.items ?? [];
  let safeToStart: ReadinessAssessment | undefined;
  for (const a of assessments) {
    if (a.readiness_type === 'safe_to_start') {
      if (!safeToStart || a.assessed_at > safeToStart.assessed_at) {
        safeToStart = a;
      }
    }
  }

  const completeness = completenessQuery.data;
  const report = completionQuery.data;
  const steps = deriveSteps(completeness, safeToStart);

  // Step 3 (complete) must be done or partial for generate button
  const canGenerate = steps[2].status === 'done';

  return (
    <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <ShieldCheck className="w-5 h-5 text-gray-500 dark:text-slate-400" />
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{t('dossier.status_panel')}</h3>
      </div>

      <AsyncStateWrapper
        isLoading={isLoading}
        isError={isError}
        data={completeness || report}
        variant="inline"
        loadingType="skeleton"
        isEmpty={false}
        className="p-0"
      >
        {/* Progress Stepper */}
        <div className="mb-5">
          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-3">
            {t('dossier.journey')}
          </p>
          <div className="flex items-center">
            {steps.map((step, idx) => {
              const Icon = step.icon;
              return (
                <div key={step.key} className="flex items-center flex-1 last:flex-initial">
                  <div className="flex flex-col items-center min-w-0">
                    <div
                      className={cn(
                        'w-10 h-10 rounded-full flex items-center justify-center border-2',
                        step.status === 'done'
                          ? 'border-green-500 bg-green-50 dark:bg-green-900/30 dark:border-green-400'
                          : step.status === 'partial'
                            ? 'border-amber-400 bg-amber-50 dark:bg-amber-900/30 dark:border-amber-500'
                            : 'border-gray-200 bg-white dark:bg-slate-800 dark:border-slate-600',
                      )}
                    >
                      {step.status === 'done' ? (
                        <CheckCircle2 className="w-5 h-5 text-green-500 dark:text-green-400" />
                      ) : step.status === 'partial' ? (
                        <Icon className="w-5 h-5 text-amber-500 dark:text-amber-400" />
                      ) : (
                        <Icon className="w-5 h-5 text-gray-300 dark:text-slate-500" />
                      )}
                    </div>
                    <p
                      className={cn(
                        'text-xs mt-1 text-center leading-tight max-w-[80px]',
                        step.status === 'done'
                          ? 'text-green-700 dark:text-green-300 font-medium'
                          : step.status === 'partial'
                            ? 'text-amber-700 dark:text-amber-300 font-medium'
                            : 'text-gray-400 dark:text-slate-500',
                      )}
                    >
                      {t(step.labelKey)}
                    </p>
                    <p className="text-[10px] text-gray-400 dark:text-slate-500 mt-0.5">
                      {step.status === 'done'
                        ? t('dossier.achieved')
                        : step.status === 'partial'
                          ? t('dossier.in_progress_status')
                          : t('dossier.not_started')}
                    </p>
                  </div>
                  {idx < steps.length - 1 && (
                    <div className="flex-1 mx-2 flex items-center self-start mt-5">
                      <div
                        className={cn(
                          'h-0.5 flex-1',
                          STATUS_CONNECTOR_CLASS[step.status === 'done' ? 'done' : 'pending'],
                        )}
                      />
                      <ArrowRight
                        className={cn(
                          'w-3 h-3 -ml-0.5',
                          step.status === 'done'
                            ? 'text-green-500 dark:text-green-400'
                            : 'text-gray-300 dark:text-slate-600',
                        )}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Overall Status Banner */}
        {report && <OverallBanner report={report} t={t} />}

        {/* Top Blockers */}
        {report && (report.top_blockers || []).length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-2">
              {t('dossier.blockers')}
            </p>
            <ul className="space-y-1.5">
              {(report.top_blockers || []).slice(0, 5).map((blocker, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <StepIndicator status="partial" />
                  <div className="min-w-0 flex-1">
                    <span className={cn('text-xs font-medium', SEVERITY_COLORS[blocker.severity] || 'text-gray-600')}>
                      [{blocker.category}]
                    </span>{' '}
                    <span className="text-gray-700 dark:text-slate-300 text-xs">{blocker.description}</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommended Actions */}
        {report && (report.recommended_actions || []).length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-2">
              {t('dossier.recommended_actions')}
            </p>
            <ul className="space-y-1.5">
              {(report.recommended_actions || []).slice(0, 3).map((action, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <ArrowRight className="w-4 h-4 text-gray-400 dark:text-slate-500 mt-0.5 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <span className="text-gray-700 dark:text-slate-300 text-xs">{action.action}</span>
                    <span
                      className={cn(
                        'ml-2 inline-block text-[10px] px-1.5 py-0.5 rounded-full font-medium',
                        PRIORITY_COLORS[action.priority] || PRIORITY_COLORS.low,
                      )}
                    >
                      {action.priority}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Generate Dossier Button */}
        <div className="mt-5 pt-4 border-t border-gray-200 dark:border-slate-600">
          {canGenerate ? (
            <DossierPackButton buildingId={buildingId} stage={stage} />
          ) : (
            <div className="flex items-center gap-2">
              <button
                disabled
                className="inline-flex items-center gap-2 rounded-lg bg-gray-300 dark:bg-slate-600 px-4 py-2 text-sm font-medium text-gray-500 dark:text-slate-400 cursor-not-allowed"
              >
                <ShieldCheck className="w-4 h-4" />
                {t('dossier.generate')}
              </button>
              <span className="text-xs text-gray-400 dark:text-slate-500 italic">
                {t('dossier.generate_when_ready')}
              </span>
            </div>
          )}
        </div>
      </AsyncStateWrapper>
    </div>
  );
}
