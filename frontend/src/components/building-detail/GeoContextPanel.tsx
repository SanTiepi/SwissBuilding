import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { geoContextApi } from '@/api/geoContext';
import type { GeoLayerResult } from '@/api/geoContext';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import {
  RefreshCw,
  AlertTriangle,
  Sun,
  Volume2,
  Train,
  Droplets,
  Skull,
  Landmark,
  Bus,
  Flame,
  Radiation,
  CloudRain,
  Loader2,
  MapPin,
} from 'lucide-react';

interface GeoContextPanelProps {
  buildingId: string;
}

const LAYER_CONFIG: Record<
  string,
  {
    icon: typeof Sun;
    colorClass: string;
    darkColorClass: string;
  }
> = {
  radon: { icon: Radiation, colorClass: 'text-yellow-600', darkColorClass: 'dark:text-yellow-400' },
  noise_road: { icon: Volume2, colorClass: 'text-orange-600', darkColorClass: 'dark:text-orange-400' },
  noise_rail: { icon: Train, colorClass: 'text-orange-500', darkColorClass: 'dark:text-orange-300' },
  solar: { icon: Sun, colorClass: 'text-amber-500', darkColorClass: 'dark:text-amber-300' },
  natural_hazards: { icon: CloudRain, colorClass: 'text-blue-600', darkColorClass: 'dark:text-blue-400' },
  groundwater_protection: {
    icon: Droplets,
    colorClass: 'text-cyan-600',
    darkColorClass: 'dark:text-cyan-400',
  },
  contaminated_sites: { icon: Skull, colorClass: 'text-red-600', darkColorClass: 'dark:text-red-400' },
  heritage_isos: { icon: Landmark, colorClass: 'text-purple-600', darkColorClass: 'dark:text-purple-400' },
  public_transport: { icon: Bus, colorClass: 'text-green-600', darkColorClass: 'dark:text-green-400' },
  thermal_networks: { icon: Flame, colorClass: 'text-rose-600', darkColorClass: 'dark:text-rose-400' },
};

function formatLayerValue(key: string, layer: GeoLayerResult): string {
  switch (key) {
    case 'radon':
      return layer.zone || layer.value?.toString() || 'Voir details';
    case 'noise_road':
    case 'noise_rail':
      return layer.level_db != null ? `${layer.level_db} dB(A)` : 'Voir details';
    case 'solar':
      if (layer.potential_kwh != null) return `${layer.potential_kwh} kWh/an`;
      return layer.suitability || 'Voir details';
    case 'natural_hazards':
      return layer.hazard_level || 'Voir details';
    case 'groundwater_protection':
      return layer.zone_type || 'Voir details';
    case 'contaminated_sites':
      return layer.status || layer.category || 'Voir details';
    case 'heritage_isos':
      return layer.name || layer.status || 'Voir details';
    case 'public_transport':
      return layer.quality_class || 'Voir details';
    case 'thermal_networks':
      return layer.network_name || layer.status || 'Voir details';
    default:
      return 'Voir details';
  }
}

function LayerCard({ layerKey, layer }: { layerKey: string; layer: GeoLayerResult }) {
  const config = LAYER_CONFIG[layerKey] || {
    icon: MapPin,
    colorClass: 'text-gray-600',
    darkColorClass: 'dark:text-gray-400',
  };
  const Icon = config.icon;
  const displayValue = formatLayerValue(layerKey, layer);

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 hover:shadow-sm transition-shadow">
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
            'bg-gray-50 dark:bg-gray-700',
          )}
        >
          <Icon className={cn('w-4 h-4', config.colorClass, config.darkColorClass)} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 truncate">{layer.label}</p>
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5 truncate">{displayValue}</p>
          <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1 truncate">{layer.source}</p>
        </div>
      </div>
    </div>
  );
}

export default function GeoContextPanel({ buildingId }: GeoContextPanelProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['geo-context', buildingId],
    queryFn: () => geoContextApi.get(buildingId),
    enabled: !!buildingId,
    staleTime: 5 * 60_000,
    retry: false,
  });

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await geoContextApi.refresh(buildingId);
      await queryClient.invalidateQueries({ queryKey: ['geo-context', buildingId] });
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
            {t('geo_context.loading') || 'Chargement du contexte geographique...'}
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
            {data?.detail || t('geo_context.error') || 'Contexte geographique non disponible'}
          </span>
        </div>
      </div>
    );
  }

  const context = data?.context || {};
  const layerKeys = Object.keys(context);

  // All possible layers (show "Non disponible" for missing ones)
  const allLayerKeys = [
    'radon',
    'noise_road',
    'noise_rail',
    'solar',
    'natural_hazards',
    'groundwater_protection',
    'contaminated_sites',
    'heritage_isos',
    'public_transport',
    'thermal_networks',
  ];

  const fetchedAt = data?.fetched_at;
  const formattedDate = fetchedAt
    ? new Date(fetchedAt).toLocaleDateString('fr-CH', { day: '2-digit', month: '2-digit', year: 'numeric' })
    : null;

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-red-600 dark:text-red-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            {t('geo_context.title') || 'Contexte geographique'}
          </h3>
          {data?.cached && (
            <span className="text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 px-1.5 py-0.5 rounded">
              cache
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {formattedDate && <span className="text-[10px] text-gray-400 dark:text-gray-500">{formattedDate}</span>}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 rounded hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
            title={t('geo_context.refresh') || 'Actualiser'}
          >
            <RefreshCw className={cn('w-3 h-3', isRefreshing && 'animate-spin')} />
            {t('geo_context.refresh') || 'Actualiser'}
          </button>
        </div>
      </div>

      {/* Source badge */}
      <p className="text-[10px] text-gray-400 dark:text-gray-500 mb-3">
        Source: geo.admin.ch (API federale) &middot; {data?.source_version || 'geo.admin-v1'}
      </p>

      {/* Layer grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {allLayerKeys.map((key) => {
          const layer = context[key];
          if (layer) {
            return <LayerCard key={key} layerKey={key} layer={layer} />;
          }
          // Show "Non disponible" for layers without data
          const config = LAYER_CONFIG[key];
          if (!config) return null;
          const Icon = config.icon;
          const label = key.replace(/_/g, ' ');
          return (
            <div
              key={key}
              className="bg-gray-50 dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-lg p-3 opacity-60"
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-gray-100 dark:bg-gray-800">
                  <Icon className="w-4 h-4 text-gray-400 dark:text-gray-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-400 dark:text-gray-500 truncate capitalize">{label}</p>
                  <p className="text-sm text-gray-400 dark:text-gray-600 mt-0.5">
                    {t('geo_context.not_available') || 'Non disponible'}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {layerKeys.length === 0 && (
        <p className="text-xs text-gray-400 dark:text-gray-500 text-center py-4">
          {t('geo_context.no_data') || 'Aucune donnee disponible pour cette localisation'}
        </p>
      )}
    </div>
  );
}
