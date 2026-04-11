import { memo, useCallback, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { geoContextApi } from '@/api/geoContext';
import type { GeoLayerResult } from '@/api/geoContext';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { GeoRiskScore } from '@/components/GeoRiskScore';
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
  Mountain,
  Plane,
  Building2,
  Wifi,
  Zap,
  Plug,
  TreePine,
  Shield,
  Bomb,
  Layers,
  Waves,
} from 'lucide-react';

interface GeoContextPanelProps {
  buildingId: string;
}

// --- Layer configuration ---
const LAYER_CONFIG: Record<
  string,
  {
    icon: typeof Sun;
    colorClass: string;
    darkColorClass: string;
  }
> = {
  // Risques naturels
  radon: { icon: Radiation, colorClass: 'text-yellow-600', darkColorClass: 'dark:text-yellow-400' },
  natural_hazards: { icon: CloudRain, colorClass: 'text-blue-600', darkColorClass: 'dark:text-blue-400' },
  flood_zones: { icon: Waves, colorClass: 'text-blue-500', darkColorClass: 'dark:text-blue-300' },
  landslides: { icon: Mountain, colorClass: 'text-amber-700', darkColorClass: 'dark:text-amber-400' },
  seismic: { icon: Layers, colorClass: 'text-red-500', darkColorClass: 'dark:text-red-300' },
  // Environnement
  contaminated_sites: { icon: Skull, colorClass: 'text-red-600', darkColorClass: 'dark:text-red-400' },
  groundwater_protection: { icon: Droplets, colorClass: 'text-cyan-600', darkColorClass: 'dark:text-cyan-400' },
  groundwater_areas: { icon: Droplets, colorClass: 'text-cyan-500', darkColorClass: 'dark:text-cyan-300' },
  accident_sites: { icon: Bomb, colorClass: 'text-red-700', darkColorClass: 'dark:text-red-500' },
  // Nuisances sonores
  noise_road: { icon: Volume2, colorClass: 'text-orange-600', darkColorClass: 'dark:text-orange-400' },
  noise_rail: { icon: Train, colorClass: 'text-orange-500', darkColorClass: 'dark:text-orange-300' },
  aircraft_noise: { icon: Plane, colorClass: 'text-orange-400', darkColorClass: 'dark:text-orange-300' },
  // Patrimoine
  heritage_isos: { icon: Landmark, colorClass: 'text-purple-600', darkColorClass: 'dark:text-purple-400' },
  protected_monuments: { icon: Shield, colorClass: 'text-purple-500', darkColorClass: 'dark:text-purple-300' },
  // Energie & Climat
  solar: { icon: Sun, colorClass: 'text-amber-500', darkColorClass: 'dark:text-amber-300' },
  thermal_networks: { icon: Flame, colorClass: 'text-rose-600', darkColorClass: 'dark:text-rose-400' },
  // Infrastructure & Connectivite
  public_transport: { icon: Bus, colorClass: 'text-green-600', darkColorClass: 'dark:text-green-400' },
  ev_charging: { icon: Plug, colorClass: 'text-green-500', darkColorClass: 'dark:text-green-300' },
  mobile_coverage: { icon: Wifi, colorClass: 'text-blue-500', darkColorClass: 'dark:text-blue-300' },
  broadband: { icon: Zap, colorClass: 'text-blue-400', darkColorClass: 'dark:text-blue-200' },
  // Geologie & Sol
  building_zones: { icon: Building2, colorClass: 'text-indigo-600', darkColorClass: 'dark:text-indigo-400' },
  agricultural_zones: { icon: TreePine, colorClass: 'text-lime-600', darkColorClass: 'dark:text-lime-400' },
  forest_reserves: { icon: TreePine, colorClass: 'text-emerald-600', darkColorClass: 'dark:text-emerald-400' },
  military_zones: { icon: Shield, colorClass: 'text-gray-600', darkColorClass: 'dark:text-gray-400' },
};

// --- Categories with layer keys ---
interface LayerCategory {
  key: string;
  layers: string[];
}

const CATEGORIES: LayerCategory[] = [
  {
    key: 'natural_risks',
    layers: ['radon', 'natural_hazards', 'flood_zones', 'landslides', 'seismic'],
  },
  {
    key: 'environment',
    layers: ['contaminated_sites', 'groundwater_protection', 'groundwater_areas', 'accident_sites'],
  },
  {
    key: 'noise',
    layers: ['noise_road', 'noise_rail', 'aircraft_noise'],
  },
  {
    key: 'heritage',
    layers: ['heritage_isos', 'protected_monuments'],
  },
  {
    key: 'energy',
    layers: ['solar', 'thermal_networks'],
  },
  {
    key: 'infrastructure',
    layers: ['public_transport', 'ev_charging', 'mobile_coverage', 'broadband'],
  },
  {
    key: 'geology',
    layers: ['building_zones', 'agricultural_zones', 'forest_reserves', 'military_zones'],
  },
];

const ALL_LAYER_KEYS = CATEGORIES.flatMap((c) => c.layers);

