"""swissBUILDINGS3D spatial enrichment service — fetches footprint, height, roof type, volume from swisstopo."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_geo_context import BuildingGeoContext
from app.services.source_registry_service import SourceRegistryService

logger = logging.getLogger(__name__)

# Cache TTL — don't re-fetch if data is less than 7 days old
CACHE_TTL_DAYS = 7
DEFAULT_TIMEOUT = 15.0

# geo.admin REST API
IDENTIFY_URL = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"

# swissBUILDINGS3D 3.0 layer on geo.admin
LAYER_ID = "ch.swisstopo.swissbuildings3d_3_0.v2"

SOURCE_KEY = "swissbuildings3d"
SOURCE_VERSION = "swissbuildings3d-v3.0"
SPATIAL_CACHE_KEY = "spatial_enrichment"


def _build_map_extent(lon: float, lat: float, buffer: float = 0.005) -> str:
    """Build a small map extent around the point for the identify call."""
    return f"{lon - buffer},{lat - buffer},{lon + buffer},{lat + buffer}"


def _parse_spatial_response(features: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Extract footprint, height, roof type, volume from swissBUILDINGS3D identify response."""
    if not features:
        return None

    feature = features[0]
    attrs = feature.get("attributes") or feature.get("properties") or {}
    geom = feature.get("geometry") or {}

    if not attrs:
        return None

    # Extract key spatial attributes
    # swissBUILDINGS3D attribute names vary; try known fields
    height_m = attrs.get("gebaeudehoehe") or attrs.get("building_height") or attrs.get("hoehe") or attrs.get("height")
    roof_type = attrs.get("dachform") or attrs.get("roof_type") or attrs.get("dachtyp")
    volume_m3 = attrs.get("volumen") or attrs.get("volume") or attrs.get("gebaeudevolumen")
    surface_m2 = (
        attrs.get("grundflaeche") or attrs.get("surface") or attrs.get("gebaeudeflaeche") or attrs.get("footprint_area")
    )
    floors = attrs.get("geschosszahl") or attrs.get("floors") or attrs.get("anzahl_geschosse")

    # Build WKT from geometry if available (rings → polygon)
    footprint_wkt: str | None = None
    if geom.get("rings"):
        rings = geom["rings"]
        if rings and rings[0]:
            coords_str = ", ".join(f"{p[0]} {p[1]}" for p in rings[0])
            footprint_wkt = f"POLYGON(({coords_str}))"
    elif geom.get("coordinates"):
        coords = geom["coordinates"]
        if coords and isinstance(coords[0], list) and isinstance(coords[0][0], list):
            coords_str = ", ".join(f"{p[0]} {p[1]}" for p in coords[0])
            footprint_wkt = f"POLYGON(({coords_str}))"

    # Parse numeric values safely
    def _to_float(val: Any) -> float | None:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    return {
        "footprint_wkt": footprint_wkt,
        "height_m": _to_float(height_m),
        "roof_type": str(roof_type) if roof_type else None,
        "volume_m3": _to_float(volume_m3),
        "surface_m2": _to_float(surface_m2),
        "floors": int(floors) if floors else None,
        "source": LAYER_ID,
        "source_version": SOURCE_VERSION,
        "raw_attributes": attrs,
    }


