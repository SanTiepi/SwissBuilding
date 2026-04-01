"""
BatiConnect - Building Score Hub

Central aggregation hub for ALL computed scores of a building.
Single entry point that collects passport, completeness, trust,
geo risk, sustainability, insurance risk, accessibility, sinistralite,
energy, compliance, and overall intelligence scores.

Each sub-score is fetched from its respective service.
Missing data or unavailable services return null gracefully.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Grade helpers
# ---------------------------------------------------------------------------

GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (90, "A"),
    (75, "B"),
    (60, "C"),
    (40, "D"),
    (20, "E"),
    (0, "F"),
]


def _score_to_grade(score: float) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


# ---------------------------------------------------------------------------
# Individual score fetchers (each handles its own errors)
# ---------------------------------------------------------------------------


async def _fetch_passport(db: AsyncSession, building_id: UUID) -> dict | None:
    """Fetch passport grade + score."""
    try:
        from app.services.passport_service import get_passport_summary

        result = await get_passport_summary(db, building_id)
        if result is None:
            return None
        grade = result.get("passport_grade", "F")
        # Convert grade to numeric score
        grade_scores = {"A": 95, "B": 80, "C": 65, "D": 45, "E": 25, "F": 10}
        score = grade_scores.get(grade, 10)
        return {"grade": grade, "score": score}
    except Exception:
        logger.debug("passport_service unavailable for building %s", building_id)
        return None


async def _fetch_completeness(db: AsyncSession, building_id: UUID) -> dict | None:
    """Fetch completeness score + percentage."""
    try:
        from app.services.completeness_engine import evaluate_completeness

        result = await evaluate_completeness(db, building_id)
        score = getattr(result, "overall_score", 0)
        return {"score": round(score * 100, 1) if score <= 1 else round(score, 1), "pct": round(score, 2)}
    except Exception:
        logger.debug("completeness_engine unavailable for building %s", building_id)
        return None


async def _fetch_trust(db: AsyncSession, building_id: UUID) -> dict | None:
    """Fetch trust score + grade."""
    try:
        from app.services.trust_score_calculator import calculate_trust_score

        result = await calculate_trust_score(db, building_id)
        score_val = getattr(result, "overall_score", 0) or 0
        # Trust score is 0-1, convert to 0-100
        score_100 = round(score_val * 100 if score_val <= 1 else score_val, 1)
        return {"score": score_100, "grade": _score_to_grade(score_100)}
    except Exception:
        logger.debug("trust_score_calculator unavailable for building %s", building_id)
        return None


async def _fetch_geo_risk(db: AsyncSession, building_id: UUID) -> dict | None:
    """Fetch geo/environmental risk score."""
    try:
        from sqlalchemy import select

        from app.models.building_geo_context import BuildingGeoContext

        result = await db.execute(select(BuildingGeoContext).where(BuildingGeoContext.building_id == building_id))
        geo = result.scalar_one_or_none()
        if not geo or not geo.context_data:
            return None

        from app.services.enrichment.score_computers import compute_environmental_risk_score

        score_10 = compute_environmental_risk_score(geo.context_data)
        # Convert 0-10 (10=safest) to 0-100
        score_100 = round(score_10 * 10, 1)
        return {"score": score_100, "grade": _score_to_grade(score_100)}
    except Exception:
        logger.debug("geo_risk unavailable for building %s", building_id)
        return None


async def _fetch_sustainability(db: AsyncSession, building_id: UUID) -> dict | None:
    """Fetch green building / sustainability score."""
    try:
        from app.services.environmental_impact_service import compute_green_building_score

        result = await compute_green_building_score(db, building_id)
        score = getattr(result, "overall_score", 0) or 0
        score_100 = round(score * 10, 1) if score <= 10 else round(score, 1)
        return {"score": score_100, "grade": _score_to_grade(score_100)}
    except Exception:
        logger.debug("sustainability unavailable for building %s", building_id)
        return None


async def _fetch_insurance_risk(db: AsyncSession, building_id: UUID) -> dict | None:
    """Fetch insurance risk profile score + grade."""
    try:
        from app.services.insurance_risk_profiler import compute_insurance_risk_profile

        result = await compute_insurance_risk_profile(db, building_id)
        if "error" in result:
            return None
        return {"score": result["overall_score"], "grade": result["grade"]}
    except Exception:
        logger.debug("insurance_risk_profiler unavailable for building %s", building_id)
        return None


async def _fetch_accessibility(db: AsyncSession, building_id: UUID) -> dict | None:
    """Fetch accessibility evaluation score + grade."""
    try:
        from app.services.accessibility_evaluator import evaluate_accessibility

        result = await evaluate_accessibility(db, building_id)
        if "error" in result:
            return None
        return {"score": result["score"], "grade": result["grade"]}
    except Exception:
        logger.debug("accessibility_evaluator unavailable for building %s", building_id)
        return None


async def _fetch_sinistralite(db: AsyncSession, building_id: UUID) -> dict | None:
    """Fetch sinistralite (claims/incidents frequency) score.

    Computed inline: counts incidents + claims, lower count = higher score.
    """
    try:
        from sqlalchemy import select

        from app.models.claim import Claim
        from app.models.incident import IncidentEpisode

        inc_q = await db.execute(select(IncidentEpisode).where(IncidentEpisode.building_id == building_id))
        incidents = list(inc_q.scalars().all())

        claim_q = await db.execute(select(Claim).where(Claim.building_id == building_id))
        claims = list(claim_q.scalars().all())

        total = len(incidents) + len(claims)
        # Score: 0 events = 100 (excellent), 1-2 = 80, 3-5 = 60, 6-10 = 40, >10 = 20
        if total == 0:
            score = 100.0
        elif total <= 2:
            score = 80.0
        elif total <= 5:
            score = 60.0
        elif total <= 10:
            score = 40.0
        else:
            score = 20.0

        return {"score": score, "grade": _score_to_grade(score)}
    except Exception:
        logger.debug("sinistralite unavailable for building %s", building_id)
        return None


async def _fetch_energy(db: AsyncSession, building_id: UUID) -> dict | None:
    """Fetch energy performance class + kWh/m2."""
    try:
        from app.services.energy_performance_service import estimate_energy_class

        result = await estimate_energy_class(db, building_id)
        energy_class = getattr(result, "energy_class", None)
        kwh_m2 = getattr(result, "kwh_per_m2_year", None)
        if energy_class is None:
            return None
        return {"class": energy_class, "kwh_m2": kwh_m2}
    except Exception:
        logger.debug("energy_performance unavailable for building %s", building_id)
        return None


async def _fetch_compliance(db: AsyncSession, building_id: UUID) -> dict | None:
    """Fetch health index compliance dimension or overall health score."""
    try:
        from app.services.building_health_index_service import calculate_health_index

        result = await calculate_health_index(db, building_id)
        score = getattr(result, "score", 0) or 0
        grade = getattr(result, "grade", "F") or "F"
        return {"score": round(score, 1), "grade": grade}
    except Exception:
        logger.debug("building_health_index unavailable for building %s", building_id)
        return None


# ---------------------------------------------------------------------------
# Main aggregation
# ---------------------------------------------------------------------------

# Weights for overall intelligence score
_INTELLIGENCE_WEIGHTS: dict[str, float] = {
    "passport": 2.0,
    "completeness": 1.5,
    "trust": 1.5,
    "insurance_risk": 1.0,
    "accessibility": 0.5,
    "sinistralite": 1.0,
    "compliance": 1.5,
    "geo_risk": 0.5,
    "sustainability": 0.5,
}


async def get_all_scores(db: AsyncSession, building_id: UUID) -> dict:
    """Aggregate all computed scores for a building in one call.

    Returns:
        {
            passport: {grade, score} | null,
            completeness: {score, pct} | null,
            trust: {score, grade} | null,
            geo_risk: {score, grade} | null,
            sustainability: {score, grade} | null,
            insurance_risk: {score, grade} | null,
            accessibility: {score, grade} | null,
            sinistralite: {score, grade} | null,
            energy: {class, kwh_m2} | null,
            compliance: {score, grade} | null,
            overall_intelligence: {score, grade, data_completeness},
            computed_at: ISO timestamp,
        }

    Each sub-score is fetched from its service. Missing = null.
    """
    passport = await _fetch_passport(db, building_id)
    completeness = await _fetch_completeness(db, building_id)
    trust = await _fetch_trust(db, building_id)
    geo_risk = await _fetch_geo_risk(db, building_id)
    sustainability = await _fetch_sustainability(db, building_id)
    insurance_risk = await _fetch_insurance_risk(db, building_id)
    accessibility = await _fetch_accessibility(db, building_id)
    sinistralite = await _fetch_sinistralite(db, building_id)
    energy = await _fetch_energy(db, building_id)
    compliance = await _fetch_compliance(db, building_id)

    # Compute overall intelligence score
    score_sources: dict[str, dict | None] = {
        "passport": passport,
        "completeness": completeness,
        "trust": trust,
        "geo_risk": geo_risk,
        "sustainability": sustainability,
        "insurance_risk": insurance_risk,
        "accessibility": accessibility,
        "sinistralite": sinistralite,
        "compliance": compliance,
    }

    weighted_sum = 0.0
    total_weight = 0.0
    available_count = 0

    for key, data in score_sources.items():
        weight = _INTELLIGENCE_WEIGHTS.get(key, 1.0)
        if data is not None and "score" in data:
            raw_score = data["score"]
            # For insurance_risk, invert: 100 (risky) → 0 (good intelligence)
            if key == "insurance_risk":
                raw_score = 100 - raw_score
            weighted_sum += raw_score * weight
            total_weight += weight
            available_count += 1

    total_possible = len(score_sources)
    data_completeness = round(available_count / total_possible, 2) if total_possible > 0 else 0

    if total_weight > 0:
        overall_score = round(weighted_sum / total_weight, 1)
    else:
        overall_score = 0.0

    overall_grade = _score_to_grade(overall_score)

    return {
        "passport": passport,
        "completeness": completeness,
        "trust": trust,
        "geo_risk": geo_risk,
        "sustainability": sustainability,
        "insurance_risk": insurance_risk,
        "accessibility": accessibility,
        "sinistralite": sinistralite,
        "energy": energy,
        "compliance": compliance,
        "overall_intelligence": {
            "score": overall_score,
            "grade": overall_grade,
            "data_completeness": data_completeness,
        },
        "computed_at": datetime.now(UTC).isoformat(),
    }
