"""Geo risk score composite service — computes a 0-100 geospatial risk score for a building.

Combines 5 sub-dimensions (each 0-10) from cached geo context data:
- Inondation (flood risk)
- Seismic class
- Grêle (hail frequency)
- Contaminated sites proximity
- Radon potential
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building_geo_context import BuildingGeoContext

logger = logging.getLogger(__name__)

# Weights for each sub-dimension (equal by default)
SUB_DIMENSIONS = ["inondation", "seismic", "grele", "contamination", "radon"]
WEIGHT_PER_DIM = 2  # 5 dims x 2 = 10 -> scaled to 100


def _score_inondation(context_data: dict[str, Any]) -> float:
    """Score flood risk 0-10 from natural_hazards layer."""
    hazards = context_data.get("natural_hazards") or {}
    gefahrenstufe = hazards.get("gefahrenstufe", "")

    if not gefahrenstufe:
        return 0.0

    # Swiss hazard levels: erheblich (considerable) > mittel (medium) > gering (low) > restgefahr (residual)
    level_map = {
        "erheblich": 10.0,
        "mittel": 7.0,
        "gering": 4.0,
        "restgefahr": 2.0,
        "residual": 2.0,
        "keine": 0.0,
    }

    level_str = str(gefahrenstufe).lower().strip()
    for key, score in level_map.items():
        if key in level_str:
            return score

    return 3.0  # Unknown hazard level — moderate default


def _score_seismic(context_data: dict[str, Any]) -> float:
    """Score seismic risk 0-10 from building ground class or zone."""
    # Check for seismic data in context — may be stored under various keys
    seismic = context_data.get("seismic") or context_data.get("erdbeben") or {}

    baugrundklasse = seismic.get("baugrundklasse", "") or seismic.get("klasse", "")
    if not baugrundklasse:
        return 0.0

    # Swiss SIA 261 ground classes: E (worst) > D > C > B > A (best)
    class_map = {
        "E": 10.0,
        "D": 8.0,
        "C": 6.0,
        "B": 4.0,
        "A": 2.0,
    }

    class_str = str(baugrundklasse).upper().strip()
    for key, score in class_map.items():
        if key in class_str:
            return score

    return 3.0


def _score_grele(context_data: dict[str, Any]) -> float:
    """Score hail risk 0-10 from climate/hail data."""
    # Hail data may come from climate overlays or dedicated grele layer
    grele = context_data.get("grele") or context_data.get("hail") or {}
    climate = context_data.get("climate") or {}

    # Check for explicit hail frequency or zone
    frequency = grele.get("frequency") or grele.get("haeufigkeit")
    if frequency is not None:
        try:
            freq_val = float(frequency)
            return min(10.0, round(freq_val, 1))
        except (ValueError, TypeError):
            pass

    zone = grele.get("zone", "") or climate.get("hail_zone", "")
    if zone:
        zone_map = {"high": 8.0, "hoch": 8.0, "medium": 5.0, "mittel": 5.0, "low": 2.0, "gering": 2.0}
        zone_str = str(zone).lower().strip()
        for key, score in zone_map.items():
            if key in zone_str:
                return score

    return 0.0


def _score_contamination(context_data: dict[str, Any]) -> float:
    """Score contamination risk 0-10 from contaminated sites data."""
    sites = context_data.get("contaminated_sites") or {}

    if not sites:
        return 0.0

    status = sites.get("status", "")
    kategorie = sites.get("kategorie", "") or sites.get("belastungskategorie", "")

    if not status and not kategorie:
        return 0.0

    # Any contaminated site nearby = elevated risk
    status_str = str(status).lower()
    if "sanierungsbedürftig" in status_str or "assaini" in status_str:
        return 10.0
    if "überwachungsbedürftig" in status_str or "surveill" in status_str:
        return 7.0
    if "belastet" in status_str or "pollué" in status_str or "contamin" in status_str:
        return 5.0

    # Has entry but unknown severity
    return 3.0


def _score_radon(context_data: dict[str, Any]) -> float:
    """Score radon risk 0-10 from radon layer data."""
    radon = context_data.get("radon") or {}

    if not radon:
        return 0.0

    # Check for Bq/m3 value
    bq = radon.get("radon_bq_m3") or radon.get("bq_m3")
    if bq is not None:
        try:
            # Parse range like "200-400" -> take upper bound
            bq_str = str(bq)
            if "-" in bq_str:
                bq_val = float(bq_str.split("-")[-1])
            else:
                bq_val = float(bq_str)

            # Swiss thresholds: 300 Bq/m3 reference, 1000 Bq/m3 action
            if bq_val >= 1000:
                return 10.0
            if bq_val >= 300:
                return 7.0
            if bq_val >= 100:
                return 4.0
            return 2.0
        except (ValueError, TypeError):
            pass

    # Zone-based scoring
    zone = radon.get("zone", "") or radon.get("radonrisiko", "")
    if zone:
        zone_str = str(zone).lower()
        if "hoch" in zone_str or "high" in zone_str or "élevé" in zone_str:
            return 8.0
        if "mittel" in zone_str or "moderate" in zone_str or "moyen" in zone_str:
            return 5.0
        if "gering" in zone_str or "low" in zone_str or "faible" in zone_str:
            return 2.0

    return 0.0


def compute_geo_risk_score(context_data: dict[str, Any]) -> dict[str, Any]:
    """Compute composite geo risk score from context_data.

    Returns dict with composite score (0-100) and individual sub-scores (0-10).
    """
    sub_scores = {
        "inondation": _score_inondation(context_data),
        "seismic": _score_seismic(context_data),
        "grele": _score_grele(context_data),
        "contamination": _score_contamination(context_data),
        "radon": _score_radon(context_data),
    }

    # Composite: sum of sub-scores x 2 (5 dims x 10 max x 2 = 100 max)
    composite = round(sum(sub_scores.values()) * WEIGHT_PER_DIM)

    return {
        "score": min(100, composite),
        **sub_scores,
    }


async def get_geo_risk_score(db: AsyncSession, building_id: uuid.UUID) -> dict[str, Any] | None:
    """Get or compute geo risk score for a building.

    Uses cached geo context data. Returns None if building has no geo context.
    """
    result = await db.execute(
        select(BuildingGeoContext).where(BuildingGeoContext.building_id == building_id)
    )
    geo_ctx = result.scalar_one_or_none()

    if geo_ctx is None:
        return None

    context_data: dict[str, Any] = dict(geo_ctx.context_data or {})

    # Check for cached score
    cached = context_data.get("geo_risk_score")
    if cached is not None:
        return cached

    # Compute and cache
    score_result = compute_geo_risk_score(context_data)

    # Store in context_data for caching
    context_data["geo_risk_score"] = score_result
    geo_ctx.context_data = context_data
    await db.flush()

    return score_result
