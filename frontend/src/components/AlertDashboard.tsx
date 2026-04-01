import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { proactiveAlertsApi, type ProactiveAlert, type AlertSummary } from '@/api/proactiveAlerts';
import { AlertTriangle, Bell, Info, RefreshCw, Shield } from 'lucide-react';

// ---------------------------------------------------------------------------
// Severity styles
// ---------------------------------------------------------------------------

const SEVERITY_STYLES = {
  critical: {
    badge: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    border: 'border-red-300 dark:border-red-700',
    bg: 'bg-red-50 dark:bg-red-900/20',
    icon: 'text-red-600 dark:text-red-400',
  },
  warning: {
    badge: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    border: 'border-amber-300 dark:border-amber-700',
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    icon: 'text-amber-600 dark:text-amber-400',
  },
  info: {
    badge: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    border: 'border-blue-300 dark:border-blue-700',
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    icon: 'text-blue-600 dark:text-blue-400',
  },
} as const;

const SEVERITY_ICONS: Record<string, typeof AlertTriangle> = {
  critical: AlertTriangle,
  warning: Bell,
  info: Info,
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function AlertCard({ alert }: { alert: ProactiveAlert }) {
  const style = SEVERITY_STYLES[alert.severity as keyof typeof SEVERITY_STYLES] ?? SEVERITY_STYLES.info;
  const Icon = SEVERITY_ICONS[alert.severity] ?? Info;

  return (
    <div className={cn('rounded-lg border p-3', style.border, style.bg)}>
      <div className="flex items-start gap-2">
        <Icon className={cn('mt-0.5 h-4 w-4 flex-shrink-0', style.icon)} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{alert.title}</p>
          <p className="mt-0.5 text-xs text-gray-600 dark:text-gray-400">{alert.message}</p>
          {alert.recommended_action && (
            <p className="mt-1 text-xs font-medium text-gray-700 dark:text-gray-300">
              <Shield className="mr-1 inline h-3 w-3" />
              {alert.recommended_action}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function AlertDashboard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);
  const [buildingFilter, setBuildingFilter] = useState<string | null>(null);

  const summaryQuery = useQuery({
    queryKey: ['proactive-alerts-summary'],
    queryFn: () => proactiveAlertsApi.getSummary(),
  });

  const scanMutation = useMutation({
    mutationFn: () => proactiveAlertsApi.scanPortfolio(),
    onSuccess: (data) => {
      setScanResults(data);
      queryClient.invalidateQueries({ queryKey: ['proactive-alerts-summary'] });
    },
  });

  const [scanResults, setScanResults] = useState<ProactiveAlert[] | null>(null);

  const summary: AlertSummary = summaryQuery.data ?? {
    total_alerts: 0,
    by_severity: { critical: 0, warning: 0, info: 0 },
    by_type: {},
    buildings_with_alerts: 0,
  };

  // Filter scan results
  const filteredAlerts = scanResults
    ? scanResults.filter((a) => {
        if (severityFilter && a.severity !== severityFilter) return false;
        if (buildingFilter && a.building_id !== buildingFilter) return false;
        return true;
      })
    : null;

  // Unique buildings for filter
  const buildingIds = scanResults ? [...new Set(scanResults.map((a) => a.building_id))] : [];

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
          <p className="text-xs text-gray-500 dark:text-gray-400">{t('alerts.title')}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{summary.total_alerts}</p>
        </div>
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
          <p className="text-xs text-red-600 dark:text-red-400">{t('alerts.critical')}</p>
          <p className="mt-1 text-2xl font-bold text-red-700 dark:text-red-300">
            {summary.by_severity.critical ?? 0}
          </p>
        </div>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-900/20">
          <p className="text-xs text-amber-600 dark:text-amber-400">{t('alerts.warning')}</p>
          <p className="mt-1 text-2xl font-bold text-amber-700 dark:text-amber-300">
            {summary.by_severity.warning ?? 0}
          </p>
        </div>
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20">
          <p className="text-xs text-blue-600 dark:text-blue-400">{t('alerts.info')}</p>
          <p className="mt-1 text-2xl font-bold text-blue-700 dark:text-blue-300">
            {summary.by_severity.info ?? 0}
          </p>
        </div>
      </div>

      {/* Buildings with alerts */}
      <p className="text-sm text-gray-600 dark:text-gray-400">
        {t('alerts.buildings_with_alerts')}: {summary.buildings_with_alerts}
      </p>

      {/* Scan button */}
      <button
        onClick={() => scanMutation.mutate()}
        disabled={scanMutation.isPending}
        className={cn(
          'inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white',
          'bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50',
          'dark:bg-indigo-500 dark:hover:bg-indigo-600',
        )}
      >
        <RefreshCw className={cn('h-4 w-4', scanMutation.isPending && 'animate-spin')} />
        {scanMutation.isPending ? t('alerts.scanning') : t('alerts.scan_portfolio')}
      </button>

      {/* Filters (shown after scan) */}
      {scanResults && scanResults.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSeverityFilter(null)}
            className={cn(
              'rounded-full px-3 py-1 text-xs',
              !severityFilter
                ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
                : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
            )}
          >
            {t('alerts.title')}
          </button>
          {(['critical', 'warning', 'info'] as const).map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(severityFilter === sev ? null : sev)}
              className={cn(
                'rounded-full px-3 py-1 text-xs',
                severityFilter === sev
                  ? SEVERITY_STYLES[sev].badge
                  : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
              )}
            >
              {t(`alerts.${sev}`)}
            </button>
          ))}
          {buildingIds.length > 1 && (
            <select
              value={buildingFilter ?? ''}
              onChange={(e) => setBuildingFilter(e.target.value || null)}
              className="rounded-lg border border-gray-300 px-2 py-1 text-xs dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
            >
              <option value="">{t('alerts.title')}</option>
              {buildingIds.map((bid) => (
                <option key={bid} value={bid}>
                  {bid.slice(0, 8)}...
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {/* Alert list */}
      {filteredAlerts && filteredAlerts.length > 0 && (
        <div className="space-y-2">
          {filteredAlerts.map((alert, i) => (
            <AlertCard key={`${alert.alert_type}-${alert.entity_id}-${i}`} alert={alert} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {scanResults && scanResults.length === 0 && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-6 text-center dark:border-green-800 dark:bg-green-900/20">
          <Shield className="mx-auto h-8 w-8 text-green-600 dark:text-green-400" />
          <p className="mt-2 text-sm font-medium text-green-700 dark:text-green-300">{t('alerts.no_alerts')}</p>
        </div>
      )}
    </div>
  );
}
