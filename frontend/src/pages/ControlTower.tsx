import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import {
  AlertTriangle,
  Clock,
  Inbox,
  FileQuestion,
  UserPlus,
  RefreshCw,
  ArrowRight,
  Building2,
  Filter,
} from 'lucide-react';
import { cn, formatDate } from '@/utils/formatters';
import { fetchControlTowerData, buildNextBestActions, type NextBestAction } from '@/api/controlTower';

const ACTION_TYPE_CONFIG: Record<
  NextBestAction['type'],
  { icon: React.ElementType; color: string; bgColor: string; darkBgColor: string }
> = {
  overdue_obligation: {
    icon: AlertTriangle,
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-50',
    darkBgColor: 'dark:bg-red-950/30',
  },
  unmatched_publication: {
    icon: FileQuestion,
    color: 'text-amber-600 dark:text-amber-400',
    bgColor: 'bg-amber-50',
    darkBgColor: 'dark:bg-amber-950/30',
  },
  pending_inbox: {
    icon: Inbox,
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50',
    darkBgColor: 'dark:bg-blue-950/30',
  },
  intake_request: {
    icon: UserPlus,
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-50',
    darkBgColor: 'dark:bg-purple-950/30',
  },
  due_soon_obligation: {
    icon: Clock,
    color: 'text-orange-600 dark:text-orange-400',
    bgColor: 'bg-orange-50',
    darkBgColor: 'dark:bg-orange-950/30',
  },
};

