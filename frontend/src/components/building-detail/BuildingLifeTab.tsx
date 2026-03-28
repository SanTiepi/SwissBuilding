import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { apiClient } from '@/api/client';
import {
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Shield,
  FileText,
  Home,
  Wrench,
  ClipboardList,
  ChevronDown,
  ChevronRight,
  Loader2,
  BarChart3,
  Filter,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CalendarEvent {
  id: string;
  date: string;
  type: string;
  title: string;
  description: string;
  building_id: string;
  source_id: string | null;
  source_type: string;
  status: string;
  days_remaining: number;
  action_required: string | null;
  priority: string;
}

interface CalendarSummary {
  total_events: number;
  overdue: number;
  due_30d: number;
  due_90d: number;
  due_365d: number;
}

interface CalendarData {
  events: CalendarEvent[];
  summary: CalendarSummary;
  by_month: Record<string, CalendarEvent[]>;
}

interface AnnualReview {
  building_id: string;
  year: number;
  evaluated_at: string;
  diagnostics: { valid: number; expiring: number; expired: number };
  interventions_completed: number;
  open_obligations: number;
  overdue_obligations: number;
  insurance_coverage: { active_policies: number; expiring_this_year: number };
  contracts: { active: number; ending_this_year: number };
  recommendations: string[];
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

const buildingLifeApi = {
  getCalendar: async (buildingId: string, horizon = 365): Promise<CalendarData> => {
    const res = await apiClient.get<CalendarData>(`/buildings/${buildingId}/calendar`, {
      params: { horizon },
    });
    return res.data;
  },
  getAnnualReview: async (buildingId: string): Promise<AnnualReview> => {
    const res = await apiClient.get<AnnualReview>(`/buildings/${buildingId}/annual-review`);
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TYPE_CONFIG: Record<string, { icon: typeof Calendar; color: string; label: string }> = {
  obligation: { icon: ClipboardList, color: 'text-blue-600 dark:text-blue-400', label: 'Obligation' },
  insurance: { icon: Shield, color: 'text-purple-600 dark:text-purple-400', label: 'Assurance' },
  contract: { icon: FileText, color: 'text-indigo-600 dark:text-indigo-400', label: 'Contrat' },
  lease: { icon: Home, color: 'text-teal-600 dark:text-teal-400', label: 'Bail' },
  diagnostic_expiry: { icon: AlertTriangle, color: 'text-amber-600 dark:text-amber-400', label: 'Diagnostic' },
  intervention: { icon: Wrench, color: 'text-green-600 dark:text-green-400', label: 'Intervention' },
  form: { icon: FileText, color: 'text-slate-600 dark:text-slate-400', label: 'Formulaire' },
  compliance: { icon: Shield, color: 'text-rose-600 dark:text-rose-400', label: 'Conformite' },
};

const STATUS_STYLES: Record<string, string> = {
  overdue: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 border-red-200 dark:border-red-800',
  due_soon: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border-amber-200 dark:border-amber-800',
  upcoming: 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300 border-blue-200 dark:border-blue-800',
  completed: 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300 border-green-200 dark:border-green-800',
};

const PRIORITY_DOT: Record<string, string> = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-yellow-500',
  low: 'bg-green-500',
};

const MONTH_NAMES_FR = [
  '', 'Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Aout', 'Septembre', 'Octobre', 'Novembre', 'Decembre',
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SummaryCards({ summary }: { summary: CalendarSummary }) {
  const cards = [
    { label: 'En retard', value: summary.overdue, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-900/20' },
    { label: 'Sous 30 jours', value: summary.due_30d, color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-900/20' },
    { label: 'Sous 90 jours', value: summary.due_90d, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-900/20' },
    { label: 'Total actifs', value: summary.due_365d, color: 'text-gray-600 dark:text-gray-400', bg: 'bg-gray-50 dark:bg-slate-700' },
  ];
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {cards.map((c) => (
        <div key={c.label} className={cn('rounded-lg p-3 border border-gray-200 dark:border-slate-700', c.bg)}>
          <p className={cn('text-2xl font-bold', c.color)}>{c.value}</p>
          <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{c.label}</p>
        </div>
      ))}
    </div>
  );
}

function EventRow({ event }: { event: CalendarEvent }) {
  const config = TYPE_CONFIG[event.type] || TYPE_CONFIG.obligation;
  const Icon = config.icon;
  const statusStyle = STATUS_STYLES[event.status] || STATUS_STYLES.upcoming;
  const dotColor = PRIORITY_DOT[event.priority] || PRIORITY_DOT.medium;

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString('fr-CH', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return iso;
    }
  };

  const daysLabel = () => {
    if (event.status === 'completed') return 'Termine';
    if (event.days_remaining < 0) return `${Math.abs(event.days_remaining)}j en retard`;
    if (event.days_remaining === 0) return "Aujourd'hui";
    return `${event.days_remaining}j`;
  };

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-3 rounded-lg border transition-colors',
        event.status === 'overdue'
          ? 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800'
          : 'bg-white dark:bg-slate-800 border-gray-200 dark:border-slate-700 hover:border-gray-300 dark:hover:border-slate-600',
      )}
      data-testid="building-life-event"
    >
      {/* Priority dot */}
      <span className={cn('w-2 h-2 rounded-full flex-shrink-0 mt-2', dotColor)} title={event.priority} />

      {/* Type icon */}
      <Icon className={cn('w-4 h-4 flex-shrink-0 mt-1', config.color)} />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-gray-900 dark:text-white truncate">{event.title}</span>
          <span className={cn('px-1.5 py-0.5 text-[10px] font-medium rounded-full', statusStyle)}>
            {daysLabel()}
          </span>
          <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400">
            {config.label}
          </span>
        </div>
        {event.description && (
          <p className="text-xs text-gray-500 dark:text-slate-400 mt-1 line-clamp-1">{event.description}</p>
        )}
        <div className="flex items-center gap-3 mt-1.5">
          <span className="text-xs text-gray-400 dark:text-slate-500">
            <Calendar className="w-3 h-3 inline mr-1" />
            {formatDate(event.date)}
          </span>
          {event.action_required && (
            <span className="text-xs font-medium text-red-600 dark:text-red-400">
              {event.action_required}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function MonthSection({
  monthKey,
  events,
  defaultOpen,
}: {
  monthKey: string;
  events: CalendarEvent[];
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [year, monthStr] = monthKey.split('-');
  const monthNum = parseInt(monthStr, 10);
  const label = `${MONTH_NAMES_FR[monthNum] || monthStr} ${year}`;
  const overdueCount = events.filter((e) => e.status === 'overdue').length;
  const dueSoonCount = events.filter((e) => e.status === 'due_soon').length;

  return (
    <div className="border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-slate-800 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
      >
        <div className="flex items-center gap-3">
          {open ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )}
          <span className="text-sm font-semibold text-gray-900 dark:text-white">{label}</span>
          <span className="text-xs text-gray-500 dark:text-slate-400">{events.length} evenement(s)</span>
        </div>
        <div className="flex items-center gap-2">
          {overdueCount > 0 && (
            <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400">
              {overdueCount} en retard
            </span>
          )}
          {dueSoonCount > 0 && (
            <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
              {dueSoonCount} imminent(s)
            </span>
          )}
        </div>
      </button>
      {open && (
        <div className="p-3 space-y-2">
          {events.map((ev) => (
            <EventRow key={ev.id} event={ev} />
          ))}
        </div>
      )}
    </div>
  );
}

function AnnualReviewPanel({ buildingId }: { buildingId: string }) {
  const [show, setShow] = useState(false);
  const { data, isLoading, isError } = useQuery<AnnualReview>({
    queryKey: ['annual-review', buildingId],
    queryFn: () => buildingLifeApi.getAnnualReview(buildingId),
    enabled: show,
    retry: false,
    staleTime: 60_000,
  });

  return (
    <div className="border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setShow(!show)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-slate-800 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
      >
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-gray-500 dark:text-slate-400" />
          <span className="text-sm font-semibold text-gray-900 dark:text-white">Revue annuelle {new Date().getFullYear()}</span>
        </div>
        {show ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
      </button>

      {show && (
        <div className="p-4">
          {isLoading && (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
            </div>
          )}
          {isError && (
            <p className="text-sm text-red-600 dark:text-red-400 text-center py-4">Erreur de chargement</p>
          )}
          {data && (
            <div className="space-y-4">
              {/* Stats grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-3">
                  <p className="text-lg font-bold text-gray-900 dark:text-white">{data.diagnostics.valid}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">Diagnostics valides</p>
                  {data.diagnostics.expired > 0 && (
                    <p className="text-xs text-red-600 dark:text-red-400 mt-1">{data.diagnostics.expired} expire(s)</p>
                  )}
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-3">
                  <p className="text-lg font-bold text-gray-900 dark:text-white">{data.interventions_completed}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">Interventions terminees</p>
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-3">
                  <p className={cn('text-lg font-bold', data.overdue_obligations > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-white')}>
                    {data.open_obligations}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">Obligations ouvertes</p>
                  {data.overdue_obligations > 0 && (
                    <p className="text-xs text-red-600 dark:text-red-400 mt-1">{data.overdue_obligations} en retard</p>
                  )}
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-3">
                  <p className="text-lg font-bold text-gray-900 dark:text-white">{data.insurance_coverage.active_policies}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">Polices actives</p>
                  {data.insurance_coverage.expiring_this_year > 0 && (
                    <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">{data.insurance_coverage.expiring_this_year} a renouveler</p>
                  )}
                </div>
              </div>

              {/* Recommendations */}
              {data.recommendations.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Recommandations</h4>
                  <ul className="space-y-1.5">
                    {data.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-slate-300">
                        <CheckCircle2 className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface Props {
  buildingId: string;
}

export default function BuildingLifeTab({ buildingId }: Props) {
  const { t } = useTranslation();
  const [typeFilter, setTypeFilter] = useState<string>('all');

  const {
    data: calendar,
    isLoading,
    isError,
  } = useQuery<CalendarData>({
    queryKey: ['building-life-calendar', buildingId],
    queryFn: () => buildingLifeApi.getCalendar(buildingId, 365),
    enabled: !!buildingId,
    retry: false,
    staleTime: 60_000,
  });

  // Filtered events
  const filteredByMonth = useMemo(() => {
    if (!calendar) return {};
    if (typeFilter === 'all') return calendar.by_month;
    const filtered: Record<string, CalendarEvent[]> = {};
    for (const [month, events] of Object.entries(calendar.by_month)) {
      const f = events.filter((e) => e.type === typeFilter);
      if (f.length > 0) filtered[month] = f;
    }
    return filtered;
  }, [calendar, typeFilter]);

  // Overdue events always pinned at top
  const overdueEvents = useMemo(() => {
    if (!calendar) return [];
    let events = calendar.events.filter((e) => e.status === 'overdue');
    if (typeFilter !== 'all') events = events.filter((e) => e.type === typeFilter);
    return events;
  }, [calendar, typeFilter]);

  // Available types for filter
  const availableTypes = useMemo(() => {
    if (!calendar) return [];
    const types = new Set(calendar.events.map((e) => e.type));
    return Array.from(types).sort();
  }, [calendar]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12" data-testid="building-life-loading">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-12" data-testid="building-life-error">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-sm text-red-600 dark:text-red-400">{t('app.error') || 'Erreur de chargement'}</p>
      </div>
    );
  }

  if (!calendar || calendar.events.length === 0) {
    return (
      <div className="text-center py-12" data-testid="building-life-empty">
        <Calendar className="w-8 h-8 text-gray-300 dark:text-slate-600 mx-auto mb-2" />
        <p className="text-sm text-gray-500 dark:text-slate-400">
          Aucun evenement de cycle de vie pour ce batiment
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="building-life-tab">
      {/* Summary cards */}
      <SummaryCards summary={calendar.summary} />

      {/* Filter */}
      {availableTypes.length > 1 && (
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="text-sm rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-1.5 focus:ring-2 focus:ring-red-500 focus:border-red-500"
            data-testid="building-life-type-filter"
          >
            <option value="all">Tous les types</option>
            {availableTypes.map((t) => (
              <option key={t} value={t}>
                {TYPE_CONFIG[t]?.label || t}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Overdue section — always visible */}
      {overdueEvents.length > 0 && (
        <div data-testid="building-life-overdue-section">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <h3 className="text-base font-semibold text-red-700 dark:text-red-400">
              {overdueEvents.length} echeance(s) en retard
            </h3>
          </div>
          <div className="space-y-2">
            {overdueEvents.map((ev) => (
              <EventRow key={ev.id} event={ev} />
            ))}
          </div>
        </div>
      )}

      {/* Monthly calendar */}
      <div className="space-y-3" data-testid="building-life-months">
        {Object.entries(filteredByMonth).map(([monthKey, events], idx) => {
          // Filter out overdue events already shown above
          const nonOverdue = events.filter((e) => e.status !== 'overdue');
          if (nonOverdue.length === 0) return null;
          return (
            <MonthSection key={monthKey} monthKey={monthKey} events={nonOverdue} defaultOpen={idx < 3} />
          );
        })}
      </div>

      {/* Annual review */}
      <AnnualReviewPanel buildingId={buildingId} />
    </div>
  );
}
