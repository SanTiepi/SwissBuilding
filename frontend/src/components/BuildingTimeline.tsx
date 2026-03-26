import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { timelineApi } from '@/api/timeline';
import { cn } from '@/utils/formatters';
import { AsyncStateWrapper } from '@/components/AsyncStateWrapper';
import type { TimelineEntry, EnrichedTimelineEntry, LifecyclePhase, ImportanceLevel } from '@/types';
import {
  Building2,
  Microscope,
  FlaskConical,
  FileText,
  Wrench,
  Shield,
  Map,
  Calendar,
  ChevronDown,
  Clock,
  ClipboardCheck,
} from 'lucide-react';

const EVENT_COLORS: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  construction: {
    bg: 'bg-green-50',
    border: 'border-green-200',
    text: 'text-green-700',
    dot: 'bg-green-500',
  },
  diagnostic: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-700',
    dot: 'bg-blue-500',
  },
  sample: {
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    text: 'text-purple-700',
    dot: 'bg-purple-500',
  },
  document: {
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    text: 'text-gray-700',
    dot: 'bg-gray-500',
  },
  intervention: {
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    text: 'text-orange-700',
    dot: 'bg-orange-500',
  },
  risk_change: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-700',
    dot: 'bg-red-500',
  },
  plan: {
    bg: 'bg-teal-50',
    border: 'border-teal-200',
    text: 'text-teal-700',
    dot: 'bg-teal-500',
  },
  event: {
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    text: 'text-gray-700',
    dot: 'bg-gray-400',
  },
  diagnostic_publication: {
    bg: 'bg-indigo-50',
    border: 'border-indigo-200',
    text: 'text-indigo-700',
    dot: 'bg-indigo-500',
  },
};

const IMPORTANCE_COLORS: Record<ImportanceLevel, { bg: string; text: string; darkBg: string; darkText: string }> = {
  critical: { bg: 'bg-red-100', text: 'text-red-700', darkBg: 'dark:bg-red-900/30', darkText: 'dark:text-red-400' },
  high: {
    bg: 'bg-orange-100',
    text: 'text-orange-700',
    darkBg: 'dark:bg-orange-900/30',
    darkText: 'dark:text-orange-400',
  },
  medium: {
    bg: 'bg-blue-100',
    text: 'text-blue-700',
    darkBg: 'dark:bg-blue-900/30',
    darkText: 'dark:text-blue-400',
  },
  low: { bg: 'bg-gray-100', text: 'text-gray-600', darkBg: 'dark:bg-slate-700', darkText: 'dark:text-slate-400' },
};

const PHASE_COLORS: Record<LifecyclePhase, { bg: string; text: string; darkBg: string; darkText: string }> = {
  discovery: {
    bg: 'bg-yellow-100',
    text: 'text-yellow-700',
    darkBg: 'dark:bg-yellow-900/30',
    darkText: 'dark:text-yellow-400',
  },
  assessment: {
    bg: 'bg-blue-100',
    text: 'text-blue-700',
    darkBg: 'dark:bg-blue-900/30',
    darkText: 'dark:text-blue-400',
  },
  remediation: {
    bg: 'bg-orange-100',
    text: 'text-orange-700',
    darkBg: 'dark:bg-orange-900/30',
    darkText: 'dark:text-orange-400',
  },
  verification: {
    bg: 'bg-purple-100',
    text: 'text-purple-700',
    darkBg: 'dark:bg-purple-900/30',
    darkText: 'dark:text-purple-400',
  },
  closed: {
    bg: 'bg-green-100',
    text: 'text-green-700',
    darkBg: 'dark:bg-green-900/30',
    darkText: 'dark:text-green-400',
  },
};

const PHASE_BAR_COLORS: Record<LifecyclePhase, string> = {
  discovery: 'bg-yellow-400',
  assessment: 'bg-blue-400',
  remediation: 'bg-orange-400',
  verification: 'bg-purple-400',
  closed: 'bg-green-400',
};

