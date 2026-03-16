"""Maintenance Forecast Service.

Generates predictive maintenance items for buildings based on:
- Diagnostic renewal schedules (asbestos every 3yr pre-1991, PCB every 5yr 1955-1975)
- Intervention follow-up inspections (1yr after completed interventions)
- Element replacement forecasts (poor-condition elements within 2yr)
- Compliance checks (annual for high/critical risk buildings)
- General inspection triggers (no diagnostic in >5yr)
"""

from __future__ import annotations

import hashlib
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.zone import Zone
from app.schemas.maintenance_forecast import (
    MaintenanceBudget,
    MaintenanceForecast,
    MaintenanceItem,
    PortfolioMaintenanceForecast,
)


def _item_id(building_id: uuid.UUID, item_type: str, suffix: str = "") -> str:
    """Deterministic item id based on building + type + suffix."""
    raw = f"{building_id}:{item_type}:{suffix}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def forecast_building_maintenance(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> MaintenanceForecast:
    """Generate a full maintenance forecast for one building."""
    # Load building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return MaintenanceForecast(
            building_id=building_id,
            items=[],
            total_items=0,
            next_12_months=0,
            total_estimated_cost=None,
            generated_at=datetime.now(UTC),
        )

    items: list[MaintenanceItem] = []
    today = date.today()

    # 1. Diagnostic renewal
    items.extend(await _diagnostic_renewal_items(db, building, today))

    # 2. Intervention follow-up
    items.extend(await _intervention_followup_items(db, building, today))

    # 3. Element replacement
    items.extend(await _element_replacement_items(db, building, today))

    # 4. Compliance check
    items.extend(await _compliance_check_items(db, building, today))

    # 5. Inspection due
    items.extend(await _inspection_due_items(db, building, today))

    # Compute aggregates
    twelve_months = today + timedelta(days=365)
    next_12 = sum(1 for i in items if i.estimated_date and i.estimated_date <= twelve_months)
    total_cost = sum(i.estimated_cost_chf for i in items if i.estimated_cost_chf) or None

    return MaintenanceForecast(
        building_id=building_id,
        items=items,
        total_items=len(items),
        next_12_months=next_12,
        total_estimated_cost=total_cost,
        generated_at=datetime.now(UTC),
    )


async def _diagnostic_renewal_items(
    db: AsyncSession,
    building: Building,
    today: date,
) -> list[MaintenanceItem]:
    """Asbestos every 3yr (pre-1991), PCB every 5yr (1955-1975)."""
    items: list[MaintenanceItem] = []
    construction_year = building.construction_year

    # Asbestos: pre-1991 buildings
    if construction_year and construction_year < 1991:
        last_asbestos = await _last_diagnostic_date(db, building.id, "asbestos")
        if last_asbestos:
            next_due = date(last_asbestos.year + 3, last_asbestos.month, last_asbestos.day)
        else:
            next_due = today  # overdue
        items.append(
            MaintenanceItem(
                id=_item_id(building.id, "diagnostic_renewal", "asbestos"),
                building_id=building.id,
                item_type="diagnostic_renewal",
                title="Asbestos diagnostic renewal",
                description=f"Pre-1991 building ({construction_year}): asbestos diagnostic due every 3 years.",
                estimated_date=next_due,
                priority="high" if next_due <= today else "medium",
                estimated_cost_chf=3500.0,
                confidence=0.85,
                metadata={"pollutant": "asbestos", "cycle_years": 3},
            )
        )

    # PCB: 1955-1975 buildings
    if construction_year and 1955 <= construction_year <= 1975:
        last_pcb = await _last_diagnostic_date(db, building.id, "pcb")
        if last_pcb:
            next_due = date(last_pcb.year + 5, last_pcb.month, last_pcb.day)
        else:
            next_due = today
        items.append(
            MaintenanceItem(
                id=_item_id(building.id, "diagnostic_renewal", "pcb"),
                building_id=building.id,
                item_type="diagnostic_renewal",
                title="PCB diagnostic renewal",
                description=f"Building from PCB era ({construction_year}): PCB diagnostic due every 5 years.",
                estimated_date=next_due,
                priority="high" if next_due <= today else "medium",
                estimated_cost_chf=4000.0,
                confidence=0.80,
                metadata={"pollutant": "pcb", "cycle_years": 5},
            )
        )

    return items


