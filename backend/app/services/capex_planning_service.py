"""
SwissBuildingOS - CAPEX Planning Service

Capital expenditure planning for building pollutant remediation:
building-level plans, reserve fund assessment, investment scenario
forecasting, and portfolio-level summaries.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.schemas.capex_planning import (
    BuildingCapexPlan,
    BuildingInvestmentForecast,
    CapexLineItem,
    InvestmentScenario,
    PortfolioCapexSummary,
    ReserveFundStatus,
)
from app.services.building_data_loader import load_org_buildings

# ---------------------------------------------------------------------------
# Cost constants (CHF)
# ---------------------------------------------------------------------------

_DIAGNOSTIC_COST = 2000.0

_REMEDIATION_COST_PER_ZONE: dict[str, float] = {
    "asbestos": 15000.0,
    "pcb": 8000.0,
    "lead": 5000.0,
    "hap": 3000.0,
    "radon": 2000.0,
}

_MONITORING_COST_PER_YEAR = 1000.0
_CONTINGENCY_RATE = 0.10
_RESERVE_SPREAD_YEARS = 10
_AVOIDED_COST_PER_ISSUE_PER_YEAR = 5000.0

_PRIORITY_MAP: dict[str, str] = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


def _risk_level_to_priority(risk_level: str | None) -> str:
    if risk_level in ("critical", "high"):
        return risk_level
    if risk_level == "medium":
        return "medium"
    return "low"


def _aggregate(
    items: list[CapexLineItem],
) -> tuple[float, dict[str, float], dict[str, float]]:
    """Return (total, by_category, by_priority) from line items."""
    total = 0.0
    by_cat: dict[str, float] = {}
    by_pri: dict[str, float] = {}
    for item in items:
        total += item.estimated_cost
        by_cat[item.category] = by_cat.get(item.category, 0.0) + item.estimated_cost
        by_pri[item.priority] = by_pri.get(item.priority, 0.0) + item.estimated_cost
    return total, by_cat, by_pri


# ---------------------------------------------------------------------------
# FN1 — generate_building_capex_plan
# ---------------------------------------------------------------------------


async def generate_building_capex_plan(
    building_id: UUID,
    db: AsyncSession,
    horizon_years: int = 5,
) -> BuildingCapexPlan:
    """Generate a CAPEX plan based on diagnostics, samples, and open actions."""
    await _fetch_building(db, building_id)

    line_items: list[CapexLineItem] = []

    # --- Diagnostics with exceeded samples → remediation line items ---
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
    exceeded_samples = result.scalars().all()

    # Track unique pollutants for monitoring
    active_pollutants: set[str] = set()

    for sample in exceeded_samples:
        pt = sample.pollutant_type or "unknown"
        active_pollutants.add(pt)
        priority = _risk_level_to_priority(sample.risk_level)

        # Diagnostic cost
        line_items.append(
            CapexLineItem(
                category="diagnostic",
                description=f"Diagnostic for {pt} — sample {sample.sample_number}",
                estimated_cost=_DIAGNOSTIC_COST,
                priority=priority,
                pollutant_type=pt,
            )
        )

        # Remediation cost
        rem_cost = _REMEDIATION_COST_PER_ZONE.get(pt, 5000.0)
        line_items.append(
            CapexLineItem(
                category="remediation",
                description=f"Remediation of {pt} — sample {sample.sample_number}",
                estimated_cost=rem_cost,
                priority=priority,
                pollutant_type=pt,
            )
        )

    # --- Open action items → additional line items ---
    action_stmt = select(ActionItem).where(
        ActionItem.building_id == building_id,
        ActionItem.status.in_(["open", "in_progress"]),
    )
    action_result = await db.execute(action_stmt)
    actions = action_result.scalars().all()

    for action in actions:
        priority = _PRIORITY_MAP.get(action.priority, "medium")
        line_items.append(
            CapexLineItem(
                category="verification",
                description=action.title,
                estimated_cost=_DIAGNOSTIC_COST,
                priority=priority,
            )
        )

    # --- Monitoring line items ---
    for pt in active_pollutants:
        monitoring_total = _MONITORING_COST_PER_YEAR * horizon_years
        line_items.append(
            CapexLineItem(
                category="monitoring",
                description=f"Monitoring for {pt} ({horizon_years} years)",
                estimated_cost=monitoring_total,
                priority="medium",
                pollutant_type=pt,
            )
        )

    # --- Contingency ---
    subtotal = sum(item.estimated_cost for item in line_items)
    if subtotal > 0:
        contingency = subtotal * _CONTINGENCY_RATE
        line_items.append(
            CapexLineItem(
                category="contingency",
                description="Contingency reserve (10%)",
                estimated_cost=round(contingency, 2),
                priority="low",
            )
        )

    total, by_cat, by_pri = _aggregate(line_items)

    return BuildingCapexPlan(
        building_id=building_id,
        total_estimated=round(total, 2),
        total_by_category={k: round(v, 2) for k, v in by_cat.items()},
        total_by_priority={k: round(v, 2) for k, v in by_pri.items()},
        line_items=line_items,
        planning_horizon_years=horizon_years,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2 — evaluate_reserve_fund
# ---------------------------------------------------------------------------


async def evaluate_reserve_fund(
    building_id: UUID,
    db: AsyncSession,
) -> ReserveFundStatus:
    """Assess reserve fund adequacy based on CAPEX plan and building profile."""
    building = await _fetch_building(db, building_id)
    plan = await generate_building_capex_plan(building_id, db)

    recommended_annual = plan.total_estimated / _RESERVE_SPREAD_YEARS if plan.total_estimated > 0 else 0.0

    # Adequacy rating based on building age and risk
    year = building.construction_year
    has_critical = "critical" in plan.total_by_priority
    has_high = "high" in plan.total_by_priority

    if year is not None and year < 1960 and (has_critical or has_high):
        rating = "critical"
    elif year is not None and year < 1975 and (has_critical or has_high or plan.total_estimated > 0):
        rating = "insufficient"
    elif year is not None and year > 1975 and plan.total_estimated == 0:
        rating = "adequate"
    else:
        rating = "marginal"

    return ReserveFundStatus(
        building_id=building_id,
        recommended_annual_reserve=round(recommended_annual, 2),
        current_gap=round(recommended_annual, 2),
        adequacy_rating=rating,
        breakdown={k: round(v, 2) for k, v in plan.total_by_category.items()},
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3 — forecast_investment_scenarios
# ---------------------------------------------------------------------------


async def forecast_investment_scenarios(
    building_id: UUID,
    db: AsyncSession,
) -> BuildingInvestmentForecast:
    """Generate 3 investment scenarios: minimum, recommended, comprehensive."""
    await _fetch_building(db, building_id)
    plan = await generate_building_capex_plan(building_id, db)

    # Split items by priority
    critical_items = [i for i in plan.line_items if i.priority == "critical"]
    high_items = [i for i in plan.line_items if i.priority == "high"]
    critical_cost = sum(i.estimated_cost for i in critical_items)
    high_cost = sum(i.estimated_cost for i in high_items)
    total_issues = len(plan.line_items)

    def _payback(cost: float, issues_resolved: int) -> float | None:
        if cost <= 0 or issues_resolved <= 0:
            return None
        annual_savings = issues_resolved * _AVOIDED_COST_PER_ISSUE_PER_YEAR
        return round(cost / annual_savings, 1) if annual_savings > 0 else None

    critical_count = len(critical_items)
    high_count = len(high_items)

    scenarios = [
        InvestmentScenario(
            scenario_name="minimum_compliance",
            total_cost=round(critical_cost, 2),
            risk_reduction_pct=30.0,
            compliance_improvement="Addresses critical regulatory gaps only",
            payback_years=_payback(critical_cost, critical_count),
            recommended=False,
        ),
        InvestmentScenario(
            scenario_name="recommended",
            total_cost=round(critical_cost + high_cost, 2),
            risk_reduction_pct=70.0,
            compliance_improvement="Addresses critical and high-priority items",
            payback_years=_payback(critical_cost + high_cost, critical_count + high_count),
            recommended=True,
        ),
        InvestmentScenario(
            scenario_name="comprehensive",
            total_cost=round(plan.total_estimated, 2),
            risk_reduction_pct=95.0,
            compliance_improvement="Full remediation of all identified issues",
            payback_years=_payback(plan.total_estimated, total_issues),
            recommended=False,
        ),
    ]

    return BuildingInvestmentForecast(
        building_id=building_id,
        scenarios=scenarios,
        recommended_scenario="recommended",
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4 — get_portfolio_capex_summary
# ---------------------------------------------------------------------------


async def get_portfolio_capex_summary(
    org_id: UUID,
    db: AsyncSession,
) -> PortfolioCapexSummary:
    """Aggregate CAPEX plans across all buildings in an organization."""
    # Verify org exists
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if org is None:
        raise ValueError(f"Organization {org_id} not found")

    now = datetime.now(UTC)

    buildings = await load_org_buildings(db, org_id)

    empty = PortfolioCapexSummary(
        organization_id=org_id,
        total_buildings=0,
        total_capex_estimated=0.0,
        by_category={},
        by_priority={},
        buildings_needing_urgent_investment=0,
        average_reserve_adequacy="adequate",
        generated_at=now,
    )

    if not buildings:
        return empty

    total_capex = 0.0
    agg_cat: dict[str, float] = {}
    agg_pri: dict[str, float] = {}
    urgent_count = 0
    adequacy_scores: list[str] = []

    for bldg in buildings:
        plan = await generate_building_capex_plan(bldg.id, db)
        reserve = await evaluate_reserve_fund(bldg.id, db)

        total_capex += plan.total_estimated
        for k, v in plan.total_by_category.items():
            agg_cat[k] = agg_cat.get(k, 0.0) + v
        for k, v in plan.total_by_priority.items():
            agg_pri[k] = agg_pri.get(k, 0.0) + v

        if "critical" in plan.total_by_priority:
            urgent_count += 1

        adequacy_scores.append(reserve.adequacy_rating)

    # Average adequacy: pick worst if any critical/insufficient
    if "critical" in adequacy_scores:
        avg_adequacy = "critical"
    elif "insufficient" in adequacy_scores:
        avg_adequacy = "insufficient"
    elif "marginal" in adequacy_scores:
        avg_adequacy = "marginal"
    else:
        avg_adequacy = "adequate"

    return PortfolioCapexSummary(
        organization_id=org_id,
        total_buildings=len(buildings),
        total_capex_estimated=round(total_capex, 2),
        by_category={k: round(v, 2) for k, v in agg_cat.items()},
        by_priority={k: round(v, 2) for k, v in agg_pri.items()},
        buildings_needing_urgent_investment=urgent_count,
        average_reserve_adequacy=avg_adequacy,
        generated_at=now,
    )
