import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { buildingReportsApi } from '@/api/buildingReports';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import {
  Calendar,
  Cloud,
  Home,
  Wrench,
  FileText,
  Clock,
  AlertTriangle,
  Loader2,
  Inbox,
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface OpportunityWindow {
  id: string;
  type: 'weather' | 'lease' | 'maintenance' | 'regulatory';
  title: string;
  start_date: string;
  end_date: string;
  days_remaining: number;
  confidence: number;
  risk_of_missing: string;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const TYPE_CONFIG: Record<
  string,
  { icon: typeof Cloud; i18nKey: string; bgColor: string; borderColor: string }
> = {
  weather: {
    icon: Cloud,
    i18nKey: 'opportunity.weather',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    borderColor: 'border-blue-300 dark:border-blue-700',
  },
  lease: {
    icon: Home,
    i18nKey: 'opportunity.lease',
    bgColor: 'bg-purple-50 dark:bg-purple-900/20',
    borderColor: 'border-purple-300 dark:border-purple-700',
  },
  maintenance: {
    icon: Wrench,
    i18nKey: 'opportunity.maintenance',
    bgColor: 'bg-amber-50 dark:bg-amber-900/20',
    borderColor: 'border-amber-300 dark:border-amber-700',
  },
  regulatory: {
    icon: FileText,
    i18nKey: 'opportunity.regulatory',
    bgColor: 'bg-red-50 dark:bg-red-900/20',
    borderColor: 'border-red-300 dark:border-red-700',
  },
};

const URGENCY_COLORS: Record<string, string> = {
  high: 'text-red-600 dark:text-red-400',
  medium: 'text-orange-600 dark:text-orange-400',
  low: 'text-yellow-600 dark:text-yellow-400',
  none: 'text-green-600 dark:text-green-400',
};

const URGENCY_BADGES: Record<string, string> = {
  high: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  medium: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  low: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  none: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function deriveOpportunityWindows(report: {
  interventions: {
    planned: Array<{ title: string; type: string; date_start: string }>;
  };
  compliance: { non_conformities_count: number };
  recommendations: Array<{ priority: string; action: string; source: string }>;
}): OpportunityWindow[] {
  const windows: OpportunityWindow[] = [];
  const now = new Date();

  // Weather windows (spring + autumn)
  const month = now.getMonth(); // 0-indexed
  if (month >= 2 && month <= 4) {
    const endDate = new Date(now.getFullYear(), 5, 30);
    const daysLeft = Math.max(0, Math.ceil((endDate.getTime() - now.getTime()) / 86400000));
    windows.push({
      id: 'weather-spring',
      type: 'weather',
      title: 'Spring construction season',
      start_date: `${now.getFullYear()}-03-01`,
      end_date: `${now.getFullYear()}-06-30`,
      days_remaining: daysLeft,
      confidence: 85,
      risk_of_missing: daysLeft < 30 ? 'high' : daysLeft < 60 ? 'medium' : 'low',
    });
  }
  if (month >= 7 && month <= 9) {
    const endDate = new Date(now.getFullYear(), 10, 15);
    const daysLeft = Math.max(0, Math.ceil((endDate.getTime() - now.getTime()) / 86400000));
    windows.push({
      id: 'weather-autumn',
      type: 'weather',
      title: 'Autumn construction season',
      start_date: `${now.getFullYear()}-08-01`,
      end_date: `${now.getFullYear()}-11-15`,
      days_remaining: daysLeft,
      confidence: 80,
      risk_of_missing: daysLeft < 30 ? 'high' : daysLeft < 60 ? 'medium' : 'low',
    });
  }

  // Planned interventions → maintenance windows
  for (const interv of report.interventions.planned.slice(0, 3)) {
    if (interv.date_start && interv.date_start !== '-') {
      const startDate = new Date(interv.date_start);
      const daysLeft = Math.max(0, Math.ceil((startDate.getTime() - now.getTime()) / 86400000));
      windows.push({
        id: `maint-${interv.title.slice(0, 20)}`,
        type: 'maintenance',
        title: interv.title,
        start_date: interv.date_start,
        end_date: interv.date_start, // same day estimate
        days_remaining: daysLeft,
        confidence: 70,
        risk_of_missing: daysLeft < 14 ? 'high' : daysLeft < 45 ? 'medium' : 'low',
      });
    }
  }

  // Regulatory windows from non-conformities
  if (report.compliance.non_conformities_count > 0) {
    const deadline = new Date(now);
    deadline.setDate(deadline.getDate() + 90);
    windows.push({
      id: 'regulatory-compliance',
      type: 'regulatory',
      title: `${report.compliance.non_conformities_count} non-conformities to resolve`,
      start_date: now.toISOString().slice(0, 10),
      end_date: deadline.toISOString().slice(0, 10),
      days_remaining: 90,
      confidence: 60,
      risk_of_missing: report.compliance.non_conformities_count > 3 ? 'high' : 'medium',
    });
  }

  return windows.sort((a, b) => a.days_remaining - b.days_remaining);
}

/* ------------------------------------------------------------------ */
/*  Window card                                                        */
/* ------------------------------------------------------------------ */

function WindowCard({ window: w, t }: { window: OpportunityWindow; t: (key: string) => string }) {
  const config = TYPE_CONFIG[w.type] || TYPE_CONFIG.maintenance;
  const Icon = config.icon;

  return (
    <div className={cn('flex items-start gap-3 rounded-lg border p-3', config.bgColor, config.borderColor)}>
      <Icon className="mt-0.5 h-5 w-5 flex-shrink-0 text-gray-600 dark:text-gray-400" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">{w.title}</p>
          <span
            className={cn(
              'flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
              URGENCY_BADGES[w.risk_of_missing] || ''
            )}
          >
            {w.risk_of_missing}
          </span>
        </div>
        <div className="mt-1 flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
          <span className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {w.start_date} — {w.end_date}
          </span>
          <span className={cn('flex items-center gap-1 font-medium', URGENCY_COLORS[w.risk_of_missing] || '')}>
            <Clock className="h-3 w-3" />
            {w.days_remaining} {t('opportunity.days_left')}
          </span>
        </div>
        <div className="mt-1 text-xs text-gray-400 dark:text-gray-500">
          Confidence: {w.confidence}%
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

interface Props {
  buildingId: string;
}

export default function OpportunityWindowsPanel({ buildingId }: Props) {
  const { t } = useTranslation();

  const { data: report, isLoading, error } = useQuery({
    queryKey: ['building-report', buildingId],
    queryFn: () => buildingReportsApi.getFullReport(buildingId),
    staleTime: 60_000,
  });

  const windows = useMemo(() => {
    if (!report) return [];
    return deriveOpportunityWindows(report);
  }, [report]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">{t('app.loading')}</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-red-200 bg-red-50 p-6 dark:border-red-800 dark:bg-red-900/20">
        <AlertTriangle className="h-5 w-5 text-red-500" />
        <span className="ml-2 text-sm text-red-600 dark:text-red-400">{t('app.error')}</span>
      </div>
    );
  }

  // Group by type
  const grouped = windows.reduce(
    (acc, w) => {
      (acc[w.type] ||= []).push(w);
      return acc;
    },
    {} as Record<string, OpportunityWindow[]>
  );

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
        <Calendar className="h-5 w-5 text-gray-500 dark:text-gray-400" />
        {t('opportunity.title')}
      </h3>

      {windows.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-gray-400 dark:text-gray-500">
          <Inbox className="mb-2 h-10 w-10" />
          <p className="text-sm">{t('opportunity.empty')}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {Object.entries(grouped).map(([type, typeWindows]) => {
            const config = TYPE_CONFIG[type];
            const i18nKey = config?.i18nKey || type;
            return (
              <div key={type}>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  {t(i18nKey)}
                </p>
                <div className="space-y-2">
                  {typeWindows.map((w) => (
                    <WindowCard key={w.id} window={w} t={t} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
