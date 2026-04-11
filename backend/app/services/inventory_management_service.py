"""Inventory management service — warranty alerts + replacement cost timeline."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory_item import InventoryItem
from app.models.notification import Notification

NOTIFICATION_TYPE_ALERT = "action"


async def check_warranty_expiry(
    db: AsyncSession,
    item: InventoryItem,
    user_id: UUID,
) -> dict[str, Any] | None:
    """Create a warranty-expiry notification if warranty is expiring within 90 days.

    Returns alert dict if created, None if not applicable or already notified.
    """
    if not item.warranty_end_date:
        return None

    today = date.today()
    days_until = (item.warranty_end_date - today).days

    if days_until > 90:
        return None

    if days_until < 0:
        severity = "high"
        title = f"Garantie expiree: {item.name}"
        message = f"La garantie de {item.name} a expire le {item.warranty_end_date.isoformat()}."
        action = "Planifier le remplacement ou renouveler la garantie."
    elif days_until <= 30:
        severity = "high"
        title = f"Garantie expire bientot: {item.name}"
        message = f"La garantie de {item.name} expire dans {days_until} jours ({item.warranty_end_date.isoformat()})."
        action = "Contacter le fournisseur pour renouvellement."
    else:
        severity = "medium"
        title = f"Garantie a surveiller: {item.name}"
        message = f"La garantie de {item.name} expire dans {days_until} jours ({item.warranty_end_date.isoformat()})."
        action = "Planifier le renouvellement de la garantie."

    fingerprint = f"warranty:{item.building_id}:{item.id}"

    # Deduplicate: skip if unread notification with same fingerprint exists
    existing = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.link == fingerprint,
            Notification.status == "unread",
        )
    )
    if existing.scalar_one_or_none():
        return None

    notification = Notification(
        user_id=user_id,
        type=NOTIFICATION_TYPE_ALERT,
        title=title,
        body=f"[{severity.upper()}] {message}\n\nAction recommandee: {action}",
        link=fingerprint,
        status="unread",
    )
    db.add(notification)

    return {
        "severity": severity,
        "title": title,
        "message": message,
        "days_until_expiry": days_until,
        "recommended_action": action,
        "notification_id": str(notification.id),
    }


async def get_replacement_cost_timeline(
    db: AsyncSession,
    building_id: UUID,
) -> dict[str, Any]:
    """Forecast 5/10-year replacement costs aggregated by item type.

    Uses installation_date + estimated lifespan heuristics to project when
    replacement is needed. Items without replacement_cost_chf are excluded.
    """
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.building_id == building_id,
            InventoryItem.replacement_cost_chf.isnot(None),
        )
    )
    items = result.scalars().all()

    today = date.today()
    year_now = today.year

    # Estimated lifespans by type (years)
    lifespans: dict[str, int] = {
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

    by_type: dict[str, dict[str, Any]] = {}
    total_5y = 0.0
    total_10y = 0.0

    for item in items:
        lifespan = lifespans.get(item.item_type, 15)
        if item.installation_date:
            replacement_year = item.installation_date.year + lifespan
        else:
            # Unknown install date → assume replacement within 5 years
            replacement_year = year_now + 3

        cost = item.replacement_cost_chf or 0.0
        in_5y = replacement_year <= year_now + 5
        in_10y = replacement_year <= year_now + 10

        entry = by_type.setdefault(item.item_type, {
            "item_type": item.item_type,
            "count": 0,
            "total_replacement_cost_chf": 0.0,
            "cost_5y_chf": 0.0,
            "cost_10y_chf": 0.0,
            "items": [],
        })
        entry["count"] += 1
        entry["total_replacement_cost_chf"] += cost
        if in_5y:
            entry["cost_5y_chf"] += cost
            total_5y += cost
        if in_10y:
            entry["cost_10y_chf"] += cost
            total_10y += cost

        entry["items"].append({
            "id": str(item.id),
            "name": item.name,
            "replacement_cost_chf": cost,
            "estimated_replacement_year": replacement_year,
            "condition": item.condition,
        })

    return {
        "building_id": str(building_id),
        "forecast_date": today.isoformat(),
        "total_5y_chf": total_5y,
        "total_10y_chf": total_10y,
        "by_type": list(by_type.values()),
    }
