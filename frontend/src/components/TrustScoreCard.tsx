import { useQuery } from '@tanstack/react-query';
import { trustScoresApi } from '@/api/trustScores';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { ShieldCheck, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { AsyncStateWrapper } from './AsyncStateWrapper';

const TREND_ICON: Record<string, typeof TrendingUp> = {
  improving: TrendingUp,
  stable: Minus,
  declining: TrendingDown,
};

const TREND_COLOR: Record<string, string> = {
  improving: 'text-green-500',
  stable: 'text-gray-400',
  declining: 'text-red-500',
};

const CATEGORY_COLORS: Record<string, string> = {
  proven: 'bg-green-500',
  inferred: 'bg-blue-500',
  declared: 'bg-yellow-500',
  obsolete: 'bg-orange-500',
  contradictory: 'bg-red-500',
};

function TrustScoreContent({ trustScore }: { trustScore: any }) {
  const { t } = useTranslation();
  const pct = Math.round(trustScore.overall_score * 100);
  const TrendIcon = trustScore.trend ? (TREND_ICON[trustScore.trend] ?? Minus) : Minus;
  const trendColor = trustScore.trend ? (TREND_COLOR[trustScore.trend] ?? 'text-gray-400') : 'text-gray-400';

  const categories = [
    { key: 'proven', pct: trustScore.percent_proven, count: trustScore.proven_count },
    { key: 'inferred', pct: trustScore.percent_inferred, count: trustScore.inferred_count },
    { key: 'declared', pct: trustScore.percent_declared, count: trustScore.declared_count },
    { key: 'obsolete', pct: trustScore.percent_obsolete, count: trustScore.obsolete_count },
    { key: 'contradictory', pct: trustScore.percent_contradictory, count: trustScore.contradictory_count },
  ].filter((c) => c.pct != null && c.pct > 0);

  return (
    <>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            {t('trust_score.title') || 'Data Trust'}
          </h3>
        </div>
        <div className="flex items-center gap-1">
          <TrendIcon className={cn('w-4 h-4', trendColor)} />
          <span className="text-2xl font-bold text-gray-900 dark:text-white">{pct}%</span>
        </div>
      </div>

      {/* Stacked bar */}
      <div className="h-3 rounded-full overflow-hidden flex mb-3">
        {categories.map((cat) => (
          <div
            key={cat.key}
            className={cn('h-full', CATEGORY_COLORS[cat.key])}
            style={{ width: `${cat.pct}%` }}
            title={`${t(`trust_score.${cat.key}`) || cat.key}: ${Math.round(cat.pct ?? 0)}%`}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {categories.map((cat) => (
          <div key={cat.key} className="flex items-center gap-1.5 text-xs">
            <span className={cn('w-2 h-2 rounded-full', CATEGORY_COLORS[cat.key])} />
            <span className="text-gray-600 dark:text-slate-300">{t(`trust_score.${cat.key}`) || cat.key}</span>
            <span className="text-gray-400 dark:text-slate-500">{cat.count}</span>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-500 dark:text-slate-400 mt-2">
        {trustScore.total_data_points} {t('trust_score.data_points') || 'data points'}
      </p>
    </>
  );
}

export function TrustScoreCard({ buildingId }: { buildingId: string }) {
  const { t } = useTranslation();
  const {
    data: trustScore,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['building-trust-score', buildingId],
    queryFn: () => trustScoresApi.latest(buildingId),
    enabled: !!buildingId,
  });

  return (
    <AsyncStateWrapper
      isLoading={isLoading}
      isError={isError}
      data={trustScore}
      variant="card"
      title={t('trust_score.title') || 'Data Trust'}
      icon={<ShieldCheck className="w-5 h-5" />}
      emptyMessage={t('trust_score.no_score') || 'No trust score available'}
    >
      {trustScore && <TrustScoreContent trustScore={trustScore} />}
    </AsyncStateWrapper>
  );
}
