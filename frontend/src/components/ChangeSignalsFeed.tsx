import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { changeSignalsApi } from '@/api/changeSignals';
import type { ChangeSignal } from '@/api/changeSignals';
import { useTranslation } from '@/i18n';
import { cn, formatDate } from '@/utils/formatters';
import {
  Bell,
  ExternalLink,
  Stethoscope,
  RefreshCw,
  FileText,
  FlaskConical,
  Wrench,
  Shield,
  ShieldCheck,
} from 'lucide-react';
import { AsyncStateWrapper } from './AsyncStateWrapper';

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500',
  warning: 'bg-orange-500',
  info: 'bg-blue-500',
};

const SIGNAL_TYPE_ICON: Record<string, typeof Bell> = {
  new_diagnostic: Stethoscope,
  status_change: RefreshCw,
  document_added: FileText,
  sample_result: FlaskConical,
  intervention_complete: Wrench,
  trust_change: Shield,
  readiness_change: ShieldCheck,
};

const SIGNAL_TYPE_COLOR: Record<string, string> = {
  new_diagnostic: 'text-green-500',
  status_change: 'text-blue-500',
  document_added: 'text-purple-500',
  sample_result: 'text-red-500',
  intervention_complete: 'text-teal-500',
  trust_change: 'text-amber-500',
  readiness_change: 'text-indigo-500',
};

export function ChangeSignalsFeed({ buildingId }: { buildingId: string }) {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['building-change-signals', buildingId],
    queryFn: () => changeSignalsApi.list(buildingId),
    enabled: !!buildingId,
  });

  const signals = data?.items ?? [];
  const activeSignals = signals.filter((s) => s.status === 'active');

  return (
    <AsyncStateWrapper
      isLoading={isLoading}
      isError={isError}
      data={data}
      variant="card"
      title={t('change_signal.title') || 'Change Signals'}
      icon={<Bell className="w-5 h-5" />}
      emptyMessage={t('change_signal.none') || 'No active signals'}
      isEmpty={!isLoading && !isError && activeSignals.length === 0}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            {t('change_signal.title') || 'Change Signals'}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">
            {activeSignals.length}
          </span>
          <Link
            to={`/buildings/${buildingId}/change-signals`}
            className="text-xs text-red-600 hover:text-red-700 dark:text-red-400 flex items-center gap-0.5"
          >
            {t('change_signal.view_all') || 'View all'}
            <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
      </div>
      <ul className="space-y-2">
        {activeSignals.slice(0, 5).map((signal: ChangeSignal) => {
          const Icon = SIGNAL_TYPE_ICON[signal.signal_type] || Bell;
          const iconColor = SIGNAL_TYPE_COLOR[signal.signal_type] || 'text-gray-400';
          return (
            <li key={signal.id} className="flex items-start gap-2 text-sm">
              <Icon className={cn('w-4 h-4 mt-0.5 flex-shrink-0', iconColor)} />
              <span
                className={cn(
                  'w-2 h-2 rounded-full mt-1.5 flex-shrink-0',
                  SEVERITY_COLORS[signal.severity] ?? 'bg-gray-400',
                )}
              />
              <div className="min-w-0 flex-1">
                <p className="text-gray-700 dark:text-slate-200 truncate">{signal.title}</p>
                <p className="text-xs text-gray-400 dark:text-slate-500">{formatDate(signal.detected_at)}</p>
              </div>
            </li>
          );
        })}
        {activeSignals.length > 5 && (
          <li className="text-xs text-gray-500 dark:text-slate-400">
            +{activeSignals.length - 5} {t('common.more') || 'more'}
          </li>
        )}
      </ul>
    </AsyncStateWrapper>
  );
}
