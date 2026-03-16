import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { portfolioApi } from '@/api/portfolio';
import { campaignsApi } from '@/api/campaigns';
import { useTranslation } from '@/i18n';
import { AsyncStateWrapper } from '@/components/AsyncStateWrapper';
import { Shield, Target, AlertOctagon, ArrowRight, TrendingUp, ListChecks, GaugeCircle } from 'lucide-react';
import type { PortfolioSummary, Campaign } from '@/types';

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-emerald-500',
  B: 'bg-green-400',
  C: 'bg-yellow-400',
  D: 'bg-orange-400',
  E: 'bg-red-500',
  None: 'bg-gray-300 dark:bg-slate-600',
};

function HealthScoreRing({ score }: { score: number }) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 70 ? '#10b981' : score >= 40 ? '#f59e0b' : '#ef4444';

  return (
    <div className="relative w-24 h-24">
      <svg className="w-24 h-24 -rotate-90" viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          className="text-gray-200 dark:text-slate-700"
        />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xl font-bold text-gray-900 dark:text-white">
        {Math.round(score)}
      </span>
    </div>
  );
}

function ComplianceSection({
  summary,
  t,
  onNonCompliantClick,
}: {
  summary: PortfolioSummary;
  t: (k: string) => string;
  onNonCompliantClick?: () => void;
}) {
  const { compliance } = summary;
  const total =
    compliance.compliant_count +
    compliance.non_compliant_count +
    compliance.partially_compliant_count +
    compliance.unknown_count;
  const pct = total > 0 ? Math.round((compliance.compliant_count / total) * 100) : 0;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-slate-400">{t('portfolio.cc_compliant')}</span>
        <span className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{pct}%</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div
          className={`flex justify-between ${onNonCompliantClick ? 'cursor-pointer hover:opacity-80' : ''}`}
          onClick={onNonCompliantClick}
          role={onNonCompliantClick ? 'button' : undefined}
          tabIndex={onNonCompliantClick ? 0 : undefined}
          onKeyDown={
            onNonCompliantClick
              ? (e) => {
                  if (e.key === 'Enter' || e.key === ' ') onNonCompliantClick();
                }
              : undefined
          }
        >
          <span className="text-gray-500 dark:text-slate-400">{t('portfolio.cc_non_compliant')}</span>
          <span className="font-medium text-red-600 dark:text-red-400">{compliance.non_compliant_count}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500 dark:text-slate-400">{t('portfolio.cc_overdue')}</span>
          <span className="font-medium text-orange-600 dark:text-orange-400">{compliance.total_overdue_deadlines}</span>
        </div>
      </div>
    </div>
  );
}

