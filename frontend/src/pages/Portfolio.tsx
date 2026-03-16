import { lazy, Suspense, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { portfolioApi } from '@/api/portfolio';
import { useTranslation } from '@/i18n';
import { RISK_COLORS, POLLUTANT_COLORS } from '@/utils/constants';
import type { RiskLevel, PollutantType, PortfolioSummary } from '@/types';
import { Building2, CheckCircle2, AlertTriangle, Activity, ArrowRight, ShieldCheck, Map, Shield } from 'lucide-react';
import { DashboardSkeleton } from '@/components/Skeleton';
import { PortfolioSignalsFeed } from '@/components/PortfolioSignalsFeed';
import { PortfolioCommandCenter } from '@/components/PortfolioCommandCenter';

const PortfolioRiskMap = lazy(() => import('@/components/PortfolioRiskMap'));
const PortfolioCharts = lazy(() =>
  import('@/components/PortfolioCharts').then((m) => ({ default: m.PortfolioCharts })),
);

function ReadinessDistribution({
  readiness,
  t,
  onSegmentClick,
}: {
  readiness: PortfolioSummary['readiness'];
  t: (key: string) => string;
  onSegmentClick?: (readinessKey: string) => void;
}) {
  const items = [
    { key: 'ready', count: readiness.ready_count, color: 'bg-green-500', label: t('readiness.ready') },
    {
      key: 'partially_ready',
      count: readiness.partially_ready_count,
      color: 'bg-yellow-500',
      label: t('readiness.partially_ready'),
    },
    { key: 'not_ready', count: readiness.not_ready_count, color: 'bg-red-500', label: t('readiness.not_ready') },
    {
      key: 'unknown',
      count: readiness.unknown_count,
      color: 'bg-gray-400 dark:bg-slate-500',
      label: t('readiness.unknown'),
    },
  ];
  const total = items.reduce((acc, i) => acc + i.count, 0);

  return (
    <div className="space-y-3">
      {total > 0 && (
        <div className="w-full h-4 rounded-full overflow-hidden flex bg-gray-100 dark:bg-slate-700">
          {items.map(
            (item) =>
              item.count > 0 && (
                <div
                  key={item.key}
                  className={`${item.color} h-full transition-all ${onSegmentClick ? 'cursor-pointer hover:opacity-80' : ''}`}
                  style={{ width: `${Math.round((item.count / total) * 100)}%` }}
                  title={`${item.label}: ${item.count}`}
                  onClick={onSegmentClick ? () => onSegmentClick(item.key) : undefined}
                  role={onSegmentClick ? 'button' : undefined}
                  tabIndex={onSegmentClick ? 0 : undefined}
                  onKeyDown={
                    onSegmentClick
                      ? (e) => {
                          if (e.key === 'Enter' || e.key === ' ') onSegmentClick(item.key);
                        }
                      : undefined
                  }
                />
              ),
          )}
        </div>
      )}
      <div className="grid grid-cols-2 gap-2">
        {items.map((item) => (
          <div
            key={item.key}
            className={`flex items-center justify-between text-sm ${onSegmentClick ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-slate-700/50 rounded-md px-1 -mx-1 py-0.5' : ''}`}
            onClick={onSegmentClick ? () => onSegmentClick(item.key) : undefined}
            role={onSegmentClick ? 'button' : undefined}
            tabIndex={onSegmentClick ? 0 : undefined}
            onKeyDown={
              onSegmentClick
                ? (e) => {
                    if (e.key === 'Enter' || e.key === ' ') onSegmentClick(item.key);
                  }
                : undefined
            }
          >
            <div className="flex items-center gap-2">
              <span className={`w-3 h-3 rounded-full ${item.color} inline-block`} />
              <span className="text-gray-700 dark:text-slate-300">{item.label}</span>
            </div>
            <span className="font-medium text-gray-900 dark:text-white">{item.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TrustDistributionBar({
  avgTrust,
  t,
  onTierClick,
}: {
  avgTrust: number;
  t: (key: string) => string;
  onTierClick?: (tier: string) => void;
}) {
  const pct = Math.round(avgTrust * 100);
  const barColor = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-amber-500' : 'bg-red-500';
  const tierLabel = pct >= 70 ? t('trust.high') : pct >= 40 ? t('trust.medium') : t('trust.low');
  const tierKey = pct >= 70 ? 'high' : pct >= 40 ? 'medium' : 'low';

  return (
    <div
      className={`space-y-2 ${onTierClick ? 'cursor-pointer hover:opacity-80' : ''}`}
      onClick={onTierClick ? () => onTierClick(tierKey) : undefined}
      role={onTierClick ? 'button' : undefined}
      tabIndex={onTierClick ? 0 : undefined}
      onKeyDown={
        onTierClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') onTierClick(tierKey);
            }
          : undefined
      }
    >
      <div className="w-full h-4 rounded-full bg-gray-100 dark:bg-slate-700 overflow-hidden">
        <div className={`${barColor} h-full rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <div className="flex items-center gap-2 text-sm">
        <span className={`w-3 h-3 rounded-full ${barColor} inline-block`} />
        <span className="text-gray-700 dark:text-slate-300">{tierLabel}</span>
      </div>
    </div>
  );
}

export default function Portfolio() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [showMap, setShowMap] = useState(false);

  const drillDown = (params: Record<string, string>) => {
    const sp = new URLSearchParams(params);
    navigate(`/buildings?${sp.toString()}`);
  };

  const {
    data: metrics,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['portfolio', 'metrics'],
    queryFn: portfolioApi.getMetrics,
  });

  const { data: summary } = useQuery({
    queryKey: ['portfolio', 'summary'],
    queryFn: portfolioApi.getSummary,
  });

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (isError || !metrics) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
      </div>
    );
  }

  const kpis = [
    {
      label: t('portfolio.total_buildings'),
      value: metrics.total_buildings,
      icon: Building2,
      color: 'bg-blue-500',
      onClick: undefined as (() => void) | undefined,
    },
    {
      label: t('portfolio.avg_completeness'),
      value: `${Math.round(metrics.completeness_avg * 100)}%`,
      icon: CheckCircle2,
      color: 'bg-emerald-500',
      onClick: undefined as (() => void) | undefined,
    },
    {
      label: t('portfolio.buildings_ready'),
      value: metrics.buildings_ready,
      icon: CheckCircle2,
      color: 'bg-green-500',
      onClick: () => drillDown({ readiness: 'ready' }),
    },
    {
      label: t('portfolio.critical_actions'),
      value: metrics.actions_critical,
      icon: AlertTriangle,
      color: 'bg-red-500',
      onClick: () => drillDown({ risk: 'critical' }),
    },
  ];

  const riskData = Object.entries(metrics.risk_distribution).map(([level, count]) => ({
    name: t(`risk.${level}`),
    value: count,
    color: RISK_COLORS[level as RiskLevel] || '#94a3b8',
  }));

  const pollutantData = Object.entries(metrics.pollutant_prevalence).map(([pollutant, count]) => ({
    name: t(`pollutant.${pollutant}`),
    count,
    fill: POLLUTANT_COLORS[pollutant as PollutantType] || '#64748b',
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('portfolio.title')}</h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('app.subtitle')}</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className={`bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm ${kpi.onClick ? 'cursor-pointer hover:border-red-300 dark:hover:border-red-700 hover:shadow-md transition-all' : ''}`}
            onClick={kpi.onClick}
            role={kpi.onClick ? 'button' : undefined}
            tabIndex={kpi.onClick ? 0 : undefined}
            onKeyDown={
              kpi.onClick
                ? (e) => {
                    if (e.key === 'Enter' || e.key === ' ') kpi.onClick?.();
                  }
                : undefined
            }
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-slate-400">{kpi.label}</p>
                <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{kpi.value}</p>
              </div>
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${kpi.color}`}>
                <kpi.icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Map Toggle */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setShowMap(!showMap)}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
            showMap
              ? 'bg-red-600 text-white border-red-600 hover:bg-red-700'
              : 'bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-200 border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700'
          }`}
        >
          <Map className="w-4 h-4" />
          {t('portfolio.map_view')}
        </button>
      </div>

      {/* Risk Heatmap */}
      {showMap && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">{t('portfolio.risk_heatmap')}</h2>
          <Suspense
            fallback={
              <div className="h-[500px] flex items-center justify-center">
                <div className="text-center">
                  <div className="w-8 h-8 border-4 border-red-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                  <p className="text-sm text-gray-500 dark:text-slate-400">{t('app.loading')}</p>
                </div>
              </div>
            }
          >
            <PortfolioRiskMap />
          </Suspense>
        </div>
      )}

      {/* Readiness Breakdown */}
      {metrics.total_buildings > 0 &&
        (() => {
          const ready = metrics.buildings_ready;
          const notReady = metrics.buildings_not_ready;
          const notEvaluated = metrics.total_buildings - ready - notReady;
          const total = metrics.total_buildings;
          const readyPct = Math.round((ready / total) * 100);
          const notReadyPct = Math.round((notReady / total) * 100);
          const notEvalPct = 100 - readyPct - notReadyPct;
          return (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
                <ShieldCheck className="w-5 h-5 text-emerald-500" />
                {t('portfolio.readiness_title') || 'Readiness Status'}
              </h2>
              {/* Stacked bar */}
              <div className="w-full h-4 rounded-full overflow-hidden flex bg-gray-100 dark:bg-slate-700">
                {readyPct > 0 && (
                  <div
                    className="bg-emerald-500 h-full transition-all cursor-pointer hover:opacity-80"
                    style={{ width: `${readyPct}%` }}
                    title={`${t('portfolio.buildings_ready') || 'Buildings ready'}: ${ready}`}
                    onClick={() => drillDown({ readiness: 'ready' })}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') drillDown({ readiness: 'ready' });
                    }}
                  />
                )}
                {notReadyPct > 0 && (
                  <div
                    className="bg-red-400 h-full transition-all cursor-pointer hover:opacity-80"
                    style={{ width: `${notReadyPct}%` }}
                    title={`${t('portfolio.buildings_not_ready') || 'Buildings not ready'}: ${notReady}`}
                    onClick={() => drillDown({ readiness: 'not_ready' })}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') drillDown({ readiness: 'not_ready' });
                    }}
                  />
                )}
                {notEvalPct > 0 && (
                  <div
                    className="bg-gray-300 dark:bg-slate-500 h-full transition-all"
                    style={{ width: `${notEvalPct}%` }}
                    title={`${t('portfolio.not_evaluated') || 'Not evaluated'}: ${notEvaluated}`}
                  />
                )}
              </div>
              {/* Legend */}
              <div className="flex flex-wrap gap-4 mt-3 text-sm">
                <div
                  className="flex items-center gap-2 cursor-pointer hover:opacity-80"
                  onClick={() => drillDown({ readiness: 'ready' })}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') drillDown({ readiness: 'ready' });
                  }}
                >
                  <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" />
                  <span className="text-gray-700 dark:text-slate-300">
                    {t('portfolio.buildings_ready') || 'Buildings ready'}: {ready} ({readyPct}%)
                  </span>
                </div>
                <div
                  className="flex items-center gap-2 cursor-pointer hover:opacity-80"
                  onClick={() => drillDown({ readiness: 'not_ready' })}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') drillDown({ readiness: 'not_ready' });
                  }}
                >
                  <span className="w-3 h-3 rounded-full bg-red-400 inline-block" />
                  <span className="text-gray-700 dark:text-slate-300">
                    {t('portfolio.buildings_not_ready') || 'Buildings not ready'}: {notReady} ({notReadyPct}%)
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-gray-300 dark:bg-slate-500 inline-block" />
                  <span className="text-gray-700 dark:text-slate-300">
                    {t('portfolio.not_evaluated') || 'Not evaluated'}: {notEvaluated} ({notEvalPct}%)
                  </span>
                </div>
              </div>
            </div>
          );
        })()}

      {/* Readiness + Trust Distribution */}
      {summary && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Readiness by status */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5 text-blue-500" />
              {t('readiness.distribution')}
            </h2>
            <ReadinessDistribution
              readiness={summary.readiness}
              t={t}
              onSegmentClick={(key) => drillDown({ readiness: key })}
            />
          </div>

          {/* Trust distribution */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
              <ShieldCheck className="w-5 h-5 text-emerald-500" />
              {t('trust.distribution')}
            </h2>
            {summary.overview.avg_trust != null ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500 dark:text-slate-400">{t('portfolio.avg_trust')}</span>
                  <span className="text-lg font-bold text-gray-900 dark:text-white">
                    {Math.round(summary.overview.avg_trust * 100)}%
                  </span>
                </div>
                <TrustDistributionBar
                  avgTrust={summary.overview.avg_trust}
                  t={t}
                  onTierClick={(tier) => drillDown({ trust: tier })}
                />
              </div>
            ) : (
              <p className="text-sm text-gray-500 dark:text-slate-400">{t('trust.unknown')}</p>
            )}
          </div>
        </div>
      )}

      {/* Command Center */}
      <PortfolioCommandCenter onDrillDown={drillDown} />

      {/* Charts */}
      <Suspense
        fallback={
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-[352px] rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 animate-pulse" />
            <div className="h-[352px] rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 animate-pulse" />
          </div>
        }
      >
        <PortfolioCharts riskData={riskData} pollutantData={pollutantData} t={t} />
      </Suspense>

      {/* Recent Activity Summary */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-500" />
            {t('portfolio.recent_diagnostics')}
          </h2>
          <Link to="/actions" className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1">
            {t('form.view')}
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="text-center p-4 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{metrics.recent_diagnostics}</p>
            <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('portfolio.recent_diagnostics')}</p>
          </div>
          <div className="text-center p-4 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{metrics.interventions_in_progress}</p>
            <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('portfolio.interventions_active')}</p>
          </div>
          <div className="text-center p-4 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{metrics.actions_pending}</p>
            <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('portfolio.critical_actions')}</p>
          </div>
        </div>
      </div>

      {/* Portfolio Change Signals */}
      <PortfolioSignalsFeed />
    </div>
  );
}