// --- Risk indicator ---
function riskIndicator(key: string, layer: GeoLayerResult): 'green' | 'orange' | 'red' | null {
  const val = (s?: string | null) => (s || '').toLowerCase();

  switch (key) {
    case 'radon': {
      const zone = val(layer.zone);
      if (zone.includes('hoch') || zone.includes('high') || zone.includes('élev')) return 'red';
      if (zone.includes('mittel') || zone.includes('moyen') || zone.includes('moderate')) return 'orange';
      return 'green';
    }
    case 'natural_hazards':
    case 'flood_zones':
    case 'landslides': {
      const level = val(layer.hazard_level);
      if (level.includes('erheblich') || level.includes('hoch') || level.includes('high')) return 'red';
      if (level.includes('mittel') || level.includes('medium') || level.includes('moyen')) return 'orange';
      if (level) return 'green';
      return null;
    }
    case 'seismic': {
      const zone = val(layer.zone);
      if (zone.includes('3') || zone.includes('e') || zone.includes('d')) return 'red';
      if (zone.includes('2') || zone.includes('c')) return 'orange';
      return 'green';
    }
    case 'contaminated_sites': {
      const status = val(layer.status);
      if (status.includes('sanierung') || status.includes('assaini')) return 'red';
      if (status.includes('überwachung') || status.includes('surveill') || status.includes('belastet'))
        return 'orange';
      return 'green';
    }
    case 'accident_sites': {
      const status = val(layer.status);
      if (status.includes('proximite') || status.includes('seveso')) return 'red';
      return 'green';
    }
    case 'noise_road':
    case 'noise_rail':
    case 'aircraft_noise': {
      const db = typeof layer.level_db === 'number' ? layer.level_db : parseFloat(String(layer.level_db || '0'));
      if (db >= 70) return 'red';
      if (db >= 55) return 'orange';
      return 'green';
    }
    default:
      return null;
  }
}

const INDICATOR_STYLES = {
  green: 'bg-green-500',
  orange: 'bg-orange-400',
  red: 'bg-red-500',
} as const;

// --- Value formatter ---
function formatLayerValue(key: string, layer: GeoLayerResult): string {
  switch (key) {
    case 'radon':
      return layer.zone || layer.value?.toString() || 'Voir details';
    case 'noise_road':
    case 'noise_rail':
    case 'aircraft_noise':
      return layer.level_db != null ? `${layer.level_db} dB(A)` : 'Voir details';
    case 'solar':
      if (layer.potential_kwh != null) return `${layer.potential_kwh} kWh/an`;
      return layer.suitability || 'Voir details';
    case 'natural_hazards':
    case 'flood_zones':
    case 'landslides':
      return layer.hazard_level || 'Voir details';
    case 'groundwater_protection':
    case 'groundwater_areas':
      return layer.zone_type || 'Voir details';
    case 'contaminated_sites':
      return layer.status || layer.category || 'Voir details';
    case 'heritage_isos':
      return layer.name || layer.status || 'Voir details';
    case 'public_transport':
      return layer.quality_class || 'Voir details';
    case 'thermal_networks':
      return layer.network_name || layer.status || 'Voir details';
    case 'seismic':
      return layer.zone ? `Zone ${layer.zone}` : 'Voir details';
    case 'building_zones':
      return layer.zone_type || layer.value || 'Voir details';
    case 'mobile_coverage':
      return layer.status || 'Voir details';
    case 'broadband':
      return layer.name || layer.value || 'Voir details';
    case 'ev_charging':
      return layer.status || 'Voir details';
    case 'protected_monuments':
      return layer.status || layer.category || 'Voir details';
    case 'agricultural_zones':
      return layer.value || layer.zone || 'Voir details';
    case 'forest_reserves':
      return layer.name || layer.status || 'Voir details';
    case 'military_zones':
      return layer.status || 'Voir details';
    case 'accident_sites':
      return layer.name || layer.status || 'Voir details';
    default:
      return layer.value || layer.status || 'Voir details';
  }
}

// --- LayerCard ---
function LayerCard({ layerKey, layer }: { layerKey: string; layer: GeoLayerResult }) {
  const config = LAYER_CONFIG[layerKey] || {
    icon: MapPin,
    colorClass: 'text-gray-600',
    darkColorClass: 'dark:text-gray-400',
  };
  const Icon = config.icon;
  const displayValue = formatLayerValue(layerKey, layer);
  const indicator = riskIndicator(layerKey, layer);

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
        {indicator && (
          <div className={cn('w-2.5 h-2.5 rounded-full flex-shrink-0 mt-1', INDICATOR_STYLES[indicator])} />
        )}
      </div>
    </div>
  );
}

// --- MissingLayerCard ---
function MissingLayerCard({ layerKey }: { layerKey: string }) {
  const { t } = useTranslation();
  const config = LAYER_CONFIG[layerKey];
  if (!config) return null;
  const Icon = config.icon;
  const label = layerKey.replace(/_/g, ' ');

  return (
    <div className="bg-gray-50 dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-lg p-3 opacity-60">
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
}

// --- Main panel ---
export default memo(function GeoContextPanel({ buildingId }: GeoContextPanelProps) {
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

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await geoContextApi.refresh(buildingId);
      await queryClient.invalidateQueries({ queryKey: ['geo-context', buildingId] });
    } catch {
      // Error handled by query refetch
    } finally {
      setIsRefreshing(false);
    }
  }, [buildingId, queryClient]);

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
          <span className="text-[10px] bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-300 px-1.5 py-0.5 rounded font-medium">
            {layerKeys.length}/{ALL_LAYER_KEYS.length}
          </span>
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

      {/* Risk Score */}
      {data?.risk_score && <GeoRiskScore riskScore={data.risk_score} />}

      {/* Categorized layer grid */}
      <div className="space-y-4">
        {CATEGORIES.map((cat) => {
          const hasAny = cat.layers.some((k) => context[k]);
          if (!hasAny && layerKeys.length === 0) return null;

          return (
            <div key={cat.key}>
              <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                {t(`geo_context.cat_${cat.key}`) || cat.key.replace(/_/g, ' ')}
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {cat.layers.map((key) => {
                  const layer = context[key];
                  if (layer) {
                    return <LayerCard key={key} layerKey={key} layer={layer} />;
                  }
                  return <MissingLayerCard key={key} layerKey={key} />;
                })}
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
});
