"""Geology intelligence service — Programme V.

Extracts geological context from enrichment metadata (source_metadata_json)
populated by the building enrichment pipeline. Computes foundation risk scores,
construction constraints, and underground risk assessments.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building

# ---------------------------------------------------------------------------
# Risk scoring weights and tables
# ---------------------------------------------------------------------------

_SEISMIC_SCORES: dict[str, int] = {
    "3b": 90,
    "3a": 70,
    "2": 40,
    "1": 15,
}

_GROUNDWATER_SCORES: dict[str, int] = {
    "S1": 80,
    "S2": 50,
    "S3": 25,
}

_LANDSLIDE_SCORES: dict[str, int] = {
    "high": 90,
    "medium": 50,
    "low": 15,
    "none": 5,
}

_FLOOD_SCORES: dict[str, int] = {
    "high": 85,
    "medium": 45,
    "low": 15,
    "none": 5,
}

# Weights for foundation risk
_WEIGHTS = {
    "seismic": 3.0,
    "groundwater": 2.0,
    "contamination": 2.5,
    "landslide": 2.0,
    "flood": 2.0,
}

_TOTAL_WEIGHT = sum(_WEIGHTS.values())

# Grade boundaries
_GRADE_BOUNDARIES = [
    (0, 20, "A"),
    (20, 40, "B"),
    (40, 55, "C"),
    (55, 70, "D"),
    (70, 85, "E"),
    (85, 101, "F"),
]


def _score_to_grade(score: float) -> str:
    for lo, hi, grade in _GRADE_BOUNDARIES:
        if lo <= score < hi:
            return grade
    return "F"


# ---------------------------------------------------------------------------
# Helpers — extract from enrichment_meta
# ---------------------------------------------------------------------------


def _get_enrichment_meta(building: Building) -> dict[str, Any]:
    return dict(building.source_metadata_json or {}) if building.source_metadata_json else {}


def _normalize_flood_risk(enrichment: dict[str, Any]) -> str:
    """Extract flood risk level from enrichment data."""
    # From natural_hazards
    hazards = enrichment.get("natural_hazards", {})
    flood = hazards.get("flood_risk", "")

    # Also from flood_zones
    fz = enrichment.get("flood_zones", {})
    flood_level = fz.get("flood_danger_level", "")

    raw = (str(flood) + " " + str(flood_level)).lower()
    if "hoch" in raw or "erheblich" in raw or "high" in raw or "significant" in raw:
        return "high"
    if "mittel" in raw or "medium" in raw or "moderate" in raw:
        return "medium"
    if "gering" in raw or "low" in raw or "minor" in raw:
        return "low"
    if raw.strip():
        return "low"
    return "none"


def _normalize_landslide_risk(enrichment: dict[str, Any]) -> str:
    hazards = enrichment.get("natural_hazards", {})
    raw = str(hazards.get("landslide_risk", "")).lower()
    if "hoch" in raw or "high" in raw:
        return "high"
    if "mittel" in raw or "medium" in raw:
        return "medium"
    if "gering" in raw or "low" in raw:
        return "low"
    return "none"


def _normalize_seismic_zone(enrichment: dict[str, Any]) -> str:
    seismic = enrichment.get("seismic", {})
    zone = str(seismic.get("seismic_zone", "")).strip().lower()
    # Normalize to canonical values
    if zone in ("3b", "3a", "2", "1"):
        return zone
    if "3" in zone:
        return "3a"
    return zone or ""


def _get_groundwater_zone(enrichment: dict[str, Any]) -> str:
    """Get protection zone S1/S2/S3 from water_protection or groundwater data."""
    wp = enrichment.get("water_protection", {})
    zone = wp.get("protection_zone", "") or wp.get("zone", "")
    raw = str(zone).upper().strip()
    if "S1" in raw:
        return "S1"
    if "S2" in raw:
        return "S2"
    if "S3" in raw:
        return "S3"
    return ""


def _is_contaminated(enrichment: dict[str, Any]) -> bool:
    cs = enrichment.get("contaminated_sites", {})
    return bool(cs.get("is_contaminated"))


def _get_radon_level(enrichment: dict[str, Any]) -> str:
    radon = enrichment.get("radon", {})
    return str(radon.get("radon_level", "")).lower() or "unknown"


# ---------------------------------------------------------------------------
# Foundation risk score computation (pure function)
# ---------------------------------------------------------------------------


def compute_foundation_risk_score(enrichment_meta: dict[str, Any]) -> dict[str, Any]:
    """Score 0-100 for foundation/subsurface risk.

    Higher = worse. Grade A (best) to F (worst).
    """
    seismic_zone = _normalize_seismic_zone(enrichment_meta)
    gw_zone = _get_groundwater_zone(enrichment_meta)
    contaminated = _is_contaminated(enrichment_meta)
    landslide = _normalize_landslide_risk(enrichment_meta)
    flood = _normalize_flood_risk(enrichment_meta)

    # Individual scores
    seismic_score = _SEISMIC_SCORES.get(seismic_zone, 5)
    gw_score = _GROUNDWATER_SCORES.get(gw_zone, 5)
    contam_score = 85 if contaminated else 5
    landslide_score = _LANDSLIDE_SCORES.get(landslide, 5)
    flood_score = _FLOOD_SCORES.get(flood, 5)

    # Weighted average
    weighted = (
        seismic_score * _WEIGHTS["seismic"]
        + gw_score * _WEIGHTS["groundwater"]
        + contam_score * _WEIGHTS["contamination"]
        + landslide_score * _WEIGHTS["landslide"]
        + flood_score * _WEIGHTS["flood"]
    )
    score = round(weighted / _TOTAL_WEIGHT, 1)
    grade = _score_to_grade(score)

    breakdown = {
        "seismic": {"score": seismic_score, "weight": _WEIGHTS["seismic"], "zone": seismic_zone or "n/a"},
        "groundwater": {"score": gw_score, "weight": _WEIGHTS["groundwater"], "zone": gw_zone or "none"},
        "contamination": {"score": contam_score, "weight": _WEIGHTS["contamination"], "contaminated": contaminated},
        "landslide": {"score": landslide_score, "weight": _WEIGHTS["landslide"], "risk": landslide},
        "flood": {"score": flood_score, "weight": _WEIGHTS["flood"], "risk": flood},
    }

    # Top risks: anything scoring > 40
    top_risks = []
    for key, data in breakdown.items():
        if data["score"] > 40:
            top_risks.append(
                {
                    "type": key,
                    "score": data["score"],
                    "detail": str(data.get("zone") or data.get("risk") or data.get("contaminated", "")),
                }
            )

    return {
        "score": score,
        "grade": grade,
        "breakdown": breakdown,
        "top_risks": top_risks,
    }


# ---------------------------------------------------------------------------
# Construction constraints
# ---------------------------------------------------------------------------


def _derive_constraints(enrichment_meta: dict[str, Any]) -> list[str]:
    """Derive construction constraints from geological context."""
    constraints: list[str] = []

    gw_zone = _get_groundwater_zone(enrichment_meta)
    if gw_zone == "S1":
        constraints.append("Zone S1: construction interdite ou très restreinte — captage d'eau potable")
    elif gw_zone == "S2":
        constraints.append(
            "Zone S2: restrictions sur l'évacuation des eaux usées et stockage de substances dangereuses"
        )
    elif gw_zone == "S3":
        constraints.append("Zone S3: restrictions sur les excavations profondes et l'injection dans le sous-sol")

    seismic = _normalize_seismic_zone(enrichment_meta)
    if seismic in ("3a", "3b"):
        constraints.append(f"Zone sismique {seismic}: dimensionnement parasismique SIA 261 requis — analyse dynamique")
    elif seismic == "2":
        constraints.append("Zone sismique 2: dimensionnement parasismique SIA 261 requis")

    if _is_contaminated(enrichment_meta):
        cs = enrichment_meta.get("contaminated_sites", {})
        status = cs.get("investigation_status", "inconnu")
        constraints.append(f"Site contaminé (cadastre fédéral) — état d'investigation: {status}")

    flood = _normalize_flood_risk(enrichment_meta)
    if flood == "high":
        constraints.append("Zone inondable à haut risque — mesures de protection obligatoires selon LEaux")
    elif flood == "medium":
        constraints.append("Zone inondable à risque moyen — mesures de protection recommandées")

    landslide = _normalize_landslide_risk(enrichment_meta)
    if landslide == "high":
        constraints.append("Risque de glissement élevé — étude géotechnique approfondie requise")
    elif landslide == "medium":
        constraints.append("Risque de glissement moyen — étude géotechnique recommandée")

    return constraints


# ---------------------------------------------------------------------------
# Underground risk assessment
# ---------------------------------------------------------------------------


def _derive_underground_risk(enrichment_meta: dict[str, Any]) -> dict[str, str]:
    """Assess underground/subsurface-specific risks."""
    gw_zone = _get_groundwater_zone(enrichment_meta)
    contaminated = _is_contaminated(enrichment_meta)
    radon = _get_radon_level(enrichment_meta)

    # Groundwater impact
    if gw_zone == "S1":
        gw_impact = "high"
    elif gw_zone == "S2":
        gw_impact = "moderate"
    elif gw_zone == "S3":
        gw_impact = "low"
    else:
        gw_impact = "none"

    # Basement humidity risk from groundwater proximity
    if gw_zone in ("S1", "S2"):
        humidity_risk = "high"
    elif gw_zone == "S3":
        humidity_risk = "moderate"
    else:
        humidity_risk = "low"

    # Radon from soil
    if radon == "high":
        radon_soil = "Risque radon élevé — mesures de protection requises (ORaP Art. 110)"
    elif radon == "medium":
        radon_soil = "Risque radon modéré — mesure recommandée"
    else:
        radon_soil = "Risque radon faible"

    return {
        "groundwater_impact": gw_impact,
        "basement_humidity_risk": humidity_risk,
        "radon_from_soil": radon_soil,
        "contamination_risk": "high" if contaminated else "none",
    }


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def _derive_recommendations(enrichment_meta: dict[str, Any], foundation_risk: dict[str, Any]) -> list[str]:
    """Generate actionable recommendations based on geological context."""
    recs: list[str] = []
    score = foundation_risk.get("score", 0)

    if score >= 70:
        recs.append("Risque fondation élevé — mandater un ingénieur géotechnicien avant tout projet")
    elif score >= 40:
        recs.append("Risque fondation modéré — étude géotechnique recommandée pour travaux importants")

    if _is_contaminated(enrichment_meta):
        recs.append("Site contaminé — consulter le cadastre cantonal des sites pollués et évaluer l'assainissement")

    seismic = _normalize_seismic_zone(enrichment_meta)
    if seismic in ("3a", "3b"):
        recs.append("Zone sismique élevée — vérifier la conformité parasismique (SIA 261/SIA 269/8)")

    gw_zone = _get_groundwater_zone(enrichment_meta)
    if gw_zone in ("S1", "S2"):
        recs.append("Zone de protection des eaux — consulter le service cantonal de l'environnement")

    radon = _get_radon_level(enrichment_meta)
    if radon == "high":
        recs.append("Risque radon élevé — effectuer une mesure en conditions hivernales et prévoir un assainissement")

    flood = _normalize_flood_risk(enrichment_meta)
    if flood in ("high", "medium"):
        recs.append("Zone inondable — vérifier la carte des dangers et les prescriptions communales")

    if not recs:
        recs.append("Contexte géologique favorable — pas de contrainte majeure identifiée")

    return recs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def analyze_geology(db: AsyncSession, building_id: UUID) -> dict[str, Any]:
    """Extract geological intelligence from building enrichment data.

    Returns comprehensive geological assessment with soil context,
    foundation risk, construction constraints, underground risk, and recommendations.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    enrichment = _get_enrichment_meta(building)

    # Soil context
    soil_context = {
        "contaminated": _is_contaminated(enrichment),
        "groundwater_zone": _get_groundwater_zone(enrichment) or "none",
        "flood_risk": _normalize_flood_risk(enrichment),
        "seismic_zone": _normalize_seismic_zone(enrichment) or "unknown",
        "landslide_risk": _normalize_landslide_risk(enrichment),
    }

    # Foundation risk
    foundation_risk = compute_foundation_risk_score(enrichment)

    # Construction constraints
    constraints = _derive_constraints(enrichment)

    # Underground risk
    underground_risk = _derive_underground_risk(enrichment)

    # Recommendations
    recommendations = _derive_recommendations(enrichment, foundation_risk)

    return {
        "building_id": str(building_id),
        "soil_context": soil_context,
        "foundation_risk": foundation_risk,
        "construction_constraints": constraints,
        "underground_risk": underground_risk,
        "recommendations": recommendations,
    }
