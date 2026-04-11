import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { crossLayerIntelligenceApi, type CrossLayerInsight } from '@/api/crossLayerIntelligence';
import { cn } from '@/utils/formatters';

/* ------------------------------------------------------------------ */
/*  Config                                                             */
/* ------------------------------------------------------------------ */

const SEVERITY_CONFIG: Record<string, { icon: string; bgClass: string; textClass: string; borderClass: string }> = {
  critical: {
    icon: '\u26A0',
    bgClass: 'bg-red-50 dark:bg-red-900/20',
    textClass: 'text-red-700 dark:text-red-300',
    borderClass: 'border-l-red-500',
  },
  warning: {
    icon: '\u26A0',
    bgClass: 'bg-amber-50 dark:bg-amber-900/20',
    textClass: 'text-amber-700 dark:text-amber-300',
    borderClass: 'border-l-amber-500',
  },
  info: {
    icon: '\u2139',
    bgClass: 'bg-blue-50 dark:bg-blue-900/20',
    textClass: 'text-blue-700 dark:text-blue-300',
    borderClass: 'border-l-blue-500',
  },
  opportunity: {
    icon: '\u2728',
    bgClass: 'bg-green-50 dark:bg-green-900/20',
    textClass: 'text-green-700 dark:text-green-300',
    borderClass: 'border-l-green-500',
  },
};

/* ------------------------------------------------------------------ */
/*  Portfolio Insight Card                                             */
/* ------------------------------------------------------------------ */

function PortfolioInsightCard({ insight }: { insight: CrossLayerInsight }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const config = SEVERITY_CONFIG[insight.severity] || SEVERITY_CONFIG.info;

  return (
    <div
      className={cn('rounded-lg border-l-4 p-4 bg-white dark:bg-slate-800', config.borderClass)}
      data-testid={`portfolio-insight-${insight.insight_type}`}
    >
      <div className="flex items-start gap-3">
        <span className="text-lg">{config.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={cn('rounded-full px-2 py-0.5 text-[11px] font-medium', config.bgClass, config.textClass)}>
              {insight.severity}
            </span>
            <span className="text-xs text-gray-500 dark:text-slate-400">
              {t('intelligence.confidence')}: {Math.round(insight.confidence * 100)}%
            </span>
          </div>
          <h4 className="mt-1 text-sm font-semibold text-gray-900 dark:text-white">{insight.title}</h4>
          <p className="mt-1 text-sm text-gray-600 dark:text-slate-300">{insight.description}</p>

          {/* Recommendation */}
          <div className="mt-3 rounded-md bg-gray-50 dark:bg-slate-700/50 px-3 py-2">
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide">
              {t('intelligence.recommendation') || 'Recommendation'}
            </p>
            <p className="mt-0.5 text-sm text-gray-700 dark:text-slate-200">{insight.recommendation}</p>
          </div>

          {/* Estimated impact / savings */}
          <div className="mt-2 flex items-center gap-2 text-xs text-gray-500 dark:text-slate-400">
            <span>{t('intelligence.impact') || 'Impact'}:</span>
            <span className="font-semibold text-gray-700 dark:text-slate-300">{insight.estimated_impact}</span>
          </div>

          {/* Evidence trail */}
          {insight.evidence.length > 0 && (
            <div className="mt-3">
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
              >
                {t('intelligence.evidence_trail')} ({insight.evidence.length})
                {expanded ? ' \u25B2' : ' \u25BC'}
              </button>
              {expanded && (
                <div className="mt-2 space-y-1">
                  {insight.evidence.map((ev, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 text-xs text-gray-500 dark:text-slate-400 bg-gray-50 dark:bg-slate-700/30 rounded px-2 py-1"
                    >
                      <span className="font-medium capitalize">{ev.layer}</span>
                      <span className="text-gray-400">/</span>
                      <span>{ev.signal}</span>
                      <span className="text-gray-400">=</span>
                      <span className="font-mono">{JSON.stringify(ev.value)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export function PortfolioIntelligence() {
  const { t } = useTranslation();

  const { data: insights, isLoading } = useQuery({
    queryKey: ['portfolio-intelligence'],
    queryFn: () => crossLayerIntelligenceApi.getPortfolioIntelligence(),
  });

  const { data: summary } = useQuery({
    queryKey: ['intelligence-summary'],
    queryFn: () => crossLayerIntelligenceApi.getIntelligenceSummary(),
  });

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3" data-testid="portfolio-intelligence-loading">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 bg-gray-100 dark:bg-slate-700 rounded-lg" />
        ))}
      </div>
    );
  }

  if (!insights || insights.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-slate-400" data-testid="no-portfolio-insights">
        <p className="text-sm">{t('intelligence.no_insights') || 'No portfolio insights detected'}</p>
      </div>
    );
  }

  // Severity breakdown from summary
  const bySeverity = summary?.by_severity || {};

  return (
    <div className="space-y-6" data-testid="portfolio-intelligence">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('intelligence.portfolio')} ({insights.length})
        </h3>
      </div>

      {/* Summary counters */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {(['critical', 'warning', 'info', 'opportunity'] as const).map((sev) => {
            const config = SEVERITY_CONFIG[sev];
            const count = bySeverity[sev] || 0;
            return (
              <div key={sev} className={cn('rounded-lg px-4 py-3', config.bgClass)}>
                <p className={cn('text-2xl font-bold', config.textClass)}>{count}</p>
                <p className="text-xs text-gray-500 dark:text-slate-400 capitalize">{sev}</p>
              </div>
            );
          })}
        </div>
      )}

      {/* Insight list */}
      <div className="space-y-3">
        {insights.map((insight) => (
          <PortfolioInsightCard key={insight.insight_id} insight={insight} />
        ))}
      </div>
    </div>
  );
}

export default PortfolioIntelligence;
