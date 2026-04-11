/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view (pilot scorecard).
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/store/authStore';
import { apiClient } from '@/api/client';
import { cn } from '@/utils/formatters';
import { Loader2, AlertTriangle, Target, TrendingUp, Award } from 'lucide-react';

// ---- Types ----

interface PilotMetricResult {
  key: string;
  label: string;
  current_value: number;
  target_value: number;
  unit: string;
  description: string;
}

interface PilotScorecardResult {
  org_id: string;
  pilot_score: number;
  grade: string;
  metrics: PilotMetricResult[];
  computed_at: string;
}

// ---- Grade badge ----

const GRADE_COLORS: Record<string, { bg: string; ring: string }> = {
  A: { bg: 'bg-emerald-500', ring: 'ring-emerald-200 dark:ring-emerald-800' },
  B: { bg: 'bg-green-500', ring: 'ring-green-200 dark:ring-green-800' },
  C: { bg: 'bg-yellow-500', ring: 'ring-yellow-200 dark:ring-yellow-800' },
  D: { bg: 'bg-orange-500', ring: 'ring-orange-200 dark:ring-orange-800' },
  E: { bg: 'bg-red-500', ring: 'ring-red-200 dark:ring-red-800' },
  F: { bg: 'bg-red-700', ring: 'ring-red-300 dark:ring-red-900' },
};

function GradeGauge({ grade, score }: { grade: string; score: number }) {
  const g = grade.toUpperCase();
  const colors = GRADE_COLORS[g] || GRADE_COLORS.F;
  // SVG gauge
  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="relative w-40 h-40 mx-auto" data-testid="grade-gauge">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r="45"
          stroke="currentColor"
          strokeWidth="8"
          fill="none"
          className="text-slate-200 dark:text-slate-700"
        />
        <circle
          cx="50"
          cy="50"
          r="45"
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          className={cn(score >= 75 ? 'text-emerald-500' : score >= 50 ? 'text-yellow-500' : 'text-red-500')}
          stroke="currentColor"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1s ease-out' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className={cn(
            'text-3xl font-black text-white w-14 h-14 rounded-xl flex items-center justify-center shadow-lg',
            colors.bg,
          )}
        >
          {g}
        </span>
        <span className="text-sm font-bold text-slate-700 dark:text-slate-300 mt-1">{Math.round(score)}%</span>
      </div>
    </div>
  );
}

// ---- Metric gauge card ----

function MetricCard({ metric }: { metric: PilotMetricResult }) {
  const { t } = useTranslation();
  const progress =
    metric.target_value > 0 ? Math.min(100, Math.round((metric.current_value / metric.target_value) * 100)) : 0;
  const barColor = progress >= 80 ? 'bg-emerald-500' : progress >= 50 ? 'bg-yellow-500' : 'bg-red-500';
  const met = metric.current_value >= metric.target_value;

  return (
    <div
      className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 space-y-3"
      data-testid={`metric-${metric.key}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{metric.label}</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{metric.description}</p>
        </div>
        {met && (
          <span className="text-emerald-500 text-xs font-bold px-2 py-0.5 bg-emerald-50 dark:bg-emerald-900/20 rounded-full">
            {t('pilot_scorecard.target_met') || 'Atteint'}
          </span>
        )}
      </div>

      {/* Values */}
      <div className="flex items-end gap-3">
        <div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{metric.current_value}</p>
          <p className="text-[10px] text-slate-400">{metric.unit}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t('pilot_scorecard.target') || 'Cible'}: {metric.target_value} {metric.unit}
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-[10px] text-slate-400">
          <span>0</span>
          <span>{progress}%</span>
          <span>100</span>
        </div>
        <div className="h-2.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
          <div
            className={cn('h-full rounded-full transition-all duration-1000 ease-out', barColor)}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// ---- Main page ----

export default function PilotScorecard() {
  const { t } = useTranslation();
  useAuth();
  const { user } = useAuthStore();

  const orgId = user?.organization_id;

  const {
    data: scorecard,
    isLoading,
    isError,
  } = useQuery<PilotScorecardResult>({
    queryKey: ['pilot-scorecard-computed', orgId],
    queryFn: async () => {
      const response = await apiClient.get<PilotScorecardResult>(`/organizations/${orgId}/pilot-scorecard`);
      return response.data;
    },
    enabled: !!orgId,
  });

  if (!orgId) {
    return (
      <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto mb-2" />
        <p className="text-amber-700 dark:text-amber-300">
          {t('pilot_scorecard.no_org') || 'Aucune organisation associee.'}
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  if (isError || !scorecard) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
      </div>
    );
  }

  const metsMet = scorecard.metrics.filter((m) => m.current_value >= m.target_value).length;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-red-600 text-white mb-4 shadow-lg">
          <Award className="w-7 h-7" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          {t('pilot_scorecard.title') || 'Scorecard Pilote'}
        </h1>
        <p className="mt-2 text-base text-slate-500 dark:text-slate-400 max-w-xl mx-auto">
          {t('pilot_scorecard.description') || 'Metriques de succes du programme pilote pour votre organisation.'}
        </p>
      </div>

      {/* Overall score */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-8 shadow-sm">
        <div className="flex flex-col sm:flex-row items-center gap-8">
          <GradeGauge grade={scorecard.grade} score={scorecard.pilot_score} />
          <div className="flex-1 space-y-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                {t('pilot_scorecard.overall_score') || 'Score global'}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t('pilot_scorecard.overall_description') || 'Moyenne ponderee de toutes les metriques pilote.'}
              </p>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-3 rounded-xl bg-slate-50 dark:bg-slate-700/50">
                <Target className="w-5 h-5 text-slate-400 mx-auto mb-1" />
                <p className="text-lg font-bold text-slate-900 dark:text-white">{scorecard.metrics.length}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">
                  {t('pilot_scorecard.metrics_count') || 'Metriques'}
                </p>
              </div>
              <div className="text-center p-3 rounded-xl bg-emerald-50 dark:bg-emerald-900/20">
                <TrendingUp className="w-5 h-5 text-emerald-500 mx-auto mb-1" />
                <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{metsMet}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">
                  {t('pilot_scorecard.targets_met') || 'Cibles atteintes'}
                </p>
              </div>
              <div className="text-center p-3 rounded-xl bg-slate-50 dark:bg-slate-700/50">
                <Award className="w-5 h-5 text-slate-400 mx-auto mb-1" />
                <p className="text-lg font-bold text-slate-900 dark:text-white">{scorecard.grade}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">
                  {t('pilot_scorecard.grade_label') || 'Grade'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics grid */}
      <div>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4">
          {t('pilot_scorecard.metrics_detail') || 'Detail des metriques'}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="metrics-grid">
          {scorecard.metrics.map((metric) => (
            <MetricCard key={metric.key} metric={metric} />
          ))}
        </div>
      </div>

      {/* Computed at */}
      <p className="text-xs text-center text-slate-400 dark:text-slate-500">
        {t('pilot_scorecard.computed_at') || 'Calcule le'}: {new Date(scorecard.computed_at).toLocaleString('fr-CH')}
      </p>
    </div>
  );
}
