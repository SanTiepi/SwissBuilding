import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { remediationIntelligenceApi } from '@/api/remediationIntelligence';
import type { ScopeCoverageItem } from '@/api/remediationIntelligence';
import { BarChart3, AlertTriangle } from 'lucide-react';

function ScopeMatrix({ items }: { items: ScopeCoverageItem[] }) {
  if (items.length === 0) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            <th className="text-left py-2 px-2 font-medium text-gray-500">Scope Item</th>
            <th className="text-left py-2 px-2 font-medium text-gray-500">Present In</th>
            <th className="text-left py-2 px-2 font-medium text-gray-500">Missing From</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.item} className="border-b border-gray-100 dark:border-gray-800">
              <td className="py-1.5 px-2 font-mono">{item.item}</td>
              <td className="py-1.5 px-2 text-green-600">{item.present_in.join(', ') || '-'}</td>
              <td className="py-1.5 px-2 text-red-600">{item.missing_from.join(', ') || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface QuoteInsightsPanelProps {
  requestId: string;
}

export function QuoteInsightsPanel({ requestId }: QuoteInsightsPanelProps) {
  const { t } = useTranslation();

  const { data, isLoading, error } = useQuery({
    queryKey: ['quote-insights', requestId],
    queryFn: () => remediationIntelligenceApi.getComparisonInsights(requestId),
    enabled: !!requestId,
  });

  if (isLoading) {
    return <div className="animate-pulse h-32 bg-gray-100 dark:bg-gray-800 rounded-lg" />;
  }

  if (error) {
    return (
      <div className="text-sm text-red-500">
        {t('intelligence.insights_error') || 'Failed to load comparison insights.'}
      </div>
    );
  }

  if (!data || data.quote_count === 0) {
    return <div className="text-sm text-gray-500">{t('intelligence.no_quotes') || 'No quotes to compare.'}</div>;
  }

  const { price_spread, timeline_spread, common_exclusions, ambiguity_flags, scope_coverage_matrix } = data;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-blue-600" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {t('intelligence.quote_insights') || 'Quote Comparison Insights'}
        </h3>
        <span className="text-xs text-gray-500">({data.quote_count} quotes)</span>
      </div>

      {/* Price Spread */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
          <div className="text-xs text-gray-500">{t('intelligence.price_min') || 'Min Price'}</div>
          <div className="text-lg font-semibold">{price_spread.min.toLocaleString()} CHF</div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
          <div className="text-xs text-gray-500">{t('intelligence.price_max') || 'Max Price'}</div>
          <div className="text-lg font-semibold">{price_spread.max.toLocaleString()} CHF</div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
          <div className="text-xs text-gray-500">{t('intelligence.price_median') || 'Median'}</div>
          <div className="text-lg font-semibold">{price_spread.median.toLocaleString()} CHF</div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
          <div className="text-xs text-gray-500">{t('intelligence.price_range') || 'Range'}</div>
          <div className="text-lg font-semibold">{price_spread.range_pct}%</div>
        </div>
      </div>

      {/* Timeline Spread */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
          <div className="text-xs text-gray-500">{t('intelligence.timeline_min') || 'Min Timeline'}</div>
          <div className="text-lg font-semibold">{timeline_spread.min_weeks}w</div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
          <div className="text-xs text-gray-500">{t('intelligence.timeline_max') || 'Max Timeline'}</div>
          <div className="text-lg font-semibold">{timeline_spread.max_weeks}w</div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
          <div className="text-xs text-gray-500">{t('intelligence.timeline_median') || 'Median'}</div>
          <div className="text-lg font-semibold">{timeline_spread.median_weeks}w</div>
        </div>
      </div>

      {/* Scope Coverage Matrix */}
      {scope_coverage_matrix.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('intelligence.scope_coverage') || 'Scope Coverage'}
          </h4>
          <ScopeMatrix items={scope_coverage_matrix} />
        </div>
      )}

      {/* Common Exclusions */}
      {common_exclusions.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t('intelligence.common_exclusions') || 'Common Exclusions'}
          </h4>
          <div className="flex flex-wrap gap-1">
            {common_exclusions.map((e) => (
              <span
                key={e}
                className="text-xs bg-red-50 dark:bg-red-900 text-red-600 dark:text-red-300 px-2 py-0.5 rounded"
              >
                {e}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Ambiguity Flags */}
      {ambiguity_flags.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-500" />
            {t('intelligence.ambiguity_flags') || 'Ambiguity Flags'}
          </h4>
          <div className="space-y-1">
            {ambiguity_flags.map((f, i) => (
              <div key={i} className="text-xs text-amber-700 dark:text-amber-300">
                <span className="font-mono">{f.field}</span>: {f.description}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default QuoteInsightsPanel;
