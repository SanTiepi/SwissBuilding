/**
 * MIGRATION: ABSORB INTO PortfolioCommand
 * This page will be absorbed into the PortfolioCommand master workspace.
 * Per ADR-005 and V3 migration plan.
 * New features should target the master workspace directly.
 */
import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/utils/formatters';
import { useAuthStore } from '@/store/authStore';
import {
  intelligenceApi,
  type PortfolioTriageBuilding,
  type PortfolioBenchmarkBuilding,
  type PortfolioCluster,
} from '@/api/intelligence';
import {
  AlertTriangle,
  AlertCircle,
  Eye,
  CheckCircle2,
  MapPin,
  ArrowRight,
  ArrowUp,
  ArrowDown,
  Minus,
  Loader2,
  Filter,
  Building2,
  BarChart3,
  Layers,
} from 'lucide-react';

// --- Status config ---

type TriageStatus = 'critical' | 'action_needed' | 'monitored' | 'under_control';

interface StatusConfig {
  label: string;
  icon: React.ReactNode;
  bgCard: string;
  bgBadge: string;
  textBadge: string;
  ringColor: string;
}

function useStatusConfig(): Record<TriageStatus, StatusConfig> {
  const { t } = useTranslation();
  return {
    critical: {
      label: t('triage.critical') || 'Critique',
      icon: <AlertTriangle className="w-5 h-5" />,
      bgCard: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
      bgBadge: 'bg-red-100 dark:bg-red-900/40',
      textBadge: 'text-red-700 dark:text-red-400',
      ringColor: 'ring-red-500/30',
    },
    action_needed: {
      label: t('triage.action_needed') || 'Action requise',
      icon: <AlertCircle className="w-5 h-5" />,
      bgCard: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800',
      bgBadge: 'bg-orange-100 dark:bg-orange-900/40',
      textBadge: 'text-orange-700 dark:text-orange-400',
      ringColor: 'ring-orange-500/30',
    },
    monitored: {
      label: t('triage.monitored') || 'Surveille',
      icon: <Eye className="w-5 h-5" />,
      bgCard: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
      bgBadge: 'bg-yellow-100 dark:bg-yellow-900/40',
      textBadge: 'text-yellow-700 dark:text-yellow-400',
      ringColor: 'ring-yellow-500/30',
    },
    under_control: {
      label: t('triage.under_control') || 'Sous controle',
      icon: <CheckCircle2 className="w-5 h-5" />,
      bgCard: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
      bgBadge: 'bg-green-100 dark:bg-green-900/40',
      textBadge: 'text-green-700 dark:text-green-400',
      ringColor: 'ring-green-500/30',
    },
  };
}

// --- Grade badge ---

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-emerald-500',
  B: 'bg-green-500',
  C: 'bg-yellow-500',
  D: 'bg-orange-500',
  E: 'bg-red-500',
  F: 'bg-red-700',
};

function MiniGradeBadge({ grade }: { grade: string }) {
  const g = (grade || 'F').toUpperCase();
  return (
    <span
      className={cn(
        'inline-flex items-center justify-center w-7 h-7 rounded-lg text-xs font-black text-white',
        GRADE_COLORS[g] || GRADE_COLORS.F,
      )}
      data-testid="mini-grade-badge"
    >
      {g}
    </span>
  );
}

// --- Threshold color helpers ---

function pctBadgeColor(pct: number): string {
  if (pct >= 80) return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400';
  if (pct >= 60) return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400';
  if (pct >= 40) return 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400';
  return 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400';
}

function blockerBadgeColor(pct: number): string {
  if (pct <= 10) return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400';
  if (pct <= 30) return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400';
  if (pct <= 50) return 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400';
  return 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400';
}

// --- Trend icon ---

function TrendIcon({ trend }: { trend: 'improved' | 'degraded' | 'stable' }) {
  if (trend === 'improved') return <ArrowUp className="w-4 h-4 text-emerald-500" data-testid="trend-up" />;
  if (trend === 'degraded') return <ArrowDown className="w-4 h-4 text-red-500" data-testid="trend-down" />;
  return <Minus className="w-4 h-4 text-slate-400" data-testid="trend-stable" />;
}

// --- Urgency bar ---

function UrgencyBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = pct >= 75 ? 'bg-red-500' : pct >= 50 ? 'bg-orange-500' : pct >= 25 ? 'bg-yellow-500' : 'bg-emerald-500';
  return (
    <div className="w-full h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden" data-testid="urgency-bar">
      <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${pct}%` }} />
    </div>
  );
}

// --- KPI card ---

interface KpiCardProps {
  label: string;
  value: string;
  colorClass: string;
}

function KpiCard({ label, value, colorClass }: KpiCardProps) {
  return (
    <div className="flex flex-col items-center gap-1 p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
      <span
        className={cn('inline-flex items-center justify-center px-2.5 py-1 rounded-lg text-sm font-bold', colorClass)}
      >
        {value}
      </span>
      <span className="text-[11px] text-slate-500 dark:text-slate-400 text-center leading-tight">{label}</span>
    </div>
  );
}

// --- Summary card ---

interface SummaryCardProps {
  config: StatusConfig;
  count: number;
  status: TriageStatus;
  isActive: boolean;
  onClick: () => void;
}

function SummaryCard({ config, count, status, isActive, onClick }: SummaryCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex flex-col items-center gap-1.5 p-4 rounded-xl border transition-all text-center',
        config.bgCard,
        isActive && `ring-2 ${config.ringColor} shadow-md`,
        'hover:shadow-md cursor-pointer',
      )}
      data-testid={`summary-card-${status}`}
    >
      <div className={cn('p-2 rounded-lg', config.bgBadge, config.textBadge)}>{config.icon}</div>
      <p className="text-2xl font-bold text-slate-800 dark:text-slate-200">{count}</p>
      <p className={cn('text-xs font-medium', config.textBadge)}>{config.label}</p>
    </button>
  );
}

// --- Building row (triage) ---

interface BuildingRowProps {
  building: PortfolioTriageBuilding;
  config: StatusConfig;
  trend?: 'improved' | 'degraded' | 'stable';
  onClick: () => void;
}

function BuildingRow({ building, config, trend, onClick }: BuildingRowProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-center gap-4 px-4 py-3.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-all text-left group"
      data-testid="building-row"
    >
      <MiniGradeBadge grade={building.passport_grade} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">{building.address}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span
            className={cn(
              'inline-block px-2 py-0.5 text-[10px] font-semibold rounded-full uppercase',
              config.bgBadge,
              config.textBadge,
            )}
          >
            {config.label}
          </span>
          {building.top_blocker && (
            <span className="text-[11px] text-slate-500 dark:text-slate-400 truncate">{building.top_blocker}</span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {trend && <TrendIcon trend={trend} />}
        <div className="text-right">
          {building.risk_score > 0 && (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Risque: {Math.round(building.risk_score * 100)}%
            </p>
          )}
          {building.next_action && (
            <p className="text-[11px] text-blue-600 dark:text-blue-400 truncate max-w-[180px]">
              {building.next_action}
            </p>
          )}
        </div>
      </div>
      <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300 shrink-0 transition-colors" />
    </button>
  );
}

// --- Benchmark row ---

interface BenchmarkRowProps {
  building: PortfolioBenchmarkBuilding;
  trend?: 'improved' | 'degraded' | 'stable';
  onClick: () => void;
}

function BenchmarkRow({ building, trend, onClick }: BenchmarkRowProps) {
  const { t } = useTranslation();
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex flex-col gap-2 px-4 py-3.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-all text-left group"
      data-testid="benchmark-row"
    >
      <div className="flex items-center gap-3 w-full">
        <MiniGradeBadge grade={building.passport_grade} />
        <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate flex-1">{building.address}</p>
        {trend && <TrendIcon trend={trend} />}
        <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300 shrink-0 transition-colors" />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 w-full">
        <div className="text-[11px]">
          <span className="text-slate-500 dark:text-slate-400">
            {t('portfolio_benchmark.grade_rank') || 'Rang note'}:
          </span>{' '}
          <span className="font-semibold text-slate-700 dark:text-slate-300">#{building.grade_rank}</span>
        </div>
        <div className="text-[11px]">
          <span className="text-slate-500 dark:text-slate-400">
            {t('portfolio_benchmark.trust_percentile') || 'Percentile confiance'}:
          </span>{' '}
          <span className="font-semibold text-slate-700 dark:text-slate-300">
            P{Math.round(building.trust_percentile)}
          </span>
        </div>
        <div className="text-[11px]">
          <span className="text-slate-500 dark:text-slate-400">
            {t('portfolio_benchmark.completeness_percentile') || 'Percentile completude'}:
          </span>{' '}
          <span className="font-semibold text-slate-700 dark:text-slate-300">
            P{Math.round(building.completeness_percentile)}
          </span>
        </div>
        <div className="text-[11px]">
          <span className="text-slate-500 dark:text-slate-400">
            {t('portfolio_benchmark.urgency_score') || 'Score urgence'}:
          </span>{' '}
          <span className="font-semibold text-slate-700 dark:text-slate-300">{Math.round(building.urgency_score)}</span>
        </div>
      </div>
      <UrgencyBar score={building.urgency_score} />
    </button>
  );
}

// --- Cluster card ---

interface ClusterCardProps {
  cluster: PortfolioCluster;
}

function ClusterCard({ cluster }: ClusterCardProps) {
  const { t } = useTranslation();
  return (
    <div
      className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
      data-testid="cluster-card"
    >
      <div className="flex items-center gap-2 mb-3">
        <Layers className="w-4 h-4 text-slate-400" />
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">{cluster.label}</h3>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {t('portfolio_benchmark.building_count') || 'Batiments'}
          </p>
          <p className="text-lg font-bold text-slate-800 dark:text-slate-200">{cluster.building_count}</p>
        </div>
        <div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {t('portfolio_benchmark.dominant_grade') || 'Note dominante'}
          </p>
          <MiniGradeBadge grade={cluster.dominant_grade} />
        </div>
        <div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {t('portfolio_benchmark.avg_trust') || 'Confiance moy.'}
          </p>
          <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">{Math.round(cluster.avg_trust)}%</p>
        </div>
        <div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {t('portfolio_benchmark.avg_completeness') || 'Completude moy.'}
          </p>
          <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            {Math.round(cluster.avg_completeness)}%
          </p>
        </div>
      </div>
    </div>
  );
}

// --- Tab type ---

type ViewTab = 'triage' | 'benchmark' | 'clusters';

const STATUS_ORDER: TriageStatus[] = ['critical', 'action_needed', 'monitored', 'under_control'];

// --- Main page ---

export default function PortfolioTriage() {
  const { t } = useTranslation();
  useAuth();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

  const orgId = user?.organization_id;

  // Triage data (original)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['portfolio-triage', orgId],
    queryFn: () => intelligenceApi.getPortfolioTriage(orgId!),
    enabled: !!orgId,
  });

  // Benchmark data
  const { data: benchmarkData, isLoading: benchmarkLoading } = useQuery({
    queryKey: ['portfolio-benchmark', orgId],
    queryFn: () => intelligenceApi.getPortfolioBenchmark(orgId!),
    enabled: !!orgId,
  });

  // Trends data
  const { data: trendsData } = useQuery({
    queryKey: ['portfolio-trends', orgId],
    queryFn: () => intelligenceApi.getPortfolioTrends(orgId!),
    enabled: !!orgId,
  });

  const statusConfig = useStatusConfig();
  const [filter, setFilter] = useState<TriageStatus | 'all'>('all');
  const [activeTab, setActiveTab] = useState<ViewTab>('triage');

  // Build trend lookup map
  const trendMap = useMemo(() => {
    const map = new Map<string, 'improved' | 'degraded' | 'stable'>();
    if (trendsData?.buildings) {
      for (const b of trendsData.buildings) {
        map.set(b.id, b.trend);
      }
    }
    return map;
  }, [trendsData]);

  const filteredBuildings = useMemo(() => {
    if (!data) return [];
    if (filter === 'all') return data.buildings;
    return data.buildings.filter((b) => b.status === filter);
  }, [data, filter]);

  const sortedBuildings = useMemo(() => {
    return [...filteredBuildings].sort((a, b) => {
      const ai = STATUS_ORDER.indexOf(a.status as TriageStatus);
      const bi = STATUS_ORDER.indexOf(b.status as TriageStatus);
      if (ai !== bi) return ai - bi;
      return b.risk_score - a.risk_score;
    });
  }, [filteredBuildings]);

  // Benchmark buildings sorted by urgency (worst first)
  const sortedBenchmarkBuildings = useMemo(() => {
    if (!benchmarkData?.buildings) return [];
    return [...benchmarkData.buildings].sort((a, b) => b.urgency_score - a.urgency_score);
  }, [benchmarkData]);

  if (!orgId) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-slate-500 dark:text-slate-400 text-sm">
          {t('triage.no_org') || 'Aucune organisation associee'}
        </p>
      </div>
    );
  }

  const tabs: { key: ViewTab; label: string; icon: React.ReactNode }[] = [
    {
      key: 'triage',
      label: t('portfolio_benchmark.tab_triage') || 'Triage',
      icon: <AlertTriangle className="w-4 h-4" />,
    },
    {
      key: 'benchmark',
      label: t('portfolio_benchmark.tab_benchmark') || 'Benchmark',
      icon: <BarChart3 className="w-4 h-4" />,
    },
    {
      key: 'clusters',
      label: t('portfolio_benchmark.tab_clusters') || 'Clusters',
      icon: <Layers className="w-4 h-4" />,
    },
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2.5 rounded-xl bg-red-600 text-white shadow-lg">
          <Building2 className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white" data-testid="triage-title">
            {t('triage.title') || 'Triage du portefeuille'}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t('triage.subtitle') || 'Vue evidence de vos immeubles par urgence'}
          </p>
        </div>
      </div>

      {/* KPIs bar */}
      {benchmarkData && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-6" data-testid="portfolio-kpis">
          <KpiCard
            label={t('portfolio_benchmark.avg_grade') || 'Note moyenne'}
            value={benchmarkData.avg_grade}
            colorClass={cn(
              'text-white',
              GRADE_COLORS[(benchmarkData.avg_grade || 'F').toUpperCase()] || GRADE_COLORS.F,
            )}
          />
          <KpiCard
            label={t('portfolio_benchmark.avg_trust') || 'Confiance moy.'}
            value={`${Math.round(benchmarkData.avg_trust_pct)}%`}
            colorClass={pctBadgeColor(benchmarkData.avg_trust_pct)}
          />
          <KpiCard
            label={t('portfolio_benchmark.avg_completeness') || 'Completude moy.'}
            value={`${Math.round(benchmarkData.avg_completeness_pct)}%`}
            colorClass={pctBadgeColor(benchmarkData.avg_completeness_pct)}
          />
          <KpiCard
            label={t('portfolio_benchmark.buildings_with_blockers') || 'Avec bloquants'}
            value={`${Math.round(benchmarkData.buildings_with_blockers_pct)}%`}
            colorClass={blockerBadgeColor(benchmarkData.buildings_with_blockers_pct)}
          />
          <KpiCard
            label={t('portfolio_benchmark.proof_coverage') || 'Couverture preuves'}
            value={`${Math.round(benchmarkData.proof_coverage_pct)}%`}
            colorClass={pctBadgeColor(benchmarkData.proof_coverage_pct)}
          />
        </div>
      )}

      {/* Trend summary */}
      {trendsData && (
        <div
          className="flex flex-wrap items-center gap-4 mb-6 p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
          data-testid="trend-summary"
        >
          <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">
            {t('portfolio_benchmark.trend_summary') || 'Tendance du portefeuille'}
          </span>
          <div className="flex items-center gap-1">
            <ArrowUp className="w-3.5 h-3.5 text-emerald-500" />
            <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
              {trendsData.improved_count} {t('portfolio_benchmark.trend_improved') || 'Ameliore'}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <ArrowDown className="w-3.5 h-3.5 text-red-500" />
            <span className="text-xs text-red-600 dark:text-red-400 font-medium">
              {trendsData.degraded_count} {t('portfolio_benchmark.trend_degraded') || 'Degrade'}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <Minus className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
              {trendsData.stable_count} {t('portfolio_benchmark.trend_stable') || 'Stable'}
            </span>
          </div>
        </div>
      )}

      {/* Tab switcher */}
      <div className="flex gap-1 mb-6 p-1 rounded-xl bg-slate-100 dark:bg-slate-800" data-testid="view-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              'flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all flex-1 justify-center',
              activeTab === tab.key
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300',
            )}
            data-testid={`tab-${tab.key}`}
          >
            {tab.icon}
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Loading */}
      {(isLoading || (activeTab === 'benchmark' && benchmarkLoading)) && (
        <div className="flex items-center justify-center py-20" data-testid="triage-loading">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div
          className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm"
          data-testid="triage-error"
        >
          {t('triage.error') || 'Erreur lors du chargement du triage'}
        </div>
      )}

      {/* === TRIAGE TAB === */}
      {activeTab === 'triage' && data && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8" data-testid="summary-cards">
            <SummaryCard
              config={statusConfig.critical}
              count={data.critical_count}
              status="critical"
              isActive={filter === 'critical'}
              onClick={() => setFilter(filter === 'critical' ? 'all' : 'critical')}
            />
            <SummaryCard
              config={statusConfig.action_needed}
              count={data.action_needed_count}
              status="action_needed"
              isActive={filter === 'action_needed'}
              onClick={() => setFilter(filter === 'action_needed' ? 'all' : 'action_needed')}
            />
            <SummaryCard
              config={statusConfig.monitored}
              count={data.monitored_count}
              status="monitored"
              isActive={filter === 'monitored'}
              onClick={() => setFilter(filter === 'monitored' ? 'all' : 'monitored')}
            />
            <SummaryCard
              config={statusConfig.under_control}
              count={data.under_control_count}
              status="under_control"
              isActive={filter === 'under_control'}
              onClick={() => setFilter(filter === 'under_control' ? 'all' : 'under_control')}
            />
          </div>

          {/* Filter indicator */}
          {filter !== 'all' && (
            <div className="flex items-center gap-2 mb-4">
              <Filter className="w-4 h-4 text-slate-400" />
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {t('triage.filtering') || 'Filtre'}: {statusConfig[filter].label}
              </span>
              <button
                type="button"
                onClick={() => setFilter('all')}
                className="text-xs text-red-600 hover:text-red-700 dark:text-red-400 underline"
                data-testid="clear-filter"
              >
                {t('triage.clear_filter') || 'Effacer'}
              </button>
            </div>
          )}

          {/* Building list */}
          <div className="space-y-2" data-testid="building-list">
            {sortedBuildings.length === 0 ? (
              <div className="text-center py-12 text-slate-500 dark:text-slate-400 text-sm">
                <MapPin className="w-8 h-8 mx-auto mb-2 opacity-40" />
                {t('triage.no_buildings') || 'Aucun batiment dans cette categorie'}
              </div>
            ) : (
              sortedBuildings.map((b) => (
                <BuildingRow
                  key={b.id}
                  building={b}
                  config={statusConfig[b.status as TriageStatus] || statusConfig.under_control}
                  trend={trendMap.get(b.id)}
                  onClick={() => navigate(`/buildings/${b.id}`)}
                />
              ))
            )}
          </div>

          {/* Total count */}
          <p className="text-center text-xs text-slate-400 dark:text-slate-500 mt-6">
            {sortedBuildings.length} / {data.buildings.length} {t('triage.buildings') || 'batiments'}
          </p>
        </>
      )}

      {/* === BENCHMARK TAB === */}
      {activeTab === 'benchmark' && !benchmarkLoading && (
        <>
          {benchmarkData && sortedBenchmarkBuildings.length > 0 ? (
            <>
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                {t('portfolio_benchmark.worst_first') || 'Les plus urgents'}
              </h2>
              <div className="space-y-2" data-testid="benchmark-list">
                {sortedBenchmarkBuildings.map((b) => (
                  <BenchmarkRow
                    key={b.id}
                    building={b}
                    trend={trendMap.get(b.id)}
                    onClick={() => navigate(`/buildings/${b.id}`)}
                  />
                ))}
              </div>
              <p className="text-center text-xs text-slate-400 dark:text-slate-500 mt-6">
                {sortedBenchmarkBuildings.length} {t('triage.buildings') || 'batiments'}
              </p>
            </>
          ) : (
            <div className="text-center py-12 text-slate-500 dark:text-slate-400 text-sm">
              <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-40" />
              {t('portfolio_benchmark.no_benchmark_data') || 'Aucune donnee de benchmark disponible'}
            </div>
          )}
        </>
      )}

      {/* === CLUSTERS TAB === */}
      {activeTab === 'clusters' && (
        <>
          {benchmarkData && (benchmarkData.clusters || []).length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" data-testid="cluster-list">
              {(benchmarkData.clusters || []).map((c) => (
                <ClusterCard key={c.key} cluster={c} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-500 dark:text-slate-400 text-sm">
              <Layers className="w-8 h-8 mx-auto mb-2 opacity-40" />
              {t('portfolio_benchmark.no_clusters') || 'Aucun cluster identifie'}
            </div>
          )}
        </>
      )}
    </div>
  );
}
