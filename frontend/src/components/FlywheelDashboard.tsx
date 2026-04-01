import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { flywheelApi, type FlywheelDashboard as FlywheelDashboardData } from '@/api/flywheel';

function TrendIndicator({ trend }: { trend: string }) {
  const { t } = useTranslation();
  if (trend === 'improving') {
    return <span className="text-green-600 dark:text-green-400" data-testid="trend-improving">&#9650; {t('flywheel.trend_improving') || 'Improving'}</span>;
  }
  if (trend === 'declining') {
    return <span className="text-red-600 dark:text-red-400" data-testid="trend-declining">&#9660; {t('flywheel.trend_declining') || 'Declining'}</span>;
  }
  return <span className="text-gray-500 dark:text-gray-400" data-testid="trend-stable">&#9654; {t('flywheel.trend_stable') || 'Stable'}</span>;
}

export default function FlywheelDashboard() {
  const { t } = useTranslation();

  const { data, isLoading, error } = useQuery<FlywheelDashboardData>({
    queryKey: ['flywheel-dashboard'],
    queryFn: () => flywheelApi.getDashboard(),
    staleTime: 60_000,
  });

  if (isLoading) {
    return <div className="animate-pulse p-4 text-gray-500 dark:text-gray-400">{t('common.loading') || 'Loading...'}</div>;
  }

  if (error || !data) {
    return (
      <div className="p-4 text-gray-500 dark:text-gray-400" data-testid="flywheel-empty">
        {t('flywheel.title') || 'Flywheel'} — {t('common.no_data') || 'No data yet'}
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4" data-testid="flywheel-dashboard">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
        {t('flywheel.title') || 'Flywheel Learning'}
      </h2>

      {/* Overall metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label={t('flywheel.accuracy') || 'Classification accuracy'}
          value={`${Math.round(data.classification_accuracy * 100)}%`}
        />
        <MetricCard
          label={t('flywheel.extraction_accuracy') || 'Extraction accuracy'}
          value={`${Math.round(data.extraction_accuracy * 100)}%`}
        />
        <MetricCard
          label={t('flywheel.total_processed') || 'Total processed'}
          value={String(data.total_documents_processed)}
        />
        <MetricCard
          label={t('flywheel.correction_rate') || 'Correction rate'}
          value={`${Math.round(data.correction_rate * 100)}%`}
        />
      </div>

      {/* Trend */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {t('flywheel.trend') || 'Trend'}:
        </span>
        <TrendIndicator trend={data.improvement_trend} />
      </div>

      {/* Corrections */}
      <div className="text-sm text-gray-600 dark:text-gray-400" data-testid="correction-summary">
        {t('flywheel.corrections') || 'Corrections'}: {data.total_corrections} / {data.total_documents_processed}
      </div>

      {/* Confusion pairs */}
      {data.top_confusion_pairs.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            {t('flywheel.confusion') || 'Top confusion pairs'}
          </h3>
          <ul className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
            {data.top_confusion_pairs.map((pair, i) => (
              <li key={i}>
                <span className="font-mono">{pair.predicted}</span> &rarr;{' '}
                <span className="font-mono">{pair.actual}</span>{' '}
                <span className="text-gray-400">({pair.count}x)</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Learned rules */}
      {data.learned_rules.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            {t('flywheel.learned_rules') || 'Learned rules'} ({data.learned_rules_count})
          </h3>
          <ul className="space-y-2 text-sm">
            {data.learned_rules.map((rule, i) => (
              <li key={i} className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded text-gray-700 dark:text-gray-300">
                {rule.suggestion}
                <span className="ml-2 text-xs text-gray-400">
                  ({Math.round(rule.confidence * 100)}%)
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-3 text-center">
      <div className="text-2xl font-bold text-gray-900 dark:text-white">{value}</div>
      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{label}</div>
    </div>
  );
}
