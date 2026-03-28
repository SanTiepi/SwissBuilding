"""geo.admin context overlay service — fetches building-level public context from Swiss federal geodata."""

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

# geo.admin REST API base
BASE_URL = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"

# Layers of interest with French labels
LAYERS: dict[str, dict[str, str]] = {
    "radon": {
        "layer_id": "ch.bag.radonkarte",
        "label": "Radon",
    },
    "noise_road": {
        "layer_id": "ch.bafu.laerm-strassenlaerm_tag",
        "label": "Bruit routier (jour)",
    },
    "noise_rail": {
        "layer_id": "ch.bafu.laerm-bahnlaerm_tag",
        "label": "Bruit ferroviaire (jour)",
    },
    "solar": {
        "layer_id": "ch.bfe.solarenergie-eignung-daecher",
        "label": "Potentiel solaire",
    },
    "natural_hazards": {
        "layer_id": "ch.bafu.showme-kantone_hochwasser",
        "label": "Dangers naturels (crues)",
    },
    "groundwater_protection": {
        "layer_id": "ch.bafu.grundwasserschutzzonen",
        "label": "Protection des eaux souterraines",
    },
    "contaminated_sites": {
        "layer_id": "ch.bafu.kataster-belasteter-standorte-oeffTransport",
        "label": "Sites contamines",
    },
    "heritage_isos": {
        "layer_id": "ch.bak.bundesinventar-schuetzenswerte-ortsbilder",
        "label": "Patrimoine ISOS",
    },
    "public_transport": {
        "layer_id": "ch.are.gueteklassen_oev",
        "label": "Qualite desserte TP",
    },
    "thermal_networks": {
        "layer_id": "ch.bfe.fernwaermenetze",
        "label": "Reseaux de chaleur",
    },
}


def _build_map_extent(lon: float, lat: float, buffer: float = 0.01) -> str:
    """Build a small map extent around the point for the identify call."""
    return f"{lon - buffer},{lat - buffer},{lon + buffer},{lat + buffer}"


