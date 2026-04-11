"""Amenity analysis service — deep scoring of OSM amenity data from enrichment.

Extracts and scores amenity data from building enrichment_meta (source_metadata_json),
producing per-category scores, composite convenience scores, and persona-based scores.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building

logger = logging.getLogger(__name__)

# Distance -> score mapping (distance_m range -> score 0-10)
DISTANCE_SCORING: list[tuple[tuple[int, int], float]] = [
    ((0, 200), 10.0),
    ((200, 500), 8.0),
    ((500, 1000), 6.0),
    ((1000, 2000), 3.0),
    ((2000, 99999), 1.0),
]

# Amenity categories with expected count thresholds for score = 10
_AMENITY_THRESHOLDS: dict[str, int] = {
    "schools": 3,
    "hospitals": 1,
    "pharmacies": 2,
    "supermarkets": 3,
    "restaurants": 10,
    "parks": 3,
    "banks": 2,
    "post_offices": 1,
    "cafes": 5,
    "kindergartens": 2,
}


def score_from_distance(distance_m: float | int | None) -> float:
    """Convert a distance in meters to a 0-10 score."""
    if distance_m is None:
        return 0.0
    for (low, high), score in DISTANCE_SCORING:
        if low <= distance_m < high:
            return score
    return 1.0


def _score_from_count(count: int, threshold: int) -> float:
    """Convert an amenity count to a 0-10 score based on threshold."""
    if count <= 0:
        return 0.0
    return min(10.0, round(count / threshold * 10.0, 1))


def _estimate_nearest_distance(count: int, radius: int = 500) -> int | None:
    """Estimate nearest distance from count within search radius.

    More amenities in area -> likely one is close.
    Heuristic: if count >= 3, nearest is ~100m; if 1, nearest is ~radius/2.
    """
    if count <= 0:
        return None
    if count >= 5:
        return 100
    if count >= 3:
        return 200
    if count >= 2:
        return 350
    return radius // 2  # count == 1


def _extract_amenity_data(enrichment_meta: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract per-amenity-type data from enrichment_meta.osm_amenities.

    Returns {category: {count, nearest_distance_m (estimated), score_0_10}}.
    """
    osm = enrichment_meta.get("osm_amenities") or {}
    result: dict[str, dict[str, Any]] = {}

    for category, threshold in _AMENITY_THRESHOLDS.items():
        count = osm.get(category, 0)
        if not isinstance(count, (int, float)):
            count = 0
        count = int(count)

        nearest = _estimate_nearest_distance(count)
        count_score = _score_from_count(count, threshold)
        dist_score = score_from_distance(nearest)
        # Blend: 60% count-based, 40% distance-based
        blended = round(count_score * 0.6 + dist_score * 0.4, 1) if nearest is not None else count_score

        result[category] = {
            "count": count,
            "nearest_distance_m": nearest,
            "score_0_10": round(blended, 1),
        }

    return result


def _compute_walking_convenience(amenities: dict[str, dict[str, Any]]) -> float:
    """Composite score (0-10) for how many amenities are reachable on foot (<500m)."""
    walkable = 0
    total = len(amenities)
    if total == 0:
        return 0.0

    for _cat, info in amenities.items():
        dist = info.get("nearest_distance_m")
        if dist is not None and dist <= 500:
            walkable += 1

    return round(walkable / total * 10.0, 1)


def _compute_daily_needs_score(amenities: dict[str, dict[str, Any]]) -> float:
    """Score (0-10) for daily essentials (supermarket + pharmacy + post) within close range."""
    daily_keys = ["supermarkets", "pharmacies", "post_offices"]
    total_score = 0.0
    count = 0
    for key in daily_keys:
        info = amenities.get(key, {})
        dist = info.get("nearest_distance_m")
        if dist is not None and dist <= 500:
            total_score += 10.0
        elif dist is not None and dist <= 1000:
            total_score += 5.0
        count += 1

    return round(total_score / count, 1) if count > 0 else 0.0


def _compute_family_score(amenities: dict[str, dict[str, Any]]) -> float:
    """Score (0-10) weighted for families (schools + parks + hospitals + kindergartens)."""
    weights = {"schools": 3.0, "parks": 2.5, "hospitals": 2.0, "kindergartens": 2.5}
    total_w = 0.0
    total_s = 0.0
    for key, w in weights.items():
        info = amenities.get(key, {})
        score = info.get("score_0_10", 0.0)
        total_s += score * w
        total_w += w

    return round(total_s / total_w, 1) if total_w > 0 else 0.0