async def _last_diagnostic_date(
    db: AsyncSession,
    building_id: uuid.UUID,
    diagnostic_type: str,
) -> date | None:
    """Get the most recent completed diagnostic date for a type."""
    result = await db.execute(
        select(Diagnostic.date_report)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.diagnostic_type == diagnostic_type,
            Diagnostic.status.in_(["completed", "validated"]),
        )
        .order_by(Diagnostic.date_report.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row


async def _intervention_followup_items(
    db: AsyncSession,
    building: Building,
    today: date,
) -> list[MaintenanceItem]:
    """Completed interventions need re-inspection 1 year later."""
    result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building.id,
            Intervention.status == "completed",
        )
    )
    interventions = result.scalars().all()
    items: list[MaintenanceItem] = []

    for interv in interventions:
        # Use updated_at or created_at as the completion date
        completion = interv.date_end or (interv.updated_at.date() if interv.updated_at else today)
        followup_date = completion + timedelta(days=365)
        items.append(
            MaintenanceItem(
                id=_item_id(building.id, "intervention_followup", str(interv.id)),
                building_id=building.id,
                item_type="intervention_followup",
                title=f"Follow-up inspection: {interv.title}",
                description=f"Re-inspection needed 1 year after completed intervention ({interv.intervention_type}).",
                estimated_date=followup_date,
                priority="medium",
                estimated_cost_chf=1000.0,
                confidence=0.90,
                metadata={"intervention_id": str(interv.id), "intervention_type": interv.intervention_type},
            )
        )

    return items


async def _element_replacement_items(
    db: AsyncSession,
    building: Building,
    today: date,
) -> list[MaintenanceItem]:
    """Elements with condition='poor' need replacement within 2 years."""
    result = await db.execute(
        select(BuildingElement)
        .join(Zone, BuildingElement.zone_id == Zone.id)
        .where(
            Zone.building_id == building.id,
            BuildingElement.condition == "poor",
        )
    )
    elements = result.scalars().all()
    items: list[MaintenanceItem] = []

    for elem in elements:
        replacement_date = today + timedelta(days=730)  # within 2 years
        # Cost varies by element type
        cost = 20000.0 if elem.element_type in ("structural", "wall", "floor") else 5000.0
        items.append(
            MaintenanceItem(
                id=_item_id(building.id, "element_replacement", str(elem.id)),
                building_id=building.id,
                item_type="element_replacement",
                title=f"Replace {elem.element_type}: {elem.name}",
                description="Element in poor condition — replacement recommended within 2 years.",
                estimated_date=replacement_date,
                priority="high",
                estimated_cost_chf=cost,
                confidence=0.70,
                metadata={"element_id": str(elem.id), "element_type": elem.element_type},
            )
        )

    return items


async def _compliance_check_items(
    db: AsyncSession,
    building: Building,
    today: date,
) -> list[MaintenanceItem]:
    """Buildings with risk_level high/critical need annual compliance check."""
    result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building.id))
    risk = result.scalar_one_or_none()
    if not risk or risk.overall_risk_level not in ("high", "critical"):
        return []

    return [
        MaintenanceItem(
            id=_item_id(building.id, "compliance_check", str(today.year)),
            building_id=building.id,
            item_type="compliance_check",
            title="Annual compliance check",
            description=f"Building with {risk.overall_risk_level} risk level requires annual compliance verification.",
            estimated_date=date(today.year + 1, 1, 1),
            priority="high" if risk.overall_risk_level == "critical" else "medium",
            estimated_cost_chf=1500.0,
            confidence=0.85,
            metadata={"risk_level": risk.overall_risk_level},
        )
    ]


