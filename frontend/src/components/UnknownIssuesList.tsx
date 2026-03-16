import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { unknownsApi } from '@/api/unknowns';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { HelpCircle, AlertTriangle, Settings2 } from 'lucide-react';
import type { UnknownIssue } from '@/types';
import { AsyncStateWrapper } from './AsyncStateWrapper';
import { UnknownIssuesPanel } from './UnknownIssuesPanel';

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-yellow-500',
  low: 'bg-green-500',
};

export function UnknownIssuesList({ buildingId }: { buildingId: string }) {
  const { t } = useTranslation();
  const [showPanel, setShowPanel] = useState(false);
  const { data, isLoading, isError } = useQuery({
    queryKey: ['building-unknowns', buildingId],
    queryFn: () => unknownsApi.list(buildingId, 'open'),
    enabled: !!buildingId,
  });

  const issues = data?.items ?? [];
  const blockingCount = issues.filter((i) => i.blocks_readiness).length;

  if (showPanel) {
    return (
      <div className="md:col-span-2 bg-gray-50 dark:bg-slate-700/50 rounded-xl p-5">
        <UnknownIssuesPanel buildingId={buildingId} onClose={() => setShowPanel(false)} />
      </div>
    );
  }

  return (
    <AsyncStateWrapper
      isLoading={isLoading}
      isError={isError}
      data={data}
      variant="card"
      title={t('unknown_issue.title') || 'Blind Spots'}
      icon={<HelpCircle className="w-5 h-5" />}
      emptyMessage={t('unknown_issue.none') || 'No open blind spots'}
      isEmpty={!isLoading && !isError && issues.length === 0}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <HelpCircle className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            {t('unknown_issue.title') || 'Blind Spots'}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 text-xs font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 rounded-full">
            {issues.length}
          </span>
          <button
            onClick={() => setShowPanel(true)}
            className="p-1 rounded hover:bg-gray-200 dark:hover:bg-slate-600 text-gray-400 dark:text-slate-400 transition-colors"
            title={t('unknown_issue.manage_all')}
          >
            <Settings2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {blockingCount > 0 && (
        <div className="flex items-center gap-1.5 mb-3 px-2 py-1 bg-red-50 dark:bg-red-900/20 rounded-lg">
          <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
          <span className="text-xs text-red-600 dark:text-red-400">
            {blockingCount} {t('unknown_issue.blocking_readiness') || 'blocking readiness'}
          </span>
        </div>
      )}

      <ul className="space-y-2">
        {issues.slice(0, 5).map((issue: UnknownIssue) => (
          <li key={issue.id} className="flex items-start gap-2 text-sm">
            <span
              className={cn(
                'w-2 h-2 rounded-full mt-1.5 flex-shrink-0',
                SEVERITY_COLORS[issue.severity] ?? 'bg-gray-400',
              )}
            />
            <div className="min-w-0">
              <p className="text-gray-700 dark:text-slate-200 truncate">{issue.title}</p>
              {issue.blocks_readiness && (
                <p className="text-xs text-red-500">
                  {t('unknown_issue.blocks_readiness_label') || 'Blocks readiness'}
                </p>
              )}
            </div>
          </li>
        ))}
        {issues.length > 5 && (
          <li className="text-xs text-gray-500 dark:text-slate-400">
            +{issues.length - 5} {t('common.more') || 'more'}
          </li>
        )}
      </ul>

      {issues.length > 0 && (
        <button
          onClick={() => setShowPanel(true)}
          className="mt-3 w-full text-center text-xs font-medium text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 transition-colors"
        >
          {t('unknown_issue.manage_all')}
        </button>
      )}
    </AsyncStateWrapper>
  );
}
