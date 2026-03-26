import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { cn, formatDate } from '@/utils/formatters';
import { publicSectorApi, type GovernanceSignalData } from '@/api/publicSector';
import { AlertTriangle, CheckCircle2, Loader2, Shield, Search, Info, AlertCircle } from 'lucide-react';

const SEVERITY_COLORS: Record<string, string> = {
  info: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  warning: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const SEVERITY_ICONS: Record<string, React.ElementType> = {
  info: Info,
  warning: AlertTriangle,
  critical: AlertCircle,
};

export default function AdminGovernanceSignals() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const orgId = user?.organization_id;

  const [filterBuilding] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('');

  const {
    data: signals = [],
    isLoading,
    isError,
  } = useQuery<GovernanceSignalData[]>({
    queryKey: ['governance-signals', orgId],
    queryFn: () => publicSectorApi.listGovernanceSignals(orgId!),
    enabled: !!orgId,
    retry: false,
  });

  const resolveMutation = useMutation({
    mutationFn: (signalId: string) => publicSectorApi.resolveGovernanceSignal(signalId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['governance-signals', orgId] }),
  });

  // Derive unique filter values
  const signalTypes = [...new Set(signals.map((s) => s.signal_type))];
  const severities = [...new Set(signals.map((s) => s.severity))];

  // Filter
  const filtered = signals.filter((s) => {
    if (filterSeverity && s.severity !== filterSeverity) return false;
    if (filterType && s.signal_type !== filterType) return false;
    if (filterBuilding && s.building_id !== filterBuilding) return false;
    if (!s.resolved) return true; // show active by default
    return false;
  });

  // Also show resolved if no active signals match
  const activeSignals = signals.filter((s) => !s.resolved);
  const showResolved = activeSignals.length === 0;
  const displaySignals = showResolved ? signals : filtered;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-6 h-6 text-red-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {t('public_sector.governance_signals_title')}
            </h1>
            <p className="text-sm text-gray-500 dark:text-slate-400">
              {t('public_sector.governance_signals_subtitle')}
            </p>
          </div>
        </div>
        <span className="text-sm text-gray-500 dark:text-slate-400">
          {activeSignals.length} {t('public_sector.active_signals')}
        </span>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4">
        <div className="flex flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-gray-400" />
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              data-testid="filter-severity"
              className="px-2 py-1 text-sm border border-gray-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 dark:text-white"
            >
              <option value="">{t('public_sector.all_severities')}</option>
              {severities.map((s) => (
                <option key={s} value={s}>
                  {t(`public_sector.severity.${s}`) || s}
                </option>
              ))}
            </select>
          </div>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            data-testid="filter-signal-type"
            className="px-2 py-1 text-sm border border-gray-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 dark:text-white"
          >
            <option value="">{t('public_sector.all_types')}</option>
            {signalTypes.map((st) => (
              <option key={st} value={st}>
                {st}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Content */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      )}

      {isError && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
        </div>
      )}

      {!isLoading && !isError && displaySignals.length === 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-8 text-center">
          <CheckCircle2 className="w-8 h-8 text-green-500 mx-auto mb-2" />
          <p className="text-gray-500 dark:text-slate-400" data-testid="no-signals">
            {t('public_sector.no_governance_signals')}
          </p>
        </div>
      )}

      {displaySignals.length > 0 && (
        <div className="space-y-3">
          {displaySignals.map((signal) => {
            const SeverityIcon = SEVERITY_ICONS[signal.severity] || Info;
            return (
              <div
                key={signal.id}
                className={cn(
                  'bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4',
                  signal.resolved && 'opacity-60',
                )}
                data-testid="governance-signal-item"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <SeverityIcon
                      className={cn(
                        'w-5 h-5 mt-0.5',
                        signal.severity === 'critical'
                          ? 'text-red-500'
                          : signal.severity === 'warning'
                            ? 'text-orange-500'
                            : 'text-blue-500',
                      )}
                    />
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-gray-900 dark:text-white" data-testid="signal-title">
                          {signal.title}
                        </span>
                        <span
                          className={cn(
                            'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
                            SEVERITY_COLORS[signal.severity] || SEVERITY_COLORS.info,
                          )}
                          data-testid="signal-severity-badge"
                        >
                          {t(`public_sector.severity.${signal.severity}`) || signal.severity}
                        </span>
                        <span className="text-xs text-gray-400 dark:text-slate-500">{signal.signal_type}</span>
                      </div>
                      {signal.description && (
                        <p className="text-sm text-gray-600 dark:text-slate-300 mb-1">{signal.description}</p>
                      )}
                      <span className="text-xs text-gray-400 dark:text-slate-500">{formatDate(signal.created_at)}</span>
                    </div>
                  </div>
                  {!signal.resolved && (
                    <button
                      onClick={() => resolveMutation.mutate(signal.id)}
                      disabled={resolveMutation.isPending}
                      data-testid="resolve-signal-button"
                      className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
                    >
                      {resolveMutation.isPending ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <CheckCircle2 className="w-3.5 h-3.5" />
                      )}
                      {t('public_sector.resolve')}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
