import { useQuery } from '@tanstack/react-query';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { buildingReportsApi, type RadarAxis } from '@/api/buildingReports';
import { useTranslation } from '@/i18n';
import { Loader2, AlertTriangle, Shield } from 'lucide-react';
import { cn } from '@/utils/formatters';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const GRADE_COLORS: Record<string, { stroke: string; fill: string }> = {
  A: { stroke: '#059669', fill: 'rgba(5, 150, 105, 0.25)' },
  B: { stroke: '#65a30d', fill: 'rgba(101, 163, 13, 0.25)' },
  C: { stroke: '#ca8a04', fill: 'rgba(202, 138, 4, 0.25)' },
  D: { stroke: '#ea580c', fill: 'rgba(234, 88, 12, 0.25)' },
  E: { stroke: '#dc2626', fill: 'rgba(220, 38, 38, 0.25)' },
  F: { stroke: '#7f1d1d', fill: 'rgba(127, 29, 29, 0.25)' },
};

const GRADE_BADGE_COLORS: Record<string, string> = {
  A: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  B: 'bg-lime-100 text-lime-800 dark:bg-lime-900/40 dark:text-lime-300',
  C: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  D: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  E: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  F: 'bg-red-200 text-red-900 dark:bg-red-900/50 dark:text-red-200',
};

const AXIS_I18N_KEYS: Record<string, string> = {
  safe_to_start: 'readiness.safe_to_start',
  safe_to_sell: 'readiness.safe_to_sell',
  safe_to_insure: 'readiness.safe_to_insure',
  safe_to_finance: 'readiness.safe_to_finance',
  safe_to_renovate: 'readiness.safe_to_renovate',
  safe_to_occupy: 'readiness.safe_to_occupy',
  safe_to_transfer: 'readiness.safe_to_transfer',
};

/* ------------------------------------------------------------------ */
/*  Custom tooltip                                                     */
/* ------------------------------------------------------------------ */

interface TooltipPayload {
  payload?: {
    axis: RadarAxis;
    label: string;
    score: number;
  };
}

function RadarTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const item = payload[0]?.payload;
  if (!item) return null;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-lg dark:border-gray-700 dark:bg-gray-800">
      <p className="font-medium text-gray-900 dark:text-gray-100">{item.label}</p>
      <p className="text-sm text-gray-600 dark:text-gray-400">
        Score: <span className="font-semibold">{item.score}/100</span>
      </p>
      <p className="text-sm text-gray-600 dark:text-gray-400">
        Grade:{' '}
        <span className={cn('inline-block rounded px-1.5 py-0.5 text-xs font-bold', GRADE_BADGE_COLORS[item.axis.grade] || '')}>
          {item.axis.grade}
        </span>
      </p>
      {item.axis.blockers.length > 0 && (
        <div className="mt-2 border-t border-gray-200 pt-2 dark:border-gray-600">
          <p className="text-xs font-medium text-red-600 dark:text-red-400">Blockers:</p>
          {item.axis.blockers.map((b, i) => (
            <p key={i} className="text-xs text-red-500 dark:text-red-400">
              - {b}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

interface Props {
  buildingId: string;
}

export default function ReadinessRadarChart({ buildingId }: Props) {
  const { t } = useTranslation();

  const { data, isLoading, error } = useQuery({
    queryKey: ['readiness-radar', buildingId],
    queryFn: () => buildingReportsApi.getReadinessRadar(buildingId),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-gray-200 bg-white p-8 dark:border-gray-700 dark:bg-gray-800">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">{t('app.loading')}</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-red-200 bg-red-50 p-6 dark:border-red-800 dark:bg-red-900/20">
        <AlertTriangle className="h-5 w-5 text-red-500" />
        <span className="ml-2 text-sm text-red-600 dark:text-red-400">{t('app.error')}</span>
      </div>
    );
  }

  const colors = GRADE_COLORS[data.overall_grade] || GRADE_COLORS.F;

  const chartData = data.axes.map((axis) => ({
    label: t(AXIS_I18N_KEYS[axis.name] || axis.name),
    score: axis.score,
    fullMark: 100,
    axis,
  }));

  const totalBlockers = data.axes.reduce((sum, a) => sum + a.blockers.length, 0);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-gray-500 dark:text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{t('readiness.radar_title')}</h3>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={cn(
              'inline-flex items-center rounded-full px-3 py-1 text-sm font-bold',
              GRADE_BADGE_COLORS[data.overall_grade] || ''
            )}
          >
            {data.overall_grade}
          </span>
          <span className="text-sm text-gray-500 dark:text-gray-400">{data.overall_score}/100</span>
        </div>
      </div>

      {/* Radar chart */}
      <ResponsiveContainer width="100%" height={320}>
        <RadarChart data={chartData} cx="50%" cy="50%" outerRadius="75%">
          <PolarGrid stroke="#d1d5db" className="dark:stroke-gray-600" />
          <PolarAngleAxis
            dataKey="label"
            tick={{ fill: '#6b7280', fontSize: 11 }}
            className="dark:fill-gray-400"
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: '#9ca3af', fontSize: 10 }}
            tickCount={5}
          />
          <Tooltip content={<RadarTooltip />} />
          <Radar
            name="Readiness"
            dataKey="score"
            stroke={colors.stroke}
            fill={colors.fill}
            fillOpacity={0.6}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>

      {/* Blocker summary */}
      {totalBlockers > 0 && (
        <div className="mt-3 rounded-md bg-red-50 px-3 py-2 dark:bg-red-900/20">
          <p className="text-xs font-medium text-red-700 dark:text-red-400">
            {totalBlockers} blocker{totalBlockers > 1 ? 's' : ''} across {data.axes.filter((a) => a.blockers.length > 0).length} axes
          </p>
        </div>
      )}
    </div>
  );
}
