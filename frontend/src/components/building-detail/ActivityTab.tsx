import { lazy, Suspense } from 'react';
import { useTranslation } from '@/i18n';
import { formatDate, cn } from '@/utils/formatters';
import type { ActivityItem } from '@/types';
import { Loader2, AlertTriangle, Activity, FileSearch, FileText, Calendar, CheckCircle2 } from 'lucide-react';

const LazyRequalificationTimeline = lazy(() =>
  import('@/components/RequalificationTimeline').then((m) => ({ default: m.RequalificationTimeline })),
);

const ACTIVITY_ICONS: Record<string, React.ElementType> = {
  diagnostic: FileSearch,
  document: FileText,
  event: Calendar,
  action: CheckCircle2,
};

interface ActivityTabProps {
  buildingId: string;
  activity: ActivityItem[];
  activityLoading: boolean;
  activityError: boolean;
}

export function ActivityTab({ buildingId, activity, activityLoading, activityError }: ActivityTabProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200">{t('activity.title')}</h3>
      {activityLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      ) : activityError ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <AlertTriangle className="w-8 h-8 text-red-400 mb-2" />
          <p className="text-sm text-red-600 dark:text-red-400">{t('app.error')}</p>
        </div>
      ) : activity.length > 0 ? (
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-slate-600" />
          <ul className="space-y-4">
            {activity.map((item: ActivityItem) => {
              const IconComponent = ACTIVITY_ICONS[item.kind] || Activity;
              return (
                <li key={item.id} className="relative pl-10">
                  {/* Timeline dot */}
                  <div className="absolute left-2 top-1 w-5 h-5 rounded-full bg-white dark:bg-slate-800 border-2 border-gray-300 dark:border-slate-500 flex items-center justify-center">
                    <IconComponent className="w-3 h-3 text-gray-500 dark:text-slate-400" />
                  </div>
                  <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-medium text-gray-900 dark:text-white">{item.title}</span>
                          <span className="px-1.5 py-0.5 text-xs font-medium bg-gray-100 dark:bg-slate-600 text-gray-600 dark:text-slate-300 rounded">
                            {t(`activity.kind.${item.kind}`) || item.kind}
                          </span>
                          {item.status && (
                            <span
                              className={cn(
                                'px-1.5 py-0.5 text-xs font-medium rounded',
                                item.status === 'validated' || item.status === 'done'
                                  ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                                  : item.status === 'in_progress'
                                    ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                                    : 'bg-gray-100 dark:bg-slate-600 text-gray-600 dark:text-slate-300',
                              )}
                            >
                              {item.status}
                            </span>
                          )}
                        </div>
                        {item.description && (
                          <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{item.description}</p>
                        )}
                      </div>
                      <span className="text-xs text-gray-400 dark:text-slate-500 whitespace-nowrap">
                        {formatDate(item.occurred_at)}
                      </span>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Activity className="w-8 h-8 text-gray-300 dark:text-slate-600 mb-2" />
          <p className="text-sm text-gray-500 dark:text-slate-400">{t('activity.no_activity')}</p>
        </div>
      )}

      {/* Requalification Timeline */}
      <Suspense
        fallback={
          <div className="flex items-center justify-center py-6">
            <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
          </div>
        }
      >
        <LazyRequalificationTimeline buildingId={buildingId} />
      </Suspense>
    </div>
  );
}

export default ActivityTab;
