import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { apiClient } from '@/api/client';
import {
  Building2,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldAlert,
  TrendingUp,
  ChevronUp,
  ChevronDown,
  Target,
  DollarSign,
} from 'lucide-react';
import { cn, formatDate } from '@/utils/formatters';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BuildingRow {
  id: string;
  name: string;
  address: string;
  municipality: string;
  canton: string;
  passport_grade: string;
  completeness_pct: number;
  trust_pct: number;
  readiness_status: string;
  open_actions_count: number;
  overdue_actions_count: number;
  expiring_diagnostics_count: number;
  planned_interventions_count: number;
  estimated_cost_pending: number | null;
  risk_level: string;
  last_activity: string | null;
}

interface PriorityItem {
  building_id: string;
  building_name: string;
  reason: string;
  priority_score: number;
}

interface Aggregates {
  total_buildings: number;
  grade_distribution: Record<string, number>;
  readiness_distribution: Record<string, number>;
  avg_completeness: number;
  avg_trust: number;
  total_open_actions: number;
  total_overdue: number;
  total_expiring_90d: number;
  total_planned_interventions: number;
  buildings_needing_attention: number;
}

interface BudgetWindow {
  buildings_with_work: number;
  estimated_cost: number | null;
}

interface PortfolioOverview {
  buildings: BuildingRow[];
  aggregates: Aggregates;
  top_priorities: PriorityItem[];
  budget_horizon: Record<string, BudgetWindow>;
}

interface HeatmapPoint {
  building_id: string;
  building_name: string;
  completeness_pct: number;
  trust_pct: number;
  passport_grade: string;
  readiness_status: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-emerald-500 text-white',
  B: 'bg-green-400 text-white',
  C: 'bg-yellow-400 text-gray-900',
  D: 'bg-orange-400 text-white',
  E: 'bg-red-500 text-white',
  F: 'bg-red-700 text-white',
  unknown: 'bg-gray-300 dark:bg-slate-600 text-gray-700 dark:text-slate-200',
};

const GRADE_BAR_COLORS: Record<string, string> = {
  A: 'bg-emerald-500',
  B: 'bg-green-400',
  C: 'bg-yellow-400',
  D: 'bg-orange-400',
  E: 'bg-red-500',
  F: 'bg-red-700',
  unknown: 'bg-gray-300 dark:bg-slate-600',
};

const READINESS_BADGE: Record<string, string> = {
  ready: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
  partial: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
  not_ready: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
};

const READINESS_LABEL: Record<string, string> = {
  ready: 'Pret',
  partial: 'Partiel',
  not_ready: 'Non pret',
};

const READINESS_DOT_COLOR: Record<string, string> = {
  ready: '#22c55e',
  partial: '#eab308',
  not_ready: '#ef4444',
};

type SortKey = keyof BuildingRow;

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

const fetchOverview = async (): Promise<PortfolioOverview> => {
  const res = await apiClient.get<PortfolioOverview>('/portfolio/command');
  return res.data;
};

const fetchHeatmap = async (): Promise<{ buildings: HeatmapPoint[] }> => {
  const res = await apiClient.get<{ buildings: HeatmapPoint[] }>('/portfolio/heatmap');
  return res.data;
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  icon: Icon,
  color,
  onClick,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color: string;
  onClick?: () => void;
}) {
  return (
    <div
      className={cn(
        'bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm',
        onClick && 'cursor-pointer hover:border-red-300 dark:hover:border-red-700 hover:shadow-md transition-all',
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onClick(); } : undefined}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-slate-400">{label}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
        </div>
        <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center', color)}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </div>
  );
}

function GradeBadge({ grade }: { grade: string }) {
  return (
    <span className={cn('inline-flex items-center justify-center w-8 h-8 rounded-lg text-sm font-bold', GRADE_COLORS[grade] || GRADE_COLORS.unknown)}>
      {grade}
    </span>
  );
}

function ProgressBar({ pct, color }: { pct: number; color?: string }) {
  const barColor = color || (pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-amber-500' : 'bg-red-500');
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 rounded-full bg-gray-100 dark:bg-slate-700">
        <div className={cn('h-full rounded-full transition-all', barColor)} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-500 dark:text-slate-400 w-10 text-right">{Math.round(pct)}%</span>
    </div>
  );
}

