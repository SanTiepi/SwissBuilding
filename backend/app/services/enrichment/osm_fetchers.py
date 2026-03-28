"""Fetchers for OSM (Overpass), climate estimation, and transport.opendata.ch.

NOTE: functions resolve ``_retry_request`` / ``_throttle`` through the
backward-compat shim module so that ``unittest.mock.patch`` on
``app.services.building_enrichment_service`` correctly intercepts calls.
"""

from __future__ import annotations

import contextlib
import logging
import sys
from typing import Any

import httpx

from app.services.enrichment.http_helpers import _retry_request, _throttle
from app.services.enrichment.source_provenance import _source_entry


def _resolve(name: str, fallback: object) -> object:
    """Resolve *name* from the backward-compat shim module."""
    mod = sys.modules.get("app.services.building_enrichment_service")
    if mod is not None:
        return getattr(mod, name, fallback)
    return fallback


logger = logging.getLogger(__name__)


async def fetch_osm_amenities(lat: float, lon: float, radius: int = 500) -> dict[str, Any]:
    """Count amenities by type within radius using Overpass API."""
    await _resolve("_throttle", _throttle)()
    query = f"[out:json][timeout:15];(node[amenity](around:{radius},{lat},{lon}););out body;"
    retry_count = 0
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp, retry_count = await _resolve("_retry_request", _retry_request)(
                client,
                "POST",
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                timeout=20.0,
            )
            resp.raise_for_status()
            data = resp.json()

        elements = data.get("elements", [])
        counts: dict[str, int] = {}
        _amenity_map = {
            "school": "schools",
            "hospital": "hospitals",
            "pharmacy": "pharmacies",
            "supermarket": "supermarkets",
            "restaurant": "restaurants",
            "cafe": "cafes",
            "bank": "banks",
            "post_office": "post_offices",
            "park": "parks",
            "kindergarten": "kindergartens",
        }
        for el in elements:
            amenity = el.get("tags", {}).get("amenity", "")
            key = _amenity_map.get(amenity)
            if key:
                counts[key] = counts.get(key, 0) + 1

        result: dict[str, Any] = {k: counts.get(k, 0) for k in _amenity_map.values()}
        result["total_amenities"] = len(elements)
        result["_source_entry"] = _source_entry(
            "overpass/amenities",
            status="success",
            confidence="medium",
            retry_count=retry_count,
        )
        return result

    except Exception as exc:
        logger.warning("Overpass amenities fetch failed for (%s, %s): %s", lat, lon, exc)
        status = "timeout" if "504" in str(exc) or "timeout" in str(exc).lower() else "failed"
        return {
            "_source_entry": _source_entry(
                "overpass/amenities",
                status=status,
                confidence="low",
                error=str(exc),
                retry_count=retry_count,
            ),
        }


async def fetch_osm_building_details(lat: float, lon: float) -> dict[str, Any]:
    """Fetch building footprint details from OSM via Overpass."""
    await _resolve("_throttle", _throttle)()
    query = f"[out:json][timeout:15];(way[building](around:30,{lat},{lon}););out body 1;"
    retry_count = 0
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp, retry_count = await _resolve("_retry_request", _retry_request)(
                client,
                "POST",
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                timeout=20.0,
            )
            resp.raise_for_status()
            data = resp.json()

        elements = data.get("elements", [])
        if not elements:
            return {
                "_source_entry": _source_entry(
                    "overpass/building",
                    status="success",
                    confidence="medium",
                    retry_count=retry_count,
                ),
            }

        tags = elements[0].get("tags", {})
        result: dict[str, Any] = {}
        if tags.get("height"):
            with contextlib.suppress(ValueError, TypeError):
                result["height"] = float(tags["height"])
        if tags.get("building:levels"):
            with contextlib.suppress(ValueError, TypeError):
                result["levels"] = int(tags["building:levels"])
        if tags.get("building:material"):
            result["material"] = str(tags["building:material"])
        if tags.get("roof:shape"):
            result["roof_type"] = str(tags["roof:shape"])
        if tags.get("wheelchair"):
            result["wheelchair_access"] = str(tags["wheelchair"])
        result["_source_entry"] = _source_entry(
            "overpass/building",
            status="success",
            confidence="medium",
            retry_count=retry_count,
        )
        return result

    except Exception as exc:
        logger.warning("Overpass building details fetch failed for (%s, %s): %s", lat, lon, exc)
        status = "timeout" if "504" in str(exc) or "timeout" in str(exc).lower() else "failed"
        return {
            "_source_entry": _source_entry(
                "overpass/building",
                status=status,
                confidence="low",
                error=str(exc),
                retry_count=retry_count,
            ),
        }


