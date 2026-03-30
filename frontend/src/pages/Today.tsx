import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { todayApi } from '@/api/today';
import type { TodayFeedItem, TodayDeadline, TodayBlocked, TodayExpiring, TodayActivity } from '@/api/today';
import { cn, formatDate } from '@/utils/formatters';
import {
  AlertTriangle,
  Building2,
  Calendar,
  CheckCircle2,
  ShieldAlert,
  Activity,
  Ban,
  FileWarning,
  Zap,
} from 'lucide-react';
import ReviewQueuePanel from '@/components/ReviewQueuePanel';
import InvalidationAlerts from '@/components/InvalidationAlerts';
import { NudgePanel } from '@/components/NudgePanel';
import { AlertDashboard } from '@/components/AlertDashboard';
import { PortfolioIntelligence } from '@/components/PortfolioIntelligence';

// ---------------------------------------------------------------------------
// Priority / deadline badge helpers
// ---------------------------------------------------------------------------

const PRIORITY_BADGE: Record<string, string> = {
  critical: 'bg-red-600 text-white',
  high: 'bg-orange-500 text-white',
  medium: 'bg-blue-500 text-white',
  low: 'bg-slate-400 text-white',
};

function deadlineBadge(deadline: string | null | undefined): { label: string; cls: string } | null {
  if (!deadline) return null;
  const d = new Date(deadline);
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const diff = Math.ceil((d.getTime() - now.getTime()) / 86400000);
  if (diff < 0) return { label: `${Math.abs(diff)}j en retard`, cls: 'bg-red-600 text-white' };
  if (diff === 0) return { label: "Aujourd'hui", cls: 'bg-amber-500 text-white' };
  if (diff <= 7) return { label: `${diff}j`, cls: 'bg-blue-500 text-white' };
  return { label: `${diff}j`, cls: 'bg-slate-500 text-white' };
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function TodaySkeleton() {
  return (
    <div className="animate-pulse space-y-6 p-6">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-slate-200 dark:bg-slate-700" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-64 rounded-xl bg-slate-200 dark:bg-slate-700" />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: number;
  icon: React.ElementType;
  accent?: string;
}) {
  return (
    <div
      className={cn(
        'rounded-xl border p-4 flex flex-col gap-1',
        'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700',
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {label}
        </span>
        <Icon className={cn('w-4 h-4', accent ?? 'text-slate-400')} />
      </div>
      <span className="text-2xl font-bold text-slate-900 dark:text-white">{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section wrapper
// ---------------------------------------------------------------------------

function Section({
  title,
  icon: Icon,
  count,
  children,
  accent,
}: {
  title: string;
  icon: React.ElementType;
  count?: number;
  children: React.ReactNode;
  accent?: string;
}) {
  return (
    <div className="rounded-xl border bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 flex flex-col">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100 dark:border-slate-700">
        <Icon className={cn('w-4 h-4', accent ?? 'text-slate-500')} />
        <h2 className="text-sm font-semibold text-slate-900 dark:text-white">{title}</h2>
        {count !== undefined && (
          <span className="ml-auto text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
            {count}
          </span>
        )}
      </div>
      <div className="flex-1 overflow-y-auto max-h-[420px]">{children}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Item cards
// ---------------------------------------------------------------------------

function UrgentCard({ item, onClick }: { item: TodayFeedItem; onClick: () => void }) {
  const badge = deadlineBadge(item.deadline);
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-4 py-3 border-b border-slate-50 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{item.title}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 truncate">{item.building_name}</p>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {item.priority && (
            <span
              className={cn(
                'text-[10px] font-bold uppercase px-1.5 py-0.5 rounded',
                PRIORITY_BADGE[item.priority] ?? PRIORITY_BADGE.medium,
              )}
            >
              {item.priority}
            </span>
          )}
          {badge && (
            <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded', badge.cls)}>{badge.label}</span>
          )}
        </div>
      </div>
    </button>
  );
}

function DeadlineCard({ item, onClick }: { item: TodayDeadline; onClick: () => void }) {
  const urgency =
    item.days_remaining <= 3
      ? 'text-red-600 dark:text-red-400'
      : item.days_remaining <= 7
        ? 'text-amber-600 dark:text-amber-400'
        : 'text-blue-600 dark:text-blue-400';
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-4 py-3 border-b border-slate-50 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm text-slate-900 dark:text-white truncate">{item.description}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 truncate">{item.building_name}</p>
        </div>
        <span className={cn('text-xs font-semibold whitespace-nowrap', urgency)}>
          {item.days_remaining === 0 ? "Aujourd'hui" : `${item.days_remaining}j`}
        </span>
      </div>
    </button>
  );
}

function BlockedCard({ item, onClick }: { item: TodayBlocked; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-4 py-3 border-b border-slate-50 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors"
    >
      <div className="flex items-start gap-2">
        <Ban className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
        <div className="min-w-0">
          <p className="text-sm text-slate-900 dark:text-white truncate">{item.blocker_description}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 truncate">{item.building_name}</p>
        </div>
      </div>
    </button>
  );
}

function ExpiringCard({ item, onClick }: { item: TodayExpiring; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-4 py-3 border-b border-slate-50 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm text-slate-900 dark:text-white truncate">
            {item.document_type} — {item.building_name}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Expire le {formatDate(item.expiry_date)}</p>
        </div>
        <span
          className={cn(
            'text-xs font-semibold whitespace-nowrap',
            item.days_remaining <= 30 ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400',
          )}
        >
          {item.days_remaining}j
        </span>
      </div>
    </button>
  );
}

function ActivityCard({ item }: { item: TodayActivity }) {
  return (
    <div className="px-4 py-2.5 border-b border-slate-50 dark:border-slate-700/50">
      <div className="flex items-center gap-2">
        <div className="w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-xs text-slate-700 dark:text-slate-300 truncate">
            <span className="font-medium">{item.action}</span>
            {item.building_name !== '—' && (
              <span className="text-slate-500 dark:text-slate-400"> — {item.building_name}</span>
            )}
          </p>
          {item.timestamp && (
            <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">{formatDate(item.timestamp)}</p>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ icon: Icon, message }: { icon: React.ElementType; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-slate-400 dark:text-slate-500">
      <Icon className="w-8 h-8 mb-2" />
      <p className="text-sm">{message}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function Today() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['today-feed'],
    queryFn: todayApi.getFeed,
    refetchInterval: 60_000,
  });

  if (isLoading) return <TodaySkeleton />;

  if (isError || !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-slate-500 dark:text-slate-400">{t('common.error') || 'Erreur lors du chargement'}</p>
      </div>
    );
  }

  const { stats, urgent, this_week, upcoming_deadlines, blocked, expiring_soon, recent_activity } = data;
  const goBuilding = (id: string | null) => id && navigate(`/buildings/${id}`);

  return (
    <div className="space-y-6 p-4 md:p-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{t('today.title') || "Aujourd'hui"}</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          {t('today.subtitle') || 'Vue operationnelle de votre portfolio'}
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard
          label={t('today.stats.total_buildings') || 'Batiments'}
          value={stats.total_buildings}
          icon={Building2}
        />
        <StatCard
          label={t('today.stats.ready') || 'Prets'}
          value={stats.buildings_ready}
          icon={CheckCircle2}
          accent="text-emerald-500"
        />
        <StatCard
          label={t('today.stats.blocked') || 'Bloques'}
          value={stats.buildings_blocked}
          icon={Ban}
          accent="text-red-500"
        />
        <StatCard
          label={t('today.stats.open_actions') || 'Actions ouvertes'}
          value={stats.open_actions}
          icon={Zap}
          accent="text-amber-500"
        />
        <StatCard
          label={t('today.stats.overdue') || 'En retard'}
          value={stats.overdue_actions}
          icon={AlertTriangle}
          accent="text-red-500"
        />
        <StatCard
          label={t('today.stats.expiring') || 'Expirent 90j'}
          value={stats.diagnostics_expiring_90d}
          icon={FileWarning}
          accent="text-orange-500"
        />
      </div>

      {/* Invalidation Alerts */}
      <InvalidationAlerts />

      {/* Nudge Panel — portfolio-level compliance nudges */}
      <NudgePanel context="dashboard" />

      {/* Review Queue */}
      <ReviewQueuePanel />

      {/* Main 3-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Column 1: Urgent actions */}
        <Section
          title={t('today.urgent_title') || 'Actions urgentes'}
          icon={ShieldAlert}
          count={urgent.length + this_week.length}
          accent="text-red-500"
        >
          {urgent.length === 0 && this_week.length === 0 ? (
            <EmptyState icon={CheckCircle2} message={t('today.no_urgent') || 'Aucune action urgente'} />
          ) : (
            <>
              {urgent.map((item, i) => (
                <UrgentCard key={`u-${i}`} item={item} onClick={() => goBuilding(item.building_id ?? null)} />
              ))}
              {this_week.length > 0 && (
                <>
                  <div className="px-4 py-2 bg-slate-50 dark:bg-slate-700/30">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      {t('today.this_week') || 'Cette semaine'}
                    </span>
                  </div>
                  {this_week.map((item, i) => (
                    <UrgentCard key={`w-${i}`} item={item} onClick={() => goBuilding(item.building_id ?? null)} />
                  ))}
                </>
              )}
            </>
          )}
        </Section>

        {/* Column 2: Upcoming deadlines */}
        <Section
          title={t('today.deadlines_title') || 'Echeances a venir'}
          icon={Calendar}
          count={upcoming_deadlines.length}
          accent="text-blue-500"
        >
          {upcoming_deadlines.length === 0 ? (
            <EmptyState icon={Calendar} message={t('today.no_deadlines') || 'Aucune echeance a 30 jours'} />
          ) : (
            upcoming_deadlines.map((item, i) => (
              <DeadlineCard key={i} item={item} onClick={() => goBuilding(item.building_id)} />
            ))
          )}
        </Section>

        {/* Column 3: Recent activity */}
        <Section
          title={t('today.activity_title') || 'Activite recente'}
          icon={Activity}
          count={recent_activity.length}
          accent="text-indigo-500"
        >
          {recent_activity.length === 0 ? (
            <EmptyState icon={Activity} message={t('today.no_activity') || 'Aucune activite recente'} />
          ) : (
            recent_activity.map((item, i) => <ActivityCard key={i} item={item} />)
          )}
        </Section>
      </div>

      {/* Bottom sections: Blocked + Expiring */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Blocked items */}
        <Section
          title={t('today.blocked_title') || 'Elements bloques'}
          icon={Ban}
          count={blocked.length}
          accent="text-red-500"
        >
          {blocked.length === 0 ? (
            <EmptyState icon={CheckCircle2} message={t('today.no_blocked') || 'Rien de bloque'} />
          ) : (
            blocked.map((item, i) => <BlockedCard key={i} item={item} onClick={() => goBuilding(item.building_id)} />)
          )}
        </Section>

        {/* Expiring diagnostics */}
        <Section
          title={t('today.expiring_title') || 'Diagnostics expirant bientot'}
          icon={FileWarning}
          count={expiring_soon.length}
          accent="text-orange-500"
        >
          {expiring_soon.length === 0 ? (
            <EmptyState icon={CheckCircle2} message={t('today.no_expiring') || 'Aucun diagnostic expirant'} />
          ) : (
            expiring_soon.map((item, i) => (
              <ExpiringCard key={i} item={item} onClick={() => goBuilding(item.building_id)} />
            ))
          )}
        </Section>
      </div>

      {/* Alert Dashboard — proactive alerts summary */}
      <AlertDashboard />

      {/* Portfolio Intelligence — cross-layer insights */}
      <PortfolioIntelligence />
    </div>
  );
}
