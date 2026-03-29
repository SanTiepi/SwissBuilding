import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import type { BuildingRiskPoint } from '@/api/portfolioRisk';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Loader2, MapPin } from 'lucide-react';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

const GRADE_COLORS: Record<string, string> = {
  A: '#22c55e',
  B: '#3b82f6',
  C: '#eab308',
  D: '#f97316',
  F: '#ef4444',
};

interface Props {
  buildings: BuildingRiskPoint[];
}

export default function PortfolioRiskMapEvidence({ buildings }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import('mapbox-gl').Map | null>(null);
  const popupRef = useRef<import('mapbox-gl').Popup | null>(null);

  const [isMapReady, setIsMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const effectiveError = !MAPBOX_TOKEN ? t('map.no_data') : mapError;

  const isDark = document.documentElement.classList.contains('dark');

  const buildGeoJSON = useCallback((): GeoJSON.FeatureCollection => {
    return {
      type: 'FeatureCollection',
      features: buildings.map((b) => ({
        type: 'Feature' as const,
        geometry: {
          type: 'Point' as const,
          coordinates: [b.longitude!, b.latitude!],
        },
        properties: {
          id: b.building_id,
          address: b.address,
          city: b.city,
          canton: b.canton,
          score: b.score,
          grade: b.grade,
          risk_level: b.risk_level,
          open_actions_count: b.open_actions_count,
          critical_actions_count: b.critical_actions_count,
        },
      })),
    };
  }, [buildings]);

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

          const geojson = buildGeoJSON();

          map.addSource('risk-buildings', {
            type: 'geojson',
            data: geojson,
            cluster: true,
            clusterMaxZoom: 14,
            clusterRadius: 50,
          });

          // Clusters
          map.addLayer({
            id: 'risk-clusters',
            type: 'circle',
            source: 'risk-buildings',
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
            id: 'risk-cluster-count',
            type: 'symbol',
            source: 'risk-buildings',
            filter: ['has', 'point_count'],
            layout: {
              'text-field': ['get', 'point_count_abbreviated'],
              'text-font': ['DIN Offc Pro Medium', 'Arial Unicode MS Bold'],
              'text-size': 13,
            },
            paint: { 'text-color': '#ffffff' },
          });

          // Individual points: color by grade, size by critical actions
          map.addLayer({
            id: 'risk-points',
            type: 'circle',
            source: 'risk-buildings',
            filter: ['!', ['has', 'point_count']],
            paint: {
              'circle-radius': [
                'interpolate',
                ['linear'],
                ['get', 'critical_actions_count'],
                0,
                6,
                1,
                8,
                3,
                11,
                5,
                14,
                10,
                18,
              ],
              'circle-color': [
                'match',
                ['get', 'grade'],
                'A',
                GRADE_COLORS.A,
                'B',
                GRADE_COLORS.B,
                'C',
                GRADE_COLORS.C,
                'D',
                GRADE_COLORS.D,
                'F',
                GRADE_COLORS.F,
                '#94a3b8',
              ],
              'circle-opacity': 0.85,
              'circle-stroke-width': 1.5,
              'circle-stroke-color': '#ffffff',
            },
          });

          // Click handler for individual points
          map.on('click', 'risk-points', (e) => {
            if (!e.features || e.features.length === 0) return;
            const feature = e.features[0];
            const props = feature.properties || {};
            const coords = (feature.geometry as GeoJSON.Point).coordinates.slice() as [number, number];

            if (popupRef.current) popupRef.current.remove();

            const gradeColor = GRADE_COLORS[props.grade] || '#64748b';

            const popup = new mapboxgl.Popup({ offset: 15, maxWidth: '280px' })
              .setLngLat(coords)
              .setHTML(
                `
                <div style="font-family:system-ui,sans-serif;">
                  <p style="font-weight:600;font-size:14px;margin:0 0 4px;">${props.address || '-'}</p>
                  <p style="font-size:12px;color:#6b7280;margin:0 0 8px;">${props.city || ''}</p>
                  <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <span style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;font-size:13px;font-weight:700;background:${gradeColor}20;color:${gradeColor};">
                      ${props.grade || '?'}
                    </span>
                    <span style="font-size:13px;color:#374151;">Score: ${props.score ?? '-'}</span>
                  </div>
                  <p style="font-size:12px;color:#6b7280;margin:0 0 8px;">
                    ${t('portfolio.critical_actions')}: ${props.critical_actions_count ?? 0}
                  </p>
                  <button id="popup-risk-${props.id}" style="width:100%;padding:6px 12px;font-size:12px;font-weight:500;color:white;background:#dc2626;border:none;border-radius:6px;cursor:pointer;">
                    ${t('form.view')}
                  </button>
                </div>
              `,
              )
              .addTo(map);

            popupRef.current = popup;

            setTimeout(() => {
              const btn = document.getElementById(`popup-risk-${props.id}`);
              if (btn) {
                btn.addEventListener('click', () => {
                  navigate(`/buildings/${props.id}`);
                });
              }
            }, 50);
          });

          // Cluster click to zoom
          map.on('click', 'risk-clusters', (e) => {
            const features = map.queryRenderedFeatures(e.point, { layers: ['risk-clusters'] });
            if (!features.length) return;
            const clusterId = features[0].properties?.cluster_id;
            const source = map.getSource('risk-buildings') as import('mapbox-gl').GeoJSONSource;
            source.getClusterExpansionZoom(clusterId, (err, zoom) => {
              if (err) return;
              map.easeTo({
                center: (features[0].geometry as GeoJSON.Point).coordinates as [number, number],
                zoom: zoom ?? undefined,
              });
            });
          });

          // Cursor changes
          map.on('mouseenter', 'risk-points', () => {
            map.getCanvas().style.cursor = 'pointer';
          });
          map.on('mouseleave', 'risk-points', () => {
            map.getCanvas().style.cursor = '';
          });
          map.on('mouseenter', 'risk-clusters', () => {
            map.getCanvas().style.cursor = 'pointer';
          });
          map.on('mouseleave', 'risk-clusters', () => {
            map.getCanvas().style.cursor = '';
          });

          // Fit bounds to data
          if (geojson.features.length > 0) {
            const lngs = geojson.features.map(
              (f) => (f.geometry as GeoJSON.Point).coordinates[0],
            );
            const lats = geojson.features.map(
              (f) => (f.geometry as GeoJSON.Point).coordinates[1],
            );
            map.fitBounds(
              [
                [Math.min(...lngs) - 0.05, Math.min(...lats) - 0.05],
                [Math.max(...lngs) + 0.05, Math.max(...lats) + 0.05],
              ],
              { padding: 40, maxZoom: 14 },
            );
          }
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

  // Update data when buildings change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapReady) return;

    const source = map.getSource('risk-buildings') as import('mapbox-gl').GeoJSONSource;
    if (source) {
      source.setData(buildGeoJSON());
    }
  }, [buildings, isMapReady, buildGeoJSON]);

  return (
    <div className="h-[500px] relative rounded-xl overflow-hidden border border-gray-200 dark:border-slate-700 shadow-sm">
      <div ref={mapContainer} className="absolute inset-0" />

      {/* Loading overlay */}
      {!isMapReady && MAPBOX_TOKEN && !effectiveError && (
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

      {/* Legend */}
      <div className="absolute bottom-4 right-4 z-20 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-gray-200 dark:border-slate-700 p-3">
        <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-2">
          Evidence Grade
        </p>
        <div className="space-y-1">
          {(['A', 'B', 'C', 'D', 'F'] as const).map((g) => (
            <div key={g} className="flex items-center gap-2">
              <span
                className="w-3 h-3 rounded-full border border-white dark:border-slate-800 shadow-sm"
                style={{ backgroundColor: GRADE_COLORS[g] }}
              />
              <span className="text-xs text-gray-600 dark:text-slate-300">{g}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
