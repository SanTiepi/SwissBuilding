import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { completenessApi } from '@/api/completeness';
import { CheckCircle2, XCircle, MinusCircle, Shield, ShieldCheck, AlertTriangle } from 'lucide-react';
import type { CompletenessCheck, CompletenessStatus } from '@/types';
import { AsyncStateWrapper } from './AsyncStateWrapper';

interface CompletenessGaugeProps {
  buildingId: string;
  stage?: string;
}

const STATUS_ICONS: Record<CompletenessStatus, typeof CheckCircle2> = {
  complete: CheckCircle2,
  missing: XCircle,
  partial: AlertTriangle,
  not_applicable: MinusCircle,
};

const STATUS_COLORS: Record<CompletenessStatus, string> = {
  complete: 'text-green-500',
  missing: 'text-red-500',
  partial: 'text-yellow-500',
  not_applicable: 'text-gray-400',
};

const CATEGORY_ORDER = ['diagnostic', 'evidence', 'document', 'regulatory', 'action'];

function groupByCategory(checks: CompletenessCheck[]): Record<string, CompletenessCheck[]> {
  const groups: Record<string, CompletenessCheck[]> = {};
  for (const check of checks) {
    if (!groups[check.category]) {
      groups[check.category] = [];
    }
    groups[check.category].push(check);
  }
  return groups;
}

export function CompletenessGauge({ buildingId, stage = 'avt' }: CompletenessGaugeProps) {
  const {
    data: result,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['building-completeness', buildingId, stage],
    queryFn: () => completenessApi.evaluate(buildingId, stage),
  });

  if (!isLoading && !isError && !result) return null;

  return (
    <AsyncStateWrapper
      isLoading={isLoading}
      isError={isError}
      data={result}
      variant="inline"
      loadingType="skeleton"
      isEmpty={false}
      className="p-0"
    >
      {result && <CompletenessContent result={result} stage={stage} />}
    </AsyncStateWrapper>
  );
}

function CompletenessContent({ result, stage }: { result: any; stage: string }) {
  const { t } = useTranslation();
  const score = Math.round(result.overall_score * 100);
  const color = score >= 80 ? 'text-green-600' : score >= 50 ? 'text-yellow-600' : 'text-red-600';
  const strokeColor = score >= 80 ? 'stroke-green-500' : score >= 50 ? 'stroke-yellow-500' : 'stroke-red-500';
  const bgColor =
    score >= 80
      ? 'bg-green-50 dark:bg-green-900/20'
      : score >= 50
        ? 'bg-yellow-50 dark:bg-yellow-900/20'
        : 'bg-red-50 dark:bg-red-900/20';

  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - result.overall_score * circumference;

  const grouped = groupByCategory(result.checks);

  return (
    <div className={`rounded-lg p-4 ${bgColor}`}>
      {/* Header with gauge */}
      <div className="flex items-center gap-4 mb-4">
        <div className="relative w-24 h-24 flex-shrink-0">
          <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
            <circle cx="50" cy="50" r={radius} fill="none" stroke="#e5e7eb" strokeWidth="8" />
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              className={strokeColor}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`text-xl font-bold ${color}`}>{score}%</span>
          </div>
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {t('completeness.title') || 'Dossier Completeness'}
          </h3>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            {stage.toUpperCase()} - {t('completeness.workflow_stage') || 'Workflow stage'}
          </p>
          {result.ready_to_proceed ? (
            <div className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 rounded-full text-xs font-medium">
              <ShieldCheck className="h-3.5 w-3.5" />
              {t('completeness.ready') || 'Ready to proceed'}
            </div>
          ) : (
            <div className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 rounded-full text-xs font-medium">
              <Shield className="h-3.5 w-3.5" />
              {t('completeness.not_ready') || 'Not ready'}
            </div>
          )}
        </div>
      </div>

      {/* Checks grouped by category */}
      <div className="space-y-3">
        {CATEGORY_ORDER.filter((cat) => grouped[cat]).map((category) => (
          <div key={category}>
            <h4 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              {t(`completeness.category.${category}`) || category}
            </h4>
            <div className="space-y-1">
              {grouped[category].map((check) => {
                const Icon = STATUS_ICONS[check.status];
                const iconColor = STATUS_COLORS[check.status];
                return (
                  <div key={check.id} className="flex items-center gap-2 text-sm">
                    <Icon className={`h-3.5 w-3.5 flex-shrink-0 ${iconColor}`} />
                    <span className="text-gray-700 dark:text-slate-300 truncate">{t(check.label_key) || check.id}</span>
                    {check.details && (
                      <span className="ml-auto text-xs text-gray-400 dark:text-slate-500 truncate max-w-[200px]">
                        {check.details}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Missing items summary */}
      {result.missing_items.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-slate-600">
          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
            {t('completeness.missing_items') || 'Missing items'}:
          </p>
          <ul className="text-xs text-gray-500 dark:text-slate-400 space-y-0.5">
            {result.missing_items.map((item: string, i: number) => (
              <li key={i} className="flex items-center gap-1.5">
                <span className="w-1 h-1 rounded-full bg-red-400 flex-shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="mt-3 text-xs text-gray-400 dark:text-slate-500 italic">
        {t('disclaimer.completeness') ||
          'Completeness estimated from recorded data. Verify with competent authorities.'}
      </p>
    </div>
  );
}
