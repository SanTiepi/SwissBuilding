import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { contradictionsApi } from '@/api/contradictions';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { toast } from '@/store/toastStore';
import { AsyncStateWrapper } from '@/components/AsyncStateWrapper';
import { ContradictionPanel } from '@/components/ContradictionPanel';
import { AlertTriangle, CheckCircle2, Loader2, Search, Maximize2, Minimize2 } from 'lucide-react';

const TYPE_KEYS = [
  'conflicting_sample_results',
  'inconsistent_risk_levels',
  'pollutant_type_discrepancy',
  'duplicate_samples',
  'construction_year_conflict',
] as const;

const SEVERITY_COLORS: Record<string, string> = {
  conflicting_sample_results: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  inconsistent_risk_levels: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  pollutant_type_discrepancy: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  duplicate_samples: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  construction_year_conflict: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
};

export function ContradictionCard({ buildingId }: { buildingId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);

  const {
    data: summary,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['contradictions', 'summary', buildingId],
    queryFn: () => contradictionsApi.summary(buildingId),
    enabled: !!buildingId,
  });

  const detectMutation = useMutation({
    mutationFn: () => contradictionsApi.detect(buildingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contradictions', 'summary', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['contradiction-issues'] });
    },
    onError: (err: any) => {
      toast(err?.response?.data?.detail || err?.message || t('app.error') || 'An error occurred');
    },
  });

  const total = summary?.total ?? 0;
  const unresolved = summary?.unresolved ?? 0;
  const resolved = summary?.resolved ?? 0;
  const byType = summary?.by_type ?? {};

  const activeTypes = TYPE_KEYS.filter((k) => (byType[k] ?? 0) > 0);

  // Full expanded view
  if (expanded) {
    return (
      <div className="col-span-full bg-white dark:bg-slate-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-slate-600">
        <div className="flex items-center justify-end mb-2">
          <button
            onClick={() => setExpanded(false)}
            className="flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
          >
            <Minimize2 className="w-3.5 h-3.5" />
            {t('contradiction.collapse')}
          </button>
        </div>
        <ContradictionPanel buildingId={buildingId} />
      </div>
    );
  }

  return (
    <AsyncStateWrapper
      isLoading={isLoading}
      isError={isError}
      data={summary}
      isEmpty={false}
      icon={<AlertTriangle className="w-5 h-5" />}
      title={t('contradiction.title') || 'Contradictions'}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            {t('contradiction.title') || 'Contradictions'}
          </h3>
        </div>

        <div className="flex items-center gap-2">
          {total > 0 && (
            <button
              onClick={() => setExpanded(true)}
              className="flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
              title={t('contradiction.expand')}
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          )}
          {total > 0 && (
            <span
              className={cn(
                'inline-flex items-center justify-center min-w-[1.5rem] h-6 px-2 rounded-full text-xs font-bold',
                unresolved > 0
                  ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'
                  : 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
              )}
            >
              {total}
            </span>
          )}
        </div>
      </div>

      {total === 0 ? (
        <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
          <CheckCircle2 className="w-4 h-4" />
          <span>{t('contradiction.none') || 'Aucune contradiction detectee'}</span>
        </div>
      ) : (
        <>
          {/* Type pills */}
          <div className="flex flex-wrap gap-1.5 mb-3">
            {activeTypes.map((typeKey) => (
              <span
                key={typeKey}
                className={cn(
                  'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs',
                  SEVERITY_COLORS[typeKey],
                )}
              >
                {t(`contradiction.type.${typeKey}`) || typeKey}
                <span className="font-bold">{byType[typeKey]}</span>
              </span>
            ))}
          </div>

          {/* Resolved / Unresolved progress */}
          <div className="space-y-1.5">
            <div className="h-2 rounded-full overflow-hidden flex bg-gray-200 dark:bg-slate-600">
              {resolved > 0 && (
                <div className="h-full bg-green-500" style={{ width: `${(resolved / total) * 100}%` }} />
              )}
              {unresolved > 0 && (
                <div className="h-full bg-red-400" style={{ width: `${(unresolved / total) * 100}%` }} />
              )}
            </div>
            <div className="flex justify-between text-xs text-gray-500 dark:text-slate-400">
              <span>
                {resolved} {t('contradiction.resolved') || 'Resolues'}
              </span>
              <span>
                {unresolved} {t('contradiction.unresolved') || 'Non resolues'}
              </span>
            </div>
          </div>

          {/* View All button */}
          <button
            onClick={() => setExpanded(true)}
            className={cn(
              'mt-3 w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
              'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300',
              'hover:bg-red-100 dark:hover:bg-red-900/30',
            )}
          >
            <Maximize2 className="w-3.5 h-3.5" />
            {t('contradiction.view_all')}
          </button>
        </>
      )}

      {/* Scan button */}
      <button
        onClick={() => detectMutation.mutate()}
        disabled={detectMutation.isPending}
        className={cn(
          'mt-2 w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
          'bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-slate-200',
          'hover:bg-gray-300 dark:hover:bg-slate-500',
          'disabled:opacity-50 disabled:cursor-not-allowed',
        )}
      >
        {detectMutation.isPending ? (
          <>
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            {t('contradiction.scanning') || 'Analyse en cours...'}
          </>
        ) : (
          <>
            <Search className="w-3.5 h-3.5" />
            {t('contradiction.scan') || 'Analyser'}
          </>
        )}
      </button>
    </AsyncStateWrapper>
  );
}
