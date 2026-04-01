import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { actionQueueApi, type ActionQueueItem, type ActionQueueResponse } from '@/api/actionQueue';
import {
  AlertTriangle,
  Calendar,
  Check,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Clock,
  Inbox,
  Pause,
  Zap,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500',
  high: 'bg-amber-500',
  medium: 'bg-blue-500',
  low: 'bg-slate-400',
};

const URGENCY_BADGE: Record<string, { label: string; cls: string }> = {
  overdue: { label: 'En retard', cls: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' },
  this_week: {
    label: 'Cette semaine',
    cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  },
  this_month: { label: 'Ce mois', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' },
  backlog: { label: 'Backlog', cls: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300' },
};

const SOURCE_LABELS: Record<string, string> = {
  readiness: 'Readiness',
  unknown: 'Inconnue',
  contradiction: 'Contradiction',
  manual: 'Manuelle',
  risk: 'Risque',
  diagnostic: 'Diagnostic',
  document: 'Document',
  compliance: 'Conformite',
  system: 'Systeme',
  simulation: 'Simulation',
};

const EFFORT_LABELS: Record<string, { label: string; cls: string }> = {
  quick: { label: 'Rapide', cls: 'text-green-600 dark:text-green-400' },
  medium: { label: 'Moyen', cls: 'text-amber-600 dark:text-amber-400' },
  heavy: { label: 'Lourd', cls: 'text-red-600 dark:text-red-400' },
};

const TREND_CONFIG = {
  improved: { label: 'Amelioree', icon: TrendingUp, cls: 'text-green-600 dark:text-green-400' },
  stable: { label: 'Stable', icon: Minus, cls: 'text-slate-500 dark:text-slate-400' },
  degraded: { label: 'Degradee', icon: TrendingDown, cls: 'text-red-600 dark:text-red-400' },
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function QueueSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      <div className="flex gap-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-12 flex-1 rounded-lg bg-slate-200 dark:bg-slate-700" />
        ))}
      </div>
      {[...Array(3)].map((_, i) => (
        <div key={i} className="h-16 rounded-lg bg-slate-200 dark:bg-slate-700" />
      ))}
    </div>
  );
}

