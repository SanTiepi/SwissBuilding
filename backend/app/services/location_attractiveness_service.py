"""Location attractiveness service — persona-based location scoring.

Scores a building location for different buyer/tenant personas:
young professional, family, retiree, investor, remote worker.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.services.amenity_analysis_service import _extract_amenity_data

logger = logging.getLogger(__name__)


def _compute_young_professional(
    enrichment_meta: dict[str, Any],
    amenities: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Score for young professionals: transport, nightlife/culture, connectivity."""
    scores: list[tuple[float, float]] = []
    factors: list[str] = []

    # Transport quality (weight 3)
    transport = enrichment_meta.get("transport") or {}
    tclass = (transport.get("transport_quality_class") or "").upper()
    t_map = {"A": 10.0, "B": 8.0, "C": 5.0, "D": 2.0}
    t_score = t_map.get(tclass, 3.0)
    scores.append((t_score, 3.0))
    if tclass:
        factors.append(f"Transport class {tclass}")

    # Nightlife / culture: restaurants + cafes (weight 2.5)
    rest = amenities.get("restaurants", {}).get("score_0_10", 0.0)
    cafe = amenities.get("cafes", {}).get("score_0_10", 0.0)
    nightlife_score = (rest + cafe) / 2 if (rest + cafe) > 0 else 0.0
    scores.append((nightlife_score, 2.5))
    rest_count = amenities.get("restaurants", {}).get("count", 0)
    cafe_count = amenities.get("cafes", {}).get("count", 0)
    if rest_count + cafe_count > 5:
        factors.append(f"{rest_count} restaurants, {cafe_count} cafes")

    # Connectivity (weight 2)
    conn = enrichment_meta.get("connectivity_score")
    conn_score = float(conn) if conn is not None else 5.0
    scores.append((conn_score, 2.0))
    if conn is not None and conn >= 7:
        factors.append("Good digital connectivity")

    # Banks (weight 1)
    banks = amenities.get("banks", {}).get("score_0_10", 0.0)
    scores.append((banks, 1.0))

    total_w = sum(w for _, w in scores)
    total_s = sum(s * w for s, w in scores)
    score = round(total_s / total_w, 1) if total_w > 0 else 0.0
    return {"score": score, "factors": factors}


