/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view under BuildingDetail (Building Home).
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useBuilding } from '@/hooks/useBuildings';
import { transactionReadinessApi } from '@/api/transactionReadiness';
import { formatDate } from '@/utils/formatters';
import { BuildingSubNav } from '@/components/BuildingSubNav';
import type { TransactionType, TransactionStatus, TransactionReadiness } from '@/api/transactionReadiness';
import {
  ArrowLeft,
  KeyRound,
  Shield,
  Banknote,
  Home,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Minus,
  Info,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

const TRANSACTION_TYPES: TransactionType[] = ['sell', 'insure', 'finance', 'lease'];

const TYPE_ICONS: Record<TransactionType, React.ElementType> = {
  sell: KeyRound,
  insure: Shield,
  finance: Banknote,
  lease: Home,
};

function statusColor(status: TransactionStatus): string {
  switch (status) {
    case 'ready':
      return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
    case 'conditional':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
    case 'not_ready':
      return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
    default:
      return 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400';
  }
}

function progressBarColor(score: number): string {
  const pct = score * 100;
  if (pct >= 80) return 'bg-green-500';
  if (pct >= 50) return 'bg-yellow-500';
  return 'bg-red-500';
}

export default function SafeToXCockpit() {
  const { buildingId } = useParams<{ buildingId: string }>();
  const { t } = useTranslation();
  const { data: building } = useBuilding(buildingId || '');

  const {
    data: readinessData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['transaction-readiness', buildingId],
    queryFn: () => transactionReadinessApi.evaluateAll(buildingId!),
    enabled: !!buildingId,
  });

  const items = readinessData || [];

  const getReadiness = (type: TransactionType): TransactionReadiness | undefined => {
    return items.find((r) => r.transaction_type === type);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <Link
          to={`/buildings/${buildingId}`}
          className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
        >
          <ArrowLeft className="w-4 h-4" />
          {building?.address || t('safe_to.back_to_building') || 'Back to building'}
        </Link>
        <div className="w-full">
          <BuildingSubNav buildingId={buildingId!} />
        </div>
        <div className="flex items-center gap-3">
          <Shield className="w-6 h-6 text-red-600" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('safe_to.title') || 'Transaction Readiness'}
          </h1>
        </div>
        {/* Spacer to balance flex layout */}
        <div className="w-32 hidden sm:block" />
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {TRANSACTION_TYPES.map((type) => (
            <div
              key={type}
              className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6 animate-pulse"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-gray-200 dark:bg-slate-600" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 dark:bg-slate-600 rounded w-1/3" />
                  <div className="h-3 bg-gray-200 dark:bg-slate-600 rounded w-1/4" />
                </div>
              </div>
              <div className="h-2 bg-gray-200 dark:bg-slate-600 rounded-full w-full" />
            </div>
          ))}
        </div>
      )}

      {/* Error state */}
      {!isLoading && isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center dark:border-red-900/50 dark:bg-red-950/20">
          <AlertTriangle className="mx-auto mb-2 h-6 w-6 text-red-500" />
          <p className="text-sm font-medium text-red-700 dark:text-red-300">
            {t('safe_to.error') || 'Failed to load transaction readiness'}
          </p>
        </div>
      )}

      {/* 2x2 Grid */}
      {!isLoading && !isError && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {TRANSACTION_TYPES.map((type) => {
            const readiness = getReadiness(type);
            return <TransactionCard key={type} type={type} readiness={readiness} t={t} />;
          })}
        </div>
      )}

      {/* Disclaimer */}
      <div className="flex items-start gap-2 p-4 bg-gray-50 dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700">
        <Info className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-gray-500 dark:text-slate-400">
          {t('disclaimer.readiness_wallet') || 'Regulatory readiness overview. Not legal advice.'}
        </p>
      </div>
    </div>
  );
}

