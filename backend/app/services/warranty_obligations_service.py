"""Service for warranty obligations, recurring obligations, and defect tracking."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.schemas.warranty_obligations import (
    BuildingDefectSummary,
    BuildingObligationsSchedule,
    BuildingWarrantyReport,
    DefectClaim,
    PortfolioWarrantyOverview,
    RecurringObligation,
    WarrantyItem,
)
from app.services.building_data_loader import load_org_buildings

# ---------------------------------------------------------------------------
# Duration rules (months) by warranty type and pollutant context
# ---------------------------------------------------------------------------

_DEFECT_LIABILITY_MONTHS = 24
_WORKMANSHIP_MONTHS = 12
_MATERIAL_GUARANTEE_MONTHS_DEFAULT = 36
_MATERIAL_GUARANTEE_MONTHS_ASBESTOS = 60
_EXPIRING_SOON_DAYS = 90


def _warranty_status(end_dt: date, today: date) -> str:
    if end_dt < today:
        return "expired"
    if (end_dt - today).days <= _EXPIRING_SOON_DAYS:
        return "expiring_soon"
    return "active"


def _add_months(start: date, months: int) -> date:
    """Approximate month addition."""
    return start + timedelta(days=months * 30)


def _build_warranties_for_intervention(
    intervention: Intervention,
    today: date,
    is_asbestos: bool,
) -> list[WarrantyItem]:
    """Generate warranty items for a single completed intervention."""
    base_id = str(intervention.id)[:8]
    start = intervention.date_end or (
        intervention.date_start or intervention.created_at.date() if intervention.created_at else today
    )
    items: list[WarrantyItem] = []

    # Defect liability — 2 years
    dl_end = _add_months(start, _DEFECT_LIABILITY_MONTHS)
    items.append(
        WarrantyItem(
            warranty_id=f"WR-{base_id}-DL",
            intervention_id=intervention.id,
            warranty_type="defect_liability",
            start_date=start,
            end_date=dl_end,
            duration_months=_DEFECT_LIABILITY_MONTHS,
            contractor_name=intervention.contractor_name,
            status=_warranty_status(dl_end, today),
            coverage_description="Defect liability period per SIA 118",
        )
    )

    # Material guarantee — 5 years (asbestos) / 3 years (others)
    mg_months = _MATERIAL_GUARANTEE_MONTHS_ASBESTOS if is_asbestos else _MATERIAL_GUARANTEE_MONTHS_DEFAULT
    mg_end = _add_months(start, mg_months)
    items.append(
        WarrantyItem(
            warranty_id=f"WR-{base_id}-MG",
            intervention_id=intervention.id,
            warranty_type="material_guarantee",
            start_date=start,
            end_date=mg_end,
            duration_months=mg_months,
            contractor_name=intervention.contractor_name,
            status=_warranty_status(mg_end, today),
            coverage_description=f"Material guarantee ({mg_months} months)",
        )
    )

    # Workmanship — 1 year
    wm_end = _add_months(start, _WORKMANSHIP_MONTHS)
    items.append(
        WarrantyItem(
            warranty_id=f"WR-{base_id}-WM",
            intervention_id=intervention.id,
            warranty_type="workmanship",
            start_date=start,
            end_date=wm_end,
            duration_months=_WORKMANSHIP_MONTHS,
            contractor_name=intervention.contractor_name,
            status=_warranty_status(wm_end, today),
            coverage_description="Workmanship guarantee",
        )
    )

    return items


# ---------------------------------------------------------------------------
# FN1 — Building Warranty Report
# ---------------------------------------------------------------------------


async def get_building_warranty_report(
    building_id: UUID,
    db: AsyncSession,
) -> BuildingWarrantyReport | None:
    building = await db.get(Building, building_id)
    if not building:
        return None

    today = date.today()

    # Fetch completed interventions
    result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building_id,
            Intervention.status == "completed",
        )
    )
    interventions = list(result.scalars().all())

    # Check if building has asbestos diagnostics
    diag_result = await db.execute(
        select(Diagnostic).where(
            Diagnostic.building_id == building_id,
            Diagnostic.diagnostic_type == "asbestos",
        )
    )
    has_asbestos = bool(diag_result.scalars().first())

    warranties: list[WarrantyItem] = []
    for intv in interventions:
        warranties.extend(_build_warranties_for_intervention(intv, today, has_asbestos))

    total_active = sum(1 for w in warranties if w.status == "active")
    total_expiring = sum(1 for w in warranties if w.status == "expiring_soon")
    total_expired = sum(1 for w in warranties if w.status == "expired")

    total_interventions = len(interventions)
    coverage_score = (total_active / total_interventions) if total_interventions > 0 else 1.0
    coverage_score = min(coverage_score, 1.0)

    return BuildingWarrantyReport(
        building_id=building_id,
        warranties=warranties,
        total_active=total_active,
        total_expiring_soon=total_expiring,
        total_expired=total_expired,
        coverage_score=round(coverage_score, 2),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2 — Obligations Schedule
# ---------------------------------------------------------------------------


async def get_obligations_schedule(
    building_id: UUID,
    db: AsyncSession,
) -> BuildingObligationsSchedule | None:
    building = await db.get(Building, building_id)
    if not building:
        return None

    today = date.today()
    obligations: list[RecurringObligation] = []
    ob_counter = 0

    # Diagnostics with exceeded samples
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    for diag in diagnostics:
        sample_result = await db.execute(
            select(Sample).where(
                Sample.diagnostic_id == diag.id,
                Sample.threshold_exceeded.is_(True),
            )
        )
        exceeded_samples = list(sample_result.scalars().all())
        if not exceeded_samples:
            continue

        last_performed = diag.date_inspection or (diag.created_at.date() if diag.created_at else None)

        pollutant_type = diag.diagnostic_type
        if pollutant_type in ("asbestos", "radon"):
            ob_counter += 1
            freq = 12
            next_due = _add_months(last_performed, freq) if last_performed else today
            obligations.append(
                RecurringObligation(
                    obligation_id=f"OB-{ob_counter:04d}",
                    obligation_type="air_monitoring",
                    frequency_months=freq,
                    last_performed=last_performed,
                    next_due=next_due,
                    is_overdue=next_due < today,
                    pollutant_type=pollutant_type,
                    description=f"Annual air monitoring for {pollutant_type}",
                )
            )
        elif pollutant_type == "pcb":
            ob_counter += 1
            freq = 24
            next_due = _add_months(last_performed, freq) if last_performed else today
            obligations.append(
                RecurringObligation(
                    obligation_id=f"OB-{ob_counter:04d}",
                    obligation_type="surface_testing",
                    frequency_months=freq,
                    last_performed=last_performed,
                    next_due=next_due,
                    is_overdue=next_due < today,
                    pollutant_type="pcb",
                    description="Biennial surface testing for PCB",
                )
            )

    # Completed interventions → maintenance_check every 12 months
    intv_result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building_id,
            Intervention.status == "completed",
        )
    )
    for intv in intv_result.scalars().all():
        ob_counter += 1
        last_performed = intv.date_end or (intv.created_at.date() if intv.created_at else None)
        next_due = _add_months(last_performed, 12) if last_performed else today
        obligations.append(
            RecurringObligation(
                obligation_id=f"OB-{ob_counter:04d}",
                obligation_type="maintenance_check",
                frequency_months=12,
                last_performed=last_performed,
                next_due=next_due,
                is_overdue=next_due < today,
                pollutant_type=None,
                description=f"Annual maintenance check for intervention {str(intv.id)[:8]}",
            )
        )

    overdue_count = sum(1 for o in obligations if o.is_overdue)
    next_dates = [o.next_due for o in obligations if o.next_due >= today]
    next_action_date = min(next_dates) if next_dates else None

    return BuildingObligationsSchedule(
        building_id=building_id,
        obligations=obligations,
        total_obligations=len(obligations),
        overdue_count=overdue_count,
        next_action_date=next_action_date,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3 — Defect Summary
# ---------------------------------------------------------------------------

_PRIORITY_TO_SEVERITY = {
    "critical": "critical",
    "high": "major",
    "medium": "minor",
    "low": "minor",
}

_STATUS_TO_CLAIM = {
    "open": "reported",
    "in_progress": "under_review",
    "completed": "resolved",
}


async def get_defect_summary(
    building_id: UUID,
    db: AsyncSession,
) -> BuildingDefectSummary | None:
    building = await db.get(Building, building_id)
    if not building:
        return None

    result = await db.execute(
        select(ActionItem).where(
            ActionItem.building_id == building_id,
        )
    )
    actions = list(result.scalars().all())

    claims: list[DefectClaim] = []
    for action in actions:
        is_defect = (
            action.source_type == "intervention"
            or "defect" in (action.action_type or "").lower()
            or "rework" in (action.action_type or "").lower()
        )
        if not is_defect:
            continue

        severity = _PRIORITY_TO_SEVERITY.get(action.priority, "minor")
        claim_status = _STATUS_TO_CLAIM.get(action.status, "reported")
        reported = action.created_at.date() if action.created_at else date.today()

        claims.append(
            DefectClaim(
                claim_id=f"DC-{str(action.id)[:8]}",
                warranty_id=f"WR-{str(action.id)[:8]}",
                defect_description=action.title or "Defect claim",
                reported_date=reported,
                severity=severity,
                status=claim_status,
            )
        )

    total = len(claims)
    resolved = sum(1 for c in claims if c.status == "resolved")
    open_claims = sum(1 for c in claims if c.status not in ("resolved", "rejected"))
    resolution_rate = (resolved / total) if total > 0 else 0.0

    return BuildingDefectSummary(
        building_id=building_id,
        claims=claims,
        total_claims=total,
        open_claims=open_claims,
        resolution_rate=round(resolution_rate, 2),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4 — Portfolio Warranty Overview
# ---------------------------------------------------------------------------


async def get_portfolio_warranty_overview(
    org_id: UUID,
    db: AsyncSession,
) -> PortfolioWarrantyOverview | None:
    org = await db.get(Organization, org_id)
    if not org:
        return None

    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return PortfolioWarrantyOverview(
            organization_id=org_id,
            total_buildings=0,
            total_active_warranties=0,
            expiring_within_90_days=0,
            total_overdue_obligations=0,
            average_coverage_score=0.0,
            generated_at=datetime.now(UTC),
        )

    total_active = 0
    expiring_90 = 0
    total_overdue = 0
    coverage_scores: list[float] = []

    for bldg in buildings:
        report = await get_building_warranty_report(bldg.id, db)
        if report:
            total_active += report.total_active
            expiring_90 += report.total_expiring_soon
            coverage_scores.append(report.coverage_score)

        schedule = await get_obligations_schedule(bldg.id, db)
        if schedule:
            total_overdue += schedule.overdue_count

    avg_score = (sum(coverage_scores) / len(coverage_scores)) if coverage_scores else 0.0

    return PortfolioWarrantyOverview(
        organization_id=org_id,
        total_buildings=len(buildings),
        total_active_warranties=total_active,
        expiring_within_90_days=expiring_90,
        total_overdue_obligations=total_overdue,
        average_coverage_score=round(avg_score, 2),
        generated_at=datetime.now(UTC),
    )
