import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { spatialEnrichmentApi } from '@/api/spatialEnrichment';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import {
  RefreshCw,
  AlertTriangle,
  Building2,
  Ruler,
  Box,
  Layers,
  Home,
  Loader2,
} from 'lucide-react';

interface SpatialEnrichmentCardProps {
  buildingId: string;
}

function formatValue(value: number | null | undefined, unit: string): string {
  if (value == null) return '--';
  return `${Number(value).toLocaleString('fr-CH', { maximumFractionDigits: 1 })} ${unit}`;
}

function MetricTile({
  icon: Icon,
  label,
  value,
  colorClass,
  darkColorClass,
}: {
  icon: typeof Ruler;
  label: string;
  value: string;
  colorClass: string;
  darkColorClass: string;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3">
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
            'bg-gray-50 dark:bg-gray-700',
          )}
        >
          <Icon className={cn('w-4 h-4', colorClass, darkColorClass)} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 truncate">{label}</p>
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">{value}</p>
        </div>
      </div>
    </div>
  );
}

export default function SpatialEnrichmentCard({ buildingId }: SpatialEnrichmentCardProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['spatial-enrichment', buildingId],
    queryFn: () => spatialEnrichmentApi.get(buildingId),
    enabled: !!buildingId,
    staleTime: 5 * 60_000,
    retry: false,
  });

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await spatialEnrichmentApi.refresh(buildingId);
      await queryClient.invalidateQueries({ queryKey: ['spatial-enrichment', buildingId] });
    } catch {
      // Error handled by query refetch
    } finally {
      setIsRefreshing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
        <div className="flex items-center gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {t('spatial_enrichment.loading') || 'Chargement des donnees spatiales...'}
          </span>
        </div>
      </div>
    );
  }

  if (isError || data?.error) {
    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {data?.detail || t('spatial_enrichment.error') || 'Donnees spatiales non disponibles'}
          </span>
        </div>
      </div>
    );
  }

  const fetchedAt = data?.fetched_at;
  const formattedDate = fetchedAt
    ? new Date(fetchedAt).toLocaleDateString('fr-CH', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      })
    : null;

  const hasData = data?.height_m != null || data?.volume_m3 != null || data?.surface_m2 != null;

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Building2 className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            {t('spatial_enrichment.title') || 'Enrichissement spatial 3D'}
          </h3>
          {data?.cached && (
            <span className="text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 px-1.5 py-0.5 rounded">
              cache
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {formattedDate && (
            <span className="text-[10px] text-gray-400 dark:text-gray-500">{formattedDate}</span>
          )}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 rounded hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
            title={t('spatial_enrichment.refresh') || 'Actualiser'}
          >
            <RefreshCw className={cn('w-3 h-3', isRefreshing && 'animate-spin')} />
            {t('spatial_enrichment.refresh') || 'Actualiser'}
          </button>
        </div>
      </div>

      {/* Source badge */}
      <p className="text-[10px] text-gray-400 dark:text-gray-500 mb-3">
        Source: swisstopo swissBUILDINGS3D 3.0 &middot; {data?.source_version || 'swissbuildings3d-v3.0'}
      </p>

      {hasData ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <MetricTile
            icon={Ruler}
            label={t('spatial_enrichment.height') || 'Hauteur du batiment'}
            value={formatValue(data?.height_m, 'm')}
            colorClass="text-blue-600"
            darkColorClass="dark:text-blue-400"
          />
          <MetricTile
            icon={Layers}
            label={t('spatial_enrichment.surface') || 'Surface au sol'}
            value={formatValue(data?.surface_m2, 'm\u00B2')}
            colorClass="text-green-600"
            darkColorClass="dark:text-green-400"
          />
          <MetricTile
            icon={Box}
            label={t('spatial_enrichment.volume') || 'Volume'}
            value={formatValue(data?.volume_m3, 'm\u00B3')}
            colorClass="text-purple-600"
            darkColorClass="dark:text-purple-400"
          />
          <MetricTile
            icon={Home}
            label={t('spatial_enrichment.roof_type') || 'Type de toiture'}
            value={data?.roof_type || '--'}
            colorClass="text-amber-600"
            darkColorClass="dark:text-amber-400"
          />
        </div>
      ) : (
        <p className="text-xs text-gray-400 dark:text-gray-500 text-center py-4">
          {t('spatial_enrichment.no_data') || 'Aucune donnee 3D disponible pour ce batiment'}
        </p>
      )}
    </div>
  );
}
