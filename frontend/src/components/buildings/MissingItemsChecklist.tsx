import { memo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { completenessApi, type MissingItemDetail } from '@/api/completeness';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { CheckCircle2, Circle, Loader2, AlertTriangle } from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const IMPORTANCE_SORT: Record<string, number> = { critical: 0, important: 1, nice_to_have: 2 };

const IMPORTANCE_COLOR: Record<string, string> = {
  critical: 'text-red-600 dark:text-red-400',
  important: 'text-yellow-600 dark:text-yellow-400',
  nice_to_have: 'text-gray-500 dark:text-gray-400',
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

interface Props {
  buildingId: string;
}

export const MissingItemsChecklist = memo(function MissingItemsChecklist({ buildingId }: Props) {
  const { t } = useTranslation();
  const [inProgress, setInProgress] = useState<Set<string>>(new Set());

  const { data, isLoading } = useQuery({
    queryKey: ['completeness-missing', buildingId],
    queryFn: () => completenessApi.getMissingItems(buildingId),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const toggleProgress = (key: string) => {
    setInProgress((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="flex flex-col items-center py-8 text-center">
        <CheckCircle2 className="h-10 w-10 text-green-500 mb-2" />
        <p className="text-sm text-gray-600 dark:text-gray-300">
          {t('completeness.all_complete') || 'All items complete!'}
        </p>
      </div>
    );
  }

  const sorted = [...data.items].sort(
    (a, b) => (IMPORTANCE_SORT[a.importance] ?? 9) - (IMPORTANCE_SORT[b.importance] ?? 9),
  );

  // Group by dimension
  const groups: Record<string, MissingItemDetail[]> = {};
  for (const item of sorted) {
    const key = item.dimension;
    if (!groups[key]) groups[key] = [];
    groups[key].push(item);
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">
          {t('completeness.missing_checklist') || 'Missing Items Checklist'}
        </h3>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {data.total} {t('completeness.items') || 'items'}
        </span>
      </div>

      <div className="divide-y divide-gray-100 dark:divide-gray-700">
        {Object.entries(groups).map(([dimension, items]) => (
          <div key={dimension} className="px-4 py-3">
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
              {items[0]?.dimension_label || dimension.replace(/_/g, ' ')}
            </h4>
            <div className="space-y-2">
              {items.map((item) => {
                const itemKey = `${item.dimension}-${item.field}`;
                const isInProgress = inProgress.has(itemKey);

                return (
                  <button
                    key={itemKey}
                    className="flex items-center gap-2 w-full text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded px-1 py-1 transition-colors"
                    onClick={() => toggleProgress(itemKey)}
                  >
                    {isInProgress ? (
                      <CheckCircle2 className="h-4 w-4 text-blue-500 shrink-0" />
                    ) : (
                      <Circle className="h-4 w-4 text-gray-300 dark:text-gray-600 shrink-0" />
                    )}
                    <span
                      className={cn(
                        'text-sm flex-1',
                        isInProgress
                          ? 'line-through text-gray-400 dark:text-gray-500'
                          : 'text-gray-700 dark:text-gray-300',
                      )}
                    >
                      {item.field.replace(/_/g, ' ')}
                    </span>
                    <AlertTriangle
                      className={cn('h-3 w-3 shrink-0', IMPORTANCE_COLOR[item.importance] || IMPORTANCE_COLOR.nice_to_have)}
                    />
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});
