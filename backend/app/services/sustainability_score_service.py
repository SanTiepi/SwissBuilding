"""Sustainability Score Service — composite sustainability evaluation.

Combines energy performance, pollutant status, climate resilience,
material health, and waste management into a single 0-100 score (A-F grade).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.climate_exposure import ClimateExposureProfile
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.material_risk_predictor import predict_building_material_risks

if TYPE_CHECKING:
    pass

# ── Dimension weights ────────────────────────────────────────────
_WEIGHT_ENERGY = 3.0
_WEIGHT_POLLUTANT = 2.5
_WEIGHT_CLIMATE = 2.0
_WEIGHT_MATERIAL_HEALTH = 1.5
_WEIGHT_WASTE = 1.0
_TOTAL_WEIGHT = _WEIGHT_ENERGY + _WEIGHT_POLLUTANT + _WEIGHT_CLIMATE + _WEIGHT_MATERIAL_HEALTH + _WEIGHT_WASTE

# Grade boundaries
_GRADE_BOUNDARIES: list[tuple[int, str]] = [
    (20, "F"),
    (35, "E"),
    (50, "D"),
    (65, "C"),
    (80, "B"),
    (101, "A"),
]

# Stress level scores
_STRESS_SCORES: dict[str, float] = {
    "low": 90.0,
    "moderate": 60.0,
    "high": 30.0,
    "unknown": 50.0,
}


def _grade_from_score(score: float) -> str:
    """Map a 0-100 score to a letter grade (A=best, F=worst)."""
    for threshold, grade in _GRADE_BOUNDARIES:
        if score < threshold:
            return grade
    return "A"


def _estimate_energy_score(building: Building) -> tuple[float, str]:
    """Estimate energy performance from building age (no CECB field yet).

    Newer buildings tend to have better energy performance.
    Returns (score, explanation).
    """
    year = building.construction_year
    if year is None:
        return 50.0, "Unknown construction year — default estimate"

    if year >= 2010:
        return 85.0, f"Modern construction ({year}) — likely good energy performance"
    if year >= 2000:
        return 70.0, f"Post-2000 construction ({year}) — decent energy standards"
    if year >= 1990:
        return 55.0, f"1990s construction ({year}) — may need energy retrofit"
    if year >= 1970:
        return 35.0, f"1970-1989 construction ({year}) — likely poor insulation"
    return 25.0, f"Pre-1970 construction ({year}) — probable energy deficit"


async def _compute_pollutant_score(db: AsyncSession, building_id: UUID) -> tuple[float, str]:
    """Score based on confirmed pollutant status from diagnostics.

    Clean building = high score, contaminated = low score.
    """
    diagnostics = list(
        (await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))).scalars().all()
    )

    if not diagnostics:
        return 50.0, "No diagnostics — pollutant status unknown"

    diag_ids = [d.id for d in diagnostics]
    samples = list((await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))).scalars().all())

    if not samples:
        return 60.0, "Diagnostics exist but no samples — partial evaluation"

    total = len(samples)
    contaminated = sum(1 for s in samples if s.threshold_exceeded)
    clean_ratio = (total - contaminated) / total

    score = clean_ratio * 100
    if contaminated == 0:
        explanation = f"All {total} samples clean — excellent pollutant status"
    else:
        explanation = f"{contaminated}/{total} samples contaminated — remediation needed"

    return round(score, 1), explanation


async def _compute_climate_score(db: AsyncSession, building_id: UUID) -> tuple[float, str]:
    """Score from ClimateExposureProfile stress indicators."""
    profile = (
        await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building_id))
    ).scalar_one_or_none()

    if profile is None:
        return 50.0, "No climate exposure profile — default estimate"

    stress_values = [
        _STRESS_SCORES.get(profile.moisture_stress or "unknown", 50.0),
        _STRESS_SCORES.get(profile.thermal_stress or "unknown", 50.0),
        _STRESS_SCORES.get(profile.uv_exposure or "unknown", 50.0),
    ]

    score = sum(stress_values) / len(stress_values)
    explanation = f"Moisture: {profile.moisture_stress}, Thermal: {profile.thermal_stress}, UV: {profile.uv_exposure}"
    return round(score, 1), explanation


async def _compute_material_health_score(db: AsyncSession, building_id: UUID) -> tuple[float, str]:
    """Score from predicted material pollutant risks."""
    predictions = await predict_building_material_risks(db, building_id)

    if not predictions:
        return 70.0, "No materials registered — default assumption"

    # Average risk across all materials
    total_risk = 0.0
    materials_with_risk = 0

    for pred in predictions:
        if pred["predictions"]:
            max_prob = max(pred["predictions"].values())
            total_risk += max_prob
            materials_with_risk += 1

    if materials_with_risk == 0:
        return 90.0, f"{len(predictions)} materials, none with predicted risk"

    avg_risk = total_risk / materials_with_risk
    # Invert: high risk → low score
    score = max(0, (1.0 - avg_risk) * 100)
    explanation = (
        f"{materials_with_risk}/{len(predictions)} materials with predicted risk, avg probability {avg_risk:.0%}"
    )
    return round(score, 1), explanation


async def _compute_waste_score(db: AsyncSession, building_id: UUID) -> tuple[float, str]:
    """Score based on whether waste disposal is documented for contaminated samples."""
    diagnostics = list(
        (await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))).scalars().all()
    )

    if not diagnostics:
        return 50.0, "No diagnostics — waste management unknown"

    diag_ids = [d.id for d in diagnostics]
    samples = list((await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))).scalars().all())

    positive = [s for s in samples if s.threshold_exceeded]
    if not positive:
        return 90.0, "No contaminated samples — no waste management needed"

    documented = sum(1 for s in positive if s.waste_disposal_type)
    ratio = documented / len(positive)
    score = ratio * 100

    if ratio == 1.0:
        explanation = f"All {len(positive)} contaminated samples have waste classification"
    else:
        explanation = f"{documented}/{len(positive)} contaminated samples with waste classification"

    return round(score, 1), explanation


async def compute_sustainability_score(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Compute a composite sustainability score 0-100 (A-F grade).

    Combines: energy_performance, pollutant_status, climate_resilience,
    material_health, waste_management.

    Returns: {score, grade, breakdown, recommendations}.
    """
    # Load building for energy estimation
    building = (await db.execute(select(Building).where(Building.id == building_id))).scalar_one_or_none()

    if building is None:
        return {
            "score": 0,
            "grade": "F",
            "breakdown": {},
            "recommendations": ["Building not found"],
        }

    # Compute all dimensions
    energy_score, energy_explanation = _estimate_energy_score(building)
    pollutant_score, pollutant_explanation = await _compute_pollutant_score(db, building_id)
    climate_score, climate_explanation = await _compute_climate_score(db, building_id)
    material_score, material_explanation = await _compute_material_health_score(db, building_id)
    waste_score, waste_explanation = await _compute_waste_score(db, building_id)

    # Weighted composite
    composite = (
        energy_score * _WEIGHT_ENERGY
        + pollutant_score * _WEIGHT_POLLUTANT
        + climate_score * _WEIGHT_CLIMATE
        + material_score * _WEIGHT_MATERIAL_HEALTH
        + waste_score * _WEIGHT_WASTE
    ) / _TOTAL_WEIGHT

    final_score = round(min(max(composite, 0), 100), 1)
    grade = _grade_from_score(final_score)

    # Generate recommendations
    recommendations: list[str] = []
    if energy_score < 50:
        recommendations.append("Consider energy audit and insulation retrofit")
    if pollutant_score < 50:
        recommendations.append("Plan pollutant remediation for contaminated materials")
    if climate_score < 50:
        recommendations.append("Assess climate adaptation measures (moisture, thermal protection)")
    if material_score < 50:
        recommendations.append("Investigate high-risk materials for pollutant testing")
    if waste_score < 50:
        recommendations.append("Document waste disposal types for all contaminated samples")

    return {
        "score": final_score,
        "grade": grade,
        "breakdown": {
            "energy_performance": {
                "score": energy_score,
                "weight": _WEIGHT_ENERGY,
                "explanation": energy_explanation,
            },
            "pollutant_status": {
                "score": pollutant_score,
                "weight": _WEIGHT_POLLUTANT,
                "explanation": pollutant_explanation,
            },
            "climate_resilience": {
                "score": climate_score,
                "weight": _WEIGHT_CLIMATE,
                "explanation": climate_explanation,
            },
            "material_health": {
                "score": material_score,
                "weight": _WEIGHT_MATERIAL_HEALTH,
                "explanation": material_explanation,
            },
            "waste_management": {
                "score": waste_score,
                "weight": _WEIGHT_WASTE,
                "explanation": waste_explanation,
            },
        },
        "recommendations": recommendations,
    }