def _compute_senior_score(amenities: dict[str, dict[str, Any]], enrichment_meta: dict[str, Any]) -> float:
    """Score (0-10) for retirees (hospital + pharmacy + transport + flat terrain)."""
    weights: dict[str, float] = {}
    scores: dict[str, float] = {}

    # Hospital proximity
    hosp = amenities.get("hospitals", {})
    scores["hospital"] = hosp.get("score_0_10", 0.0)
    weights["hospital"] = 3.0

    # Pharmacy proximity
    pharm = amenities.get("pharmacies", {})
    scores["pharmacy"] = pharm.get("score_0_10", 0.0)
    weights["pharmacy"] = 2.5

    # Transport quality
    transport = enrichment_meta.get("transport") or {}
    tclass = (transport.get("transport_quality_class") or "").upper()
    t_map = {"A": 10.0, "B": 8.0, "C": 5.0, "D": 2.0}
    scores["transport"] = t_map.get(tclass, 3.0)
    weights["transport"] = 2.5

    # Flat terrain proxy: lower altitude = likely flatter (simplified)
    climate = enrichment_meta.get("climate") or {}
    alt = climate.get("estimated_altitude_m")
    if alt is not None:
        if alt < 500:
            scores["terrain"] = 9.0
        elif alt < 800:
            scores["terrain"] = 6.0
        else:
            scores["terrain"] = 3.0
    else:
        scores["terrain"] = 5.0
    weights["terrain"] = 2.0

    total_w = sum(weights.values())
    total_s = sum(scores[k] * weights[k] for k in scores)
    return round(total_s / total_w, 1) if total_w > 0 else 0.0


def _compute_remote_work_score(amenities: dict[str, dict[str, Any]], enrichment_meta: dict[str, Any]) -> float:
    """Score (0-10) for remote workers (quiet + connectivity + cafes)."""
    scores: list[tuple[float, float]] = []

    # Quietness (inverse of noise)
    noise = enrichment_meta.get("noise") or {}
    road_db = noise.get("road_noise_day_db")
    if road_db is not None:
        if road_db < 45:
            scores.append((10.0, 3.0))
        elif road_db < 55:
            scores.append((7.0, 3.0))
        elif road_db < 65:
            scores.append((4.0, 3.0))
        else:
            scores.append((1.0, 3.0))
    else:
        scores.append((5.0, 3.0))

    # Connectivity
    conn = enrichment_meta.get("connectivity_score")
    if conn is not None:
        scores.append((float(conn), 2.5))
    else:
        scores.append((5.0, 2.5))

    # Cafe proximity
    cafes = amenities.get("cafes", {})
    scores.append((cafes.get("score_0_10", 0.0), 2.0))

    # Nature proximity (parks for breaks)
    parks = amenities.get("parks", {})
    scores.append((parks.get("score_0_10", 0.0), 1.5))

    total_w = sum(w for _, w in scores)
    total_s = sum(s * w for s, w in scores)
    return round(total_s / total_w, 1) if total_w > 0 else 0.0


async def analyze_amenities(db: AsyncSession, building_id: uuid.UUID) -> dict[str, Any]:
    """Extract and score amenity data from enrichment_meta.

    Returns comprehensive amenity analysis with per-category scores,
    walking convenience, daily needs, family, senior, and remote work scores.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()

    if building is None:
        return {
            "amenities": {},
            "walking_convenience": 0.0,
            "daily_needs_score": 0.0,
            "family_score": 0.0,
            "senior_score": 0.0,
            "remote_work_score": 0.0,
            "error": "building_not_found",
        }

    enrichment_meta: dict[str, Any] = dict(building.source_metadata_json or {})

    amenities = _extract_amenity_data(enrichment_meta)

    return {
        "amenities": amenities,
        "walking_convenience": _compute_walking_convenience(amenities),
        "daily_needs_score": _compute_daily_needs_score(amenities),
        "family_score": _compute_family_score(amenities),
        "senior_score": _compute_senior_score(amenities, enrichment_meta),
        "remote_work_score": _compute_remote_work_score(amenities, enrichment_meta),
    }
