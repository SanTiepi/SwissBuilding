"""Mapbox Isochrone API service — fetches walking/cycling/driving isochrones for buildings."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.building import Building

logger = logging.getLogger(__name__)

MAPBOX_ISOCHRONE_URL = "https://api.mapbox.com/isochrone/v1/mapbox"
CACHE_TTL_DAYS = 7
DEFAULT_TIMEOUT = 15.0

VALID_PROFILES = {"walking", "cycling", "driving"}
MAX_MINUTES = 60
CONTOUR_COLORS = {5: "00b33c", 10: "f59e0b", 15: "ef4444", 20: "9333ea", 30: "3b82f6"}


async def _get_building_coords(db: AsyncSession, building_id: uuid.UUID) -> tuple[float, float]:
    """Return (longitude, latitude) for a building, or raise ValueError."""
    result = await db.execute(select(Building.longitude, Building.latitude).where(Building.id == building_id))
    row = result.one_or_none()
    if not row or row.longitude is None or row.latitude is None:
        raise ValueError(f"Building {building_id} not found or has no coordinates")
    return float(row.longitude), float(row.latitude)


async def _fetch_isochrone_from_mapbox(
    lon: float,
    lat: float,
    profile: str,
    minutes_list: list[int],
) -> dict[str, Any]:
    """Call Mapbox Isochrone API and return raw GeoJSON FeatureCollection."""
    api_key = settings.MAPBOX_API_KEY
    if not api_key:
        return {"error": "MAPBOX_API_KEY not configured"}

    contours = ",".join(str(m) for m in minutes_list)
    colors = ",".join(CONTOUR_COLORS.get(m, "666666") for m in minutes_list)

    url = f"{MAPBOX_ISOCHRONE_URL}/{profile}/{lon},{lat}"
    params = {
        "contours_minutes": contours,
        "contours_colors": colors,
        "polygons": "true",
        "access_token": api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.warning("Mapbox Isochrone API HTTP error: %s", e)
        return {"error": f"Mapbox API returned {e.response.status_code}"}
    except httpx.RequestError as e:
        logger.warning("Mapbox Isochrone API request error: %s", e)
        return {"error": "Mapbox API unreachable"}


def _parse_features(raw: dict[str, Any], profile: str, minutes_list: list[int]) -> list[dict[str, Any]]:
    """Parse Mapbox FeatureCollection into structured contours."""
    features = raw.get("features", [])
    contours = []
    for i, feat in enumerate(features):
        minutes = minutes_list[i] if i < len(minutes_list) else 0
        contours.append(
            {
                "minutes": minutes,
                "profile": profile,
                "geometry": feat.get("geometry", {}),
            }
        )
    return contours


# In-memory cache keyed by (building_id, profile, contours_key)
_cache: dict[str, tuple[datetime, dict[str, Any]]] = {}


def _cache_key(building_id: uuid.UUID, profile: str, minutes_list: list[int]) -> str:
    return f"{building_id}:{profile}:{','.join(str(m) for m in sorted(minutes_list))}"


async def get_building_isochrone(
    db: AsyncSession,
    building_id: uuid.UUID,
    profile: str = "walking",
    minutes_list: list[int] | None = None,
) -> dict[str, Any]:
    """Get isochrone contours for a building (cached or fresh)."""
    if profile not in VALID_PROFILES:
        return {"error": f"Invalid profile: {profile}. Must be one of {VALID_PROFILES}"}

    if minutes_list is None:
        minutes_list = [5, 10, 15]
    minutes_list = [m for m in minutes_list if 1 <= m <= MAX_MINUTES]
    if not minutes_list:
        return {"error": "No valid minutes provided (1-60)"}

    # Check cache
    key = _cache_key(building_id, profile, minutes_list)
    if key in _cache:
        cached_at, cached_data = _cache[key]
        if datetime.now(UTC) - cached_at < timedelta(days=CACHE_TTL_DAYS):
            return {**cached_data, "cached": True}

    lon, lat = await _get_building_coords(db, building_id)

    raw = await _fetch_isochrone_from_mapbox(lon, lat, profile, minutes_list)
    if "error" in raw:
        return {
            "building_id": str(building_id),
            "latitude": lat,
            "longitude": lon,
            "profile": profile,
            "contours": [],
            "mobility_score": None,
            "cached": False,
            "error": raw["error"],
        }

    contours = _parse_features(raw, profile, minutes_list)
    now = datetime.now(UTC)

    # Mobility score: ratio of requested contours that returned valid polygons (0-10)
    valid_contours = sum(1 for c in contours if c.get("geometry", {}).get("coordinates"))
    mobility_score = round((valid_contours / max(len(minutes_list), 1)) * 10, 1)

    result = {
        "building_id": str(building_id),
        "latitude": lat,
        "longitude": lon,
        "profile": profile,
        "contours": contours,
        "mobility_score": mobility_score,
        "cached": False,
        "error": None,
    }

    # Store in cache
    _cache[key] = (now, result)

    return result
