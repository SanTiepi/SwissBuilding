import { useState, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import {
  AlertTriangle,
  Clock,
  Inbox,
  FileQuestion,
  Shield,
  RefreshCw,
  ArrowRight,
  Building2,
  Filter,
  BellOff,
  User,
  FileText,
  Gavel,
  CalendarClock,
  UserPlus,
} from 'lucide-react';
import { cn, formatDate } from '@/utils/formatters';
import {
  getActionFeed,
  getActionSummary,
  snoozeAction,
  filterSnoozed,
  type ControlTowerAction,
  type ActionPriority,
  type ActionSourceType,
  type ActionFeedFilters,
} from '@/api/controlTower';
import { apiClient } from '@/api/client';

/* ── Priority config ── */

const PRIORITY_CONFIG: Record<ActionPriority, { color: string; bgColor: string; darkBgColor: string; label: string }> =
  {
    P0: {
      color: 'text-red-700 dark:text-red-300',
      bgColor: 'bg-red-100',
      darkBgColor: 'dark:bg-red-950/40',
      label: 'P0',
    },
    P1: {
      color: 'text-orange-700 dark:text-orange-300',
      bgColor: 'bg-orange-100',
      darkBgColor: 'dark:bg-orange-950/40',
      label: 'P1',
    },
    P2: {
      color: 'text-amber-700 dark:text-amber-300',
      bgColor: 'bg-amber-100',
      darkBgColor: 'dark:bg-amber-950/40',
      label: 'P2',
    },
    P3: {
      color: 'text-blue-700 dark:text-blue-300',
      bgColor: 'bg-blue-100',
      darkBgColor: 'dark:bg-blue-950/40',
      label: 'P3',
    },
    P4: {
      color: 'text-gray-600 dark:text-gray-400',
      bgColor: 'bg-gray-100',
      darkBgColor: 'dark:bg-gray-800',
      label: 'P4',
    },
  };

const SOURCE_TYPE_ICONS: Record<ActionSourceType, React.ElementType> = {
  procedural_blocker: Shield,
  authority_request: Gavel,
  obligation: AlertTriangle,
  inbox: Inbox,
  intake: UserPlus,
  publication: FileQuestion,
  deadline: CalendarClock,
};

export default function ControlTower() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [buildingFilter, setBuildingFilter] = useState<string>('');
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [myQueue, setMyQueue] = useState(false);
  const [snoozeTick, setSnoozeTick] = useState(0);

  const filters: ActionFeedFilters = useMemo(
    () => ({
      building_id: buildingFilter || undefined,
      source_type: (sourceFilter as ActionSourceType) || undefined,
      priority: (priorityFilter as ActionPriority) || undefined,
      my_queue: myQueue || undefined,
    }),
    [buildingFilter, sourceFilter, priorityFilter, myQueue],
  );

  const {
    data: summaryData,
    isLoading: summaryLoading,
    isError: summaryError,
  } = useQuery({
    queryKey: ['control-tower-summary'],
    queryFn: getActionSummary,
    staleTime: 60_000,
  });

  const {
    data: rawActions,
    isLoading: actionsLoading,
    isError: actionsError,
    isFetching,
  } = useQuery({
    queryKey: ['control-tower-actions', filters],
    queryFn: () => getActionFeed(filters),
    staleTime: 60_000,
  });

  // Fetch building list for filter dropdown
  const { data: buildingsData } = useQuery({
    queryKey: ['control-tower-buildings'],
    queryFn: async () => {
      const res = await apiClient.get<{ items: { id: string; address: string; city: string }[] }>('/buildings', {
        params: { limit: 200 },
      });
      return res.data.items ?? [];
    },
    staleTime: 300_000,
  });

  // Apply snooze filter client-side
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const actions = useMemo(() => (rawActions ? filterSnoozed(rawActions) : []), [rawActions, snoozeTick]);

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['control-tower-summary'] });
    queryClient.invalidateQueries({ queryKey: ['control-tower-actions'] });
  };

  const handleSnooze = useCallback((actionId: string, days: number) => {
    snoozeAction(actionId, days);
    setSnoozeTick((prev) => prev + 1);
  }, []);

  const isLoading = summaryLoading || actionsLoading;
  const isError = summaryError || actionsError;
  const summary = summaryData;

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

  const buildings = buildingsData ?? [];

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6" data-testid="control-tower-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('control_tower.title')}</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{t('control_tower.description')}</p>
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

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3" data-testid="control-tower-filters">
        <Filter className="w-4 h-4 text-gray-400" />
        {buildings.length > 0 && (
          <select
            value={buildingFilter}
            onChange={(e) => setBuildingFilter(e.target.value)}
            className={cn(
              'text-sm rounded-lg border border-gray-300 dark:border-gray-600',
              'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100',
              'px-3 py-1.5 focus:ring-2 focus:ring-red-500 focus:border-red-500',
            )}
            data-testid="filter-building"
          >
            <option value="">{t('control_tower.all_buildings')}</option>
            {buildings.map((b) => (
              <option key={b.id} value={b.id}>
                {b.address}, {b.city}
              </option>
            ))}
          </select>
        )}
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className={cn(
            'text-sm rounded-lg border border-gray-300 dark:border-gray-600',
            'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100',
            'px-3 py-1.5 focus:ring-2 focus:ring-red-500 focus:border-red-500',
          )}
          data-testid="filter-source"
        >
          <option value="">{t('control_tower.filter_all_sources')}</option>
          <option value="procedural_blocker">{t('control_tower.source_procedural_blocker')}</option>
          <option value="authority_request">{t('control_tower.source_authority_request')}</option>
          <option value="obligation">{t('control_tower.source_obligation')}</option>
          <option value="inbox">{t('control_tower.source_inbox')}</option>
          <option value="intake">{t('control_tower.source_intake')}</option>
          <option value="publication">{t('control_tower.source_publication')}</option>
          <option value="deadline">{t('control_tower.source_deadline')}</option>
        </select>
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          className={cn(
            'text-sm rounded-lg border border-gray-300 dark:border-gray-600',
            'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100',
            'px-3 py-1.5 focus:ring-2 focus:ring-red-500 focus:border-red-500',
          )}
          data-testid="filter-priority"
        >
          <option value="">{t('control_tower.filter_all_priorities')}</option>
          <option value="P0">{t('control_tower.priority_p0')}</option>
          <option value="P1">{t('control_tower.priority_p1')}</option>
          <option value="P2">{t('control_tower.priority_p2')}</option>
          <option value="P3">{t('control_tower.priority_p3')}</option>
          <option value="P4">{t('control_tower.priority_p4')}</option>
        </select>
        <label className="inline-flex items-center gap-1.5 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
          <input
            type="checkbox"
            checked={myQueue}
            onChange={(e) => setMyQueue(e.target.checked)}
            className="rounded border-gray-300 dark:border-gray-600 text-red-600 focus:ring-red-500"
            data-testid="filter-my-queue"
          />
          <User className="w-3.5 h-3.5" />
          {t('control_tower.my_queue')}
        </label>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4" data-testid="control-tower-summary">
        <SummaryCard
          testId="card-p0"
          label={t('control_tower.card_p0')}
          count={summary?.p0_blockers ?? 0}
          icon={Shield}
          color="red"
        />
        <SummaryCard
          testId="card-p1"
          label={t('control_tower.card_p1')}
          count={summary?.p1_authority ?? 0}
          icon={Gavel}
          color="orange"
        />
        <SummaryCard
          testId="card-p2"
          label={t('control_tower.card_p2')}
          count={summary?.p2_overdue ?? 0}
          icon={AlertTriangle}
          color="amber"
        />
        <SummaryCard
          testId="card-p3"
          label={t('control_tower.card_p3')}
          count={summary?.p3_pending ?? 0}
          icon={Inbox}
          color="blue"
        />
        <SummaryCard
          testId="card-p4"
          label={t('control_tower.card_p4')}
          count={summary?.p4_upcoming ?? 0}
          icon={Clock}
          color="gray"
        />
      </div>

      {/* Action feed */}
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
              <ActionRow key={action.id} action={action} onSnooze={handleSnooze} />
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
  amber: {
    bg: 'bg-amber-50 dark:bg-amber-950/30',
    text: 'text-amber-700 dark:text-amber-300',
    icon: 'text-amber-500 dark:text-amber-400',
    border: 'border-amber-200 dark:border-amber-800',
  },
  blue: {
    bg: 'bg-blue-50 dark:bg-blue-950/30',
    text: 'text-blue-700 dark:text-blue-300',
    icon: 'text-blue-500 dark:text-blue-400',
    border: 'border-blue-200 dark:border-blue-800',
  },
  gray: {
    bg: 'bg-gray-50 dark:bg-gray-800/50',
    text: 'text-gray-700 dark:text-gray-300',
    icon: 'text-gray-500 dark:text-gray-400',
    border: 'border-gray-200 dark:border-gray-700',
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
    <div className={cn('rounded-xl border p-4 flex items-center gap-4', c.bg, c.border)} data-testid={testId}>
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

function ActionRow({ action, onSnooze }: { action: ControlTowerAction; onSnooze: (id: string, days: number) => void }) {
  const { t } = useTranslation();
  const [showSnooze, setShowSnooze] = useState(false);
  const pConfig = PRIORITY_CONFIG[action.priority] ?? PRIORITY_CONFIG.P3;
  const SourceIcon = SOURCE_TYPE_ICONS[action.source_type] ?? FileText;

  return (
    <div
      className={cn(
        'flex items-center gap-4 p-4 rounded-lg border transition-all',
        'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800',
        'hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600',
      )}
      data-testid={`action-row-${action.id}`}
    >
      {/* Source icon */}
      <div className={cn('p-2 rounded-lg', pConfig.bgColor, pConfig.darkBgColor)}>
        <SourceIcon className={cn('w-5 h-5', pConfig.color)} />
      </div>

      {/* Content */}
      <Link to={action.link} className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Priority badge */}
          <span
            className={cn(
              'inline-block px-2 py-0.5 rounded text-xs font-bold',
              pConfig.bgColor,
              pConfig.darkBgColor,
              pConfig.color,
            )}
            data-testid={`priority-badge-${action.id}`}
          >
            {t(`control_tower.priority_${String(action.priority || '').toLowerCase()}`)}
          </span>
          {/* Source type */}
          <span className="text-xs text-gray-400 dark:text-gray-500">
            {t(`control_tower.source_${action.source_type}`)}
          </span>
        </div>
        <p className="text-sm font-medium text-gray-900 dark:text-white mt-1 truncate">{action.title}</p>
        {action.description && (
          <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">{action.description}</p>
        )}
        <div className="flex items-center gap-3 mt-1 flex-wrap">
          {action.building_address && (
            <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
              <Building2 className="w-3 h-3" />
              {action.building_address}
            </span>
          )}
          {action.assigned_org && (
            <span className="text-xs text-gray-400 dark:text-gray-500">{action.assigned_org}</span>
          )}
          {action.assigned_user && (
            <span className="text-xs text-gray-400 dark:text-gray-500 flex items-center gap-1">
              <User className="w-3 h-3" />
              {action.assigned_user}
            </span>
          )}
          {action.confidence != null && (
            <span className="text-xs text-gray-400 dark:text-gray-500" data-testid={`confidence-${action.id}`}>
              {Math.round(action.confidence * 100)}%
            </span>
          )}
          {action.freshness && (
            <span className="text-xs text-gray-400 dark:text-gray-500" data-testid={`freshness-${action.id}`}>
              {action.freshness}
            </span>
          )}
        </div>
      </Link>

      {/* Due date */}
      {action.due_date && (
        <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap hidden sm:block">
          {formatDate(action.due_date)}
        </span>
      )}

      {/* Snooze button */}
      <div className="relative">
        <button
          onClick={(e) => {
            e.stopPropagation();
            setShowSnooze(!showSnooze);
          }}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          title={t('control_tower.snooze')}
          data-testid={`snooze-btn-${action.id}`}
        >
          <BellOff className="w-4 h-4" />
        </button>
        {showSnooze && (
          <div
            className="absolute right-0 top-full mt-1 z-10 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1 min-w-[120px]"
            data-testid={`snooze-menu-${action.id}`}
          >
            {[1, 3, 7, 14].map((days) => (
              <button
                key={days}
                onClick={(e) => {
                  e.stopPropagation();
                  onSnooze(action.id, days);
                  setShowSnooze(false);
                }}
                className="block w-full text-left px-3 py-1.5 text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                data-testid={`snooze-${days}d-${action.id}`}
              >
                {days} {t('control_tower.snooze_days')}
              </button>
            ))}
          </div>
        )}
      </div>

      <Link to={action.link}>
        <ArrowRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
      </Link>
    </div>
  );
}
