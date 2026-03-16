"""
SwissBuildingOS - Priority Matrix Service

Provides Eisenhower-style urgency x impact classification of actions and
interventions for a building, critical-path extraction, quick-win detection,
and portfolio-level priority aggregation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.priority_matrix import (
    BuildingPrioritySummary,
    CriticalPath,
    CriticalPathItem,
    MatrixCell,
    MatrixItem,
    PortfolioPriorityOverview,
    PriorityMatrix,
    QuickWinItem,
    QuickWins,
)
from app.services.building_data_loader import load_org_buildings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

URGENCY_LEVELS = ("immediate", "short_term", "medium_term", "long_term")
IMPACT_LEVELS = ("critical", "high", "medium", "low")

# Priority -> urgency mapping for actions
_PRIORITY_TO_URGENCY: dict[str, str] = {
    "critical": "immediate",
    "high": "short_term",
    "medium": "medium_term",
    "low": "long_term",
}

# Status -> urgency adjustment
_STATUS_URGENCY_BOOST: dict[str, int] = {
    "open": 0,
    "in_progress": -1,  # slightly less urgent (already started)
    "completed": 3,  # push far down
    "closed": 3,
}

# Intervention status -> urgency mapping
_INTERVENTION_STATUS_TO_URGENCY: dict[str, str] = {
    "planned": "short_term",
    "in_progress": "immediate",
    "completed": "long_term",
    "cancelled": "long_term",
}

# Risk level -> impact mapping
_RISK_TO_IMPACT: dict[str, str] = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "unknown": "medium",
}

# Effort estimation (days) by action type
_ACTION_TYPE_EFFORT: dict[str, int] = {
    "immediate_encapsulation": 3,
    "removal_required": 14,
    "suva_notification": 1,
    "waste_classification": 2,
    "monitoring_required": 5,
    "remediation_plan": 10,
    "air_measurement": 3,
    "access_restriction": 1,
    "lab_analysis": 5,
    "further_investigation": 7,
}

DEFAULT_EFFORT_DAYS = 7


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _classify_action_urgency(action: ActionItem) -> str:
    """Determine urgency level for an action item."""
    base = _PRIORITY_TO_URGENCY.get(action.priority or "medium", "medium_term")

    # Due date override
    if action.due_date:
        days_until = (action.due_date - datetime.now(UTC).date()).days
        if days_until <= 0:
            return "immediate"
        if days_until <= 14:
            return "short_term"
        if days_until <= 90:
            return "medium_term"

    # Status adjustment
    if action.status in ("completed", "closed"):
        return "long_term"

    return base


def _classify_action_impact(action: ActionItem, samples: list[Sample]) -> str:
    """Determine impact level for an action item based on metadata and linked samples."""
    # Check action metadata for risk info
    meta = action.metadata_json or {}
    risk = meta.get("risk_level", "").lower()
    if risk in _RISK_TO_IMPACT:
        return _RISK_TO_IMPACT[risk]

    # Check linked sample risk
    if action.sample_id:
        for s in samples:
            if s.id == action.sample_id:
                sample_risk = (s.risk_level or "").lower()
                if sample_risk in _RISK_TO_IMPACT:
                    return _RISK_TO_IMPACT[sample_risk]
                if s.threshold_exceeded:
                    return "high"
                break

    # Fall back to priority-based impact
    priority_impact = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
    }
    return priority_impact.get(action.priority or "medium", "medium")


def _classify_intervention_urgency(intervention: Intervention) -> str:
    """Determine urgency level for an intervention."""
    base = _INTERVENTION_STATUS_TO_URGENCY.get(intervention.status or "planned", "medium_term")

    if intervention.date_start:
        days_until = (intervention.date_start - datetime.now(UTC).date()).days
        if days_until <= 0:
            return "immediate"
        if days_until <= 14:
            return "short_term"

    return base


def _classify_intervention_impact(intervention: Intervention) -> str:
    """Determine impact level for an intervention."""
    # Type-based classification
    high_impact_types = {"removal", "remediation", "demolition", "structural_repair", "decontamination"}
    medium_impact_types = {"encapsulation", "sealing", "renovation", "replacement"}
    low_impact_types = {"monitoring", "inspection", "maintenance", "cleaning"}

    itype = (intervention.intervention_type or "").lower()
    if itype in high_impact_types:
        return "critical"
    if itype in medium_impact_types:
        return "high"
    if itype in low_impact_types:
        return "low"
    return "medium"


def _estimate_effort(action: ActionItem) -> int:
    """Estimate effort in days for an action."""
    atype = (action.action_type or "").lower()
    return _ACTION_TYPE_EFFORT.get(atype, DEFAULT_EFFORT_DAYS)


def _build_matrix_item_from_action(action: ActionItem, samples: list[Sample]) -> MatrixItem:
    """Build a MatrixItem from an ActionItem."""
    urgency = _classify_action_urgency(action)
    impact = _classify_action_impact(action, samples)

    meta = action.metadata_json or {}
    pollutant = meta.get("pollutant_type")
    risk = meta.get("risk_level")

    return MatrixItem(
        id=action.id,
        item_type="action",
        title=action.title,
        description=action.description,
        urgency=urgency,
        impact=impact,
        priority=action.priority,
        status=action.status,
        due_date=str(action.due_date) if action.due_date else None,
        pollutant_type=pollutant,
        risk_level=risk,
    )


def _build_matrix_item_from_intervention(intervention: Intervention) -> MatrixItem:
    """Build a MatrixItem from an Intervention."""
    urgency = _classify_intervention_urgency(intervention)
    impact = _classify_intervention_impact(intervention)

    return MatrixItem(
        id=intervention.id,
        item_type="intervention",
        title=intervention.title,
        description=intervention.description,
        urgency=urgency,
        impact=impact,
        priority=None,
        status=intervention.status,
        due_date=str(intervention.date_start) if intervention.date_start else None,
        pollutant_type=None,
        risk_level=None,
    )


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------


async def _fetch_building_items(
    db: AsyncSession, building_id: UUID
) -> tuple[Building | None, list[ActionItem], list[Intervention], list[Sample]]:
    """Fetch building, actions, interventions, and samples."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None, [], [], []

    action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = list(action_result.scalars().all())

    intervention_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(intervention_result.scalars().all())

    # Fetch samples for impact classification
    from app.models.diagnostic import Diagnostic

    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())
    samples: list[Sample] = []
    if diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    return building, actions, interventions, samples


