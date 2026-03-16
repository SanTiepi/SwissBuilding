"""Service for execution quality evaluation and acceptance control."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.intervention import Intervention
from app.schemas.execution_quality import (
    AcceptanceCriteria,
    BuildingAcceptanceReport,
    BuildingAcceptanceSummary,
    InterventionQualityReport,
    PortfolioQualityDashboard,
    QualityTrend,
    WorkQualityCheck,
)
from app.services.building_data_loader import load_org_buildings

# Check types by intervention type
_CHECK_MAP: dict[str, list[str]] = {
    "removal": ["visual_inspection", "air_measurement"],
    "encapsulation": ["visual_inspection", "air_measurement"],
    "containment": ["visual_inspection", "surface_test"],
    "monitoring": ["lab_verification"],
}
_DEFAULT_CHECKS = ["visual_inspection"]

# Swiss regulatory acceptance criteria
_CRITERIA: dict[str, list[dict[str, object]]] = {
    "asbestos": [
        {
            "threshold_value": 0.01,
            "unit": "fibres/cm3",
            "regulation_ref": "VDI 3492",
            "description": "Air fibre concentration limit after asbestos removal",
        },
        {
            "threshold_value": 1000.0,
            "unit": "fibres/cm2",
            "regulation_ref": "VDI 3492",
            "description": "Surface fibre density limit after asbestos removal",
        },
    ],
    "pcb": [
        {
            "threshold_value": 50.0,
            "unit": "mg/kg",
            "regulation_ref": "ORRChim Annexe 2.15",
            "description": "PCB concentration limit in building materials",
        },
    ],
    "lead": [
        {
            "threshold_value": 5000.0,
            "unit": "mg/kg",
            "regulation_ref": "ORRChim Annexe 2.18",
            "description": "Lead concentration limit in building materials",
        },
    ],
    "hap": [
        {
            "threshold_value": 50.0,
            "unit": "mg/kg",
            "regulation_ref": "ORRChim",
            "description": "HAP concentration limit in building materials",
        },
    ],
    "radon": [
        {
            "threshold_value": 300.0,
            "unit": "Bq/m3",
            "regulation_ref": "ORaP Art. 110",
            "description": "Radon reference level for indoor air",
        },
    ],
}


async def evaluate_intervention_quality(
    intervention_id: UUID,
    db: AsyncSession,
) -> InterventionQualityReport | None:
    """Evaluate quality of a specific intervention."""
    result = await db.execute(select(Intervention).where(Intervention.id == intervention_id))
    intervention = result.scalar_one_or_none()
    if intervention is None:
        return None

    check_types = _CHECK_MAP.get(intervention.intervention_type, _DEFAULT_CHECKS)

    now = datetime.now(UTC)
    checks: list[WorkQualityCheck] = []
    for ct in check_types:
        # Derive status from intervention status
        if intervention.status == "completed":
            status = "passed"
        elif intervention.status == "cancelled":
            status = "waived"
        else:
            status = "pending"

        checks.append(
            WorkQualityCheck(
                check_id=uuid.uuid4(),
                intervention_id=intervention_id,
                check_type=ct,
                status=status,
                checked_by=None,
                checked_at=now if status in ("passed", "waived") else None,
                notes=None,
            )
        )

    total = len(checks)
    passed = sum(1 for c in checks if c.status == "passed")
    pass_rate = passed / total if total > 0 else 0.0

    if all(c.status == "passed" for c in checks):
        overall_status = "acceptable"
    elif any(c.status == "failed" for c in checks):
        overall_status = "requires_rework"
    elif all(c.status == "pending" for c in checks):
        overall_status = "pending"
    else:
        overall_status = "pending"

    return InterventionQualityReport(
        building_id=intervention.building_id,
        intervention_id=intervention_id,
        intervention_type=intervention.intervention_type,
        overall_status=overall_status,
        quality_checks=checks,
        pass_rate=pass_rate,
        generated_at=now,
    )


async def get_acceptance_criteria(pollutant_type: str) -> list[AcceptanceCriteria]:
    """Return Swiss regulatory acceptance criteria for a pollutant type."""
    entries = _CRITERIA.get(pollutant_type, [])
    return [
        AcceptanceCriteria(pollutant_type=pollutant_type, **entry)  # type: ignore[arg-type]
        for entry in entries
    ]


async def get_building_acceptance_report(
    building_id: UUID,
    db: AsyncSession,
) -> BuildingAcceptanceReport | None:
    """Generate acceptance report for all interventions on a building."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(result.scalars().all())

    accepted = 0
    pending = 0
    rejected = 0
    for iv in interventions:
        if iv.status == "completed":
            accepted += 1
        elif iv.status == "cancelled":
            rejected += 1
        else:
            pending += 1

    total = len(interventions)
    acceptance_rate = accepted / total if total > 0 else 0.0

    return BuildingAcceptanceReport(
        building_id=building_id,
        interventions_total=total,
        interventions_accepted=accepted,
        interventions_pending=pending,
        interventions_rejected=rejected,
        acceptance_rate=acceptance_rate,
        by_pollutant={},
        generated_at=datetime.now(UTC),
    )


async def get_portfolio_quality_dashboard(
    org_id: UUID,
    db: AsyncSession,
) -> PortfolioQualityDashboard | None:
    """Generate portfolio-level quality dashboard for an organization."""
    buildings = await load_org_buildings(db, org_id)

    by_building: list[BuildingAcceptanceSummary] = []
    total_interventions = 0
    total_accepted = 0

    for bld in buildings:
        iv_result = await db.execute(select(Intervention).where(Intervention.building_id == bld.id))
        interventions = list(iv_result.scalars().all())
        total = len(interventions)
        accepted = sum(1 for iv in interventions if iv.status == "completed")
        pending_count = sum(1 for iv in interventions if iv.status not in ("completed", "cancelled"))

        total_interventions += total
        total_accepted += accepted

        by_building.append(
            BuildingAcceptanceSummary(
                building_id=bld.id,
                address=bld.address or "",
                acceptance_rate=accepted / total if total > 0 else 0.0,
                pending_checks=pending_count,
            )
        )

    overall_rate = total_accepted / total_interventions if total_interventions > 0 else 0.0

    # Generate trend placeholders for last 4 quarters
    now = datetime.now(UTC)
    trends: list[QualityTrend] = []
    for i in range(4):
        quarter = ((now.month - 1) // 3) + 1 - i
        year = now.year
        while quarter < 1:
            quarter += 4
            year -= 1
        trends.append(
            QualityTrend(
                period=f"{year}-Q{quarter}",
                pass_rate=overall_rate,
                total_checks=total_interventions,
                failed_checks=total_interventions - total_accepted,
            )
        )

    return PortfolioQualityDashboard(
        organization_id=org_id,
        total_interventions=total_interventions,
        overall_acceptance_rate=overall_rate,
        by_building=by_building,
        trends=trends,
        generated_at=now,
    )
