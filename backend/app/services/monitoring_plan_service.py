"""Monitoring Plan Service.

Generates and tracks post-remediation monitoring plans for buildings with
encapsulated or sealed pollutant materials that require ongoing surveillance.

Covers:
- Encapsulated asbestos → annual visual inspection + biannual air sampling
- Sealed PCB → annual wipe test
- Radon (above 300 Bq/m³) → biannual radon measurement
- Lead (sealed/encapsulated) → annual visual inspection
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.monitoring_plan import (
    BuildingMonitoringStatus,
    ComplianceGap,
    MonitoringCompliance,
    MonitoringItem,
    MonitoringPlan,
    MonitoringSchedule,
    PortfolioMonitoringStatus,
    ScheduledCheck,
)
from app.services.building_data_loader import load_org_buildings

# Frequency → days between checks
_FREQ_DAYS: dict[str, int] = {
    "quarterly": 90,
    "biannual": 182,
    "annual": 365,
}

# Annual multiplier for cost calculation
_FREQ_CYCLES: dict[str, int] = {
    "quarterly": 4,
    "biannual": 2,
    "annual": 1,
}


def _item_id(building_id: uuid.UUID, pollutant: str, suffix: str = "") -> str:
    """Deterministic item id based on building + pollutant + suffix."""
    raw = f"{building_id}:monitoring:{pollutant}:{suffix}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def generate_monitoring_plan(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> MonitoringPlan:
    """Auto-generate a monitoring plan from building state.

    Inspects diagnostics/samples for encapsulated asbestos, sealed PCB,
    elevated radon, and sealed lead to produce monitoring items.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return MonitoringPlan(
            building_id=building_id,
            items=[],
            total_items=0,
            annual_cost_chf=0.0,
            generated_at=datetime.now(UTC),
        )

    items: list[MonitoringItem] = []

    # Gather encapsulated/sealed samples from completed diagnostics
    items.extend(await _asbestos_monitoring_items(db, building))
    items.extend(await _pcb_monitoring_items(db, building))
    items.extend(await _radon_monitoring_items(db, building))
    items.extend(await _lead_monitoring_items(db, building))

    # Also check for encapsulation interventions
    items.extend(await _intervention_monitoring_items(db, building))

    # Deduplicate by id
    seen: set[str] = set()
    unique_items: list[MonitoringItem] = []
    for item in items:
        if item.id not in seen:
            seen.add(item.id)
            unique_items.append(item)

    annual_cost = sum(item.cost_per_cycle_chf * _FREQ_CYCLES.get(item.frequency, 1) for item in unique_items)

    return MonitoringPlan(
        building_id=building_id,
        items=unique_items,
        total_items=len(unique_items),
        annual_cost_chf=annual_cost,
        generated_at=datetime.now(UTC),
    )


async def _asbestos_monitoring_items(
    db: AsyncSession,
    building: Building,
) -> list[MonitoringItem]:
    """Encapsulated asbestos needs visual inspection (annual) + air sampling (biannual)."""
    samples = await _get_pollutant_samples(db, building.id, "asbestos", encapsulated=True)
    items: list[MonitoringItem] = []
    for s in samples:
        location = _sample_location(s)
        items.append(
            MonitoringItem(
                id=_item_id(building.id, "asbestos_visual", str(s.id)),
                pollutant_type="asbestos",
                location=location,
                monitoring_method="visual_inspection",
                frequency="annual",
                responsible_party="diagnostician",
                cost_per_cycle_chf=350.0,
                next_due=_next_due_from_sample(s, 365),
                last_performed=_last_check_date(s),
                metadata={"sample_id": str(s.id)},
            )
        )
        items.append(
            MonitoringItem(
                id=_item_id(building.id, "asbestos_air", str(s.id)),
                pollutant_type="asbestos",
                location=location,
                monitoring_method="air_sampling",
                frequency="biannual",
                responsible_party="laboratory",
                cost_per_cycle_chf=800.0,
                next_due=_next_due_from_sample(s, 182),
                last_performed=_last_check_date(s),
                metadata={"sample_id": str(s.id)},
            )
        )
    return items


async def _pcb_monitoring_items(
    db: AsyncSession,
    building: Building,
) -> list[MonitoringItem]:
    """Sealed PCB materials need annual wipe tests."""
    samples = await _get_pollutant_samples(db, building.id, "pcb", encapsulated=True)
    items: list[MonitoringItem] = []
    for s in samples:
        location = _sample_location(s)
        items.append(
            MonitoringItem(
                id=_item_id(building.id, "pcb_wipe", str(s.id)),
                pollutant_type="pcb",
                location=location,
                monitoring_method="wipe_test",
                frequency="annual",
                responsible_party="diagnostician",
                cost_per_cycle_chf=500.0,
                next_due=_next_due_from_sample(s, 365),
                last_performed=_last_check_date(s),
                metadata={"sample_id": str(s.id)},
            )
        )
    return items


