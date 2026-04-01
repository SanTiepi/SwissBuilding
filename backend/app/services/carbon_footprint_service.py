"""
SwissBuildingOS - Carbon Footprint Service

Estimates annual CO2 emissions for a building based on energy source
and estimated consumption. Uses Swiss emission factors and provides
an A-G carbon rating with comparison to national average.

Swiss emission factors (simplified):
- mazout (heating oil): 2.65 kg CO2/litre
- gaz (natural gas): 2.0 kg CO2/m3
- electricite (Swiss mix): 0.128 kg CO2/kWh
- bois (wood): 0.03 kg CO2/kWh
- pac (heat pump with Swiss electricity): 0.04 kg CO2/kWh
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

# Emission factors (kg CO2 per unit)
EMISSION_FACTORS: dict[str, float] = {
    "mazout": 2.65,  # kg CO2 per litre
    "gaz": 2.0,  # kg CO2 per m3
    "electricite": 0.128,  # kg CO2 per kWh (Swiss mix)
    "bois": 0.03,  # kg CO2 per kWh
    "pac": 0.04,  # kg CO2 per kWh (heat pump with Swiss elec)
}

# Energy content factors (kWh per unit) for conversion
ENERGY_CONTENT: dict[str, float] = {
    "mazout": 10.0,  # kWh per litre
    "gaz": 10.6,  # kWh per m3
    "electricite": 1.0,  # kWh per kWh
    "bois": 1.0,  # kWh per kWh
    "pac": 1.0,  # kWh per kWh (COP already factored)
}

# Default energy source assumptions based on construction year
# (simplified: older buildings tend to use fossil fuels)
DEFAULT_SOURCE_BY_ERA: dict[str, str] = {
    "pre_1970": "mazout",
    "1970_1999": "mazout",
    "2000_2019": "gaz",
    "post_2020": "pac",
}

# Average Swiss building CO2: ~25 kg CO2/m2/year (residential)
SWISS_AVERAGE_CO2_PER_M2 = 25.0

# Carbon rating thresholds (kg CO2/m2/year)
CARBON_RATING_THRESHOLDS: dict[str, float] = {
    "A": 5.0,
    "B": 10.0,
    "C": 15.0,
    "D": 25.0,
    "E": 35.0,
    "F": 50.0,
    "G": float("inf"),
}

# Base consumption kWh/m2/year by construction era
BASE_CONSUMPTION_KWH_M2: dict[str, float] = {
    "pre_1970": 220.0,
    "1970_1999": 160.0,
    "2000_2019": 90.0,
    "post_2020": 45.0,
}

DEFAULT_SURFACE_M2 = 200.0

# Intervention improvements: reduction factor for carbon footprint
INTERVENTION_CARBON_REDUCTION: dict[str, float] = {
    "insulation_upgrade": 0.20,
    "window_replacement": 0.10,
    "hvac_upgrade": 0.30,
    "full_renovation": 0.50,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _era_key(construction_year: int | None) -> str:
    """Map construction year to era key."""
    if construction_year is None:
        return "pre_1970"
    if construction_year >= 2020:
        return "post_2020"
    if construction_year >= 2000:
        return "2000_2019"
    if construction_year >= 1970:
        return "1970_1999"
    return "pre_1970"


def _carbon_rating(co2_per_m2: float) -> str:
    """Determine A-G carbon rating from kg CO2/m2/year."""
    for grade, threshold in CARBON_RATING_THRESHOLDS.items():
        if co2_per_m2 <= threshold:
            return grade
    return "G"


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


async def compute_carbon_footprint(db: AsyncSession, building_id: UUID) -> dict:
    """Estimate annual CO2 emissions based on energy source and consumption.

    Uses construction year to infer energy source and base consumption,
    then applies reductions from completed interventions.

    Return: {
        building_id, total_kg_co2, per_m2, rating,
        energy_source, consumption_kwh_m2,
        breakdown_by_source: {source: kg_co2},
        comparison_to_average: {avg_kg_m2, delta_pct, better_than_average},
        interventions_applied: [str],
        computed_at
    }
    """
    building = await _get_building(db, building_id)
    intervention_types = await _get_completed_intervention_types(db, building_id)
    surface = _surface_area(building)
    era = _era_key(building.construction_year)

    # Base energy consumption
    base_kwh_m2 = BASE_CONSUMPTION_KWH_M2[era]

    # Apply intervention reductions multiplicatively
    effective_kwh_m2 = base_kwh_m2
    for itype in intervention_types:
        reduction = INTERVENTION_CARBON_REDUCTION.get(itype, 0.0)
        effective_kwh_m2 *= 1 - reduction
    effective_kwh_m2 = round(effective_kwh_m2, 1)

    # Determine energy source
    energy_source = DEFAULT_SOURCE_BY_ERA[era]
    # Check if HVAC upgrade implies heat pump switch
    if "hvac_upgrade" in intervention_types or "full_renovation" in intervention_types:
        energy_source = "pac"

    # Calculate CO2
    emission_factor = EMISSION_FACTORS[energy_source]
    energy_content = ENERGY_CONTENT[energy_source]

    # Convert kWh/m2 to fuel units, then to CO2
    fuel_units_per_m2 = effective_kwh_m2 / energy_content
    co2_per_m2 = round(fuel_units_per_m2 * emission_factor, 2)
    total_co2 = round(co2_per_m2 * surface, 2)

    # Rating
    rating = _carbon_rating(co2_per_m2)

    # Breakdown (single source for now; could be extended for mixed sources)
    breakdown = {energy_source: round(total_co2, 2)}

    # Comparison to average
    delta_pct = round(((co2_per_m2 - SWISS_AVERAGE_CO2_PER_M2) / SWISS_AVERAGE_CO2_PER_M2) * 100, 1)

    return {
        "building_id": str(building_id),
        "total_kg_co2": total_co2,
        "per_m2": co2_per_m2,
        "rating": rating,
        "energy_source": energy_source,
        "consumption_kwh_m2": effective_kwh_m2,
        "breakdown_by_source": breakdown,
        "comparison_to_average": {
            "avg_kg_m2": SWISS_AVERAGE_CO2_PER_M2,
            "delta_pct": delta_pct,
            "better_than_average": co2_per_m2 < SWISS_AVERAGE_CO2_PER_M2,
        },
        "interventions_applied": intervention_types,
        "computed_at": datetime.now(UTC).isoformat(),
    }
