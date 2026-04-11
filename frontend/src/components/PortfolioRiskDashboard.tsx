import { useState, useMemo, lazy, Suspense } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { portfolioRiskApi } from '@/api/portfolioRisk';
import type { PortfolioRiskOverview } from '@/api/portfolioRisk';
import { Building2, AlertTriangle, CheckCircle2, TrendingDown, Map, List, Loader2 } from 'lucide-react';
import { DashboardSkeleton } from '@/components/Skeleton';

const PortfolioRiskMapLazy = lazy(() => import('@/components/PortfolioRiskMapEvidence'));

const GRADE_COLORS: Record<string, string> = {
  A: '#22c55e',
  B: '#3b82f6',
  C: '#eab308',
  D: '#f97316',
  F: '#ef4444',
};

const GRADE_BG: Record<string, string> = {
  A: 'bg-green-100 dark:bg-green-900/30',
  B: 'bg-blue-100 dark:bg-blue-900/30',
  C: 'bg-yellow-100 dark:bg-yellow-900/30',
  D: 'bg-orange-100 dark:bg-orange-900/30',
  F: 'bg-red-100 dark:bg-red-900/30',
};

const GRADE_TEXT: Record<string, string> = {
  A: 'text-green-700 dark:text-green-300',
  B: 'text-blue-700 dark:text-blue-300',
  C: 'text-yellow-700 dark:text-yellow-300',
  D: 'text-orange-700 dark:text-orange-300',
  F: 'text-red-700 dark:text-red-300',
};

type ViewMode = 'map' | 'table';

