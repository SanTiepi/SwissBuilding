import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { apiClient } from '@/api/client';
import { Loader2, CheckCircle2, AlertTriangle, ChevronRight, BarChart3, Target } from 'lucide-react';
import { cn } from '@/utils/formatters';
import { useState } from 'react';

interface PilotScorecardPanelProps {
  buildingId: string;
}

interface BuildingScorecard {
  building_id: string;
  building_name: string;
  completeness_pct: number;
  blockers_open: number;
  blockers_total: number;
  blockers_resolved: number;
  actions_total: number;
  actions_completed: number;
  actions_open: number;
  diagnostics_total: number;
  diagnostics_valid: number;
  diagnostics_expired: number;
  documents_count: number;
  dossier_stage: string;
  dossier_stage_label: string;
}

const stageColors: Record<string, string> = {
  not_assessed: 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
  partially_ready: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  ready: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  pack_generated: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  submitted: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
  complement_requested: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  acknowledged: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
};

export function PilotScorecardPanel({ buildingId }: PilotScorecardPanelProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  const {
    data: scorecard,
    isLoading,
    isError,
  } = useQuery<BuildingScorecard>({
    queryKey: ['building-scorecard', buildingId],
    queryFn: async () => {
      const res = await apiClient.get(`/buildings/${buildingId}/scorecard`);
      return res.data;
    },
    enabled: !!buildingId,
    retry: false,
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-5">
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
        </div>
      </div>
    );
  }

  if (isError || !scorecard || scorecard.actions_total === 0) {
    return null; // Gracefully hide if no data
  }

  const blockersResolved = scorecard.blockers_resolved;
  const blockersTotal = scorecard.blockers_total;
  const blockersRatio = blockersTotal > 0 ? Math.round((blockersResolved / blockersTotal) * 100) : 0;

  const actionsCompleted = scorecard.actions_completed;
  const actionsTotal = scorecard.actions_total;
  const actionsRatio = actionsTotal > 0 ? Math.round((actionsCompleted / actionsTotal) * 100) : 0;

  return (
    <div
      className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-5"
      data-testid="pilot-scorecard-panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Target className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            {t('pilot.scorecard_title') || 'Fiche pilote'}
          </h3>
        </div>
        <span
          className={cn(
            'px-2.5 py-0.5 rounded-full text-xs font-medium',
            stageColors[scorecard.dossier_stage] || stageColors.not_assessed,
          )}
        >
          {scorecard.dossier_stage_label}
        </span>
      </div>

      {/* Completeness bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-slate-400 mb-1">
          <span>{t('pilot.completeness') || 'Completude'}</span>
          <span>{scorecard.completeness_pct}%</span>
        </div>
        <div className="h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all',
              scorecard.completeness_pct >= 75
                ? 'bg-green-500'
                : scorecard.completeness_pct >= 50
                  ? 'bg-amber-500'
                  : 'bg-red-500',
            )}
            style={{ width: `${scorecard.completeness_pct}%` }}
          />
        </div>
      </div>

      {/* Compact metrics row */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        {/* Blockers */}
        <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
          <div className="flex items-center gap-1.5 mb-1">
            {scorecard.blockers_open > 0 ? (
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
            ) : (
              <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
            )}
            <span className="text-xs text-gray-500 dark:text-slate-400">{t('pilot.blockers') || 'Blocages'}</span>
          </div>
          <p className="text-lg font-bold text-gray-900 dark:text-white">
            {blockersResolved}/{blockersTotal}
          </p>
          <p className="text-[10px] text-gray-400 dark:text-slate-500">{blockersRatio}% resolus</p>
        </div>

        {/* Actions */}
        <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <BarChart3 className="w-3.5 h-3.5 text-indigo-500" />
            <span className="text-xs text-gray-500 dark:text-slate-400">{t('pilot.actions') || 'Actions'}</span>
          </div>
          <p className="text-lg font-bold text-gray-900 dark:text-white">
            {actionsCompleted}/{actionsTotal}
          </p>
          <p className="text-[10px] text-gray-400 dark:text-slate-500">{actionsRatio}% completees</p>
        </div>
      </div>

      {/* Expand for full details */}
      {expanded && (
        <div className="border-t border-gray-100 dark:border-slate-700 pt-3 mt-1 space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-gray-500 dark:text-slate-400">Diagnostics valides</span>
            <span className="font-medium text-gray-900 dark:text-white">
              {scorecard.diagnostics_valid}/{scorecard.diagnostics_total}
            </span>
          </div>
          {scorecard.diagnostics_expired > 0 && (
            <div className="flex justify-between text-xs">
              <span className="text-amber-600 dark:text-amber-400">Diagnostics expires</span>
              <span className="font-medium text-amber-600 dark:text-amber-400">{scorecard.diagnostics_expired}</span>
            </div>
          )}
          <div className="flex justify-between text-xs">
            <span className="text-gray-500 dark:text-slate-400">Documents</span>
            <span className="font-medium text-gray-900 dark:text-white">{scorecard.documents_count}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-gray-500 dark:text-slate-400">Actions ouvertes</span>
            <span className="font-medium text-gray-900 dark:text-white">{scorecard.actions_open}</span>
          </div>
        </div>
      )}

      {/* Toggle */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-3 w-full flex items-center justify-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors"
      >
        {expanded ? t('common.collapse') || 'Reduire' : t('pilot.view_full') || 'Voir la fiche pilote complete'}
        <ChevronRight className={cn('w-3.5 h-3.5 transition-transform', expanded ? 'rotate-90' : '')} />
      </button>
    </div>
  );
}

export default PilotScorecardPanel;
