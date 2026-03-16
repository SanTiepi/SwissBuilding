import { useState, useMemo, useCallback, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { buildingsApi } from '@/api/buildings';
import { buildingComparisonApi } from '@/api/buildingComparison';
import type { BuildingComparison, BuildingComparisonEntry } from '@/api/buildingComparison';
import { useTranslation } from '@/i18n';
import { AlertTriangle, BarChart3, Loader2, X, ChevronUp, ChevronDown, SlidersHorizontal } from 'lucide-react';
import { TrustBadge } from '@/components/TrustBadge';
import { formatDistanceToNow } from 'date-fns';
import type { Building } from '@/types';

const MIN_BUILDINGS = 2;
const MAX_BUILDINGS = 10;

const READINESS_GATES = ['safe_to_start', 'safe_to_tender', 'safe_to_reopen', 'safe_to_requalify'] as const;

type DimensionKey =
  | 'passport_grade'
  | 'trust_score'
  | 'completeness_score'
  | 'open_actions_count'
  | 'open_unknowns_count'
  | 'contradictions_count'
  | 'diagnostic_count'
  | 'readiness_gates'
  | 'last_diagnostic_date';

interface DimensionDef {
  key: DimensionKey;
  labelKey: string;
  sortable: boolean;
  best: 'max' | 'min' | 'none';
  getValue: (b: BuildingComparisonEntry) => number | null;
}

function countReadyGates(summary: Record<string, boolean> | null | undefined): number {
  if (!summary) return 0;
  return READINESS_GATES.filter((g) => summary[g]).length;
}

const ALL_DIMENSIONS: DimensionDef[] = [
  {
    key: 'passport_grade',
    labelKey: 'comparison.passport_grade',
    sortable: true,
    best: 'none',
    getValue: (b) => {
      if (b.passport_grade == null) return null;
      const grades: Record<string, number> = { A: 6, B: 5, C: 4, D: 3, E: 2, F: 1 };
      return grades[b.passport_grade] ?? null;
    },
  },
  {
    key: 'trust_score',
    labelKey: 'comparison.trust_score',
    sortable: true,
    best: 'max',
    getValue: (b) => b.trust_score,
  },
  {
    key: 'completeness_score',
    labelKey: 'comparison.completeness_score',
    sortable: true,
    best: 'max',
    getValue: (b) => b.completeness_score,
  },
  {
    key: 'open_actions_count',
    labelKey: 'comparison.open_actions',
    sortable: true,
    best: 'min',
    getValue: (b) => b.open_actions_count,
  },
  {
    key: 'open_unknowns_count',
    labelKey: 'comparison.open_unknowns',
    sortable: true,
    best: 'min',
    getValue: (b) => b.open_unknowns_count,
  },
  {
    key: 'contradictions_count',
    labelKey: 'comparison.contradictions',
    sortable: true,
    best: 'min',
    getValue: (b) => b.contradictions_count,
  },
  {
    key: 'diagnostic_count',
    labelKey: 'comparison.diagnostics',
    sortable: true,
    best: 'max',
    getValue: (b) => b.diagnostic_count,
  },
  {
    key: 'readiness_gates',
    labelKey: 'comparison.readiness_gates',
    sortable: true,
    best: 'max',
    getValue: (b) => countReadyGates(b.readiness_summary),
  },
  {
    key: 'last_diagnostic_date',
    labelKey: 'comparison.last_diagnostic',
    sortable: true,
    best: 'max',
    getValue: (b) => (b.last_diagnostic_date ? new Date(b.last_diagnostic_date).getTime() : null),
  },
];

const STORAGE_KEY = 'comparison-visible-dims';

function loadVisibleDimensions(): Set<DimensionKey> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const arr = JSON.parse(raw) as DimensionKey[];
      if (Array.isArray(arr) && arr.length > 0) return new Set(arr);
    }
  } catch {
    /* ignore */
  }
  return new Set(ALL_DIMENSIONS.map((d) => d.key));
}

function formatCellValue(dim: DimensionDef, b: BuildingComparisonEntry): string {
  switch (dim.key) {
    case 'passport_grade':
      return b.passport_grade ?? '-';
    case 'trust_score':
      return ''; // rendered as TrustBadge
    case 'completeness_score':
      return b.completeness_score != null ? `${Math.round(b.completeness_score * 100)}%` : '-';
    case 'open_actions_count':
      return String(b.open_actions_count ?? 0);
    case 'open_unknowns_count':
      return String(b.open_unknowns_count ?? 0);
    case 'contradictions_count':
      return String(b.contradictions_count ?? 0);
    case 'diagnostic_count':
      return String(b.diagnostic_count ?? 0);
    case 'readiness_gates':
      return ''; // rendered as custom component
    case 'last_diagnostic_date':
      return ''; // rendered as custom component
    default:
      return '-';
  }
}

