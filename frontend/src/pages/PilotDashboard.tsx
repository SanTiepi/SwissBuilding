import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { demoPilotApi } from '@/api/demoPilot';
import type { PilotScorecardWithMetrics } from '@/api/demoPilot';
import { cn, formatDate } from '@/utils/formatters';
import { Loader2, AlertTriangle, ChevronDown, ChevronRight, TrendingUp } from 'lucide-react';

function exitRecommendation(scorecard: PilotScorecardWithMetrics): string {
  if (scorecard.metrics.length === 0) return 'insufficient_data';
  const metricsMet = scorecard.metrics.filter(
    (m) => m.target_value != null && m.current_value != null && m.current_value >= m.target_value,
  ).length;
  const ratio = metricsMet / scorecard.metrics.length;
  if (ratio >= 0.8) return 'scale';
  if (ratio >= 0.5) return 'iterate';
  return 'pivot';
}

function exitBadgeColor(rec: string): string {
  if (rec === 'scale') return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300';
  if (rec === 'iterate') return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300';
  if (rec === 'pivot') return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300';
  return 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300';
}

export default function PilotDashboard() {
  const { t } = useTranslation();
  const [expandedCode, setExpandedCode] = useState<string | null>(null);

  const {
    data: pilots = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['pilot-scorecards'],
    queryFn: demoPilotApi.listPilots,
  });

  const { data: scorecard, isLoading: scorecardLoading } = useQuery<PilotScorecardWithMetrics>({
    queryKey: ['pilot-scorecard', expandedCode],
    queryFn: () => demoPilotApi.getScorecard(expandedCode!),
    enabled: !!expandedCode,
  });

  const togglePilot = (code: string) => {
    setExpandedCode((prev) => (prev === code ? null : code));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('pilot_dashboard.title')}</h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('pilot_dashboard.description')}</p>
      </div>

      {pilots.length === 0 ? (
        <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-8 text-center">
          <p className="text-gray-500 dark:text-slate-400">{t('pilot_dashboard.empty')}</p>
        </div>
      ) : (
        <div className="space-y-4" data-testid="pilot-list">
          {pilots.map((pilot) => {
            const isExpanded = expandedCode === pilot.pilot_code;
            return (
              <div
                key={pilot.id}
                className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl overflow-hidden"
              >
                {/* Pilot Header */}
                <button
                  onClick={() => togglePilot(pilot.pilot_code)}
                  className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
                  data-testid={`pilot-${pilot.pilot_code}`}
                >
                  {isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-gray-400 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-gray-900 dark:text-white">{pilot.pilot_name}</h3>
                      <span
                        className={cn(
                          'px-2 py-0.5 text-xs font-medium rounded-full',
                          pilot.status === 'active'
                            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                            : pilot.status === 'completed'
                              ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                              : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300',
                        )}
                      >
                        {pilot.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-slate-400 mt-1">
                      <span>
                        {formatDate(pilot.start_date)}
                        {pilot.end_date ? ` - ${formatDate(pilot.end_date)}` : ''}
                      </span>
                      {pilot.target_buildings && (
                        <span>
                          {pilot.target_buildings} {t('pilot_dashboard.target_buildings')}
                        </span>
                      )}
                      {pilot.target_users && (
                        <span>
                          {pilot.target_users} {t('pilot_dashboard.target_users')}
                        </span>
                      )}
                    </div>
                  </div>
                </button>

                {/* Expanded Scorecard */}
                {isExpanded && (
                  <div className="border-t border-gray-200 dark:border-slate-700 px-5 py-4">
                    {scorecardLoading ? (
                      <div className="flex items-center justify-center py-6">
                        <Loader2 className="w-6 h-6 animate-spin text-red-600" />
                      </div>
                    ) : scorecard && scorecard.pilot_code === expandedCode ? (
                      <div className="space-y-4">
                        {/* Metrics */}
                        {scorecard.metrics.length === 0 ? (
                          <p className="text-sm text-gray-500 dark:text-slate-400">
                            {t('pilot_dashboard.no_metrics')}
                          </p>
                        ) : (
                          <div className="space-y-3" data-testid="pilot-metrics">
                            {scorecard.metrics.map((metric) => {
                              const progress =
                                metric.target_value && metric.current_value
                                  ? Math.min(100, Math.round((metric.current_value / metric.target_value) * 100))
                                  : 0;
                              return (
                                <div key={metric.id} className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                                      {metric.dimension}
                                    </span>
                                    <span className="text-xs text-gray-500 dark:text-slate-400">
                                      {metric.current_value ?? '-'} / {metric.target_value ?? '-'}
                                    </span>
                                  </div>
                                  <div className="h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
                                    <div
                                      className={cn(
                                        'h-full rounded-full transition-all',
                                        progress >= 80
                                          ? 'bg-green-500'
                                          : progress >= 50
                                            ? 'bg-yellow-500'
                                            : 'bg-red-500',
                                      )}
                                      style={{ width: `${progress}%` }}
                                      data-testid={`metric-progress-${metric.dimension}`}
                                    />
                                  </div>
                                  {metric.evidence_source && (
                                    <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
                                      {t('pilot_dashboard.evidence')}: {metric.evidence_source}
                                    </p>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}

                        {/* Exit Recommendation */}
                        <div className="flex items-center gap-2 pt-2 border-t border-gray-200 dark:border-slate-700">
                          <TrendingUp className="w-4 h-4 text-gray-500 dark:text-slate-400" />
                          <span className="text-sm text-gray-700 dark:text-slate-200">
                            {t('pilot_dashboard.exit_recommendation')}:
                          </span>
                          {(() => {
                            const rec = scorecard.exit_state || exitRecommendation(scorecard);
                            return (
                              <span
                                className={cn('px-2 py-0.5 text-xs font-medium rounded-full', exitBadgeColor(rec))}
                                data-testid="exit-recommendation"
                              >
                                {t(`pilot_dashboard.exit_${rec}`) || rec}
                              </span>
                            );
                          })()}
                        </div>
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
