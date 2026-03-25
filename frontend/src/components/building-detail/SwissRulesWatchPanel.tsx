import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import {
  swissRulesWatchApi,
  type RuleSource,
  type RuleChangeEvent,
  type FreshnessState,
} from '@/api/swissRulesWatch';
import { BookOpen, MapPin, AlertTriangle, Shield, RefreshCw, Eye } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

interface SwissRulesWatchPanelProps {
  buildingId: string;
}

const FRESHNESS_CONFIG: Record<FreshnessState, { color: string; bg: string; label: string }> = {
  current: { color: 'text-green-700 dark:text-green-400', bg: 'bg-green-100 dark:bg-green-900/40', label: 'swiss_rules.freshness_current' },
  aging: { color: 'text-yellow-700 dark:text-yellow-400', bg: 'bg-yellow-100 dark:bg-yellow-900/40', label: 'swiss_rules.freshness_aging' },
  stale: { color: 'text-red-700 dark:text-red-400', bg: 'bg-red-100 dark:bg-red-900/40', label: 'swiss_rules.freshness_stale' },
  unknown: { color: 'text-gray-500 dark:text-gray-400', bg: 'bg-gray-100 dark:bg-gray-700', label: 'swiss_rules.freshness_unknown' },
};

const ADAPTER_STATUS_STYLE: Record<string, string> = {
  active: 'text-green-700 dark:text-green-400',
  draft: 'text-yellow-700 dark:text-yellow-400',
  disabled: 'text-gray-500 dark:text-gray-400',
};

