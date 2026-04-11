import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { completenessApi } from '@/api/completeness';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { CompletenessBreakdown } from '@/components/buildings/CompletenessBreakdown';
import { MissingItemsChecklist } from '@/components/buildings/MissingItemsChecklist';
import { TrendingUp, TrendingDown, Minus, ArrowLeft, Loader2, BarChart3 } from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Sparkline                                                          */
/* ------------------------------------------------------------------ */

function CompletionTrend({ trend }: { trend: string }) {
  // Simple visual trend indicator (sparkline placeholder)
  const dots = trend === 'improving' ? [30, 45, 55, 65, 80] : trend === 'declining' ? [80, 65, 55, 45, 30] : [50, 52, 48, 51, 50];
  const maxH = 24;

  return (
    <div className="flex items-end gap-0.5 h-6">
      {dots.map((v, i) => (
        <div
          key={i}
          className={cn(
            'w-1.5 rounded-full',
            trend === 'improving'
              ? 'bg-green-400 dark:bg-green-500'
              : trend === 'declining'
                ? 'bg-red-400 dark:bg-red-500'
                : 'bg-gray-300 dark:bg-gray-600',
          )}
          style={{ height: `${(v / 100) * maxH}px` }}
        />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Actions Panel                                                      */
/* ------------------------------------------------------------------ */

function ActionsPanel({ buildingId }: { buildingId: string }) {
  const { t } = useTranslation();

  const { data, isLoading } = useQuery({
    queryKey: ['completeness-actions', buildingId],
    queryFn: () => completenessApi.getRecommendedActions(buildingId),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  if (isLoading) return <Loader2 className="h-5 w-5 animate-spin text-gray-400 mx-auto" />;
  if (!data || data.actions.length === 0) return null;

  const priorityColor: Record<string, string> = {
    critical: 'border-l-red-500',
    important: 'border-l-yellow-500',
    nice_to_have: 'border-l-gray-300 dark:border-l-gray-600',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">
          {t('completeness.recommended_actions') || 'Recommended Actions'}
        </h3>
      </div>
      <div className="divide-y divide-gray-100 dark:divide-gray-700">
        {data.actions.slice(0, 15).map((a, i) => (
          <div
            key={i}
            className={cn(
              'px-4 py-2.5 border-l-4',
              priorityColor[a.priority] || priorityColor.nice_to_have,
            )}
          >
            <div className="text-sm text-gray-900 dark:text-gray-100">{a.action}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {a.dimension_label} · {a.effort} effort
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function CompletenessDetail() {
  const { buildingId } = useParams<{ buildingId: string }>();
  const { t } = useTranslation();

  const { data, isLoading } = useQuery({
    queryKey: ['completeness-dashboard', buildingId],
    queryFn: () => completenessApi.getDashboard(buildingId!),
    enabled: !!buildingId,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  if (!buildingId) return null;

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          to={`/buildings/${buildingId}`}
          className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <ArrowLeft className="h-5 w-5 text-gray-600 dark:text-gray-300" />
        </Link>
        <div className="flex items-center gap-2">
          <BarChart3 className="h-6 w-6 text-gray-600 dark:text-gray-300" />
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            {t('completeness.detail_title') || 'Dossier Completeness'}
          </h1>
        </div>
      </div>

      {/* Summary bar */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : data ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg border p-4 border-gray-200 dark:border-gray-700">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                {t('completeness.overall') || 'Overall'}
              </div>
              <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                {Math.round(data.overall_score)}%
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border p-4 border-gray-200 dark:border-gray-700">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                {t('completeness.missing') || 'Missing'}
              </div>
              <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                {data.missing_items_count}
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border p-4 border-gray-200 dark:border-gray-700">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                {t('completeness.urgent') || 'Urgent'}
              </div>
              <div className="text-3xl font-bold text-red-600 dark:text-red-400">
                {data.urgent_actions}
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border p-4 border-gray-200 dark:border-gray-700">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                {t('completeness.trend') || 'Trend'}
              </div>
              <div className="flex items-center gap-2 mt-1">
                {data.trend === 'improving' && <TrendingUp className="h-6 w-6 text-green-500" />}
                {data.trend === 'declining' && <TrendingDown className="h-6 w-6 text-red-500" />}
                {data.trend === 'stable' && <Minus className="h-6 w-6 text-gray-400" />}
                <CompletionTrend trend={data.trend} />
              </div>
            </div>
          </div>

          {/* Two-column layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <CompletenessBreakdown buildingId={buildingId} />
            <div className="space-y-6">
              <MissingItemsChecklist buildingId={buildingId} />
              <ActionsPanel buildingId={buildingId} />
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
