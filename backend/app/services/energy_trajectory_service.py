"""
SwissBuildingOS - Energy Trajectory Service

Energy performance trajectory based on Swiss Energy Strategy 2050,
renovation impact simulation with measure-specific reduction factors,
and multi-horizon target gap analysis.

Extends the existing energy_performance_service (construction-year-only
estimates) with forward-looking trajectories and renovation economics.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.intervention import Intervention

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENERGY_CLASSES = ["A", "B", "C", "D", "E", "F", "G"]

KWH_PER_CLASS: dict[str, float] = {
    "A": 35.0,
    "B": 60.0,
    "C": 90.0,
    "D": 130.0,
    "E": 180.0,
    "F": 250.0,
    "G": 350.0,
}

# Swiss Energy Strategy 2050 trajectory targets (kWh/m2/year)
SWISS_TARGETS: list[dict] = [
    {"year": 2030, "target_kwh": 90.0},  # Class C ceiling
    {"year": 2040, "target_kwh": 60.0},  # Class B ceiling
    {"year": 2050, "target_kwh": 35.0},  # Class A ceiling
]

# Renovation measure impact factors
RENOVATION_IMPACT: dict[str, dict] = {
    "facade_insulation": {"energy_reduction": 0.25, "cost_per_m2": 250, "lifespan": 40},
    "roof_insulation": {"energy_reduction": 0.15, "cost_per_m2": 180, "lifespan": 35},
    "window_replacement": {"energy_reduction": 0.12, "cost_per_m2": 800, "lifespan": 30},
    "heat_pump": {"energy_reduction": 0.40, "cost_forfait": 25000, "lifespan": 20},
    "solar_panels": {"energy_reduction": 0.20, "cost_per_m2": 350, "lifespan": 25},
}

# CO2 and cost factors
CO2_FACTOR = 0.15  # kg CO2 per kWh (Swiss average heating mix)
CHF_PER_KWH = 0.12  # CHF per kWh (Swiss average energy price)
DEFAULT_SURFACE_M2 = 200.0

# Intervention type to energy improvement (class steps, reused from energy_performance_service)
INTERVENTION_IMPROVEMENTS: dict[str, float] = {
    "insulation_upgrade": 1.0,
    "window_replacement": 0.5,
    "hvac_upgrade": 1.0,
    "full_renovation": 2.0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_class_index(construction_year: int | None) -> int:
    """Return index (0=A .. 6=G) for the base energy class from construction year."""
    if construction_year is None:
        return 6  # G
    if construction_year >= 2020:
        return 1  # B
    if construction_year >= 2010:
        return 2  # C
    if construction_year >= 2000:
        return 3  # D
    if construction_year >= 1985:
        return 4  # E
    if construction_year >= 1970:
        return 5  # F
    return 6  # G


def _apply_improvements(base_index: int, intervention_types: list[str]) -> int:
    """Apply intervention improvements and return improved class index (capped at 0=A)."""
    total = 0.0
    for itype in intervention_types:
        total += INTERVENTION_IMPROVEMENTS.get(itype, 0.0)
    return max(0, int(base_index - total))


def _class_from_index(index: int) -> str:
    return ENERGY_CLASSES[min(index, 6)]


def _surface_area(building: Building) -> float:
    return building.surface_area_m2 if building.surface_area_m2 else DEFAULT_SURFACE_M2


async def _get_building(db: AsyncSession, building_id: UUID) -> Building:
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _get_completed_intervention_types(db: AsyncSession, building_id: UUID) -> list[str]:
    stmt = select(Intervention.intervention_type).where(
        Intervention.building_id == building_id,
        Intervention.status == "completed",
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def compute_energy_trajectory(db: AsyncSession, building_id: UUID) -> dict:
    """Current energy class + target 2030/2040/2050 based on Swiss energy strategy.

    Return: {
        building_id, current_kwh_m2, current_class, surface_m2,
        targets: [{year, target_kwh, gap_kwh, gap_pct, on_track}],
        computed_at
    }
    """
    building = await _get_building(db, building_id)
    intervention_types = await _get_completed_intervention_types(db, building_id)

    base_idx = _base_class_index(building.construction_year)
    improved_idx = _apply_improvements(base_idx, intervention_types)
    energy_class = _class_from_index(improved_idx)
    current_kwh = KWH_PER_CLASS[energy_class]
    surface = _surface_area(building)

    targets = []
    for target in SWISS_TARGETS:
        gap_kwh = max(current_kwh - target["target_kwh"], 0.0)
        gap_pct = round((gap_kwh / current_kwh * 100) if current_kwh > 0 else 0.0, 1)
        on_track = current_kwh <= target["target_kwh"]
        targets.append(
            {
                "year": target["year"],
                "target_kwh": target["target_kwh"],
                "gap_kwh": round(gap_kwh, 1),
                "gap_pct": gap_pct,
                "on_track": on_track,
            }
        )

    return {
        "building_id": str(building_id),
        "current_kwh_m2": current_kwh,
        "current_class": energy_class,
        "surface_m2": surface,
        "targets": targets,
        "computed_at": datetime.now(UTC).isoformat(),
    }


async def simulate_renovation_impact(
    db: AsyncSession,
    building_id: UUID,
    measures: list[str],
) -> dict:
    """Simulate energy savings from renovation measures.

    Measures: facade_insulation, roof_insulation, window_replacement, heat_pump, solar_panels.
    Each has a percentage reduction factor applied multiplicatively.

    Return: {
        building_id, current_kwh_m2, current_class,
        projected_kwh_m2, projected_class,
        savings_kwh, savings_chf_per_year, co2_reduction_kg,
        renovation_cost, measures_detail: [{measure, energy_reduction_pct, cost, lifespan}],
        computed_at
    }
    """
    building = await _get_building(db, building_id)
    intervention_types = await _get_completed_intervention_types(db, building_id)

    base_idx = _base_class_index(building.construction_year)
    improved_idx = _apply_improvements(base_idx, intervention_types)
    current_class = _class_from_index(improved_idx)
    current_kwh = KWH_PER_CLASS[current_class]
    surface = _surface_area(building)

    # Validate measures
    valid_measures = [m for m in measures if m in RENOVATION_IMPACT]
    if not valid_measures:
        return {
            "building_id": str(building_id),
            "current_kwh_m2": current_kwh,
            "current_class": current_class,
            "projected_kwh_m2": current_kwh,
            "projected_class": current_class,
            "savings_kwh": 0.0,
            "savings_chf_per_year": 0.0,
            "co2_reduction_kg": 0.0,
            "renovation_cost": 0.0,
            "measures_detail": [],
            "computed_at": datetime.now(UTC).isoformat(),
        }

    # Apply reductions multiplicatively: each measure reduces remaining consumption
    projected_kwh = current_kwh
    total_cost = 0.0
    measures_detail = []

    for measure in valid_measures:
        impact = RENOVATION_IMPACT[measure]
        reduction = impact["energy_reduction"]
        projected_kwh *= 1 - reduction

        # Cost: either per m2 or forfait
        if "cost_forfait" in impact:
            cost = float(impact["cost_forfait"])
        else:
            cost = float(impact["cost_per_m2"]) * surface
        total_cost += cost

        measures_detail.append(
            {
                "measure": measure,
                "energy_reduction_pct": round(reduction * 100, 1),
                "cost": round(cost, 2),
                "lifespan": impact["lifespan"],
            }
        )

    projected_kwh = round(projected_kwh, 1)

    # Determine projected class
    projected_class = "A"
    for cls in ENERGY_CLASSES:
        if projected_kwh <= KWH_PER_CLASS[cls]:
            projected_class = cls
            break
    else:
        projected_class = "G"

    savings_kwh = round((current_kwh - projected_kwh) * surface, 1)
    savings_chf = round(savings_kwh * CHF_PER_KWH, 2)
    co2_reduction = round(savings_kwh * CO2_FACTOR, 2)

    return {
        "building_id": str(building_id),
        "current_kwh_m2": current_kwh,
        "current_class": current_class,
        "projected_kwh_m2": projected_kwh,
        "projected_class": projected_class,
        "savings_kwh": savings_kwh,
        "savings_chf_per_year": savings_chf,
        "co2_reduction_kg": co2_reduction,
        "renovation_cost": round(total_cost, 2),
        "measures_detail": measures_detail,
        "computed_at": datetime.now(UTC).isoformat(),
    }