def fetch_climate_data(lat: float, lon: float) -> dict[str, Any]:
    """Estimate climate data from coordinates using Swiss climate zone heuristics.

    Pure function -- no API calls. Uses latitude/altitude approximation.
    """
    # Rough altitude estimate from latitude in Switzerland
    # (higher altitude in the south / Alps)
    # Swiss plateau ~400-600m, Jura ~800-1000m, Alps ~1500-3000m
    # Latitude range: 45.8 (Chiasso) to 47.8 (Schaffhausen)
    estimated_alt = max(300, int((47.5 - lat) * 800 + 400))
    estimated_alt = min(estimated_alt, 3000)

    # Temperature: roughly -6.5C per 1000m altitude
    base_temp = 10.5  # Swiss mean at 500m
    avg_temp = round(base_temp - (estimated_alt - 500) * 0.0065, 1)

    # Precipitation: varies 800-2000mm, higher in Alps
    precip = int(900 + (estimated_alt - 500) * 0.6)
    precip = max(800, min(precip, 2200))

    # Frost days: ~80 at 500m, +15 per 500m altitude
    frost_days = int(80 + (estimated_alt - 500) * 0.03)
    frost_days = max(40, min(frost_days, 200))

    # Sunshine hours: ~1600 at plateau, less in Alps due to fog but more at high alt
    sunshine = int(1600 - abs(estimated_alt - 1200) * 0.2)
    sunshine = max(1200, min(sunshine, 2100))

    # Heating degree days (base 20C): roughly (20 - avg_temp) * 365 * 0.6
    hdd = int(max(0, (20 - avg_temp) * 365 * 0.6))

    # Tropical days (>30C): rare in Switzerland, mostly Ticino/Rhone
    tropical = 0
    if lat < 46.2:  # Ticino
        tropical = 15
    elif estimated_alt < 500:
        tropical = 5
    elif estimated_alt < 800:
        tropical = 2

    return {
        "avg_temp_c": avg_temp,
        "precipitation_mm": precip,
        "frost_days": frost_days,
        "sunshine_hours": sunshine,
        "heating_degree_days": hdd,
        "tropical_days": tropical,
        "estimated_altitude_m": estimated_alt,
    }


async def fetch_nearest_stops(lat: float, lon: float) -> dict[str, Any]:
    """Fetch nearest public transport stops via transport.opendata.ch."""
    await _resolve("_throttle", _throttle)()
    url = "https://transport.opendata.ch/v1/locations"
    params = {
        "x": str(lat),
        "y": str(lon),
        "type": "station",
    }
    retry_count = 0
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp, retry_count = await _resolve("_retry_request", _retry_request)(
                client, "GET", url, params=params, timeout=15.0
            )
            resp.raise_for_status()
            data = resp.json()

        stations = data.get("stations", [])
        if not stations:
            return {
                "_source_entry": _source_entry(
                    "transport.opendata.ch",
                    status="success",
                    confidence="high",
                    retry_count=retry_count,
                ),
            }

        stops: list[dict[str, Any]] = []
        for s in stations[:5]:
            stop: dict[str, Any] = {"name": s.get("name", "")}
            if s.get("distance") is not None:
                stop["distance_m"] = int(s["distance"])
            stops.append(stop)

        result: dict[str, Any] = {"stops": stops}
        if stops:
            result["nearest_stop_name"] = stops[0]["name"]
            result["nearest_stop_distance_m"] = stops[0].get("distance_m", 0)
        result["_source_entry"] = _source_entry(
            "transport.opendata.ch",
            status="success",
            confidence="high",
            retry_count=retry_count,
        )
        return result

    except Exception as exc:
        logger.warning("Transport stops fetch failed for (%s, %s): %s", lat, lon, exc)
        status = "timeout" if "timeout" in str(exc).lower() else "failed"
        return {
            "_source_entry": _source_entry(
                "transport.opendata.ch",
                status=status,
                confidence="low",
                error=str(exc),
                retry_count=retry_count,
            ),
        }
