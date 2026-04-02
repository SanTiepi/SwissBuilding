/**
 * Admin AI Metrics Board — accuracy trends, top errors, correction rates.
 * Programme I: AI Feedback Loop v1.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { aiFeedbackApi, type AIMetricsRead } from '@/api/aiFeedback';
import { Loader2, Bot, TrendingUp, AlertTriangle, CheckCircle2, BarChart3 } from 'lucide-react';

const ENTITY_TYPES = ['diagnostic', 'material', 'sample'] as const;

function AccuracyBadge({ rate }: { rate: number }) {
  const pct = ((1 - rate) * 100).toFixed(1);
  const color =
    rate <= 0.05
      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
      : rate <= 0.15
        ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
        : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}>{pct}%</span>;
}

export default function AdminAIMetricsBoard() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const [filterType, setFilterType] = useState<string | undefined>(undefined);

  const { data, isLoading, error } = useQuery({
    queryKey: ['ai-metrics', filterType],
    queryFn: () => aiFeedbackApi.getMetrics(filterType).then((r) => r.data),
    refetchInterval: 60_000,
  });

  if (!user || user.role !== 'admin') {
    return (
      <div className="flex items-center justify-center p-12 text-gray-500 dark:text-gray-400">
        {t('common.access_denied') || 'Access denied'}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bot className="h-6 w-6 text-blue-500" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('ai_metrics.title') || 'AI Learning Dashboard'}
          </h1>
        </div>
        <select
          value={filterType || ''}
          onChange={(e) => setFilterType(e.target.value || undefined)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
        >
          <option value="">{t('ai_metrics.all_types') || 'All entity types'}</option>
          {ENTITY_TYPES.map((et) => (
            <option key={et} value={et}>
              {et}
            </option>
          ))}
        </select>
      </div>

      {isLoading && (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      )}

      {error && (
        <div className="rounded bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
          {t('common.error') || 'Failed to load metrics'}
        </div>
      )}

      {data && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <CheckCircle2 className="h-4 w-4" />
                {t('ai_metrics.overall_accuracy') || 'Overall Accuracy'}
              </div>
              <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
                {(data.overall_accuracy * 100).toFixed(1)}%
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <BarChart3 className="h-4 w-4" />
                {t('ai_metrics.total_extractions') || 'Total Extractions'}
              </div>
              <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
                {data.total_extractions.toLocaleString()}
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <AlertTriangle className="h-4 w-4" />
                {t('ai_metrics.total_corrections') || 'Total Corrections'}
              </div>
              <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
                {data.total_corrections.toLocaleString()}
              </p>
            </div>
          </div>

          {/* Per-field metrics table */}
          {data.metrics.length > 0 ? (
            <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                      {t('ai_metrics.entity_type') || 'Entity Type'}
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                      {t('ai_metrics.field_name') || 'Field'}
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                      {t('ai_metrics.accuracy') || 'Accuracy'}
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                      {t('ai_metrics.extractions') || 'Extractions'}
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                      {t('ai_metrics.corrections') || 'Corrections'}
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                      {t('ai_metrics.top_errors') || 'Top Errors'}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                  {data.metrics.map((m: AIMetricsRead) => (
                    <tr key={m.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                      <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
                        {m.entity_type}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-sm text-gray-700 dark:text-gray-300">
                        {m.field_name}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right">
                        <AccuracyBadge rate={m.error_rate} />
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-600 dark:text-gray-400">
                        {m.total_extractions}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-600 dark:text-gray-400">
                        {m.total_corrections}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {m.common_errors.slice(0, 3).map((err, i) => (
                          <div key={i} className="text-xs text-gray-500 dark:text-gray-400">
                            <span className="line-through text-red-400">{err.original}</span>
                            {' → '}
                            <span className="text-green-600 dark:text-green-400">{err.corrected}</span>
                            <span className="ml-1 text-gray-400">({err.count}x)</span>
                          </div>
                        ))}
                        {m.common_errors.length === 0 && (
                          <span className="text-xs text-gray-400">{t('common.none') || '—'}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 py-12 text-gray-400 dark:text-gray-500">
              <TrendingUp className="h-10 w-10" />
              <p className="text-sm">{t('ai_metrics.no_data') || 'No AI metrics yet. Corrections will appear here.'}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
