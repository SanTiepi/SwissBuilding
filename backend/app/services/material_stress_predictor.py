"""
SwissBuildingOS - Material Stress Predictor

Predicts material degradation acceleration based on climate stress factors.
Combines material type, age, and climate exposure to estimate time-to-critical
and recommend preventive actions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.zone import Zone

# ---------------------------------------------------------------------------
# Degradation factors: material_type -> {stress_factor: sensitivity 0-1}
# ---------------------------------------------------------------------------

DEGRADATION_FACTORS: dict[str, dict[str, float]] = {
    "asbestos_friable": {"freeze_thaw": 0.8, "uv": 0.3, "moisture": 0.6},
    "asbestos_bonded": {"freeze_thaw": 0.3, "uv": 0.1, "moisture": 0.2},
    "pcb_joint": {"freeze_thaw": 0.7, "uv": 0.5, "moisture": 0.4},
    "lead_paint": {"freeze_thaw": 0.2, "uv": 0.6, "moisture": 0.3},
    "concrete": {"freeze_thaw": 0.9, "uv": 0.1, "moisture": 0.5},
}

# Default climate stress profile when no ClimateExposureProfile is available
_DEFAULT_CLIMATE_STRESS: dict[str, float] = {
    "freeze_thaw": 0.4,
    "uv": 0.3,
    "moisture": 0.3,
}

# Base lifespan in years for each material type (without climate stress)
_BASE_LIFESPAN: dict[str, int] = {
    "asbestos_friable": 30,
    "asbestos_bonded": 50,
    "pcb_joint": 40,
    "lead_paint": 35,
    "concrete": 80,
}

# Condition to numeric score mapping
_CONDITION_SCORES: dict[str, float] = {
    "excellent": 1.0,
    "good": 0.8,
    "fair": 0.5,
    "poor": 0.25,
    "critical": 0.1,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer_material_type(sample: Sample) -> str | None:
    """Infer a DEGRADATION_FACTORS key from sample/material data."""
    pollutant = (sample.pollutant_type or "").lower()
    state = (sample.material_state or "").lower()
    category = (sample.material_category or "").lower()

    if pollutant == "asbestos":
        if "friable" in state or "friable" in category:
            return "asbestos_friable"
        return "asbestos_bonded"
    if pollutant == "pcb":
        return "pcb_joint"
    if pollutant == "lead":
        return "lead_paint"
    return None


def _compute_climate_stress_factor(
    material_type: str,
    climate_stress: dict[str, float],
) -> float:
    """Compute weighted climate stress factor for a material type (0-1)."""
    factors = DEGRADATION_FACTORS.get(material_type, {})
    if not factors:
        return 0.0
    total = 0.0
    for stress_type, sensitivity in factors.items():
        exposure = climate_stress.get(stress_type, 0.0)
        total += sensitivity * exposure
    # Normalize by number of stress types
    return round(min(1.0, total / max(len(factors), 1)), 3)


def _project_condition(age_years: int, base_lifespan: int, stress_factor: float) -> str:
    """Project current condition based on age, lifespan, and stress acceleration."""
    # Stress accelerates aging: effective_age = age * (1 + stress_factor)
    effective_age = age_years * (1 + stress_factor)
    ratio = effective_age / base_lifespan if base_lifespan > 0 else 1.0

    if ratio < 0.3:
        return "good"
    if ratio < 0.5:
        return "fair"
    if ratio < 0.75:
        return "poor"
    return "critical"


def _years_to_critical(
    age_years: int,
    base_lifespan: int,
    stress_factor: float,
) -> int:
    """Estimate years until material reaches critical condition (ratio >= 0.75)."""
    if base_lifespan <= 0:
        return 0
    acceleration = 1 + stress_factor
    if acceleration <= 0:
        return 999
    # critical when effective_age / lifespan >= 0.75
    # effective_age = (age + years_left) * acceleration
    # (age + years_left) * acceleration / lifespan = 0.75
    critical_age = (0.75 * base_lifespan) / acceleration
    years_left = max(0, int(critical_age - age_years))
    return years_left


def _recommendation(material_type: str, projected: str, years_to_crit: int) -> str:
    """Generate a French recommendation based on material state."""
    labels = {
        "asbestos_friable": "amiante friable",
        "asbestos_bonded": "amiante lié",
        "pcb_joint": "joints PCB",
        "lead_paint": "peinture au plomb",
        "concrete": "béton",
    }
    label = labels.get(material_type, material_type)

    if projected == "critical":
        return f"Intervention urgente requise pour {label} — état critique"
    if projected == "poor":
        return f"Planifier intervention pour {label} dans les {years_to_crit} prochaines années"
    if projected == "fair":
        return f"Surveiller {label} — inspection recommandée dans {min(years_to_crit, 5)} ans"
    return f"État satisfaisant pour {label} — surveillance courante"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def predict_degradation(
    db: AsyncSession,
    building_id: UUID,
    climate_stress: dict[str, float] | None = None,
) -> list[dict]:
    """Predict material degradation for each material found in a building.

    For each material, computes degradation acceleration based on:
    - Climate stress (from climate_stress param or defaults)
    - Material age (from building construction_year)
    - Material type (inferred from sample/diagnostic data)

    Returns list of dicts with: material, age, climate_stress_factor,
    projected_condition, years_to_critical, recommendation.
    """
    # Fetch building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    climate = climate_stress or _DEFAULT_CLIMATE_STRESS
    current_year = datetime.now(UTC).year
    building_age = current_year - (building.construction_year or current_year)

    # Fetch samples via diagnostics
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    samples: list[Sample] = []
    if diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    # Also fetch building elements for concrete assessment
    zone_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = list(zone_result.scalars().all())

    elements: list[BuildingElement] = []
    if zones:
        zone_ids = [z.id for z in zones]
        el_result = await db.execute(select(BuildingElement).where(BuildingElement.zone_id.in_(zone_ids)))
        elements = list(el_result.scalars().all())

    predictions: list[dict] = []
    seen_types: set[str] = set()

    # Process samples (pollutant-bearing materials)
    for sample in samples:
        if not sample.threshold_exceeded:
            continue
        mat_type = _infer_material_type(sample)
        if mat_type is None or mat_type in seen_types:
            continue
        seen_types.add(mat_type)

        stress = _compute_climate_stress_factor(mat_type, climate)
        lifespan = _BASE_LIFESPAN.get(mat_type, 40)
        projected = _project_condition(building_age, lifespan, stress)
        ytc = _years_to_critical(building_age, lifespan, stress)

        predictions.append(
            {
                "material": mat_type,
                "age_years": building_age,
                "climate_stress_factor": stress,
                "projected_condition": projected,
                "years_to_critical": ytc,
                "recommendation": _recommendation(mat_type, projected, ytc),
            }
        )

    # Add concrete assessment if building has structural elements
    if "concrete" not in seen_types and elements:
        concrete_elements = [
            e for e in elements if (e.element_type or "").lower() in ("wall", "structural", "floor", "ceiling")
        ]
        if concrete_elements:
            seen_types.add("concrete")
            stress = _compute_climate_stress_factor("concrete", climate)
            lifespan = _BASE_LIFESPAN["concrete"]
            projected = _project_condition(building_age, lifespan, stress)
            ytc = _years_to_critical(building_age, lifespan, stress)
            predictions.append(
                {
                    "material": "concrete",
                    "age_years": building_age,
                    "climate_stress_factor": stress,
                    "projected_condition": projected,
                    "years_to_critical": ytc,
                    "recommendation": _recommendation("concrete", projected, ytc),
                }
            )

    # Sort by urgency: years_to_critical ascending
    predictions.sort(key=lambda p: p["years_to_critical"])
    return predictions