async def _inspection_due_items(
    db: AsyncSession,
    building: Building,
    today: date,
) -> list[MaintenanceItem]:
    """Buildings with no diagnostic in >5 years need general inspection."""
    result = await db.execute(
        select(func.max(Diagnostic.date_report)).where(
            Diagnostic.building_id == building.id,
            Diagnostic.status.in_(["completed", "validated"]),
        )
    )
    last_date = result.scalar_one_or_none()

    threshold = today - timedelta(days=5 * 365)
    if last_date and last_date > threshold:
        return []

    # No recent diagnostic — inspection due
    return [
        MaintenanceItem(
            id=_item_id(building.id, "inspection_due", "general"),
            building_id=building.id,
            item_type="inspection_due",
            title="General building inspection due",
            description="No diagnostic performed in the last 5 years — general inspection recommended.",
            estimated_date=today,
            priority="medium",
            estimated_cost_chf=3000.0,
            confidence=0.75,
            metadata={"last_diagnostic_date": str(last_date) if last_date else None},
        )
    ]


async def get_maintenance_budget(
    db: AsyncSession,
    building_id: uuid.UUID,
    years: int = 5,
) -> MaintenanceBudget:
    """Group forecast items by year and sum costs."""
    forecast = await forecast_building_maintenance(db, building_id)
    today = date.today()

    yearly: dict[int, dict] = {}
    for yr in range(today.year, today.year + years):
        yearly[yr] = {"year": yr, "items": 0, "estimated_cost": 0.0}

    for item in forecast.items:
        if item.estimated_date:
            yr = item.estimated_date.year
            if yr in yearly:
                yearly[yr]["items"] += 1
                yearly[yr]["estimated_cost"] += item.estimated_cost_chf or 0.0

    yearly_list = sorted(yearly.values(), key=lambda x: x["year"])
    total_3 = sum(y["estimated_cost"] for y in yearly_list[:3]) or None
    total_5 = sum(y["estimated_cost"] for y in yearly_list[:5]) or None

    return MaintenanceBudget(
        building_id=building_id,
        yearly_forecasts=yearly_list,
        total_3_year=total_3,
        total_5_year=total_5,
    )


async def forecast_portfolio_maintenance(
    db: AsyncSession,
    org_id: uuid.UUID | None = None,
) -> PortfolioMaintenanceForecast:
    """Aggregate maintenance forecasts across all buildings."""
    query = select(Building.id, Building.address)
    if org_id:
        # Filter by owner organization if needed; for now we just use all buildings
        pass
    result = await db.execute(query)
    buildings = result.all()

    all_items: list[MaintenanceItem] = []
    building_costs: dict[uuid.UUID, dict] = {}

    for b_id, b_address in buildings:
        forecast = await forecast_building_maintenance(db, b_id)
        all_items.extend(forecast.items)
        cost = forecast.total_estimated_cost or 0.0
        building_costs[b_id] = {
            "building_id": str(b_id),
            "address": b_address,
            "item_count": forecast.total_items,
            "cost": cost,
        }

    by_type: dict[str, int] = defaultdict(int)
    by_priority: dict[str, int] = defaultdict(int)
    for item in all_items:
        by_type[item.item_type] += 1
        by_priority[item.priority] += 1

    total_cost = sum(i.estimated_cost_chf for i in all_items if i.estimated_cost_chf) or None
    top_buildings = sorted(building_costs.values(), key=lambda x: x["cost"], reverse=True)[:10]

    return PortfolioMaintenanceForecast(
        total_buildings=len(buildings),
        total_items=len(all_items),
        by_type=dict(by_type),
        by_priority=dict(by_priority),
        total_estimated_cost=total_cost,
        top_buildings=top_buildings,
    )


async def get_upcoming_maintenance(
    db: AsyncSession,
    building_id: uuid.UUID,
    months: int = 12,
) -> list[MaintenanceItem]:
    """Return only items due within the next N months, sorted by date."""
    forecast = await forecast_building_maintenance(db, building_id)
    cutoff = date.today() + timedelta(days=months * 30)
    upcoming = [i for i in forecast.items if i.estimated_date and i.estimated_date <= cutoff]
    return sorted(upcoming, key=lambda i: i.estimated_date or date.max)
