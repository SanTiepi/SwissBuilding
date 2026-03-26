import { useQuery } from '@tanstack/react-query';
import { exchangeHardeningApi } from '@/api/exchangeHardening';
import { formatDate } from '@/utils/formatters';
import { GitCompare, Plus, Minus, RefreshCw } from 'lucide-react';

interface PublicationDiffViewProps {
  publicationId: string;
}

export default function PublicationDiffView({ publicationId }: PublicationDiffViewProps) {
  const {
    data: diff,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['publication-diff', publicationId],
    queryFn: () => exchangeHardeningApi.getPublicationDiff(publicationId),
    staleTime: 120_000,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-2 p-4" data-testid="diff-loading">
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-32" />
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded" />
      </div>
    );
  }

  if (error || !diff) {
    return (
      <div className="text-sm text-gray-400 p-4" data-testid="diff-error">
        {'Diff not available'}
      </div>
    );
  }

  const summary = diff.diff_summary;

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4"
      data-testid="publication-diff-view"
    >
      <div className="flex items-center gap-2 mb-3">
        <GitCompare className="w-4 h-4 text-indigo-500" />
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{'Publication Diff'}</h4>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {diff.sections_changed_count} {'section(s) changed'}
        </span>
      </div>

      {diff.prior_publication_id && (
        <p className="text-xs text-gray-400 dark:text-gray-500 mb-2">
          {'Compared to prior:'} {diff.prior_publication_id.slice(0, 8)}...
        </p>
      )}

      {summary && (
        <div className="space-y-2">
          {summary.added_sections.length > 0 && (
            <div data-testid="diff-added">
              {summary.added_sections.map((s) => (
                <div key={s} className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
                  <Plus className="w-3 h-3" />
                  <span>{s}</span>
                </div>
              ))}
            </div>
          )}

          {summary.removed_sections.length > 0 && (
            <div data-testid="diff-removed">
              {summary.removed_sections.map((s) => (
                <div key={s} className="flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
                  <Minus className="w-3 h-3" />
                  <span>{s}</span>
                </div>
              ))}
            </div>
          )}

          {summary.changed_sections.length > 0 && (
            <div data-testid="diff-changed" className="space-y-1">
              {summary.changed_sections.map((c, i) => (
                <div key={i} className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400">
                  <RefreshCw className="w-3 h-3" />
                  <span className="font-medium">
                    {c.section}.{c.field}
                  </span>
                  {c.old && <span className="line-through text-gray-400">{c.old}</span>}
                  {c.new && <span>{c.new}</span>}
                </div>
              ))}
            </div>
          )}

          {summary.added_sections.length === 0 &&
            summary.removed_sections.length === 0 &&
            summary.changed_sections.length === 0 && <p className="text-xs text-gray-400">{'No changes detected'}</p>}
        </div>
      )}

      {diff.computed_at && (
        <p className="text-xs text-gray-400 mt-2">
          {'Computed:'} {formatDate(diff.computed_at)}
        </p>
      )}
    </div>
  );
}
