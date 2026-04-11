import React, { memo } from 'react';
import { cn } from '@/utils/formatters';
import { useTrustScore } from '@/hooks/useTrustScore';
import { AsyncStateWrapper } from '@/components/AsyncStateWrapper';
import { ShieldCheck } from 'lucide-react';
import { useTranslation } from '@/i18n';

interface Props {
  buildingId: string;
}

const getTrustColor = (score: number | undefined) => {
  if (!score) return 'from-gray-100 to-gray-50 border-gray-200 dark:from-gray-800 dark:to-gray-900 dark:border-gray-700';
  if (score < 40) return 'from-red-100 to-red-50 border-red-200 dark:from-red-900/30 dark:to-red-950/20 dark:border-red-800';
  if (score < 70) return 'from-amber-100 to-amber-50 border-amber-200 dark:from-amber-900/30 dark:to-amber-950/20 dark:border-amber-800';
  return 'from-green-100 to-green-50 border-green-200 dark:from-green-900/30 dark:to-green-950/20 dark:border-green-800';
};

const getTrustTextColor = (score: number | undefined) => {
  if (!score) return 'text-gray-700 dark:text-gray-300';
  if (score < 40) return 'text-red-700 dark:text-red-400';
  if (score < 70) return 'text-amber-700 dark:text-amber-400';
  return 'text-green-700 dark:text-green-400';
};

const getTrustStatus = (score: number | undefined) => {
  if (!score) return { icon: '❓', label: 'Données insuffisantes' };
  if (score < 40) return { icon: '❌', label: 'Trust bas — preuves insuffisantes' };
  if (score < 70) return { icon: '⚠️', label: 'Trust modéré — manquent données' };
  return { icon: '✅', label: 'Trust élevé — dossier fiable' };
};

const getBarColor = (ratio: number) => {
  if (ratio > 0.7) return 'bg-green-500';
  if (ratio > 0.4) return 'bg-amber-500';
  return 'bg-red-500';
};

const getSparkBarColor = (value: number) => {
  if (value < 40) return 'bg-red-400';
  if (value < 70) return 'bg-amber-400';
  return 'bg-green-400';
};

export const TrustScorePanel = memo(({ buildingId }: Props) => {
  const { t } = useTranslation();
  const { score, breakdown, history, trend, isLoading, isError } = useTrustScore(buildingId);

  const status = getTrustStatus(score);

  return (
    <AsyncStateWrapper
      isLoading={isLoading}
      isError={isError}
      data={score}
      variant="card"
      title={t('trust_score.title') || 'Dossier Confiance'}
      icon={<ShieldCheck className="w-5 h-5" />}
      emptyMessage={t('trust_score.no_score') || 'Aucun score de confiance disponible'}
    >
      <div className={cn('p-6 rounded-lg border bg-gradient-to-br', getTrustColor(score))}>
        <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
          {t('trust_score.title') || 'Dossier Confiance'}
        </h3>

        {score !== undefined && (
          <>
            <div className={cn('text-5xl font-bold mb-2', getTrustTextColor(score))}>
              {Math.round(score)}
            </div>

            <div className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              {status.icon} {status.label}
            </div>

            {trend && (
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-4 font-semibold">
                {trend === 'improving' && '↑ Amélioration'}
                {trend === 'stable' && '→ Stable'}
                {trend === 'declining' && '↓ En baisse'}
              </div>
            )}

            {breakdown.length > 0 && (
              <div className="space-y-3 mb-4">
                <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Composants du score
                </div>
                {breakdown.map((item) => {
                  const ratio = item.max > 0 ? item.value / item.max : 0;
                  return (
                    <div key={item.key} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-700 dark:text-gray-300">{item.label}</span>
                        <span className="text-gray-900 dark:text-gray-100 font-semibold">
                          {item.value}/{item.max}
                        </span>
                      </div>
                      <div className="w-full bg-gray-300 dark:bg-gray-600 rounded h-1.5">
                        <div
                          className={cn('h-full rounded transition-all', getBarColor(ratio))}
                          style={{ width: `${ratio * 100}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {history.length > 0 && (
              <div className="mt-4">
                <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Évolution (6 derniers mois)
                </div>
                <div className="h-12 bg-white dark:bg-gray-800 rounded p-2 flex items-end gap-1">
                  {history.map((value, idx) => (
                    <div
                      key={idx}
                      className={cn('flex-1 rounded-t transition-all', getSparkBarColor(value))}
                      style={{ height: `${Math.max(20, (value / 100) * 100)}%` }}
                      title={`${Math.round(value)}`}
                    />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </AsyncStateWrapper>
  );
});

TrustScorePanel.displayName = 'TrustScorePanel';
