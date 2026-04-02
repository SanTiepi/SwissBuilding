import { memo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { completenessApi, type DimensionScore } from '@/api/completeness';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { ChevronDown, ChevronRight, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const BAR_COLOR: Record<string, string> = {
  green: 'bg-green-500 dark:bg-green-400',
  yellow: 'bg-yellow-500 dark:bg-yellow-400',
  orange: 'bg-orange-500 dark:bg-orange-400',
  red: 'bg-red-500 dark:bg-red-400',
};

const IMPORTANCE_BADGE: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  important: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  nice_to_have: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
};

/* ------------------------------------------------------------------ */
/*  DimensionRow                                                       */
/* ------------------------------------------------------------------ */

function DimensionRow({ dim }: { dim: DimensionScore }) {
  const [expanded, setExpanded] = useState(false);
  const hasMissing = dim.missing_items.length > 0;

  return (
    <div className="border-b border-gray-100 dark:border-gray-700 last:border-0">
      <button
        className="w-full flex items-center gap-3 py-3 px-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-left"
        onClick={() => setExpanded(!expanded)}
      >
        {hasMissing ? (
          expanded ? (
            <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-400 shrink-0" />
          )
        ) : (
          <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
              {dim.label}
            </span>
            <span
              className={cn(
                'text-sm font-semibold tabular-nums',
                dim.score >= 90
                  ? 'text-green-600 dark:text-green-400'
                  : dim.score >= 70
                    ? 'text-yellow-600 dark:text-yellow-400'
                    : dim.score >= 50
                      ? 'text-orange-600 dark:text-orange-400'
                      : 'text-red-600 dark:text-red-400',
              )}
            >
              {Math.round(dim.score)}%
            </span>
          </div>
          {/* Progress bar */}
          <div className="h-1.5 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className={cn('h-full rounded-full transition-all', BAR_COLOR[dim.color] || BAR_COLOR.red)}
              style={{ width: `${Math.min(100, dim.score)}%` }}
            />
          </div>
        </div>
      </button>

      {/* Expanded: missing items */}
      {expanded && hasMissing && (
        <div className="pl-9 pr-2 pb-3 space-y-1.5">
          {dim.missing_items.map((item) => (
            <div
              key={item.field}
              className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400"
            >
              <AlertTriangle className="h-3 w-3 text-amber-500 shrink-0" />
              <span className="flex-1">{item.field.replace(/_/g, ' ')}</span>
              <span
                className={cn(
                  'px-1.5 py-0.5 rounded text-[10px] font-medium',
                  IMPORTANCE_BADGE[item.importance] || IMPORTANCE_BADGE.nice_to_have,
                )}
              >
                {item.importance}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

interface Props {
  buildingId: string;
}

export const CompletenessBreakdown = memo(function CompletenessBreakdown({ buildingId }: Props) {
  const { t } = useTranslation();

  const { data, isLoading } = useQuery({
    queryKey: ['completeness-dashboard', buildingId],
    queryFn: () => completenessApi.getDashboard(buildingId),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">
          {t('completeness.breakdown_title') || 'Completeness Breakdown'}
        </h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          {t('completeness.breakdown_subtitle') || '16 dimensions assessed'}
        </p>
      </div>
      <div>
        {data.dimensions.map((dim) => (
          <DimensionRow key={dim.key} dim={dim} />
        ))}
      </div>
    </div>
  );
});
