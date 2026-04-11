"""
SwissBuildingOS - Energy Performance Service

Estimates building energy performance class (CECB-inspired A-G),
carbon footprint, and renovation impact based on construction
characteristics and completed interventions.

Swiss energy class logic (simplified):
- Base class derived from construction_year
- Improvements from completed interventions
- Cap at A (best)
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.intervention import Intervention
from app.schemas.energy_performance import (
    BuildingEnergyComparison,
    EnergyPerformanceEstimate,
    PortfolioEnergyProfile,
    RenovationEnergyImpact,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENERGY_CLASSES = ["A", "B", "C", "D", "E", "F", "G"]

# kWh/m²/year for each class
KWH_PER_CLASS: dict[str, float] = {
    "A": 35.0,
    "B": 60.0,
    "C": 90.0,
    "D": 130.0,
    "E": 180.0,
    "F": 250.0,
    "G": 350.0,
}

# CO2 factor: kg CO2 per kWh (Swiss average heating mix)
CO2_FACTOR = 0.15

# CHF per kWh for annual savings
CHF_PER_KWH = 0.12

# Default surface area when not specified
DEFAULT_SURFACE_M2 = 200.0

# Intervention improvement values (in class steps, higher = more improvement)
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
    """Return the index (0=A .. 6=G) for the base energy class from construction year."""
    if construction_year is None:
        return 6  # G (worst) if unknown
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
    return 6  # G (pre-1970)


def _apply_improvements(base_index: int, intervention_types: list[str]) -> int:
    """Apply intervention improvements and return the improved class index (capped at 0=A).

    Uses floor so that e.g. 0.5-class improvements always count toward a
    better class once accumulated (4.5 steps → 4 full steps of improvement,
    index 6 → 2 = class C; but two window replacements = 1.0 → 1 step).
    """
    total_improvement = 0.0
    for itype in intervention_types:
        total_improvement += INTERVENTION_IMPROVEMENTS.get(itype, 0.0)
    improved_index = int(base_index - total_improvement)
    return max(0, improved_index)  # Cap at A


def _class_from_index(index: int) -> str:
    """Convert index (0-6) to energy class letter."""
    return ENERGY_CLASSES[min(index, 6)]


def _surface_area(building: Building) -> float:
    """Return the building surface area, defaulting to 200 m² if not set."""
    return building.surface_area_m2 if building.surface_area_m2 else DEFAULT_SURFACE_M2


async def _get_building(db: AsyncSession, building_id: UUID) -> Building:
    """Fetch a building by ID or raise ValueError."""
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _get_completed_intervention_types(db: AsyncSession, building_id: UUID) -> list[str]:
    """Fetch all completed intervention types for a building."""
    stmt = select(Intervention.intervention_type).where(
        Intervention.building_id == building_id,
        Intervention.status == "completed",
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def estimate_energy_class(
    db: AsyncSession,
    building_id: UUID,
) -> EnergyPerformanceEstimate:
    """Return energy class — real CECB if available, else estimated from construction year."""
    building = await _get_building(db, building_id)
    intervention_types = await _get_completed_intervention_types(db, building_id)

    # Prefer real CECB data when available
    if building.cecb_class:
        energy_class = building.cecb_class
        kwh = building.cecb_heating_demand or KWH_PER_CLASS.get(energy_class, 130.0)
        source = "cecb"
        factors = [f"source=CECB ({building.cecb_source or 'registre'})"]
        if building.cecb_certificate_date:
            factors.append(f"certificate_date={building.cecb_certificate_date.date()}")
    else:
        base_idx = _base_class_index(building.construction_year)
        improved_idx = _apply_improvements(base_idx, intervention_types)
        energy_class = _class_from_index(improved_idx)
        kwh = KWH_PER_CLASS[energy_class]
        source = "estimated"
        factors = [f"construction_year={building.construction_year or 'unknown'}"]
        for itype in intervention_types:
            if itype in INTERVENTION_IMPROVEMENTS:
                factors.append(f"intervention:{itype}")

    surface = _surface_area(building)
    co2_per_m2 = kwh * CO2_FACTOR
    total_co2 = co2_per_m2 * surface

    # Improvement potential: best possible class if all interventions were done
    base_idx = _base_class_index(building.construction_year)
    all_types = list(INTERVENTION_IMPROVEMENTS.keys())
    best_idx = _apply_improvements(base_idx, all_types)
    best_class = _class_from_index(best_idx)
    improvement_potential = best_class if best_class != energy_class else None

    return EnergyPerformanceEstimate(
        building_id=building.id,
        energy_class=energy_class,
        kwh_per_m2_year=kwh,
        co2_kg_per_m2_year=co2_per_m2,
        total_co2_kg_year=total_co2,
        improvement_potential_class=improvement_potential,
        minergie_compatible=energy_class in ("A", "B"),
        factors=factors,
        source=source,
        cecb_heating_demand=building.cecb_heating_demand,
        cecb_cooling_demand=building.cecb_cooling_demand,
        cecb_dhw_demand=building.cecb_dhw_demand,
        estimated_at=datetime.now(UTC),
    )


async def estimate_renovation_impact(
    db: AsyncSession,
    building_id: UUID,
    planned_interventions: list[str],
) -> RenovationEnergyImpact:
    """Project energy improvement from planned interventions."""
    building = await _get_building(db, building_id)
    existing_types = await _get_completed_intervention_types(db, building_id)

    base_idx = _base_class_index(building.construction_year)
    current_idx = _apply_improvements(base_idx, existing_types)
    current_class = _class_from_index(current_idx)
    current_kwh = KWH_PER_CLASS[current_class]

    # Project with existing + planned interventions
    combined = existing_types + planned_interventions
    projected_idx = _apply_improvements(base_idx, combined)
    projected_class = _class_from_index(projected_idx)
    projected_kwh = KWH_PER_CLASS[projected_class]

    surface = _surface_area(building)
    energy_savings_pct = ((current_kwh - projected_kwh) / current_kwh * 100) if current_kwh > 0 else 0.0
    co2_reduction = (current_kwh - projected_kwh) * CO2_FACTOR * surface
    annual_savings = (current_kwh - projected_kwh) * CHF_PER_KWH * surface

    return RenovationEnergyImpact(
        building_id=building.id,
        current_class=current_class,
        projected_class=projected_class,
        energy_savings_percent=round(energy_savings_pct, 1),
        co2_reduction_kg=round(co2_reduction, 2),
        annual_savings_chf=round(annual_savings, 2),
        planned_interventions=planned_interventions,
    )


async def get_portfolio_energy_profile(
    db: AsyncSession,
    org_id: UUID | None = None,
) -> PortfolioEnergyProfile:
    """Aggregate energy profile across all buildings (optionally filtered by org)."""
    stmt = select(Building)
    # org_id filtering would require an org→building relationship; for now we
    # include all buildings if org_id is None. A real implementation would add
    # a join to an organization_buildings table here.
    result = await db.execute(stmt)
    buildings = list(result.scalars().all())

    if not buildings:
        return PortfolioEnergyProfile(
            total_buildings=0,
            class_distribution={c: 0 for c in ENERGY_CLASSES},
            total_co2_tonnes_year=0.0,
            avg_kwh_per_m2=0.0,
            worst_performers=[],
            improvement_potential_summary="No buildings in portfolio.",
        )

    distribution: dict[str, int] = {c: 0 for c in ENERGY_CLASSES}
    total_co2 = 0.0
    total_kwh_weighted = 0.0
    total_surface = 0.0
    building_estimates: list[tuple[Building, str, float, float]] = []

    for bld in buildings:
        intervention_types = await _get_completed_intervention_types(db, bld.id)
        base_idx = _base_class_index(bld.construction_year)
        improved_idx = _apply_improvements(base_idx, intervention_types)
        energy_class = _class_from_index(improved_idx)
        kwh = KWH_PER_CLASS[energy_class]
        surface = _surface_area(bld)
        co2 = kwh * CO2_FACTOR * surface

        distribution[energy_class] += 1
        total_co2 += co2
        total_kwh_weighted += kwh * surface
        total_surface += surface
        building_estimates.append((bld, energy_class, kwh, co2))

    avg_kwh = total_kwh_weighted / total_surface if total_surface > 0 else 0.0

    # Worst performers: buildings with class F or G
    worst = sorted(
        [(bld, ec, kwh_val, co2_val) for bld, ec, kwh_val, co2_val in building_estimates if ec in ("F", "G")],
        key=lambda x: x[2],
        reverse=True,
    )[:5]
    worst_performers = [
        {
            "building_id": str(bld.id),
            "address": bld.address,
            "energy_class": ec,
            "kwh_per_m2_year": kwh_val,
        }
        for bld, ec, kwh_val, _co2 in worst
    ]

    # Improvement summary
    improvable = sum(1 for _, ec, _, _ in building_estimates if ec in ("D", "E", "F", "G"))
    summary = f"{improvable} of {len(buildings)} buildings have significant improvement potential (class D-G)."

    return PortfolioEnergyProfile(
        total_buildings=len(buildings),
        class_distribution=distribution,
        total_co2_tonnes_year=round(total_co2 / 1000, 2),
        avg_kwh_per_m2=round(avg_kwh, 1),
        worst_performers=worst_performers,
        improvement_potential_summary=summary,
    )


async def compare_buildings_energy(
    db: AsyncSession,
    building_ids: list[UUID],
) -> list[BuildingEnergyComparison]:
    """Compare energy performance of up to 10 buildings, ranked by efficiency."""
    if len(building_ids) > 10:
        raise ValueError("Cannot compare more than 10 buildings at once")

    entries: list[tuple[UUID, str, str, float, float]] = []
    for bid in building_ids:
        building = await _get_building(db, bid)
        intervention_types = await _get_completed_intervention_types(db, bid)
        base_idx = _base_class_index(building.construction_year)
        improved_idx = _apply_improvements(base_idx, intervention_types)
        energy_class = _class_from_index(improved_idx)
        kwh = KWH_PER_CLASS[energy_class]
        co2 = kwh * CO2_FACTOR
        entries.append((building.id, building.address, energy_class, kwh, co2))

    # Sort by kwh (lower is better = rank 1)
    entries.sort(key=lambda x: x[3])

    return [
        BuildingEnergyComparison(
            building_id=bid,
            address=addr,
            energy_class=ec,
            kwh_per_m2_year=kwh,
            co2_kg_per_m2_year=co2,
            rank=i + 1,
        )
        for i, (bid, addr, ec, kwh, co2) in enumerate(entries)
    ]
