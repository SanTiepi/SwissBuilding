"""
SwissBuildingOS - Remediation Tracking Service

Tracks pollutant remediation progress per building, estimates timelines,
monitors costs, and provides portfolio-wide remediation dashboards.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.remediation_tracking import (
    BuildingAtRiskOfDelay,
    BuildingCostTracker,
    BuildingRemediationStatus,
    BuildingRemediationTimeline,
    CostPhaseBreakdown,
    PollutantCostTracker,
    PollutantDistribution,
    PollutantTimeline,
    PortfolioRemediationDashboard,
    RemediationPollutantStatus,
)
from app.services.building_data_loader import load_org_buildings

# ---------------------------------------------------------------------------
# Cost estimates by pollutant (CHF) — aligned with risk_mitigation_planner
# ---------------------------------------------------------------------------

COST_ESTIMATES: dict[str, float] = {
    "asbestos": 50_000.0,
    "pcb": 40_000.0,
    "lead": 20_000.0,
    "hap": 25_000.0,
    "radon": 15_000.0,
}

DEFAULT_COST = 20_000.0

# Duration estimates in days by pollutant
DURATION_DAYS: dict[str, int] = {
    "asbestos": 28,
    "pcb": 21,
    "lead": 14,
    "hap": 21,
    "radon": 14,
}

DEFAULT_DURATION_DAYS = 21

# Dependency rules: blocker → blocked pollutants
DEPENDENCY_RULES: dict[str, list[str]] = {
    "asbestos": ["pcb", "lead", "hap"],
}

# Pollutants that can run in parallel (no dependency between them)
PARALLEL_PAIRS: set[frozenset[str]] = {
    frozenset({"radon", "asbestos"}),
    frozenset({"radon", "pcb"}),
    frozenset({"radon", "lead"}),
    frozenset({"radon", "hap"}),
    frozenset({"pcb", "lead"}),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_building(db: AsyncSession, building_id: UUID) -> Building:
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _fetch_pollutant_types_with_issues(db: AsyncSession, building_id: UUID) -> dict[str, list[Sample]]:
    """Return positive samples grouped by pollutant_type from completed/validated diagnostics."""
    stmt = (
        select(Sample)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
            Sample.threshold_exceeded.is_(True),
        )
    )
    result = await db.execute(stmt)
    samples = result.scalars().all()
    grouped: dict[str, list[Sample]] = {}
    for s in samples:
        pt = s.pollutant_type
        if pt:
            grouped.setdefault(pt, []).append(s)
    return grouped


async def _fetch_interventions(db: AsyncSession, building_id: UUID) -> list[Intervention]:
    stmt = select(Intervention).where(Intervention.building_id == building_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _fetch_actions(db: AsyncSession, building_id: UUID) -> list[ActionItem]:
    stmt = select(ActionItem).where(ActionItem.building_id == building_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _count_zones(db: AsyncSession, building_id: UUID) -> int:
    stmt = select(func.count()).select_from(Zone).where(Zone.building_id == building_id)
    result = await db.execute(stmt)
    return result.scalar() or 0


def _intervention_covers_pollutant(intervention: Intervention, pollutant_type: str) -> bool:
    it = (intervention.intervention_type or "").lower()
    return pollutant_type.lower() in it


def _determine_status(
    pollutant_type: str,
    interventions: list[Intervention],
    actions: list[ActionItem],
) -> str:
    """Determine remediation status for a pollutant."""
    relevant_interventions = [iv for iv in interventions if _intervention_covers_pollutant(iv, pollutant_type)]

    # Check for verified (completed intervention + completed/closed actions)
    completed_interventions = [iv for iv in relevant_interventions if iv.status == "completed"]
    if completed_interventions:
        relevant_actions = [a for a in actions if (a.metadata_json or {}).get("pollutant_type") == pollutant_type]
        all_actions_done = all(a.status in ("completed", "closed") for a in relevant_actions)
        if all_actions_done:
            return "verified"
        return "completed"

    # Check for in_progress interventions
    in_progress = [iv for iv in relevant_interventions if iv.status == "in_progress"]
    if in_progress:
        return "in_progress"

    # Check for planned interventions
    planned = [iv for iv in relevant_interventions if iv.status == "planned"]
    if planned:
        return "pending"

    # Check for open action items
    relevant_actions = [
        a
        for a in actions
        if (a.metadata_json or {}).get("pollutant_type") == pollutant_type and a.status in ("open", "in_progress")
    ]
    if relevant_actions:
        return "pending"

    return "pending"


def _get_blocking_issues(
    pollutant_type: str,
    actions: list[ActionItem],
) -> list[str]:
    """Identify blocking issues for a pollutant."""
    issues: list[str] = []
    today = date.today()

    for a in actions:
        meta = a.metadata_json or {}
        if meta.get("pollutant_type") != pollutant_type:
            continue
        if a.status not in ("open", "in_progress"):
            continue

        if a.due_date and a.due_date < today:
            issues.append(f"Overdue action: {a.title}")
        elif a.priority in ("critical", "high"):
            issues.append(f"High-priority action pending: {a.title}")

    return issues


def _count_affected_zones_for_pollutant(samples: list[Sample], total_zones: int) -> int:
    """Count distinct zones affected based on sample locations."""
    locations = set()
    for s in samples:
        loc = s.location_detail or s.location_floor or s.location_room
        if loc:
            locations.add(loc)
    # At minimum 1 if there are samples, capped at total_zones
    return min(max(len(locations), 1 if samples else 0), max(total_zones, 1))


def _count_remediated_zones(
    pollutant_type: str,
    interventions: list[Intervention],
    affected: int,
) -> int:
    """Estimate remediated zones from completed interventions."""
    completed = [
        iv for iv in interventions if _intervention_covers_pollutant(iv, pollutant_type) and iv.status == "completed"
    ]
    if not completed:
        return 0
    # If there are completed interventions, assume they covered proportional zones
    return affected


# ---------------------------------------------------------------------------
# FN1: get_remediation_status
# ---------------------------------------------------------------------------


async def get_remediation_status(building_id: UUID, db: AsyncSession) -> BuildingRemediationStatus:
    """Per-pollutant remediation progress for a building."""
    await _fetch_building(db, building_id)
    grouped = await _fetch_pollutant_types_with_issues(db, building_id)
    interventions = await _fetch_interventions(db, building_id)
    actions = await _fetch_actions(db, building_id)
    total_zones = await _count_zones(db, building_id)

    pollutants: list[RemediationPollutantStatus] = []

    for pollutant_type, samples in grouped.items():
        status = _determine_status(pollutant_type, interventions, actions)
        affected = _count_affected_zones_for_pollutant(samples, total_zones)
        remediated = _count_remediated_zones(pollutant_type, interventions, affected)
        progress = (remediated / affected * 100.0) if affected > 0 else 0.0
        blocking = _get_blocking_issues(pollutant_type, actions)

        pollutants.append(
            RemediationPollutantStatus(
                pollutant_type=pollutant_type,
                status=status,
                affected_zones=affected,
                remediated_zones=remediated,
                progress_percentage=round(progress, 1),
                blocking_issues=blocking,
            )
        )

    overall = 0.0
    if pollutants:
        overall = round(sum(p.progress_percentage for p in pollutants) / len(pollutants), 1)

    return BuildingRemediationStatus(
        building_id=building_id,
        pollutants=pollutants,
        overall_progress_percentage=overall,
    )


# ---------------------------------------------------------------------------
# FN2: estimate_remediation_timeline
# ---------------------------------------------------------------------------


async def estimate_remediation_timeline(building_id: UUID, db: AsyncSession) -> BuildingRemediationTimeline:
    """Estimated remediation dates per pollutant based on interventions and actions."""
    await _fetch_building(db, building_id)
    grouped = await _fetch_pollutant_types_with_issues(db, building_id)
    interventions = await _fetch_interventions(db, building_id)

    timelines: list[PollutantTimeline] = []
    today = date.today()

    # Determine order: blockers first
    ordered_pollutants = _order_by_dependencies(list(grouped.keys()))

    pollutant_end_dates: dict[str, date] = {}
    current_start = today

    for pollutant_type in ordered_pollutants:
        # Find existing interventions with dates
        relevant = [iv for iv in interventions if _intervention_covers_pollutant(iv, pollutant_type)]

        duration = DURATION_DAYS.get(pollutant_type, DEFAULT_DURATION_DAYS)

        # Check dependencies
        deps: list[str] = []
        for blocker, blocked_list in DEPENDENCY_RULES.items():
            if pollutant_type in blocked_list and blocker in grouped:
                deps.append(blocker)

        # Determine if parallel execution is possible
        parallel = _is_parallel_possible(pollutant_type, list(grouped.keys()))

        # Calculate start date based on dependencies
        if deps:
            dep_end_dates = [pollutant_end_dates.get(d, today) for d in deps]
            estimated_start = max(dep_end_dates) if dep_end_dates else current_start
        else:
            estimated_start = current_start

        # Use actual intervention dates if available
        planned_or_in_progress = [iv for iv in relevant if iv.status in ("planned", "in_progress")]
        if planned_or_in_progress:
            iv = planned_or_in_progress[0]
            if iv.date_start:
                estimated_start = iv.date_start
            if iv.date_end:
                duration = max((iv.date_end - estimated_start).days, 1)

        estimated_completion = estimated_start + timedelta(days=duration)
        pollutant_end_dates[pollutant_type] = estimated_completion

        # If not parallel, next sequential item starts after this one
        if not parallel:
            current_start = estimated_completion

        timelines.append(
            PollutantTimeline(
                pollutant_type=pollutant_type,
                estimated_start=estimated_start,
                estimated_completion=estimated_completion,
                duration_days=duration,
                dependencies=deps,
                parallel_possible=parallel,
            )
        )

    return BuildingRemediationTimeline(
        building_id=building_id,
        timelines=timelines,
    )


def _order_by_dependencies(pollutant_types: list[str]) -> list[str]:
    """Order pollutants so blockers come first."""
    ordered: list[str] = []
    remaining = set(pollutant_types)

    # First pass: add blockers
    for blocker in DEPENDENCY_RULES:
        if blocker in remaining:
            ordered.append(blocker)
            remaining.discard(blocker)

    # Second pass: add the rest
    for pt in pollutant_types:
        if pt in remaining:
            ordered.append(pt)
            remaining.discard(pt)

    return ordered


def _is_parallel_possible(pollutant_type: str, all_pollutants: list[str]) -> bool:
    """Check if this pollutant can be remediated in parallel with others."""
    for other in all_pollutants:
        if other == pollutant_type:
            continue
        if frozenset({pollutant_type, other}) in PARALLEL_PAIRS:
            return True
    return False


# ---------------------------------------------------------------------------
# FN3: get_remediation_cost_tracker
# ---------------------------------------------------------------------------


async def get_remediation_cost_tracker(building_id: UUID, db: AsyncSession) -> BuildingCostTracker:
    """Cost tracking per pollutant for a building."""
    await _fetch_building(db, building_id)
    grouped = await _fetch_pollutant_types_with_issues(db, building_id)
    interventions = await _fetch_interventions(db, building_id)

    costs: list[PollutantCostTracker] = []
    total_estimated = 0.0
    total_actual = 0.0

    for pollutant_type in grouped:
        estimated = COST_ESTIMATES.get(pollutant_type, DEFAULT_COST)

        # Sum actual costs from completed interventions
        actual = 0.0
        phases: list[CostPhaseBreakdown] = []
        relevant = [iv for iv in interventions if _intervention_covers_pollutant(iv, pollutant_type)]

        for iv in relevant:
            phase_name = iv.status or "unknown"
            phase_cost = iv.cost_chf or 0.0
            if iv.status == "completed":
                actual += phase_cost
            phases.append(
                CostPhaseBreakdown(
                    phase=f"{iv.intervention_type or pollutant_type}_{phase_name}",
                    estimated_cost=estimated / max(len(relevant), 1),
                    actual_cost=phase_cost,
                )
            )

        # If no interventions, add a single planned phase
        if not phases:
            phases.append(
                CostPhaseBreakdown(
                    phase=f"{pollutant_type}_planned",
                    estimated_cost=estimated,
                    actual_cost=0.0,
                )
            )

        variance = 0.0
        if estimated > 0:
            variance = round((actual - estimated) / estimated * 100.0, 1)

        if actual > estimated * 1.1:
            budget_status = "over"
        elif actual < estimated * 0.9 and actual > 0:
            budget_status = "under"
        else:
            budget_status = "on_track"

        total_estimated += estimated
        total_actual += actual

        costs.append(
            PollutantCostTracker(
                pollutant_type=pollutant_type,
                estimated_cost=estimated,
                actual_cost=actual,
                variance_percentage=variance,
                budget_status=budget_status,
                breakdown_by_phase=phases,
            )
        )

    return BuildingCostTracker(
        building_id=building_id,
        costs=costs,
        total_estimated=round(total_estimated, 2),
        total_actual=round(total_actual, 2),
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_remediation_dashboard
# ---------------------------------------------------------------------------


async def get_portfolio_remediation_dashboard(org_id: UUID, db: AsyncSession) -> PortfolioRemediationDashboard:
    """Organization-wide remediation dashboard."""
    all_buildings = await load_org_buildings(db, org_id)
    buildings = [b for b in all_buildings if b.status == "active"]

    if not buildings:
        return PortfolioRemediationDashboard(
            organization_id=org_id,
            total_buildings_needing_remediation=0,
            by_pollutant_type=[],
            overall_progress_pct=0.0,
            estimated_total_cost=0.0,
            buildings_at_risk_of_delay=[],
        )

    buildings_needing_remediation = 0
    pollutant_stats: dict[str, dict] = {}
    all_progress: list[float] = []
    total_cost = 0.0
    at_risk: list[BuildingAtRiskOfDelay] = []
    today = date.today()

    for building in buildings:
        grouped = await _fetch_pollutant_types_with_issues(db, building.id)
        if not grouped:
            continue

        buildings_needing_remediation += 1
        interventions = await _fetch_interventions(db, building.id)
        actions = await _fetch_actions(db, building.id)
        total_zones = await _count_zones(db, building.id)

        building_progress: list[float] = []
        building_blocking: list[str] = []

        for pollutant_type, samples in grouped.items():
            # Aggregate pollutant distribution
            if pollutant_type not in pollutant_stats:
                pollutant_stats[pollutant_type] = {"count": 0, "progress_sum": 0.0}
            pollutant_stats[pollutant_type]["count"] += 1

            affected = _count_affected_zones_for_pollutant(samples, total_zones)
            remediated = _count_remediated_zones(pollutant_type, interventions, affected)
            progress = (remediated / affected * 100.0) if affected > 0 else 0.0
            building_progress.append(progress)
            pollutant_stats[pollutant_type]["progress_sum"] += progress

            # Check for blocking
            blocking = _get_blocking_issues(pollutant_type, actions)
            if blocking:
                building_blocking.append(pollutant_type)

            # Cost
            total_cost += COST_ESTIMATES.get(pollutant_type, DEFAULT_COST)

        avg_progress = sum(building_progress) / len(building_progress) if building_progress else 0.0
        all_progress.append(avg_progress)

        # Check overdue actions
        overdue_count = sum(
            1 for a in actions if a.status in ("open", "in_progress") and a.due_date and a.due_date < today
        )

        if overdue_count > 0 or building_blocking:
            at_risk.append(
                BuildingAtRiskOfDelay(
                    building_id=building.id,
                    address=building.address,
                    overdue_actions=overdue_count,
                    blocking_pollutants=building_blocking,
                )
            )

    overall_progress = round(sum(all_progress) / len(all_progress), 1) if all_progress else 0.0

    by_pollutant = [
        PollutantDistribution(
            pollutant_type=pt,
            building_count=stats["count"],
            avg_progress=round(stats["progress_sum"] / stats["count"], 1) if stats["count"] > 0 else 0.0,
        )
        for pt, stats in pollutant_stats.items()
    ]

    return PortfolioRemediationDashboard(
        organization_id=org_id,
        total_buildings_needing_remediation=buildings_needing_remediation,
        by_pollutant_type=by_pollutant,
        overall_progress_pct=overall_progress,
        estimated_total_cost=round(total_cost, 2),
        buildings_at_risk_of_delay=at_risk,
    )