async def _radon_monitoring_items(
    db: AsyncSession,
    building: Building,
) -> list[MonitoringItem]:
    """Radon above 300 Bq/m³ needs biannual measurement."""
    samples = await _get_pollutant_samples(db, building.id, "radon", threshold_exceeded=True)
    items: list[MonitoringItem] = []
    for s in samples:
        location = _sample_location(s)
        items.append(
            MonitoringItem(
                id=_item_id(building.id, "radon_measure", str(s.id)),
                pollutant_type="radon",
                location=location,
                monitoring_method="radon_measurement",
                frequency="biannual",
                responsible_party="diagnostician",
                cost_per_cycle_chf=250.0,
                next_due=_next_due_from_sample(s, 182),
                last_performed=_last_check_date(s),
                metadata={"sample_id": str(s.id), "concentration": s.concentration, "unit": s.unit},
            )
        )
    return items


async def _lead_monitoring_items(
    db: AsyncSession,
    building: Building,
) -> list[MonitoringItem]:
    """Sealed/encapsulated lead needs annual visual inspection."""
    samples = await _get_pollutant_samples(db, building.id, "lead", encapsulated=True)
    items: list[MonitoringItem] = []
    for s in samples:
        location = _sample_location(s)
        items.append(
            MonitoringItem(
                id=_item_id(building.id, "lead_visual", str(s.id)),
                pollutant_type="lead",
                location=location,
                monitoring_method="visual_inspection",
                frequency="annual",
                responsible_party="diagnostician",
                cost_per_cycle_chf=300.0,
                next_due=_next_due_from_sample(s, 365),
                last_performed=_last_check_date(s),
                metadata={"sample_id": str(s.id)},
            )
        )
    return items


async def _intervention_monitoring_items(
    db: AsyncSession,
    building: Building,
) -> list[MonitoringItem]:
    """Encapsulation/sealing interventions trigger monitoring."""
    result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building.id,
            Intervention.status == "completed",
            Intervention.intervention_type.in_(["encapsulation", "sealing", "containment"]),
        )
    )
    interventions = result.scalars().all()
    items: list[MonitoringItem] = []

    for interv in interventions:
        completion = interv.date_end or date.today()
        items.append(
            MonitoringItem(
                id=_item_id(building.id, "intervention_monitor", str(interv.id)),
                pollutant_type="asbestos",  # encapsulation is mostly asbestos
                location=interv.title,
                monitoring_method="visual_inspection",
                frequency="annual",
                responsible_party="contractor",
                cost_per_cycle_chf=400.0,
                next_due=completion + timedelta(days=365),
                last_performed=completion,
                metadata={"intervention_id": str(interv.id), "type": interv.intervention_type},
            )
        )

    return items


async def _get_pollutant_samples(
    db: AsyncSession,
    building_id: uuid.UUID,
    pollutant_type: str,
    *,
    encapsulated: bool = False,
    threshold_exceeded: bool = False,
) -> list[Sample]:
    """Fetch samples of a given pollutant type from completed diagnostics."""
    query = (
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
            Sample.pollutant_type == pollutant_type,
        )
    )
    if encapsulated:
        query = query.where(Sample.action_required.in_(["encapsulation", "sealing", "monitoring"]))
    if threshold_exceeded:
        query = query.where(Sample.threshold_exceeded.is_(True))

    result = await db.execute(query)
    return list(result.scalars().all())


def _sample_location(s: Sample) -> str:
    """Build a human-readable location string from sample fields."""
    parts = [p for p in [s.location_floor, s.location_room, s.location_detail] if p]
    return " / ".join(parts) if parts else "Unknown location"


def _last_check_date(s: Sample) -> date | None:
    """Use sample creation as the last check date proxy."""
    if s.created_at:
        if isinstance(s.created_at, datetime):
            return s.created_at.date()
        return s.created_at
    return None


def _next_due_from_sample(s: Sample, interval_days: int) -> date:
    """Calculate next due date from last check + interval."""
    last = _last_check_date(s)
    if last:
        return last + timedelta(days=interval_days)
    return date.today()


# ---------------------------------------------------------------------------
# FN2: get_monitoring_schedule
# ---------------------------------------------------------------------------