function getCellColor(dim: DimensionDef, b: BuildingComparisonEntry, buildings: BuildingComparisonEntry[]): string {
  if (dim.best === 'none') return '';
  const val = dim.getValue(b);
  if (val == null) return '';

  const values = buildings.map((x) => dim.getValue(x)).filter((v): v is number => v != null);
  if (values.length < 2) return '';

  const best = dim.best === 'max' ? Math.max(...values) : Math.min(...values);
  const worst = dim.best === 'max' ? Math.min(...values) : Math.max(...values);

  if (val === best) return 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200';
  if (val === worst) return 'bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-200';
  return 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200';
}

type SortDir = 'asc' | 'desc';

function ReadinessGatesCell({
  summary,
  t,
}: {
  summary: Record<string, boolean> | null | undefined;
  t: (key: string) => string;
}) {
  const ready = countReadyGates(summary);
  const total = READINESS_GATES.length;

  const color =
    ready === total
      ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300'
      : ready >= 2
        ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300'
        : 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300';

  const tooltipLines = READINESS_GATES.map((g) => {
    const isReady = summary?.[g] ?? false;
    const label = t(`comparison.gate_${g}`);
    return `${isReady ? '\u2713' : '\u2717'} ${label}`;
  }).join('\n');

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${color}`}
      title={tooltipLines}
    >
      {ready}/{total}
    </span>
  );
}

function LastDiagnosticCell({ date, t }: { date: string | null; t: (key: string) => string }) {
  if (!date) {
    return <span className="text-gray-400 dark:text-gray-500 text-xs">{t('comparison.no_diagnostic')}</span>;
  }
  return (
    <span className="text-xs" title={new Date(date).toLocaleDateString()}>
      {formatDistanceToNow(new Date(date), { addSuffix: true })}
    </span>
  );
}

export default function BuildingComparisonPage() {
  const { t } = useTranslation();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [result, setResult] = useState<BuildingComparison | null>(null);
  const [sortKey, setSortKey] = useState<DimensionKey | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [visibleDims, setVisibleDims] = useState<Set<DimensionKey>>(loadVisibleDimensions);
  const [showDimSelector, setShowDimSelector] = useState(false);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...visibleDims]));
  }, [visibleDims]);

  const {
    data: buildingsList,
    isLoading: loadingBuildings,
    isError: buildingsError,
  } = useQuery({
    queryKey: ['buildings', 'all-for-comparison'],
    queryFn: () => buildingsApi.list({ size: 200 }),
  });

  const compareMutation = useMutation({
    mutationFn: (ids: string[]) => buildingComparisonApi.compare(ids),
    onSuccess: (data) => setResult(data),
  });

  const availableBuildings = useMemo(() => {
    if (!buildingsList?.items) return [];
    return buildingsList.items;
  }, [buildingsList]);

  const toggleBuilding = (id: string) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= MAX_BUILDINGS) return prev;
      return [...prev, id];
    });
  };

  const removeBuilding = (id: string) => {
    setSelectedIds((prev) => prev.filter((x) => x !== id));
  };

  const canCompare = selectedIds.length >= MIN_BUILDINGS && selectedIds.length <= MAX_BUILDINGS;

  const handleCompare = () => {
    if (canCompare) {
      compareMutation.mutate(selectedIds);
    }
  };

  const handleSort = useCallback(
    (key: DimensionKey) => {
      if (sortKey === key) {
        setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortKey(key);
        setSortDir('desc');
      }
    },
    [sortKey],
  );

  const toggleDimension = useCallback((key: DimensionKey) => {
    setVisibleDims((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size <= 1) return prev; // keep at least 1
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }, []);

  const activeDimensions = useMemo(() => ALL_DIMENSIONS.filter((d) => visibleDims.has(d.key)), [visibleDims]);

  const sortedBuildings = useMemo(() => {
    if (!result) return [];
    if (!sortKey) return result.buildings;

    const dim = ALL_DIMENSIONS.find((d) => d.key === sortKey);
    if (!dim) return result.buildings;

    const sorted = [...result.buildings].sort((a, b) => {
      const va = dim.getValue(a);
      const vb = dim.getValue(b);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      return sortDir === 'asc' ? va - vb : vb - va;
    });
    return sorted;
  }, [result, sortKey, sortDir]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <BarChart3 className="w-7 h-7 text-red-600 dark:text-red-400" />
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('comparison.title')}</h1>
      </div>

      {/* Building selector */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          {t('comparison.select_buildings')}
        </h2>

        {/* Selected chips */}
        {selectedIds.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {selectedIds.map((id) => {
              const b = availableBuildings.find((x: Building) => x.id === id);
              return (
                <span
                  key={id}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-200 rounded-full text-sm"
                >
                  {b?.address || id}
                  <button
                    onClick={() => removeBuilding(id)}
                    className="ml-1 hover:text-red-600 dark:hover:text-red-300"
                    aria-label={`Remove ${b?.address || id}`}
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </span>
              );
            })}
          </div>
        )}

        {/* Building list */}
        {loadingBuildings ? (
          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 py-4">
            <Loader2 className="w-4 h-4 animate-spin" />
            {t('comparison.loading')}
          </div>
        ) : buildingsError ? (
          <div className="flex items-center gap-2 text-red-600 dark:text-red-400 py-4">
            <AlertTriangle className="w-4 h-4" />
            {t('app.error')}
          </div>
        ) : availableBuildings.length === 0 ? (
          <div className="py-4 text-sm text-gray-500 dark:text-gray-400">{t('form.no_results')}</div>
        ) : (
          <div className="max-h-60 overflow-y-auto border border-gray-200 dark:border-gray-600 rounded-lg">
            {availableBuildings.map((b: Building) => (
              <label
                key={b.id}
                className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-100 dark:border-gray-700 last:border-b-0"
              >
                <input
                  type="checkbox"
                  checked={selectedIds.includes(b.id)}
                  onChange={() => toggleBuilding(b.id)}
                  disabled={!selectedIds.includes(b.id) && selectedIds.length >= MAX_BUILDINGS}
                  className="rounded border-gray-300 dark:border-gray-600 text-red-600 focus:ring-red-500"
                />
                <span className="text-sm text-gray-900 dark:text-gray-100">{b.address}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto">{b.postal_code}</span>
              </label>
            ))}
          </div>
        )}

        {/* Hint + Compare button */}
        <div className="flex items-center justify-between mt-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {selectedIds.length < MIN_BUILDINGS
              ? t('comparison.min_buildings')
              : selectedIds.length >= MAX_BUILDINGS
                ? t('comparison.max_buildings')
                : `${selectedIds.length} / ${MAX_BUILDINGS}`}
          </p>
          <button
            onClick={handleCompare}
            disabled={!canCompare || compareMutation.isPending}
            className="px-5 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {compareMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            {t('comparison.compare_button')}
          </button>
        </div>
      </div>

      {/* Error */}
      {compareMutation.isError && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
          <AlertTriangle className="w-6 h-6 text-red-400 mx-auto mb-2" />
          <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Summary bar */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <SummaryCard label={t('comparison.best_passport')} value={result.best_passport || '-'} accent="green" />
            <SummaryCard label={t('comparison.worst_passport')} value={result.worst_passport || '-'} accent="red" />
            <SummaryCard
              label={t('comparison.average_trust')}
              value={`${Math.round(result.average_trust * 100)}%`}
              accent="blue"
            />
            <SummaryCard
              label={t('comparison.average_completeness')}
              value={`${Math.round(result.average_completeness * 100)}%`}
              accent="blue"
            />
          </div>

          {/* Dimension selector */}
          <div className="relative">
            <button
              onClick={() => setShowDimSelector((prev) => !prev)}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <SlidersHorizontal className="w-4 h-4" />
              {t('comparison.show_hide_columns')}
              <span className="text-xs text-gray-400 dark:text-gray-500">
                ({visibleDims.size}/{ALL_DIMENSIONS.length})
              </span>
            </button>
            {showDimSelector && (
              <div className="absolute z-20 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 min-w-[240px]">
                {ALL_DIMENSIONS.map((dim) => (
                  <label
                    key={dim.key}
                    className="flex items-center gap-2 px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-700 rounded cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={visibleDims.has(dim.key)}
                      onChange={() => toggleDimension(dim.key)}
                      className="rounded border-gray-300 dark:border-gray-600 text-red-600 focus:ring-red-500"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">{t(dim.labelKey)}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Comparison table — desktop */}
          <div className="hidden md:block bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
                    <th className="text-left px-4 py-3 font-semibold text-gray-700 dark:text-gray-300 sticky left-0 bg-gray-50 dark:bg-gray-900/50 z-10 min-w-[160px]">
                      &nbsp;
                    </th>
                    {sortedBuildings.map((b) => (
                      <th
                        key={b.building_id}
                        className="text-center px-4 py-3 font-semibold text-gray-700 dark:text-gray-300 min-w-[140px]"
                      >
                        <div className="truncate max-w-[180px]">{b.building_name || b.address}</div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {activeDimensions.map((dim) => (
                    <tr key={dim.key} className="border-b border-gray-100 dark:border-gray-700 last:border-b-0">
                      <td className="px-4 py-3 font-medium text-gray-700 dark:text-gray-300 sticky left-0 bg-white dark:bg-gray-800 z-10">
                        {dim.sortable ? (
                          <button
                            onClick={() => handleSort(dim.key)}
                            className="flex items-center gap-1 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                            title={
                              sortKey === dim.key && sortDir === 'asc'
                                ? t('comparison.sort_desc')
                                : t('comparison.sort_asc')
                            }
                          >
                            {t(dim.labelKey)}
                            {sortKey === dim.key ? (
                              sortDir === 'asc' ? (
                                <ChevronUp className="w-3.5 h-3.5 text-red-600 dark:text-red-400" />
                              ) : (
                                <ChevronDown className="w-3.5 h-3.5 text-red-600 dark:text-red-400" />
                              )
                            ) : (
                              <span className="w-3.5 h-3.5 opacity-0 group-hover:opacity-30">
                                <ChevronDown className="w-3.5 h-3.5" />
                              </span>
                            )}
                          </button>
                        ) : (
                          t(dim.labelKey)
                        )}
                      </td>
                      {sortedBuildings.map((b) => (
                        <td
                          key={b.building_id}
                          className={`px-4 py-3 text-center font-mono ${getCellColor(dim, b, result.buildings)}`}
                        >
                          <CellRenderer dim={dim} building={b} t={t} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Comparison cards — mobile */}
          <div className="md:hidden space-y-4" data-testid="comparison-mobile-cards">
            {sortedBuildings.map((b) => (
              <MobileComparisonCard
                key={b.building_id}
                building={b}
                dimensions={activeDimensions}
                allBuildings={result.buildings}
                t={t}
              />
            ))}
          </div>
        </>
      )}

      {/* No results hint */}
      {!result && !compareMutation.isPending && !buildingsError && (
        <div className="text-center py-12 text-gray-400 dark:text-gray-500">
          <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>{t('comparison.no_results')}</p>
        </div>
      )}
    </div>
  );
}

function CellRenderer({
  dim,
  building,
  t,
}: {
  dim: DimensionDef;
  building: BuildingComparisonEntry;
  t: (key: string) => string;
}) {
  if (dim.key === 'trust_score') {
    return <TrustBadge score={building.trust_score} size="sm" />;
  }
  if (dim.key === 'readiness_gates') {
    return <ReadinessGatesCell summary={building.readiness_summary} t={t} />;
  }
  if (dim.key === 'last_diagnostic_date') {
    return <LastDiagnosticCell date={building.last_diagnostic_date} t={t} />;
  }
  return <>{formatCellValue(dim, building)}</>;
}

function MobileComparisonCard({
  building,
  dimensions,
  allBuildings,
  t,
}: {
  building: BuildingComparisonEntry;
  dimensions: DimensionDef[];
  allBuildings: BuildingComparisonEntry[];
  t: (key: string) => string;
}) {
  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
      data-testid="comparison-mobile-card"
    >
      <div className="px-4 py-3 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
        <h3 className="font-semibold text-gray-900 dark:text-white text-sm truncate">
          {building.building_name || building.address}
        </h3>
        {building.building_name && (
          <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">{building.address}</p>
        )}
      </div>
      <div className="divide-y divide-gray-100 dark:divide-gray-700">
        {dimensions.map((dim) => (
          <div
            key={dim.key}
            className={`flex items-center justify-between px-4 py-2.5 ${getCellColor(dim, building, allBuildings)}`}
          >
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{t(dim.labelKey)}</span>
            <span className="text-sm font-mono text-gray-900 dark:text-gray-100">
              <CellRenderer dim={dim} building={building} t={t} />
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SummaryCard({ label, value, accent }: { label: string; value: string; accent: 'green' | 'red' | 'blue' }) {
  const colors = {
    green: 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800 text-green-700 dark:text-green-300',
    red: 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300',
    blue: 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300',
  };

  return (
    <div className={`rounded-xl border p-4 ${colors[accent]}`}>
      <p className="text-xs font-medium opacity-80">{label}</p>
      <p className="text-xl font-bold mt-1">{value}</p>
    </div>
  );
}