def _parse_layer_response(layer_key: str, features: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Extract meaningful attributes from geo.admin identify response features."""
    if not features:
        return None

    # Take the first (closest) feature
    feature = features[0]
    attrs = feature.get("attributes") or feature.get("properties") or {}
    if not attrs:
        return None

    result: dict[str, Any] = {
        "source": LAYERS[layer_key]["layer_id"],
        "label": LAYERS[layer_key]["label"],
        "raw_attributes": attrs,
    }

    # Layer-specific parsing for key values
    if layer_key == "radon":
        result["zone"] = attrs.get("zone") or attrs.get("radonrisiko") or attrs.get("description")
        result["value"] = attrs.get("radon_bq_m3") or attrs.get("description")

    elif layer_key in ("noise_road", "noise_rail"):
        result["level_db"] = attrs.get("lre_d") or attrs.get("lr_d") or attrs.get("description")

    elif layer_key == "solar":
        result["suitability"] = attrs.get("klasse") or attrs.get("eignung") or attrs.get("description")
        result["potential_kwh"] = attrs.get("stromertrag") or attrs.get("gstrahlung")

    elif layer_key == "natural_hazards":
        result["hazard_level"] = attrs.get("gefahrenstufe") or attrs.get("description")

    elif layer_key == "groundwater_protection":
        result["zone_type"] = attrs.get("schutzzone") or attrs.get("typ") or attrs.get("description")

    elif layer_key == "contaminated_sites":
        result["status"] = attrs.get("status") or attrs.get("description")
        result["category"] = attrs.get("kategorie") or attrs.get("belastungskategorie")

    elif layer_key == "heritage_isos":
        result["status"] = attrs.get("ortsbildbedeutung") or attrs.get("description")
        result["name"] = attrs.get("ortsbildname") or attrs.get("name")

    elif layer_key == "public_transport":
        result["quality_class"] = attrs.get("klasse") or attrs.get("gueteklasse") or attrs.get("description")

    elif layer_key == "thermal_networks":
        result["network_name"] = attrs.get("name") or attrs.get("description")
        result["status"] = attrs.get("status")

    return result


async def fetch_context(
    longitude: float,
    latitude: float,
    layers: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch geo context for a coordinate point from geo.admin.

    Returns a dict keyed by layer_key with parsed attributes per layer.
    Layers that have no data at the coordinate are omitted.
    """
    target_layers = layers or list(LAYERS.keys())
    results: dict[str, Any] = {}
    extent = _build_map_extent(longitude, latitude)

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        for layer_key in target_layers:
            if layer_key not in LAYERS:
                continue
            layer_id = LAYERS[layer_key]["layer_id"]
            params = {
                "geometry": f"{longitude},{latitude}",
                "geometryType": "esriGeometryPoint",
                "sr": "4326",
                "layers": f"all:{layer_id}",
                "tolerance": "50",
                "mapExtent": extent,
                "imageDisplay": "500,500,96",
                "returnGeometry": "false",
                "f": "json",
            }
            try:
                response = await client.get(BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
                features = data.get("results") or []
                parsed = _parse_layer_response(layer_key, features)
                if parsed:
                    results[layer_key] = parsed
            except Exception:
                logger.warning(
                    "geo.admin layer %s fetch failed for (%s, %s)", layer_key, longitude, latitude, exc_info=True
                )
                # Skip this layer — don't fail the whole request

    return results


async def enrich_building_context(
    db: AsyncSession,
    building_id: uuid.UUID,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Fetch and store geo context for a building. Returns the context dict."""
    # Load building to get coordinates
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    if building.longitude is None or building.latitude is None:
        return {"error": "no_coordinates", "detail": "Building has no coordinates for geo context lookup"}

    # Check cache
    if not force:
        existing = await db.execute(select(BuildingGeoContext).where(BuildingGeoContext.building_id == building_id))
        cached = existing.scalar_one_or_none()
        if cached and cached.fetched_at:
            age = datetime.now(UTC) - cached.fetched_at.replace(tzinfo=UTC)
            if age < timedelta(days=CACHE_TTL_DAYS):
                return cached.context_data or {}

    # Fetch fresh data
    context_data = await fetch_context(building.longitude, building.latitude)

    # Record health events for geo.admin sources
    try:
        if context_data:
            await SourceRegistryService.record_health_event(db, "geo_admin_radon", "healthy")
        else:
            await SourceRegistryService.record_health_event(
                db, "geo_admin_radon", "degraded", description="No context data returned"
            )
    except Exception:
        logger.debug("Failed to record source health event", exc_info=True)

    # Upsert
    existing = await db.execute(select(BuildingGeoContext).where(BuildingGeoContext.building_id == building_id))
    cached = existing.scalar_one_or_none()
    now = datetime.now(UTC)

    if cached:
        cached.context_data = context_data
        cached.fetched_at = now
        cached.source_version = "geo.admin-v1"
    else:
        geo_ctx = BuildingGeoContext(
            building_id=building_id,
            context_data=context_data,
            fetched_at=now,
            source_version="geo.admin-v1",
        )
        db.add(geo_ctx)

    await db.commit()
    return context_data


async def get_building_context(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> dict[str, Any]:
    """Get stored geo context for a building. Returns cached data or fetches fresh."""
    existing = await db.execute(select(BuildingGeoContext).where(BuildingGeoContext.building_id == building_id))
    cached = existing.scalar_one_or_none()

    if cached and cached.fetched_at:
        age = datetime.now(UTC) - cached.fetched_at.replace(tzinfo=UTC)
        if age < timedelta(days=CACHE_TTL_DAYS):
            return {
                "context": cached.context_data or {},
                "fetched_at": cached.fetched_at.isoformat(),
                "source_version": cached.source_version,
                "cached": True,
            }

    # Fetch fresh
    context_data = await enrich_building_context(db, building_id)
    if "error" in context_data:
        return context_data
    return {
        "context": context_data,
        "fetched_at": datetime.now(UTC).isoformat(),
        "source_version": "geo.admin-v1",
        "cached": False,
    }