export default function SwissRulesWatchPanel({ buildingId }: SwissRulesWatchPanelProps) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  const { data: communeCtx, isLoading: loadingCommune } = useQuery({
    queryKey: ['building-commune-context', buildingId],
    queryFn: () => swissRulesWatchApi.getBuildingCommuneContext(buildingId),
    staleTime: 120_000,
  });

  const { data: sources, isLoading: loadingSources } = useQuery({
    queryKey: ['swiss-rules-sources'],
    queryFn: () => swissRulesWatchApi.listSources(),
    staleTime: 120_000,
  });

  const { data: unreviewedChanges } = useQuery({
    queryKey: ['swiss-rules-unreviewed'],
    queryFn: () => swissRulesWatchApi.getUnreviewedChanges(),
    staleTime: 60_000,
    enabled: isAdmin,
  });

  const isLoading = loadingCommune || loadingSources;

  if (isLoading) {
    return (
      <div
        className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6"
        data-testid="swiss-rules-watch-loading"
      >
        <div className="animate-pulse space-y-3">
          <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-48" />
          <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      </div>
    );
  }

  const activeSources = sources?.filter((s) => s.is_active) ?? [];
  const overrides = communeCtx?.overrides ?? [];

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6"
      data-testid="swiss-rules-watch-panel"
    >
      <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
        <BookOpen className="w-5 h-5 text-gray-500 dark:text-gray-400" />
        {t('swiss_rules.title')}
      </h3>

      {/* Commune context */}
      {communeCtx && (
        <div className="mb-4 p-3 rounded-lg bg-gray-50 dark:bg-gray-900/30" data-testid="commune-context">
          <div className="flex items-center gap-2 mb-2">
            <MapPin className="w-4 h-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {communeCtx.adapter?.commune_name || communeCtx.city}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">({communeCtx.canton})</span>
          </div>

          {communeCtx.adapter ? (
            <div className="flex flex-wrap gap-2 text-xs" data-testid="adapter-info">
              <span className={cn('font-medium', ADAPTER_STATUS_STYLE[communeCtx.adapter.adapter_status] ?? 'text-gray-500')}>
                {t('swiss_rules.adapter_status')}: {communeCtx.adapter.adapter_status}
              </span>
              <span className="text-gray-500 dark:text-gray-400">
                {t('swiss_rules.fallback')}: {communeCtx.adapter.fallback_mode}
              </span>
            </div>
          ) : (
            <p className="text-xs text-gray-500 dark:text-gray-400" data-testid="no-adapter">
              {t('swiss_rules.no_adapter')}
            </p>
          )}
        </div>
      )}

      {/* Active rule sources */}
      {activeSources.length > 0 && (
        <div className="mb-4" data-testid="rule-sources-list">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1.5">
            <RefreshCw className="w-3.5 h-3.5" />
            {t('swiss_rules.active_sources')}
          </h4>
          <div className="space-y-2">
            {activeSources.map((source) => (
              <SourceRow key={source.id} source={source} />
            ))}
          </div>
        </div>
      )}

      {/* Unreviewed changes (admin only) */}
      {isAdmin && unreviewedChanges && unreviewedChanges.length > 0 && (
        <div className="mb-4" data-testid="unreviewed-changes">
          <h4 className="text-sm font-medium text-amber-700 dark:text-amber-400 mb-2 flex items-center gap-1.5">
            <Eye className="w-3.5 h-3.5" />
            {t('swiss_rules.unreviewed_changes')} ({unreviewedChanges.length})
          </h4>
          <div className="space-y-1.5">
            {unreviewedChanges.slice(0, 5).map((evt) => (
              <ChangeRow key={evt.id} event={evt} />
            ))}
            {unreviewedChanges.length > 5 && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                +{unreviewedChanges.length - 5} {t('common.more') || 'more'}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Override alerts */}
      {overrides.length > 0 && (
        <div data-testid="override-alerts">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
            {t('swiss_rules.overrides')} ({overrides.length})
          </h4>
          <div className="space-y-1.5">
            {overrides.map((ov) => (
              <div
                key={ov.id}
                className="flex items-start gap-2 py-1.5 px-2 rounded bg-amber-50 dark:bg-amber-900/20 text-xs"
                data-testid={`override-${ov.id}`}
              >
                <Shield className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">{ov.override_type}</span>
                  {ov.rule_reference && (
                    <span className="text-gray-500 dark:text-gray-400 ml-1">({ov.rule_reference})</span>
                  )}
                  <p className="text-gray-500 dark:text-gray-400 mt-0.5">{ov.impact_summary}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {activeSources.length === 0 && overrides.length === 0 && !communeCtx?.adapter && (
        <div className="text-center py-6" data-testid="swiss-rules-empty">
          <BookOpen className="w-8 h-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
          <p className="text-sm text-gray-500 dark:text-gray-400">{t('swiss_rules.empty')}</p>
        </div>
      )}
    </div>
  );
}

function SourceRow({ source }: { source: RuleSource }) {
  const { t } = useTranslation();
  const freshConf = FRESHNESS_CONFIG[source.freshness_state as FreshnessState] ?? FRESHNESS_CONFIG.unknown;

  return (
    <div
      className="flex items-center gap-2 py-1.5 px-2 rounded-lg bg-gray-50 dark:bg-gray-900/30"
      data-testid={`source-row-${source.id}`}
    >
      <span className="text-sm text-gray-700 dark:text-gray-300 flex-1 truncate">{source.source_name}</span>
      <span className="text-xs text-gray-500 dark:text-gray-400">{source.watch_tier}</span>
      <span
        className={cn('inline-block px-2 py-0.5 rounded text-xs font-medium', freshConf.bg, freshConf.color)}
        data-testid={`freshness-badge-${source.id}`}
      >
        {t(freshConf.label)}
      </span>
    </div>
  );
}

function ChangeRow({ event }: { event: RuleChangeEvent }) {
  return (
    <div
      className="flex items-start gap-2 py-1.5 px-2 rounded bg-amber-50 dark:bg-amber-900/20 text-xs"
      data-testid={`change-row-${event.id}`}
    >
      <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
      <div>
        <span className="font-medium text-gray-700 dark:text-gray-300">{event.title}</span>
        <span className="text-gray-500 dark:text-gray-400 ml-1">({event.event_type})</span>
        {event.impact_summary && (
          <p className="text-gray-500 dark:text-gray-400 mt-0.5">{event.impact_summary}</p>
        )}
      </div>
    </div>
  );
}
