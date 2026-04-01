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

# Expected attribute keys per layer — used for schema drift detection
_LAYER_EXPECTED_KEYS: dict[str, list[str]] = {
    "radon": ["zone", "radonrisiko", "description", "radon_bq_m3"],
    "noise_road": ["lre_d", "lr_d", "description"],
    "noise_rail": ["lre_d", "lr_d", "description"],
    "solar": ["klasse", "eignung", "description", "stromertrag", "gstrahlung"],
    "natural_hazards": ["gefahrenstufe", "description"],
    "groundwater_protection": ["schutzzone", "typ", "description"],
    "contaminated_sites": ["status", "description", "kategorie", "belastungskategorie"],
    "heritage_isos": ["ortsbildbedeutung", "description", "ortsbildname", "name"],
    "public_transport": ["klasse", "gueteklasse", "description"],
    "thermal_networks": ["name", "description", "status"],
    "seismic": ["zone", "erdbebenzone", "klasse", "bauwerksklasse"],
    "flood_zones": ["gefahrenstufe", "stufe", "wiederkehrperiode"],
    "aircraft_noise": ["lr_tag", "db", "lrpegel"],
    "building_zones": ["zone_type", "zonentyp", "bezeichnung"],
    "mobile_coverage": ["technology", "provider"],
    "broadband": ["technology", "technologie", "max_speed"],
    "ev_charging": ["distance", "entfernung"],
    "protected_monuments": ["kategorie", "category", "klasse"],
    "agricultural_zones": ["eignung", "klasse", "zone"],
    "forest_reserves": ["name", "bezeichnung", "reservatname"],
    "military_zones": ["distance", "entfernung"],
    "accident_sites": ["name", "bezeichnung", "betrieb"],
    "groundwater_areas": ["zone", "schutzzone", "typ"],
    "landslides": ["stufe", "level", "intensitaet"],
}

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
    "seismic": {
        "layer_id": "ch.bafu.erdbeben-erdbebenzonen",
        "label": "Zone sismique",
    },
    "flood_zones": {
        "layer_id": "ch.bafu.gefahrenkarte-hochwasser",
        "label": "Carte de danger crues",
    },
    "aircraft_noise": {
        "layer_id": "ch.bazl.laermbelastungskataster-zivilflugplaetze",
        "label": "Bruit aerien",
    },
    "building_zones": {
        "layer_id": "ch.are.bauzonen",
        "label": "Zones a batir",
    },
    "mobile_coverage": {
        "layer_id": "ch.bakom.mobilnetz-5g",
        "label": "Couverture 5G",
    },
    "broadband": {
        "layer_id": "ch.bakom.breitband-technologien",
        "label": "Haut debit",
    },
    "ev_charging": {
        "layer_id": "ch.bfe.ladestellen-elektromobilitaet",
        "label": "Bornes de recharge EV",
    },
    "protected_monuments": {
        "layer_id": "ch.bak.bundesinventar-schuetzenswerte-denkmaler",
        "label": "Monuments proteges",
    },
    "agricultural_zones": {
        "layer_id": "ch.blw.bodeneignungskarte",
        "label": "Aptitude des sols",
    },
    "forest_reserves": {
        "layer_id": "ch.bafu.waldreservate",
        "label": "Reserves forestieres",
    },
    "military_zones": {
        "layer_id": "ch.vbs.schiessplaetze",
        "label": "Zones militaires",
    },
    "accident_sites": {
        "layer_id": "ch.bafu.stoerfallverordnung",
        "label": "Sites Seveso",
    },
    "groundwater_areas": {
        "layer_id": "ch.bafu.grundwasserschutzareale",
        "label": "Aires de protection des eaux",
    },
    "landslides": {
        "layer_id": "ch.bafu.showme-gemeinden_rutschungen",
        "label": "Glissements de terrain",
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

    elif layer_key == "seismic":
        result["zone"] = attrs.get("zone") or attrs.get("erdbebenzone") or attrs.get("description")
        result["value"] = attrs.get("klasse") or attrs.get("bauwerksklasse")

    elif layer_key == "flood_zones":
        result["hazard_level"] = attrs.get("gefahrenstufe") or attrs.get("stufe") or attrs.get("description")
        period = attrs.get("wiederkehrperiode") or attrs.get("return_period")
        if period is not None:
            result["value"] = f"{period} ans"

    elif layer_key == "aircraft_noise":
        result["level_db"] = attrs.get("lr_tag") or attrs.get("db") or attrs.get("lrpegel")

    elif layer_key == "building_zones":
        result["zone_type"] = attrs.get("zone_type") or attrs.get("zonentyp") or attrs.get("typ")
        result["value"] = attrs.get("bezeichnung") or attrs.get("zone_description") or attrs.get("description")

    elif layer_key == "mobile_coverage":
        result["status"] = "5G disponible" if attrs else "Non couvert"

    elif layer_key == "broadband":
        result["value"] = attrs.get("technology") or attrs.get("technologie")
        speed = attrs.get("max_speed") or attrs.get("geschwindigkeit") or attrs.get("speed_down")
        if speed is not None:
            result["name"] = f"{speed} Mbps"

    elif layer_key == "ev_charging":
        result["status"] = "Borne(s) a proximite" if attrs else "Aucune borne"
        dist = attrs.get("distance") or attrs.get("entfernung")
        if dist is not None:
            result["value"] = f"{dist} m"

    elif layer_key == "protected_monuments":
        result["status"] = "Monument protege" if attrs else "Non classe"
        result["category"] = attrs.get("kategorie") or attrs.get("category") or attrs.get("klasse")

    elif layer_key == "agricultural_zones":
        result["value"] = attrs.get("eignung") or attrs.get("soil_quality") or attrs.get("klasse")
        result["zone"] = attrs.get("zone") or attrs.get("agricultural_zone") or attrs.get("typ")

    elif layer_key == "forest_reserves":
        result["status"] = "Reserve forestiere" if attrs else "Hors reserve"
        result["name"] = attrs.get("name") or attrs.get("bezeichnung") or attrs.get("reservatname")

    elif layer_key == "military_zones":
        result["status"] = "Zone militaire a proximite" if attrs else "Hors zone"
        dist = attrs.get("distance") or attrs.get("entfernung")
        if dist is not None:
            result["value"] = f"{dist} m"

    elif layer_key == "accident_sites":
        result["status"] = "Site Seveso a proximite" if attrs else "Hors perimetre"
        result["name"] = attrs.get("name") or attrs.get("bezeichnung") or attrs.get("betrieb")

    elif layer_key == "groundwater_areas":
        result["zone_type"] = attrs.get("zone") or attrs.get("schutzzone") or attrs.get("azone")
        result["value"] = attrs.get("typ") or attrs.get("zone_type") or attrs.get("art")

    elif layer_key == "landslides":
        result["hazard_level"] = attrs.get("stufe") or attrs.get("level") or attrs.get("intensitaet") or attrs.get("description")

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


def _validate_layer_response(layer_name: str, response_data: dict[str, Any]) -> dict[str, Any]:
    """Validate response from a specific geo.admin layer has expected structure.

    Detect when geo.admin changes response format (schema drift).
    Returns: {valid: bool, drift_detected: bool, missing_keys: [...], detail: str}
    """
    if layer_name not in _LAYER_EXPECTED_KEYS:
        return {"valid": True, "drift_detected": False, "missing_keys": [], "detail": "no_schema_defined"}

    expected = _LAYER_EXPECTED_KEYS[layer_name]
    attrs = response_data.get("raw_attributes") or {}
    if not attrs:
        return {
            "valid": False,
            "drift_detected": True,
            "missing_keys": expected,
            "detail": "no_attributes_in_response",
        }

    # Check if at least one expected key is present
    present = [k for k in expected if k in attrs]
    if not present:
        return {
            "valid": False,
            "drift_detected": True,
            "missing_keys": expected,
            "detail": f"none_of_expected_keys_found: {expected}",
        }

    return {"valid": True, "drift_detected": False, "missing_keys": [], "detail": "ok"}


async def fetch_context_with_fallback(
    longitude: float,
    latitude: float,
    layers: list[str] | None = None,
    *,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """Fetch context with explicit per-layer fallback and health tracking.

    Returns results for successful layers + explicit gap list for failed layers.
    Records per-layer health events when db is provided.
    """
    target_layers = layers or list(LAYERS.keys())
    results: dict[str, Any] = {}
    failed_layers: list[str] = []
    drift_layers: list[str] = []
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
                    # Validate schema
                    validation = _validate_layer_response(layer_key, parsed)
                    if validation["drift_detected"]:
                        drift_layers.append(layer_key)
                        if db:
                            source_name = f"geo_admin_{layer_key}"
                            try:
                                await SourceRegistryService.record_health_event(
                                    db,
                                    source_name,
                                    "schema_drift",
                                    description=f"Schema drift on {layer_key}: {validation['detail']}",
                                )
                            except Exception:
                                logger.debug("Failed to record schema_drift event for %s", layer_key, exc_info=True)
                    results[layer_key] = parsed
                # Record per-layer success health event
                if db:
                    source_name = f"geo_admin_{layer_key}"
                    try:
                        await SourceRegistryService.record_health_event(
                            db, source_name, "healthy", description=f"Layer {layer_key} fetched ok"
                        )
                    except Exception:
                        logger.debug("Failed to record healthy event for %s", layer_key, exc_info=True)
            except Exception:
                logger.warning(
                    "geo.admin layer %s fetch failed for (%s, %s)", layer_key, longitude, latitude, exc_info=True
                )
                failed_layers.append(layer_key)
                # Record per-layer failure health event
                if db:
                    source_name = f"geo_admin_{layer_key}"
                    try:
                        await SourceRegistryService.record_health_event(
                            db,
                            source_name,
                            "degraded",
                            description=f"Layer {layer_key} failed",
                            fallback_used=True,
                            fallback_source_name="partial_result",
                        )
                    except Exception:
                        logger.debug("Failed to record degraded event for %s", layer_key, exc_info=True)

    return {
        "layers": results,
        "failed_layers": failed_layers,
        "drift_layers": drift_layers,
        "total_requested": len(target_layers),
        "total_succeeded": len(results),
        "total_failed": len(failed_layers),
    }


async def check_context_freshness(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> dict[str, Any]:
    """Check if cached geo context is fresh per source TTL (7 days).

    Returns: {fresh: bool, stale_layers: [...], recommended_action: str}
    """
    existing = await db.execute(select(BuildingGeoContext).where(BuildingGeoContext.building_id == building_id))
    cached = existing.scalar_one_or_none()

    if cached is None:
        return {
            "fresh": False,
            "stale_layers": list(LAYERS.keys()),
            "recommended_action": "full_fetch",
            "detail": "no_cached_context",
        }

    if cached.fetched_at is None:
        return {
            "fresh": False,
            "stale_layers": list(LAYERS.keys()),
            "recommended_action": "full_fetch",
            "detail": "no_fetched_at_timestamp",
        }

    now = datetime.now(UTC)
    age = now - cached.fetched_at.replace(tzinfo=UTC)
    is_fresh = age < timedelta(days=CACHE_TTL_DAYS)

    if is_fresh:
        return {
            "fresh": True,
            "stale_layers": [],
            "recommended_action": "none",
            "age_days": round(age.total_seconds() / 86400, 1),
            "fetched_at": cached.fetched_at.isoformat(),
        }

    # Stale: determine which layers are in the cached data
    cached_layers = list((cached.context_data or {}).keys())
    # All layers not in cached data are stale, plus the whole cache is expired
    all_layer_keys = list(LAYERS.keys())
    missing_layers = [k for k in all_layer_keys if k not in cached_layers]

    return {
        "fresh": False,
        "stale_layers": cached_layers + missing_layers,
        "recommended_action": "refresh",
        "age_days": round(age.total_seconds() / 86400, 1),
        "fetched_at": cached.fetched_at.isoformat(),
    }


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