def _compute_family(
    enrichment_meta: dict[str, Any],
    amenities: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Score for families: schools, parks, safety, hospitals, kindergartens."""
    scores: list[tuple[float, float]] = []
    factors: list[str] = []

    # Schools (weight 3)
    schools = amenities.get("schools", {})
    scores.append((schools.get("score_0_10", 0.0), 3.0))
    if schools.get("count", 0) > 0:
        factors.append(f"{schools['count']} schools nearby")

    # Kindergartens (weight 2)
    kinder = amenities.get("kindergartens", {})
    scores.append((kinder.get("score_0_10", 0.0), 2.0))

    # Parks (weight 2.5)
    parks = amenities.get("parks", {})
    scores.append((parks.get("score_0_10", 0.0), 2.5))
    if parks.get("count", 0) > 0:
        factors.append(f"{parks['count']} parks nearby")

    # Safety: quiet + no contamination (weight 2.5)
    noise = enrichment_meta.get("noise") or {}
    road_db = noise.get("road_noise_day_db")
    if road_db is not None:
        if road_db < 45:
            safety = 10.0
        elif road_db < 55:
            safety = 7.0
        elif road_db < 65:
            safety = 4.0
        else:
            safety = 1.0
    else:
        safety = 5.0
    contam = enrichment_meta.get("contaminated_sites") or {}
    if contam.get("is_contaminated"):
        safety = max(0.0, safety - 3.0)
        factors.append("Contamination concern")
    scores.append((safety, 2.5))
    if road_db is not None and road_db < 50:
        factors.append("Quiet neighborhood")

    # Hospitals (weight 1.5)
    hosp = amenities.get("hospitals", {})
    scores.append((hosp.get("score_0_10", 0.0), 1.5))

    total_w = sum(w for _, w in scores)
    total_s = sum(s * w for s, w in scores)
    score = round(total_s / total_w, 1) if total_w > 0 else 0.0
    return {"score": score, "factors": factors}


def _compute_retiree(
    enrichment_meta: dict[str, Any],
    amenities: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Score for retirees: healthcare, quiet, accessibility, shops."""
    scores: list[tuple[float, float]] = []
    factors: list[str] = []

    # Hospitals (weight 3)
    hosp = amenities.get("hospitals", {})
    scores.append((hosp.get("score_0_10", 0.0), 3.0))
    if hosp.get("count", 0) > 0:
        factors.append("Hospital nearby")

    # Pharmacies (weight 2.5)
    pharm = amenities.get("pharmacies", {})
    scores.append((pharm.get("score_0_10", 0.0), 2.5))
    if pharm.get("count", 0) > 0:
        factors.append(f"{pharm['count']} pharmacies")

    # Quiet (weight 2.5)
    noise = enrichment_meta.get("noise") or {}
    road_db = noise.get("road_noise_day_db")
    if road_db is not None:
        if road_db < 45:
            quiet = 10.0
        elif road_db < 55:
            quiet = 7.0
        elif road_db < 65:
            quiet = 4.0
        else:
            quiet = 1.0
    else:
        quiet = 5.0
    scores.append((quiet, 2.5))
    if road_db is not None and road_db < 50:
        factors.append("Quiet area")

    # Shops: supermarkets + post (weight 2)
    super_score = amenities.get("supermarkets", {}).get("score_0_10", 0.0)
    post_score = amenities.get("post_offices", {}).get("score_0_10", 0.0)
    shop_avg = (super_score + post_score) / 2 if (super_score + post_score) > 0 else 0.0
    scores.append((shop_avg, 2.0))
    if amenities.get("supermarkets", {}).get("count", 0) > 0:
        factors.append("Supermarket nearby")

    # Transport (weight 1.5) - important for non-driving elderly
    transport = enrichment_meta.get("transport") or {}
    tclass = (transport.get("transport_quality_class") or "").upper()
    t_map = {"A": 10.0, "B": 8.0, "C": 5.0, "D": 2.0}
    scores.append((t_map.get(tclass, 3.0), 1.5))
    if tclass in ("A", "B"):
        factors.append(f"Good transport ({tclass})")

    total_w = sum(w for _, w in scores)
    total_s = sum(s * w for s, w in scores)
    score = round(total_s / total_w, 1) if total_w > 0 else 0.0
    return {"score": score, "factors": factors}


def _compute_investor(
    enrichment_meta: dict[str, Any],
    amenities: dict[str, dict[str, Any]],
    building: Building,
) -> dict[str, Any]:
    """Score for investors: yield proxy, growth, demand, transport."""
    scores: list[tuple[float, float]] = []
    factors: list[str] = []

    # Transport (strong demand driver, weight 3)
    transport = enrichment_meta.get("transport") or {}
    tclass = (transport.get("transport_quality_class") or "").upper()
    t_map = {"A": 10.0, "B": 8.0, "C": 5.0, "D": 2.0}
    scores.append((t_map.get(tclass, 3.0), 3.0))
    if tclass:
        factors.append(f"Transport class {tclass}")

    # Services richness = demand indicator (weight 2.5)
    osm = enrichment_meta.get("osm_amenities") or {}
    total_am = osm.get("total_amenities", 0)
    if total_am >= 50:
        am_score = 10.0
    elif total_am >= 20:
        am_score = 7.0
    elif total_am >= 10:
        am_score = 5.0
    elif total_am > 0:
        am_score = 3.0
    else:
        am_score = 1.0
    scores.append((am_score, 2.5))
    if total_am > 0:
        factors.append(f"{total_am} amenities in area")

    # Renovation potential (inversely proportional to age -> growth proxy)
    year = building.construction_year
    if year is not None:
        if year >= 2000:
            growth = 6.0
        elif year >= 1980:
            growth = 7.0  # renovation potential
        elif year >= 1960:
            growth = 8.0  # high renovation upside
        else:
            growth = 5.0  # very old, might be costly
    else:
        growth = 5.0
    scores.append((growth, 2.0))
    if year is not None and year < 1990:
        factors.append(f"Built {year} -- renovation potential")

    # No contamination (reduces value, weight 1.5)
    contam = enrichment_meta.get("contaminated_sites") or {}
    if contam.get("is_contaminated"):
        scores.append((1.0, 1.5))
        factors.append("Contamination risk -- value impact")
    else:
        scores.append((8.0, 1.5))

    total_w = sum(w for _, w in scores)
    total_s = sum(s * w for s, w in scores)
    score = round(total_s / total_w, 1) if total_w > 0 else 0.0
    return {"score": score, "factors": factors}


def _compute_remote_worker(
    enrichment_meta: dict[str, Any],
    amenities: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Score for remote workers: connectivity, quiet, cafes, nature."""
    scores: list[tuple[float, float]] = []
    factors: list[str] = []

    # Connectivity (weight 3)
    conn = enrichment_meta.get("connectivity_score")
    conn_score = float(conn) if conn is not None else 5.0
    scores.append((conn_score, 3.0))
    mobile = enrichment_meta.get("mobile_coverage") or {}
    if mobile.get("has_5g_coverage"):
        factors.append("5G coverage")
    bb = enrichment_meta.get("broadband") or {}
    speed = bb.get("max_speed_mbps")
    if speed is not None and speed >= 100:
        factors.append(f"Broadband {speed} Mbps")

    # Quiet (weight 2.5)
    noise = enrichment_meta.get("noise") or {}
    road_db = noise.get("road_noise_day_db")
    if road_db is not None:
        if road_db < 45:
            quiet = 10.0
        elif road_db < 55:
            quiet = 7.0
        elif road_db < 65:
            quiet = 4.0
        else:
            quiet = 1.0
    else:
        quiet = 5.0
    scores.append((quiet, 2.5))
    if road_db is not None and road_db < 50:
        factors.append("Quiet environment")

    # Cafes (weight 2)
    cafes = amenities.get("cafes", {})
    scores.append((cafes.get("score_0_10", 0.0), 2.0))
    if cafes.get("count", 0) > 0:
        factors.append(f"{cafes['count']} cafes for coworking")

    # Parks / nature (weight 1.5)
    parks = amenities.get("parks", {})
    scores.append((parks.get("score_0_10", 0.0), 1.5))
    if parks.get("count", 0) > 0:
        factors.append("Parks nearby for breaks")

    total_w = sum(w for _, w in scores)
    total_s = sum(s * w for s, w in scores)
    score = round(total_s / total_w, 1) if total_w > 0 else 0.0
    return {"score": score, "factors": factors}


async def compute_location_attractiveness(db: AsyncSession, building_id: uuid.UUID) -> dict[str, Any]:
    """Score location attractiveness for different buyer/tenant personas.

    Returns per-persona scores (0-10) with factors, plus overall best/worst fit.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()

    if building is None:
        return {
            "young_professional": {"score": 0.0, "factors": []},
            "family": {"score": 0.0, "factors": []},
            "retiree": {"score": 0.0, "factors": []},
            "investor": {"score": 0.0, "factors": []},
            "remote_worker": {"score": 0.0, "factors": []},
            "overall": {"score": 0.0, "best_fit": "none", "worst_fit": "none"},
            "error": "building_not_found",
        }

    enrichment_meta: dict[str, Any] = dict(building.source_metadata_json or {})
    amenities = _extract_amenity_data(enrichment_meta)

    personas: dict[str, dict[str, Any]] = {
        "young_professional": _compute_young_professional(enrichment_meta, amenities),
        "family": _compute_family(enrichment_meta, amenities),
        "retiree": _compute_retiree(enrichment_meta, amenities),
        "investor": _compute_investor(enrichment_meta, amenities, building),
        "remote_worker": _compute_remote_worker(enrichment_meta, amenities),
    }

    # Overall: average of all personas
    all_scores = [p["score"] for p in personas.values()]
    overall_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0

    # Best and worst fit
    best_fit = max(personas, key=lambda k: personas[k]["score"])
    worst_fit = min(personas, key=lambda k: personas[k]["score"])

    return {
        **personas,
        "overall": {
            "score": overall_score,
            "best_fit": best_fit,
            "worst_fit": worst_fit,
        },
    }