async def get_monitoring_schedule(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> MonitoringSchedule:
    """Next 12 months: scheduled checks, overdue checks, cost forecast."""
    plan = await generate_monitoring_plan(db, building_id)
    today = date.today()
    twelve_months = today + timedelta(days=365)

    scheduled: list[ScheduledCheck] = []
    overdue: list[ScheduledCheck] = []

    for item in plan.items:
        if not item.next_due:
            continue

        # Generate checks for the next 12 months
        interval_days = _FREQ_DAYS.get(item.frequency, 365)
        check_date = item.next_due

        while check_date <= twelve_months:
            check = ScheduledCheck(
                item_id=item.id,
                pollutant_type=item.pollutant_type,
                location=item.location,
                monitoring_method=item.monitoring_method,
                scheduled_date=check_date,
                is_overdue=check_date < today,
                cost_chf=item.cost_per_cycle_chf,
            )
            if check_date < today:
                overdue.append(check)
            else:
                scheduled.append(check)
            check_date = check_date + timedelta(days=interval_days)

    scheduled.sort(key=lambda c: c.scheduled_date)
    overdue.sort(key=lambda c: c.scheduled_date)

    cost_forecast = sum(c.cost_chf for c in scheduled) + sum(c.cost_chf for c in overdue)

    return MonitoringSchedule(
        building_id=building_id,
        scheduled_checks=scheduled,
        overdue_checks=overdue,
        total_scheduled=len(scheduled),
        total_overdue=len(overdue),
        cost_forecast_chf=cost_forecast,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3: evaluate_monitoring_compliance
# ---------------------------------------------------------------------------


async def evaluate_monitoring_compliance(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> MonitoringCompliance:
    """Evaluate whether monitoring obligations are being met.

    Compares expected checks (based on plan frequency) against what has been
    performed (approximated from diagnostic dates and intervention dates).
    """
    plan = await generate_monitoring_plan(db, building_id)
    today = date.today()
    one_year_ago = today - timedelta(days=365)

    gaps: list[ComplianceGap] = []
    total_required = 0
    total_performed = 0
    total_overdue = 0

    for item in plan.items:
        cycles = _FREQ_CYCLES.get(item.frequency, 1)
        total_required += cycles

        # Estimate performed checks: if last_performed is recent enough
        performed = 0
        if item.last_performed and item.last_performed >= one_year_ago:
            # Assume at least 1 check was done
            performed = 1
            # For higher frequency, check if next_due is still in the future
            if item.next_due and item.next_due > today:
                performed = min(cycles, max(1, performed))

        missed = max(0, cycles - performed)
        total_performed += performed

        if missed > 0:
            total_overdue += missed
            gaps.append(
                ComplianceGap(
                    item_id=item.id,
                    pollutant_type=item.pollutant_type,
                    location=item.location,
                    expected_checks=cycles,
                    performed_checks=performed,
                    missed_checks=missed,
                    last_performed=item.last_performed,
                )
            )

    # Score: 0-100
    if total_required > 0:
        score = round((total_performed / total_required) * 100)
    else:
        score = 100  # No monitoring required = fully compliant

    score = max(0, min(100, score))

    return MonitoringCompliance(
        building_id=building_id,
        compliance_score=score,
        total_required=total_required,
        total_performed=total_performed,
        total_overdue=total_overdue,
        gaps=gaps,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_monitoring_status
# ---------------------------------------------------------------------------


async def get_portfolio_monitoring_status(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> PortfolioMonitoringStatus:
    """Org-level monitoring status across all buildings."""
    # Find buildings belonging to users in this org
    all_buildings = await load_org_buildings(db, org_id)
    buildings = [b for b in all_buildings if b.status == "active"]

    building_statuses: list[BuildingMonitoringStatus] = []
    total_overdue = 0
    total_annual_cost = 0.0
    buildings_with_plans = 0
    buildings_needing_plans = 0
    compliance_scores: list[int] = []

    for b in buildings:
        plan = await generate_monitoring_plan(db, b.id)
        compliance = await evaluate_monitoring_compliance(db, b.id)

        has_plan = plan.total_items > 0
        if has_plan:
            buildings_with_plans += 1

        # A building needs a new plan if it has pollutant diagnostics but no monitoring items
        needs_plan = await _building_needs_monitoring(db, b.id) and not has_plan
        if needs_plan:
            buildings_needing_plans += 1

        compliance_scores.append(compliance.compliance_score)
        total_overdue += compliance.total_overdue
        total_annual_cost += plan.annual_cost_chf

        building_statuses.append(
            BuildingMonitoringStatus(
                building_id=b.id,
                address=b.address,
                has_active_plan=has_plan,
                compliance_score=compliance.compliance_score,
                overdue_checks=compliance.total_overdue,
                annual_cost_chf=plan.annual_cost_chf,
                needs_new_plan=needs_plan,
            )
        )

    compliance_rate = (
        sum(1 for s in compliance_scores if s >= 80) / len(compliance_scores) if compliance_scores else 1.0
    )

    return PortfolioMonitoringStatus(
        organization_id=org_id,
        total_buildings=len(buildings),
        buildings_with_plans=buildings_with_plans,
        compliance_rate=round(compliance_rate, 2),
        total_overdue_checks=total_overdue,
        total_annual_cost_chf=total_annual_cost,
        buildings_needing_plans=buildings_needing_plans,
        buildings=building_statuses,
        generated_at=datetime.now(UTC),
    )


async def _building_needs_monitoring(db: AsyncSession, building_id: uuid.UUID) -> bool:
    """Check if a building has pollutant samples that would warrant monitoring."""
    result = await db.execute(
        select(func.count())
        .select_from(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
            Sample.threshold_exceeded.is_(True),
        )
    )
    count = result.scalar() or 0
    return count > 0
