"""Stakeholder-specific dashboard services.

Each function returns an aggregate read-model tailored to a specific user role:
owner, diagnostician, authority, contractor.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.contractor_acknowledgment import ContractorAcknowledgment
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.schemas.stakeholder_dashboard import (
    AuthorityDashboard,
    BuildingAttentionItem,
    ContractorDashboard,
    DiagnosticianDashboard,
    InterventionSummaryItem,
    OwnerDashboard,
    UpcomingDeadline,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _worst_risk(levels: list[str | None]) -> str | None:
    """Return the worst risk level from a list."""
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
    worst: str | None = None
    worst_score = -1
    for lvl in levels:
        if lvl is None:
            continue
        score = order.get(lvl, 0)
        if score > worst_score:
            worst_score = score
            worst = lvl
    return worst


# ---------------------------------------------------------------------------
# FN1 — Owner dashboard
# ---------------------------------------------------------------------------


async def get_owner_dashboard(db: AsyncSession, user_id: UUID) -> OwnerDashboard:
    """Property owner view: buildings owned, risk overview, deadlines, costs."""

    # Buildings owned by this user (owner_id) or created_by
    building_result = await db.execute(
        select(Building).where((Building.owner_id == user_id) | (Building.created_by == user_id))
    )
    buildings = list(building_result.scalars().all())
    building_ids = [b.id for b in buildings]

    if not building_ids:
        return OwnerDashboard()

    # Overall risk status — from BuildingRiskScore
    risk_result = await db.execute(
        select(BuildingRiskScore.building_id, BuildingRiskScore.overall_risk_level).where(
            BuildingRiskScore.building_id.in_(building_ids)
        )
    )
    risk_rows = risk_result.all()
    risk_by_building: dict[UUID, str] = {r[0]: r[1] for r in risk_rows}
    overall_risk = _worst_risk(list(risk_by_building.values()))

    # Upcoming deadlines (next 30 days)
    today = date.today()
    deadline_cutoff = today + timedelta(days=30)
    deadline_result = await db.execute(
        select(ActionItem)
        .where(
            ActionItem.building_id.in_(building_ids),
            ActionItem.due_date.isnot(None),
            ActionItem.due_date >= today,
            ActionItem.due_date <= deadline_cutoff,
            ActionItem.status.in_(("open", "in_progress")),
        )
        .order_by(ActionItem.due_date)
        .limit(20)
    )
    deadline_actions = list(deadline_result.scalars().all())
    upcoming_deadlines = [
        UpcomingDeadline(
            action_id=a.id,
            building_id=a.building_id,
            title=a.title,
            due_date=a.due_date,
            priority=a.priority,
        )
        for a in deadline_actions
    ]

    # Pending actions count
    pending_result = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .where(
            ActionItem.building_id.in_(building_ids),
            ActionItem.status.in_(("open", "in_progress")),
        )
    )
    pending_actions = pending_result.scalar() or 0

    # Total estimated cost from interventions (planned/in_progress)
    cost_result = await db.execute(
        select(func.coalesce(func.sum(Intervention.cost_chf), 0.0))
        .select_from(Intervention)
        .where(
            Intervention.building_id.in_(building_ids),
            Intervention.status.in_(("planned", "in_progress")),
        )
    )
    total_cost = float(cost_result.scalar() or 0.0)

    # Buildings needing attention (critical/high risk)
    attention_items: list[BuildingAttentionItem] = []
    for b in buildings:
        rl = risk_by_building.get(b.id)
        if rl in ("critical", "high"):
            attention_items.append(
                BuildingAttentionItem(
                    building_id=b.id,
                    address=b.address,
                    city=b.city,
                    risk_level=rl,
                    reason=f"Risk level: {rl}",
                )
            )

    return OwnerDashboard(
        buildings_count=len(buildings),
        overall_risk_status=overall_risk,
        upcoming_deadlines=upcoming_deadlines,
        pending_actions=pending_actions,
        total_estimated_cost=total_cost,
        buildings_needing_attention=attention_items,
    )


# ---------------------------------------------------------------------------
# FN2 — Diagnostician dashboard
# ---------------------------------------------------------------------------


async def get_diagnostician_dashboard(db: AsyncSession, user_id: UUID) -> DiagnosticianDashboard:
    """Diagnostician view: assigned work, quality, validation backlog."""

    # Diagnostics assigned to this user
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.diagnostician_id == user_id))
    diagnostics = list(diag_result.scalars().all())

    # Unique buildings from those diagnostics
    assigned_building_ids = {d.building_id for d in diagnostics}

    # In-progress count
    in_progress = sum(1 for d in diagnostics if d.status == "in_progress")

    # Completed this month
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    completed_this_month = sum(
        1
        for d in diagnostics
        if d.status in ("completed", "validated")
        and d.updated_at is not None
        and d.updated_at >= month_start.replace(tzinfo=None)
    )

    # Quality score avg — from BuildingRiskScore confidence as proxy
    quality_score: float | None = None
    if assigned_building_ids:
        quality_result = await db.execute(
            select(func.avg(BuildingRiskScore.confidence)).where(
                BuildingRiskScore.building_id.in_(list(assigned_building_ids))
            )
        )
        avg_val = quality_result.scalar()
        if avg_val is not None:
            quality_score = round(float(avg_val), 2)

    # Pending validations (completed but not validated)
    pending_validations = sum(1 for d in diagnostics if d.status == "completed")

    # Workload forecast (draft diagnostics)
    workload = sum(1 for d in diagnostics if d.status == "draft")

    return DiagnosticianDashboard(
        assigned_buildings=len(assigned_building_ids),
        diagnostics_in_progress=in_progress,
        completed_this_month=completed_this_month,
        quality_score_avg=quality_score,
        pending_validations=pending_validations,
        workload_forecast=workload,
    )


# ---------------------------------------------------------------------------
# FN3 — Authority dashboard
# ---------------------------------------------------------------------------


async def get_authority_dashboard(db: AsyncSession, user_id: UUID) -> AuthorityDashboard:
    """Authority view: jurisdiction buildings, compliance, approval queue."""

    # All buildings visible to authority (all buildings — authority sees everything)
    building_count_result = await db.execute(select(func.count()).select_from(Building))
    buildings_total = building_count_result.scalar() or 0

    # Pending submissions: diagnostics in completed status awaiting validation
    pending_result = await db.execute(
        select(func.count()).select_from(Diagnostic).where(Diagnostic.status == "completed")
    )
    pending_submissions = pending_result.scalar() or 0

    # Overdue compliance items: actions past due_date that are still open
    today = date.today()
    overdue_result = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .where(
            ActionItem.due_date.isnot(None),
            ActionItem.due_date < today,
            ActionItem.status.in_(("open", "in_progress")),
        )
    )
    overdue_count = overdue_result.scalar() or 0

    # Buildings with critical risk
    critical_result = await db.execute(
        select(func.count()).select_from(BuildingRiskScore).where(BuildingRiskScore.overall_risk_level == "critical")
    )
    critical_count = critical_result.scalar() or 0

    # Approval queue: diagnostics pending validation
    approval_result = await db.execute(
        select(func.count()).select_from(Diagnostic).where(Diagnostic.status == "completed")
    )
    approval_queue = approval_result.scalar() or 0

    return AuthorityDashboard(
        buildings_in_jurisdiction=buildings_total,
        pending_submissions=pending_submissions,
        overdue_compliance_items=overdue_count,
        buildings_with_critical_risk=critical_count,
        approval_queue=approval_queue,
    )


# ---------------------------------------------------------------------------
# FN4 — Contractor dashboard
# ---------------------------------------------------------------------------


async def get_contractor_dashboard(db: AsyncSession, user_id: UUID) -> ContractorDashboard:
    """Contractor view: assigned interventions, work status, certifications."""

    # Interventions assigned to this contractor
    interv_result = await db.execute(select(Intervention).where(Intervention.contractor_id == user_id))
    interventions = list(interv_result.scalars().all())

    total_assigned = len(interventions)
    in_progress = sum(1 for i in interventions if i.status == "in_progress")

    # Completed this month
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    completed_this_month = sum(
        1
        for i in interventions
        if i.status == "completed" and i.updated_at is not None and i.updated_at >= month_start.replace(tzinfo=None)
    )

    # Upcoming starts (planned, with date_start in future, limit 10)
    today = date.today()
    upcoming = sorted(
        [i for i in interventions if i.status == "planned" and i.date_start is not None and i.date_start >= today],
        key=lambda i: i.date_start,
    )[:10]
    upcoming_starts = [
        InterventionSummaryItem(
            intervention_id=i.id,
            building_id=i.building_id,
            title=i.title,
            status=i.status,
            date_start=i.date_start,
            date_end=i.date_end,
        )
        for i in upcoming
    ]

    # Acknowledgment status
    ack_result = await db.execute(
        select(
            ContractorAcknowledgment.status,
            func.count(),
        )
        .where(ContractorAcknowledgment.contractor_user_id == user_id)
        .group_by(ContractorAcknowledgment.status)
    )
    ack_rows = ack_result.all()
    ack_status: dict[str, int] = {row[0]: row[1] for row in ack_rows}

    # Required certifications = pending acknowledgments
    required_certs = ack_status.get("pending", 0)

    return ContractorDashboard(
        assigned_interventions=total_assigned,
        in_progress_works=in_progress,
        completed_this_month=completed_this_month,
        upcoming_starts=upcoming_starts,
        required_certifications=required_certs,
        acknowledgment_status=ack_status,
    )
