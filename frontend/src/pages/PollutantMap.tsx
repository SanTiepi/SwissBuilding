/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view under PortfolioCommand (geo visualization).
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { RISK_COLORS, POLLUTANT_COLORS, SWISS_CANTONS } from '@/utils/constants';
import { riskApi } from '@/api/risk';
import type { PollutantType, RiskLevel, MapBuildingsResponse } from '@/types';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Filter, Loader2, MapPin } from 'lucide-react';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

const POLLUTANT_TYPES: PollutantType[] = ['asbestos', 'pcb', 'lead', 'hap', 'radon'] as PollutantType[];
const RISK_LEVELS: RiskLevel[] = ['low', 'medium', 'high', 'critical'] as RiskLevel[];

export default function PollutantMap() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import('mapbox-gl').Map | null>(null);
  const popupRef = useRef<import('mapbox-gl').Popup | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [mapError, setMapError] = useState<string | null>(null);
  const effectiveError = !MAPBOX_TOKEN ? t('map.no_data') : mapError;
  const [showControls, setShowControls] = useState(true);

  // Filters
  const [activePollutants, setActivePollutants] = useState<Set<string>>(new Set(POLLUTANT_TYPES));
  const [activeRiskLevels, setActiveRiskLevels] = useState<Set<string>>(new Set(RISK_LEVELS));
  const [filterCanton, setFilterCanton] = useState('');

  const [geojsonData, setGeojsonData] = useState<MapBuildingsResponse | null>(null);

  const togglePollutant = (p: string) => {
    setActivePollutants((prev) => {
      const next = new Set(prev);
      if (next.has(p)) next.delete(p);
      else next.add(p);
      return next;
    });
  };

  const toggleRiskLevel = (r: string) => {
    setActiveRiskLevels((prev) => {
      const next = new Set(prev);
      if (next.has(r)) next.delete(r);
      else next.add(r);
      return next;
    });
  };

  // Fetch GeoJSON data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await riskApi.getMapBuildings();
        setGeojsonData(data);
      } catch {
        setMapError(t('map.no_data'));
      }
    };
    fetchData();
  }, [t]);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || !MAPBOX_TOKEN) {
      return;
    }

    let cancelled = false;
    let localMap: import('mapbox-gl').Map | null = null;

    const initializeMap = async () => {
      try {
        const mapboxgl = (await import('mapbox-gl')).default;
        if (cancelled || !mapContainer.current) return;

        mapboxgl.accessToken = MAPBOX_TOKEN;

        const map = new mapboxgl.Map({
          container: mapContainer.current,
          style: 'mapbox://styles/mapbox/light-v11',
          center: [8.2, 46.8],
          zoom: 7,
        });

        localMap = map;
        map.addControl(new mapboxgl.NavigationControl(), 'top-right');

        map.on('load', () => {
          setIsLoading(false);

          map.addSource('buildings', {
            type: 'geojson',
            data: geojsonData || { type: 'FeatureCollection', features: [] },
            cluster: true,
            clusterMaxZoom: 14,
            clusterRadius: 50,
          });

          map.addLayer({
            id: 'clusters',
            type: 'circle',
            source: 'buildings',
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
            id: 'cluster-count',
            type: 'symbol',
            source: 'buildings',
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
            id: 'buildings-layer',
            type: 'circle',
            source: 'buildings',
            filter: ['!', ['has', 'point_count']],
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

          map.on('click', 'buildings-layer', (e) => {
            if (!e.features || e.features.length === 0) return;
            const feature = e.features[0];
            const props = feature.properties || {};
            const coords = (feature.geometry as GeoJSON.Point).coordinates.slice() as [number, number];

            if (popupRef.current) popupRef.current.remove();

            const pollutantsHtml = (props.pollutants || '')
              .split(',')
              .filter(Boolean)
              .map(
                (p: string) =>
                  `<span style="display:inline-block;padding:2px 6px;margin:2px;border-radius:9999px;font-size:11px;background:${POLLUTANT_COLORS[p.trim() as PollutantType] || '#64748b'}20;color:${POLLUTANT_COLORS[p.trim() as PollutantType] || '#64748b'};font-weight:500;">${p.trim()}</span>`,
              )
              .join('');

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
                  <p style="font-size:12px;color:#6b7280;margin:0 0 8px;">${props.postal_code || ''} ${props.city || ''} (${props.canton || ''})</p>
                  <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <span style="padding:2px 8px;border-radius:9999px;font-size:11px;font-weight:600;background:${riskBg};color:${RISK_COLORS[props.overall_risk_level as RiskLevel] || '#64748b'};">
                      ${props.overall_risk_level || 'N/A'}
                    </span>
                    ${props.risk_score ? `<span style="font-size:12px;color:#6b7280;">Score: ${props.risk_score}</span>` : ''}
                  </div>
                  <div style="margin-bottom:8px;">${pollutantsHtml || '<span style="font-size:12px;color:#9ca3af;">-</span>'}</div>
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

          map.on('click', 'clusters', (e) => {
            const features = map.queryRenderedFeatures(e.point, { layers: ['clusters'] });
            if (!features.length) return;
            const clusterId = features[0].properties?.cluster_id;
            const source = map.getSource('buildings') as import('mapbox-gl').GeoJSONSource;
            source.getClusterExpansionZoom(clusterId, (err, zoom) => {
              if (err) return;
              map.easeTo({
                center: (features[0].geometry as GeoJSON.Point).coordinates as [number, number],
                zoom: zoom ?? undefined,
              });
            });
          });

          map.on('mouseenter', 'clusters', () => {
            map.getCanvas().style.cursor = 'pointer';
          });
          map.on('mouseleave', 'clusters', () => {
            map.getCanvas().style.cursor = '';
          });
          map.on('mouseenter', 'buildings-layer', () => {
            map.getCanvas().style.cursor = 'pointer';
          });
          map.on('mouseleave', 'buildings-layer', () => {
            map.getCanvas().style.cursor = '';
          });
        });

        map.on('error', () => {
          setMapError(t('app.error'));
          setIsLoading(false);
        });

        mapRef.current = map;
      } catch {
        if (!cancelled) {
          setMapError(t('app.error'));
          setIsLoading(false);
        }
      }
    };

    void initializeMap();

    return () => {
      cancelled = true;
      if (popupRef.current) popupRef.current.remove();
      localMap?.remove();
    };
  }, [geojsonData, navigate, t]);

  // Update data source when geojsonData changes after map init
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !geojsonData) return;

    const source = map.getSource('buildings') as mapboxgl.GeoJSONSource;
    if (source) {
      source.setData(geojsonData);
    }
  }, [geojsonData]);

  // Apply filters
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    try {
      const filters: any[] = ['all'];

      if (activePollutants.size < POLLUTANT_TYPES.length) {
        const pollutantFilters: any[] = ['any'];
        activePollutants.forEach((p) => {
          pollutantFilters.push(['in', p, ['get', 'pollutants']]);
        });
        if (pollutantFilters.length > 1) filters.push(pollutantFilters);
      }

      if (activeRiskLevels.size < RISK_LEVELS.length) {
        filters.push(['in', ['get', 'overall_risk_level'], ['literal', Array.from(activeRiskLevels)]]);
      }

      if (filterCanton) {
        filters.push(['==', ['get', 'canton'], filterCanton]);
      }

      map.setFilter('buildings-layer', filters.length > 1 ? filters : null);
    } catch {}
  }, [activePollutants, activeRiskLevels, filterCanton]);

  return (
    <div className="h-[calc(100vh-120px)] relative rounded-xl overflow-hidden border border-gray-200 dark:border-slate-700 shadow-sm">
      {/* Map container */}
      <div ref={mapContainer} className="absolute inset-0" />

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-white/80 dark:bg-slate-900/80 flex items-center justify-center z-10">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin text-red-600 mx-auto mb-2" />
            <p className="text-sm text-gray-500 dark:text-slate-400">{t('app.loading')}</p>
          </div>
        </div>
      )}

      {/* Error overlay */}
      {effectiveError && (
        <div className="absolute inset-0 bg-white/90 dark:bg-slate-900/90 flex items-center justify-center z-10">
          <div className="text-center p-6">
            <MapPin className="w-10 h-10 text-gray-300 dark:text-slate-600 mx-auto mb-2" />
            <p className="text-sm text-gray-600 dark:text-slate-400">{effectiveError}</p>
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

      {/* Controls Panel */}
      {showControls && (
        <div className="absolute top-14 left-4 z-20 w-64 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-gray-200 dark:border-slate-700 p-4 space-y-4 max-h-[calc(100%-80px)] overflow-y-auto">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{t('map.filter')}</h3>

          {/* Pollutant Filters */}
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-2">
              {t('sample.pollutant_type')}
            </p>
            <div className="space-y-1.5">
              {POLLUTANT_TYPES.map((p) => (
                <label key={p} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={activePollutants.has(p)}
                    onChange={() => togglePollutant(p)}
                    className="w-3.5 h-3.5 rounded border-gray-300 dark:border-slate-600 text-red-600 focus:ring-red-500"
                  />
                  <span
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: POLLUTANT_COLORS[p] || '#64748b' }}
                  />
                  <span className="text-sm text-gray-700 dark:text-slate-200">{t(`pollutant.${p}`)}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Risk Level Filters */}
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-2">
              {t('sample.risk_level')}
            </p>
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
              {t('building.canton')}
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
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-4 right-4 z-20 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-gray-200 dark:border-slate-700 p-3">
        <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-2">
          {t('map.legend')}
        </p>
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
      </div>
    </div>
  );
}
