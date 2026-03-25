import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { artifactCustodyApi, type ArtifactVersion, type CustodyEvent } from '@/api/artifactCustody';
import { cn, formatDate } from '@/utils/formatters';
import { ChevronDown, ChevronRight, History, Loader2, Shield } from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  current: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  superseded: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  archived: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  withdrawn: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const EVENT_ICONS: Record<string, string> = {
  created: '📄',
  published: '📤',
  delivered: '📬',
  viewed: '👁',
  acknowledged: '✅',
  disputed: '⚠️',
  superseded: '🔄',
  archived: '📦',
  withdrawn: '🚫',
};

interface CustodyChainPanelProps {
  buildingId: string;
}

export function VersionCard({ version }: { version: ArtifactVersion }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  const { data: events = [], isLoading } = useQuery<CustodyEvent[]>({
    queryKey: ['version-events', version.id],
    queryFn: () => artifactCustodyApi.getVersionEvents(version.id),
    enabled: expanded,
    retry: false,
  });

  return (
    <div className="border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              v{version.version_number}
            </span>
            <span
              className={cn(
                'inline-block px-2 py-0.5 text-[10px] font-medium rounded-full',
                STATUS_COLORS[version.status] || STATUS_COLORS.current,
              )}
            >
              {version.status}
            </span>
            <span className="text-xs text-gray-500 dark:text-slate-400">
              {version.artifact_type.replace(/_/g, ' ')}
            </span>
          </div>
          <p className="text-xs text-gray-400 dark:text-slate-500 truncate mt-0.5">
            {formatDate(version.created_at)}
            {version.content_hash && (
              <span className="ml-2 font-mono">#{version.content_hash.slice(0, 8)}</span>
            )}
          </p>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-gray-200 dark:border-slate-700 px-4 py-3 bg-gray-50 dark:bg-slate-800/50">
          {isLoading ? (
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Loader2 className="w-3 h-3 animate-spin" />
              Loading events...
            </div>
          ) : events.length === 0 ? (
            <p className="text-xs text-gray-400 dark:text-slate-500">
              {t('artifact_custody.no_events') || 'No custody events recorded'}
            </p>
          ) : (
            <div className="space-y-2">
              {events.map((evt) => (
                <div key={evt.id} className="flex items-start gap-2 text-xs">
                  <span className="shrink-0 mt-0.5">{EVENT_ICONS[evt.event_type] || '•'}</span>
                  <div className="flex-1 min-w-0">
                    <span className="font-medium text-gray-700 dark:text-slate-300">{evt.event_type}</span>
                    {evt.actor_name && (
                      <span className="text-gray-500 dark:text-slate-400"> by {evt.actor_name}</span>
                    )}
                    <span className="text-gray-400 dark:text-slate-500 ml-1">
                      ({evt.actor_type})
                    </span>
                    <p className="text-gray-400 dark:text-slate-500">{formatDate(evt.occurred_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function CustodyChainPanel({ buildingId }: CustodyChainPanelProps) {
  const { t } = useTranslation();
  const { data: posture, isLoading } = useQuery({
    queryKey: ['archive-posture', buildingId],
    queryFn: () => artifactCustodyApi.getArchivePosture(buildingId),
    retry: false,
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
          <span className="text-sm text-gray-500">Loading custody chain...</span>
        </div>
      </div>
    );
  }

  if (!posture || posture.total_versions === 0) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
        <div className="flex items-center gap-2 mb-2">
          <Shield className="w-5 h-5 text-gray-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            {t('artifact_custody.chain_title') || 'Custody Chain'}
          </h3>
        </div>
        <p className="text-xs text-gray-500 dark:text-slate-400">
          {t('artifact_custody.no_versions') || 'No artifact versions recorded yet.'}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
      <div className="flex items-center gap-2 mb-4">
        <History className="w-5 h-5 text-gray-500 dark:text-slate-400" />
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          {t('artifact_custody.chain_title') || 'Custody Chain'}
        </h3>
        <span className="ml-auto text-xs text-gray-500 dark:text-slate-400">
          {posture.total_versions} {t('artifact_custody.versions') || 'versions'}
        </span>
      </div>

      <p className="text-xs text-gray-500 dark:text-slate-400 mb-4">
        {t('artifact_custody.chain_description') ||
          'Full version history and chain-of-custody for all building artifacts. Click a version to see its events.'}
      </p>

      {/* The panel shows posture summary — individual chains are loaded on demand */}
      <div className="grid grid-cols-4 gap-2 text-center mb-4">
        <div>
          <p className="text-lg font-bold text-green-600 dark:text-green-400">{posture.current_count}</p>
          <p className="text-[10px] text-gray-500 dark:text-slate-400">Current</p>
        </div>
        <div>
          <p className="text-lg font-bold text-gray-500 dark:text-slate-400">{posture.superseded_count}</p>
          <p className="text-[10px] text-gray-500 dark:text-slate-400">Superseded</p>
        </div>
        <div>
          <p className="text-lg font-bold text-amber-600 dark:text-amber-400">{posture.archived_count}</p>
          <p className="text-[10px] text-gray-500 dark:text-slate-400">Archived</p>
        </div>
        <div>
          <p className="text-lg font-bold text-red-600 dark:text-red-400">{posture.withdrawn_count}</p>
          <p className="text-[10px] text-gray-500 dark:text-slate-400">Withdrawn</p>
        </div>
      </div>

      {posture.last_custody_event && (
        <div className="text-xs text-gray-500 dark:text-slate-400 border-t border-gray-200 dark:border-slate-700 pt-3">
          <span className="font-medium">{t('artifact_custody.last_event') || 'Last event'}:</span>{' '}
          {posture.last_custody_event.event_type}
          {posture.last_custody_event.actor_name && ` by ${posture.last_custody_event.actor_name}`}
          {' — '}
          {formatDate(posture.last_custody_event.occurred_at)}
        </div>
      )}
    </div>
  );
}

export default CustodyChainPanel;
