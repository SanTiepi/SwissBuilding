import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { readinessApi } from '@/api/readiness';
import { AlertTriangle, Beaker, FileSearch, ShieldAlert, Zap } from 'lucide-react';
import type { PreworkTrigger, PreworkTriggerUrgency } from '@/types';

const URGENCY_STYLES: Record<PreworkTriggerUrgency, string> = {
  high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  low: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
};

const URGENCY_BORDER: Record<PreworkTriggerUrgency, string> = {
  high: 'border-red-200 dark:border-red-900/50',
  medium: 'border-yellow-200 dark:border-yellow-900/50',
  low: 'border-blue-200 dark:border-blue-900/50',
};

function triggerIcon(triggerType: string) {
  const lower = triggerType.toLowerCase();
  if (lower.includes('diagnostic') || lower.includes('sample')) {
    return <Beaker className="w-4 h-4" />;
  }
  if (lower.includes('document') || lower.includes('report')) {
    return <FileSearch className="w-4 h-4" />;
  }
  if (lower.includes('compliance') || lower.includes('regulation')) {
    return <ShieldAlert className="w-4 h-4" />;
  }
  return <Zap className="w-4 h-4" />;
}

interface PreworkDiagnosticTriggerCardProps {
  triggers?: PreworkTrigger[] | undefined | null;
  buildingId?: string;
}

export function PreworkDiagnosticTriggerCard({ triggers, buildingId }: PreworkDiagnosticTriggerCardProps) {
  const { t } = useTranslation();

  // Self-fetch mode: when buildingId is provided and triggers are not
  const shouldFetch = !!buildingId && triggers === undefined;
  const { data: readinessData } = useQuery({
    queryKey: ['readiness', buildingId],
    queryFn: () => readinessApi.list(buildingId!),
    enabled: shouldFetch,
  });

  const resolvedTriggers = useMemo(() => {
    if (triggers !== undefined) return triggers ?? [];
    if (!readinessData?.items) return [];
    const collected: PreworkTrigger[] = [];
    for (const assessment of readinessData.items) {
      if (assessment.prework_triggers) {
        collected.push(...assessment.prework_triggers);
      }
    }
    return collected;
  }, [triggers, readinessData]);

  if (!resolvedTriggers || resolvedTriggers.length === 0) {
    return null;
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-amber-200 dark:border-amber-900/50 p-6 space-y-4">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-5 h-5 text-amber-500" />
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('readiness.prework_triggers') || 'Pre-work Diagnostic Triggers'}
        </h2>
        <span className="ml-auto text-sm text-gray-500 dark:text-slate-400">
          {resolvedTriggers.length} {t('readiness.triggers_count') || 'trigger(s)'}
        </span>
      </div>

      <div className="space-y-3">
        {resolvedTriggers.map((trigger, i) => (
          <div
            key={`${trigger.trigger_type}-${trigger.source_check}-${i}`}
            className={cn(
              'flex items-start gap-3 p-3 rounded-lg border',
              URGENCY_BORDER[trigger.urgency] || URGENCY_BORDER.low,
              'bg-gray-50 dark:bg-slate-700/30',
            )}
          >
            <div className="flex-shrink-0 mt-0.5 text-gray-500 dark:text-slate-400">
              {triggerIcon(trigger.trigger_type)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className={cn(
                    'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
                    URGENCY_STYLES[trigger.urgency] || URGENCY_STYLES.low,
                  )}
                >
                  {trigger.urgency}
                </span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">{trigger.trigger_type}</span>
              </div>
              <p className="mt-1 text-sm text-gray-700 dark:text-slate-300">{trigger.reason}</p>
              <p className="mt-0.5 text-xs text-gray-500 dark:text-slate-400">
                {t('readiness.source_check') || 'Source'}: {trigger.source_check}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
