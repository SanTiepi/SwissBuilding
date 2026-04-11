import { memo } from 'react';
import { RadialBarChart, RadialBar, ResponsiveContainer } from 'recharts';
import type { GeoRiskScore as GeoRiskScoreType } from '@/api/geoContext';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { ShieldAlert } from 'lucide-react';

interface GeoRiskScoreProps {
  riskScore: GeoRiskScoreType;
}

const SUB_DIMENSIONS: { key: keyof Omit<GeoRiskScoreType, 'score'>; maxPts: number }[] = [
  { key: 'inondation', maxPts: 10 },
  { key: 'seismic', maxPts: 10 },
  { key: 'grele', maxPts: 10 },
  { key: 'contamination', maxPts: 10 },
  { key: 'radon', maxPts: 10 },
];

function scoreColor(score: number): string {
  if (score >= 60) return 'text-red-600 dark:text-red-400';
  if (score >= 30) return 'text-orange-500 dark:text-orange-400';
  return 'text-green-600 dark:text-green-400';
}

function scoreFill(score: number): string {
  if (score >= 60) return '#dc2626';
  if (score >= 30) return '#f97316';
  return '#16a34a';
}

function scoreBg(score: number): string {
  if (score >= 60) return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
  if (score >= 30) return 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800';
  return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800';
}

function barColor(value: number, max: number): string {
  const pct = (value / max) * 100;
  if (pct >= 60) return 'bg-red-500';
  if (pct >= 30) return 'bg-orange-400';
  return 'bg-green-500';
}

function interpretationKey(score: number): string {
  if (score >= 60) return 'high_risk';
  if (score >= 30) return 'moderate_risk';
  return 'low_risk';
}

const INTERPRETATION_FALLBACK: Record<string, string> = {
  low_risk: 'Risque faible',
  moderate_risk: 'Risque modere',
  high_risk: 'Risque eleve',
};

export const GeoRiskScore = memo(function GeoRiskScore({ riskScore }: GeoRiskScoreProps) {
  const { t } = useTranslation();
  const fill = scoreFill(riskScore.score);
  const interpKey = interpretationKey(riskScore.score);

  const gaugeData = [{ value: riskScore.score, fill }];

  return (
    <div className={cn('border rounded-lg p-3 mb-3', scoreBg(riskScore.score))}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <ShieldAlert className={cn('w-4 h-4', scoreColor(riskScore.score))} />
        <span className="text-xs font-semibold text-gray-700 dark:text-gray-200">
          {t('geo_context.risk_score') || 'Score de risque geo'}
        </span>
      </div>

      {/* Score gauge + breakdown: horizontal on desktop, stacked on mobile */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        {/* Radial gauge */}
        <div className="relative w-28 h-28 flex-shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <RadialBarChart
              cx="50%"
              cy="50%"
              innerRadius="70%"
              outerRadius="100%"
              startAngle={180}
              endAngle={0}
              data={gaugeData}
              barSize={8}
            >
              <RadialBar dataKey="value" background={{ fill: '#e5e7eb' }} cornerRadius={4} />
            </RadialBarChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={cn('text-2xl font-bold leading-none', scoreColor(riskScore.score))}>
              {riskScore.score}
            </span>
            <span className="text-[10px] text-gray-400 dark:text-gray-500">/100</span>
          </div>
        </div>

        {/* Right side: interpretation + bars */}
        <div className="flex-1 w-full">
          {/* Interpretation text */}
          <p className={cn('text-xs font-semibold mb-2', scoreColor(riskScore.score))}>
            {t(`geo_context.interpretation_${interpKey}`) || INTERPRETATION_FALLBACK[interpKey]}
          </p>

          {/* Sub-dimension bars */}
          <div className="space-y-1.5">
            {SUB_DIMENSIONS.map(({ key, maxPts }) => {
              const val = riskScore[key] ?? 0;
              const pct = Math.min(100, (val / maxPts) * 100);
              return (
                <div key={key} className="flex items-center gap-2">
                  <span className="text-[10px] text-gray-500 dark:text-gray-400 w-24 truncate capitalize">
                    {t(`geo_context.risk_${key}`) || key}
                  </span>
                  <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={cn('h-full rounded-full transition-all', barColor(val, maxPts))}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-gray-500 dark:text-gray-400 w-8 text-right">
                    {val}/{maxPts}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
});
