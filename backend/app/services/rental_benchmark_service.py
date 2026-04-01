"""Rental benchmark service — Programme R.

Benchmarks building rental potential against commune-level reference data.
Uses Swiss rental market averages (CHF/m2/month) by commune and unit type.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.lease import Lease
from app.models.unit import Unit

# ---------------------------------------------------------------------------
# Rental benchmarks: CHF/m2/month by commune and room count
# ---------------------------------------------------------------------------

RENTAL_BENCHMARKS: dict[str, dict[str, int]] = {
    "Lausanne": {"1_room": 28, "2_rooms": 22, "3_rooms": 19, "4_rooms": 17, "5_rooms": 15},
    "Genève": {"1_room": 35, "2_rooms": 28, "3_rooms": 24, "4_rooms": 21, "5_rooms": 19},
    "Zürich": {"1_room": 32, "2_rooms": 26, "3_rooms": 22, "4_rooms": 20, "5_rooms": 18},
    "Bern": {"1_room": 24, "2_rooms": 19, "3_rooms": 16, "4_rooms": 14, "5_rooms": 13},
    "Pully": {"1_room": 30, "2_rooms": 24, "3_rooms": 20, "4_rooms": 18, "5_rooms": 16},
    "Renens": {"1_room": 26, "2_rooms": 21, "3_rooms": 18, "4_rooms": 16, "5_rooms": 14},
    "Morges": {"1_room": 27, "2_rooms": 22, "3_rooms": 19, "4_rooms": 17, "5_rooms": 15},
    "Nyon": {"1_room": 29, "2_rooms": 23, "3_rooms": 20, "4_rooms": 18, "5_rooms": 16},
    "Sion": {"1_room": 20, "2_rooms": 16, "3_rooms": 14, "4_rooms": 12, "5_rooms": 11},
    "Fribourg": {"1_room": 22, "2_rooms": 18, "3_rooms": 15, "4_rooms": 13, "5_rooms": 12},
    "Neuchâtel": {"1_room": 21, "2_rooms": 17, "3_rooms": 14, "4_rooms": 13, "5_rooms": 11},
    "Basel": {"1_room": 28, "2_rooms": 22, "3_rooms": 19, "4_rooms": 17, "5_rooms": 15},
    "_default": {"1_room": 22, "2_rooms": 18, "3_rooms": 15, "4_rooms": 13, "5_rooms": 12},
}

# Canton average gross yields (%)
_CANTON_AVG_YIELD: dict[str, float] = {
    "VD": 3.2,
    "GE": 2.8,
    "ZH": 2.9,
    "BE": 3.8,
    "VS": 4.0,
    "FR": 3.5,
    "BS": 3.1,
    "NE": 3.6,
}
_DEFAULT_YIELD = 3.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _fetch_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


def _rooms_to_key(rooms: float | None) -> str:
    """Map room count to benchmark key."""
    if rooms is None or rooms <= 1:
        return "1_room"
    if rooms <= 2:
        return "2_rooms"
    if rooms <= 3:
        return "3_rooms"
    if rooms <= 4:
        return "4_rooms"
    return "5_rooms"


def _get_commune_benchmarks(city: str) -> dict[str, int]:
    """Lookup benchmarks for a commune, with fallback to _default."""
    if not city:
        return RENTAL_BENCHMARKS["_default"]
    # Try exact match, then title-case
    for key in RENTAL_BENCHMARKS:
        if key.lower() == city.lower():
            return RENTAL_BENCHMARKS[key]
    return RENTAL_BENCHMARKS["_default"]


def _compute_benchmark_rent(rooms: float | None, surface_m2: float, city: str) -> float:
    """Compute monthly benchmark rent (CHF) for a unit."""
    benchmarks = _get_commune_benchmarks(city)
    room_key = _rooms_to_key(rooms)
    rate = benchmarks.get(room_key, benchmarks.get("3_rooms", 15))
    return surface_m2 * rate


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def benchmark_rental(db: AsyncSession, building_id: UUID) -> dict[str, Any]:
    """Compare building's rental potential against commune benchmarks.

    Returns per-unit analysis with benchmark delta and optimization potential.
    """
    building = await _fetch_building(db, building_id)
    city = building.city or ""
    canton = (building.canton or "").upper()

    # Fetch units
    stmt = select(Unit).where(Unit.building_id == building_id, Unit.status == "active")
    result = await db.execute(stmt)
    units = list(result.scalars().all())

    # Fetch active leases for this building
    lease_stmt = select(Lease).where(Lease.building_id == building_id, Lease.status == "active")
    lease_result = await db.execute(lease_stmt)
    leases = list(lease_result.scalars().all())
    lease_by_unit: dict[str, Lease] = {}
    for lease in leases:
        if lease.unit_id:
            lease_by_unit[str(lease.unit_id)] = lease

    unit_analyses: list[dict[str, Any]] = []
    total_current_rent = 0.0
    total_benchmark_rent = 0.0

    if units:
        for unit in units:
            surface = unit.surface_m2 or 50.0  # default 50m2 if unknown
            rooms = unit.rooms
            room_key = _rooms_to_key(rooms)
            benchmark_rate = _get_commune_benchmarks(city).get(room_key, 15)
            benchmark_monthly = surface * benchmark_rate

            # Current rent from lease if available
            lease = lease_by_unit.get(str(unit.id))
            current_rent = lease.rent_monthly_chf if lease and lease.rent_monthly_chf else None

            if current_rent and benchmark_monthly > 0:
                delta_pct = round((current_rent - benchmark_monthly) / benchmark_monthly * 100, 1)
            else:
                delta_pct = 0.0

            if current_rent:
                total_current_rent += current_rent
            total_benchmark_rent += benchmark_monthly

            if delta_pct > 5:
                verdict = "above_market"
            elif delta_pct < -5:
                verdict = "below_market"
            else:
                verdict = "at_market"

            unit_analyses.append(
                {
                    "unit_id": str(unit.id),
                    "unit_type": unit.unit_type,
                    "rooms": rooms,
                    "surface_m2": surface,
                    "current_rent_estimate": current_rent or benchmark_monthly,
                    "benchmark_monthly": round(benchmark_monthly),
                    "benchmark_rate_m2": benchmark_rate,
                    "delta_pct": delta_pct,
                    "verdict": verdict,
                }
            )
    else:
        # No units — estimate from building surface
        surface = building.surface_area_m2 or 200.0
        benchmark_rate = _get_commune_benchmarks(city).get("3_rooms", 15)
        benchmark_monthly = surface * benchmark_rate
        total_benchmark_rent = benchmark_monthly

        unit_analyses.append(
            {
                "unit_id": None,
                "unit_type": "estimated",
                "rooms": None,
                "surface_m2": surface,
                "current_rent_estimate": benchmark_monthly,
                "benchmark_monthly": round(benchmark_monthly),
                "benchmark_rate_m2": benchmark_rate,
                "delta_pct": 0.0,
                "verdict": "at_market",
            }
        )

    # Portfolio/commune yield
    commune_avg_yield = _CANTON_AVG_YIELD.get(canton, _DEFAULT_YIELD)
    annual_benchmark = total_benchmark_rent * 12
    optimization_potential = max(0, total_benchmark_rent - total_current_rent) * 12 if total_current_rent > 0 else 0.0

    return {
        "building_id": str(building_id),
        "city": city,
        "canton": canton,
        "units": unit_analyses,
        "total_benchmark_monthly": round(total_benchmark_rent),
        "total_current_monthly": round(total_current_rent) if total_current_rent > 0 else None,
        "annual_benchmark_rent": round(annual_benchmark),
        "commune_avg_yield": commune_avg_yield,
        "optimization_potential_chf": round(optimization_potential),
        "generated_at": datetime.now(UTC).isoformat(),
    }
