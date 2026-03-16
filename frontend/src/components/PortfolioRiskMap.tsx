import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { portfolioApi } from '@/api/portfolio';
import { RISK_COLORS, SWISS_CANTONS } from '@/utils/constants';
import type { RiskLevel, MapBuildingsResponse } from '@/types';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Filter, Loader2, MapPin, Layers } from 'lucide-react';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;
const RISK_LEVELS: RiskLevel[] = ['low', 'medium', 'high', 'critical'];

type LayerMode = 'heatmap' | 'points';

export default function PortfolioRiskMap() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import('mapbox-gl').Map | null>(null);
  const popupRef = useRef<import('mapbox-gl').Popup | null>(null);

  const [isMapReady, setIsMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const effectiveError = !MAPBOX_TOKEN ? t('map.no_data') : mapError;
  const [showControls, setShowControls] = useState(true);
  const [layerMode, setLayerMode] = useState<LayerMode>('points');

  // Filters
  const [activeRiskLevels, setActiveRiskLevels] = useState<Set<string>>(new Set(RISK_LEVELS));
  const [filterCanton, setFilterCanton] = useState('');

  const riskLevelParam =
    activeRiskLevels.size < RISK_LEVELS.length ? Array.from(activeRiskLevels).join(',') : undefined;

  const {
    data: geojsonData,
    isLoading: isDataLoading,
    isError: isDataError,
  } = useQuery<MapBuildingsResponse>({
    queryKey: ['portfolio', 'map-buildings', riskLevelParam, filterCanton],
    queryFn: () =>
      portfolioApi.getMapBuildings({
        risk_level: riskLevelParam,
        canton: filterCanton || undefined,
      }),
    enabled: !!MAPBOX_TOKEN,
  });

  const toggleRiskLevel = (r: string) => {
    setActiveRiskLevels((prev) => {
      const next = new Set(prev);
      if (next.has(r)) next.delete(r);
      else next.add(r);
      return next;
    });
  };

  const isDark = document.documentElement.classList.contains('dark');

  const updateLayers = useCallback((map: import('mapbox-gl').Map, mode: LayerMode) => {
    if (!map.isStyleLoaded()) return;

    // Toggle heatmap layer visibility
    if (map.getLayer('portfolio-heatmap')) {
      map.setLayoutProperty('portfolio-heatmap', 'visibility', mode === 'heatmap' ? 'visible' : 'none');
    }

    // Toggle points layer visibility
    if (map.getLayer('portfolio-buildings')) {
      map.setLayoutProperty('portfolio-buildings', 'visibility', mode === 'points' ? 'visible' : 'none');
    }
  }, []);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || !MAPBOX_TOKEN) return;

    let cancelled = false;
    let localMap: import('mapbox-gl').Map | null = null;

    const initializeMap = async () => {
      try {
        const mapboxgl = (await import('mapbox-gl')).default;
        if (cancelled || !mapContainer.current) return;

        mapboxgl.accessToken = MAPBOX_TOKEN;

        const map = new mapboxgl.Map({
          container: mapContainer.current,
          style: isDark ? 'mapbox://styles/mapbox/dark-v11' : 'mapbox://styles/mapbox/light-v11',
          center: [8.2, 46.8],
          zoom: 7,
        });

        localMap = map;
        map.addControl(new mapboxgl.NavigationControl(), 'top-right');

        map.on('load', () => {
          setIsMapReady(true);

          map.addSource('portfolio-buildings', {
            type: 'geojson',
            data: geojsonData || { type: 'FeatureCollection', features: [] },
            cluster: true,
            clusterMaxZoom: 14,
            clusterRadius: 50,
          });

          map.addLayer({
            id: 'portfolio-heatmap',
            type: 'heatmap',
            source: 'portfolio-buildings',
            filter: ['!', ['has', 'point_count']],
            layout: { visibility: 'none' },
            paint: {
              'heatmap-weight': ['interpolate', ['linear'], ['get', 'risk_score'], 0, 0, 1, 1],
              'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 0, 1, 14, 3],
              'heatmap-color': [
                'interpolate',
                ['linear'],
                ['heatmap-density'],
                0,
                'rgba(0,0,0,0)',
                0.2,
                '#22c55e',
                0.4,
                '#84cc16',
                0.6,
                '#eab308',
                0.8,
                '#f97316',
                1,
                '#ef4444',
              ],
              'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 15, 14, 30],
              'heatmap-opacity': 0.8,
            },
          });

          map.addLayer({
            id: 'portfolio-clusters',
            type: 'circle',
            source: 'portfolio-buildings',
            filter: ['has', 'point_count'],
            paint: {
              'circle-color': '#64748b',
              'circle-radius': ['step', ['get', 'point_count'], 18, 10, 24, 50, 32],
              'circle-opacity': 0.85,
              'circle-stroke-width': 2,
              'circle-stroke-color': '#ffffff',
            },
          });

          map.addLayer({
            id: 'portfolio-cluster-count',
            type: 'symbol',
            source: 'portfolio-buildings',
            filter: ['has', 'point_count'],
            layout: {
              'text-field': ['get', 'point_count_abbreviated'],
              'text-font': ['DIN Offc Pro Medium', 'Arial Unicode MS Bold'],
              'text-size': 13,
            },
            paint: {
              'text-color': '#ffffff',
            },
          });

          map.addLayer({
            id: 'portfolio-buildings',
            type: 'circle',
            source: 'portfolio-buildings',
            filter: ['!', ['has', 'point_count']],
            layout: { visibility: 'visible' },
            paint: {
              'circle-radius': ['interpolate', ['linear'], ['zoom'], 7, 4, 12, 8, 16, 14],
              'circle-color': [
                'match',
                ['get', 'overall_risk_level'],
                'critical',
                RISK_COLORS.critical || '#dc2626',
                'high',
                RISK_COLORS.high || '#ea580c',
                'medium',
                RISK_COLORS.medium || '#eab308',
                'low',
                RISK_COLORS.low || '#22c55e',
                '#94a3b8',
              ],
              'circle-opacity': 0.8,
              'circle-stroke-width': 1.5,
              'circle-stroke-color': '#ffffff',
            },
          });

          map.on('click', 'portfolio-buildings', (e) => {
            if (!e.features || e.features.length === 0) return;
            const feature = e.features[0];
            const props = feature.properties || {};
            const coords = (feature.geometry as GeoJSON.Point).coordinates.slice() as [number, number];

            if (popupRef.current) popupRef.current.remove();

            const riskBg =
              props.overall_risk_level === 'critical'
                ? '#fef2f2'
                : props.overall_risk_level === 'high'
                  ? '#fff7ed'
                  : props.overall_risk_level === 'medium'
                    ? '#fefce8'
                    : '#f0fdf4';

            const popup = new mapboxgl.Popup({ offset: 15, maxWidth: '280px' })
              .setLngLat(coords)
              .setHTML(
                `
                <div style="font-family:system-ui,sans-serif;">
                  <p style="font-weight:600;font-size:14px;margin:0 0 4px;">${props.address || '-'}</p>
                  <p style="font-size:12px;color:#6b7280;margin:0 0 8px;">${props.city || ''} (${props.canton || ''})</p>
                  <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <span style="padding:2px 8px;border-radius:9999px;font-size:11px;font-weight:600;background:${riskBg};color:${RISK_COLORS[props.overall_risk_level as RiskLevel] || '#64748b'};">
                      ${props.overall_risk_level || 'N/A'}
                    </span>
                    ${props.completeness_score ? `<span style="font-size:12px;color:#6b7280;">Score: ${Math.round(Number(props.completeness_score) * 100)}%</span>` : ''}
                  </div>
                  ${props.construction_year ? `<p style="font-size:12px;color:#6b7280;margin:0 0 8px;">Construction: ${props.construction_year}</p>` : ''}
                  <button id="popup-detail-${props.id}" style="width:100%;padding:6px 12px;font-size:12px;font-weight:500;color:white;background:#dc2626;border:none;border-radius:6px;cursor:pointer;">
                    ${t('form.view')}
                  </button>
                </div>
              `,
              )
              .addTo(map);

            popupRef.current = popup;

            setTimeout(() => {
              const btn = document.getElementById(`popup-detail-${props.id}`);
              if (btn) {
                btn.addEventListener('click', () => {
                  navigate(`/buildings/${props.id}`);
                });
              }
            }, 50);
          });

          map.on('click', 'portfolio-clusters', (e) => {
            const features = map.queryRenderedFeatures(e.point, { layers: ['portfolio-clusters'] });
            if (!features.length) return;
            const clusterId = features[0].properties?.cluster_id;
            const source = map.getSource('portfolio-buildings') as import('mapbox-gl').GeoJSONSource;
            source.getClusterExpansionZoom(clusterId, (err, zoom) => {
              if (err) return;
              map.easeTo({
                center: (features[0].geometry as GeoJSON.Point).coordinates as [number, number],
                zoom: zoom ?? undefined,
              });
            });
          });

          map.on('mouseenter', 'portfolio-clusters', () => {
            map.getCanvas().style.cursor = 'pointer';
          });
          map.on('mouseleave', 'portfolio-clusters', () => {
            map.getCanvas().style.cursor = '';
          });
          map.on('mouseenter', 'portfolio-buildings', () => {
            map.getCanvas().style.cursor = 'pointer';
          });
          map.on('mouseleave', 'portfolio-buildings', () => {
            map.getCanvas().style.cursor = '';
          });

          updateLayers(map, layerMode);
        });

        map.on('error', () => {
          setMapError(t('app.error'));
          setIsMapReady(false);
        });

        mapRef.current = map;
      } catch {
        if (!cancelled) {
          setMapError(t('app.error'));
          setIsMapReady(false);
        }
      }
    };

    void initializeMap();

    return () => {
      cancelled = true;
      if (popupRef.current) popupRef.current.remove();
      localMap?.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update data source when geojsonData changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapReady || !geojsonData) return;

    const source = map.getSource('portfolio-buildings') as import('mapbox-gl').GeoJSONSource;
    if (source) {
      source.setData(geojsonData);
    }
  }, [geojsonData, isMapReady]);

  // Update layer visibility when mode changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapReady) return;
    updateLayers(map, layerMode);
  }, [layerMode, isMapReady, updateLayers]);

  const featureCount = geojsonData?.features?.length ?? 0;

  return (
    <div className="h-[500px] relative rounded-xl overflow-hidden border border-gray-200 dark:border-slate-700 shadow-sm">
      {/* Map container */}
      <div ref={mapContainer} className="absolute inset-0" />

      {/* Loading overlay */}
      {(isDataLoading || (!isMapReady && MAPBOX_TOKEN && !effectiveError)) && (
        <div className="absolute inset-0 bg-white/80 dark:bg-slate-900/80 flex items-center justify-center z-10">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin text-red-600 mx-auto mb-2" />
            <p className="text-sm text-gray-500 dark:text-slate-400">{t('app.loading')}</p>
          </div>
        </div>
      )}

      {/* Error overlay */}
      {(effectiveError || isDataError) && (
        <div className="absolute inset-0 bg-white/90 dark:bg-slate-900/90 flex items-center justify-center z-10">
          <div className="text-center p-6">
            <MapPin className="w-10 h-10 text-gray-300 dark:text-slate-600 mx-auto mb-2" />
            <p className="text-sm text-gray-600 dark:text-slate-400">{effectiveError || t('app.error')}</p>
          </div>
        </div>
      )}

      {/* Controls Toggle */}
      <button
        onClick={() => setShowControls(!showControls)}
        className="absolute top-4 left-4 z-20 p-2 bg-white dark:bg-slate-800 rounded-lg shadow-md border border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700"
      >
        <Filter className="w-4 h-4 text-gray-600 dark:text-slate-300" />
      </button>

      {/* Layer Mode Toggle */}
      <button
        onClick={() => setLayerMode(layerMode === 'points' ? 'heatmap' : 'points')}
        className="absolute top-4 left-14 z-20 p-2 bg-white dark:bg-slate-800 rounded-lg shadow-md border border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700"
        title={layerMode === 'points' ? t('portfolio.heatmap_mode') : t('portfolio.points_mode')}
      >
        <Layers className="w-4 h-4 text-gray-600 dark:text-slate-300" />
      </button>

      {/* Controls Panel */}
      {showControls && (
        <div className="absolute top-14 left-4 z-20 w-64 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-gray-200 dark:border-slate-700 p-4 space-y-4 max-h-[calc(100%-80px)] overflow-y-auto">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{t('portfolio.filter_risk_level')}</h3>

          {/* Risk Level Filters */}
          <div>
            <div className="space-y-1.5">
              {RISK_LEVELS.map((r) => (
                <label key={r} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={activeRiskLevels.has(r)}
                    onChange={() => toggleRiskLevel(r)}
                    className="w-3.5 h-3.5 rounded border-gray-300 dark:border-slate-600 text-red-600 focus:ring-red-500"
                  />
                  <span
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: RISK_COLORS[r] || '#94a3b8' }}
                  />
                  <span className="text-sm text-gray-700 dark:text-slate-200">{t(`risk.${r}`)}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Canton Filter */}
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-2">
              {t('portfolio.filter_canton')}
            </p>
            <select
              value={filterCanton}
              onChange={(e) => setFilterCanton(e.target.value)}
              className="w-full px-2 py-1.5 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              <option value="">{t('form.all')}</option>
              {SWISS_CANTONS.map((c) => (
                <option key={c} value={c}>
                  {t(`canton.${c}`) || c}
                </option>
              ))}
            </select>
          </div>

          {/* Building count */}
          <div className="text-xs text-gray-500 dark:text-slate-400 pt-2 border-t border-gray-200 dark:border-slate-600">
            {t('portfolio.buildings_on_map')}: {featureCount}
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-4 right-4 z-20 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-gray-200 dark:border-slate-700 p-3">
        <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-2">
          {layerMode === 'points' ? t('portfolio.points_mode') : t('portfolio.heatmap_mode')}
        </p>
        {layerMode === 'points' ? (
          <div className="space-y-1">
            {RISK_LEVELS.map((r) => (
              <div key={r} className="flex items-center gap-2">
                <span
                  className="w-3 h-3 rounded-full border border-white dark:border-slate-800 shadow-sm"
                  style={{ backgroundColor: RISK_COLORS[r] || '#94a3b8' }}
                />
                <span className="text-xs text-gray-600 dark:text-slate-300">{t(`risk.${r}`)}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-600 dark:text-slate-300">{t('risk.low')}</span>
            <div className="w-24 h-3 rounded-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500" />
            <span className="text-xs text-gray-600 dark:text-slate-300">{t('risk.critical')}</span>
          </div>
        )}
      </div>
    </div>
  );
}
