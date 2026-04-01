"""
SwissBuildingOS - Shadow Analysis Service (Programme W)

Basic shadow analysis from building heights and neighbor positions.
Uses floor count or OSM height data to estimate shadow impact from
taller buildings, particularly from the south/southwest (critical
for solar panel viability and winter heating).

Sun angles for Switzerland (latitude ~46.5-47.5):
  - Winter solstice: ~20-25 degrees above horizon at noon
  - Summer solstice: ~65-70 degrees above horizon at noon
"""

from __future__ import annotations

import math
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Average Swiss latitude for sun angle calculations
_SWISS_LAT = 46.8

# Sun elevation at solar noon (approximate)
_WINTER_SUN_ANGLE_DEG = 20.0  # December solstice
_EQUINOX_SUN_ANGLE_DEG = 43.0  # March/September
_SUMMER_SUN_ANGLE_DEG = 66.0  # June solstice

# Hours of potential shadow (rough estimates for Swiss latitudes)
_WINTER_SUN_HOURS = 8.5  # ~8h of daylight
_SUMMER_SUN_HOURS = 15.5  # ~15.5h of daylight


def _estimate_height(building: Building) -> float | None:
    """Estimate building height from floors or enrichment data."""
    meta = building.source_metadata_json or {}
    osm = meta.get("osm_building", {})
    if osm.get("height"):
        try:
            return float(osm["height"])
        except (ValueError, TypeError):
            pass
    if building.floors_above:
        return building.floors_above * 3.0
    return None


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in meters."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Bearing in degrees from point 1 to point 2 (0=N, 90=E, 180=S, 270=W)."""
    dlon = math.radians(lon2 - lon1)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    x = math.sin(dlon) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _cardinal(bearing: float) -> str:
    """Convert bearing to cardinal direction label."""
    if bearing < 22.5 or bearing >= 337.5:
        return "north"
    if bearing < 67.5:
        return "northeast"
    if bearing < 112.5:
        return "east"
    if bearing < 157.5:
        return "southeast"
    if bearing < 202.5:
        return "south"
    if bearing < 247.5:
        return "southwest"
    if bearing < 292.5:
        return "west"
    return "northwest"


def _shadow_length(height_diff: float, sun_angle_deg: float) -> float:
    """Maximum shadow length from height difference and sun angle."""
    if sun_angle_deg <= 0 or height_diff <= 0:
        return 0.0
    return height_diff / math.tan(math.radians(sun_angle_deg))


def _shadow_hours_estimate(
    distance_m: float,
    height_diff: float,
    sun_angle: float,
    total_sun_hours: float,
) -> float:
    """Estimate hours of shadow impact.

    If the shadow reaches the building, estimate fraction of day affected.
    The sun moves ~15 degrees/hour, so a building to the south affects
    roughly proportional to the width angle subtended.
    """
    shadow_len = _shadow_length(height_diff, sun_angle)
    if shadow_len <= distance_m:
        return 0.0

    # Shadow reaches our building — estimate hours
    # More height difference + closer = more shadow hours
    coverage_ratio = min(1.0, (shadow_len - distance_m) / max(distance_m, 1.0))
    # A building directly south might shadow for 2-4 hours max
    max_shadow = total_sun_hours * 0.25  # max 25% of day
    return round(coverage_ratio * max_shadow, 1)


def _solar_panel_impact(winter_hours: float, summer_hours: float) -> str:
    """Assess impact on solar panel viability."""
    if winter_hours < 0.5 and summer_hours < 0.5:
        return "none"
    if winter_hours < 1.5 and summer_hours < 0.5:
        return "minor"
    if winter_hours < 3.0 and summer_hours < 1.5:
        return "significant"
    return "severe"


# ---------------------------------------------------------------------------
# Internal: get nearby buildings (fallback for non-PostGIS)
# ---------------------------------------------------------------------------


async def _get_nearby_buildings(
    db: AsyncSession,
    building: Building,
    radius_m: float,
) -> list[Building]:
    """Get nearby buildings, using coordinate filter + haversine."""
    degree_radius = radius_m / 111_000
    stmt = select(Building).where(
        Building.id != building.id,
        Building.status != "archived",
        Building.latitude.isnot(None),
        Building.longitude.isnot(None),
        Building.latitude.between(
            building.latitude - degree_radius,
            building.latitude + degree_radius,
        ),
        Building.longitude.between(
            building.longitude - degree_radius,
            building.longitude + degree_radius,
        ),
    )
    result = await db.execute(stmt)
    candidates = list(result.scalars().all())

    return [
        c
        for c in candidates
        if _haversine_m(building.latitude, building.longitude, c.latitude, c.longitude) <= radius_m
    ]


