import { memo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { completenessApi, type DimensionScore } from '@/api/completeness';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { TrendingUp, TrendingDown, Minus, Loader2, BarChart3 } from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const COLOR_MAP: Record<string, string> = {
  green: 'bg-green-500 dark:bg-green-400',
  yellow: 'bg-yellow-500 dark:bg-yellow-400',
  orange: 'bg-orange-500 dark:bg-orange-400',
  red: 'bg-red-500 dark:bg-red-400',
};

const BG_MAP: Record<string, string> = {
  green: 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800',
  yellow: 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800',
  orange: 'bg-orange-50 border-orange-200 dark:bg-orange-900/20 dark:border-orange-800',
  red: 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800',
};

const TEXT_MAP: Record<string, string> = {
  green: 'text-green-700 dark:text-green-300',
  yellow: 'text-yellow-700 dark:text-yellow-300',
  orange: 'text-orange-700 dark:text-orange-300',
  red: 'text-red-700 dark:text-red-300',
};

function TrendIndicator({ trend }: { trend: string }) {
  if (trend === 'improving') return <TrendingUp className="h-4 w-4 text-green-500" />;
  if (trend === 'declining') return <TrendingDown className="h-4 w-4 text-red-500" />;
  return <Minus className="h-4 w-4 text-gray-400 dark:text-gray-500" />;
}

function DimensionCircle({ dim }: { dim: DimensionScore }) {
  return (
    <div className="flex flex-col items-center gap-1" title={`${dim.label}: ${Math.round(dim.score)}%`}>
      <div
        className={cn('h-6 w-6 rounded-full', COLOR_MAP[dim.color] || COLOR_MAP.red)}
        aria-label={`${dim.label} ${Math.round(dim.score)}%`}
      />
      <span className="text-[10px] text-gray-500 dark:text-gray-400 truncate max-w-[48px] text-center">
        {dim.label.split(' ')[0]}
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

interface Props {
  buildingId: string;
  onClick?: () => void;
}

export const CompletenessCard = memo(function CompletenessCard({ buildingId, onClick }: Props) {
  const { t } = useTranslation();

  const { data, isLoading } = useQuery({
    queryKey: ['completeness-dashboard', buildingId],
    queryFn: () => completenessApi.getDashboard(buildingId),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="p-4 border rounded-lg bg-white dark:bg-gray-800 animate-pulse flex items-center justify-center h-40">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!data) return null;

  const color = data.overall_color || 'red';

  return (
    <div
      className={cn(
        'p-4 border rounded-lg cursor-pointer hover:shadow-md transition-shadow',
        BG_MAP[color] || BG_MAP.red,
      )}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-gray-600 dark:text-gray-300" />
          <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">
            {t('completeness.dashboard_title') || 'Dossier Completeness'}
          </h3>
        </div>
        <TrendIndicator trend={data.trend} />
      </div>

      {/* Big score */}
      <div className="flex items-end gap-2 mb-4">
        <span className={cn('text-4xl font-bold', TEXT_MAP[color] || TEXT_MAP.red)}>
          {Math.round(data.overall_score)}%
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400 mb-1">
          {data.missing_items_count > 0
            ? `${data.missing_items_count} ${t('completeness.missing') || 'missing'}`
            : t('completeness.complete') || 'Complete'}
        </span>
      </div>

      {/* 16 dimension circles — 4×4 grid */}
      <div className="grid grid-cols-8 gap-1.5">
        {data.dimensions.map((dim) => (
          <DimensionCircle key={dim.key} dim={dim} />
        ))}
      </div>

      {/* Urgent actions badge */}
      {data.urgent_actions > 0 && (
        <div className="mt-3 text-xs font-medium text-red-600 dark:text-red-400">
          {data.urgent_actions} {t('completeness.urgent_actions') || 'urgent action(s)'}
        </div>
      )}
    </div>
  );
});
