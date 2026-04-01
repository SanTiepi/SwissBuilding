// MIGRATED to canonical BuildingSignal API (2026-03-28).
// Previously read from legacy ChangeSignal API — now reads from
// /portfolio/signals (BuildingSignal model via change_tracker_service).

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { buildingSignalsApi } from '@/api/buildingSignals';
import type { BuildingSignal } from '@/api/buildingSignals';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { AsyncStateWrapper } from '@/components/AsyncStateWrapper';
import { Bell } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500',
  warning: 'bg-orange-500',
  info: 'bg-blue-500',
};

const SEVERITY_FILTERS = ['all', 'critical', 'warning', 'info'] as const;

export function PortfolioSignalsFeed() {
  const { t } = useTranslation();
  const [severity, setSeverity] = useState<string | undefined>(undefined);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['portfolio', 'building-signals', severity],
    queryFn: () => buildingSignalsApi.listPortfolio(severity, 'active'),
  });

  const signals = data ?? [];

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Bell className="w-5 h-5 text-blue-500" />
          {t('portfolio.signals_title') || 'Recent Signals'}
        </h2>
      </div>

      {/* Severity filter pills */}
      <div className="flex gap-2 mb-4">
        {SEVERITY_FILTERS.map((filter) => {
          const isActive = filter === 'all' ? !severity : severity === filter;
          const label =
            filter === 'all'
              ? t('portfolio.signal_severity_all') || 'All'
              : filter.charAt(0).toUpperCase() + filter.slice(1);
          return (
            <button
              key={filter}
              onClick={() => setSeverity(filter === 'all' ? undefined : filter)}
              className={cn(
                'px-3 py-1 text-xs font-medium rounded-full transition-colors',
                isActive
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                  : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-400 hover:bg-gray-200 dark:hover:bg-slate-600',
              )}
            >
              {label}
            </button>
          );
        })}
      </div>

      <AsyncStateWrapper
        isLoading={isLoading}
        isError={isError}
        data={signals}
        variant="inline"
        emptyMessage={t('portfolio.no_signals') || 'No active signals'}
        errorMessage={t('app.loading_error') || 'Unable to load signals right now.'}
      >
        <ul className="space-y-3">
          {signals.slice(0, 10).map((signal: BuildingSignal) => (
            <li
              key={signal.id}
              className="flex items-start gap-3 text-sm p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700/50"
            >
              <span
                className={cn(
                  'w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0',
                  SEVERITY_COLORS[signal.severity] ?? 'bg-gray-400',
                )}
              />
              <div className="min-w-0 flex-1">
                <p className="text-gray-700 dark:text-slate-200 truncate">{signal.title}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-gray-400 dark:text-slate-500 font-mono">
                    {signal.building_id.substring(0, 8)}
                  </span>
                  <span className="text-xs text-gray-400 dark:text-slate-500">
                    {formatDistanceToNow(new Date(signal.detected_at), { addSuffix: true })}
                  </span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </AsyncStateWrapper>
    </div>
  );
}
