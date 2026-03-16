"""
SwissBuildingOS - Portfolio Optimization Service

Prioritize buildings for intervention, allocate budgets optimally,
and identify highest-leverage actions across a portfolio.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.schemas.portfolio_optimization import (
    BudgetAllocationResult,
    BuildingActionRecommendation,
    BuildingBudgetAllocation,
    BuildingPriority,
    PortfolioActionPlan,
    PortfolioPrioritization,
    RiskDistributionAnalysis,
)

# ---------------------------------------------------------------------------
# Pollutant severity weights (higher = worse)
# ---------------------------------------------------------------------------
POLLUTANT_SEVERITY: dict[str, float] = {
    "asbestos": 1.0,
    "pcb": 0.8,
    "lead": 0.7,
    "hap": 0.6,
    "radon": 0.5,
}

# Priority weights for action urgency
PRIORITY_WEIGHT: dict[str, float] = {
    "critical": 4.0,
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
}

# Cost estimate per priority level (CHF)
ESTIMATED_COST_PER_PRIORITY: dict[str, float] = {
    "critical": 50_000.0,
    "high": 30_000.0,
    "medium": 15_000.0,
    "low": 5_000.0,
}

# Timeline estimate per priority level (weeks)
TIMELINE_PER_PRIORITY: dict[str, int] = {
    "critical": 2,
    "high": 4,
    "medium": 8,
    "low": 12,
}

# Building type impact multiplier (residential = higher occupant risk)
BUILDING_TYPE_IMPACT: dict[str, float] = {
    "residential": 1.0,
    "mixed": 0.85,
    "commercial": 0.7,
    "industrial": 0.6,
    "public": 0.9,
}


# ---------------------------------------------------------------------------
# Internal scoring helpers
# ---------------------------------------------------------------------------


def _construction_year_risk(year: int | None) -> float:
    """Return a 0-100 risk factor based on construction year."""
    if year is None:
        return 50.0
    if year < 1920:
        return 30.0
    if year < 1940:
        return 45.0
    if year < 1960:
        return 70.0
    if year < 1980:
        return 90.0
    if year < 1990:
        return 60.0
    if year < 2000:
        return 30.0
    return 10.0


def _compute_risk_score(
    diagnostic_count: int,
    pollutant_types: list[str],
    construction_year: int | None,
) -> float:
    """Compute risk score 0-100 from diagnostics and construction year."""
    year_risk = _construction_year_risk(construction_year)

    # Pollutant severity contribution (up to 50 points)
    severity_sum = sum(POLLUTANT_SEVERITY.get(p, 0.5) for p in pollutant_types)
    pollutant_score = min(severity_sum * 15.0, 50.0)

    # Diagnostic count contribution (up to 20 points)
    diag_score = min(diagnostic_count * 5.0, 20.0)

    # Weighted combination
    raw = 0.4 * year_risk + 0.4 * pollutant_score + 0.2 * diag_score
    return min(round(raw, 2), 100.0)


def _compute_urgency_score(
    pending_actions: int,
    overdue_actions: int,
    critical_actions: int,
) -> float:
    """Compute urgency score 0-100 from action items."""
    if pending_actions == 0:
        return 0.0
    raw = min(pending_actions * 8.0, 40.0) + min(overdue_actions * 15.0, 40.0) + min(critical_actions * 10.0, 20.0)
    return min(round(raw, 2), 100.0)


def _compute_impact_score(
    surface_area: float | None,
    building_type: str,
) -> float:
    """Compute impact score 0-100 based on surface and building type."""
    # Surface contribution: log-scale, cap at 70 points
    area = surface_area or 100.0
    surface_score = min(area / 50.0, 70.0)

    # Building type contribution: up to 30 points
    type_mult = BUILDING_TYPE_IMPACT.get(building_type, 0.5)
    type_score = type_mult * 30.0

    return min(round(surface_score + type_score, 2), 100.0)


def _compute_roi_score(risk_score: float, estimated_cost: float) -> float:
    """Estimate risk-reduction per CHF (higher = better ROI)."""
    if estimated_cost <= 0:
        return 0.0
    return round(risk_score / (estimated_cost / 10_000.0), 2)


def _combined_score(
    risk: float,
    urgency: float,
    impact: float,
    roi: float,
) -> float:
    return round(0.4 * risk + 0.3 * urgency + 0.2 * impact + 0.1 * roi, 2)


def _estimate_building_cost(actions: list[ActionItem]) -> float:
    """Estimate total remediation cost for a building based on action priorities."""
    if not actions:
        return 5_000.0  # baseline inspection cost
    return sum(ESTIMATED_COST_PER_PRIORITY.get(a.priority, 10_000.0) for a in actions)


def _estimate_timeline_weeks(actions: list[ActionItem]) -> int:
    """Estimate max timeline across actions (parallel execution)."""
    if not actions:
        return 4
    return max(TIMELINE_PER_PRIORITY.get(a.priority, 8) for a in actions)


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


async def _load_buildings_with_data(
    db: AsyncSession,
    org_id: UUID | None = None,
    building_ids: list[UUID] | None = None,
) -> list[dict]:
    """Load buildings with their diagnostics and action items."""
    query = select(Building).where(Building.status == "active")
    if building_ids:
        query = query.where(Building.id.in_(building_ids))

    result = await db.execute(query)
    buildings = result.scalars().all()

    enriched = []
    for b in buildings:
        # Load diagnostics
        diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == b.id))
        diagnostics = diag_result.scalars().all()

        # Load action items
        action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == b.id))
        actions = action_result.scalars().all()

        pollutant_types = list({d.diagnostic_type for d in diagnostics})
        pending_actions = [a for a in actions if a.status in ("open", "in_progress")]
        overdue_actions = [a for a in actions if a.status == "overdue"]
        critical_actions = [a for a in actions if a.priority == "critical"]

        risk = _compute_risk_score(len(diagnostics), pollutant_types, b.construction_year)
        urgency = _compute_urgency_score(len(pending_actions), len(overdue_actions), len(critical_actions))
        impact = _compute_impact_score(b.surface_area_m2, b.building_type)
        cost = _estimate_building_cost(list(actions))
        roi = _compute_roi_score(risk, cost)
        combined = _combined_score(risk, urgency, impact, roi)

        enriched.append(
            {
                "building": b,
                "diagnostics": diagnostics,
                "actions": actions,
                "pollutant_types": pollutant_types,
                "risk_score": risk,
                "urgency_score": urgency,
                "impact_score": impact,
                "roi_score": roi,
                "combined_score": combined,
                "estimated_cost": cost,
                "timeline_weeks": _estimate_timeline_weeks(list(actions)),
            }
        )

    # Sort by combined score descending
    enriched.sort(key=lambda x: x["combined_score"], reverse=True)
    return enriched


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def prioritize_buildings(
    db: AsyncSession,
    org_id: UUID | None = None,
    budget_chf: float | None = None,
) -> PortfolioPrioritization:
    """Rank buildings by priority and optionally allocate a budget."""
    enriched = await _load_buildings_with_data(db, org_id)

    total_cost = sum(e["estimated_cost"] for e in enriched)

    prioritized: list[BuildingPriority] = []
    for rank, entry in enumerate(enriched, start=1):
        b = entry["building"]
        rec_budget = None
        if budget_chf and total_cost > 0:
            proportion = entry["combined_score"] / max(sum(e["combined_score"] for e in enriched), 1.0)
            rec_budget = round(budget_chf * proportion, 2)

        prioritized.append(
            BuildingPriority(
                building_id=b.id,
                address=b.address,
                city=b.city,
                canton=b.canton,
                risk_score=entry["risk_score"],
                urgency_score=entry["urgency_score"],
                impact_score=entry["impact_score"],
                roi_score=entry["roi_score"],
                combined_score=entry["combined_score"],
                rank=rank,
                recommended_budget_chf=rec_budget,
            )
        )

    coverage = None
    if budget_chf and total_cost > 0:
        coverage = round(min(budget_chf / total_cost * 100, 100.0), 2)

    return PortfolioPrioritization(
        total_buildings=len(prioritized),
        total_estimated_cost_chf=round(total_cost, 2),
        budget_chf=budget_chf,
        prioritized_buildings=prioritized,
        budget_coverage_percent=coverage,
    )


async def get_portfolio_action_plan(
    db: AsyncSession,
    org_id: UUID | None = None,
    max_buildings: int = 10,
) -> PortfolioActionPlan:
    """Return top N buildings with recommended actions."""
    enriched = await _load_buildings_with_data(db, org_id)
    top = enriched[:max_buildings]

    plan: list[BuildingActionRecommendation] = []
    total_cost = 0.0
    max_timeline = 0

    for rank, entry in enumerate(top, start=1):
        b = entry["building"]
        actions = entry["actions"]
        rec_actions = [a.title for a in actions if a.status in ("open", "in_progress")]
        if not rec_actions:
            rec_actions = ["Schedule initial diagnostic assessment"]

        cost = entry["estimated_cost"]
        total_cost += cost
        timeline = entry["timeline_weeks"]
        max_timeline = max(max_timeline, timeline)

        plan.append(
            BuildingActionRecommendation(
                building_id=b.id,
                address=b.address,
                recommended_actions=rec_actions,
                estimated_cost_chf=round(cost, 2),
                priority_rank=rank,
                timeline_weeks=timeline,
            )
        )

    return PortfolioActionPlan(
        total_buildings_analyzed=len(top),
        action_plan=plan,
        total_estimated_cost_chf=round(total_cost, 2),
        total_timeline_weeks=max_timeline,
    )


async def analyze_portfolio_risk_distribution(
    db: AsyncSession,
    org_id: UUID | None = None,
) -> RiskDistributionAnalysis:
    """Analyze risk distribution across canton, building type, decade, and pollutant."""
    enriched = await _load_buildings_with_data(db, org_id)

    by_canton: dict[str, list[float]] = {}
    by_type: dict[str, list[float]] = {}
    by_decade: dict[str, list[float]] = {}
    by_pollutant: dict[str, list[float]] = {}

    for entry in enriched:
        b = entry["building"]
        risk = entry["risk_score"]

        by_canton.setdefault(b.canton, []).append(risk)
        by_type.setdefault(b.building_type, []).append(risk)

        decade = "unknown"
        if b.construction_year:
            decade = f"{(b.construction_year // 10) * 10}s"
        by_decade.setdefault(decade, []).append(risk)

        for p in entry["pollutant_types"]:
            by_pollutant.setdefault(p, []).append(risk)

    def _avg(scores: dict[str, list[float]]) -> dict[str, float]:
        return {k: round(sum(v) / len(v), 2) for k, v in scores.items()}

    canton_avg = _avg(by_canton)
    type_avg = _avg(by_type)
    decade_avg = _avg(by_decade)
    pollutant_avg = _avg(by_pollutant)

    # Determine highest risk cluster
    all_clusters = {
        **{f"canton:{k}": v for k, v in canton_avg.items()},
        **{f"type:{k}": v for k, v in type_avg.items()},
        **{f"decade:{k}": v for k, v in decade_avg.items()},
        **{f"pollutant:{k}": v for k, v in pollutant_avg.items()},
    }
    highest = max(all_clusters, key=all_clusters.get) if all_clusters else "none"

    return RiskDistributionAnalysis(
        by_canton=canton_avg,
        by_building_type=type_avg,
        by_decade=decade_avg,
        by_pollutant=pollutant_avg,
        highest_risk_cluster=highest,
    )


async def simulate_budget_allocation(
    db: AsyncSession,
    building_ids: list[UUID],
    total_budget_chf: float,
) -> BudgetAllocationResult:
    """Distribute a budget across buildings proportionally to combined priority."""
    enriched = await _load_buildings_with_data(db, building_ids=building_ids)

    total_score = sum(e["combined_score"] for e in enriched)

    allocations: list[BuildingBudgetAllocation] = []
    allocated_sum = 0.0

    for entry in enriched:
        b = entry["building"]
        if total_score > 0:
            proportion = entry["combined_score"] / total_score
        else:
            proportion = 1.0 / max(len(enriched), 1)

        allocated = round(min(total_budget_chf * proportion, entry["estimated_cost"]), 2)
        allocated_sum += allocated

        # Risk reduction proportional to budget coverage
        if entry["estimated_cost"] > 0:
            coverage = allocated / entry["estimated_cost"]
        else:
            coverage = 1.0
        risk_reduction = round(entry["risk_score"] * coverage * 0.7, 2)

        allocations.append(
            BuildingBudgetAllocation(
                building_id=b.id,
                address=b.address,
                allocated_chf=allocated,
                percent_of_budget=round(proportion * 100, 2) if total_score > 0 else 0.0,
                expected_risk_reduction=risk_reduction,
            )
        )

    portfolio_risk_reduction = sum(a.expected_risk_reduction for a in allocations)
    unallocated = round(max(total_budget_chf - allocated_sum, 0.0), 2)

    return BudgetAllocationResult(
        total_budget_chf=total_budget_chf,
        allocations=allocations,
        expected_portfolio_risk_reduction=round(portfolio_risk_reduction, 2),
        unallocated_chf=unallocated,
    )
