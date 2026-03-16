"""
SwissBuildingOS - Budget Tracking Service

Tracks estimated vs actual costs for building remediation work,
provides burn-rate analysis, quarterly forecasts, and portfolio-level
budget summaries. Costs are derived from interventions and remediation
estimates based on diagnostic samples.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.budget_tracking import (
    BudgetOverview,
    BuildingBudgetItem,
    CostVarianceResponse,
    InterventionCostItem,
    PortfolioBudgetSummary,
    QuarterlyForecast,
    QuarterlySpendResponse,
)

# ---------------------------------------------------------------------------
# Cost constants (CHF, Swiss market rates — aligned with cost_benefit_analysis)
# ---------------------------------------------------------------------------

_REMEDIATION_COST_PER_M2: dict[str, float] = {
    "asbestos": 120.0,
    "pcb": 150.0,
    "lead": 80.0,
    "hap": 100.0,
    "radon": 15.0,
}

_RADON_FIXED = 5000.0

# Map intervention_type to cost category
_TYPE_TO_CATEGORY: dict[str, str] = {
    "diagnostic": "diagnostic",
    "sampling": "diagnostic",
    "inspection": "diagnostic",
    "remediation": "remediation",
    "encapsulation": "remediation",
    "removal": "remediation",
    "monitoring": "monitoring",
    "disposal": "disposal",
    "waste_removal": "disposal",
    "administrative": "admin",
    "notification": "admin",
}

_ALL_CATEGORIES = ["diagnostic", "remediation", "monitoring", "disposal", "admin"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _fetch_interventions(db: AsyncSession, building_id: UUID) -> list[Intervention]:
    result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    return list(result.scalars().all())


async def _estimate_total_cost(db: AsyncSession, building_id: UUID, building: Building) -> float:
    """Estimate total remediation cost from diagnostic samples with exceeded thresholds."""
    stmt = (
        select(Sample)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
        )
    )
    result = await db.execute(stmt)
    samples = result.scalars().all()

    surface = building.surface_area_m2 or 200.0
    seen_pollutants: set[str] = set()
    total = 0.0

    for s in samples:
        pt = s.pollutant_type
        if pt and s.threshold_exceeded and pt not in seen_pollutants:
            seen_pollutants.add(pt)
            rate = _REMEDIATION_COST_PER_M2.get(pt, 100.0)
            if pt == "radon":
                total += _RADON_FIXED + rate * surface
            else:
                total += rate * surface

    return total


def _categorize(intervention_type: str) -> str:
    return _TYPE_TO_CATEGORY.get(intervention_type, "remediation")


def _quarter_label(d: date) -> str:
    q = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{q}"


# ---------------------------------------------------------------------------
# FN1 — get_building_budget_overview
# ---------------------------------------------------------------------------


async def get_building_budget_overview(db: AsyncSession, building_id: UUID) -> BudgetOverview:
    """Budget status: estimated total, spent, remaining, burn rate, variance."""
    building = await _fetch_building(db, building_id)
    interventions = await _fetch_interventions(db, building_id)
    estimated = await _estimate_total_cost(db, building_id, building)

    # Sum actual spend from completed interventions
    spent = sum(i.cost_chf or 0.0 for i in interventions if i.status == "completed")

    # Remaining planned cost (interventions not yet completed)
    planned_not_done = sum(i.cost_chf or 0.0 for i in interventions if i.status in ("planned", "in_progress"))

    remaining = max(estimated - spent, 0.0)

    # Burn rate: spent / months elapsed since first intervention
    first_date = None
    for i in interventions:
        if i.date_start and (first_date is None or i.date_start < first_date):
            first_date = i.date_start

    if first_date and spent > 0:
        today = date.today()
        months = max((today.year - first_date.year) * 12 + (today.month - first_date.month), 1)
        burn_rate = spent / months
    else:
        burn_rate = 0.0

    # Projected completion cost: spent + remaining planned + unplanned gap
    projected = spent + max(planned_not_done, remaining)

    # Variance
    variance_pct = ((projected - estimated) / estimated * 100) if estimated > 0 else 0.0

    if variance_pct > 5.0:
        status = "over_budget"
    elif variance_pct < -5.0:
        status = "under_budget"
    else:
        status = "on_track"

    return BudgetOverview(
        building_id=building_id,
        estimated_total_cost_chf=round(estimated, 2),
        spent_chf=round(spent, 2),
        remaining_chf=round(remaining, 2),
        burn_rate_chf_per_month=round(burn_rate, 2),
        projected_completion_cost_chf=round(projected, 2),
        variance_pct=round(variance_pct, 2),
        status=status,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2 — track_cost_variance
# ---------------------------------------------------------------------------


async def track_cost_variance(db: AsyncSession, building_id: UUID) -> CostVarianceResponse:
    """Per-intervention cost tracking: estimated vs actual, variance, overrun flags."""
    await _fetch_building(db, building_id)
    interventions = await _fetch_interventions(db, building_id)

    items: list[InterventionCostItem] = []
    total_estimated = 0.0
    total_actual = 0.0
    overrun_count = 0
    category_totals: dict[str, float] = {c: 0.0 for c in _ALL_CATEGORIES}

    for iv in interventions:
        est = iv.cost_chf or 0.0
        category = _categorize(iv.intervention_type)

        if iv.status == "completed":
            actual = iv.cost_chf or 0.0
            variance = actual - est
            variance_pct = (variance / est * 100) if est > 0 else 0.0
            is_overrun = variance > 0 and variance_pct > 10.0
            if is_overrun:
                overrun_count += 1
            total_actual += actual
            category_totals[category] = category_totals.get(category, 0.0) + actual
        else:
            actual = None
            variance = 0.0
            variance_pct = 0.0
            is_overrun = False
            category_totals[category] = category_totals.get(category, 0.0) + est

        total_estimated += est

        items.append(
            InterventionCostItem(
                intervention_id=iv.id,
                title=iv.title,
                intervention_type=iv.intervention_type,
                cost_category=category,
                estimated_cost_chf=round(est, 2),
                actual_cost_chf=round(actual, 2) if actual is not None else None,
                variance_chf=round(variance, 2),
                variance_pct=round(variance_pct, 2),
                is_overrun=is_overrun,
                status=iv.status,
            )
        )

    return CostVarianceResponse(
        building_id=building_id,
        items=items,
        total_estimated_chf=round(total_estimated, 2),
        total_actual_chf=round(total_actual, 2),
        total_variance_chf=round(total_actual - total_estimated, 2),
        overrun_count=overrun_count,
        by_category={k: round(v, 2) for k, v in category_totals.items()},
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3 — forecast_quarterly_spend
# ---------------------------------------------------------------------------


async def forecast_quarterly_spend(db: AsyncSession, building_id: UUID) -> QuarterlySpendResponse:
    """Next 4 quarters: projected spend from planned interventions + monitoring."""
    await _fetch_building(db, building_id)
    interventions = await _fetch_interventions(db, building_id)

    today = date.today()
    # Generate next 4 quarter labels
    quarter_labels: list[str] = []
    for offset in range(4):
        month = today.month + offset * 3
        year = today.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        q = (month - 1) // 3 + 1
        label = f"{year}-Q{q}"
        if label not in quarter_labels:
            quarter_labels.append(label)

    # Fill remaining if dedup removed any
    while len(quarter_labels) < 4:
        last = quarter_labels[-1]
        y, q = int(last[:4]), int(last[-1])
        q += 1
        if q > 4:
            q = 1
            y += 1
        quarter_labels.append(f"{y}-Q{q}")

    quarters_data: dict[str, dict[str, float]] = {ql: {} for ql in quarter_labels}
    quarters_count: dict[str, int] = {ql: 0 for ql in quarter_labels}

    for iv in interventions:
        if iv.status in ("completed", "cancelled"):
            continue
        cost = iv.cost_chf or 0.0
        category = _categorize(iv.intervention_type)

        if iv.date_start:
            ql = _quarter_label(iv.date_start)
        else:
            # Unscheduled: assign to first quarter
            ql = quarter_labels[0]

        if ql in quarters_data:
            quarters_data[ql][category] = quarters_data[ql].get(category, 0.0) + cost
            quarters_count[ql] += 1

    result_quarters: list[QuarterlyForecast] = []
    total = 0.0

    for ql in quarter_labels:
        cats = quarters_data[ql]
        spend = sum(cats.values())
        total += spend
        result_quarters.append(
            QuarterlyForecast(
                quarter=ql,
                projected_spend_chf=round(spend, 2),
                intervention_count=quarters_count[ql],
                categories={k: round(v, 2) for k, v in cats.items()},
            )
        )

    return QuarterlySpendResponse(
        building_id=building_id,
        quarters=result_quarters,
        total_projected_chf=round(total, 2),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4 — get_portfolio_budget_summary
# ---------------------------------------------------------------------------


async def get_portfolio_budget_summary(db: AsyncSession, org_id: UUID) -> PortfolioBudgetSummary:
    """Org-level budget: total estimated, spent, remaining, buildings over budget, ROI."""
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)

    empty = PortfolioBudgetSummary(
        organization_id=org_id,
        total_estimated_chf=0.0,
        total_spent_chf=0.0,
        total_remaining_chf=0.0,
        buildings_over_budget=0,
        quarterly_forecast=[],
        risk_reduction_per_chf=0.0,
        buildings=[],
        generated_at=datetime.now(UTC),
    )

    if not buildings:
        return empty

    total_estimated = 0.0
    total_spent = 0.0
    over_budget_count = 0
    building_items: list[BuildingBudgetItem] = []

    # Aggregate quarterly data across all buildings
    agg_quarters: dict[str, dict[str, float]] = {}
    agg_quarter_counts: dict[str, int] = {}

    for bldg in buildings:
        estimated = await _estimate_total_cost(db, bldg.id, bldg)
        interventions = await _fetch_interventions(db, bldg.id)

        spent = sum(i.cost_chf or 0.0 for i in interventions if i.status == "completed")
        remaining = max(estimated - spent, 0.0)
        is_over = spent > estimated if estimated > 0 else spent > 0

        if is_over:
            over_budget_count += 1

        total_estimated += estimated
        total_spent += spent

        building_items.append(
            BuildingBudgetItem(
                building_id=bldg.id,
                address=bldg.address,
                estimated_cost_chf=round(estimated, 2),
                spent_chf=round(spent, 2),
                remaining_chf=round(remaining, 2),
                is_over_budget=is_over,
            )
        )

        # Quarterly forecast from planned interventions
        for iv in interventions:
            if iv.status in ("completed", "cancelled"):
                continue
            cost = iv.cost_chf or 0.0
            category = _categorize(iv.intervention_type)
            if iv.date_start:
                ql = _quarter_label(iv.date_start)
            else:
                today = date.today()
                ql = _quarter_label(today)

            if ql not in agg_quarters:
                agg_quarters[ql] = {}
                agg_quarter_counts[ql] = 0
            agg_quarters[ql][category] = agg_quarters[ql].get(category, 0.0) + cost
            agg_quarter_counts[ql] += 1

    # Sort quarters and build forecast
    sorted_qs = sorted(agg_quarters.keys())[:4]
    quarterly_forecast = [
        QuarterlyForecast(
            quarter=ql,
            projected_spend_chf=round(sum(agg_quarters[ql].values()), 2),
            intervention_count=agg_quarter_counts[ql],
            categories={k: round(v, 2) for k, v in agg_quarters[ql].items()},
        )
        for ql in sorted_qs
    ]

    total_remaining = max(total_estimated - total_spent, 0.0)

    # ROI estimate: risk reduction per CHF spent
    # Count buildings with pollutant issues resolved (spent > 0)
    risk_reduction_per_chf = 0.0
    if total_spent > 0 and len(buildings) > 0:
        # Simple metric: fraction of estimated work completed per CHF
        completion_ratio = min(total_spent / total_estimated, 1.0) if total_estimated > 0 else 0.0
        risk_reduction_per_chf = completion_ratio / total_spent * 100_000  # per 100k CHF

    return PortfolioBudgetSummary(
        organization_id=org_id,
        total_estimated_chf=round(total_estimated, 2),
        total_spent_chf=round(total_spent, 2),
        total_remaining_chf=round(total_remaining, 2),
        buildings_over_budget=over_budget_count,
        quarterly_forecast=quarterly_forecast,
        risk_reduction_per_chf=round(risk_reduction_per_chf, 4),
        buildings=building_items,
        generated_at=datetime.now(UTC),
    )
