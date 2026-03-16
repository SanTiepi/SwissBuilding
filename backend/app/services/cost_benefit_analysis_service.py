"""
SwissBuildingOS - Cost-Benefit Analysis Service

Provides ROI analysis, strategy comparison, inaction cost modelling,
and portfolio-level investment planning for pollutant remediation.
Uses Swiss regulatory context (OTConst, CFST 6503, ORRChim, ORaP).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.schemas.cost_benefit_analysis import (
    BudgetBreakpoint,
    BuildingInvestmentItem,
    InactionCost,
    InterventionROI,
    InterventionROIResponse,
    PollutantInactionDetail,
    PortfolioInvestmentPlan,
    RemediationStrategiesResponse,
    RemediationStrategy,
)

# ---------------------------------------------------------------------------
# Cost constants (CHF, simplified Swiss market rates)
# ---------------------------------------------------------------------------

_REMEDIATION_COST_PER_M2: dict[str, float] = {
    "asbestos": 120.0,
    "pcb": 150.0,
    "lead": 80.0,
    "hap": 100.0,
    "radon": 15.0,
}

_RADON_FIXED = 5000.0

# Risk reduction value: what avoiding risk is worth per m² per year
_RISK_VALUE_PER_M2: dict[str, float] = {
    "asbestos": 60.0,
    "pcb": 45.0,
    "lead": 30.0,
    "hap": 35.0,
    "radon": 20.0,
}

_RISK_LEVEL_MULTIPLIER: dict[str, float] = {
    "critical": 2.0,
    "high": 1.5,
    "medium": 1.0,
    "low": 0.5,
    "unknown": 0.7,
}

# Depreciation percentage per pollutant when threshold exceeded
_DEPRECIATION_PCT: dict[str, float] = {
    "asbestos": 15.0,
    "pcb": 10.0,
    "lead": 5.0,
    "hap": 5.0,
    "radon": 2.0,
}

# Regulatory fine ranges (CHF)
_FINE_RANGES: dict[str, tuple[float, float]] = {
    "critical": (50_000.0, 100_000.0),
    "high": (20_000.0, 50_000.0),
    "medium": (10_000.0, 20_000.0),
    "low": (0.0, 10_000.0),
    "unknown": (0.0, 10_000.0),
}

# Timeline weeks per pollutant remediation
_WEEKS_PER_POLLUTANT = 3

# NPV discount rate
_DEFAULT_DISCOUNT_RATE = 0.03

# NPV horizon (years)
_NPV_HORIZON = 10

# Budget breakpoints for portfolio plan
_BUDGET_BREAKPOINTS = [100_000.0, 500_000.0, 1_000_000.0]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _fetch_samples_grouped(db: AsyncSession, building_id: UUID) -> dict[str, list[Sample]]:
    """Return samples grouped by pollutant_type for completed/validated diagnostics."""
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
    grouped: dict[str, list[Sample]] = {}
    for s in samples:
        pt = s.pollutant_type
        if pt:
            grouped.setdefault(pt, []).append(s)
    return grouped


def _surface(building: Building) -> float:
    return building.surface_area_m2 or 200.0  # default 200m² if unknown


def _dominant_risk_level(samples: list[Sample]) -> str:
    priority = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
    best = "unknown"
    best_p = 0
    for s in samples:
        rl = s.risk_level or "unknown"
        if priority.get(rl, 0) > best_p:
            best = rl
            best_p = priority[rl]
    return best


def _has_threshold_exceeded(samples: list[Sample]) -> bool:
    return any(s.threshold_exceeded for s in samples)


def _compute_remediation_cost(pollutant: str, surface: float) -> float:
    rate = _REMEDIATION_COST_PER_M2.get(pollutant, 100.0)
    if pollutant == "radon":
        return _RADON_FIXED + rate * surface
    return rate * surface


def _compute_risk_value(pollutant: str, risk_level: str, surface: float) -> float:
    """Annual risk-reduction value if pollutant is remediated."""
    base = _RISK_VALUE_PER_M2.get(pollutant, 30.0)
    mult = _RISK_LEVEL_MULTIPLIER.get(risk_level, 1.0)
    return base * mult * surface


def _npv(annual_value: float, cost: float, rate: float, horizon: int) -> float:
    """Net Present Value: sum of discounted annual values minus upfront cost."""
    if rate <= 0:
        return annual_value * horizon - cost
    pv = sum(annual_value / ((1 + rate) ** year) for year in range(1, horizon + 1))
    return pv - cost


# ---------------------------------------------------------------------------
# FN1 — analyze_intervention_roi
# ---------------------------------------------------------------------------


async def analyze_intervention_roi(db: AsyncSession, building_id: UUID) -> InterventionROIResponse:
    """Per-intervention ROI: cost vs risk reduction value, payback, NPV, priority."""
    building = await _fetch_building(db, building_id)
    grouped = await _fetch_samples_grouped(db, building_id)
    surface = _surface(building)

    interventions: list[InterventionROI] = []

    for pollutant, samples in grouped.items():
        if not _has_threshold_exceeded(samples):
            continue

        risk_level = _dominant_risk_level(samples)
        cost = _compute_remediation_cost(pollutant, surface)
        annual_value = _compute_risk_value(pollutant, risk_level, surface)

        payback = cost / annual_value if annual_value > 0 else 99.0
        roi = annual_value / cost if cost > 0 else 0.0
        npv_val = _npv(annual_value, cost, _DEFAULT_DISCOUNT_RATE, _NPV_HORIZON)

        # Priority score: higher is more urgent (combines ROI and risk severity)
        severity_weight = _RISK_LEVEL_MULTIPLIER.get(risk_level, 1.0)
        priority = roi * severity_weight * 100

        interventions.append(
            InterventionROI(
                pollutant_type=pollutant,
                risk_level=risk_level,
                estimated_cost_chf=round(cost, 2),
                risk_reduction_value_chf=round(annual_value, 2),
                roi_ratio=round(roi, 4),
                payback_years=round(payback, 2),
                npv_chf=round(npv_val, 2),
                priority_score=round(priority, 2),
            )
        )

    # Sort by priority_score descending (best ROI first)
    interventions.sort(key=lambda i: i.priority_score, reverse=True)

    return InterventionROIResponse(
        building_id=building_id,
        interventions=interventions,
        discount_rate=_DEFAULT_DISCOUNT_RATE,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2 — compare_remediation_strategies
# ---------------------------------------------------------------------------


async def compare_remediation_strategies(db: AsyncSession, building_id: UUID) -> RemediationStrategiesResponse:
    """Compare 3 strategies: minimal, standard, comprehensive."""
    building = await _fetch_building(db, building_id)
    grouped = await _fetch_samples_grouped(db, building_id)
    surface = _surface(building)

    # Classify pollutants
    critical: list[str] = []
    non_compliant: list[str] = []
    detected: list[str] = []

    for pollutant, samples in grouped.items():
        risk_level = _dominant_risk_level(samples)
        exceeded = _has_threshold_exceeded(samples)
        detected.append(pollutant)
        if exceeded:
            non_compliant.append(pollutant)
        if risk_level in ("critical", "high"):
            critical.append(pollutant)

    # Ensure critical is a subset of non_compliant for cost calculation
    for p in critical:
        if p not in non_compliant:
            non_compliant.append(p)

    total_pollutants = len(detected) if detected else 1
    strategies: list[RemediationStrategy] = []

    # --- Minimal: critical only ---
    minimal_cost = sum(_compute_remediation_cost(p, surface) for p in critical)
    minimal_reduction = (len(critical) / total_pollutants * 100) if critical else 0.0
    remaining_after_minimal = [p for p in detected if p not in critical]
    minimal_residual = _worst_risk(remaining_after_minimal, grouped)
    strategies.append(
        RemediationStrategy(
            strategy="minimal",
            description="Address critical and high-risk pollutants only",
            total_cost_chf=round(minimal_cost, 2),
            risk_reduction_pct=round(minimal_reduction, 2),
            timeline_weeks=max(len(critical), 1) * _WEEKS_PER_POLLUTANT if critical else 0,
            residual_risk_level=minimal_residual,
            pollutants_addressed=critical,
        )
    )

    # --- Standard: all non-compliant ---
    standard_cost = sum(_compute_remediation_cost(p, surface) for p in non_compliant)
    standard_reduction = (len(non_compliant) / total_pollutants * 100) if non_compliant else 0.0
    remaining_after_standard = [p for p in detected if p not in non_compliant]
    standard_residual = _worst_risk(remaining_after_standard, grouped)
    strategies.append(
        RemediationStrategy(
            strategy="standard",
            description="Address all non-compliant pollutants (threshold exceeded)",
            total_cost_chf=round(standard_cost, 2),
            risk_reduction_pct=round(standard_reduction, 2),
            timeline_weeks=max(len(non_compliant), 1) * _WEEKS_PER_POLLUTANT if non_compliant else 0,
            residual_risk_level=standard_residual,
            pollutants_addressed=non_compliant,
        )
    )

    # --- Comprehensive: all detected ---
    comprehensive_cost = sum(_compute_remediation_cost(p, surface) for p in detected)
    strategies.append(
        RemediationStrategy(
            strategy="comprehensive",
            description="Address all detected pollutants regardless of threshold",
            total_cost_chf=round(comprehensive_cost, 2),
            risk_reduction_pct=100.0 if detected else 0.0,
            timeline_weeks=max(len(detected), 1) * _WEEKS_PER_POLLUTANT if detected else 0,
            residual_risk_level="low",
            pollutants_addressed=detected,
        )
    )

    return RemediationStrategiesResponse(
        building_id=building_id,
        strategies=strategies,
        generated_at=datetime.now(UTC),
    )


def _worst_risk(remaining_pollutants: list[str], grouped: dict[str, list[Sample]]) -> str:
    """Return the worst risk level among remaining pollutants."""
    if not remaining_pollutants:
        return "low"
    priority = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
    worst = "low"
    worst_p = 0
    for p in remaining_pollutants:
        samples = grouped.get(p, [])
        rl = _dominant_risk_level(samples) if samples else "unknown"
        if priority.get(rl, 0) > worst_p:
            worst = rl
            worst_p = priority[rl]
    return worst


# ---------------------------------------------------------------------------
# FN3 — calculate_inaction_cost
# ---------------------------------------------------------------------------


async def calculate_inaction_cost(db: AsyncSession, building_id: UUID) -> InactionCost:
    """Cost of doing nothing: fines, liability, insurance, depreciation."""
    building = await _fetch_building(db, building_id)
    grouped = await _fetch_samples_grouped(db, building_id)
    surface = _surface(building)

    total_fine_min = 0.0
    total_fine_max = 0.0
    total_depreciation = 0.0
    total_liability_per_year = 0.0
    insurance_increase = 0.0
    details: list[PollutantInactionDetail] = []

    for pollutant, samples in grouped.items():
        if not _has_threshold_exceeded(samples):
            continue

        risk_level = _dominant_risk_level(samples)
        fine_min, fine_max = _FINE_RANGES.get(risk_level, (0.0, 10_000.0))
        depr = _DEPRECIATION_PCT.get(pollutant, 2.0)

        total_fine_min += fine_min
        total_fine_max += fine_max
        total_depreciation += depr

        # Liability grows with surface and severity
        mult = _RISK_LEVEL_MULTIPLIER.get(risk_level, 1.0)
        total_liability_per_year += surface * 10.0 * mult  # CHF 10/m²/year base

        # Insurance increase: 5% per non-compliant critical pollutant, 2% per high
        if risk_level == "critical":
            insurance_increase += 5.0
        elif risk_level == "high":
            insurance_increase += 2.0
        else:
            insurance_increase += 1.0

        details.append(
            PollutantInactionDetail(
                pollutant_type=pollutant,
                risk_level=risk_level,
                depreciation_pct=round(depr, 2),
                fine_range_min_chf=round(fine_min, 2),
                fine_range_max_chf=round(fine_max, 2),
            )
        )

    # Cap depreciation at 30%
    total_depreciation = min(total_depreciation, 30.0)

    # Year 1 total: average fine + liability + estimated insurance cost
    avg_fine = (total_fine_min + total_fine_max) / 2
    year1 = avg_fine + total_liability_per_year
    # Year 5: compounding liability growth (10% per year)
    year5 = avg_fine + sum(total_liability_per_year * (1.1**y) for y in range(5))

    return InactionCost(
        building_id=building_id,
        regulatory_fine_min_chf=round(total_fine_min, 2),
        regulatory_fine_max_chf=round(total_fine_max, 2),
        liability_exposure_chf_per_year=round(total_liability_per_year, 2),
        insurance_premium_increase_pct=round(insurance_increase, 2),
        property_depreciation_pct=round(total_depreciation, 2),
        total_inaction_cost_year1_chf=round(year1, 2),
        total_inaction_cost_year5_chf=round(year5, 2),
        pollutant_details=details,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4 — get_portfolio_investment_plan
# ---------------------------------------------------------------------------


async def get_portfolio_investment_plan(db: AsyncSession, org_id: UUID) -> PortfolioInvestmentPlan:
    """Optimal investment allocation across all buildings of an organization."""
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return PortfolioInvestmentPlan(
            organization_id=org_id,
            ranked_buildings=[],
            budget_breakpoints=[],
            total_portfolio_cost_chf=0.0,
            total_risk_reduction_pct=0.0,
            generated_at=datetime.now(UTC),
        )

    # Score each building
    items: list[tuple[float, float, float, Building]] = []  # (risk_score, cost, reduction, building)
    for bldg in buildings:
        grouped = await _fetch_samples_grouped(db, bldg.id)
        surface = _surface(bldg)

        cost = 0.0
        risk_score = 0.0
        exceeded_count = 0

        for pollutant, samples in grouped.items():
            if _has_threshold_exceeded(samples):
                cost += _compute_remediation_cost(pollutant, surface)
                rl = _dominant_risk_level(samples)
                risk_score += _RISK_LEVEL_MULTIPLIER.get(rl, 1.0)
                exceeded_count += 1

        # Risk reduction as fraction of total pollutants
        total_pollutants = len(grouped) if grouped else 1
        reduction = (exceeded_count / total_pollutants * 100) if exceeded_count > 0 else 0.0

        items.append((risk_score, cost, reduction, bldg))

    # Sort by risk_score descending (highest risk first), then by cost ascending
    items.sort(key=lambda x: (-x[0], x[1]))

    # Build ranked list with cumulative values
    ranked: list[BuildingInvestmentItem] = []
    cumulative_cost = 0.0
    total_possible_reduction = sum(it[2] for it in items) if items else 1.0
    cumulative_reduction = 0.0

    for rank, (risk_score, cost, reduction, bldg) in enumerate(items, 1):
        cumulative_cost += cost
        cumulative_reduction += reduction
        cum_reduction_pct = (cumulative_reduction / total_possible_reduction * 100) if total_possible_reduction else 0.0

        ranked.append(
            BuildingInvestmentItem(
                building_id=bldg.id,
                address=bldg.address,
                estimated_cost_chf=round(cost, 2),
                risk_score=round(risk_score, 2),
                risk_reduction_pct=round(reduction, 2),
                cumulative_cost_chf=round(cumulative_cost, 2),
                cumulative_risk_reduction_pct=round(cum_reduction_pct, 2),
                rank=rank,
            )
        )

    # Budget breakpoints
    breakpoints: list[BudgetBreakpoint] = []
    for bp_budget in _BUDGET_BREAKPOINTS:
        covered = 0
        bp_reduction = 0.0
        running = 0.0
        for item in ranked:
            if running + item.estimated_cost_chf <= bp_budget:
                running += item.estimated_cost_chf
                covered += 1
                bp_reduction += item.risk_reduction_pct
        bp_reduction_pct = (bp_reduction / total_possible_reduction * 100) if total_possible_reduction else 0.0
        breakpoints.append(
            BudgetBreakpoint(
                budget_chf=bp_budget,
                buildings_covered=covered,
                risk_reduction_pct=round(bp_reduction_pct, 2),
            )
        )

    return PortfolioInvestmentPlan(
        organization_id=org_id,
        ranked_buildings=ranked,
        budget_breakpoints=breakpoints,
        total_portfolio_cost_chf=round(cumulative_cost, 2),
        total_risk_reduction_pct=round(
            (cumulative_reduction / total_possible_reduction * 100) if total_possible_reduction else 0.0, 2
        ),
        generated_at=datetime.now(UTC),
    )