function SummaryBar({ summary }: { summary: ActionQueueResponse['summary'] }) {
  const items = [
    {
      label: 'En retard',
      value: summary.overdue,
      cls: 'text-red-600 dark:text-red-400',
      bg: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
    },
    {
      label: 'Cette semaine',
      value: summary.this_week,
      cls: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
    },
    {
      label: 'Ce mois',
      value: summary.this_month,
      cls: 'text-blue-600 dark:text-blue-400',
      bg: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    },
    {
      label: 'Backlog',
      value: summary.backlog,
      cls: 'text-slate-600 dark:text-slate-400',
      bg: 'bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600',
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
      {items.map((item) => (
        <div key={item.label} className={cn('rounded-lg border px-3 py-2 text-center', item.bg)}>
          <p className={cn('text-xl font-bold', item.cls)}>{item.value}</p>
          <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
            {item.label}
          </p>
        </div>
      ))}
    </div>
  );
}

function ActionCard({
  item,
  urgency,
  onComplete,
  onSnooze,
  onResolve,
  isCompleting,
}: {
  item: ActionQueueItem;
  urgency: string;
  onComplete: (id: string) => void;
  onSnooze: (id: string) => void;
  onResolve: (item: ActionQueueItem) => void;
  isCompleting: boolean;
}) {
  const effort = EFFORT_LABELS[item.estimated_effort] || EFFORT_LABELS.medium;
  const badge = URGENCY_BADGE[urgency];
  const sourceLabel = SOURCE_LABELS[item.source_type] || item.source_type;

  return (
    <div className="flex items-start gap-3 px-4 py-3 border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
      {/* Priority dot */}
      <div
        className={cn(
          'w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0',
          PRIORITY_COLORS[item.priority] || 'bg-slate-400',
        )}
      />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium text-slate-900 dark:text-white leading-snug">{item.title}</p>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {badge && (
              <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded', badge.cls)}>{badge.label}</span>
            )}
          </div>
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
            {sourceLabel}
          </span>
          <span className={cn('text-[10px] font-medium', effort.cls)}>{effort.label}</span>
          {item.deadline && (
            <span className="text-[10px] text-slate-500 dark:text-slate-400">
              Echeance: {new Date(item.deadline).toLocaleDateString('fr-CH')}
            </span>
          )}
          {item.linked_entity && (
            <span className="text-[10px] text-slate-400 dark:text-slate-500">{item.linked_entity.type}</span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 mt-2">
          <button
            onClick={() => onResolve(item)}
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
          >
            Resoudre
            <ChevronRight className="w-3 h-3" />
          </button>
          <button
            onClick={() => onComplete(item.id)}
            disabled={isCompleting}
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-300 transition-colors disabled:opacity-50"
          >
            <Check className="w-3 h-3" />
            Fait
          </button>
          <button
            onClick={() => onSnooze(item.id)}
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
          >
            <Pause className="w-3 h-3" />
            Reporter
          </button>
        </div>
      </div>
    </div>
  );
}

function UrgencyGroup({
  title,
  icon: Icon,
  items,
  urgency,
  accent,
  onComplete,
  onSnooze,
  onResolve,
  completingId,
}: {
  title: string;
  icon: React.ElementType;
  items: ActionQueueItem[];
  urgency: string;
  accent: string;
  onComplete: (id: string) => void;
  onSnooze: (id: string) => void;
  onResolve: (item: ActionQueueItem) => void;
  completingId: string | null;
}) {
  if (items.length === 0) return null;

  return (
    <div>
      <div className="flex items-center gap-2 px-4 py-2 bg-slate-50 dark:bg-slate-700/30">
        <Icon className={cn('w-3.5 h-3.5', accent)} />
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {title}
        </span>
        <span className="ml-auto text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300">
          {items.length}
        </span>
      </div>
      {items.map((item) => (
        <ActionCard
          key={item.id}
          item={item}
          urgency={urgency}
          onComplete={onComplete}
          onSnooze={onSnooze}
          onResolve={onResolve}
          isCompleting={completingId === item.id}
        />
      ))}
    </div>
  );
}

function WeeklySummaryPanel({ buildingId }: { buildingId: string }) {
  const [expanded, setExpanded] = useState(false);

  const { data } = useQuery({
    queryKey: ['weekly-summary', buildingId],
    queryFn: () => actionQueueApi.getWeeklySummary(buildingId),
    staleTime: 5 * 60 * 1000,
  });

  if (!data) return null;

  const trend = TREND_CONFIG[data.readiness_trend] || TREND_CONFIG.stable;
  const TrendIcon = trend.icon;

  return (
    <div className="border-t border-slate-200 dark:border-slate-700">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">Bilan hebdomadaire</span>
          <span className="text-[10px] text-slate-500 dark:text-slate-400">
            {data.completed_count} completees, {data.created_count} ajoutees
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className={cn('flex items-center gap-1 text-xs font-medium', trend.cls)}>
            <TrendIcon className="w-3.5 h-3.5" />
            {trend.label}
          </div>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          {/* Stats */}
          <div className="grid grid-cols-3 gap-2">
            <div className="text-center p-2 rounded bg-green-50 dark:bg-green-900/20">
              <p className="text-lg font-bold text-green-600 dark:text-green-400">{data.completed_count}</p>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">Completees</p>
            </div>
            <div className="text-center p-2 rounded bg-blue-50 dark:bg-blue-900/20">
              <p className="text-lg font-bold text-blue-600 dark:text-blue-400">{data.created_count}</p>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">Ajoutees</p>
            </div>
            <div className="text-center p-2 rounded bg-slate-50 dark:bg-slate-700/50">
              <p className="text-lg font-bold text-slate-700 dark:text-slate-200">{data.open_count}</p>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">Ouvertes</p>
            </div>
          </div>

          {/* Next week priorities */}
          {data.next_priorities.length > 0 && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                Priorites semaine prochaine
              </p>
              <ul className="space-y-1">
                {data.next_priorities.map((p) => (
                  <li key={p.id} className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
                    <span
                      className={cn(
                        'w-2 h-2 rounded-full flex-shrink-0',
                        PRIORITY_COLORS[p.priority] || 'bg-slate-400',
                      )}
                    />
                    <span className="truncate">{p.title}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Snooze modal (simple inline)
// ---------------------------------------------------------------------------

function SnoozeModal({ onConfirm, onCancel }: { onConfirm: (dateStr: string) => void; onCancel: () => void }) {
  const [selectedDate, setSelectedDate] = useState('');

  const presets = [
    { label: 'Demain', days: 1 },
    { label: 'Dans 3 jours', days: 3 },
    { label: 'Lundi prochain', days: 7 },
    { label: 'Dans 2 semaines', days: 14 },
    { label: 'Dans 1 mois', days: 30 },
  ];

  const addDays = (days: number) => {
    const d = new Date();
    d.setDate(d.getDate() + days);
    return d.toISOString().split('T')[0];
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-600 p-5 w-80 shadow-xl">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">Reporter l'action</h3>
        <div className="space-y-2 mb-3">
          {presets.map((p) => (
            <button
              key={p.days}
              onClick={() => onConfirm(addDays(p.days))}
              className="w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors"
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 mb-3">
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="flex-1 text-sm px-2 py-1.5 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
          />
          <button
            onClick={() => selectedDate && onConfirm(selectedDate)}
            disabled={!selectedDate}
            className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            OK
          </button>
        </div>
        <button
          onClick={onCancel}
          className="w-full text-center text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300 transition-colors"
        >
          Annuler
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface ActionQueueProps {
  buildingId: string;
  onNavigateTab?: (tab: string) => void;
}

export function ActionQueue({ buildingId, onNavigateTab }: ActionQueueProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [completingId, setCompletingId] = useState<string | null>(null);
  const [snoozingId, setSnoozingId] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['action-queue', buildingId],
    queryFn: () => actionQueueApi.getQueue(buildingId),
    staleTime: 30_000,
  });

  const completeMutation = useMutation({
    mutationFn: (actionId: string) => actionQueueApi.complete(actionId),
    onMutate: (actionId) => setCompletingId(actionId),
    onSettled: () => {
      setCompletingId(null);
      queryClient.invalidateQueries({ queryKey: ['action-queue', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['weekly-summary', buildingId] });
    },
  });

  const snoozeMutation = useMutation({
    mutationFn: ({ actionId, date }: { actionId: string; date: string }) => actionQueueApi.snooze(actionId, date),
    onSettled: () => {
      setSnoozingId(null);
      queryClient.invalidateQueries({ queryKey: ['action-queue', buildingId] });
    },
  });

  const handleComplete = (id: string) => completeMutation.mutate(id);

  const handleSnooze = (id: string) => setSnoozingId(id);

  const handleSnoozeConfirm = (dateStr: string) => {
    if (snoozingId) {
      snoozeMutation.mutate({ actionId: snoozingId, date: dateStr });
    }
  };

  /** Navigate to the relevant tab/section based on action source */
  const handleResolve = (item: ActionQueueItem) => {
    if (!onNavigateTab) return;
    const sourceToTab: Record<string, string> = {
      diagnostic: 'diagnostics',
      risk: 'diagnostics',
      document: 'documents',
      compliance: 'details',
      readiness: 'overview',
      unknown: 'overview',
      contradiction: 'overview',
    };
    const tab = sourceToTab[item.source_type] || 'overview';
    onNavigateTab(tab);
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
        <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-700">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-500" />
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white">File d'actions</h2>
          </div>
        </div>
        <div className="p-4">
          <QueueSkeleton />
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <p className="text-sm text-slate-500 dark:text-slate-400">{t('common.error') || 'Erreur lors du chargement'}</p>
      </div>
    );
  }

  const hasActions = data.summary.total > 0;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-500" />
          <h2 className="text-sm font-semibold text-slate-900 dark:text-white">File d'actions</h2>
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
            {data.summary.total}
          </span>
        </div>
      </div>

      {/* Summary bar */}
      <div className="p-3">
        <SummaryBar summary={data.summary} />
      </div>

      {/* Action list */}
      {hasActions ? (
        <div className="max-h-[500px] overflow-y-auto">
          <UrgencyGroup
            title="En retard"
            icon={AlertTriangle}
            items={data.overdue}
            urgency="overdue"
            accent="text-red-500"
            onComplete={handleComplete}
            onSnooze={handleSnooze}
            onResolve={handleResolve}
            completingId={completingId}
          />
          <UrgencyGroup
            title="Cette semaine"
            icon={Clock}
            items={data.this_week}
            urgency="this_week"
            accent="text-amber-500"
            onComplete={handleComplete}
            onSnooze={handleSnooze}
            onResolve={handleResolve}
            completingId={completingId}
          />
          <UrgencyGroup
            title="Ce mois"
            icon={Calendar}
            items={data.this_month}
            urgency="this_month"
            accent="text-blue-500"
            onComplete={handleComplete}
            onSnooze={handleSnooze}
            onResolve={handleResolve}
            completingId={completingId}
          />
          <UrgencyGroup
            title="Backlog"
            icon={Inbox}
            items={data.backlog}
            urgency="backlog"
            accent="text-slate-400"
            onComplete={handleComplete}
            onSnooze={handleSnooze}
            onResolve={handleResolve}
            completingId={completingId}
          />
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-8 text-slate-400 dark:text-slate-500">
          <Check className="w-8 h-8 mb-2" />
          <p className="text-sm">Aucune action en attente</p>
        </div>
      )}

      {/* Weekly summary */}
      <WeeklySummaryPanel buildingId={buildingId} />

      {/* Snooze modal */}
      {snoozingId && <SnoozeModal onConfirm={handleSnoozeConfirm} onCancel={() => setSnoozingId(null)} />}
    </div>
  );
}

export default ActionQueue;