# ---------------------------------------------------------------------------
# FN1: build_priority_matrix
# ---------------------------------------------------------------------------


async def build_priority_matrix(db: AsyncSession, building_id: UUID) -> PriorityMatrix:
    """Build 2D urgency x impact matrix for a building's actions and interventions."""
    building, actions, interventions, samples = await _fetch_building_items(db, building_id)
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    # Classify all items
    matrix_items: list[MatrixItem] = []
    for action in actions:
        if action.status in ("completed", "closed"):
            continue
        matrix_items.append(_build_matrix_item_from_action(action, samples))

    for intervention in interventions:
        if intervention.status in ("completed", "cancelled"):
            continue
        matrix_items.append(_build_matrix_item_from_intervention(intervention))

    # Build cells
    cells: list[MatrixCell] = []
    summary: dict[str, int] = {}
    for urgency in URGENCY_LEVELS:
        for impact in IMPACT_LEVELS:
            cell_items = [m for m in matrix_items if m.urgency == urgency and m.impact == impact]
            cell = MatrixCell(
                urgency=urgency,
                impact=impact,
                items=cell_items,
                count=len(cell_items),
            )
            cells.append(cell)
            label = f"{urgency}_{impact}"
            summary[label] = len(cell_items)

    return PriorityMatrix(
        building_id=building_id,
        cells=cells,
        total_items=len(matrix_items),
        summary=summary,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: get_critical_path_items
# ---------------------------------------------------------------------------


async def get_critical_path_items(db: AsyncSession, building_id: UUID) -> CriticalPath:
    """Extract items in the urgent + critical quadrant with dependencies."""
    building, actions, interventions, samples = await _fetch_building_items(db, building_id)
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    critical_items: list[CriticalPathItem] = []

    for action in actions:
        if action.status in ("completed", "closed"):
            continue
        urgency = _classify_action_urgency(action)
        impact = _classify_action_impact(action, samples)
        if urgency == "immediate" and impact == "critical":
            deps = _determine_action_dependencies(action)
            reason = _determine_blocking_reason(action)
            days = _estimate_effort(action)
            critical_items.append(
                CriticalPathItem(
                    id=action.id,
                    item_type="action",
                    title=action.title,
                    description=action.description,
                    blocking_reason=reason,
                    dependencies=deps,
                    estimated_days=days,
                    priority=action.priority,
                    status=action.status,
                )
            )

    for intervention in interventions:
        if intervention.status in ("completed", "cancelled"):
            continue
        urgency = _classify_intervention_urgency(intervention)
        impact = _classify_intervention_impact(intervention)
        if urgency == "immediate" and impact == "critical":
            deps = _determine_intervention_dependencies(intervention)
            reason = f"Active {intervention.intervention_type} intervention requires immediate attention"
            days = 14 if intervention.date_start and intervention.date_end else 21
            if intervention.date_start and intervention.date_end:
                days = max(1, (intervention.date_end - intervention.date_start).days)
            critical_items.append(
                CriticalPathItem(
                    id=intervention.id,
                    item_type="intervention",
                    title=intervention.title,
                    description=intervention.description,
                    blocking_reason=reason,
                    dependencies=deps,
                    estimated_days=days,
                    priority=None,
                    status=intervention.status,
                )
            )

    total_days = sum(item.estimated_days for item in critical_items)

    return CriticalPath(
        building_id=building_id,
        items=critical_items,
        total_blocking=len(critical_items),
        estimated_total_days=total_days,
        evaluated_at=datetime.now(UTC),
    )


def _determine_action_dependencies(action: ActionItem) -> list[str]:
    """Determine dependencies for an action item."""
    deps: list[str] = []
    atype = (action.action_type or "").lower()

    if atype == "removal_required":
        deps.append("SUVA notification must be filed before work begins")
        deps.append("Waste disposal plan required")
    elif atype == "suva_notification":
        deps.append("Diagnostic report must be completed")
    elif atype == "remediation_plan":
        deps.append("All lab analyses must be completed")
        deps.append("Work category classification required")
    elif atype == "air_measurement":
        deps.append("Access to affected zones required")
    elif atype == "waste_classification":
        deps.append("Lab analysis results required")

    return deps


def _determine_blocking_reason(action: ActionItem) -> str:
    """Determine why an action is blocking."""
    atype = (action.action_type or "").lower()
    reasons = {
        "immediate_encapsulation": "Exposed hazardous material requires immediate containment",
        "removal_required": "Regulatory mandate for pollutant removal before renovation",
        "suva_notification": "Legal obligation to notify SUVA of asbestos presence",
        "waste_classification": "Waste must be classified before disposal can proceed",
        "access_restriction": "Occupant safety requires immediate access restriction",
        "remediation_plan": "Remediation plan needed before any work can begin",
    }
    return reasons.get(atype, f"Critical action '{action.title}' blocks downstream work")


def _determine_intervention_dependencies(intervention: Intervention) -> list[str]:
    """Determine dependencies for an intervention."""
    deps: list[str] = []
    itype = (intervention.intervention_type or "").lower()

    if itype in ("removal", "demolition", "decontamination"):
        deps.append("SUVA notification and work authorization required")
        deps.append("Contractor with appropriate certification required")
    elif itype in ("remediation", "structural_repair"):
        deps.append("Remediation plan approval required")
    elif itype == "encapsulation":
        deps.append("Material condition assessment required")

    return deps


# ---------------------------------------------------------------------------
# FN3: suggest_quick_wins
# ---------------------------------------------------------------------------


async def suggest_quick_wins(db: AsyncSession, building_id: UUID) -> QuickWins:
    """Find low-effort, high-impact items that can be done in <1 week."""
    building, actions, interventions, samples = await _fetch_building_items(db, building_id)
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    quick_wins: list[QuickWinItem] = []

    for action in actions:
        if action.status in ("completed", "closed"):
            continue
        effort = _estimate_effort(action)
        if effort > 7:
            continue  # Not a quick win

        impact = _classify_action_impact(action, samples)
        if impact in ("low",):
            continue  # Not high enough impact

        deps = _determine_action_dependencies(action)

        # Determine risk reduction level
        if impact == "critical":
            risk_reduction = "significant"
            cost_benefit = "Very high — critical risk eliminated with minimal effort"
        elif impact == "high":
            risk_reduction = "significant"
            cost_benefit = "High — major risk reduction for low effort"
        else:
            risk_reduction = "moderate"
            cost_benefit = "Good — meaningful risk reduction achievable quickly"

        quick_wins.append(
            QuickWinItem(
                id=action.id,
                item_type="action",
                title=action.title,
                description=action.description,
                effort_days=effort,
                risk_reduction=risk_reduction,
                cost_benefit=cost_benefit,
                dependencies=deps,
            )
        )

    for intervention in interventions:
        if intervention.status in ("completed", "cancelled"):
            continue
        itype = (intervention.intervention_type or "").lower()
        # Only short interventions qualify
        if itype not in ("monitoring", "inspection", "maintenance", "cleaning", "encapsulation", "sealing"):
            continue

        effort = 5 if itype in ("monitoring", "inspection", "cleaning") else 7
        impact = _classify_intervention_impact(intervention)
        if impact == "low":
            continue

        deps = _determine_intervention_dependencies(intervention)
        risk_reduction = "moderate" if impact in ("medium", "high") else "minor"
        cost_benefit = "Good — preventive measure with low cost" if effort <= 5 else "Moderate — worthwhile investment"

        quick_wins.append(
            QuickWinItem(
                id=intervention.id,
                item_type="intervention",
                title=intervention.title,
                description=intervention.description,
                effort_days=effort,
                risk_reduction=risk_reduction,
                cost_benefit=cost_benefit,
                dependencies=deps,
            )
        )

    # Sort: lowest effort first, then highest impact
    impact_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    quick_wins.sort(key=lambda qw: (qw.effort_days, impact_order.get(qw.risk_reduction, 2)))

    return QuickWins(
        building_id=building_id,
        items=quick_wins,
        total_quick_wins=len(quick_wins),
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_priority_overview
# ---------------------------------------------------------------------------


async def get_portfolio_priority_overview(db: AsyncSession, org_id: UUID) -> PortfolioPriorityOverview:
    """Org-level priority matrix aggregation across buildings."""
    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return _empty_portfolio_overview(org_id)

    # Aggregate across buildings
    quadrant_totals: dict[str, int] = {}
    for u in URGENCY_LEVELS:
        for i in IMPACT_LEVELS:
            quadrant_totals[f"{u}_{i}"] = 0

    building_summaries: list[BuildingPrioritySummary] = []
    total_items = 0

    for b in buildings:
        _bld, actions, interventions, samples = await _fetch_building_items(db, b.id)

        counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        building_total = 0

        for action in actions:
            if action.status in ("completed", "closed"):
                continue
            urgency = _classify_action_urgency(action)
            impact = _classify_action_impact(action, samples)
            key = f"{urgency}_{impact}"
            quadrant_totals[key] = quadrant_totals.get(key, 0) + 1
            counts[impact] = counts.get(impact, 0) + 1
            building_total += 1

        for intervention in interventions:
            if intervention.status in ("completed", "cancelled"):
                continue
            urgency = _classify_intervention_urgency(intervention)
            impact = _classify_intervention_impact(intervention)
            key = f"{urgency}_{impact}"
            quadrant_totals[key] = quadrant_totals.get(key, 0) + 1
            counts[impact] = counts.get(impact, 0) + 1
            building_total += 1

        total_items += building_total

        building_summaries.append(
            BuildingPrioritySummary(
                building_id=b.id,
                address=b.address,
                city=b.city,
                critical_count=counts["critical"],
                high_count=counts["high"],
                medium_count=counts["medium"],
                low_count=counts["low"],
                total_items=building_total,
            )
        )

    # Sort by critical items descending
    building_summaries.sort(key=lambda s: (s.critical_count, s.high_count, s.total_items), reverse=True)

    # Resource allocation recommendations
    recommendations = _generate_resource_recommendations(quadrant_totals, building_summaries)

    return PortfolioPriorityOverview(
        organization_id=org_id,
        building_count=len(buildings),
        quadrant_totals=quadrant_totals,
        buildings_most_critical=building_summaries[:10],
        resource_allocation=recommendations,
        total_items=total_items,
        evaluated_at=datetime.now(UTC),
    )


def _generate_resource_recommendations(
    quadrant_totals: dict[str, int],
    summaries: list[BuildingPrioritySummary],
) -> list[str]:
    """Generate resource allocation recommendations."""
    recs: list[str] = []

    immediate_critical = quadrant_totals.get("immediate_critical", 0)
    immediate_high = quadrant_totals.get("immediate_high", 0)

    if immediate_critical > 0:
        recs.append(
            f"URGENT: {immediate_critical} item(s) require immediate action on critical risks. "
            "Allocate dedicated resources now."
        )

    if immediate_high > 0:
        recs.append(
            f"HIGH PRIORITY: {immediate_high} item(s) need short-term attention. Schedule within the next 2 weeks."
        )

    # Buildings with most critical items
    critical_buildings = [s for s in summaries if s.critical_count > 0]
    if len(critical_buildings) > 3:
        recs.append(
            f"{len(critical_buildings)} buildings have critical items. "
            "Consider a dedicated task force for parallel remediation."
        )

    total_short = sum(v for k, v in quadrant_totals.items() if k.startswith("short_term"))
    if total_short > 10:
        recs.append(f"{total_short} short-term items pending. Plan capacity for the next 3 months to avoid escalation.")

    if not recs:
        recs.append("No urgent resource allocation changes needed. Continue regular monitoring.")

    return recs


def _empty_portfolio_overview(org_id: UUID) -> PortfolioPriorityOverview:
    """Return empty portfolio overview when no buildings found."""
    quadrant_totals: dict[str, int] = {}
    for u in URGENCY_LEVELS:
        for i in IMPACT_LEVELS:
            quadrant_totals[f"{u}_{i}"] = 0

    return PortfolioPriorityOverview(
        organization_id=org_id,
        building_count=0,
        quadrant_totals=quadrant_totals,
        buildings_most_critical=[],
        resource_allocation=["No buildings found for this organization."],
        total_items=0,
        evaluated_at=datetime.now(UTC),
    )
