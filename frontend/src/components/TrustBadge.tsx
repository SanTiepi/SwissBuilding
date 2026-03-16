import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface TrustBadgeProps {
  score: number | null;
  trend?: string | null;
  size?: 'sm' | 'md';
}

function getTrustTier(score: number): { color: string; bgColor: string; label: string } {
  if (score >= 70)
    return {
      color: 'text-green-700 dark:text-green-300',
      bgColor: 'bg-green-100 dark:bg-green-900/40',
      label: 'trust.high',
    };
  if (score >= 40)
    return {
      color: 'text-amber-700 dark:text-amber-300',
      bgColor: 'bg-amber-100 dark:bg-amber-900/40',
      label: 'trust.medium',
    };
  return { color: 'text-red-700 dark:text-red-300', bgColor: 'bg-red-100 dark:bg-red-900/40', label: 'trust.low' };
}

const TREND_ICONS: Record<string, typeof TrendingUp> = {
  improving: TrendingUp,
  stable: Minus,
  declining: TrendingDown,
};

export function TrustBadge({ score, trend, size = 'sm' }: TrustBadgeProps) {
  const { t } = useTranslation();

  if (score == null) {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1 rounded-full font-medium',
          'bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400',
          size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
        )}
        title={t('trust.unknown')}
      >
        <span className="w-2 h-2 rounded-full bg-gray-400 dark:bg-slate-500" />
        --
      </span>
    );
  }

  const pct = Math.round(score * 100);
  const tier = getTrustTier(pct);
  const TrendIcon = trend ? TREND_ICONS[trend] : null;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full font-medium',
        tier.bgColor,
        tier.color,
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
      )}
      title={`${t('trust.score')}: ${pct}%`}
    >
      <span
        className={cn(
          'rounded-full flex-shrink-0',
          size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5',
          pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-amber-500' : 'bg-red-500',
        )}
      />
      {pct}%{TrendIcon && <TrendIcon className={cn('flex-shrink-0', size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5')} />}
    </span>
  );
}
