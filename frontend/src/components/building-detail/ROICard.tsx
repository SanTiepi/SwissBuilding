import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { demoPilotApi } from '@/api/demoPilot';
import { Loader2, Clock, RotateCcw, CalendarOff, Repeat, Info } from 'lucide-react';

interface ROICardProps {
  buildingId: string;
}

const metricIcons: Record<string, React.ElementType> = {
  time_saved_hours: Clock,
  rework_avoided: RotateCcw,
  blocker_days_saved: CalendarOff,
  pack_reuse_count: Repeat,
};

export function ROICard({ buildingId }: ROICardProps) {
  const { t } = useTranslation();

  const {
    data: roi,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['building-roi', buildingId],
    queryFn: () => demoPilotApi.getBuildingROI(buildingId),
    enabled: !!buildingId,
    retry: false,
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-5">
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-6 h-6 animate-spin text-red-600" />
        </div>
      </div>
    );
  }

  if (isError || !roi) {
    return null; // Gracefully hide if ROI data unavailable
  }

  const metrics = [
    {
      key: 'time_saved_hours',
      value: roi.time_saved_hours,
      label: t('roi.time_saved'),
      unit: t('roi.unit_hours'),
    },
    {
      key: 'rework_avoided',
      value: roi.rework_avoided,
      label: t('roi.rework_avoided'),
      unit: t('roi.unit_count'),
    },
    {
      key: 'blocker_days_saved',
      value: roi.blocker_days_saved,
      label: t('roi.blocker_days_saved'),
      unit: t('roi.unit_days'),
    },
    {
      key: 'pack_reuse_count',
      value: roi.pack_reuse_count,
      label: t('roi.pack_reuse'),
      unit: t('roi.unit_count'),
    },
  ];

  return (
    <div
      className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-5"
      data-testid="roi-card"
    >
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">{t('roi.title')}</h3>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {metrics.map((m) => {
          const Icon = metricIcons[m.key] || Clock;
          const source = roi.breakdown.find((b) => b.label === m.key);
          return (
            <div
              key={m.key}
              className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3 text-center"
              data-testid={`roi-metric-${m.key}`}
            >
              <Icon className="w-5 h-5 text-red-600 mx-auto mb-1" />
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {typeof m.value === 'number' ? (m.value % 1 !== 0 ? m.value.toFixed(1) : m.value) : '-'}
              </p>
              <p className="text-xs text-gray-500 dark:text-slate-400">{m.label}</p>
              <p className="text-xs text-gray-400 dark:text-slate-500">{m.unit}</p>
              {source && source.evidence_count > 0 && (
                <p className="text-xs text-blue-500 dark:text-blue-400 mt-1">
                  {source.evidence_count} {t('roi.evidence_events')}
                </p>
              )}
            </div>
          );
        })}
      </div>

      {/* Evidence sources */}
      {roi.evidence_sources.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {roi.evidence_sources.map((src) => (
            <span
              key={src}
              className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-400 rounded"
            >
              {src}
            </span>
          ))}
        </div>
      )}

      {/* Disclaimer */}
      <div className="mt-3 flex items-start gap-1.5 text-xs text-gray-400 dark:text-slate-500">
        <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
        <p>{t('roi.disclaimer')}</p>
      </div>
    </div>
  );
}

export default ROICard;