# ---------------------------------------------------------------------------
# FN1: compute_shadow_impact
# ---------------------------------------------------------------------------


async def compute_shadow_impact(
    db: AsyncSession,
    building_id: UUID,
    radius_m: float = 100,
) -> dict:
    """Compute shadow impact from taller neighboring buildings.

    Uses building heights (from floors or OSM data) and positions to estimate:
    - Shadow sources (taller buildings, especially to south/southwest)
    - Winter vs summer shadow hours
    - Impact on solar panel viability
    """
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    if building.latitude is None or building.longitude is None:
        return {
            "shadow_sources": [],
            "winter_shadow_hours": 0.0,
            "summer_shadow_hours": 0.0,
            "solar_panel_impact": "unknown",
            "recommendation": "Coordonnées GPS non disponibles — enrichissement nécessaire",
            "coordinates_available": False,
        }

    my_height = _estimate_height(building)
    if my_height is None:
        my_height = 9.0  # default assumption: 3 floors

    neighbors = await _get_nearby_buildings(db, building, radius_m)

    shadow_sources = []
    total_winter_shadow = 0.0
    total_summer_shadow = 0.0

    for n in neighbors:
        n_height = _estimate_height(n)
        if n_height is None:
            continue

        height_diff = n_height - my_height
        if height_diff <= 0:
            continue  # Not taller, no shadow impact

        dist = _haversine_m(building.latitude, building.longitude, n.latitude, n.longitude)
        bearing = _bearing_deg(building.latitude, building.longitude, n.latitude, n.longitude)
        direction = _cardinal(bearing)

        # Only buildings roughly to the south cast significant shadows
        # (bearing 90-270 = east through south to west)
        is_south_ish = 90 <= bearing <= 270

        winter_shadow = 0.0
        summer_shadow = 0.0

        if is_south_ish:
            winter_shadow = _shadow_hours_estimate(dist, height_diff, _WINTER_SUN_ANGLE_DEG, _WINTER_SUN_HOURS)
            summer_shadow = _shadow_hours_estimate(dist, height_diff, _SUMMER_SUN_ANGLE_DEG, _SUMMER_SUN_HOURS)

        if winter_shadow > 0 or summer_shadow > 0:
            shadow_sources.append(
                {
                    "building_id": str(n.id),
                    "address": n.address,
                    "height_m": round(n_height, 1),
                    "height_diff_m": round(height_diff, 1),
                    "direction": direction,
                    "distance_m": round(dist, 1),
                    "winter_shadow_hours": winter_shadow,
                    "summer_shadow_hours": summer_shadow,
                }
            )
            total_winter_shadow += winter_shadow
            total_summer_shadow += summer_shadow

    # Cap totals at realistic maximums
    total_winter_shadow = min(total_winter_shadow, _WINTER_SUN_HOURS * 0.8)
    total_summer_shadow = min(total_summer_shadow, _SUMMER_SUN_HOURS * 0.5)

    # Sort by winter shadow impact (most impactful first)
    shadow_sources.sort(key=lambda s: s["winter_shadow_hours"], reverse=True)

    impact = _solar_panel_impact(total_winter_shadow, total_summer_shadow)

    # Recommendation
    if not shadow_sources:
        recommendation = "Aucun ombrage significatif détecté — bon potentiel solaire"
    elif impact == "severe":
        recommendation = (
            "Ombrage important — panneaux solaires déconseillés sur le toit, envisager façade sud ou alternatives"
        )
    elif impact == "significant":
        recommendation = (
            "Ombrage modéré en hiver — étude de rendement solaire recommandée avant installation de panneaux"
        )
    elif impact == "minor":
        recommendation = "Ombrage mineur en hiver — impact limité sur le rendement solaire"
    else:
        recommendation = "Pas d'ombrage significatif"

    return {
        "shadow_sources": shadow_sources,
        "winter_shadow_hours": round(total_winter_shadow, 1),
        "summer_shadow_hours": round(total_summer_shadow, 1),
        "solar_panel_impact": impact,
        "recommendation": recommendation,
        "building_height_m": round(my_height, 1),
        "coordinates_available": True,
    }