function TransactionCard({
  type,
  readiness,
  t,
}: {
  type: TransactionType;
  readiness: TransactionReadiness | undefined;
  t: (key: string) => string;
}) {
  const [expanded, setExpanded] = useState(false);
  const Icon = TYPE_ICONS[type];
  const typeLabel = t(`safe_to.${type}`) || type;

  if (!readiness) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-slate-700 flex items-center justify-center">
            <Icon className="w-5 h-5 text-gray-400 dark:text-slate-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{typeLabel}</h3>
            <span className="px-2.5 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400">
              {t('safe_to.empty') || 'Not evaluated'}
            </span>
          </div>
        </div>
      </div>
    );
  }

  const { overall_status, score, blockers, conditions, recommendations, checks, evaluated_at } = readiness;
  const pct = Math.round(score * 100);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6 space-y-4">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-red-50 dark:bg-red-900/20 flex items-center justify-center">
            <Icon className="w-5 h-5 text-red-600 dark:text-red-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{typeLabel}</h3>
            <span
              className={`inline-block mt-0.5 px-2.5 py-0.5 text-xs font-medium rounded-full ${statusColor(overall_status)}`}
            >
              {t(`safe_to.${overall_status}`) || overall_status}
            </span>
          </div>
        </div>

        {/* Badges */}
        <div className="flex items-center gap-2">
          {blockers.length > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
              <XCircle className="w-3 h-3" />
              {blockers.length}
            </span>
          )}
          {conditions.length > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
              <AlertTriangle className="w-3 h-3" />
              {conditions.length}
            </span>
          )}
        </div>
      </div>

      {/* Score + progress bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600 dark:text-slate-400">{t('safe_to.score') || 'Score'}</span>
          <span className="font-semibold text-gray-900 dark:text-white">{pct}%</span>
        </div>
        <div className="w-full h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${progressBarColor(score)}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Expand/collapse toggle */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 transition-colors"
      >
        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        {expanded ? t('safe_to.collapse') || 'Collapse' : t('safe_to.expand') || 'Show details'}
      </button>

      {/* Expandable details */}
      {expanded && (
        <div className="space-y-3 pt-2 border-t border-gray-100 dark:border-slate-700">
          {/* Blockers */}
          {blockers.length > 0 && (
            <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3">
              <h4 className="text-sm font-medium text-red-800 dark:text-red-300 mb-2 flex items-center gap-1.5">
                <XCircle className="w-4 h-4" />
                {t('safe_to.blockers') || 'Blockers'}
              </h4>
              <ul className="space-y-1">
                {blockers.map((blocker, i) => (
                  <li key={i} className="text-sm text-red-700 dark:text-red-300 flex items-start gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                    <div>
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

          {/* Conditions */}
          {conditions.length > 0 && (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3">
              <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-300 mb-2 flex items-center gap-1.5">
                <Info className="w-4 h-4" />
                {t('safe_to.conditions') || 'Conditions'}
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

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
              <h4 className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-2 flex items-center gap-1.5">
                <Info className="w-4 h-4" />
                {t('safe_to.recommendations') || 'Recommendations'}
              </h4>
              <ul className="space-y-1">
                {recommendations.map((rec, i) => (
                  <li key={i} className="text-sm text-blue-700 dark:text-blue-300 flex items-start gap-2">
                    <Minus className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                    <div>
                      <span>{rec.label}</span>
                      {rec.details && (
                        <span className="block text-xs text-blue-600 dark:text-blue-400">{rec.details}</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Checks */}
          {checks.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                {t('safe_to.checks') || 'Checks'}
              </h4>
              <ul className="space-y-1.5">
                {checks.map((check, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    {check.passed ? (
                      <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                    )}
                    <div className="min-w-0">
                      <span className="text-gray-800 dark:text-slate-200">{check.label}</span>
                      {check.details && (
                        <span className="block text-xs text-gray-500 dark:text-slate-400">{check.details}</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Last evaluated */}
      <div className="text-xs text-gray-400 dark:text-slate-500 pt-2 border-t border-gray-100 dark:border-slate-700">
        {t('safe_to.evaluated_at') || 'Evaluated'}: {formatDate(evaluated_at)}
      </div>
    </div>
  );
}
