import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { remediationIntelligenceApi } from '@/api/remediationIntelligence';
import type { ReadinessAdvisorSuggestion } from '@/api/remediationIntelligence';
import { AlertTriangle, CheckCircle, Clock, Shield, FileQuestion, Zap } from 'lucide-react';

const TYPE_CONFIG: Record<string, { color: string; icon: typeof AlertTriangle; label: string }> = {
  blocker: { color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200', icon: AlertTriangle, label: 'Blocker' },
  gap: { color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200', icon: FileQuestion, label: 'Gap' },
  stale: { color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200', icon: Clock, label: 'Stale' },
  missing_pollutant: { color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200', icon: Shield, label: 'Missing' },
  pending_procedure: { color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200', icon: Clock, label: 'Pending' },
  proof_gap: { color: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200', icon: FileQuestion, label: 'Proof Gap' },
};

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500">{pct}%</span>
    </div>
  );
}

function SuggestionCard({ suggestion }: { suggestion: ReadinessAdvisorSuggestion }) {
  const config = TYPE_CONFIG[suggestion.type] || TYPE_CONFIG.gap;
  const Icon = config.icon;

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-2">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4" />
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${config.color}`}>{config.label}</span>
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{suggestion.title}</span>
        </div>
        <ConfidenceBar confidence={suggestion.confidence} />
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400">{suggestion.description}</p>
      {suggestion.recommended_action && (
        <div className="flex items-center gap-2 text-xs text-blue-600 dark:text-blue-400">
          <Zap className="w-3 h-3" />
          <span>{suggestion.recommended_action}</span>
        </div>
      )}
      {suggestion.evidence_refs.length > 0 && (
        <div className="text-xs text-gray-400">
          Evidence: {suggestion.evidence_refs.join(', ')}
        </div>
      )}
    </div>
  );
}

interface ReadinessAdvisorPanelProps {
  buildingId: string;
}

export function ReadinessAdvisorPanel({ buildingId }: ReadinessAdvisorPanelProps) {
  const { t } = useTranslation();

  const { data, isLoading, error } = useQuery({
    queryKey: ['readiness-advisor', buildingId],
    queryFn: () => remediationIntelligenceApi.getReadinessAdvisor(buildingId),
    enabled: !!buildingId,
  });

  if (isLoading) {
    return <div className="animate-pulse h-32 bg-gray-100 dark:bg-gray-800 rounded-lg" />;
  }

  if (error) {
    return (
      <div className="text-sm text-red-500">
        {t('intelligence.advisor_error') || 'Failed to load readiness advisor.'}
      </div>
    );
  }

  const suggestions = data?.suggestions || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {t('intelligence.readiness_advisor') || 'Readiness Advisor'}
        </h3>
        {suggestions.length === 0 && (
          <div className="flex items-center gap-1 text-green-600 text-sm">
            <CheckCircle className="w-4 h-4" />
            <span>{t('intelligence.no_suggestions') || 'No issues found'}</span>
          </div>
        )}
      </div>
      {suggestions.length > 0 && (
        <div className="space-y-3">
          {suggestions.map((s, i) => (
            <SuggestionCard key={i} suggestion={s} />
          ))}
        </div>
      )}
    </div>
  );
}

export default ReadinessAdvisorPanel;
