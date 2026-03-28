/**
 * MIGRATION: ABSORB INTO PortfolioCommand
 * This page will be absorbed into the PortfolioCommand master workspace as the buildings list view.
 * Per ADR-005 and V3 migration plan.
 * New features should target the master workspace directly.
 */
import { useState, useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useQueryClient, useQuery } from '@tanstack/react-query';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useBuildings, useCreateBuilding } from '@/hooks/useBuildings';
import { buildingsApi } from '@/api/buildings';
import { OnboardingWizard } from '@/components/OnboardingWizard';
import { buildingDashboardApi } from '@/api/buildingDashboard';
import { useAuth } from '@/hooks/useAuth';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { SWISS_CANTONS, BUILDING_TYPES } from '@/utils/constants';
import { DataTable } from '@/components/DataTable';
import { BuildingCard } from '@/components/BuildingCard';
import { RoleGate } from '@/components/RoleGate';
import { TrustBadge } from '@/components/TrustBadge';
import { ReadinessBadge } from '@/components/ReadinessBadge';
import type { Building } from '@/types';
import {
  Plus,
  Search,
  LayoutGrid,
  List,
  X,
  Loader2,
  Building2,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Clock,
  Filter,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';

function getDataFreshness(updatedAt: string): { label: string; color: string; darkColor: string } {
  const now = new Date();
  const updated = new Date(updatedAt);
  const diffDays = Math.floor((now.getTime() - updated.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays <= 7)
    return {
      label: '< 7d',
      color: 'bg-green-100 text-green-700',
      darkColor: 'dark:bg-green-900/40 dark:text-green-300',
    };
  if (diffDays <= 30)
    return {
      label: '< 30d',
      color: 'bg-yellow-100 text-yellow-700',
      darkColor: 'dark:bg-yellow-900/40 dark:text-yellow-300',
    };
  if (diffDays <= 90)
    return {
      label: '< 90d',
      color: 'bg-orange-100 text-orange-700',
      darkColor: 'dark:bg-orange-900/40 dark:text-orange-300',
    };
  return { label: '> 90d', color: 'bg-red-100 text-red-700', darkColor: 'dark:bg-red-900/40 dark:text-red-300' };
}

const currentYear = new Date().getFullYear();

const buildingSchema = z.object({
  address: z.string().min(1, 'Address is required'),
  city: z.string().min(1, 'City is required'),
  canton: z.string().min(1, 'Canton is required'),
  postal_code: z
    .string()
    .min(1, 'Postal code is required')
    .regex(/^\d{4}$/, 'Postal code must be exactly 4 digits'),
  construction_year: z.coerce
    .number()
    .min(1800, 'Year must be 1800 or later')
    .max(currentYear, `Year must be ${currentYear} or earlier`),
  building_type: z.string().min(1, 'Building type is required'),
  floors_above: z.coerce.number().min(0).optional().or(z.literal('')),
  floors_below: z.coerce.number().min(0).optional().or(z.literal('')),
  surface_area_m2: z.coerce.number().min(1).optional().or(z.literal('')),
  egid: z.coerce.number().int().positive().optional().or(z.literal('')),
  egrid: z.string().optional(),
  official_id: z.string().optional(),
});

type BuildingFormData = z.infer<typeof buildingSchema>;

function useBuildingDashboard(buildingId: string) {
  return useQuery({
    queryKey: ['building-dashboard', buildingId],
    queryFn: () => buildingDashboardApi.get(buildingId),
    staleTime: 60_000,
    enabled: !!buildingId,
  });
}

function BuildingTrustCell({ buildingId }: { buildingId: string }) {
  const { data, isLoading } = useBuildingDashboard(buildingId);
  if (isLoading) return <span className="inline-block w-12 h-4 bg-slate-200 dark:bg-slate-600 rounded animate-pulse" />;
  return <TrustBadge score={data?.trust.score ?? null} trend={data?.trust.trend} />;
}

function BuildingReadinessCell({ buildingId }: { buildingId: string }) {
  const { data, isLoading } = useBuildingDashboard(buildingId);
  if (isLoading) return <span className="inline-block w-16 h-4 bg-slate-200 dark:bg-slate-600 rounded animate-pulse" />;
  return (
    <ReadinessBadge status={data?.readiness.overall_status ?? null} blockedCount={data?.readiness.blocked_count} />
  );
}

function BuildingCardDashboardBadges({ buildingId }: { buildingId: string }) {
  const { data, isLoading } = useBuildingDashboard(buildingId);
  if (isLoading) {
    return (
      <div className="flex items-center gap-2">
        <span className="inline-block w-12 h-4 bg-slate-200 dark:bg-slate-600 rounded animate-pulse" />
        <span className="inline-block w-16 h-4 bg-slate-200 dark:bg-slate-600 rounded animate-pulse" />
      </div>
    );
  }
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <TrustBadge score={data?.trust.score ?? null} trend={data?.trust.trend} />
      <ReadinessBadge status={data?.readiness.overall_status ?? null} blockedCount={data?.readiness.blocked_count} />
    </div>
  );
}

const PORTFOLIO_FILTER_KEYS = ['readiness', 'risk', 'grade', 'trust', 'canton'] as const;
type PortfolioFilterKey = (typeof PORTFOLIO_FILTER_KEYS)[number];

function usePortfolioFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const activeFilters = useMemo(() => {
    const filters: Partial<Record<PortfolioFilterKey, string>> = {};
    for (const key of PORTFOLIO_FILTER_KEYS) {
      const val = searchParams.get(key);
      if (val) filters[key] = val;
    }
    return filters;
  }, [searchParams]);

  const clearFilter = useCallback(
    (key: PortfolioFilterKey) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.delete(key);
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const clearAllFilters = useCallback(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        for (const key of PORTFOLIO_FILTER_KEYS) next.delete(key);
        return next;
      },
      { replace: true },
    );
  }, [setSearchParams]);

  const hasPortfolioFilters = Object.keys(activeFilters).length > 0;

  return { activeFilters, clearFilter, clearAllFilters, hasPortfolioFilters };
}

