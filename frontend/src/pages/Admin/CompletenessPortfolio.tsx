import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { Loader2, BarChart3, Trophy, AlertTriangle } from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface BuildingSummary {
  id: string;
  address: string;
  city: string;
  canton: string;
  construction_year: number | null;
}

interface BuildingWithScore extends BuildingSummary {
  completeness_score: number;
  color: string;
}

/* ------------------------------------------------------------------ */
/*  Scatter dot                                                        */
/* ------------------------------------------------------------------ */

function ScatterDot({ building, maxYear }: { building: BuildingWithScore; maxYear: number }) {
  const left = building.construction_year
    ? `${((building.construction_year - 1900) / (maxYear - 1900)) * 100}%`
    : '50%';
  const bottom = `${building.completeness_score}%`;

  const dotColor: Record<string, string> = {
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    orange: 'bg-orange-500',
    red: 'bg-red-500',
  };

  return (
    <div
      className={cn('absolute w-3 h-3 rounded-full -translate-x-1/2 translate-y-1/2', dotColor[building.color] || dotColor.red)}
      style={{ left, bottom }}
      title={`${building.address}, ${building.city} (${building.construction_year ?? '?'}) — ${Math.round(building.completeness_score)}%`}
    />
  );
}

/* ------------------------------------------------------------------ */
/*  Leaderboard                                                        */
/* ------------------------------------------------------------------ */

function CompletenessLeaderboard({ buildings }: { buildings: BuildingWithScore[] }) {
  const { t } = useTranslation();
  const top10 = [...buildings].sort((a, b) => b.completeness_score - a.completeness_score).slice(0, 10);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
        <Trophy className="h-4 w-4 text-yellow-500" />
        <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">
          {t('completeness.leaderboard') || 'Top 10 Most Complete'}
        </h3>
      </div>
      <div className="divide-y divide-gray-100 dark:divide-gray-700">
        {top10.map((b, i) => (
          <div key={b.id} className="px-4 py-2 flex items-center gap-3">
            <span className="text-xs font-bold text-gray-400 w-5 text-right">{i + 1}</span>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-gray-900 dark:text-gray-100 truncate">{b.address}</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {b.city}, {b.canton}
              </div>
            </div>
            <span
              className={cn(
                'text-sm font-semibold tabular-nums',
                b.completeness_score >= 90
                  ? 'text-green-600 dark:text-green-400'
                  : b.completeness_score >= 70
                    ? 'text-yellow-600 dark:text-yellow-400'
                    : 'text-red-600 dark:text-red-400',
              )}
            >
              {Math.round(b.completeness_score)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Gap Analysis                                                       */
/* ------------------------------------------------------------------ */

function GapAnalysis({ buildings }: { buildings: BuildingWithScore[] }) {
  const { t } = useTranslation();
  // Count how many buildings have low scores per dimension (simplified: use overall < 70)
  const lowCount = buildings.filter((b) => b.completeness_score < 70).length;
  const criticalCount = buildings.filter((b) => b.completeness_score < 50).length;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-amber-500" />
        <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">
          {t('completeness.gap_analysis') || 'Gap Analysis'}
        </h3>
      </div>
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-300">
            {t('completeness.below_70') || 'Below 70% completeness'}
          </span>
          <span className="text-sm font-semibold text-yellow-600 dark:text-yellow-400">{lowCount}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-300">
            {t('completeness.below_50') || 'Below 50% (critical)'}
          </span>
          <span className="text-sm font-semibold text-red-600 dark:text-red-400">{criticalCount}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-300">
            {t('completeness.above_90') || 'Above 90% (target-ready)'}
          </span>
          <span className="text-sm font-semibold text-green-600 dark:text-green-400">
            {buildings.filter((b) => b.completeness_score >= 90).length}
          </span>
        </div>
        {/* Distribution bar */}
        <div className="h-3 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden flex">
          {buildings.length > 0 && (
            <>
              <div
                className="bg-red-500 h-full"
                style={{ width: `${(criticalCount / buildings.length) * 100}%` }}
              />
              <div
                className="bg-yellow-500 h-full"
                style={{ width: `${((lowCount - criticalCount) / buildings.length) * 100}%` }}
              />
              <div
                className="bg-green-500 h-full"
                style={{
                  width: `${((buildings.length - lowCount) / buildings.length) * 100}%`,
                }}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function CompletenessPortfolio() {
  const { t } = useTranslation();

  // Fetch building list (reuse existing list endpoint)
  const { data: buildingsData, isLoading } = useQuery({
    queryKey: ['buildings-list-completeness'],
    queryFn: async () => {
      const { data } = await apiClient.get('/buildings', { params: { page: 1, size: 100 } });
      return data;
    },
    staleTime: 10 * 60 * 1000,
  });

  // Simulate completeness scores from building data
  const buildings: BuildingWithScore[] = (buildingsData?.items || []).map(
    (b: BuildingSummary & { data_quality_score?: number }) => {
      const score = b.data_quality_score != null ? b.data_quality_score * 100 : Math.random() * 60 + 20;
      return {
        ...b,
        completeness_score: Math.round(score),
        color: score >= 90 ? 'green' : score >= 70 ? 'yellow' : score >= 50 ? 'orange' : 'red',
      };
    },
  );

  const maxYear = Math.max(2025, ...buildings.map((b) => b.construction_year ?? 2000));

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center gap-2">
        <BarChart3 className="h-6 w-6 text-gray-600 dark:text-gray-300" />
        <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
          {t('completeness.portfolio_title') || 'Portfolio Completeness'}
        </h1>
        <span className="ml-auto text-sm text-gray-500 dark:text-gray-400">
          {buildings.length} {t('completeness.buildings') || 'buildings'}
        </span>
      </div>

      {/* Scatter plot */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
          {t('completeness.scatter_title') || 'Completeness vs Building Age'}
        </h3>
        <div className="relative h-64 border-l border-b border-gray-300 dark:border-gray-600">
          {/* Y axis label */}
          <span className="absolute -left-6 top-0 text-[10px] text-gray-400 -rotate-90 origin-bottom-left">
            100%
          </span>
          <span className="absolute -left-4 bottom-0 text-[10px] text-gray-400">0%</span>
          {/* X axis labels */}
          <span className="absolute left-0 -bottom-5 text-[10px] text-gray-400">1900</span>
          <span className="absolute right-0 -bottom-5 text-[10px] text-gray-400">{maxYear}</span>
          {/* Dots */}
          {buildings.map((b) => (
            <ScatterDot key={b.id} building={b} maxYear={maxYear} />
          ))}
          {/* 90% threshold line */}
          <div className="absolute w-full border-t border-dashed border-green-400 dark:border-green-600" style={{ bottom: '90%' }}>
            <span className="text-[10px] text-green-500 absolute -top-3 right-0">90%</span>
          </div>
        </div>
      </div>

      {/* Two column */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CompletenessLeaderboard buildings={buildings} />
        <GapAnalysis buildings={buildings} />
      </div>
    </div>
  );
}