const LIFECYCLE_PHASES: LifecyclePhase[] = ['discovery', 'assessment', 'remediation', 'verification', 'closed'];

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  building: Building2,
  microscope: Microscope,
  flask: FlaskConical,
  file: FileText,
  wrench: Wrench,
  shield: Shield,
  map: Map,
  calendar: Calendar,
  clipboard: ClipboardCheck,
};

function getEventIcon(iconHint: string, className?: string) {
  const Icon = ICON_MAP[iconHint] || Calendar;
  return <Icon className={className} />;
}

function formatTimelineDate(dateStr: string): { display: string; relative: string } {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  const display = date.toLocaleDateString('fr-CH', {
    month: 'short',
    year: 'numeric',
  });

  let relative: string;
  if (diffDays < 0) {
    relative = '';
  } else if (diffDays === 0) {
    relative = "Aujourd'hui";
  } else if (diffDays === 1) {
    relative = 'Hier';
  } else if (diffDays < 30) {
    relative = `${diffDays}j`;
  } else if (diffDays < 365) {
    relative = `${Math.floor(diffDays / 30)}m`;
  } else {
    relative = `${Math.floor(diffDays / 365)}a`;
  }

  return { display, relative };
}

interface TimelineItemProps {
  entry: TimelineEntry;
  enriched?: boolean;
}

