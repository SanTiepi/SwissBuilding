import { useQuery } from '@tanstack/react-query';
import { readinessApi } from '@/api/readiness';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { Shield, CheckCircle2, XCircle, AlertTriangle, ChevronRight } from 'lucide-react';
import type { ReadinessAssessment, ReadinessStatus } from '@/types';
import { AsyncStateWrapper } from './AsyncStateWrapper';

const STATUS_CONFIG: Record<ReadinessStatus, { color: string; icon: typeof CheckCircle2 }> = {
  ready: { color: 'text-green-600 dark:text-green-400', icon: CheckCircle2 },
  conditionally_ready: { color: 'text-yellow-600 dark:text-yellow-400', icon: AlertTriangle },
  not_ready: { color: 'text-red-600 dark:text-red-400', icon: XCircle },
  blocked: { color: 'text-red-700 dark:text-red-500', icon: XCircle },
};

const READINESS_LABELS: Record<string, string> = {
  safe_to_start: 'readiness.safe_to_start',
  safe_to_tender: 'readiness.safe_to_tender',
  safe_to_reopen: 'readiness.safe_to_reopen',
  safe_to_requalify: 'readiness.safe_to_requalify',
};

/** Map blocker label keywords to building detail tab keys */
function blockerToTab(label: string): string | null {
  const lower = label.toLowerCase();
  if (lower.includes('diagnostic') || lower.includes('sample') || lower.includes('pollutant')) return 'diagnostics';
  if (lower.includes('document') || lower.includes('evidence') || lower.includes('report') || lower.includes('proof'))
    return 'documents';
  if (lower.includes('ownership') || lower.includes('owner')) return 'ownership';
  if (lower.includes('lease') || lower.includes('tenant')) return 'leases';
  if (lower.includes('contract')) return 'contracts';
  if (lower.includes('procedure') || lower.includes('compliance') || lower.includes('regulatory')) return 'procedures';
  return null;
}

export function ReadinessSummary({
  buildingId,
  onNavigateTab,
}: {
  buildingId: string;
  onNavigateTab?: (tab: string) => void;
}) {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['building-readiness', buildingId],
    queryFn: () => readinessApi.list(buildingId),
    enabled: !!buildingId,
  });

  const assessments = data?.items ?? [];

  // Group by readiness_type, take the latest per type
  const latestByType = new Map<string, ReadinessAssessment>();
  for (const a of assessments) {
    const existing = latestByType.get(a.readiness_type);
    if (!existing || a.assessed_at > existing.assessed_at) {
      latestByType.set(a.readiness_type, a);
    }
  }

  return (
    <AsyncStateWrapper
      isLoading={isLoading}
      isError={isError}
      data={data}
      variant="card"
      title={t('readiness.title') || 'Readiness'}
      icon={<Shield className="w-5 h-5" />}
      emptyMessage={t('readiness.no_assessment') || 'No readiness assessment available'}
      isEmpty={!isLoading && !isError && assessments.length === 0}
    >
      <div className="flex items-center gap-2 mb-4">
        <Shield className="w-5 h-5 text-gray-500 dark:text-slate-400" />
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{t('readiness.title') || 'Readiness'}</h3>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {['safe_to_start', 'safe_to_tender', 'safe_to_reopen', 'safe_to_requalify'].map((type) => {
          const assessment = latestByType.get(type);
          const config = assessment ? STATUS_CONFIG[assessment.status as ReadinessStatus] : null;
          const Icon = config?.icon ?? Shield;

          return (
            <div
              key={type}
              className="flex items-center gap-2 p-2 rounded-lg bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600"
            >
              <Icon className={cn('w-4 h-4 flex-shrink-0', config?.color ?? 'text-gray-300 dark:text-slate-500')} />
              <div className="min-w-0">
                <p className="text-xs font-medium text-gray-700 dark:text-slate-200 truncate">
                  {t(READINESS_LABELS[type]) || type.replace(/_/g, ' ')}
                </p>
                {assessment && (
                  <p className={cn('text-xs truncate', config?.color ?? 'text-gray-400')}>
                    {t(`readiness.status.${assessment.status}`) || assessment.status}
                  </p>
                )}
                {!assessment && (
                  <p className="text-xs text-gray-400 dark:text-slate-500">
                    {t('readiness.not_evaluated') || 'Not evaluated'}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {/* Show blockers if any */}
      {Array.from(latestByType.values()).some((a) => a.blockers_json && a.blockers_json.length > 0) && (
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-slate-600">
          <p className="text-xs font-medium text-red-600 dark:text-red-400 mb-1">
            {t('readiness.blockers') || 'Blockers'}
          </p>
          <ul className="space-y-1">
            {Array.from(latestByType.values())
              .flatMap((a) => a.blockers_json ?? [])
              .slice(0, 3)
              .map((blocker, i) => {
                const targetTab = blockerToTab(blocker.label);
                return (
                  <li key={i} className="text-xs text-gray-600 dark:text-slate-300 flex items-start gap-1">
                    <XCircle className="w-3 h-3 text-red-400 mt-0.5 flex-shrink-0" />
                    <span className="flex-1">{blocker.label}</span>
                    {onNavigateTab && targetTab && (
                      <button
                        onClick={() => onNavigateTab(targetTab)}
                        className="flex-shrink-0 inline-flex items-center text-red-500 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 transition-colors"
                        title={t('form.view') || 'Voir'}
                      >
                        <ChevronRight className="w-3 h-3" />
                      </button>
                    )}
                  </li>
                );
              })}
          </ul>
        </div>
      )}
      <p className="mt-3 text-xs text-gray-400 dark:text-slate-500 italic">
        {t('disclaimer.readiness') || 'Readiness indicators based on available data. Not a legal compliance guarantee.'}
      </p>
    </AsyncStateWrapper>
  );
}
