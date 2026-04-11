import { useEffect, useRef, useState, useCallback } from 'react';
import mapboxgl from 'mapbox-gl';
import { useIsochrone } from '@/hooks/useIsochrone';
import { IsochroneControls } from '@/components/IsochroneControls';
import type { IsochroneProfile } from '@/components/IsochroneControls';
import type { IsochroneContour } from '@/api/isochrone';
import { Loader2, AlertTriangle, MapPin } from 'lucide-react';

function getMapboxToken() {
  return import.meta.env.VITE_MAPBOX_TOKEN;
}

const CONTOUR_STYLES: Record<number, { color: string; opacity: number }> = {
  5: { color: '#00b33c', opacity: 0.25 },
  10: { color: '#f59e0b', opacity: 0.2 },
  15: { color: '#ef4444', opacity: 0.15 },
};

interface IsochroneMapPanelProps {
  buildingId: string;
  latitude: number;
  longitude: number;
}

export default function IsochroneMapPanel({ buildingId, latitude, longitude }: IsochroneMapPanelProps) {
  const MAPBOX_TOKEN = getMapboxToken();
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markerRef = useRef<mapboxgl.Marker | null>(null);

  const [profile, setProfile] = useState<IsochroneProfile>('walking');
  const [visibleMinutes, setVisibleMinutes] = useState<Set<number>>(new Set([5, 10, 15]));

  const { data, isLoading, isError, error } = useIsochrone(buildingId, profile);

  const toggleMinutes = useCallback((m: number) => {
    setVisibleMinutes((prev) => {
      const next = new Set(prev);
      if (next.has(m)) next.delete(m);
      else next.add(m);
      return next;
    });
  }, []);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || !MAPBOX_TOKEN || mapRef.current) return;

    mapboxgl.accessToken = MAPBOX_TOKEN;
    const map = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: [longitude, latitude],
      zoom: 13,
    });
    map.addControl(new mapboxgl.NavigationControl(), 'top-right');

    const marker = new mapboxgl.Marker({ color: '#2563eb' }).setLngLat([longitude, latitude]).addTo(map);

    mapRef.current = map;
    markerRef.current = marker;

    return () => {
      marker.remove();
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
  }, [latitude, longitude]);

  // Update isochrone layers
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !data?.contours) return;

    const updateLayers = () => {
      // Remove old layers/sources
      for (const minutes of [15, 10, 5]) {
        const layerId = `isochrone-${minutes}`;
        const outlineId = `isochrone-outline-${minutes}`;
        if (map.getLayer(outlineId)) map.removeLayer(outlineId);
        if (map.getLayer(layerId)) map.removeLayer(layerId);
        if (map.getSource(layerId)) map.removeSource(layerId);
      }

      // Add new layers (largest first so smaller ones render on top)
      const sorted = [...data.contours].sort((a, b) => b.minutes - a.minutes);
      for (const contour of sorted) {
        addContourLayer(map, contour, visibleMinutes.has(contour.minutes));
      }
    };

    if (map.isStyleLoaded()) {
      updateLayers();
    } else {
      map.on('load', updateLayers);
    }
  }, [data, visibleMinutes]);

  const mobilityScore = data?.mobility_score ?? null;

  if (!MAPBOX_TOKEN) {
    return (
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-6 text-center">
        <AlertTriangle className="w-8 h-8 text-yellow-500 mx-auto mb-2" />
        <p className="text-sm text-yellow-700 dark:text-yellow-300">Mapbox token not configured</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MapPin className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Mobilité & Isochrones</h3>
          {mobilityScore !== null && (
            <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
              {mobilityScore}/10
            </span>
          )}
        </div>
        {isLoading && <Loader2 className="w-4 h-4 animate-spin text-gray-400" />}
      </div>

      {/* Controls */}
      <IsochroneControls
        profile={profile}
        onProfileChange={setProfile}
        visibleMinutes={visibleMinutes}
        onToggleMinutes={toggleMinutes}
      />

      {/* Error */}
      {isError && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-700 dark:text-red-300">
          <AlertTriangle className="w-4 h-4 inline mr-1" />
          {(error as Error)?.message || 'Erreur de chargement des isochrones'}
        </div>
      )}

      {/* API-level error */}
      {data?.error && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3 text-sm text-yellow-700 dark:text-yellow-300">
          <AlertTriangle className="w-4 h-4 inline mr-1" />
          {data.error}
        </div>
      )}

      {/* Map */}
      <div
        ref={mapContainer}
        className="w-full h-[400px] rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden"
      />

      {/* Cache indicator */}
      {data?.cached && (
        <p className="text-xs text-gray-400 dark:text-gray-500">Données en cache</p>
      )}
    </div>
  );
}

function addContourLayer(map: mapboxgl.Map, contour: IsochroneContour, visible: boolean) {
  const layerId = `isochrone-${contour.minutes}`;
  const style = CONTOUR_STYLES[contour.minutes] || { color: '#666666', opacity: 0.15 };

  map.addSource(layerId, {
    type: 'geojson',
    data: { type: 'Feature', geometry: contour.geometry, properties: { minutes: contour.minutes } },
  });

  map.addLayer({
    id: layerId,
    type: 'fill',
    source: layerId,
    paint: {
      'fill-color': style.color,
      'fill-opacity': visible ? style.opacity : 0,
    },
  });

  map.addLayer({
    id: `isochrone-outline-${contour.minutes}`,
    type: 'line',
    source: layerId,
    paint: {
      'line-color': style.color,
      'line-width': 2,
      'line-opacity': visible ? 0.8 : 0,
    },
  });
}