function TimelineItem({ entry, enriched }: TimelineItemProps) {
  const [expanded, setExpanded] = useState(false);
  const { t } = useTranslation();
  const colors = EVENT_COLORS[entry.event_type] || EVENT_COLORS.event;
  const { display, relative } = formatTimelineDate(entry.date);

  const eventTypeLabel = t(`timeline.event_type.${entry.event_type}`) || entry.event_type;

  const enrichedEntry = enriched ? (entry as EnrichedTimelineEntry) : null;

  return (
    <div className="flex gap-4 group">
      {/* Date column */}
      <div className="w-20 flex-shrink-0 text-right pt-1">
        <p className="text-xs font-medium text-gray-700 dark:text-slate-300">{display}</p>
        {relative && <p className="text-xs text-gray-400 dark:text-slate-500">{relative}</p>}
      </div>

      {/* Timeline line + dot */}
      <div className="flex flex-col items-center">
        <div
          className={cn(
            'w-3 h-3 rounded-full border-2 border-white ring-2 z-10',
            colors.dot,
            `ring-${colors.dot.replace('bg-', '').split('-')[0]}-200`,
          )}
        />
        <div className="w-0.5 bg-gray-200 dark:bg-slate-700 flex-1 min-h-[24px]" />
      </div>

      {/* Event card */}
      <div className="flex-1 pb-6">
        <div
          className={cn(
            'rounded-lg border p-3 transition-shadow hover:shadow-sm',
            colors.bg,
            colors.border,
            'dark:bg-slate-800 dark:border-slate-700',
          )}
        >
          <div className="flex items-start gap-2">
            <div className={cn('mt-0.5', colors.text)}>{getEventIcon(entry.icon_hint, 'w-4 h-4')}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={cn('text-xs font-medium px-1.5 py-0.5 rounded', colors.bg, colors.text)}>
                  {eventTypeLabel}
                </span>
                {enrichedEntry && (
                  <>
                    <ImportanceBadge importance={enrichedEntry.importance} />
                    <PhaseTag phase={enrichedEntry.lifecycle_phase} />
                  </>
                )}
              </div>
              <p className="text-sm font-medium text-gray-900 dark:text-white mt-1">{entry.title}</p>
              {entry.description && (
                <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5 line-clamp-2">{entry.description}</p>
              )}
              {entry.event_type === 'diagnostic_publication' && entry.metadata && (() => {
                const meta = entry.metadata as Record<string, unknown>;
                return (
                  <div className="flex flex-wrap items-center gap-1.5 mt-1.5" data-testid="diagnostic-pub-meta">
                    <span className="text-[10px] font-medium text-indigo-600 dark:text-indigo-400">
                      Imported from Batiscan V4
                    </span>
                    {meta.source_mission_id ? (
                      <span className="text-[10px] text-gray-500 dark:text-slate-400">
                        Mission {String(meta.source_mission_id)}
                      </span>
                    ) : null}
                    {meta.report_readiness_status ? (
                      <span
                        className={cn(
                          'px-1.5 py-0.5 rounded text-[10px] font-medium',
                          meta.report_readiness_status === 'ready'
                            ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                            : meta.report_readiness_status === 'blocked'
                              ? 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                              : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-400',
                        )}
                      >
                        {String(meta.report_readiness_status)}
                      </span>
                    ) : null}
                    {meta.sample_count != null && (
                      <span className="text-[10px] text-gray-500 dark:text-slate-400">
                        {String(meta.sample_count)} samples
                        {meta.positive_sample_count != null &&
                          `, ${String(meta.positive_sample_count)} positive`}
                      </span>
                    )}
                    {Array.isArray(meta.flags) &&
                      (meta.flags as string[]).map((flag: string) => (
                        <span
                          key={flag}
                          className={cn(
                            'px-1 py-0.5 rounded text-[10px] font-medium',
                            flag === 'no_ai'
                              ? 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300'
                              : flag === 'partial_package'
                                ? 'bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300'
                                : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-400',
                          )}
                        >
                          {flag.replace(/_/g, ' ')}
                        </span>
                      ))}
                  </div>
                );
              })()}
            </div>
            {entry.metadata && Object.keys(entry.metadata).length > 0 && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 transition-colors"
                aria-label={expanded ? 'Collapse' : 'Expand'}
              >
                <ChevronDown className={cn('w-4 h-4 transition-transform', expanded && 'rotate-180')} />
              </button>
            )}
          </div>

          {/* Expanded metadata */}
          {expanded && entry.metadata && (
            <div className="mt-3 pt-3 border-t border-gray-200/50 dark:border-slate-600/50">
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                {Object.entries(entry.metadata).map(([key, value]) => {
                  if (value === null || value === undefined) return null;
                  return (
                    <div key={key} className="text-xs">
                      <span className="text-gray-400 dark:text-slate-500">{key}: </span>
                      <span className="text-gray-700 dark:text-slate-300">{String(value)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ImportanceBadge({ importance }: { importance: ImportanceLevel }) {
  const { t } = useTranslation();
  const colors = IMPORTANCE_COLORS[importance];
  return (
    <span
      className={cn(
        'text-xs font-medium px-1.5 py-0.5 rounded',
        colors.bg,
        colors.text,
        colors.darkBg,
        colors.darkText,
      )}
    >
      {t(`timeline.importance_${importance}`) || importance}
    </span>
  );
}

function PhaseTag({ phase }: { phase: LifecyclePhase }) {
  const { t } = useTranslation();
  const colors = PHASE_COLORS[phase];
  return (
    <span
      className={cn(
        'text-xs font-medium px-1.5 py-0.5 rounded',
        colors.bg,
        colors.text,
        colors.darkBg,
        colors.darkText,
      )}
    >
      {t(`timeline.phase_${phase}`) || phase}
    </span>
  );
}

function LifecycleSummaryBar({ summary }: { summary: Record<string, number> }) {
  const { t } = useTranslation();
  const total = LIFECYCLE_PHASES.reduce((sum, phase) => sum + (summary[phase] || 0), 0);
  if (total === 0) return null;

  return (
    <div className="mb-4">
      <p className="text-xs font-medium text-gray-600 dark:text-slate-400 mb-1.5">
        {t('timeline.lifecycle_summary') || 'Lifecycle Summary'}
      </p>
      <div className="flex h-3 rounded-full overflow-hidden bg-gray-100 dark:bg-slate-700">
        {LIFECYCLE_PHASES.map((phase) => {
          const count = summary[phase] || 0;
          if (count === 0) return null;
          const pct = (count / total) * 100;
          return (
            <div
              key={phase}
              className={cn('h-full transition-all', PHASE_BAR_COLORS[phase])}
              style={{ width: `${pct}%` }}
              title={`${t(`timeline.phase_${phase}`) || phase}: ${count}`}
            />
          );
        })}
      </div>
      <div className="flex gap-3 mt-1.5 flex-wrap">
        {LIFECYCLE_PHASES.map((phase) => {
          const count = summary[phase] || 0;
          if (count === 0) return null;
          const colors = PHASE_COLORS[phase];
          return (
            <span key={phase} className={cn('text-xs', colors.text, colors.darkText)}>
              {t(`timeline.phase_${phase}`) || phase}: {count}
            </span>
          );
        })}
      </div>
    </div>
  );
}

interface BuildingTimelineProps {
  buildingId: string;
  eventTypeFilter?: string | null;
  lifecycleFilter?: LifecyclePhase | null;
  enrichedMode?: boolean;
}

export function BuildingTimeline({
  buildingId,
  eventTypeFilter,
  lifecycleFilter,
  enrichedMode,
}: BuildingTimelineProps) {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const simpleQuery = useQuery({
    queryKey: ['building-timeline', buildingId, page, eventTypeFilter],
    queryFn: () =>
      timelineApi.list(buildingId, {
        page,
        size: pageSize,
        event_type: eventTypeFilter || undefined,
      }),
    enabled: !enrichedMode,
  });

  const enrichedQuery = useQuery({
    queryKey: ['building-timeline-enriched', buildingId],
    queryFn: () => timelineApi.enriched(buildingId),
    enabled: !!enrichedMode,
  });

  if (enrichedMode) {
    const enrichedData = enrichedQuery.data;
    let entries = enrichedData?.entries || [];

    // Apply event type filter
    if (eventTypeFilter) {
      entries = entries.filter((e) => e.event_type === eventTypeFilter);
    }
    // Apply lifecycle phase filter
    if (lifecycleFilter) {
      entries = entries.filter((e) => e.lifecycle_phase === lifecycleFilter);
    }

    return (
      <AsyncStateWrapper
        isLoading={enrichedQuery.isLoading}
        isError={enrichedQuery.isError}
        data={entries}
        variant="inline"
        icon={<Clock className="w-5 h-5" />}
        emptyMessage={t('timeline.empty') || 'No timeline events'}
      >
        {enrichedData?.lifecycle_summary && <LifecycleSummaryBar summary={enrichedData.lifecycle_summary} />}

        <div className="pl-2">
          {entries.map((entry) => (
            <TimelineItem key={entry.id} entry={entry} enriched />
          ))}
        </div>
      </AsyncStateWrapper>
    );
  }

  const items = simpleQuery.data?.items || [];
  const pages = simpleQuery.data?.pages || 0;

  return (
    <AsyncStateWrapper
      isLoading={simpleQuery.isLoading}
      isError={simpleQuery.isError}
      data={items}
      variant="inline"
      icon={<Clock className="w-5 h-5" />}
      emptyMessage={t('timeline.empty') || 'No timeline events'}
    >
      <div className="pl-2">
        {items.map((entry) => (
          <TimelineItem key={entry.id} entry={entry} />
        ))}
      </div>

      {/* Load more / pagination */}
      {pages > 1 && page < pages && (
        <div className="text-center pt-2 pb-4">
          <button
            onClick={() => setPage((p) => p + 1)}
            className="text-sm text-red-600 hover:text-red-700 font-medium px-4 py-2 rounded-lg hover:bg-red-50 transition-colors"
          >
            {t('timeline.load_more')}
          </button>
        </div>
      )}
    </AsyncStateWrapper>
  );
}