function GradeDistributionBar({
  distribution,
  onGradeClick,
}: {
  distribution: Record<string, number>;
  onGradeClick: (grade: string) => void;
}) {
  const grades = ['A', 'B', 'C', 'D', 'E', 'F'];
  const total = grades.reduce((s, g) => s + (distribution[g] || 0), 0);
  if (total === 0) return <p className="text-sm text-gray-500 dark:text-slate-400">Aucune donnee</p>;

  return (
    <div className="space-y-3">
      <div className="flex h-8 rounded-lg overflow-hidden bg-gray-100 dark:bg-slate-700">
        {grades.map((g) => {
          const count = distribution[g] || 0;
          if (count === 0) return null;
          const pct = (count / total) * 100;
          return (
            <div
              key={g}
              className={cn(GRADE_BAR_COLORS[g], 'h-full cursor-pointer hover:opacity-80 transition-opacity flex items-center justify-center text-xs font-bold text-white')}
              style={{ width: `${pct}%`, minWidth: pct > 3 ? undefined : '24px' }}
              onClick={() => onGradeClick(g)}
              title={`${g}: ${count}`}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onGradeClick(g); }}
            >
              {pct > 8 ? `${g}: ${count}` : g}
            </div>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-3 text-xs">
        {grades.map((g) => (
          <div
            key={g}
            className="flex items-center gap-1.5 cursor-pointer hover:opacity-80"
            onClick={() => onGradeClick(g)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onGradeClick(g); }}
          >
            <span className={cn('w-3 h-3 rounded-full', GRADE_BAR_COLORS[g])} />
            <span className="text-gray-600 dark:text-slate-300">{g}: {distribution[g] || 0}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function BudgetCard({ label, window }: { label: string; window: BudgetWindow }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm">
      <p className="text-sm text-gray-500 dark:text-slate-400 mb-2">{label}</p>
      <div className="space-y-1">
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{window.buildings_with_work}</p>
        <p className="text-xs text-gray-500 dark:text-slate-400">batiments avec travaux</p>
        {window.estimated_cost != null && (
          <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400 mt-1">
            CHF {window.estimated_cost.toLocaleString('fr-CH')}
          </p>
        )}
      </div>
    </div>
  );
}

function HeatmapChart({ points }: { points: HeatmapPoint[] }) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (points.length === 0) {
    return <p className="text-sm text-gray-500 dark:text-slate-400 text-center py-8">Aucune donnee</p>;
  }

  // SVG-based scatter plot
  const W = 600;
  const H = 400;
  const PAD = 50;
  const plotW = W - PAD * 2;
  const plotH = H - PAD * 2;

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 400 }}>
        {/* Grid lines */}
        {[0, 25, 50, 75, 100].map((v) => {
          const x = PAD + (v / 100) * plotW;
          const y = PAD + ((100 - v) / 100) * plotH;
          return (
            <g key={v}>
              <line x1={x} y1={PAD} x2={x} y2={PAD + plotH} stroke="currentColor" strokeOpacity={0.1} />
              <line x1={PAD} y1={y} x2={PAD + plotW} y2={y} stroke="currentColor" strokeOpacity={0.1} />
              <text x={x} y={PAD + plotH + 16} textAnchor="middle" className="fill-gray-400 dark:fill-slate-500" fontSize={10}>
                {v}%
              </text>
              <text x={PAD - 8} y={y + 3} textAnchor="end" className="fill-gray-400 dark:fill-slate-500" fontSize={10}>
                {v}%
              </text>
            </g>
          );
        })}

        {/* Axes labels */}
        <text x={W / 2} y={H - 4} textAnchor="middle" className="fill-gray-500 dark:fill-slate-400" fontSize={12}>
          Completude
        </text>
        <text x={12} y={H / 2} textAnchor="middle" className="fill-gray-500 dark:fill-slate-400" fontSize={12} transform={`rotate(-90, 12, ${H / 2})`}>
          Confiance
        </text>

        {/* Danger zone background */}
        <rect
          x={PAD}
          y={PAD + plotH / 2}
          width={plotW / 2}
          height={plotH / 2}
          fill="red"
          fillOpacity={0.04}
          rx={4}
        />

        {/* Points */}
        {points.map((p, i) => {
          const cx = PAD + (p.completeness_pct / 100) * plotW;
          const cy = PAD + ((100 - p.trust_pct) / 100) * plotH;
          const color = READINESS_DOT_COLOR[p.readiness_status] || '#94a3b8';
          const isHovered = hoveredIdx === i;
          return (
            <g key={p.building_id}>
              <circle
                cx={cx}
                cy={cy}
                r={isHovered ? 8 : 6}
                fill={color}
                fillOpacity={0.8}
                stroke={isHovered ? '#111' : 'white'}
                strokeWidth={isHovered ? 2 : 1}
                className="cursor-pointer transition-all"
                onMouseEnter={() => setHoveredIdx(i)}
                onMouseLeave={() => setHoveredIdx(null)}
              />
            </g>
          );
        })}
      </svg>

      {/* Tooltip */}
      {hoveredIdx !== null && points[hoveredIdx] && (
        <div className="absolute top-2 right-2 bg-white dark:bg-slate-700 rounded-lg shadow-lg border border-gray-200 dark:border-slate-600 p-3 text-sm z-10 max-w-[200px]">
          <p className="font-medium text-gray-900 dark:text-white truncate">{points[hoveredIdx].building_name}</p>
          <div className="mt-1 space-y-0.5 text-gray-500 dark:text-slate-400">
            <p>Grade: <span className="font-bold">{points[hoveredIdx].passport_grade}</span></p>
            <p>Completude: {Math.round(points[hoveredIdx].completeness_pct)}%</p>
            <p>Confiance: {Math.round(points[hoveredIdx].trust_pct)}%</p>
            <p>Status: {READINESS_LABEL[points[hoveredIdx].readiness_status] || points[hoveredIdx].readiness_status}</p>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex justify-center gap-4 mt-2 text-xs">
        {Object.entries(READINESS_LABEL).map(([key, label]) => (
          <div key={key} className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: READINESS_DOT_COLOR[key] }} />
            <span className="text-gray-600 dark:text-slate-300">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function PortfolioCommand() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [sortKey, setSortKey] = useState<SortKey>('overdue_actions_count');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [gradeFilter, setGradeFilter] = useState<string | null>(null);
  const [readinessFilter, setReadinessFilter] = useState<string | null>(null);
  const [cantonFilter, setCantonFilter] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['portfolio', 'command'],
    queryFn: fetchOverview,
  });

  const { data: heatmapData } = useQuery({
    queryKey: ['portfolio', 'heatmap'],
    queryFn: fetchHeatmap,
  });

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <ChevronDown className="w-3 h-3 opacity-30" />;
    return sortDir === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />;
  };

  // Compute canton options
  const cantons = useMemo(() => {
    if (!data) return [];
    const set = new Set(data.buildings.map((b) => b.canton).filter(Boolean));
    return Array.from(set).sort();
  }, [data]);

  // Filter + sort buildings
  const filteredBuildings = useMemo(() => {
    if (!data) return [];
    let list = data.buildings;
    if (gradeFilter) list = list.filter((b) => b.passport_grade === gradeFilter);
    if (readinessFilter) list = list.filter((b) => b.readiness_status === readinessFilter);
    if (cantonFilter) list = list.filter((b) => b.canton === cantonFilter);

    return [...list].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === 'string' && typeof bv === 'string') {
        return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      const na = typeof av === 'number' ? av : 0;
      const nb = typeof bv === 'number' ? bv : 0;
      return sortDir === 'asc' ? na - nb : nb - na;
    });
  }, [data, gradeFilter, readinessFilter, cantonFilter, sortKey, sortDir]);

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6 p-6">
        <div className="h-8 w-64 bg-gray-200 dark:bg-slate-700 rounded" />
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-28 rounded-xl bg-gray-200 dark:bg-slate-700" />
          ))}
        </div>
        <div className="h-64 rounded-xl bg-gray-200 dark:bg-slate-700" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('app.error') || 'Erreur de chargement'}</p>
      </div>
    );
  }

  const agg = data.aggregates;
  const avgGrade = (() => {
    const grades = ['A', 'B', 'C', 'D', 'E', 'F'];
    const weights = [6, 5, 4, 3, 2, 1];
    let sum = 0;
    let count = 0;
    grades.forEach((g, i) => {
      const n = agg.grade_distribution[g] || 0;
      sum += n * weights[i];
      count += n;
    });
    if (count === 0) return '—';
    const avg = sum / count;
    if (avg >= 5.5) return 'A';
    if (avg >= 4.5) return 'B';
    if (avg >= 3.5) return 'C';
    if (avg >= 2.5) return 'D';
    if (avg >= 1.5) return 'E';
    return 'F';
  })();

  const readyCount = agg.readiness_distribution.ready || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {t('portfolio_cmd.title') || 'Centre de commande portefeuille'}
        </h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
          {t('portfolio_cmd.subtitle') || 'Vue strategique directeur -- attention, budget, priorites'}
        </p>
      </div>

      {/* Section 1 - Aggregate Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard
          label={t('portfolio_cmd.total_buildings') || 'Total batiments'}
          value={agg.total_buildings}
          icon={Building2}
          color="bg-blue-500"
        />
        <StatCard
          label={t('portfolio_cmd.avg_grade') || 'Grade moyen'}
          value={avgGrade}
          icon={TrendingUp}
          color="bg-indigo-500"
        />
        <StatCard
          label={t('portfolio_cmd.avg_completeness') || 'Completude moyenne'}
          value={`${Math.round(agg.avg_completeness)}%`}
          icon={CheckCircle2}
          color="bg-emerald-500"
        />
        <StatCard
          label={t('portfolio_cmd.ready_count') || 'Prets'}
          value={readyCount}
          icon={CheckCircle2}
          color="bg-green-500"
          onClick={() => setReadinessFilter(readinessFilter === 'ready' ? null : 'ready')}
        />
        <StatCard
          label={t('portfolio_cmd.overdue') || 'Actions en retard'}
          value={agg.total_overdue}
          icon={AlertTriangle}
          color="bg-red-500"
        />
        <StatCard
          label={t('portfolio_cmd.expiring') || 'Diagnostics expirant'}
          value={agg.total_expiring_90d}
          icon={Clock}
          color="bg-amber-500"
        />
      </div>

      {/* Section 2 - Grade Distribution */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-indigo-500" />
          {t('portfolio_cmd.grade_distribution') || 'Distribution des grades'}
        </h2>
        <GradeDistributionBar
          distribution={agg.grade_distribution}
          onGradeClick={(g) => setGradeFilter(gradeFilter === g ? null : g)}
        />
      </div>

      {/* Section 3 - Top Priorities */}
      {data.top_priorities.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-red-500" />
            {t('portfolio_cmd.top_priorities') || 'Top 5 batiments necessitant attention'}
          </h2>
          <div className="space-y-3">
            {data.top_priorities.map((p, idx) => {
              const bld = data.buildings.find((b) => b.id === p.building_id);
              return (
                <div
                  key={p.building_id}
                  className="flex items-center gap-4 p-3 rounded-lg bg-gray-50 dark:bg-slate-700/50 cursor-pointer hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                  onClick={() => navigate(`/buildings/${p.building_id}`)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') navigate(`/buildings/${p.building_id}`); }}
                >
                  <span className="text-sm font-bold text-gray-400 dark:text-slate-500 w-6">#{idx + 1}</span>
                  {bld && <GradeBadge grade={bld.passport_grade} />}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{p.building_name}</p>
                    <p className="text-xs text-gray-500 dark:text-slate-400 truncate">{p.reason}</p>
                  </div>
                  {bld && (
                    <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium', READINESS_BADGE[bld.readiness_status])}>
                      {READINESS_LABEL[bld.readiness_status] || bld.readiness_status}
                    </span>
                  )}
                  {bld && bld.overdue_actions_count > 0 && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 font-medium">
                      {bld.overdue_actions_count} retard
                    </span>
                  )}
                  <span className="text-xs font-mono text-gray-400 dark:text-slate-500">{Math.round(p.priority_score)}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Section 4 - Portfolio Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-slate-700">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Building2 className="w-5 h-5 text-blue-500" />
              {t('portfolio_cmd.all_buildings') || 'Tous les batiments'}
            </h2>
            <div className="flex-1" />

            {/* Filters */}
            {gradeFilter && (
              <button
                onClick={() => setGradeFilter(null)}
                className="text-xs px-2 py-1 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-900/50"
              >
                Grade: {gradeFilter} x
              </button>
            )}
            {readinessFilter && (
              <button
                onClick={() => setReadinessFilter(null)}
                className="text-xs px-2 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50"
              >
                {READINESS_LABEL[readinessFilter] || readinessFilter} x
              </button>
            )}
            <select
              value={cantonFilter || ''}
              onChange={(e) => setCantonFilter(e.target.value || null)}
              className="text-xs border border-gray-300 dark:border-slate-600 rounded-lg px-2 py-1 bg-white dark:bg-slate-700 text-gray-700 dark:text-slate-200"
            >
              <option value="">{t('portfolio_cmd.all_cantons') || 'Tous cantons'}</option>
              {cantons.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <span className="text-xs text-gray-500 dark:text-slate-400">
              {filteredBuildings.length} / {agg.total_buildings}
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50">
                {([
                  ['name', 'Batiment'],
                  ['passport_grade', 'Grade'],
                  ['completeness_pct', 'Completude'],
                  ['trust_pct', 'Confiance'],
                  ['readiness_status', 'Readiness'],
                  ['open_actions_count', 'Actions'],
                  ['overdue_actions_count', 'En retard'],
                  ['expiring_diagnostics_count', 'Expirations'],
                  ['planned_interventions_count', 'Interventions'],
                  ['last_activity', 'Derniere activite'],
                ] as [SortKey, string][]).map(([key, label]) => (
                  <th
                    key={key}
                    className="px-3 py-2 text-left font-medium text-gray-500 dark:text-slate-400 cursor-pointer hover:text-gray-700 dark:hover:text-slate-200 whitespace-nowrap"
                    onClick={() => handleSort(key)}
                  >
                    <div className="flex items-center gap-1">
                      {label}
                      <SortIcon col={key} />
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredBuildings.map((b) => (
                <tr
                  key={b.id}
                  className="border-b border-gray-100 dark:border-slate-700/50 hover:bg-gray-50 dark:hover:bg-slate-700/30 cursor-pointer transition-colors"
                  onClick={() => navigate(`/buildings/${b.id}`)}
                >
                  <td className="px-3 py-2.5">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white truncate max-w-[200px]">{b.name}</p>
                      <p className="text-xs text-gray-500 dark:text-slate-400 truncate max-w-[200px]">{b.municipality}, {b.canton}</p>
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <GradeBadge grade={b.passport_grade} />
                  </td>
                  <td className="px-3 py-2.5 min-w-[120px]">
                    <ProgressBar pct={b.completeness_pct} />
                  </td>
                  <td className="px-3 py-2.5 min-w-[120px]">
                    <ProgressBar pct={b.trust_pct} />
                  </td>
                  <td className="px-3 py-2.5">
                    <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium whitespace-nowrap', READINESS_BADGE[b.readiness_status])}>
                      {READINESS_LABEL[b.readiness_status] || b.readiness_status}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    <span className={cn('font-medium', b.open_actions_count > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-gray-400 dark:text-slate-500')}>
                      {b.open_actions_count}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    <span className={cn('font-medium', b.overdue_actions_count > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-400 dark:text-slate-500')}>
                      {b.overdue_actions_count}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    <span className={cn('font-medium', b.expiring_diagnostics_count > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-gray-400 dark:text-slate-500')}>
                      {b.expiring_diagnostics_count}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    <span className={cn('font-medium', b.planned_interventions_count > 0 ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400 dark:text-slate-500')}>
                      {b.planned_interventions_count}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-xs text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    {b.last_activity ? formatDate(b.last_activity) : '—'}
                  </td>
                </tr>
              ))}
              {filteredBuildings.length === 0 && (
                <tr>
                  <td colSpan={10} className="px-3 py-8 text-center text-gray-500 dark:text-slate-400">
                    {t('app.no_data') || 'Aucun batiment'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Section 5 - Budget Horizon */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-emerald-500" />
          {t('portfolio_cmd.budget_horizon') || 'Horizon budgetaire'}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <BudgetCard label="30 jours" window={data.budget_horizon.next_30d} />
          <BudgetCard label="90 jours" window={data.budget_horizon.next_90d} />
          <BudgetCard label="365 jours" window={data.budget_horizon.next_365d} />
        </div>
      </div>

      {/* Section 6 - Readiness Heatmap */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-purple-500" />
          {t('portfolio_cmd.heatmap') || 'Matrice completude / confiance'}
        </h2>
        <p className="text-xs text-gray-500 dark:text-slate-400 mb-4">
          {t('portfolio_cmd.heatmap_desc') || 'Chaque point = un batiment. Zone rouge (bas-gauche) = completude et confiance faibles.'}
        </p>
        <HeatmapChart points={heatmapData?.buildings || []} />
      </div>
    </div>
  );
}
