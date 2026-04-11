/**
 * MIGRATION: ABSORB INTO BuildingDetail
 * This page will be absorbed into the BuildingDetail (Building Home) master workspace.
 * Per ADR-005 and V3 migration plan.
 * New features should target the master workspace directly.
 */
import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { useBuilding } from '@/hooks/useBuildings';
import { BuildingTimeline as TimelineComponent } from '@/components/BuildingTimeline';
import { ArrowLeft, Clock } from 'lucide-react';
import { cn } from '@/utils/formatters';
import { BuildingSubNav } from '@/components/BuildingSubNav';
import type { LifecyclePhase } from '@/types';

const EVENT_TYPES = [
  'construction',
  'diagnostic',
  'sample',
  'document',
  'intervention',
  'risk_change',
  'plan',
  'event',
  'diagnostic_publication',
] as const;

const LIFECYCLE_PHASES: LifecyclePhase[] = ['discovery', 'assessment', 'remediation', 'verification', 'closed'];

export default function BuildingTimeline() {
  const { buildingId } = useParams<{ buildingId: string }>();
  const { t } = useTranslation();
  const { data: building } = useBuilding(buildingId!);
  const [filter, setFilter] = useState<string | null>(null);
  const [enrichedMode, setEnrichedMode] = useState(false);
  const [lifecycleFilter, setLifecycleFilter] = useState<LifecyclePhase | null>(null);

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          to={`/buildings/${buildingId}`}
          className="inline-flex items-center text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 mb-3"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          {t('form.back')}
        </Link>
        <div className="mb-3">
          <BuildingSubNav buildingId={buildingId!} />
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Clock className="w-6 h-6 text-red-600" />
            <div>
              <h1 className="text-xl font-semibold text-gray-900 dark:text-white">{t('timeline.title')}</h1>
              {building && (
                <p className="text-sm text-gray-500 dark:text-slate-400">
                  {building.address}, {building.postal_code} {building.city}
                </p>
              )}
            </div>
          </div>

          {/* Enriched / Simple toggle */}
          <button
            onClick={() => {
              setEnrichedMode((prev) => !prev);
              setLifecycleFilter(null);
            }}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors border',
              enrichedMode
                ? 'bg-red-600 text-white border-red-600'
                : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-slate-300 border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700',
            )}
          >
            {enrichedMode ? t('timeline.enriched_view') : t('timeline.simple_view')}
          </button>
        </div>
      </div>

      {/* Filter chips */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          onClick={() => setFilter(null)}
          className={cn(
            'px-3 py-1.5 text-xs font-medium rounded-full transition-colors',
            filter === null
              ? 'bg-red-600 text-white'
              : 'bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-700',
          )}
        >
          {t('timeline.filter.all')}
        </button>
        {EVENT_TYPES.map((type) => {
          const label =
            type === 'diagnostic_publication'
              ? t('timeline.event_type.diagnostic_publication') || 'Imported Reports'
              : t(`timeline.event_type.${type}`);
          return (
            <button
              key={type}
              onClick={() => setFilter(filter === type ? null : type)}
              className={cn(
                'px-3 py-1.5 text-xs font-medium rounded-full transition-colors',
                filter === type
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-700',
              )}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Lifecycle phase filter chips (enriched mode only) */}
      {enrichedMode && (
        <div className="flex flex-wrap gap-2 mb-6">
          <span className="px-2 py-1.5 text-xs font-medium text-gray-500 dark:text-slate-400">
            {t('timeline.lifecycle_phase')}:
          </span>
          <button
            onClick={() => setLifecycleFilter(null)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-full transition-colors',
              lifecycleFilter === null
                ? 'bg-red-600 text-white'
                : 'bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-700',
            )}
          >
            {t('timeline.filter.all')}
          </button>
          {LIFECYCLE_PHASES.map((phase) => (
            <button
              key={phase}
              onClick={() => setLifecycleFilter(lifecycleFilter === phase ? null : phase)}
              className={cn(
                'px-3 py-1.5 text-xs font-medium rounded-full transition-colors',
                lifecycleFilter === phase
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-700',
              )}
            >
              {t(`timeline.phase_${phase}`)}
            </button>
          ))}
        </div>
      )}

      {/* Timeline */}
      <div className="bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-800 p-6">
        <TimelineComponent
          buildingId={buildingId!}
          eventTypeFilter={filter}
          enrichedMode={enrichedMode}
          lifecycleFilter={lifecycleFilter}
        />
      </div>
    </div>
  );
}
