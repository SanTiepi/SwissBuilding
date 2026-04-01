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

export function GeoRiskScore({ riskScore }: GeoRiskScoreProps) {
  const { t } = useTranslation();

  return (
    <div className={cn('border rounded-lg p-3 mb-3', scoreBg(riskScore.score))}>
      <div className="flex items-center gap-2 mb-2">
        <ShieldAlert className={cn('w-4 h-4', scoreColor(riskScore.score))} />
        <span className="text-xs font-semibold text-gray-700 dark:text-gray-200">
          {t('geo_context.risk_score') || 'Score de risque geo'}
        </span>
        <span className={cn('text-lg font-bold ml-auto', scoreColor(riskScore.score))}>
          {riskScore.score}/100
        </span>
      </div>
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
  );
}
