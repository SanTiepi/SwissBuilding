import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { recommendationsApi, type Recommendation } from '@/api/recommendations';
import { ChevronDown, ChevronUp, AlertTriangle, Clock } from 'lucide-react';

// ---------------------------------------------------------------------------
// Priority config
// ---------------------------------------------------------------------------

const PRIORITY_STYLES: Record<number, { bg: string; text: string; border: string; label: string }> = {
  1: {
    bg: 'bg-red-100 dark:bg-red-900/30',
    text: 'text-red-700 dark:text-red-300',
    border: 'border-l-red-500',
    label: 'priority_critical',
  },
  2: {
    bg: 'bg-orange-100 dark:bg-orange-900/30',
    text: 'text-orange-700 dark:text-orange-300',
    border: 'border-l-orange-500',
    label: 'priority_high',
  },
  3: {
    bg: 'bg-yellow-100 dark:bg-yellow-900/30',
    text: 'text-yellow-700 dark:text-yellow-300',
    border: 'border-l-yellow-500',
    label: 'priority_medium',
  },
  4: {
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-700 dark:text-blue-300',
    border: 'border-l-blue-500',
    label: 'priority_low',
  },
};

const CATEGORY_ICONS: Record<string, string> = {
  remediation: '\u{1F527}',
  investigation: '\u{1F50D}',
  documentation: '\u{1F4C4}',
  compliance: '\u{2696}\u{FE0F}',
  monitoring: '\u{1F4CA}',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PriorityBadge({ priority }: { priority: number }) {
  const { t } = useTranslation();
  const style = PRIORITY_STYLES[priority] || PRIORITY_STYLES[3];
  return (
    <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', style.bg, style.text)}>
      {t(`recommendations.${style.label}`) || style.label}
    </span>
  );
}

function UrgencyBadge({ days }: { days: number | null }) {
  const { t } = useTranslation();
  if (days === null) return null;
  const isUrgent = days <= 14;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
        isUrgent
          ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
          : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
      )}
    >
      <Clock className="h-3 w-3" />
      {days}
      {t('recommendations.urgency_days_suffix') || 'd'}
    </span>
  );
}

function CostDisplay({ cost }: { cost: Recommendation['cost_estimate'] }) {
  const { t } = useTranslation();
  if (!cost) return null;
  if (cost.min === 0 && cost.max === 0) {
    return <span className="text-xs text-green-600 dark:text-green-400">{t('recommendations.free') || 'Free'}</span>;
  }
  return (
    <span className="text-xs text-gray-500 dark:text-gray-400">
      {t('recommendations.cost_estimate') || 'Cost'}: {cost.min.toLocaleString()}-{cost.max.toLocaleString()}{' '}
      {cost.currency}
    </span>
  );
}

function RecommendationCard({ rec }: { rec: Recommendation }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const style = PRIORITY_STYLES[rec.priority] || PRIORITY_STYLES[3];
  const categoryIcon = CATEGORY_ICONS[rec.category] || '\u{2139}\u{FE0F}';
  const categoryLabel = t(`recommendations.category_${rec.category}`) || rec.category;

  return (
    <div
      className={cn(
        'rounded-lg border border-l-4 bg-white p-4 shadow-sm transition-shadow hover:shadow-md dark:bg-gray-800',
        style.border,
        'border-gray-200 dark:border-gray-700',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="text-base" title={categoryLabel}>
              {categoryIcon}
            </span>
            <PriorityBadge priority={rec.priority} />
            <UrgencyBadge days={rec.urgency_days} />
            <span className="text-xs text-gray-400 dark:text-gray-500">{categoryLabel}</span>
          </div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{rec.title}</h4>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{rec.description}</p>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-1 flex-shrink-0 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
          aria-label={expanded ? 'Collapse' : 'Expand'}
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      {expanded && (
        <div className="mt-3 space-y-2 border-t border-gray-100 pt-3 dark:border-gray-700">
          <div>
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
              {t('recommendations.why') || 'Why'}:
            </span>
            <p className="text-sm text-gray-700 dark:text-gray-300">{rec.why}</p>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <CostDisplay cost={rec.cost_estimate} />
            {rec.impact_score > 0 && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Impact: {Math.round(rec.impact_score * 100)}%
              </span>
            )}
            <span className="text-xs text-gray-400 dark:text-gray-500">
              {t('recommendations.source') || 'Source'}: {rec.source}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface RecommendationListProps {
  buildingId: string;
}

export function RecommendationList({ buildingId }: RecommendationListProps) {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['recommendations', buildingId],
    queryFn: () => recommendationsApi.list(buildingId),
    enabled: !!buildingId,
  });

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
        {t('recommendations.title') || 'Recommendations'}
      </h3>

      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500" />
          {t('app.loading') || 'Loading...'}
        </div>
      )}

      {isError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          <AlertTriangle className="h-4 w-4" />
          {t('app.loading_error') || 'Failed to load data'}
        </div>
      )}

      {data && data.recommendations.length === 0 && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-center text-sm text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300">
          {t('recommendations.empty') || 'No recommendations -- building is well-managed!'}
        </div>
      )}

      {data && data.recommendations.length > 0 && (
        <div className="space-y-2">
          {data.recommendations.map((rec) => (
            <RecommendationCard key={rec.id} rec={rec} />
          ))}
        </div>
      )}
    </div>
  );
}
