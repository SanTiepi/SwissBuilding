"""Nature score service — green environment quality scoring for a building.

Computes a 0-10 nature/green environment score from enrichment data,
considering parks, water proximity, green ratio, air quality, altitude,
and natural hazard penalties.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building

logger = logging.getLogger(__name__)

# Weights for each nature dimension
_WEIGHTS: dict[str, float] = {
    "parks_nearby": 2.0,
    "water_proximity": 1.5,
    "green_ratio": 2.0,
    "air_quality": 2.5,
    "altitude_bonus": 1.0,
    "nature_hazard_penalty": -1.0,
}

# Grade thresholds
_GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (8.5, "A"),
    (7.0, "B"),
    (5.5, "C"),
    (4.0, "D"),
    (2.5, "E"),
    (0.0, "F"),
]


def _grade_from_score(score: float) -> str:
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def _compute_parks_score(enrichment_meta: dict[str, Any]) -> tuple[float, str]:
    """Score parks from OSM amenities (0-10)."""
    osm = enrichment_meta.get("osm_amenities") or {}
    parks_count = osm.get("parks", 0)
    if not isinstance(parks_count, (int, float)):
        parks_count = 0
    parks_count = int(parks_count)

    if parks_count >= 5:
        return 10.0, f"{parks_count} parks within radius"
    if parks_count >= 3:
        return 8.0, f"{parks_count} parks within radius"
    if parks_count >= 1:
        return 5.0, f"{parks_count} park(s) within radius"
    return 0.0, "No parks detected nearby"


def _compute_water_proximity(enrichment_meta: dict[str, Any]) -> tuple[float, str]:
    """Estimate water proximity from flood zone data.

    Flood zone presence often correlates with proximity to water bodies.
    """
    flood = enrichment_meta.get("flood_zones") or {}
    flood_level = str(flood.get("flood_danger_level", "")).lower()
    water_prot = enrichment_meta.get("water_protection") or {}

    score = 0.0
    detail = "No water body indicators"

    # Groundwater protection zone indicates water proximity
    if water_prot:
        zone = str(water_prot.get("protection_zone", "")).upper()
        if zone in ("S1", "S2"):
            score = max(score, 8.0)
            detail = f"Near water protection zone {zone}"
        elif zone in ("S3", "SH"):
            score = max(score, 5.0)
            detail = f"Moderate water proximity (zone {zone})"

    # Flood zone also indicates water proximity (positive for nature, despite risk)
    if flood_level:
        if "hoch" in flood_level or "high" in flood_level:
            score = max(score, 7.0)
            detail = "Close to water body (high flood zone)"
        elif "mittel" in flood_level or "medium" in flood_level:
            score = max(score, 6.0)
            detail = "Near water body (medium flood zone)"
        elif "gering" in flood_level or "low" in flood_level:
            score = max(score, 4.0)
            detail = "Some water proximity (low flood zone)"

    return score, detail


def _compute_green_ratio(enrichment_meta: dict[str, Any]) -> tuple[float, str]:
    """Estimate green ratio from agricultural zones and forest reserves."""
    agri = enrichment_meta.get("agricultural_zones") or {}
    forest = enrichment_meta.get("forest_reserves") or {}

    score = 0.0
    factors: list[str] = []

    if forest:
        has_forest = forest.get("in_forest_reserve") or forest.get("forest_nearby")
        if has_forest:
            score += 5.0
            factors.append("Forest reserve nearby")

    if agri:
        has_agri = agri.get("in_agricultural_zone") or agri.get("agricultural_zone")
        if has_agri:
            score += 4.0
            factors.append("Agricultural zone nearby")

    # Cap at 10
    score = min(10.0, score)

    if not factors:
        # Fallback: if building is in low-density zone, assume some green
        zones = enrichment_meta.get("building_zones") or {}
        zone_type = str(zones.get("zone_type", "")).lower()
        if "villa" in zone_type or "rural" in zone_type or "green" in zone_type:
            score = 4.0
            factors.append("Low-density residential zone")

    detail = "; ".join(factors) if factors else "No green indicators detected"
    return score, detail


def _compute_air_quality(enrichment_meta: dict[str, Any]) -> tuple[float, str]:
    """Estimate air quality from inverse of noise + contamination + traffic.

    Lower noise, no contamination, less traffic = better air.
    """
    penalties = 0.0
    factors: list[str] = []

    # Noise as proxy for traffic/pollution
    noise = enrichment_meta.get("noise") or {}
    road_db = noise.get("road_noise_day_db")
    if road_db is not None:
        if road_db > 65:
            penalties += 4.0
            factors.append(f"Heavy traffic noise ({road_db} dB)")
        elif road_db > 55:
            penalties += 2.5
            factors.append(f"Moderate traffic noise ({road_db} dB)")
        elif road_db > 45:
            penalties += 1.0
            factors.append(f"Light traffic noise ({road_db} dB)")

    # Contaminated site
    contam = enrichment_meta.get("contaminated_sites") or {}
    if contam.get("is_contaminated"):
        penalties += 3.0
        factors.append("Contaminated site nearby")

    # Railway noise (diesel trains)
    rail = enrichment_meta.get("railway_noise") or {}
    rail_db = rail.get("railway_noise_day_db", 0) or 0
    if rail_db > 55:
        penalties += 1.5
        factors.append(f"Railway noise ({rail_db} dB)")

    # Aircraft noise
    aircraft = enrichment_meta.get("aircraft_noise") or {}
    air_db = aircraft.get("aircraft_noise_db", 0) or 0
    if air_db > 55:
        penalties += 1.5
        factors.append(f"Aircraft noise ({air_db} dB)")

    score = max(0.0, 10.0 - penalties)
    detail = "; ".join(factors) if factors else "Low pollution indicators (good air quality)"
    return round(score, 1), detail


def _compute_altitude_bonus(enrichment_meta: dict[str, Any]) -> tuple[float, str]:
    """Higher altitude generally means cleaner air in Switzerland."""
    climate = enrichment_meta.get("climate") or {}
    alt = climate.get("estimated_altitude_m")

    if alt is None:
        return 0.0, "No altitude data"

    if alt >= 1500:
        return 10.0, f"High altitude ({alt}m) - excellent air"
    if alt >= 1000:
        return 7.0, f"Mountain zone ({alt}m) - clean air"
    if alt >= 700:
        return 5.0, f"Pre-alpine zone ({alt}m) - good air"
    if alt >= 500:
        return 3.0, f"Plateau ({alt}m) - average air"
    return 1.0, f"Low altitude ({alt}m)"


def _compute_hazard_penalty(enrichment_meta: dict[str, Any]) -> tuple[float, str]:
    """Natural hazards reduce nature enjoyment (landslides, floods, etc.)."""
    hazards = enrichment_meta.get("natural_hazards") or {}
    if not hazards:
        return 0.0, "No hazard data"

    penalty = 0.0
    factors: list[str] = []

    for risk_key in ("flood_risk", "landslide_risk", "rockfall_risk"):
        level = str(hazards.get(risk_key, "")).lower()
        if "high" in level or "hoch" in level:
            penalty += 3.0
            factors.append(f"{risk_key}=high")
        elif "medium" in level or "mittel" in level:
            penalty += 1.5
            factors.append(f"{risk_key}=medium")

    # Cap penalty at 10
    penalty = min(10.0, penalty)
    detail = "; ".join(factors) if factors else "Low natural hazard risk"
    return penalty, detail


async def compute_nature_score(db: AsyncSession, building_id: uuid.UUID) -> dict[str, Any]:
    """Compute a 0-10 nature/green environment score for a building.

    Dimensions:
    - parks_nearby (weight 2): from OSM amenities parks count
    - water_proximity (weight 1.5): from flood zone / water protection data
    - green_ratio (weight 2): from agricultural zones + forest reserves
    - air_quality (weight 2.5): inverse of noise + contamination
    - altitude_bonus (weight 1): higher altitude = cleaner air
    - nature_hazard_penalty (weight -1): high hazards reduce score

    Returns: {score, grade, breakdown, highlights, recommendations}
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()

    if building is None:
        return {
            "score": 0.0,
            "grade": "F",
            "breakdown": {},
            "highlights": [],
            "recommendations": ["Building not found"],
        }

    enrichment_meta: dict[str, Any] = dict(building.source_metadata_json or {})

    # Compute each dimension
    parks_score, parks_detail = _compute_parks_score(enrichment_meta)
    water_score, water_detail = _compute_water_proximity(enrichment_meta)
    green_score, green_detail = _compute_green_ratio(enrichment_meta)
    air_score, air_detail = _compute_air_quality(enrichment_meta)
    alt_score, alt_detail = _compute_altitude_bonus(enrichment_meta)
    hazard_penalty, hazard_detail = _compute_hazard_penalty(enrichment_meta)

    breakdown: dict[str, Any] = {
        "parks_nearby": {"score": parks_score, "weight": 2.0, "detail": parks_detail},
        "water_proximity": {"score": water_score, "weight": 1.5, "detail": water_detail},
        "green_ratio": {"score": green_score, "weight": 2.0, "detail": green_detail},
        "air_quality": {"score": air_score, "weight": 2.5, "detail": air_detail},
        "altitude_bonus": {"score": alt_score, "weight": 1.0, "detail": alt_detail},
        "nature_hazard_penalty": {"score": hazard_penalty, "weight": -1.0, "detail": hazard_detail},
    }

    # Weighted score computation
    # Positive dimensions
    pos_weighted = parks_score * 2.0 + water_score * 1.5 + green_score * 2.0 + air_score * 2.5 + alt_score * 1.0
    pos_total_weight = 2.0 + 1.5 + 2.0 + 2.5 + 1.0  # = 9.0

    base_score = pos_weighted / pos_total_weight

    # Apply hazard penalty (subtract proportionally, max impact -2 points)
    penalty_impact = hazard_penalty * 1.0 / pos_total_weight
    final_score = max(0.0, min(10.0, round(base_score - penalty_impact, 1)))

    # Highlights and recommendations
    highlights: list[str] = []
    recommendations: list[str] = []

    if parks_score >= 7:
        highlights.append("Good park access nearby")
    elif parks_score == 0:
        recommendations.append("No parks detected -- consider urban greening options")

    if water_score >= 6:
        highlights.append("Near water body")

    if green_score >= 6:
        highlights.append("Green surroundings (forest/agriculture)")
    elif green_score <= 2:
        recommendations.append("Low green coverage in immediate area")

    if air_score >= 8:
        highlights.append("Excellent estimated air quality")
    elif air_score < 4:
        recommendations.append("Air quality concerns due to traffic/contamination")

    if alt_score >= 7:
        highlights.append("Mountain/pre-alpine setting -- clean air")

    if hazard_penalty >= 3:
        recommendations.append("Natural hazard risk may affect outdoor enjoyment")

    return {
        "score": final_score,
        "grade": _grade_from_score(final_score),
        "breakdown": breakdown,
        "highlights": highlights,
        "recommendations": recommendations,
    }
