"""Equipment lifecycle and replacement timeline service."""

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory_item import InventoryItem

# Average useful lifespan in years by equipment type (Swiss market data)
EQUIPMENT_LIFESPAN: dict[str, int] = {
    "hvac": 15,
    "boiler": 25,
    "elevator": 30,
    "heat_pump": 20,
    "solar_panel": 25,
    "water_heater": 12,
    "electrical_panel": 40,
    "ventilation": 20,
    "fire_system": 15,
    "garage_door": 15,
    "intercom": 12,
    "appliance": 10,
    "furniture": 15,
    "other": 15,
}

DEFAULT_LIFESPAN = 15


def _estimate_replacement_year(item: InventoryItem) -> int | None:
    """Estimate the year an item will need replacement."""
    if item.warranty_end_date:
        return item.warranty_end_date.year
    if item.installation_date:
        lifespan = EQUIPMENT_LIFESPAN.get(item.item_type, DEFAULT_LIFESPAN)
        return item.installation_date.year + lifespan
    return None


def _is_critical(item: InventoryItem, replacement_year: int, today: date) -> bool:
    """Determine if an item needs urgent replacement."""
    if item.condition == "critical":
        return True
    if replacement_year <= today.year:
        return True
    return bool(item.warranty_end_date and item.warranty_end_date < today)


async def get_equipment_timeline(
    db: AsyncSession,
    building_id: UUID,
    years: int = 10,
) -> dict:
    """Get equipment replacement forecast for a building.

    Returns a timeline of items due for replacement within the forecast period,
    sorted by replacement year, with total cost and critical item count.
    """
    today = date.today()

    result = await db.execute(
        select(InventoryItem).where(InventoryItem.building_id == building_id)
    )
    items = result.scalars().all()

    timeline = []
    total_cost = 0.0
    critical_count = 0

    for item in items:
        replacement_year = _estimate_replacement_year(item)
        if replacement_year is None:
            continue

        years_until = replacement_year - today.year

        # Include overdue items (years_until < 0) and items within forecast window
        if years_until > years:
            continue

        cost = item.replacement_cost_chf or 0.0
        total_cost += cost

        critical = _is_critical(item, replacement_year, today)
        if critical:
            critical_count += 1

        timeline.append({
            "item_id": str(item.id),
            "name": item.name,
            "type": item.item_type,
            "installation_year": item.installation_date.year if item.installation_date else None,
            "replacement_year": replacement_year,
            "years_until_replacement": years_until,
            "condition": item.condition,
            "cost_chf": item.replacement_cost_chf,
            "critical": critical,
        })

    timeline.sort(key=lambda x: x["replacement_year"])

    return {
        "building_id": str(building_id),
        "timeline": timeline,
        "total_forecast_cost_chf": total_cost,
        "critical_items_count": critical_count,
        "forecast_period_years": years,
        "item_count": len(timeline),
    }
