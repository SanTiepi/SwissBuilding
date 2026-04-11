"""Investment score service — Programme R + V composite.

Computes an investment attractiveness score (0-100, A-F) by combining
rental yield, appreciation potential, risk profile, energy trajectory,
and subsidy eligibility. Builds on market_valuation_service,
geology_intelligence_service, and rental_benchmark_service.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.geology_intelligence_service import compute_foundation_risk_score
from app.services.market_valuation_service import (
    _CANTON_AVG_YIELD,
    _DEFAULT_AVG_YIELD,
    _DEFAULT_RENT_M2,
    _RENT_PER_M2_MONTH,
    _age_factor,
    _building_age,
    _get_price_per_m2,
    _location_factor,
    _map_building_type,
    _surface,
)

# ---------------------------------------------------------------------------
# Component weights
# ---------------------------------------------------------------------------

_WEIGHTS = {
    "yield": 3.0,
    "appreciation": 2.0,
    "risk": 2.5,
    "energy": 1.5,
    "subsidy": 1.0,
}
_TOTAL_WEIGHT = sum(_WEIGHTS.values())

# Grade boundaries (same as geology)
_GRADE_BOUNDARIES = [
    (80, 101, "A"),
    (65, 80, "B"),
    (50, 65, "C"),
    (35, 50, "D"),
    (20, 35, "E"),
    (0, 20, "F"),
]


def _score_to_grade(score: float) -> str:
    for lo, hi, grade in _GRADE_BOUNDARIES:
        if lo <= score < hi:
            return grade
    return "F"


# ---------------------------------------------------------------------------
# Component scorers (each returns 0-100)
# ---------------------------------------------------------------------------


def _yield_score(gross_yield: float, canton_avg: float) -> float:
    """Score rental yield vs canton average. Higher yield = better score."""
    if canton_avg <= 0:
        return 50.0
    ratio = gross_yield / canton_avg
    # ratio 1.0 = 60 points, 1.5 = 90, 0.5 = 30
    score = min(100, max(0, 60 * ratio))
    return round(score, 1)


def _appreciation_score(age_factor: float, location_factor: float, has_renovation_potential: bool) -> float:
    """Score appreciation potential from location + renovation upside."""
    # Fresh building in premium location = high appreciation
    base = (location_factor - 0.95) / 0.10 * 50  # 0-50 from location
    base = min(50, max(0, base))

    # Renovation potential adds value
    if has_renovation_potential:
        base += 25

    # Very old buildings have more renovation upside
    if age_factor < 0.80:
        base += 15

    return round(min(100, base), 1)


def _risk_score_from_pollutants_and_geology(pollutant_severity: str, foundation_grade: str) -> float:
    """Lower risk = higher investment score. Inverted scale."""
    # Pollutant penalty
    pollutant_penalty = {
        "clean": 0,
        "minor": 15,
        "major": 35,
        "critical": 55,
    }.get(pollutant_severity, 20)

    # Geology penalty
    geology_penalty = {
        "A": 0,
        "B": 8,
        "C": 18,
        "D": 30,
        "E": 42,
        "F": 55,
    }.get(foundation_grade, 20)

    # Combined penalty, max 100
    total_penalty = min(100, pollutant_penalty + geology_penalty)
    return round(100 - total_penalty, 1)


def _energy_score(energy_class: str | None, construction_year: int | None) -> float:
    """Score energy trajectory. Good energy class or recent build = high."""
    class_scores = {
        "A": 95,
        "B": 85,
        "C": 70,
        "D": 55,
        "E": 40,
        "F": 25,
        "G": 10,
    }
    if energy_class:
        return float(class_scores.get(energy_class.upper(), 50))

    # Estimate from construction year
    if not construction_year:
        return 50.0
    current = datetime.now(UTC).year
    age = current - construction_year
    if age < 10:
        return 80.0
    if age < 30:
        return 60.0
    if age < 50:
        return 40.0
    return 25.0


def _subsidy_score(enrichment_meta: dict[str, Any]) -> float:
    """Score subsidy eligibility (reduces net investment cost)."""
    subsidies = enrichment_meta.get("subsidies", {})
    if not subsidies:
        return 30.0  # unknown = neutral-low

    eligible = subsidies.get("eligible_programs", [])
    total_amount = subsidies.get("total_estimated_chf", 0)

    if total_amount > 50000:
        return 90.0
    if total_amount > 20000:
        return 70.0
    if len(eligible) > 0:
        return 55.0
    return 30.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _pollutant_severity(db: AsyncSession, building_id: UUID) -> str:
    stmt = (
        select(Sample)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
        )
    )
    result = await db.execute(stmt)
    samples = list(result.scalars().all())
    exceeded = [s for s in samples if s.threshold_exceeded]
    if not exceeded:
        return "clean"
    risk_levels = {s.risk_level for s in exceeded if s.risk_level}
    if "critical" in risk_levels:
        return "critical"
    if len(exceeded) >= 3 or "high" in risk_levels:
        return "major"
    return "minor"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def compute_investment_score(db: AsyncSession, building_id: UUID) -> dict[str, Any]:
    """Compute composite investment attractiveness score (0-100, A-F).

    Dimensions: yield, appreciation, risk, energy, subsidy.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    canton = (building.canton or "").upper()
    surface = _surface(building)
    meta = building.source_metadata_json or {}

    # --- Yield component ---
    rent_m2 = _RENT_PER_M2_MONTH.get(canton, _DEFAULT_RENT_M2)
    annual_rent = surface * rent_m2 * 12
    btype = _map_building_type(building.building_type or "")
    price_m2 = _get_price_per_m2(canton, btype)
    market_value = surface * price_m2 * _age_factor(_building_age(building))
    gross_yield = (annual_rent / market_value * 100) if market_value > 0 else 0
    canton_avg = _CANTON_AVG_YIELD.get(canton, _DEFAULT_AVG_YIELD)
    yield_sc = _yield_score(gross_yield, canton_avg)

    # --- Appreciation component ---
    af = _age_factor(_building_age(building))
    lf = _location_factor(canton)
    has_reno_potential = af < 0.90 and (
        not building.renovation_year or (datetime.now(UTC).year - building.renovation_year) > 15
    )
    appreciation_sc = _appreciation_score(af, lf, has_reno_potential)

    # --- Risk component ---
    severity = await _pollutant_severity(db, building_id)
    enrichment = dict(meta) if meta else {}
    foundation = compute_foundation_risk_score(enrichment)
    risk_sc = _risk_score_from_pollutants_and_geology(severity, foundation["grade"])

    # --- Energy component ---
    e_class = meta.get("energy_class") or meta.get("cecb_class")
    energy_sc = _energy_score(e_class, building.construction_year)

    # --- Subsidy component ---
    subsidy_sc = _subsidy_score(enrichment)

    # --- Weighted composite ---
    weighted = (
        yield_sc * _WEIGHTS["yield"]
        + appreciation_sc * _WEIGHTS["appreciation"]
        + risk_sc * _WEIGHTS["risk"]
        + energy_sc * _WEIGHTS["energy"]
        + subsidy_sc * _WEIGHTS["subsidy"]
    )
    score = round(weighted / _TOTAL_WEIGHT, 1)
    grade = _score_to_grade(score)

    # --- Strengths & weaknesses ---
    components = {
        "yield": yield_sc,
        "appreciation": appreciation_sc,
        "risk": risk_sc,
        "energy": energy_sc,
        "subsidy": subsidy_sc,
    }
    strengths = [k for k, v in components.items() if v >= 65]
    weaknesses = [k for k, v in components.items() if v < 40]

    # Recommendation
    if score >= 70:
        recommendation = "Investissement attractif — bon équilibre rendement/risque"
    elif score >= 50:
        recommendation = "Investissement acceptable — points d'amélioration identifiés"
    elif score >= 35:
        recommendation = "Investissement à risque — analyse approfondie recommandée"
    else:
        recommendation = "Investissement déconseillé en l'état — risques majeurs identifiés"

    return {
        "building_id": str(building_id),
        "score": score,
        "grade": grade,
        "breakdown": {
            "yield": {"score": yield_sc, "weight": _WEIGHTS["yield"], "gross_yield_pct": round(gross_yield, 2)},
            "appreciation": {"score": appreciation_sc, "weight": _WEIGHTS["appreciation"]},
            "risk": {
                "score": risk_sc,
                "weight": _WEIGHTS["risk"],
                "pollutant_severity": severity,
                "foundation_grade": foundation["grade"],
            },
            "energy": {"score": energy_sc, "weight": _WEIGHTS["energy"], "class": e_class},
            "subsidy": {"score": subsidy_sc, "weight": _WEIGHTS["subsidy"]},
        },
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendation": recommendation,
        "generated_at": datetime.now(UTC).isoformat(),
    }
