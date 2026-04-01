"""Swiss public registry connector — fetches building data from RegBL, Swisstopo, and hazard APIs."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10.0

# ---------------------------------------------------------------------------
# In-memory cache (key → (timestamp, data))
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def _cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    ts, data = entry
    if time.monotonic() - ts > CACHE_TTL_SECONDS:
        del _cache[key]
        return None
    return data


def _cache_set(key: str, data: Any) -> None:
    _cache[key] = (time.monotonic(), data)


# ---------------------------------------------------------------------------
# RegBL lookup by EGID
# ---------------------------------------------------------------------------
REGBL_URL = "https://api3.geo.admin.ch/rest/services/api/MapServer/find"
REGBL_LAYER = "ch.bfs.gebaeude_wohnungs_register"


async def lookup_by_egid(egid: int) -> dict | None:
    """Look up building data from the federal RegBL registry by EGID.

    Returns parsed building dict or None if not found.
    """
    cache_key = f"regbl:{egid}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params = {
        "layer": REGBL_LAYER,
        "searchText": str(egid),
        "searchField": "egid_edid",
        "returnGeometry": "true",
        "contains": "false",
    }

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(REGBL_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.warning("RegBL lookup timed out for EGID %s", egid)
        return None
    except httpx.HTTPError as exc:
        logger.warning("RegBL lookup failed for EGID %s: %s", egid, exc)
        return None

    results = data.get("results", [])
    if not results:
        return None

    # Take the first matching feature
    attrs = results[0].get("attrs", {}) or results[0].get("attributes", {})
    geometry = results[0].get("geometry", {})

    parsed = _parse_regbl_attrs(attrs, geometry, egid)
    _cache_set(cache_key, parsed)
    return parsed


def _parse_regbl_attrs(attrs: dict, geometry: dict, egid: int) -> dict:
    """Parse RegBL feature attributes into a normalized dict."""
    # Coordinates may come from geometry or attributes
    lat = geometry.get("y") or attrs.get("gkode") or attrs.get("latitude")
    lng = geometry.get("x") or attrs.get("gkodn") or attrs.get("longitude")

    return {
        "egid": egid,
        "source": "regbl",
        "address": attrs.get("strname_deinr") or attrs.get("strname") or None,
        "postal_code": str(attrs.get("dplz4", "")) or None,
        "city": attrs.get("ggdename") or attrs.get("dplzname") or None,
        "canton": attrs.get("gdekt") or None,
        "construction_year": _safe_int(attrs.get("gbauj")),
        "building_category": attrs.get("gkat_decoded") or attrs.get("gkat") or None,
        "building_class": attrs.get("gklas_decoded") or attrs.get("gklas") or None,
        "floors": _safe_int(attrs.get("gastw")),
        "area": _safe_float(attrs.get("garea")),
        "heating_type": attrs.get("gheizh_decoded") or attrs.get("genh1_decoded") or None,
        "energy_source": attrs.get("genhe1_decoded") or attrs.get("genhe1") or None,
        "renovation_year": _safe_int(attrs.get("gbaum")),
        "coordinates": {"lat": lat, "lng": lng} if lat and lng else None,
        "raw_attributes": attrs,
    }


# ---------------------------------------------------------------------------
# Swisstopo geocoding / address search
# ---------------------------------------------------------------------------
SWISSTOPO_SEARCH_URL = "https://api3.geo.admin.ch/rest/services/api/SearchServer"


async def lookup_by_address(address: str, postal_code: str | None = None) -> list[dict]:
    """Search for buildings/locations via Swisstopo geocoding.

    Returns list of matches with address, coordinates, and egid if available.
    """
    query = address
    if postal_code:
        query = f"{postal_code} {address}"

    cache_key = f"swisstopo:{query}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params = {
        "searchText": query,
        "type": "locations",
        "limit": 10,
    }

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(SWISSTOPO_SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.warning("Swisstopo geocoding timed out for query %s", query)
        return []
    except httpx.HTTPError as exc:
        logger.warning("Swisstopo geocoding failed for query %s: %s", query, exc)
        return []

    results = []
    for feature in data.get("results", []):
        attrs = feature.get("attrs", {})
        results.append(
            {
                "source": "swisstopo",
                "address": attrs.get("label") or attrs.get("detail") or None,
                "postal_code": str(attrs.get("zip", "")) or None,
                "city": attrs.get("commune") or attrs.get("city") or None,
                "canton": attrs.get("canton") or None,
                "lat": attrs.get("lat"),
                "lng": attrs.get("lon") or attrs.get("lng"),
                "egid": _safe_int(attrs.get("egid")),
                "feature_id": attrs.get("featureId"),
            }
        )

    _cache_set(cache_key, results)
    return results


# ---------------------------------------------------------------------------
# Natural hazards lookup
# ---------------------------------------------------------------------------
HAZARDS_URL = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"

HAZARD_LAYERS = {
    "flood": "ch.bafu.showme-kantone_hochwasser",
    "landslide": "ch.bafu.showme-kantone_rutschungen",
    "avalanche": "ch.bafu.showme-kantone_lawinen",
    "earthquake": "ch.bafu.erdbeben-gefaehrdungsmodell_pga",
}


async def get_natural_hazards(lat: float, lng: float) -> dict:
    """Fetch natural hazard data at given coordinates from geo.admin.

    Returns dict with flood_risk, landslide_risk, avalanche_risk, earthquake_zone.
    """
    cache_key = f"hazards:{lat:.5f},{lng:.5f}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    result: dict[str, dict | None] = {}

    for hazard_type, layer_id in HAZARD_LAYERS.items():
        result[f"{hazard_type}_risk"] = await _fetch_hazard_layer(lat, lng, layer_id, hazard_type)

    _cache_set(cache_key, result)
    return result


async def _fetch_hazard_layer(lat: float, lng: float, layer_id: str, hazard_type: str) -> dict | None:
    """Fetch a single hazard layer."""
    # Build a small extent around the point
    delta = 0.001
    extent = f"{lng - delta},{lat - delta},{lng + delta},{lat + delta}"

    params = {
        "layers": f"all:{layer_id}",
        "geometry": f"{lng},{lat}",
        "geometryType": "esriGeometryPoint",
        "tolerance": 50,
        "mapExtent": extent,
        "imageDisplay": "400,400,96",
        "returnGeometry": "false",
        "sr": "4326",
    }

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(HAZARDS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.warning("Hazard layer %s fetch failed: %s", hazard_type, exc)
        return None

    results = data.get("results", [])
    if not results:
        return None

    attrs = results[0].get("attributes", {})
    return {
        "level": attrs.get("gefahrenstufe") or attrs.get("stufe") or attrs.get("pga_value") or "unknown",
        "description": attrs.get("description") or attrs.get("beschreibung") or None,
        "source": layer_id,
    }


# ---------------------------------------------------------------------------
# Building enrichment from registries
# ---------------------------------------------------------------------------

# Fields that can be enriched from RegBL (DB column → RegBL parsed key)
_ENRICHABLE_FIELDS: dict[str, str] = {
    "construction_year": "construction_year",
    "renovation_year": "renovation_year",
    "canton": "canton",
    "postal_code": "postal_code",
    "city": "city",
    "floors_above": "floors",
    "surface_area_m2": "area",
}


async def enrich_building_from_registry(db: AsyncSession, building_id: uuid.UUID) -> dict:
    """Auto-enrich a building from public registries.

    - If building has EGID: lookup RegBL and fill empty fields
    - If building has coordinates: fetch natural hazards and store in metadata
    - NEVER overwrites user-entered data (only fills None/empty fields)

    Returns dict of fields that were updated.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    updated_fields: dict[str, Any] = {}
    hazards: dict | None = None

    # 1. RegBL enrichment if we have an EGID
    if building.egid:
        regbl_data = await lookup_by_egid(building.egid)
        if regbl_data:
            for db_field, regbl_key in _ENRICHABLE_FIELDS.items():
                current_value = getattr(building, db_field, None)
                new_value = regbl_data.get(regbl_key)
                if current_value is None and new_value is not None:
                    setattr(building, db_field, new_value)
                    updated_fields[db_field] = new_value

            # Fill coordinates if missing
            coords = regbl_data.get("coordinates")
            if coords and building.latitude is None and building.longitude is None:
                building.latitude = coords.get("lat")
                building.longitude = coords.get("lng")
                updated_fields["latitude"] = coords.get("lat")
                updated_fields["longitude"] = coords.get("lng")

    # 2. Natural hazards if we have coordinates
    if building.latitude and building.longitude:
        hazards = await get_natural_hazards(building.latitude, building.longitude)
        if hazards:
            # Store hazards in source_metadata_json
            meta = building.source_metadata_json or {}
            meta["natural_hazards"] = hazards
            meta["natural_hazards_source"] = "geo.admin"
            building.source_metadata_json = meta
            updated_fields["natural_hazards"] = hazards

    if updated_fields:
        await db.commit()
        await db.refresh(building)

    return {
        "building_id": str(building_id),
        "updated_fields": updated_fields,
        "source": "regbl+geo.admin",
        "egid_found": building.egid is not None,
        "hazards_fetched": hazards is not None,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_int(val: Any) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