export default function BuildingsList() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  useAuth();
  const { data: buildingsData, isLoading, isError } = useBuildings();
  const createBuilding = useCreateBuilding();
  const queryClient = useQueryClient();
  const { activeFilters, clearFilter, clearAllFilters, hasPortfolioFilters } = usePortfolioFilters();

  const handlePrefetch = useCallback(
    (id: string) => {
      queryClient.prefetchQuery({
        queryKey: ['buildings', id],
        queryFn: () => buildingsApi.get(id),
        staleTime: 30_000,
      });
    },
    [queryClient],
  );

  const buildings: Building[] = useMemo(() => buildingsData?.items ?? [], [buildingsData]);

  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showOnboardingWizard, setShowOnboardingWizard] = useState(false);
  const [editingBuilding, setEditingBuilding] = useState<Building | null>(null);
  const [showAdvancedFields, setShowAdvancedFields] = useState(false);
  const [formSuccess, setFormSuccess] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 12;

  // Filters
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search, 300);
  const [filterCanton, setFilterCanton] = useState('');
  const [filterType, setFilterType] = useState('');
  const [yearFrom, setYearFrom] = useState('');
  const [yearTo, setYearTo] = useState('');

  const filtered = useMemo(() => {
    if (!Array.isArray(buildings)) return [];
    return buildings.filter((b: Building) => {
      if (debouncedSearch) {
        const q = debouncedSearch.toLowerCase();
        const match =
          b.address?.toLowerCase().includes(q) ||
          b.city?.toLowerCase().includes(q) ||
          b.egrid?.toLowerCase().includes(q);
        if (!match) return false;
      }
      // Local filters
      if (filterCanton && b.canton !== filterCanton) return false;
      if (filterType && b.building_type !== filterType) return false;
      if (yearFrom && (b.construction_year == null || b.construction_year < parseInt(yearFrom))) return false;
      if (yearTo && (b.construction_year == null || b.construction_year > parseInt(yearTo))) return false;
      // Portfolio URL param filters (applied where data is available on the building object)
      if (activeFilters.risk && b.risk_scores?.overall_risk_level !== activeFilters.risk) return false;
      if (activeFilters.canton && b.canton !== activeFilters.canton) return false;
      return true;
    });
  }, [buildings, debouncedSearch, filterCanton, filterType, yearFrom, yearTo, activeFilters]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const paged = filtered.slice((page - 1) * pageSize, page * pageSize);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<BuildingFormData>({
    resolver: zodResolver(buildingSchema),
  });

  const openCreateModal = useCallback(() => {
    setEditingBuilding(null);
    setFormSuccess(false);
    setFormError(null);
    reset({});
    setShowCreateModal(true);
  }, [reset]);

  const openEditModal = useCallback(
    (building: Building) => {
      setEditingBuilding(building);
      setFormSuccess(false);
      setFormError(null);
      setShowAdvancedFields(true);
      reset({
        address: building.address,
        city: building.city,
        canton: building.canton,
        postal_code: building.postal_code,
        construction_year: building.construction_year ?? undefined,
        building_type: building.building_type,
        floors_above: building.floors_above ?? undefined,
        floors_below: building.floors_below ?? undefined,
        surface_area_m2: building.surface_area_m2 ?? undefined,
        egid: building.egid ?? undefined,
        egrid: building.egrid ?? undefined,
        official_id: building.official_id ?? undefined,
      });
      setShowCreateModal(true);
    },
    [reset],
  );
  // openEditModal is exposed for future row-level edit actions
  void openEditModal;

  const closeModal = useCallback(() => {
    setShowCreateModal(false);
    setEditingBuilding(null);
    setFormSuccess(false);
    setFormError(null);
    reset({});
  }, [reset]);

  const onFormSubmit = async (data: BuildingFormData) => {
    setFormError(null);
    setFormSuccess(false);
    // Clean optional numeric fields: convert empty strings to undefined
    const cleaned: Record<string, unknown> = { ...data };
    for (const key of ['floors_above', 'floors_below', 'surface_area_m2', 'egid'] as const) {
      if (cleaned[key] === '' || cleaned[key] === undefined) {
        delete cleaned[key];
      }
    }
    try {
      await createBuilding.mutateAsync(cleaned as Partial<Building>);
      setFormSuccess(true);
      setTimeout(() => {
        closeModal();
      }, 1200);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setFormError(e?.response?.data?.detail || e?.message || 'An unexpected error occurred');
    }
  };

  const tableColumns = [
    { key: 'address', header: t('building.address'), sortable: true },
    { key: 'city', header: t('building.city'), sortable: true },
    { key: 'canton', header: t('building.canton'), sortable: true },
    { key: 'construction_year', header: t('building.construction_year'), sortable: true },
    {
      key: 'building_type',
      header: t('building.building_type'),
      sortable: true,
      render: (row: Building) => (
        <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 rounded-full">
          {t(`building_type.${row.building_type}`) || row.building_type}
        </span>
      ),
    },
    {
      key: 'risk_level',
      header: t('building.risk_score'),
      sortable: true,
      render: (row: Building) => {
        const val = row.risk_scores?.overall_risk_level;
        if (!val) {
          return (
            <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400 rounded-full">
              N/A
            </span>
          );
        }
        return (
          <span
            className={cn(
              'px-2 py-0.5 text-xs font-medium rounded-full',
              val === 'critical'
                ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                : val === 'high'
                  ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
                  : val === 'medium'
                    ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'
                    : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
            )}
          >
            {t(`risk.${val}`) || val}
          </span>
        );
      },
    },
    {
      key: 'trust',
      header: t('trust.score'),
      render: (row: Building) => <BuildingTrustCell buildingId={row.id} />,
    },
    {
      key: 'readiness',
      header: t('readiness.title'),
      render: (row: Building) => <BuildingReadinessCell buildingId={row.id} />,
    },
    {
      key: 'updated_at',
      header: t('building.data_freshness') || 'Last updated',
      sortable: true,
      render: (row: Building) => {
        if (!row.updated_at) return <span className="text-xs text-gray-400 dark:text-slate-500">--</span>;
        const freshness = getDataFreshness(row.updated_at);
        return (
          <span
            className={cn(
              'inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full',
              freshness.color,
              freshness.darkColor,
            )}
          >
            <Clock className="w-3 h-3" />
            {freshness.label}
          </span>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('building.title')}</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            {filtered.length} {t('building.title').toLowerCase()}
          </p>
        </div>
        <RoleGate allowedRoles={['admin', 'diagnostician']}>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowOnboardingWizard(true)}
              data-testid="buildings-wizard-button"
              className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              {t('building.add')}
            </button>
            <button
              onClick={openCreateModal}
              data-testid="buildings-create-button"
              className="inline-flex items-center gap-2 px-3 py-2 border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 text-sm font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
              title="Ajout manuel"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </RoleGate>
      </div>

      {/* Portfolio Filter Banner */}
      {hasPortfolioFilters && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-sm font-medium text-blue-700 dark:text-blue-300">
              <Filter className="w-4 h-4" />
              {t('portfolio.filtered_from_portfolio')}
            </div>
            <button
              onClick={clearAllFilters}
              className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 underline"
            >
              {t('portfolio.clear_filter')}
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {(Object.entries(activeFilters) as [PortfolioFilterKey, string][]).map(([key, value]) => {
              const labelKey = `portfolio.${key}_filter`;
              const i18nPrefix =
                key === 'risk' ? 'risk' : key === 'readiness' ? 'readiness' : key === 'trust' ? 'trust' : '';
              const displayValue = i18nPrefix ? t(`${i18nPrefix}.${value}`) || value : value;
              return (
                <span
                  key={key}
                  className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                >
                  {(t(labelKey) || key).replace('{value}', displayValue)}
                  <button
                    onClick={() => clearFilter(key)}
                    className="hover:text-blue-900 dark:hover:text-blue-100"
                    aria-label={`${t('portfolio.clear_filter')} ${key}`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
        {/* Search + view toggle row */}
        <div className="flex items-center gap-3 mb-3 sm:mb-0">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder={t('building.search')}
              aria-label={t('building.search')}
              className="w-full pl-9 pr-4 py-2.5 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
            />
          </div>
          {/* View toggle */}
          <div className="flex items-center border border-gray-300 dark:border-slate-600 rounded-lg overflow-hidden flex-shrink-0">
            <button
              onClick={() => setViewMode('grid')}
              aria-label={t('form.grid_view')}
              aria-pressed={viewMode === 'grid'}
              className={cn(
                'p-2.5 min-w-[44px] min-h-[44px] flex items-center justify-center transition-colors',
                viewMode === 'grid'
                  ? 'bg-red-600 text-white'
                  : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-slate-400 hover:bg-gray-50 dark:hover:bg-slate-700',
              )}
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              aria-label={t('form.table_view')}
              aria-pressed={viewMode === 'table'}
              className={cn(
                'p-2.5 min-w-[44px] min-h-[44px] flex items-center justify-center transition-colors',
                viewMode === 'table'
                  ? 'bg-red-600 text-white'
                  : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-slate-400 hover:bg-gray-50 dark:hover:bg-slate-700',
              )}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
        {/* Filter row */}
        <div className="flex flex-wrap items-center gap-2 sm:mt-3">
          <select
            value={filterCanton}
            onChange={(e) => {
              setFilterCanton(e.target.value);
              setPage(1);
            }}
            aria-label={t('building.filter_canton')}
            className="flex-1 sm:flex-none px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 dark:text-white min-w-0"
          >
            <option value="">{t('building.filter_canton')}</option>
            {SWISS_CANTONS.map((c) => (
              <option key={c} value={c}>
                {t(`canton.${c}`) || c}
              </option>
            ))}
          </select>
          <select
            value={filterType}
            onChange={(e) => {
              setFilterType(e.target.value);
              setPage(1);
            }}
            aria-label={t('building.filter_type')}
            className="flex-1 sm:flex-none px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 dark:text-white min-w-0"
          >
            <option value="">{t('building.filter_type')}</option>
            {BUILDING_TYPES.map((bt) => (
              <option key={bt} value={bt}>
                {t(`building_type.${bt}`) || bt}
              </option>
            ))}
          </select>
          <div className="hidden sm:flex items-center gap-2">
            <input
              type="number"
              value={yearFrom}
              onChange={(e) => {
                setYearFrom(e.target.value);
                setPage(1);
              }}
              placeholder="1800"
              aria-label={t('building.year_from')}
              className="w-24 px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
            />
            <span className="text-gray-400 dark:text-slate-500" aria-hidden="true">
              -
            </span>
            <input
              type="number"
              value={yearTo}
              onChange={(e) => {
                setYearTo(e.target.value);
                setPage(1);
              }}
              placeholder={new Date().getFullYear().toString()}
              aria-label={t('building.year_to')}
              className="w-24 px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
            />
          </div>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      ) : isError ? (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
          <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-12 text-center">
          <Building2 className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-slate-400 text-sm">{t('building.no_buildings')}</p>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {paged.map((building) => (
            <div key={building.id} onMouseEnter={() => handlePrefetch(building.id)} className="flex flex-col">
              <BuildingCard building={building} onClick={() => navigate(`/buildings/${building.id}`)} />
              <div className="mt-1 px-1">
                <BuildingCardDashboardBadges buildingId={building.id} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <DataTable columns={tableColumns} data={paged} />
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            aria-label={t('pagination.previous')}
            className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg border border-gray-300 dark:border-slate-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors dark:text-slate-200"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm text-gray-600 dark:text-slate-300">
            {t('pagination.page', { page, pages: totalPages })}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            aria-label={t('pagination.next')}
            className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg border border-gray-300 dark:border-slate-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors dark:text-slate-200"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Onboarding Wizard */}
      <OnboardingWizard open={showOnboardingWizard} onClose={() => setShowOnboardingWizard(false)} />

      {/* Create/Edit Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div
            data-testid="buildings-create-modal"
            className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto mx-4 p-6"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                {editingBuilding ? t('building.edit') || 'Edit building' : t('building.add')}
              </h2>
              <button
                onClick={closeModal}
                className="p-1 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg"
                aria-label={t('form.close')}
              >
                <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
              </button>
            </div>

            {/* Success message */}
            {formSuccess && (
              <div
                role="status"
                className="flex items-center gap-2 mb-4 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300 text-sm"
              >
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
                {t('form.save_success') || 'Building saved successfully'}
              </div>
            )}

            {/* Error message */}
            {formError && (
              <div
                role="alert"
                className="flex items-center gap-2 mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm"
              >
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-5">
              {/* Group 1: Location */}
              <fieldset>
                <legend className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-slate-500 mb-3">
                  {t('building.location_group') || 'Location'}
                </legend>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                      {t('building.address')} *
                    </label>
                    <input
                      {...register('address')}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                    />
                    {errors.address && (
                      <p className="text-xs text-red-600 mt-1">
                        {t('validation.address_required') || errors.address.message}
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                      {t('building.city')} *
                    </label>
                    <input
                      {...register('city')}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                    />
                    {errors.city && (
                      <p className="text-xs text-red-600 mt-1">
                        {t('validation.city_required') || errors.city.message}
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                      {t('building.postal_code')} *
                    </label>
                    <input
                      {...register('postal_code')}
                      placeholder="1000"
                      maxLength={4}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                    />
                    {errors.postal_code && (
                      <p className="text-xs text-red-600 mt-1">
                        {t('validation.postal_code_format') || errors.postal_code.message}
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                      {t('building.canton')} *
                    </label>
                    <select
                      {...register('canton')}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 dark:text-white"
                    >
                      <option value="">{t('form.select_option')}</option>
                      {SWISS_CANTONS.map((c) => (
                        <option key={c} value={c}>
                          {t(`canton.${c}`) || c}
                        </option>
                      ))}
                    </select>
                    {errors.canton && (
                      <p className="text-xs text-red-600 mt-1">
                        {t('validation.canton_required') || errors.canton.message}
                      </p>
                    )}
                  </div>
                </div>
              </fieldset>

              {/* Group 2: Building info */}
              <fieldset>
                <legend className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-slate-500 mb-3">
                  {t('building.info_group') || 'Building information'}
                </legend>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                      {t('building.building_type')} *
                    </label>
                    <select
                      {...register('building_type')}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 dark:text-white"
                    >
                      <option value="">{t('form.select_option')}</option>
                      {BUILDING_TYPES.map((bt) => (
                        <option key={bt} value={bt}>
                          {t(`building_type.${bt}`) || bt}
                        </option>
                      ))}
                    </select>
                    {errors.building_type && (
                      <p className="text-xs text-red-600 mt-1">
                        {t('validation.building_type_required') || errors.building_type.message}
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                      {t('building.construction_year')} *
                    </label>
                    <input
                      type="number"
                      {...register('construction_year')}
                      placeholder={`1800 - ${currentYear}`}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                    />
                    {errors.construction_year ? (
                      <p className="text-xs text-red-600 mt-1">
                        {t('validation.construction_year_range') || errors.construction_year.message}
                      </p>
                    ) : (
                      <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
                        {t('building.year_range_hint') || `Between 1800 and ${currentYear}`}
                      </p>
                    )}
                  </div>
                </div>
              </fieldset>

              {/* Advanced fields - collapsible */}
              <button
                type="button"
                onClick={() => setShowAdvancedFields(!showAdvancedFields)}
                data-testid="buildings-form-advanced-toggle"
                className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 transition-colors"
              >
                {showAdvancedFields ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                {t('form.advanced_options')}
              </button>
              {showAdvancedFields && (
                <div className="space-y-5 pt-2 border-t border-gray-100 dark:border-slate-700">
                  {/* Group 2b: Extended building info */}
                  <fieldset>
                    <legend className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-slate-500 mb-3">
                      {t('building.details_group') || 'Details'}
                    </legend>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                          {t('building.floors_above')}
                        </label>
                        <input
                          type="number"
                          min="0"
                          {...register('floors_above')}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                          {t('building.floors_below') || 'Basement floors'}
                        </label>
                        <input
                          type="number"
                          min="0"
                          {...register('floors_below')}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                          {t('building.surface_area')}
                        </label>
                        <input
                          type="number"
                          min="1"
                          {...register('surface_area_m2')}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                        />
                      </div>
                    </div>
                  </fieldset>

                  {/* Group 3: Identifiers */}
                  <fieldset>
                    <legend className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-slate-500 mb-3">
                      {t('building.identifiers_group') || 'Identifiers'}
                    </legend>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                          {t('building.egid') || 'EGID'}
                        </label>
                        <input
                          type="number"
                          {...register('egid')}
                          placeholder="e.g. 1234567"
                          className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                        />
                        <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
                          {t('building.egid_hint') || 'Federal building identifier (numeric)'}
                        </p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                          {t('building.egrid')}
                        </label>
                        <input
                          {...register('egrid')}
                          placeholder="e.g. CH123456789012"
                          className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                        />
                        <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
                          {t('building.egrid_hint') || 'Land registry parcel identifier'}
                        </p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                          {t('building.official_id') || 'Official ID'}
                        </label>
                        <input
                          {...register('official_id')}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                        />
                        <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
                          {t('building.official_id_hint') || 'External reference from authority'}
                        </p>
                      </div>
                    </div>
                  </fieldset>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-slate-700">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
                >
                  {t('form.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={createBuilding.isPending || formSuccess}
                  data-testid="buildings-form-submit"
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400 disabled:cursor-not-allowed"
                >
                  {createBuilding.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  {editingBuilding ? t('form.save') || 'Save' : t('form.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
