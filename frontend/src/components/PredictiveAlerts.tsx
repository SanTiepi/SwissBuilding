import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import {
  predictiveReadinessApi,
  type PredictiveAlert,
  type PredictiveProjection,
} from '@/api/predictiveReadiness';
import {
  AlertTriangle,
  Clock,
  Shield,
  ChevronRight,
  TrendingDown,
  FileWarning,
  Wrench,
  CalendarClock,
  ShieldAlert,
  Zap,
  ArrowRight,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Severity config
// ---------------------------------------------------------------------------

const SEVERITY_STYLES = {
  critical: {
    border: 'border-red-300 dark:border-red-700',
    bg: 'bg-red-50 dark:bg-red-900/20',
    badge: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    icon: 'text-red-600 dark:text-red-400',
    dot: 'bg-red-500',
  },
  warning: {
    border: 'border-amber-300 dark:border-amber-700',
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    badge: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    icon: 'text-amber-600 dark:text-amber-400',
    dot: 'bg-amber-500',
  },
  info: {
    border: 'border-blue-300 dark:border-blue-700',
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    badge: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    icon: 'text-blue-600 dark:text-blue-400',
    dot: 'bg-blue-500',
  },
} as const;

const ALERT_TYPE_ICONS: Record<string, typeof AlertTriangle> = {
  diagnostic_expiring: FileWarning,
  readiness_degradation: TrendingDown,
  obligation_due: CalendarClock,
  coverage_gap: ShieldAlert,
  intervention_unready: Wrench,
};

const READINESS_COLORS: Record<string, string> = {
  ready: 'text-green-700 dark:text-green-400 bg-green-100 dark:bg-green-900/30',
  partial: 'text-amber-700 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/30',
  not_ready: 'text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-900/30',
};

const READINESS_LABELS: Record<string, string> = {
  ready: 'Pret',
  partial: 'Partiel',
  not_ready: 'Non pret',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function DaysRemainingBadge({ days }: { days: number | null }) {
  if (days === null) return null;
  const label =
    days < 0
      ? `${Math.abs(days)}j en retard`
      : days === 0
        ? "Aujourd'hui"
        : `${days}j`;
  const color =
    days <= 0
      ? 'bg-red-600 text-white'
      : days <= 30
        ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
        : days <= 90
          ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
          : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300';

  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold', color)}>
      <Clock className="w-3 h-3" />
      {label}
    </span>
  );
}

function AlertCard({
  alert,
  compact = false,
  onNavigate,
}: {
  alert: PredictiveAlert;
  compact?: boolean;
  onNavigate?: (buildingId: string) => void;
}) {
  const styles = SEVERITY_STYLES[alert.severity];
  const Icon = ALERT_TYPE_ICONS[alert.alert_type] || AlertTriangle;

  return (
    <div className={cn('rounded-lg border p-3', styles.border, styles.bg)}>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          <Icon className={cn('w-5 h-5', styles.icon)} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold text-gray-900 dark:text-white">{alert.title}</p>
            <DaysRemainingBadge days={alert.days_remaining} />
          </div>
          {!compact && (
            <p className="text-xs text-gray-600 dark:text-slate-300 mt-1">{alert.description}</p>
          )}
          {onNavigate && (
            <button
              onClick={() => onNavigate(alert.building_id)}
              className="text-xs text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 mt-0.5 truncate block"
            >
              {alert.building_name}
            </button>
          )}
          <div className="flex items-center gap-2 mt-2">
            <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium', styles.badge)}>
              <Zap className="w-3 h-3" />
              {alert.recommended_action}
            </span>
          </div>
        </div>
        {onNavigate && (
          <button
            onClick={() => onNavigate(alert.building_id)}
            className="flex-shrink-0 inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
          >
            Agir
            <ChevronRight className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  );
}

function ProjectionTable({ projections }: { projections: PredictiveProjection[] }) {
  const navigate = useNavigate();
  const degrading = projections.filter(
    (p) => p.current_readiness !== p.projected_readiness_90d || p.degradation_reason,
  );

  if (degrading.length === 0) return null;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-200 dark:border-slate-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <TrendingDown className="w-4 h-4 text-amber-500" />
          Projections de readiness
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-slate-700">
          <thead className="bg-gray-50 dark:bg-slate-700/50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                Batiment
              </th>
              <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                Actuelle
              </th>
              <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                30j
              </th>
              <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                90j
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                Raison
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-slate-700">
            {degrading.map((proj) => (
              <tr
                key={proj.building_id}
                className="hover:bg-gray-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors"
                onClick={() => navigate(`/buildings/${proj.building_id}`)}
              >
                <td className="px-4 py-2 text-sm text-gray-900 dark:text-white whitespace-nowrap">
                  {proj.building_name}
                </td>
                <td className="px-4 py-2 text-center">
                  <span className={cn('inline-block px-2 py-0.5 rounded-full text-xs font-medium', READINESS_COLORS[proj.current_readiness])}>
                    {READINESS_LABELS[proj.current_readiness] || proj.current_readiness}
                  </span>
                </td>
                <td className="px-4 py-2 text-center">
                  <span className={cn('inline-block px-2 py-0.5 rounded-full text-xs font-medium', READINESS_COLORS[proj.projected_readiness_30d])}>
                    {READINESS_LABELS[proj.projected_readiness_30d] || proj.projected_readiness_30d}
                  </span>
                </td>
                <td className="px-4 py-2 text-center">
                  <span className={cn('inline-block px-2 py-0.5 rounded-full text-xs font-medium', READINESS_COLORS[proj.projected_readiness_90d])}>
                    {READINESS_LABELS[proj.projected_readiness_90d] || proj.projected_readiness_90d}
                  </span>
                </td>
                <td className="px-4 py-2 text-xs text-gray-500 dark:text-slate-400">
                  {proj.degradation_reason || '\u2014'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component — Portfolio mode
// ---------------------------------------------------------------------------

export function PredictiveAlertsPortfolio() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showAll, setShowAll] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['predictive-readiness', 'portfolio'],
    queryFn: predictiveReadinessApi.scanPortfolio,
    staleTime: 5 * 60 * 1000,
  });

  const generateMutation = useMutation({
    mutationFn: predictiveReadinessApi.generateActions,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['predictive-readiness'] });
    },
  });

  const handleNavigate = (buildingId: string) => {
    navigate(`/buildings/${buildingId}`);
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-200 dark:bg-slate-600 rounded w-48" />
          <div className="h-20 bg-gray-200 dark:bg-slate-600 rounded" />
          <div className="h-20 bg-gray-200 dark:bg-slate-600 rounded" />
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return null;
  }

  const { alerts, summary, projections } = data;

  if (alerts.length === 0) {
    return (
      <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-6">
        <div className="flex items-center gap-3">
          <Shield className="w-6 h-6 text-green-600 dark:text-green-400" />
          <div>
            <p className="text-sm font-semibold text-green-800 dark:text-green-200">
              {t('predictive.no_alerts') || 'Aucune alerte predictive'}
            </p>
            <p className="text-xs text-green-600 dark:text-green-400 mt-0.5">
              Tous les batiments sont en ordre pour les 12 prochains mois.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const visibleAlerts = showAll ? alerts : alerts.slice(0, 5);

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            {t('predictive.title') || 'Alertes predictives'}
          </h2>
          {summary.critical > 0 || summary.warning > 0 ? (
            <button
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-lg transition-colors"
            >
              <Zap className="w-3 h-3" />
              {generateMutation.isPending
                ? 'Creation...'
                : t('predictive.generate_actions') || 'Generer les actions'}
            </button>
          ) : null}
        </div>
        <div className="flex gap-4 text-xs">
          {summary.critical > 0 && (
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span className="font-semibold text-red-700 dark:text-red-300">{summary.critical}</span>
              <span className="text-gray-500 dark:text-slate-400">critiques</span>
            </span>
          )}
          {summary.warning > 0 && (
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              <span className="font-semibold text-amber-700 dark:text-amber-300">{summary.warning}</span>
              <span className="text-gray-500 dark:text-slate-400">avertissements</span>
            </span>
          )}
          {summary.info > 0 && (
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              <span className="font-semibold text-blue-700 dark:text-blue-300">{summary.info}</span>
              <span className="text-gray-500 dark:text-slate-400">infos</span>
            </span>
          )}
          <span className="text-gray-400 dark:text-slate-500">|</span>
          <span className="text-gray-600 dark:text-slate-300">
            <span className="font-semibold">{summary.buildings_at_risk}</span> batiment(s) a risque
          </span>
          {summary.diagnostics_expiring_90d > 0 && (
            <>
              <span className="text-gray-400 dark:text-slate-500">|</span>
              <span className="text-gray-600 dark:text-slate-300">
                <span className="font-semibold">{summary.diagnostics_expiring_90d}</span> diagnostic(s) expirant sous 90j
              </span>
            </>
          )}
        </div>
        {generateMutation.isSuccess && (
          <p className="text-xs text-green-600 dark:text-green-400 mt-2">
            {generateMutation.data.created_count} action(s) creee(s) avec succes.
          </p>
        )}
      </div>

      {/* Alert cards */}
      <div className="space-y-2">
        {visibleAlerts.map((alert) => (
          <AlertCard key={alert.id} alert={alert} onNavigate={handleNavigate} />
        ))}
      </div>

      {alerts.length > 5 && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="w-full py-2 text-xs font-medium text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 transition-colors flex items-center justify-center gap-1"
        >
          {showAll ? 'Voir moins' : `Voir les ${alerts.length - 5} alertes restantes`}
          <ArrowRight className={cn('w-3 h-3 transition-transform', showAll && 'rotate-90')} />
        </button>
      )}

      {/* Projection table */}
      <ProjectionTable projections={projections} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Building mode — compact version for OverviewTab
// ---------------------------------------------------------------------------

export function PredictiveAlertsBuilding({ buildingId }: { buildingId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['predictive-readiness', 'building', buildingId],
    queryFn: () => predictiveReadinessApi.scanBuilding(buildingId),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading || isError || !data || data.alerts.length === 0) {
    return null;
  }

  const { alerts, summary } = data;
  const topAlerts = alerts.slice(0, 3);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          Alertes predictives
        </h3>
        <div className="flex gap-2 text-xs">
          {summary.critical > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 font-semibold">
              {summary.critical} critique(s)
            </span>
          )}
          {summary.warning > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 font-semibold">
              {summary.warning} avert.
            </span>
          )}
        </div>
      </div>
      <div className="space-y-2">
        {topAlerts.map((alert) => (
          <AlertCard key={alert.id} alert={alert} compact />
        ))}
      </div>
      {alerts.length > 3 && (
        <p className="text-xs text-gray-500 dark:text-slate-400 mt-2 text-center">
          +{alerts.length - 3} alerte(s) supplementaire(s)
        </p>
      )}
    </div>
  );
}