export default function ControlTower() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [buildingFilter, setBuildingFilter] = useState<string>('');

  const {
    data: summary,
    isLoading,
    isError,
    isFetching,
  } = useQuery({
    queryKey: ['control-tower', buildingFilter],
    queryFn: () => fetchControlTowerData(buildingFilter || undefined),
    staleTime: 60_000,
  });

  const actions = useMemo(() => (summary ? buildNextBestActions(summary) : []), [summary]);

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['control-tower'] });
  };

  if (isLoading) {
    return (
      <div className="p-4 sm:p-6 lg:p-8 space-y-6" data-testid="control-tower-loading">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-48" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-xl" />
            ))}
          </div>
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4 sm:p-6 lg:p-8" data-testid="control-tower-error">
        <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
          <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-2" />
          <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
          <button
            onClick={handleRefresh}
            className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            {t('app.retry')}
          </button>
        </div>
      </div>
    );
  }

  const overdueCount = summary?.overdueObligations.length ?? 0;
  const dueSoonCount = summary?.dueSoonObligations.length ?? 0;
  const pendingInboxCount = summary?.pendingInboxCount ?? 0;
  const unmatchedCount = summary?.unmatchedPublications.length ?? 0;
  const intakeCount = summary?.newIntakeRequests ?? 0;

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6" data-testid="control-tower-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('control_tower.title')}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {t('control_tower.description')}
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isFetching}
          className={cn(
            'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600',
            'text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700',
            'disabled:opacity-50',
          )}
          data-testid="control-tower-refresh"
        >
          <RefreshCw className={cn('w-4 h-4', isFetching && 'animate-spin')} />
          {t('control_tower.refresh')}
        </button>
      </div>

      {/* Building filter */}
      {summary && summary.buildings.length > 0 && (
        <div className="flex items-center gap-2" data-testid="control-tower-filter">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={buildingFilter}
            onChange={(e) => setBuildingFilter(e.target.value)}
            className={cn(
              'text-sm rounded-lg border border-gray-300 dark:border-gray-600',
              'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100',
              'px-3 py-1.5 focus:ring-2 focus:ring-red-500 focus:border-red-500',
            )}
          >
            <option value="">{t('control_tower.all_buildings')}</option>
            {summary.buildings.map((b) => (
              <option key={b.id} value={b.id}>
                {b.address}, {b.city}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4" data-testid="control-tower-summary">
        <SummaryCard
          testId="card-overdue"
          label={t('control_tower.card_overdue')}
          count={overdueCount}
          icon={AlertTriangle}
          color="red"
        />
        <SummaryCard
          testId="card-due-soon"
          label={t('control_tower.card_due_soon')}
          count={dueSoonCount}
          icon={Clock}
          color="orange"
        />
        <SummaryCard
          testId="card-inbox"
          label={t('control_tower.card_inbox')}
          count={pendingInboxCount}
          icon={Inbox}
          color="blue"
        />
        <SummaryCard
          testId="card-unmatched"
          label={t('control_tower.card_unmatched')}
          count={unmatchedCount}
          icon={FileQuestion}
          color="amber"
        />
        <SummaryCard
          testId="card-intake"
          label={t('control_tower.card_intake')}
          count={intakeCount}
          icon={UserPlus}
          color="purple"
        />
      </div>

      {/* Next Best Actions */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          {t('control_tower.next_best_actions')}
        </h2>
        {actions.length === 0 ? (
          <div
            className="text-center py-12 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700"
            data-testid="control-tower-empty"
          >
            <p className="text-gray-500 dark:text-gray-400">{t('control_tower.no_actions')}</p>
          </div>
        ) : (
          <div className="space-y-3" data-testid="control-tower-actions">
            {actions.map((action) => (
              <ActionRow key={action.id} action={action} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ────────────── Summary Card ────────────── */

const CARD_COLORS: Record<string, { bg: string; text: string; icon: string; border: string }> = {
  red: {
    bg: 'bg-red-50 dark:bg-red-950/30',
    text: 'text-red-700 dark:text-red-300',
    icon: 'text-red-500 dark:text-red-400',
    border: 'border-red-200 dark:border-red-800',
  },
  orange: {
    bg: 'bg-orange-50 dark:bg-orange-950/30',
    text: 'text-orange-700 dark:text-orange-300',
    icon: 'text-orange-500 dark:text-orange-400',
    border: 'border-orange-200 dark:border-orange-800',
  },
  blue: {
    bg: 'bg-blue-50 dark:bg-blue-950/30',
    text: 'text-blue-700 dark:text-blue-300',
    icon: 'text-blue-500 dark:text-blue-400',
    border: 'border-blue-200 dark:border-blue-800',
  },
  amber: {
    bg: 'bg-amber-50 dark:bg-amber-950/30',
    text: 'text-amber-700 dark:text-amber-300',
    icon: 'text-amber-500 dark:text-amber-400',
    border: 'border-amber-200 dark:border-amber-800',
  },
  purple: {
    bg: 'bg-purple-50 dark:bg-purple-950/30',
    text: 'text-purple-700 dark:text-purple-300',
    icon: 'text-purple-500 dark:text-purple-400',
    border: 'border-purple-200 dark:border-purple-800',
  },
};

function SummaryCard({
  testId,
  label,
  count,
  icon: Icon,
  color,
}: {
  testId: string;
  label: string;
  count: number;
  icon: React.ElementType;
  color: string;
}) {
  const c = CARD_COLORS[color] ?? CARD_COLORS.blue;
  return (
    <div
      className={cn('rounded-xl border p-4 flex items-center gap-4', c.bg, c.border)}
      data-testid={testId}
    >
      <div className={cn('p-2 rounded-lg', c.bg)}>
        <Icon className={cn('w-6 h-6', c.icon)} />
      </div>
      <div>
        <p className={cn('text-2xl font-bold', c.text)}>{count}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      </div>
    </div>
  );
}

/* ────────────── Action Row ────────────── */

function ActionRow({ action }: { action: NextBestAction }) {
  const { t } = useTranslation();
  const config = ACTION_TYPE_CONFIG[action.type];
  const Icon = config.icon;

  return (
    <Link
      to={action.link}
      className={cn(
        'flex items-center gap-4 p-4 rounded-lg border transition-all',
        'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800',
        'hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600',
      )}
      data-testid={`action-row-${action.id}`}
    >
      <div className={cn('p-2 rounded-lg', config.bgColor, config.darkBgColor)}>
        <Icon className={cn('w-5 h-5', config.color)} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'inline-block px-2 py-0.5 rounded text-xs font-medium',
              config.bgColor,
              config.darkBgColor,
              config.color,
            )}
            data-testid={`action-type-badge-${action.id}`}
          >
            {t(`control_tower.type_${action.type}`)}
          </span>
        </div>
        <p className="text-sm font-medium text-gray-900 dark:text-white mt-1 truncate">{action.title}</p>
        {action.buildingAddress && (
          <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-0.5">
            <Building2 className="w-3 h-3" />
            {action.buildingAddress}
          </p>
        )}
      </div>
      {action.dueDate && (
        <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap hidden sm:block">
          {formatDate(action.dueDate)}
        </span>
      )}
      <ArrowRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
    </Link>
  );
}