class SpatialEnrichmentService:
    """Service for fetching and caching swissBUILDINGS3D spatial data."""

    @staticmethod
    async def fetch_building_footprint(longitude: float, latitude: float) -> dict[str, Any]:
        """Fetch building footprint and 3D attributes from swissBUILDINGS3D.

        Returns: {footprint_wkt, height_m, roof_type, volume_m3, surface_m2, source, fetched_at}
        """
        extent = _build_map_extent(longitude, latitude)
        params = {
            "geometry": f"{longitude},{latitude}",
            "geometryType": "esriGeometryPoint",
            "sr": "4326",
            "layers": f"all:{LAYER_ID}",
            "tolerance": "30",
            "mapExtent": extent,
            "imageDisplay": "500,500,96",
            "returnGeometry": "true",
            "f": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.get(IDENTIFY_URL, params=params)
                response.raise_for_status()
                data = response.json()
                features = data.get("results") or []
                parsed = _parse_spatial_response(features)
                if parsed:
                    parsed["fetched_at"] = datetime.now(UTC).isoformat()
                    return parsed
                return {
                    "error": "no_data",
                    "detail": "Aucune donnee swissBUILDINGS3D a cette position",
                    "fetched_at": datetime.now(UTC).isoformat(),
                }
        except httpx.TimeoutException:
            logger.warning("swissBUILDINGS3D timeout for (%s, %s)", longitude, latitude)
            return {"error": "timeout", "detail": "Delai d'attente depasse pour swissBUILDINGS3D"}
        except Exception:
            logger.warning("swissBUILDINGS3D fetch failed for (%s, %s)", longitude, latitude, exc_info=True)
            return {"error": "fetch_failed", "detail": "Erreur lors de la recuperation swissBUILDINGS3D"}

    @staticmethod
    async def enrich_building_spatial(
        db: AsyncSession,
        building_id: uuid.UUID,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        """Enrich a building with swissBUILDINGS3D data.

        Updates Building fields: volume_m3, surface_area_m2.
        Stores full spatial data in BuildingGeoContext cache (under 'spatial_enrichment' key).
        Records health event in source registry.
        """
        # Load building
        result = await db.execute(select(Building).where(Building.id == building_id))
        building = result.scalar_one_or_none()
        if building is None:
            raise ValueError(f"Building {building_id} not found")

        if building.longitude is None or building.latitude is None:
            return {
                "error": "no_coordinates",
                "detail": "Le batiment n'a pas de coordonnees pour la recherche spatiale",
            }

        # Check cache
        if not force:
            cached_data = await SpatialEnrichmentService._get_cached(db, building_id)
            if cached_data is not None:
                return cached_data

        # Fetch fresh data
        spatial_data = await SpatialEnrichmentService.fetch_building_footprint(building.longitude, building.latitude)

        # Record health event
        try:
            if "error" not in spatial_data:
                await SourceRegistryService.record_health_event(db, SOURCE_KEY, "healthy")
            else:
                await SourceRegistryService.record_health_event(
                    db,
                    SOURCE_KEY,
                    "degraded",
                    description=spatial_data.get("detail", "No spatial data returned"),
                )
        except Exception:
            logger.debug("Failed to record source health event for swissbuildings3d", exc_info=True)

        # Update building fields if we have data
        if "error" not in spatial_data:
            if spatial_data.get("volume_m3") and not building.volume_m3:
                building.volume_m3 = spatial_data["volume_m3"]
            if spatial_data.get("surface_m2") and not building.surface_area_m2:
                building.surface_area_m2 = spatial_data["surface_m2"]

        # Store in BuildingGeoContext (upsert, merge with existing context_data)
        existing = await db.execute(select(BuildingGeoContext).where(BuildingGeoContext.building_id == building_id))
        cached = existing.scalar_one_or_none()
        now = datetime.now(UTC)

        enrichment_record = {
            **spatial_data,
            "fetched_at": now.isoformat(),
        }

        if cached:
            ctx = dict(cached.context_data or {})
            ctx[SPATIAL_CACHE_KEY] = enrichment_record
            cached.context_data = ctx
            cached.updated_at = now
        else:
            geo_ctx = BuildingGeoContext(
                building_id=building_id,
                context_data={SPATIAL_CACHE_KEY: enrichment_record},
                fetched_at=now,
                source_version=SOURCE_VERSION,
            )
            db.add(geo_ctx)

        await db.commit()
        return enrichment_record

    @staticmethod
    async def get_building_spatial(
        db: AsyncSession,
        building_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get cached spatial enrichment data, or fetch fresh if missing/stale."""
        cached = await SpatialEnrichmentService._get_cached(db, building_id)
        if cached is not None:
            cached["cached"] = True
            return cached

        # Fetch fresh
        result = await SpatialEnrichmentService.enrich_building_spatial(db, building_id)
        if "error" not in result:
            result["cached"] = False
        return result

    @staticmethod
    async def _get_cached(
        db: AsyncSession,
        building_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Return cached spatial data if fresh enough, else None."""
        existing = await db.execute(select(BuildingGeoContext).where(BuildingGeoContext.building_id == building_id))
        cached = existing.scalar_one_or_none()
        if cached and cached.context_data and SPATIAL_CACHE_KEY in (cached.context_data or {}):
            spatial = cached.context_data[SPATIAL_CACHE_KEY]
            fetched_at_str = spatial.get("fetched_at")
            if fetched_at_str:
                try:
                    fetched_at = datetime.fromisoformat(fetched_at_str)
                    if fetched_at.tzinfo is None:
                        fetched_at = fetched_at.replace(tzinfo=UTC)
                    age = datetime.now(UTC) - fetched_at
                    if age < timedelta(days=CACHE_TTL_DAYS):
                        return dict(spatial)
                except (ValueError, TypeError):
                    pass
        return None
