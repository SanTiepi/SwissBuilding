import { useQuery } from '@tanstack/react-query';
import { trustScoresApi } from '@/api/trustScores';
import type { BuildingTrustScore } from '@/types';

export interface TrustBreakdownItem {
  label: string;
  value: number;
  max: number;
  key: string;
}

export interface TrustScoreResult {
  score: number | undefined;
  breakdown: TrustBreakdownItem[];
  history: number[];
  trend: string | null;
  isLoading: boolean;
  isError: boolean;
  raw: BuildingTrustScore | null;
}

export function useTrustScore(buildingId: string): TrustScoreResult {
  const {
    data: latest,
    isLoading: latestLoading,
    isError: latestError,
  } = useQuery({
    queryKey: ['building-trust-score', buildingId],
    queryFn: () => trustScoresApi.latest(buildingId),
    enabled: !!buildingId,
  });

  const {
    data: historyData,
    isLoading: historyLoading,
    isError: historyError,
  } = useQuery({
    queryKey: ['building-trust-score-history', buildingId],
    queryFn: () => trustScoresApi.history(buildingId, 6),
    enabled: !!buildingId,
  });

  const score = latest ? Math.round(latest.overall_score * 100) : undefined;

  const breakdown: TrustBreakdownItem[] = latest
    ? [
        {
          label: 'Source fiabilité',
          value: latest.proven_count,
          max: latest.total_data_points,
          key: 'proven',
        },
        {
          label: 'Récence données',
          value: latest.total_data_points - latest.obsolete_count,
          max: latest.total_data_points,
          key: 'recency',
        },
        {
          label: 'Observations terrain',
          value: latest.proven_count + latest.inferred_count,
          max: latest.total_data_points,
          key: 'observations',
        },
        {
          label: 'Contradictions',
          value: latest.total_data_points - latest.contradictory_count,
          max: latest.total_data_points,
          key: 'contradictions',
        },
      ]
    : [];

  const history = historyData ? historyData.map((s) => Math.round(s.overall_score * 100)) : [];

  return {
    score,
    breakdown,
    history,
    trend: latest?.trend ?? null,
    isLoading: latestLoading || historyLoading,
    isError: latestError || historyError,
    raw: latest ?? null,
  };
}
