"""Equipment Lifecycle Service — replacement timeline and CAPEX forecasting.

Computes replacement urgency and multi-year budget forecasts for all
InventoryItems in a building, based on installation date, expected
lifespan by equipment type, and replacement cost.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory_item import InventoryItem

if TYPE_CHECKING:
    pass

# ── Expected lifespan by equipment type (years) ──────────────────
LIFESPAN_BY_TYPE: dict[str, int] = {
    "hvac": 20,
    "boiler": 15,
    "elevator": 25,
    "fire_system": 15,
    "electrical_panel": 30,
    "solar_panel": 25,
    "heat_pump": 20,
    "ventilation": 15,
    "water_heater": 12,
    "garage_door": 20,
    "intercom": 10,
    "appliance": 10,
    "furniture": 15,
    "other": 15,
}

# ── Urgency thresholds (years remaining) ─────────────────────────
_CRITICAL_THRESHOLD = 2
_PLANNED_THRESHOLD = 5


def _compute_urgency(remaining_years: float) -> str:
    """Classify remaining life into urgency bucket."""
    if remaining_years <= 0:
        return "overdue"
    if remaining_years < _CRITICAL_THRESHOLD:
        return "critical"
    if remaining_years < _PLANNED_THRESHOLD:
        return "planned"
    return "ok"


_URGENCY_ORDER = {"overdue": 0, "critical": 1, "planned": 2, "ok": 3}


async def compute_replacement_timeline(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict]:
    """Build a replacement timeline for all inventory items in a building.

    Returns a list of dicts sorted by urgency (overdue first) then remaining_life.
    Each dict contains: item_id, item_name, item_type, installation_date,
    age_years, expected_lifespan, remaining_life, urgency, replacement_cost.
    """
    result = await db.execute(select(InventoryItem).where(InventoryItem.building_id == building_id))
    items = list(result.scalars().all())

    today = date.today()
    timeline: list[dict] = []

    for item in items:
        expected_lifespan = LIFESPAN_BY_TYPE.get(item.item_type, 15)

        if item.installation_date is not None:
            age_years = round((today - item.installation_date).days / 365.25, 1)
            remaining_life = round(expected_lifespan - age_years, 1)
        else:
            # Unknown installation date — assume midlife
            age_years = None
            remaining_life = None

        urgency = _compute_urgency(remaining_life) if remaining_life is not None else "unknown"

        timeline.append(
            {
                "item_id": str(item.id),
                "item_name": item.name,
                "item_type": item.item_type,
                "installation_date": item.installation_date.isoformat() if item.installation_date else None,
                "age_years": age_years,
                "expected_lifespan": expected_lifespan,
                "remaining_life": remaining_life,
                "urgency": urgency,
                "replacement_cost": item.replacement_cost_chf,
            }
        )

    # Sort: urgency order first, then remaining_life ascending (None last)
    timeline.sort(
        key=lambda x: (
            _URGENCY_ORDER.get(x["urgency"], 99),
            x["remaining_life"] if x["remaining_life"] is not None else 9999,
        )
    )
    return timeline


async def compute_capex_forecast(
    db: AsyncSession,
    building_id: UUID,
    years: int = 10,
) -> dict:
    """Aggregate replacement costs by year for the next N years.

    Returns: {"forecast": {year: total_cost}, "grand_total": float, "years": int,
              "items_without_cost": int, "items_without_date": int}.
    """
    timeline = await compute_replacement_timeline(db, building_id)

    current_year = date.today().year
    forecast: dict[int, float] = {}
    items_without_cost = 0
    items_without_date = 0

    for entry in timeline:
        remaining = entry["remaining_life"]
        cost = entry["replacement_cost"]

        if remaining is None:
            items_without_date += 1
            continue

        if cost is None:
            items_without_cost += 1
            continue

        # Calculate replacement year
        replacement_year = current_year + max(0, int(remaining))

        # Only include within forecast window
        if replacement_year <= current_year + years:
            forecast[replacement_year] = forecast.get(replacement_year, 0.0) + cost

    grand_total = sum(forecast.values())

    return {
        "forecast": dict(sorted(forecast.items())),
        "grand_total": round(grand_total, 2),
        "years": years,
        "items_without_cost": items_without_cost,
        "items_without_date": items_without_date,
    }
