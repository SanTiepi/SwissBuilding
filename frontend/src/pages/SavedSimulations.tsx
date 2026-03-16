import { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { useBuildings } from '@/hooks/useBuildings';
import { savedSimulationsApi } from '@/api/savedSimulations';
import { toast } from '@/store/toastStore';
import { cn, formatCHF, formatDate } from '@/utils/formatters';
import type { SavedSimulation, Building } from '@/types';
import {
  Loader2,
  Trash2,
  ChevronDown,
  ChevronUp,
  BarChart3,
  Clock,
  Award,
  TrendingUp,
  ArrowRight,
  Play,
  Download,
  Search,
  Filter,
  X,
  Beaker,
  Building2,
  Calendar,
  DollarSign,
  Target,
  Layers,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────

interface SimulationWithBuilding extends SavedSimulation {
  building_address?: string;
  building_city?: string;
}

type SortField = 'date' | 'grade' | 'cost';
type SortDir = 'asc' | 'desc';

// ── Helpers ────────────────────────────────────────────────────────

const GRADE_ORDER: Record<string, number> = { A: 5, B: 4, C: 3, D: 2, E: 1, F: 0 };

function gradeColor(grade: string | null): string {
  switch (grade) {
    case 'A':
      return 'text-green-600 dark:text-green-400';
    case 'B':
      return 'text-blue-600 dark:text-blue-400';
    case 'C':
      return 'text-yellow-600 dark:text-yellow-400';
    case 'D':
      return 'text-orange-600 dark:text-orange-400';
    default:
      return 'text-red-600 dark:text-red-400';
  }
}

function gradeBgColor(grade: string | null): string {
  switch (grade) {
    case 'A':
      return 'bg-green-100 dark:bg-green-900/30';
    case 'B':
      return 'bg-blue-100 dark:bg-blue-900/30';
    case 'C':
      return 'bg-yellow-100 dark:bg-yellow-900/30';
    case 'D':
      return 'bg-orange-100 dark:bg-orange-900/30';
    default:
      return 'bg-red-100 dark:bg-red-900/30';
  }
}

function gradeNumericDelta(from: string | null, to: string | null): number {
  return (GRADE_ORDER[to ?? ''] ?? 0) - (GRADE_ORDER[from ?? ''] ?? 0);
}

function getProjectedGrade(sim: SavedSimulation): string | null {
  const results = sim.results_json as Record<string, unknown> | null;
  if (!results) return sim.risk_level_after ?? null;
  const projected = results.projected_state as Record<string, unknown> | undefined;
  if (projected?.passport_grade) return projected.passport_grade as string;
  return sim.risk_level_after ?? null;
}

function getCurrentGrade(sim: SavedSimulation): string | null {
  const results = sim.results_json as Record<string, unknown> | null;
  if (!results) return sim.risk_level_before ?? null;
  const current = results.current_state as Record<string, unknown> | undefined;
  if (current?.passport_grade) return current.passport_grade as string;
  return sim.risk_level_before ?? null;
}

function getInterventions(sim: SavedSimulation): Record<string, unknown>[] {
  const params = sim.parameters_json as Record<string, unknown> | null;
  if (!params) return [];
  const interventions = params.interventions as Record<string, unknown>[] | undefined;
  return interventions ?? [];
}

function getRecommendations(sim: SavedSimulation): string[] {
  const results = sim.results_json as Record<string, unknown> | null;
  if (!results) return [];
  return (results.recommendations as string[] | undefined) ?? [];
}

function getImpactSummary(sim: SavedSimulation): Record<string, unknown> | null {
  const results = sim.results_json as Record<string, unknown> | null;
  if (!results) return null;
  return (results.impact_summary as Record<string, unknown> | undefined) ?? null;
}

function getTrustDelta(sim: SavedSimulation): number | null {
  const impact = getImpactSummary(sim);
  if (!impact) return null;
  return (impact.trust_delta as number | undefined) ?? null;
}

function exportSimulationCSV(sims: SimulationWithBuilding[]): void {
  const header = ['Title', 'Building', 'Type', 'Cost (CHF)', 'Duration (weeks)', 'Grade Before', 'Grade After', 'Date'];
  const rows = sims.map((s) => [
    s.title,
    s.building_address ?? s.building_id,
    s.simulation_type,
    s.total_cost_chf?.toString() ?? '',
    s.total_duration_weeks?.toString() ?? '',
    getCurrentGrade(s) ?? '',
    getProjectedGrade(s) ?? '',
    formatDate(s.created_at),
  ]);
  const csv = [header, ...rows].map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `simulations_export_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Main Component ─────────────────────────────────────────────────

export default function SavedSimulations() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // State
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [filterBuildingId, setFilterBuildingId] = useState<string>('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [compareMode, setCompareMode] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Data
  const { data: buildingsData, isLoading: buildingsLoading } = useBuildings({ size: 200 });
  const buildings = useMemo(() => buildingsData?.items ?? [], [buildingsData]);
  const buildingMap = useMemo(() => {
    const map = new Map<string, Building>();
    for (const b of buildings) map.set(b.id, b);
    return map;
  }, [buildings]);

  // Fetch simulations for all buildings
  const {
    data: allSimulations,
    isLoading: simsLoading,
    isError: simsError,
  } = useQuery({
    queryKey: ['all-saved-simulations', buildings.map((b) => b.id)],
    queryFn: async () => {
      if (buildings.length === 0) return [];
      const results = await Promise.allSettled(buildings.map((b) => savedSimulationsApi.list(b.id)));
      const sims: SimulationWithBuilding[] = [];
      for (let i = 0; i < results.length; i++) {
        const r = results[i];
        if (r.status === 'fulfilled' && r.value.items) {
          const building = buildings[i];
          for (const sim of r.value.items) {
            sims.push({
              ...sim,
              building_address: building.address,
              building_city: building.city,
            });
          }
        }
      }
      return sims;
    },
    enabled: buildings.length > 0,
  });

  const simulations = useMemo(() => allSimulations ?? [], [allSimulations]);

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: ({ buildingId, simId }: { buildingId: string; simId: string }) =>
      savedSimulationsApi.delete(buildingId, simId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['all-saved-simulations'] });
      toast(t('saved_simulations.deleted') || 'Simulation deleted', 'success');
      setDeleteConfirmId(null);
    },
    onError: () => {
      toast(t('app.error') || 'An error occurred', 'error');
    },
  });

  // Filter & sort
  const filtered = useMemo(() => {
    let list = [...simulations];

    if (filterBuildingId) {
      list = list.filter((s) => s.building_id === filterBuildingId);
    }
    if (dateFrom) {
      list = list.filter((s) => s.created_at >= dateFrom);
    }
    if (dateTo) {
      const endDate = dateTo + 'T23:59:59';
      list = list.filter((s) => s.created_at <= endDate);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (s) =>
          s.title.toLowerCase().includes(q) ||
          (s.building_address ?? '').toLowerCase().includes(q) ||
          (s.simulation_type ?? '').toLowerCase().includes(q),
      );
    }

    list.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'date':
          cmp = a.created_at.localeCompare(b.created_at);
          break;
        case 'grade':
          cmp = (GRADE_ORDER[getProjectedGrade(a) ?? ''] ?? 0) - (GRADE_ORDER[getProjectedGrade(b) ?? ''] ?? 0);
          break;
        case 'cost':
          cmp = (a.total_cost_chf ?? 0) - (b.total_cost_chf ?? 0);
          break;
      }
      return sortDir === 'desc' ? -cmp : cmp;
    });

    return list;
  }, [simulations, filterBuildingId, dateFrom, dateTo, searchQuery, sortField, sortDir]);

  // Summary cards
  const summaryCards = useMemo(() => {
    if (simulations.length === 0)
      return {
        total: 0,
        avgImprovement: 0,
        mostSimulatedBuilding: null as string | null,
        bestROI: null as SimulationWithBuilding | null,
      };

    // Average grade improvement
    let totalDelta = 0;
    let deltaCount = 0;
    for (const sim of simulations) {
      const before = getCurrentGrade(sim);
      const after = getProjectedGrade(sim);
      if (before && after) {
        totalDelta += gradeNumericDelta(before, after);
        deltaCount++;
      }
    }

    // Most simulated building
    const buildingCounts: Record<string, number> = {};
    for (const sim of simulations) {
      buildingCounts[sim.building_id] = (buildingCounts[sim.building_id] ?? 0) + 1;
    }
    const topBuildingId = Object.entries(buildingCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;
    const topBuilding = topBuildingId ? buildingMap.get(topBuildingId) : null;

    // Best ROI (highest grade improvement per CHF)
    let bestROI: SimulationWithBuilding | null = null;
    let bestROIValue = -Infinity;
    for (const sim of simulations) {
      const before = getCurrentGrade(sim);
      const after = getProjectedGrade(sim);
      const cost = sim.total_cost_chf ?? 0;
      if (before && after && cost > 0) {
        const delta = gradeNumericDelta(before, after);
        const roi = delta / cost;
        if (roi > bestROIValue) {
          bestROIValue = roi;
          bestROI = sim;
        }
      }
    }

    return {
      total: simulations.length,
      avgImprovement: deltaCount > 0 ? totalDelta / deltaCount : 0,
      mostSimulatedBuilding: topBuilding ? `${topBuilding.address}, ${topBuilding.city}` : topBuildingId,
      bestROI,
    };
  }, [simulations, buildingMap]);

  const toggleSort = useCallback(
    (field: SortField) => {
      if (sortField === field) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortField(field);
        setSortDir('desc');
      }
    },
    [sortField],
  );

  const toggleCompare = useCallback((id: string) => {
    setCompareIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 3) return prev;
      return [...prev, id];
    });
  }, []);

  const handleDelete = useCallback(
    (sim: SimulationWithBuilding) => {
      deleteMutation.mutate({ buildingId: sim.building_id, simId: sim.id });
    },
    [deleteMutation],
  );

  const handleLoadInSimulator = useCallback(
    (sim: SimulationWithBuilding) => {
      // Store simulation data in sessionStorage for the simulator to pick up
      sessionStorage.setItem(
        'swissbuild_load_simulation',
        JSON.stringify({
          title: sim.title,
          interventions: getInterventions(sim),
          results_json: sim.results_json,
        }),
      );
      navigate(`/buildings/${sim.building_id}/simulator`);
    },
    [navigate],
  );

  const compareSimulations = useMemo(() => filtered.filter((s) => compareIds.includes(s.id)), [filtered, compareIds]);

  const isLoading = buildingsLoading || simsLoading;

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('saved_simulations.title') || 'Saved Simulations'}
          </h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            {t('saved_simulations.subtitle') || 'Manage and compare your intervention simulations'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCompareMode(!compareMode)}
            disabled={filtered.length < 2}
            className={cn(
              'flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors',
              compareMode
                ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                : 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/50',
              'disabled:opacity-40 disabled:cursor-not-allowed',
            )}
          >
            <BarChart3 className="w-4 h-4" />
            {t('saved_simulations.compare') || 'Compare'}
            {compareMode && compareIds.length > 0 && (
              <span className="px-1.5 py-0.5 text-xs rounded-full bg-white/20">{compareIds.length}/3</span>
            )}
          </button>
          <button
            onClick={() => exportSimulationCSV(filtered)}
            disabled={filtered.length === 0}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Download className="w-4 h-4" />
            {t('saved_simulations.export') || 'Export'}
          </button>
        </div>
      </div>

      {/* Summary cards */}
      {!isLoading && simulations.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                <Layers className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  {t('saved_simulations.total_simulations') || 'Total Simulations'}
                </p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">{summaryCards.total}</p>
              </div>
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
                <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  {t('saved_simulations.avg_improvement') || 'Avg. Grade Improvement'}
                </p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">
                  {summaryCards.avgImprovement > 0 ? '+' : ''}
                  {summaryCards.avgImprovement.toFixed(1)}
                </p>
              </div>
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
                <Building2 className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  {t('saved_simulations.most_simulated') || 'Most Simulated'}
                </p>
                <p className="text-sm font-semibold text-gray-900 dark:text-white truncate max-w-[180px]">
                  {summaryCards.mostSimulatedBuilding || '-'}
                </p>
              </div>
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/30">
                <Target className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  {t('saved_simulations.best_roi') || 'Best ROI'}
                </p>
                <p className="text-sm font-semibold text-gray-900 dark:text-white truncate max-w-[180px]">
                  {summaryCards.bestROI?.title || '-'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Search + Filters */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-4">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('saved_simulations.search_placeholder') || 'Search simulations...'}
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              'flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border transition-colors',
              showFilters
                ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                : 'border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700',
            )}
          >
            <Filter className="w-4 h-4" />
            {t('saved_simulations.filters') || 'Filters'}
          </button>
        </div>

        {showFilters && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-slate-700 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                {t('saved_simulations.filter_building') || 'Building'}
              </label>
              <select
                value={filterBuildingId}
                onChange={(e) => setFilterBuildingId(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
              >
                <option value="">{t('saved_simulations.all_buildings') || 'All buildings'}</option>
                {buildings.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.address}, {b.city}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                {t('saved_simulations.date_from') || 'From'}
              </label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                {t('saved_simulations.date_to') || 'To'}
              </label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
              />
            </div>
          </div>
        )}

        {/* Active filters */}
        {(filterBuildingId || dateFrom || dateTo) && (
          <div className="mt-3 flex items-center gap-2 flex-wrap">
            {filterBuildingId && (
              <span className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                {buildingMap.get(filterBuildingId)?.address ?? filterBuildingId}
                <button onClick={() => setFilterBuildingId('')}>
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {dateFrom && (
              <span className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                {t('saved_simulations.from') || 'From'}: {dateFrom}
                <button onClick={() => setDateFrom('')}>
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {dateTo && (
              <span className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                {t('saved_simulations.to') || 'To'}: {dateTo}
                <button onClick={() => setDateTo('')}>
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            <button
              onClick={() => {
                setFilterBuildingId('');
                setDateFrom('');
                setDateTo('');
              }}
              className="text-xs text-gray-500 hover:text-gray-700 dark:text-slate-400 dark:hover:text-slate-200"
            >
              {t('saved_simulations.clear_filters') || 'Clear all'}
            </button>
          </div>
        )}
      </div>

      {/* Sort bar */}
      <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-slate-400">
        <span>{t('saved_simulations.sort_by') || 'Sort by'}:</span>
        {(['date', 'grade', 'cost'] as SortField[]).map((field) => (
          <button
            key={field}
            onClick={() => toggleSort(field)}
            className={cn(
              'flex items-center gap-1 px-2 py-1 rounded transition-colors',
              sortField === field
                ? 'bg-gray-200 dark:bg-slate-600 text-gray-900 dark:text-white font-medium'
                : 'hover:bg-gray-100 dark:hover:bg-slate-700',
            )}
          >
            {field === 'date' && (t('saved_simulations.sort_date') || 'Date')}
            {field === 'grade' && (t('saved_simulations.sort_grade') || 'Grade')}
            {field === 'cost' && (t('saved_simulations.sort_cost') || 'Cost')}
            {sortField === field &&
              (sortDir === 'desc' ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />)}
          </button>
        ))}
        <span className="ml-auto text-gray-400 dark:text-slate-500">
          {filtered.length} {t('saved_simulations.results') || 'results'}
        </span>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      )}

      {/* Error */}
      {simsError && (
        <div className="text-center py-12">
          <AlertTriangle className="w-10 h-10 mx-auto mb-3 text-red-400" />
          <p className="text-sm text-red-600 dark:text-red-400">
            {t('saved_simulations.error') || 'Failed to load simulations'}
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !simsError && filtered.length === 0 && (
        <div className="text-center py-16">
          <Beaker className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-slate-600" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">
            {t('saved_simulations.empty_title') || 'No simulations found'}
          </h3>
          <p className="text-sm text-gray-500 dark:text-slate-400 max-w-md mx-auto">
            {t('saved_simulations.empty_description') ||
              'Run simulations from the Intervention Simulator on a building page, then save them to see them here.'}
          </p>
        </div>
      )}

      {/* Simulations list */}
      {!isLoading && filtered.length > 0 && (
        <div className="space-y-3">
          {filtered.map((sim) => {
            const projectedGrade = getProjectedGrade(sim);
            const currentGrade = getCurrentGrade(sim);
            const interventions = getInterventions(sim);
            const isExpanded = expandedId === sim.id;
            const isDeleting = deleteConfirmId === sim.id;

            return (
              <div
                key={sim.id}
                className={cn(
                  'bg-white dark:bg-slate-800 rounded-xl shadow-sm border transition-all duration-200',
                  compareMode && compareIds.includes(sim.id)
                    ? 'border-indigo-400 dark:border-indigo-500 ring-1 ring-indigo-200 dark:ring-indigo-800'
                    : 'border-gray-200 dark:border-slate-700',
                )}
              >
                {/* Main row */}
                <div className="flex items-center gap-4 p-4">
                  {/* Compare checkbox */}
                  {compareMode && (
                    <input
                      type="checkbox"
                      checked={compareIds.includes(sim.id)}
                      onChange={() => toggleCompare(sim.id)}
                      disabled={!compareIds.includes(sim.id) && compareIds.length >= 3}
                      className="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                  )}

                  {/* Grade badge */}
                  {projectedGrade && (
                    <div
                      className={cn(
                        'w-11 h-11 rounded-lg flex items-center justify-center flex-shrink-0',
                        gradeBgColor(projectedGrade),
                      )}
                    >
                      <span className={cn('text-lg font-black', gradeColor(projectedGrade))}>{projectedGrade}</span>
                    </div>
                  )}

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">{sim.title}</p>
                    <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-500 dark:text-slate-400">
                      <Building2 className="w-3 h-3 flex-shrink-0" />
                      <span className="truncate">
                        {sim.building_address ?? sim.building_id}
                        {sim.building_city ? `, ${sim.building_city}` : ''}
                      </span>
                      <span className="text-gray-300 dark:text-slate-600">&middot;</span>
                      <Calendar className="w-3 h-3 flex-shrink-0" />
                      <span>{formatDate(sim.created_at)}</span>
                    </div>
                  </div>

                  {/* Grade transition */}
                  {currentGrade && projectedGrade && (
                    <div className="hidden sm:flex items-center gap-1.5 text-sm">
                      <span className={cn('font-bold', gradeColor(currentGrade))}>{currentGrade}</span>
                      <ArrowRight className="w-3.5 h-3.5 text-gray-400" />
                      <span className={cn('font-bold', gradeColor(projectedGrade))}>{projectedGrade}</span>
                    </div>
                  )}

                  {/* Cost */}
                  {sim.total_cost_chf != null && sim.total_cost_chf > 0 && (
                    <div className="hidden md:flex items-center gap-1 text-sm text-gray-600 dark:text-slate-300">
                      <DollarSign className="w-3.5 h-3.5" />
                      <span>{formatCHF(sim.total_cost_chf)}</span>
                    </div>
                  )}

                  {/* Duration */}
                  {sim.total_duration_weeks != null && sim.total_duration_weeks > 0 && (
                    <div className="hidden lg:flex items-center gap-1 text-sm text-gray-600 dark:text-slate-300">
                      <Clock className="w-3.5 h-3.5" />
                      <span>
                        {sim.total_duration_weeks} {t('saved_simulations.weeks') || 'wks'}
                      </span>
                    </div>
                  )}

                  {/* Actions */}
                  {!compareMode && (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleLoadInSimulator(sim)}
                        className="px-2.5 py-1.5 text-xs font-medium text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/30 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
                        title={t('saved_simulations.load') || 'Load in Simulator'}
                      >
                        <Play className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => setExpandedId(isExpanded ? null : sim.id)}
                        className="px-2.5 py-1.5 text-xs text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                      >
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>
                      <button
                        onClick={() => setDeleteConfirmId(isDeleting ? null : sim.id)}
                        className="px-2.5 py-1.5 text-xs text-gray-400 hover:text-red-500 dark:hover:text-red-400 rounded-lg transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>

                {/* Delete confirmation */}
                {isDeleting && (
                  <div className="px-4 pb-3">
                    <div className="flex items-center gap-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                      <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
                      <p className="text-sm text-red-700 dark:text-red-300 flex-1">
                        {t('saved_simulations.delete_confirm') || 'Delete this simulation? This cannot be undone.'}
                      </p>
                      <button
                        onClick={() => handleDelete(sim)}
                        disabled={deleteMutation.isPending}
                        className="px-3 py-1 text-xs font-medium bg-red-600 text-white rounded hover:bg-red-700 transition-colors disabled:opacity-50"
                      >
                        {deleteMutation.isPending ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          t('saved_simulations.confirm_delete') || 'Delete'
                        )}
                      </button>
                      <button
                        onClick={() => setDeleteConfirmId(null)}
                        className="px-3 py-1 text-xs font-medium text-gray-600 dark:text-slate-300 bg-gray-100 dark:bg-slate-700 rounded hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
                      >
                        {t('saved_simulations.cancel') || 'Cancel'}
                      </button>
                    </div>
                  </div>
                )}

                {/* Expanded detail */}
                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-gray-100 dark:border-slate-700">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
                      {/* Interventions list */}
                      <div>
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                          <Beaker className="w-4 h-4 text-gray-400" />
                          {t('saved_simulations.interventions_list') || 'Interventions'} ({interventions.length})
                        </h4>
                        {interventions.length > 0 ? (
                          <div className="space-y-2">
                            {interventions.map((intv, idx) => (
                              <div
                                key={idx}
                                className="flex items-center gap-2 p-2 rounded-lg bg-gray-50 dark:bg-slate-700/50 text-sm"
                              >
                                <span className="font-medium text-gray-700 dark:text-slate-300">
                                  {(intv.intervention_type as string) ?? 'N/A'}
                                </span>
                                {intv.target_pollutant != null && (
                                  <span className="px-1.5 py-0.5 text-xs rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300">
                                    {String(intv.target_pollutant).toUpperCase()}
                                  </span>
                                )}
                                {intv.estimated_cost != null && (intv.estimated_cost as number) > 0 && (
                                  <span className="ml-auto text-xs text-gray-500 dark:text-slate-400">
                                    {formatCHF(intv.estimated_cost as number)}
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-gray-400 dark:text-slate-500">
                            {t('saved_simulations.no_interventions') || 'No interventions data available'}
                          </p>
                        )}
                      </div>

                      {/* Before/after metrics & recommendations */}
                      <div className="space-y-4">
                        {/* Metrics */}
                        {sim.results_json && (
                          <div>
                            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                              <BarChart3 className="w-4 h-4 text-gray-400" />
                              {t('saved_simulations.before_after') || 'Before / After'}
                            </h4>
                            <SimulationMetrics sim={sim} />
                          </div>
                        )}

                        {/* Recommendations */}
                        {getRecommendations(sim).length > 0 && (
                          <div>
                            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                              <Award className="w-4 h-4 text-gray-400" />
                              {t('saved_simulations.recommendations') || 'Recommendations'}
                            </h4>
                            <ul className="space-y-1">
                              {getRecommendations(sim).map((rec, idx) => (
                                <li
                                  key={idx}
                                  className="flex items-start gap-2 text-xs text-gray-600 dark:text-slate-300"
                                >
                                  <CheckCircle2 className="w-3 h-3 text-green-500 flex-shrink-0 mt-0.5" />
                                  {rec}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Load button */}
                    <div className="mt-4 pt-4 border-t border-gray-100 dark:border-slate-700 flex justify-end">
                      <button
                        onClick={() => handleLoadInSimulator(sim)}
                        className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        <Play className="w-4 h-4" />
                        {t('saved_simulations.load_in_simulator') || 'Load in Simulator'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Comparison panel */}
      {compareMode && compareSimulations.length >= 2 && (
        <ComparisonPanel simulations={compareSimulations} buildingMap={buildingMap} />
      )}
    </div>
  );
}

// ── Simulation Metrics Sub-component ──────────────────────────────

function SimulationMetrics({ sim }: { sim: SavedSimulation }) {
  const { t } = useTranslation();
  const results = sim.results_json as Record<string, unknown> | null;
  if (!results) return null;

  const current = results.current_state as Record<string, unknown> | undefined;
  const projected = results.projected_state as Record<string, unknown> | undefined;
  if (!current || !projected) return null;

  const metrics = [
    {
      label: t('saved_simulations.metric_grade') || 'Grade',
      before: current.passport_grade as string,
      after: projected.passport_grade as string,
      isGrade: true,
    },
    {
      label: t('saved_simulations.metric_trust') || 'Trust',
      before: `${((current.trust_score as number) * 100).toFixed(0)}%`,
      after: `${((projected.trust_score as number) * 100).toFixed(0)}%`,
      delta: (projected.trust_score as number) - (current.trust_score as number),
    },
    {
      label: t('saved_simulations.metric_completeness') || 'Completeness',
      before: `${((current.completeness_score as number) * 100).toFixed(0)}%`,
      after: `${((projected.completeness_score as number) * 100).toFixed(0)}%`,
      delta: (projected.completeness_score as number) - (current.completeness_score as number),
    },
    {
      label: t('saved_simulations.metric_blockers') || 'Blockers',
      before: String(current.blocker_count ?? 0),
      after: String(projected.blocker_count ?? 0),
      delta: ((projected.blocker_count as number) ?? 0) - ((current.blocker_count as number) ?? 0),
      invertColor: true,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-2">
      {metrics.map((m) => (
        <div key={m.label} className="p-2 rounded-lg bg-gray-50 dark:bg-slate-700/50">
          <p className="text-[10px] uppercase tracking-wide text-gray-400 dark:text-slate-500 mb-1">{m.label}</p>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-500 dark:text-slate-400">{m.before}</span>
            <ArrowRight className="w-3 h-3 text-gray-300 dark:text-slate-600" />
            {m.isGrade ? (
              <span className={cn('text-xs font-bold', gradeColor(m.after))}>{m.after}</span>
            ) : (
              <span className="text-xs font-semibold text-gray-900 dark:text-white">{m.after}</span>
            )}
            {m.delta !== undefined && (
              <span
                className={cn(
                  'text-[10px] ml-auto',
                  m.invertColor
                    ? m.delta < 0
                      ? 'text-green-500'
                      : m.delta > 0
                        ? 'text-red-500'
                        : 'text-gray-400'
                    : m.delta > 0
                      ? 'text-green-500'
                      : m.delta < 0
                        ? 'text-red-500'
                        : 'text-gray-400',
                )}
              >
                {m.delta > 0 ? '+' : ''}
                {(m.delta * (m.label.includes('%') || !m.invertColor ? 100 : 1)).toFixed(m.invertColor ? 0 : 1)}
                {!m.invertColor ? '%' : ''}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Comparison Panel ──────────────────────────────────────────────

function ComparisonPanel({
  simulations,
}: {
  simulations: SimulationWithBuilding[];
  buildingMap: Map<string, Building>;
}) {
  const { t } = useTranslation();

  // Find the best scenario
  const bestId = useMemo(() => {
    let best = simulations[0];
    for (const s of simulations) {
      const sGrade = GRADE_ORDER[getProjectedGrade(s) ?? ''] ?? 0;
      const bGrade = GRADE_ORDER[getProjectedGrade(best) ?? ''] ?? 0;
      if (sGrade > bGrade) best = s;
      else if (sGrade === bGrade && (getTrustDelta(s) ?? 0) > (getTrustDelta(best) ?? 0)) best = s;
    }
    return best.id;
  }, [simulations]);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-indigo-500" />
        {t('saved_simulations.comparison_title') || 'Simulation Comparison'}
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-slate-700">
              <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">
                {t('saved_simulations.metric') || 'Metric'}
              </th>
              {simulations.map((sim) => (
                <th
                  key={sim.id}
                  className={cn(
                    'text-center py-2 px-3 text-xs font-medium uppercase',
                    sim.id === bestId ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-500 dark:text-slate-400',
                  )}
                >
                  <div className="flex flex-col items-center gap-1">
                    <span className="truncate max-w-[150px]">{sim.title}</span>
                    {sim.id === bestId && (
                      <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 font-semibold">
                        {t('saved_simulations.best') || 'Best'}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* Grade */}
            <tr className="border-b border-gray-100 dark:border-slate-700/50">
              <td className="py-3 pr-4 text-gray-600 dark:text-slate-300 font-medium">
                {t('saved_simulations.compare_grade') || 'Projected Grade'}
              </td>
              {simulations.map((sim) => {
                const grade = getProjectedGrade(sim);
                const current = getCurrentGrade(sim);
                return (
                  <td key={sim.id} className="py-3 px-3 text-center">
                    <div className="flex items-center justify-center gap-1.5">
                      {current && (
                        <>
                          <span className={cn('font-bold', gradeColor(current))}>{current}</span>
                          <ArrowRight className="w-3 h-3 text-gray-400" />
                        </>
                      )}
                      <span className={cn('text-lg font-black', gradeColor(grade))}>{grade ?? '-'}</span>
                    </div>
                  </td>
                );
              })}
            </tr>

            {/* Cost */}
            <tr className="border-b border-gray-100 dark:border-slate-700/50">
              <td className="py-3 pr-4 text-gray-600 dark:text-slate-300 font-medium">
                {t('saved_simulations.compare_cost') || 'Total Cost'}
              </td>
              {simulations.map((sim) => (
                <td key={sim.id} className="py-3 px-3 text-center text-gray-900 dark:text-white">
                  {sim.total_cost_chf != null ? formatCHF(sim.total_cost_chf) : '-'}
                </td>
              ))}
            </tr>

            {/* Trust delta */}
            <tr className="border-b border-gray-100 dark:border-slate-700/50">
              <td className="py-3 pr-4 text-gray-600 dark:text-slate-300 font-medium">
                {t('saved_simulations.compare_trust') || 'Trust Change'}
              </td>
              {simulations.map((sim) => {
                const delta = getTrustDelta(sim);
                return (
                  <td key={sim.id} className="py-3 px-3 text-center">
                    {delta != null ? (
                      <span
                        className={cn(
                          'font-medium',
                          delta > 0
                            ? 'text-green-600 dark:text-green-400'
                            : delta < 0
                              ? 'text-red-600 dark:text-red-400'
                              : 'text-gray-500',
                        )}
                      >
                        {delta > 0 ? '+' : ''}
                        {(delta * 100).toFixed(1)}%
                      </span>
                    ) : (
                      '-'
                    )}
                  </td>
                );
              })}
            </tr>

            {/* Duration */}
            <tr className="border-b border-gray-100 dark:border-slate-700/50">
              <td className="py-3 pr-4 text-gray-600 dark:text-slate-300 font-medium">
                {t('saved_simulations.compare_duration') || 'Duration'}
              </td>
              {simulations.map((sim) => (
                <td key={sim.id} className="py-3 px-3 text-center text-gray-900 dark:text-white">
                  {sim.total_duration_weeks != null
                    ? `${sim.total_duration_weeks} ${t('saved_simulations.weeks') || 'wks'}`
                    : '-'}
                </td>
              ))}
            </tr>

            {/* Interventions count */}
            <tr>
              <td className="py-3 pr-4 text-gray-600 dark:text-slate-300 font-medium">
                {t('saved_simulations.compare_interventions') || 'Interventions'}
              </td>
              {simulations.map((sim) => (
                <td key={sim.id} className="py-3 px-3 text-center text-gray-900 dark:text-white">
                  {getInterventions(sim).length}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
