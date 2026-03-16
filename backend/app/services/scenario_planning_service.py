"""
SwissBuildingOS - Scenario Planning Service

What-if scenario analysis for building pollutant remediation.
Supports creating scenarios, comparing alternatives, finding optimal
plans within budget/time constraints, and sensitivity analysis.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.schemas.scenario_planning import (
    CompareResponse,
    ComplianceImpact,
    InterventionConfig,
    OptimalScenarioResponse,
    RiskReductionDetail,
    ScenarioCreateRequest,
    ScenarioResult,
    SensitivityResponse,
    SensitivityVariant,
)
from app.services.risk_engine import (
    calculate_asbestos_base_probability,
    calculate_hap_base_probability,
    calculate_lead_base_probability,
    calculate_pcb_base_probability,
    calculate_radon_base_probability,
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

# Risk reduction effectiveness per intervention type
_INTERVENTION_EFFECTIVENESS: dict[str, float] = {
    "removal": 0.95,
    "encapsulation": 0.60,
    "ventilation": 0.50,
    "monitoring": 0.10,
    "containment": 0.45,
    "decontamination": 0.85,
    "replacement": 0.90,
    "treatment": 0.70,
    "sealing": 0.55,
    "extraction": 0.80,
}

# Swiss regulatory compliance thresholds (probability below which = compliant)
_COMPLIANCE_THRESHOLD: dict[str, float] = {
    "asbestos": 0.10,
    "pcb": 0.10,
    "lead": 0.15,
    "hap": 0.15,
    "radon": 0.20,
}

POLLUTANTS = ("asbestos", "pcb", "lead", "hap", "radon")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_building_or_raise(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _get_current_risk_scores(
    db: AsyncSession,
    building: Building,
) -> dict[str, float]:
    """Compute current risk probabilities for the building."""
    construction_year = building.construction_year
    canton = building.canton or ""

    scores: dict[str, float] = {
        "asbestos": calculate_asbestos_base_probability(construction_year),
        "pcb": calculate_pcb_base_probability(construction_year),
        "lead": calculate_lead_base_probability(construction_year),
        "hap": calculate_hap_base_probability(construction_year),
        "radon": calculate_radon_base_probability(canton),
    }

    # Override with diagnostic evidence if available
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building.id))
    diagnostics = diag_result.scalars().all()
    if diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())
        for sample in samples:
            pt = (sample.pollutant_type or "").lower()
            if pt in scores and sample.threshold_exceeded is not None:
                if sample.threshold_exceeded:
                    scores[pt] = max(scores[pt], 0.85)
                else:
                    scores[pt] = min(scores[pt], 0.10)

    return scores


def _apply_interventions(
    base_scores: dict[str, float],
    interventions: list[InterventionConfig],
) -> dict[str, float]:
    """Apply intervention effects to risk scores."""
    adjusted = dict(base_scores)
    for intervention in interventions:
        pollutant = intervention.pollutant.lower()
        if pollutant not in adjusted:
            continue
        effectiveness = _INTERVENTION_EFFECTIVENESS.get(intervention.intervention_type.lower(), 0.50)
        # Reduce risk by effectiveness factor
        adjusted[pollutant] = adjusted[pollutant] * (1.0 - effectiveness)
        adjusted[pollutant] = max(0.0, min(1.0, adjusted[pollutant]))
    return adjusted


def _compute_scenario_cost(interventions: list[InterventionConfig]) -> float:
    """Sum total cost of all interventions."""
    total = 0.0
    for iv in interventions:
        if iv.estimated_cost_chf > 0:
            total += iv.estimated_cost_chf
        else:
            # Estimate from surface and pollutant
            rate = _REMEDIATION_COST_PER_M2.get(iv.pollutant.lower(), 100.0)
            surface = iv.surface_m2 or 50.0
            total += rate * surface
    return round(total, 2)


def _compute_scenario_duration(interventions: list[InterventionConfig]) -> float:
    """Total duration: parallel where possible, sequential for same pollutant."""
    if not interventions:
        return 0.0
    # Group by pollutant — interventions on same pollutant are sequential
    by_pollutant: dict[str, float] = {}
    for iv in interventions:
        key = iv.pollutant.lower()
        by_pollutant[key] = by_pollutant.get(key, 0.0) + iv.duration_months
    # Different pollutants can run in parallel → take max
    return round(max(by_pollutant.values()), 1) if by_pollutant else 0.0


def _build_risk_reductions(
    before: dict[str, float],
    after: dict[str, float],
) -> list[RiskReductionDetail]:
    reductions = []
    for pollutant in POLLUTANTS:
        b = round(before.get(pollutant, 0.0), 4)
        a = round(after.get(pollutant, 0.0), 4)
        reductions.append(
            RiskReductionDetail(
                pollutant=pollutant,
                before=b,
                after=a,
                reduction=round(b - a, 4),
            )
        )
    return reductions


def _build_compliance_impacts(
    before: dict[str, float],
    after: dict[str, float],
) -> list[ComplianceImpact]:
    impacts = []
    for pollutant in POLLUTANTS:
        threshold = _COMPLIANCE_THRESHOLD.get(pollutant, 0.10)
        was = before.get(pollutant, 0.0) <= threshold
        now = after.get(pollutant, 0.0) <= threshold
        impacts.append(
            ComplianceImpact(
                pollutant=pollutant,
                was_compliant=was,
                now_compliant=now,
            )
        )
    return impacts


def _compliance_score(scores: dict[str, float]) -> float:
    """Fraction of pollutants that are compliant (0.0 to 1.0)."""
    if not scores:
        return 0.0
    compliant = sum(1 for p in POLLUTANTS if scores.get(p, 0.0) <= _COMPLIANCE_THRESHOLD.get(p, 0.10))
    return round(compliant / len(POLLUTANTS), 2)


def _evaluate_scenario(
    name: str,
    before: dict[str, float],
    interventions: list[InterventionConfig],
) -> ScenarioResult:
    """Evaluate a single scenario and return the result."""
    after = _apply_interventions(before, interventions)
    risk_reductions = _build_risk_reductions(before, after)
    overall = round(sum(r.reduction for r in risk_reductions) / len(risk_reductions), 4)
    compliance_impacts = _build_compliance_impacts(before, after)

    return ScenarioResult(
        name=name,
        total_cost_chf=_compute_scenario_cost(interventions),
        total_duration_months=_compute_scenario_duration(interventions),
        risk_reductions=risk_reductions,
        overall_risk_reduction=overall,
        compliance_impacts=compliance_impacts,
        compliance_score_before=_compliance_score(before),
        compliance_score_after=_compliance_score(after),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def create_scenario(
    db: AsyncSession,
    building_id: UUID,
    name: str,
    interventions: list[InterventionConfig],
) -> ScenarioResult:
    """
    Define a what-if scenario: select which interventions to apply, set
    timeline, budget constraints.  Returns projected outcome (risk reduction,
    cost, timeline, compliance impact).
    """
    building = await _get_building_or_raise(db, building_id)
    before = await _get_current_risk_scores(db, building)
    return _evaluate_scenario(name, before, interventions)


async def compare_scenarios(
    db: AsyncSession,
    building_id: UUID,
    scenario_configs: list[ScenarioCreateRequest],
) -> CompareResponse:
    """
    Side-by-side comparison of up to 5 scenarios: cost vs risk reduction
    chart data, timeline overlap, optimal pick recommendation.
    """
    if len(scenario_configs) > 5:
        raise ValueError("Maximum 5 scenarios for comparison")

    building = await _get_building_or_raise(db, building_id)
    before = await _get_current_risk_scores(db, building)

    results: list[ScenarioResult] = []
    for cfg in scenario_configs:
        result = _evaluate_scenario(cfg.name, before, cfg.interventions)
        results.append(result)

    # Recommend the scenario with best risk-reduction-to-cost ratio
    best_idx = 0
    best_ratio = -1.0
    for i, r in enumerate(results):
        cost = max(r.total_cost_chf, 1.0)  # avoid division by zero
        ratio = r.overall_risk_reduction / cost
        if ratio > best_ratio:
            best_ratio = ratio
            best_idx = i

    reason = (
        f"Scenario '{results[best_idx].name}' offers the best risk reduction "
        f"per CHF invested ({results[best_idx].overall_risk_reduction:.2%} "
        f"reduction for CHF {results[best_idx].total_cost_chf:,.0f})"
    )

    return CompareResponse(
        building_id=building_id,
        scenarios=results,
        recommended_index=best_idx,
        recommendation_reason=reason,
    )


async def find_optimal_scenario(
    db: AsyncSession,
    building_id: UUID,
    budget_limit_chf: float,
    time_limit_months: float,
) -> OptimalScenarioResponse:
    """
    Auto-generate best scenario within constraints: maximize risk reduction,
    respect budget/time, ensure regulatory compliance.  Uses a greedy algorithm
    that selects interventions by risk-reduction-per-CHF ratio.
    """
    building = await _get_building_or_raise(db, building_id)
    before = await _get_current_risk_scores(db, building)

    # Generate candidate interventions for each non-compliant pollutant
    candidates: list[InterventionConfig] = []
    for pollutant in POLLUTANTS:
        risk = before.get(pollutant, 0.0)
        threshold = _COMPLIANCE_THRESHOLD.get(pollutant, 0.10)
        if risk <= threshold:
            continue  # already compliant
        # Propose removal as default optimal intervention
        rate = _REMEDIATION_COST_PER_M2.get(pollutant, 100.0)
        surface = getattr(building, "surface_area_m2", None) or 200.0
        cost = rate * surface
        duration = 2.0 if pollutant == "radon" else 3.0
        candidates.append(
            InterventionConfig(
                intervention_type="removal",
                pollutant=pollutant,
                estimated_cost_chf=round(cost, 2),
                duration_months=duration,
                surface_m2=surface,
                description=f"Optimal {pollutant} removal",
            )
        )

    # Greedy selection: pick by best risk-reduction / cost ratio within budget
    selected: list[InterventionConfig] = []
    remaining_budget = budget_limit_chf

    # Sort candidates by risk_reduction / cost (higher risk → more value)
    def _value(iv: InterventionConfig) -> float:
        risk = before.get(iv.pollutant.lower(), 0.0)
        effectiveness = _INTERVENTION_EFFECTIVENESS.get(iv.intervention_type.lower(), 0.50)
        reduction = risk * effectiveness
        cost = max(iv.estimated_cost_chf, 1.0)
        return reduction / cost

    candidates.sort(key=_value, reverse=True)

    for candidate in candidates:
        if candidate.estimated_cost_chf > remaining_budget:
            continue
        duration = _compute_scenario_duration([*selected, candidate])
        if duration > time_limit_months:
            continue
        selected.append(candidate)
        remaining_budget -= candidate.estimated_cost_chf

    result = _evaluate_scenario("Optimal", before, selected)
    budget_used = budget_limit_chf - remaining_budget

    return OptimalScenarioResponse(
        building_id=building_id,
        scenario=result,
        interventions_selected=selected,
        budget_used_chf=round(budget_used, 2),
        budget_remaining_chf=round(remaining_budget, 2),
        time_used_months=result.total_duration_months,
    )


async def get_scenario_sensitivity(
    db: AsyncSession,
    building_id: UUID,
    scenario_config: ScenarioCreateRequest,
) -> SensitivityResponse:
    """
    Sensitivity analysis: how much does outcome change if cost +/-20%,
    timeline +/-30%, if one intervention is removed.  Returns robustness score.
    """
    building = await _get_building_or_raise(db, building_id)
    before = await _get_current_risk_scores(db, building)

    base = _evaluate_scenario(scenario_config.name, before, scenario_config.interventions)

    # Cost +20%
    cost_up_ivs = [
        InterventionConfig(
            intervention_type=iv.intervention_type,
            pollutant=iv.pollutant,
            estimated_cost_chf=round(iv.estimated_cost_chf * 1.2, 2),
            duration_months=iv.duration_months,
            surface_m2=iv.surface_m2,
            description=iv.description,
        )
        for iv in scenario_config.interventions
    ]
    cost_up = _evaluate_scenario("Cost +20%", before, cost_up_ivs)

    # Cost -20%
    cost_down_ivs = [
        InterventionConfig(
            intervention_type=iv.intervention_type,
            pollutant=iv.pollutant,
            estimated_cost_chf=round(iv.estimated_cost_chf * 0.8, 2),
            duration_months=iv.duration_months,
            surface_m2=iv.surface_m2,
            description=iv.description,
        )
        for iv in scenario_config.interventions
    ]
    cost_down = _evaluate_scenario("Cost -20%", before, cost_down_ivs)

    # Time +30%
    time_up_ivs = [
        InterventionConfig(
            intervention_type=iv.intervention_type,
            pollutant=iv.pollutant,
            estimated_cost_chf=iv.estimated_cost_chf,
            duration_months=round(iv.duration_months * 1.3, 1),
            surface_m2=iv.surface_m2,
            description=iv.description,
        )
        for iv in scenario_config.interventions
    ]
    time_up = _evaluate_scenario("Time +30%", before, time_up_ivs)

    # Time -30%
    time_down_ivs = [
        InterventionConfig(
            intervention_type=iv.intervention_type,
            pollutant=iv.pollutant,
            estimated_cost_chf=iv.estimated_cost_chf,
            duration_months=round(max(iv.duration_months * 0.7, 0.5), 1),
            surface_m2=iv.surface_m2,
            description=iv.description,
        )
        for iv in scenario_config.interventions
    ]
    time_down = _evaluate_scenario("Time -30%", before, time_down_ivs)

    # Removal variants: what happens if each intervention is removed
    removal_variants: list[SensitivityVariant] = []
    for i, iv in enumerate(scenario_config.interventions):
        remaining = [v for j, v in enumerate(scenario_config.interventions) if j != i]
        r = _evaluate_scenario(f"Without {iv.pollutant} {iv.intervention_type}", before, remaining)
        removal_variants.append(
            SensitivityVariant(
                label=f"Remove {iv.pollutant} {iv.intervention_type}",
                total_cost_chf=r.total_cost_chf,
                total_duration_months=r.total_duration_months,
                overall_risk_reduction=r.overall_risk_reduction,
            )
        )

    # Robustness score: how stable is the risk reduction across variants
    base_rr = base.overall_risk_reduction if base.overall_risk_reduction > 0 else 0.001
    all_rrs = [
        cost_up.overall_risk_reduction,
        cost_down.overall_risk_reduction,
        time_up.overall_risk_reduction,
        time_down.overall_risk_reduction,
    ] + [rv.overall_risk_reduction for rv in removal_variants]

    if all_rrs:
        max_deviation = max(abs(rr - base_rr) for rr in all_rrs)
        robustness = max(0.0, min(1.0, 1.0 - (max_deviation / base_rr)))
    else:
        robustness = 1.0

    return SensitivityResponse(
        building_id=building_id,
        base_scenario=base,
        cost_plus_20=SensitivityVariant(
            label="Cost +20%",
            total_cost_chf=cost_up.total_cost_chf,
            total_duration_months=cost_up.total_duration_months,
            overall_risk_reduction=cost_up.overall_risk_reduction,
        ),
        cost_minus_20=SensitivityVariant(
            label="Cost -20%",
            total_cost_chf=cost_down.total_cost_chf,
            total_duration_months=cost_down.total_duration_months,
            overall_risk_reduction=cost_down.overall_risk_reduction,
        ),
        time_plus_30=SensitivityVariant(
            label="Time +30%",
            total_cost_chf=time_up.total_cost_chf,
            total_duration_months=time_up.total_duration_months,
            overall_risk_reduction=time_up.overall_risk_reduction,
        ),
        time_minus_30=SensitivityVariant(
            label="Time -30%",
            total_cost_chf=time_down.total_cost_chf,
            total_duration_months=time_down.total_duration_months,
            overall_risk_reduction=time_down.overall_risk_reduction,
        ),
        removal_variants=removal_variants,
        robustness_score=round(robustness, 4),
    )
