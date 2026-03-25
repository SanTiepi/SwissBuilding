import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { expansionApi } from '@/api/expansion';
import { cn, formatDate } from '@/utils/formatters';
import { Loader2, AlertTriangle, TrendingUp, CheckCircle2, XCircle, Zap, Radio } from 'lucide-react';

export default function AdminExpansion() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const {
    data: oppsData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['expansion-opportunities'],
    queryFn: () => expansionApi.listOpportunities({ size: 50 }),
  });

  const { data: triggers = [] } = useQuery({
    queryKey: ['expansion-triggers'],
    queryFn: () => expansionApi.listTriggers({ limit: 20 }),
  });

  const { data: signals = [] } = useQuery({
    queryKey: ['expansion-distribution-signals'],
    queryFn: () => expansionApi.listDistributionSignals({ limit: 10 }),
  });

  const actMutation = useMutation({
    mutationFn: (id: string) => expansionApi.actOnOpportunity(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['expansion-opportunities'] }),
  });

  const dismissMutation = useMutation({
    mutationFn: (id: string) => expansionApi.dismissOpportunity(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['expansion-opportunities'] }),
  });

  const opportunities = oppsData?.items ?? [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
      </div>
    );
  }

  const priorityColor = (p: string) => {
    const map: Record<string, string> = {
      high: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
      medium: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
      low: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
    };
    return map[p] || 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300';
  };

  const statusColor = (s: string) => {
    const map: Record<string, string> = {
      open: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
      acted: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
      dismissed: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300',
    };
    return map[s] || 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300';
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('expansion.title')}</h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('expansion.description')}</p>
      </div>

      {/* Opportunities */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-red-600" />
            {t('expansion.opportunities')}
          </h2>
        </div>
        {opportunities.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-slate-400">{t('expansion.empty')}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="expansion-opportunities-table">
              <thead className="bg-gray-50 dark:bg-slate-700/50">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('expansion.type')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('expansion.priority')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('expansion.recommended_action')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('expansion.evidence')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('expansion.status')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('form.actions')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-slate-700">
                {opportunities.map((opp) => (
                  <tr key={opp.id} data-testid={`opp-row-${opp.id}`}>
                    <td className="px-4 py-3 text-gray-900 dark:text-white">{opp.opportunity_type}</td>
                    <td className="px-4 py-3">
                      <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', priorityColor(opp.priority))}>
                        {opp.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-700 dark:text-slate-300">{opp.recommended_action}</td>
                    <td className="px-4 py-3 text-gray-500 dark:text-slate-400 text-xs">{opp.evidence}</td>
                    <td className="px-4 py-3">
                      <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', statusColor(opp.status))}>
                        {opp.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {opp.status === 'open' && (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => actMutation.mutate(opp.id)}
                            className="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400 hover:text-green-800"
                            data-testid={`act-${opp.id}`}
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            {t('expansion.act')}
                          </button>
                          <button
                            onClick={() => dismissMutation.mutate(opp.id)}
                            className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400 hover:text-gray-700"
                            data-testid={`dismiss-${opp.id}`}
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            {t('expansion.dismiss')}
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Triggers Feed + Distribution Signals */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Triggers */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-slate-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-500" />
              {t('expansion.triggers')}
            </h2>
          </div>
          {triggers.length === 0 ? (
            <div className="p-6 text-center text-gray-500 dark:text-slate-400">{t('expansion.no_triggers')}</div>
          ) : (
            <ul className="divide-y divide-gray-200 dark:divide-slate-700" data-testid="expansion-triggers-list">
              {triggers.map((trig) => (
                <li key={trig.id} className="px-6 py-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-sm font-medium text-gray-900 dark:text-white">{trig.trigger_type}</span>
                      <span className="ml-2 text-xs text-gray-500 dark:text-slate-400">{trig.source_entity}</span>
                      <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">{trig.detail}</p>
                    </div>
                    <span className="text-xs text-gray-400 dark:text-slate-500 whitespace-nowrap ml-4">
                      {formatDate(trig.created_at)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Distribution Signals */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-slate-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Radio className="w-5 h-5 text-purple-500" />
              {t('expansion.distribution_signals')}
            </h2>
          </div>
          {signals.length === 0 ? (
            <div className="p-6 text-center text-gray-500 dark:text-slate-400">{t('expansion.no_signals')}</div>
          ) : (
            <ul className="divide-y divide-gray-200 dark:divide-slate-700" data-testid="expansion-signals-list">
              {signals.map((sig) => (
                <li key={sig.id} className="px-6 py-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-sm font-medium text-gray-900 dark:text-white">{sig.signal_type}</span>
                      <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300">
                        {sig.channel}
                      </span>
                      <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">{sig.detail}</p>
                    </div>
                    <span className="text-xs text-gray-400 dark:text-slate-500 whitespace-nowrap ml-4">
                      {t('expansion.reach')}: {sig.reach}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
