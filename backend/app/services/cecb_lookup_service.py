"""
CECB Lookup Service — unified energy certificate lookup for a building.

Combines real CECB data (from cecb_import_service) with estimation fallback
(from energy_performance_service) into a single EnergyCertificateRead response.

This is the service behind GET /buildings/{id}/energy-certificate.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.schemas.energy_performance import EnergyCertificateRead
from app.services.energy_performance_service import (
    CO2_FACTOR,
    KWH_PER_CLASS,
    _apply_improvements,
    _base_class_index,
    _class_from_index,
    _get_completed_intervention_types,
)

# ---------------------------------------------------------------------------
# Estimation from construction year (when no CECB exists)
# ---------------------------------------------------------------------------

ESTIMATION_TABLE: list[tuple[int, str, float]] = [
    # (year_threshold, energy_class, consumption_kwh_m2)
    (2020, "B", 60.0),
    (2010, "C", 90.0),
    (2000, "D", 130.0),
    (1985, "E", 180.0),
    (1970, "F", 250.0),
    (0, "G", 350.0),
]


def _estimate_from_construction(
    construction_year: int | None,
    intervention_types: list[str],
) -> tuple[str, float]:
    """Return (energy_class, kwh_m2) estimated from construction year + interventions."""
    base_idx = _base_class_index(construction_year)
    improved_idx = _apply_improvements(base_idx, intervention_types)
    energy_class = _class_from_index(improved_idx)
    kwh = KWH_PER_CLASS[energy_class]
    return energy_class, kwh


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_building_energy_certificate(
    db: AsyncSession,
    building_id: UUID,
) -> EnergyCertificateRead:
    """Return energy certificate — real CECB if stored, else estimated.

    Does NOT trigger a live fetch from geo.admin.ch (use POST /cecb-refresh for that).
    """
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    now = datetime.now(UTC)

    if building.cecb_class:
        # Real CECB data
        kwh = building.cecb_heating_demand or KWH_PER_CLASS.get(building.cecb_class, 130.0)
        co2 = kwh * CO2_FACTOR
        return EnergyCertificateRead(
            building_id=building.id,
            energy_class=building.cecb_class,
            energy_consumption_kwh_m2=kwh,
            energy_emissions_co2_m2=co2,
            heating_demand=building.cecb_heating_demand,
            cooling_demand=building.cecb_cooling_demand,
            dhw_demand=building.cecb_dhw_demand,
            certificate_date=building.cecb_certificate_date,
            source="cecb_official",
            estimated_at=now,
        )

    # Fallback: estimate from construction year + completed interventions
    intervention_types = await _get_completed_intervention_types(db, building_id)
    energy_class, kwh = _estimate_from_construction(building.construction_year, intervention_types)
    co2 = kwh * CO2_FACTOR

    return EnergyCertificateRead(
        building_id=building.id,
        energy_class=energy_class,
        energy_consumption_kwh_m2=kwh,
        energy_emissions_co2_m2=co2,
        heating_demand=None,
        cooling_demand=None,
        dhw_demand=None,
        certificate_date=None,
        source="estimated",
        estimated_at=now,
    )