export function PortfolioRiskDashboard() {
  const { t } = useTranslation();
  const [viewMode, setViewMode] = useState<ViewMode>('map');
  const [filterGrade, setFilterGrade] = useState('');
  const [filterCity, setFilterCity] = useState('');

  const {
    data: overview,
    isLoading,
    isError,
  } = useQuery<PortfolioRiskOverview>({
    queryKey: ['portfolio', 'risk-overview'],
    queryFn: portfolioRiskApi.getOverview,
  });

  const cities = useMemo(() => {
    if (!overview) return [];
    const set = new Set(overview.buildings.map((b) => b.city).filter(Boolean));
    return Array.from(set).sort();
  }, [overview]);

  const filteredBuildings = useMemo(() => {
    if (!overview) return [];
    let result = overview.buildings;
    if (filterGrade) {
      result = result.filter((b) => b.grade === filterGrade);
    }
    if (filterCity) {
      result = result.filter((b) => b.city === filterCity);
    }
    return result;
  }, [overview, filterGrade, filterCity]);

  const sortedBuildings = useMemo(() => {
    return [...filteredBuildings].sort((a, b) => a.score - b.score);
  }, [filteredBuildings]);

  const mappableBuildings = useMemo(() => {
    return filteredBuildings.filter((b) => b.latitude != null && b.longitude != null);
  }, [filteredBuildings]);

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (isError || !overview) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
      </div>
    );
  }

  const dist = overview.distribution;
  const gradeEntries: [string, number][] = [
    ['A', dist.grade_a],
    ['B', dist.grade_b],
    ['C', dist.grade_c],
    ['D', dist.grade_d],
    ['F', dist.grade_f],
  ];
  const maxGradeCount = Math.max(...gradeEntries.map(([, c]) => c), 1);

  const kpis = [
    {
      label: t('portfolio_risk.total_buildings'),
      value: overview.total_buildings,
      icon: Building2,
      color: 'bg-blue-500',
    },
    {
      label: t('portfolio_risk.avg_score'),
      value: `${overview.avg_evidence_score}`,
      icon: CheckCircle2,
      color: 'bg-emerald-500',
    },
    {
      label: t('portfolio_risk.at_risk'),
      value: overview.buildings_at_risk,
      icon: AlertTriangle,
      color: 'bg-red-500',
    },
    {
      label: t('portfolio_risk.ok'),
      value: overview.buildings_ok,
      icon: TrendingDown,
      color: 'bg-green-500',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">{t('portfolio_risk.title')}</h2>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm"
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

      {/* Controls: view toggle + filters */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={() => setViewMode('map')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
            viewMode === 'map'
              ? 'bg-red-600 text-white border-red-600'
              : 'bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-200 border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700'
          }`}
        >
          <Map className="w-4 h-4" />
          {t('portfolio_risk.map_view')}
        </button>
        <button
          onClick={() => setViewMode('table')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
            viewMode === 'table'
              ? 'bg-red-600 text-white border-red-600'
              : 'bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-200 border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700'
          }`}
        >
          <List className="w-4 h-4" />
          {t('portfolio_risk.table_view')}
        </button>

        {/* Grade filter */}
        <select
          value={filterGrade}
          onChange={(e) => setFilterGrade(e.target.value)}
          className="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          <option value="">{t('portfolio_risk.filter_grade')}</option>
          {['A', 'B', 'C', 'D', 'F'].map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>

        {/* City filter */}
        <select
          value={filterCity}
          onChange={(e) => setFilterCity(e.target.value)}
          className="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          <option value="">{t('portfolio_risk.filter_city')}</option>
          {cities.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {/* Map View */}
      {viewMode === 'map' && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
          <Suspense
            fallback={
              <div className="h-[500px] flex items-center justify-center">
                <div className="text-center">
                  <Loader2 className="w-8 h-8 animate-spin text-red-600 mx-auto mb-2" />
                  <p className="text-sm text-gray-500 dark:text-slate-400">{t('app.loading')}</p>
                </div>
              </div>
            }
          >
            <PortfolioRiskMapLazy buildings={mappableBuildings} />
          </Suspense>
        </div>
      )}

      {/* Table View */}
      {viewMode === 'table' && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-700/50">
                  <th className="text-left px-4 py-3 font-medium text-gray-600 dark:text-slate-300">
                    {t('building.address')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 dark:text-slate-300">
                    {t('building.city')}
                  </th>
                  <th className="text-center px-4 py-3 font-medium text-gray-600 dark:text-slate-300">
                    {t('portfolio_risk.avg_score')}
                  </th>
                  <th className="text-center px-4 py-3 font-medium text-gray-600 dark:text-slate-300">Grade</th>
                  <th className="text-center px-4 py-3 font-medium text-gray-600 dark:text-slate-300">
                    {t('portfolio.critical_actions')}
                  </th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {sortedBuildings.map((b) => (
                  <tr
                    key={b.building_id}
                    className="border-b border-gray-100 dark:border-slate-700/50 hover:bg-gray-50 dark:hover:bg-slate-700/30"
                  >
                    <td className="px-4 py-3 text-gray-900 dark:text-white">{b.address}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-300">{b.city}</td>
                    <td className="px-4 py-3 text-center font-medium text-gray-900 dark:text-white">{b.score}</td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${GRADE_BG[b.grade] || ''} ${GRADE_TEXT[b.grade] || ''}`}
                      >
                        {b.grade}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {b.critical_actions_count > 0 ? (
                        <span className="text-red-600 dark:text-red-400 font-medium">{b.critical_actions_count}</span>
                      ) : (
                        <span className="text-gray-400 dark:text-slate-500">0</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/buildings/${b.building_id}`}
                        className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                      >
                        {t('form.view')}
                      </Link>
                    </td>
                  </tr>
                ))}
                {sortedBuildings.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500 dark:text-slate-400">
                      {t('portfolio.empty')}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Grade Distribution */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          {t('portfolio_risk.grade_distribution')}
        </h3>
        <div className="space-y-3">
          {gradeEntries.map(([grade, count]) => (
            <div key={grade} className="flex items-center gap-3">
              <span
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${GRADE_BG[grade]} ${GRADE_TEXT[grade]}`}
              >
                {grade}
              </span>
              <div className="flex-1">
                <div className="w-full h-6 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${maxGradeCount > 0 ? Math.round((count / maxGradeCount) * 100) : 0}%`,
                      backgroundColor: GRADE_COLORS[grade],
                    }}
                  />
                </div>
              </div>
              <span className="w-10 text-right text-sm font-medium text-gray-900 dark:text-white">{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default PortfolioRiskDashboard;
