"""Quality of life service — comprehensive composite score for a building location.

Combines mobility, nature, services, culture, safety, comfort, and connectivity
into a 0-100 master score with A-F grading, strengths/weaknesses, and canton comparison.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.services.amenity_analysis_service import _extract_amenity_data
from app.services.nature_score_service import compute_nature_score

logger = logging.getLogger(__name__)

# Dimension weights (sum = 13.5)
_WEIGHTS: dict[str, float] = {
    "mobility": 2.5,
    "nature": 2.0,
    "services": 2.0,
    "culture": 1.5,
    "safety": 2.0,
    "comfort": 2.0,
    "connectivity": 1.0,
}

# Canton average baselines (rough estimates for comparison)
# Score is on 0-100 scale
_CANTON_AVG: dict[str, float] = {
    "ZH": 72,
    "BE": 62,
    "VD": 67,
    "GE": 70,
    "BS": 71,
    "LU": 60,
    "SG": 58,
    "AG": 59,
    "TI": 55,
    "VS": 50,
    "FR": 58,
    "NE": 56,
    "JU": 48,
    "SO": 55,
    "TG": 54,
    "GR": 45,
    "BL": 63,
    "SZ": 56,
    "ZG": 68,
    "SH": 57,
    "AR": 52,
    "AI": 47,
    "NW": 53,
    "OW": 50,
    "UR": 48,
    "GL": 49,
}
_DEFAULT_CANTON_AVG = 58.0


def _grade_from_score_100(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    if score >= 25:
        return "E"
    return "F"


def _quartile_label(score: float, canton_avg: float) -> str:
    diff = score - canton_avg
    if diff > 15:
        return "top 10%"
    if diff > 8:
        return "top 25%"
    if diff > -8:
        return "average"
    return "bottom 25%"


def _compute_mobility(enrichment_meta: dict[str, Any]) -> dict[str, Any]:
    """Mobility dimension (0-10) from transport quality and nearest stops."""
    transport = enrichment_meta.get("transport") or {}
    tclass = (transport.get("transport_quality_class") or "").upper()
    t_map = {"A": 10.0, "B": 8.0, "C": 5.0, "D": 2.0}
    transport_score = t_map.get(tclass, 3.0)

    stops = enrichment_meta.get("nearest_stops") or {}
    stop_dist = stops.get("nearest_stop_distance_m")
    stop_score = 5.0  # default
    if stop_dist is not None:
        if stop_dist < 200:
            stop_score = 10.0
        elif stop_dist < 500:
            stop_score = 7.0
        elif stop_dist < 1000:
            stop_score = 4.0
        else:
            stop_score = 2.0

    # 60% transport class, 40% stop proximity
    score = round(transport_score * 0.6 + stop_score * 0.4, 1)
    factors = []
    if tclass:
        factors.append(f"Transport quality class {tclass}")
    if stop_dist is not None:
        factors.append(f"Nearest stop at {stop_dist}m")

    return {"score": score, "factors": factors}


def _compute_services(enrichment_meta: dict[str, Any]) -> dict[str, Any]:
    """Services dimension (0-10) from essential amenities."""
    amenities = _extract_amenity_data(enrichment_meta)
    essential_keys = ["schools", "hospitals", "pharmacies", "supermarkets"]
    scores_list: list[float] = []
    factors: list[str] = []

    for key in essential_keys:
        info = amenities.get(key, {})
        s = info.get("score_0_10", 0.0)
        scores_list.append(s)
        count = info.get("count", 0)
        if count > 0:
            factors.append(f"{key}: {count} nearby")

    score = round(sum(scores_list) / len(scores_list), 1) if scores_list else 0.0
    return {"score": score, "factors": factors}


def _compute_culture(enrichment_meta: dict[str, Any]) -> dict[str, Any]:
    """Culture/social life dimension (0-10) from restaurants, cafes, banks, heritage."""
    amenities = _extract_amenity_data(enrichment_meta)
    culture_keys = ["restaurants", "cafes", "banks"]
    scores_list: list[float] = []
    factors: list[str] = []

    for key in culture_keys:
        info = amenities.get(key, {})
        s = info.get("score_0_10", 0.0)
        scores_list.append(s)
        count = info.get("count", 0)
        if count > 0:
            factors.append(f"{key}: {count} nearby")

    # Heritage bonus
    heritage = enrichment_meta.get("heritage") or {}
    if heritage.get("isos_protected"):
        scores_list.append(8.0)
        factors.append("ISOS heritage protected area")

    score = round(sum(scores_list) / len(scores_list), 1) if scores_list else 0.0
    return {"score": score, "factors": factors}


def _compute_safety(enrichment_meta: dict[str, Any]) -> dict[str, Any]:
    """Safety dimension (0-10): quiet area + low incidents proxy."""
    noise = enrichment_meta.get("noise") or {}
    road_db = noise.get("road_noise_day_db")
    factors: list[str] = []

    noise_score = 5.0  # default
    if road_db is not None:
        if road_db < 45:
            noise_score = 10.0
            factors.append("Very quiet area")
        elif road_db < 55:
            noise_score = 7.0
            factors.append("Relatively quiet")
        elif road_db < 65:
            noise_score = 4.0
            factors.append("Moderate noise level")
        else:
            noise_score = 1.0
            factors.append("High noise level")

    # No contaminated sites nearby = safer
    contam = enrichment_meta.get("contaminated_sites") or {}
    contam_penalty = 0.0
    if contam.get("is_contaminated"):
        contam_penalty = 2.0
        factors.append("Contaminated site nearby")

    # Seveso / accident sites
    accident = enrichment_meta.get("accident_sites") or {}
    if accident.get("near_seveso_site"):
        contam_penalty += 2.0
        factors.append("Near major accident site")

    score = max(0.0, round(noise_score - contam_penalty, 1))
    return {"score": score, "factors": factors}


def _compute_comfort(enrichment_meta: dict[str, Any]) -> dict[str, Any]:
    """Comfort dimension (0-10): noise (inverse), solar, low pollution."""
    scores: list[tuple[float, float]] = []
    factors: list[str] = []

    # Noise (inverse): weight 3
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

    # Solar potential: weight 2
    solar = enrichment_meta.get("solar") or {}
    suitability = (solar.get("suitability") or "").lower()
    if suitability == "high":
        scores.append((10.0, 2.0))
        factors.append("High solar potential")
    elif suitability == "medium":
        scores.append((6.0, 2.0))
        factors.append("Medium solar potential")
    elif suitability == "low":
        scores.append((3.0, 2.0))
    else:
        scores.append((5.0, 2.0))

    # Low pollution proxy: no contamination = comfort
    contam = enrichment_meta.get("contaminated_sites") or {}
    if not contam.get("is_contaminated"):
        scores.append((8.0, 1.5))
    else:
        scores.append((2.0, 1.5))
        factors.append("Contamination concerns")

    total_w = sum(w for _, w in scores)
    total_s = sum(s * w for s, w in scores)
    score = round(total_s / total_w, 1) if total_w > 0 else 5.0

    return {"score": score, "factors": factors}


def _compute_connectivity(enrichment_meta: dict[str, Any]) -> dict[str, Any]:
    """Connectivity dimension (0-10) from enrichment connectivity_score."""
    conn = enrichment_meta.get("connectivity_score")
    factors: list[str] = []

    if conn is not None:
        score = float(conn)
        if score >= 7:
            factors.append("Good digital connectivity")
        elif score < 4:
            factors.append("Limited digital connectivity")
    else:
        score = 5.0

    mobile = enrichment_meta.get("mobile_coverage") or {}
    if mobile.get("has_5g_coverage"):
        factors.append("5G coverage available")

    bb = enrichment_meta.get("broadband") or {}
    speed = bb.get("max_speed_mbps")
    if speed is not None and speed >= 100:
        factors.append(f"Broadband {speed} Mbps")

    return {"score": round(score, 1), "factors": factors}


async def compute_quality_of_life(db: AsyncSession, building_id: uuid.UUID) -> dict[str, Any]:
    """Compute a 0-100 quality of life composite score.

    Dimensions (all 0-10, weighted):
    - mobility (2.5): transport quality + stop proximity
    - nature (2.0): from nature_score_service
    - services (2.0): essential amenities (schools, hospitals, pharmacies, shops)
    - culture (1.5): restaurants, cafes, heritage
    - safety (2.0): quiet + no contamination/accidents
    - comfort (2.0): noise, solar, pollution
    - connectivity (1.0): digital infra

    Returns: {score, grade, dimensions, strengths, weaknesses, comparison_to_canton_avg, quartile}
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()

    if building is None:
        return {
            "score": 0,
            "grade": "F",
            "dimensions": {},
            "strengths": [],
            "weaknesses": [],
            "comparison_to_canton_avg": 0.0,
            "quartile": "bottom 25%",
            "error": "building_not_found",
        }

    enrichment_meta: dict[str, Any] = dict(building.source_metadata_json or {})
    canton = (building.canton or "").upper()

    # Compute nature score (calls DB again but is lightweight)
    nature_result = await compute_nature_score(db, building_id)
    nature_score = nature_result.get("score", 0.0)

    # Compute other dimensions from enrichment_meta
    mobility = _compute_mobility(enrichment_meta)
    services = _compute_services(enrichment_meta)
    culture = _compute_culture(enrichment_meta)
    safety = _compute_safety(enrichment_meta)
    comfort = _compute_comfort(enrichment_meta)
    connectivity = _compute_connectivity(enrichment_meta)

    dimensions: dict[str, Any] = {
        "mobility": mobility,
        "nature": {"score": nature_score, "factors": nature_result.get("highlights", [])},
        "services": services,
        "culture": culture,
        "safety": safety,
        "comfort": comfort,
        "connectivity": connectivity,
    }

    # Weighted composite (each dimension is 0-10)
    weighted_sum = (
        mobility["score"] * _WEIGHTS["mobility"]
        + nature_score * _WEIGHTS["nature"]
        + services["score"] * _WEIGHTS["services"]
        + culture["score"] * _WEIGHTS["culture"]
        + safety["score"] * _WEIGHTS["safety"]
        + comfort["score"] * _WEIGHTS["comfort"]
        + connectivity["score"] * _WEIGHTS["connectivity"]
    )
    total_weight = sum(_WEIGHTS.values())
    score_10 = weighted_sum / total_weight
    score_100 = round(score_10 * 10)
    score_100 = max(0, min(100, score_100))

    grade = _grade_from_score_100(score_100)

    # Strengths and weaknesses
    strengths: list[str] = []
    weaknesses: list[str] = []

    for dim_name, dim_data in dimensions.items():
        label = dim_name.replace("_", " ").capitalize()
        dim_score = dim_data["score"]
        if dim_score >= 7.0:
            detail = f"{label} ({dim_score:.1f}/10)"
            if dim_data.get("factors"):
                detail += f": {dim_data['factors'][0]}"
            strengths.append(detail)
        elif dim_score < 4.0:
            detail = f"{label} ({dim_score:.1f}/10)"
            if dim_data.get("factors"):
                detail += f": {dim_data['factors'][0]}"
            weaknesses.append(detail)

    # Canton comparison
    canton_avg = _CANTON_AVG.get(canton, _DEFAULT_CANTON_AVG)
    comparison = round(score_100 - canton_avg, 1)
    quartile = _quartile_label(score_100, canton_avg)

    return {
        "score": score_100,
        "grade": grade,
        "dimensions": dimensions,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "comparison_to_canton_avg": comparison,
        "quartile": quartile,
    }
