import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { crossLayerIntelligenceApi, type CrossLayerInsight } from '@/api/crossLayerIntelligence';
import { cn } from '@/utils/formatters';

/* ------------------------------------------------------------------ */
/*  Types & config                                                     */
/* ------------------------------------------------------------------ */

interface IntelligencePanelProps {
  buildingId: string;
}

const SEVERITY_CONFIG: Record<
  string,
  { icon: string; dotClass: string; borderClass: string; bgClass: string; textClass: string }
> = {
  critical: {
    icon: '\u26A0',
    dotClass: 'bg-red-500',
    borderClass: 'border-l-red-500',
    bgClass: 'bg-red-50 dark:bg-red-900/20',
    textClass: 'text-red-700 dark:text-red-300',
  },
  warning: {
    icon: '\u26A0',
    dotClass: 'bg-amber-500',
    borderClass: 'border-l-amber-500',
    bgClass: 'bg-amber-50 dark:bg-amber-900/20',
    textClass: 'text-amber-700 dark:text-amber-300',
  },
  info: {
    icon: '\u2139',
    dotClass: 'bg-blue-500',
    borderClass: 'border-l-blue-500',
    bgClass: 'bg-blue-50 dark:bg-blue-900/20',
    textClass: 'text-blue-700 dark:text-blue-300',
  },
  opportunity: {
    icon: '\u2728',
    dotClass: 'bg-green-500',
    borderClass: 'border-l-green-500',
    bgClass: 'bg-green-50 dark:bg-green-900/20',
    textClass: 'text-green-700 dark:text-green-300',
  },
};

const TYPE_LABELS: Record<string, string> = {
  risk_cascade: 'intelligence.type_risk_cascade',
  silent_degradation: 'intelligence.type_silent_degradation',
  sampling_trust_gap: 'intelligence.type_sampling_trust_gap',
  document_evidence_mismatch: 'intelligence.type_document_evidence_mismatch',
  pattern_match: 'intelligence.type_pattern_match',
  cluster_risk: 'intelligence.type_cluster_risk',
  flywheel_insight: 'intelligence.type_flywheel_insight',
  compliance_countdown: 'intelligence.type_compliance_countdown',
  hidden_opportunity: 'intelligence.type_hidden_opportunity',
  contagion_structural: 'intelligence.type_contagion_structural',
};

/* ------------------------------------------------------------------ */
/*  Insight Card                                                       */
/* ------------------------------------------------------------------ */

function InsightCard({ insight }: { insight: CrossLayerInsight }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const config = SEVERITY_CONFIG[insight.severity] || SEVERITY_CONFIG.info;
  const typeKey = TYPE_LABELS[insight.insight_type] || insight.insight_type;

  return (
    <div
      className={cn(
        'rounded-lg border-l-4 p-4 transition-colors',
        config.borderClass,
        'bg-white dark:bg-slate-800',
      )}
      data-testid={`insight-card-${insight.insight_type}`}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <span className="text-lg" role="img" aria-label={insight.severity}>
          {config.icon}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={cn(
                'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium',
                config.bgClass,
                config.textClass,
              )}
            >
              {t(typeKey) || insight.insight_type}
            </span>
            <span className="text-xs text-gray-500 dark:text-slate-400">
              {t('intelligence.confidence')}: {Math.round(insight.confidence * 100)}%
            </span>
          </div>
          <h4 className="mt-1 text-sm font-semibold text-gray-900 dark:text-white">{insight.title}</h4>
          <p className="mt-1 text-sm text-gray-600 dark:text-slate-300">{insight.description}</p>
        </div>
      </div>

      {/* Recommendation */}
      <div className="mt-3 rounded-md bg-gray-50 dark:bg-slate-700/50 px-3 py-2">
        <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide">
          {t('intelligence.recommendation') || 'Recommendation'}
        </p>
        <p className="mt-0.5 text-sm text-gray-700 dark:text-slate-200">{insight.recommendation}</p>
      </div>

      {/* Impact */}
      <div className="mt-2 flex items-center gap-2 text-xs text-gray-500 dark:text-slate-400">
        <span>{t('intelligence.impact') || 'Impact'}:</span>
        <span className="font-medium text-gray-700 dark:text-slate-300">{insight.estimated_impact}</span>
      </div>

      {/* Evidence trail (expandable) */}
      {insight.evidence.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
            data-testid="evidence-trail-toggle"
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
                  <span className="font-medium text-gray-600 dark:text-slate-300 capitalize">{ev.layer}</span>
                  <span className="text-gray-400 dark:text-slate-500">/</span>
                  <span>{ev.signal}</span>
                  <span className="text-gray-400 dark:text-slate-500">=</span>
                  <span className="font-mono">{JSON.stringify(ev.value)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main panel                                                         */
/* ------------------------------------------------------------------ */

export function IntelligencePanel({ buildingId }: IntelligencePanelProps) {
  const { t } = useTranslation();

  const { data: insights, isLoading } = useQuery({
    queryKey: ['building-intelligence', buildingId],
    queryFn: () => crossLayerIntelligenceApi.getBuildingIntelligence(buildingId),
    enabled: !!buildingId,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3" data-testid="intelligence-loading">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 bg-gray-100 dark:bg-slate-700 rounded-lg" />
        ))}
      </div>
    );
  }

  if (!insights || insights.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-slate-400" data-testid="no-insights">
        <p className="text-sm">{t('intelligence.no_insights') || 'No cross-layer insights detected'}</p>
      </div>
    );
  }

  // Group by severity
  const grouped: Record<string, CrossLayerInsight[]> = {};
  for (const insight of insights) {
    const sev = insight.severity;
    if (!grouped[sev]) grouped[sev] = [];
    grouped[sev].push(insight);
  }

  const severityOrder = ['critical', 'warning', 'info', 'opportunity'];

  return (
    <div className="space-y-4" data-testid="intelligence-panel">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        {t('intelligence.cross_layer_title')} ({insights.length})
      </h3>

      {severityOrder.map((sev) => {
        const group = grouped[sev];
        if (!group || group.length === 0) return null;
        return (
          <div key={sev} className="space-y-3">
            {group.map((insight) => (
              <InsightCard key={insight.insight_id} insight={insight} />
            ))}
          </div>
        );
      })}
    </div>
  );
}

export default IntelligencePanel;