function GradeDistribution({
  summary,
  onGradeClick,
}: {
  summary: PortfolioSummary;
  onGradeClick?: (grade: string) => void;
}) {
  const grades = summary.grades.by_grade;
  const total = Object.values(grades).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-3">
      <div className="flex gap-1 h-6 rounded-full overflow-hidden bg-gray-100 dark:bg-slate-700">
        {(['A', 'B', 'C', 'D', 'E', 'None'] as const).map((g) => {
          const pct = total > 0 ? (grades[g] / total) * 100 : 0;
          if (pct === 0) return null;
          return (
            <div
              key={g}
              className={`${GRADE_COLORS[g]} h-full transition-all ${onGradeClick && g !== 'None' ? 'cursor-pointer hover:opacity-80' : ''}`}
              style={{ width: `${pct}%` }}
              title={`${g}: ${grades[g]}`}
              onClick={onGradeClick && g !== 'None' ? () => onGradeClick(g) : undefined}
              role={onGradeClick && g !== 'None' ? 'button' : undefined}
              tabIndex={onGradeClick && g !== 'None' ? 0 : undefined}
              onKeyDown={
                onGradeClick && g !== 'None'
                  ? (e) => {
                      if (e.key === 'Enter' || e.key === ' ') onGradeClick(g);
                    }
                  : undefined
              }
            />
          );
        })}
      </div>
      <div className="flex flex-wrap gap-3 text-xs">
        {(['A', 'B', 'C', 'D', 'E'] as const).map((g) => (
          <div
            key={g}
            className={`flex items-center gap-1.5 ${onGradeClick ? 'cursor-pointer hover:opacity-80' : ''}`}
            onClick={onGradeClick ? () => onGradeClick(g) : undefined}
            role={onGradeClick ? 'button' : undefined}
            tabIndex={onGradeClick ? 0 : undefined}
            onKeyDown={
              onGradeClick
                ? (e) => {
                    if (e.key === 'Enter' || e.key === ' ') onGradeClick(g);
                  }
                : undefined
            }
          >
            <span className={`w-2.5 h-2.5 rounded-full ${GRADE_COLORS[g]}`} />
            <span className="text-gray-600 dark:text-slate-300">
              {g}: {grades[g]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ActionsBreakdown({ summary, t }: { summary: PortfolioSummary; t: (k: string) => string }) {
  const { actions } = summary;

  return (
    <div className="grid grid-cols-3 gap-3 text-center">
      <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
        <p className="text-xl font-bold text-amber-700 dark:text-amber-300">{actions.total_open}</p>
        <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{t('portfolio.cc_open')}</p>
      </div>
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <p className="text-xl font-bold text-blue-700 dark:text-blue-300">{actions.total_in_progress}</p>
        <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{t('portfolio.cc_in_progress')}</p>
      </div>
      <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
        <p className="text-xl font-bold text-red-700 dark:text-red-300">{actions.overdue_count}</p>
        <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{t('portfolio.cc_overdue')}</p>
      </div>
    </div>
  );
}

function AlertsBanner({ summary, t }: { summary: PortfolioSummary; t: (k: string) => string }) {
  const { alerts } = summary;
  const items = [
    {
      label: t('portfolio.cc_critical_path'),
      value: alerts.buildings_on_critical_path,
      show: alerts.buildings_on_critical_path > 0,
    },
    {
      label: t('portfolio.cc_blockers'),
      value: alerts.total_constraint_blockers,
      show: alerts.total_constraint_blockers > 0,
    },
    {
      label: t('portfolio.cc_stale'),
      value: alerts.buildings_with_stale_diagnostics,
      show: alerts.buildings_with_stale_diagnostics > 0,
    },
    { label: t('portfolio.cc_weak_signals'), value: alerts.total_weak_signals, show: alerts.total_weak_signals > 0 },
  ].filter((i) => i.show);

  if (items.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span
          key={item.label}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
        >
          <AlertOctagon className="w-3 h-3" />
          {item.value} {item.label}
        </span>
      ))}
    </div>
  );
}

function CampaignProgress({ t }: { t: (k: string) => string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['campaigns', 'active'],
    queryFn: () => campaignsApi.list({ status: 'active', size: 5 }),
  });

  const campaigns = data?.items ?? [];

  return (
    <AsyncStateWrapper
      isLoading={isLoading}
      isError={isError}
      data={campaigns}
      variant="card"
      icon={<Target className="w-5 h-5" />}
      title={t('portfolio.cc_campaigns')}
      emptyMessage={t('portfolio.cc_no_campaigns')}
      className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm"
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Target className="w-5 h-5 text-purple-500" />
          {t('portfolio.cc_campaigns')}
        </h2>
        <Link to="/campaigns" className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1">
          {t('form.view')}
          <ArrowRight className="w-3 h-3" />
        </Link>
      </div>
      <div className="space-y-3">
        {campaigns.slice(0, 4).map((c: Campaign) => {
          const pct = c.target_count > 0 ? Math.round((c.completed_count / c.target_count) * 100) : 0;
          return (
            <div key={c.id}>
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-gray-700 dark:text-slate-200 truncate max-w-[70%]">{c.title}</span>
                <span className="text-gray-500 dark:text-slate-400 font-mono">{pct}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-gray-100 dark:bg-slate-700">
                <div className="h-full rounded-full bg-purple-500 transition-all" style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </AsyncStateWrapper>
  );
}

export function PortfolioCommandCenter({ onDrillDown }: { onDrillDown?: (params: Record<string, string>) => void }) {
  const { t } = useTranslation();

  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
  } = useQuery({
    queryKey: ['portfolio', 'summary'],
    queryFn: portfolioApi.getSummary,
  });

  const {
    data: health,
    isLoading: healthLoading,
    isError: healthError,
  } = useQuery({
    queryKey: ['portfolio', 'health-score'],
    queryFn: portfolioApi.getHealthScore,
  });

  return (
    <div className="space-y-6">
      {/* Row 1: Health Score + Compliance + Grade Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Health Score */}
        <AsyncStateWrapper
          isLoading={healthLoading}
          isError={healthError}
          data={health}
          variant="card"
          icon={<GaugeCircle className="w-5 h-5" />}
          title={t('portfolio.cc_health_score')}
          className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm"
        >
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
            <GaugeCircle className="w-5 h-5 text-blue-500" />
            {t('portfolio.cc_health_score')}
          </h2>
          {health && (
            <div className="flex items-center gap-6">
              <HealthScoreRing score={health.score} />
              <div className="space-y-1.5 text-sm flex-1">
                {Object.entries(health.breakdown).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-gray-500 dark:text-slate-400 capitalize">{t(`portfolio.cc_dim_${key}`)}</span>
                    <span className="font-medium text-gray-900 dark:text-white">{Math.round(val.score)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </AsyncStateWrapper>

        {/* Compliance */}
        <AsyncStateWrapper
          isLoading={summaryLoading}
          isError={summaryError}
          data={summary}
          variant="card"
          icon={<Shield className="w-5 h-5" />}
          title={t('portfolio.cc_compliance')}
          className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm"
        >
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-emerald-500" />
            {t('portfolio.cc_compliance')}
          </h2>
          {summary && (
            <ComplianceSection
              summary={summary}
              t={t}
              onNonCompliantClick={onDrillDown ? () => onDrillDown({ readiness: 'not_ready' }) : undefined}
            />
          )}
        </AsyncStateWrapper>

        {/* Grade Distribution */}
        <AsyncStateWrapper
          isLoading={summaryLoading}
          isError={summaryError}
          data={summary}
          variant="card"
          icon={<TrendingUp className="w-5 h-5" />}
          title={t('portfolio.cc_grades')}
          className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm"
        >
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-indigo-500" />
            {t('portfolio.cc_grades')}
          </h2>
          {summary && (
            <GradeDistribution
              summary={summary}
              onGradeClick={onDrillDown ? (grade) => onDrillDown({ grade }) : undefined}
            />
          )}
        </AsyncStateWrapper>
      </div>

      {/* Row 2: Alerts Banner */}
      {summary && <AlertsBanner summary={summary} t={t} />}

      {/* Row 3: Actions Breakdown + Campaign Progress */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <AsyncStateWrapper
          isLoading={summaryLoading}
          isError={summaryError}
          data={summary}
          variant="card"
          icon={<ListChecks className="w-5 h-5" />}
          title={t('portfolio.cc_actions')}
          className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <ListChecks className="w-5 h-5 text-amber-500" />
              {t('portfolio.cc_actions')}
            </h2>
            <Link to="/actions" className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1">
              {t('form.view')}
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          {summary && <ActionsBreakdown summary={summary} t={t} />}
        </AsyncStateWrapper>

        <CampaignProgress t={t} />
      </div>
    </div>
  );
}
