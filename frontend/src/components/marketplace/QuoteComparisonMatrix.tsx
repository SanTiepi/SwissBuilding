import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { remediationApi } from '@/api/remediation';
import type { QuoteComparisonMatrix as MatrixType, QuoteComparisonRow } from '@/api/remediation';
import { formatDate, cn } from '@/utils/formatters';
import { AlertTriangle } from 'lucide-react';

function ConfidenceBadge({ confidence }: { confidence: number | null }) {
  if (confidence === null) return <span className="text-xs text-gray-400">--</span>;
  const pct = Math.round(confidence * 100);
  const color =
    pct >= 80
      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
      : pct >= 60
        ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
        : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
  return <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', color)}>{pct}%</span>;
}

interface Props {
  requestId: string;
}

export function QuoteComparisonMatrix({ requestId }: Props) {
  const { t } = useTranslation();

  const { data, isLoading, error } = useQuery<MatrixType>({
    queryKey: ['quote-comparison', requestId],
    queryFn: () => remediationApi.getComparisonMatrix(requestId),
    enabled: !!requestId,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        <div className="h-6 bg-gray-200 dark:bg-slate-700 rounded w-1/4" />
        <div className="h-48 bg-gray-200 dark:bg-slate-700 rounded" />
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-red-600 dark:text-red-400">{t('workspace.load_error') || 'Failed to load comparison.'}</p>
    );
  }

  if (!data || data.rows.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-slate-400">
        {t('workspace.no_quotes') || 'No submitted quotes for comparison.'}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        {t('workspace.comparison_title') || 'Quote Comparison'}
      </h3>
      <table className="min-w-full divide-y divide-gray-200 dark:divide-slate-700">
        <thead className="bg-gray-50 dark:bg-slate-800">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">
              {t('workspace.company') || 'Company'}
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">
              {t('workspace.amount_chf') || 'Amount (CHF)'}
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">
              {t('workspace.timeline_weeks') || 'Timeline (weeks)'}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">
              {t('workspace.scope') || 'Scope'}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">
              {t('workspace.exclusions') || 'Exclusions'}
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">
              {t('workspace.confidence') || 'Confidence'}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">
              {t('workspace.submitted_at') || 'Submitted'}
            </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-slate-900 divide-y divide-gray-200 dark:divide-slate-700">
          {data.rows.map((row: QuoteComparisonRow, idx: number) => (
            <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-slate-800/50">
              <td className="px-4 py-3 text-sm text-gray-900 dark:text-white font-medium">
                {row.company_name}
                {row.ambiguous_fields.length > 0 && <AlertTriangle className="inline w-4 h-4 ml-1 text-amber-500" />}
              </td>
              <td className="px-4 py-3 text-sm text-right text-gray-900 dark:text-white">
                {row.amount_chf !== null ? row.amount_chf.toLocaleString('fr-CH') : '--'}
              </td>
              <td className="px-4 py-3 text-sm text-right text-gray-900 dark:text-white">
                {row.timeline_weeks ?? '--'}
              </td>
              <td className="px-4 py-3 text-sm text-gray-700 dark:text-slate-300">
                <div className="flex flex-wrap gap-1">
                  {row.scope_items.map((item, i) => (
                    <span
                      key={i}
                      className="text-xs bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </td>
              <td className="px-4 py-3 text-sm text-gray-700 dark:text-slate-300">
                <div className="flex flex-wrap gap-1">
                  {row.exclusions.map((item, i) => (
                    <span
                      key={i}
                      className="text-xs bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 px-1.5 py-0.5 rounded"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </td>
              <td className="px-4 py-3 text-center">
                <ConfidenceBadge confidence={row.confidence} />
              </td>
              <td className="px-4 py-3 text-sm text-gray-500 dark:text-slate-400">
                {row.submitted_at ? formatDate(row.submitted_at) : '--'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default QuoteComparisonMatrix;
