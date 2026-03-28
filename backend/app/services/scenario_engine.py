"""
BatiConnect - Counterfactual Scenario Engine

Persisted scenario comparison engine that consumes canonical truth (passport,
completeness, readiness, trust) to evaluate different futures: do nothing,
postpone, phase, widen/reduce scope, sell before/after, insure before/after,
funding timing, alternative approach.

All projections are clearly marked as projections, not truth.
Trade-offs are explicit.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.scenario import SCENARIO_TYPES, CounterfactualScenario
from app.services.passport_service import _compute_passport_grade, get_passport_summary

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cost heuristics (CHF, simplified Swiss market rates)
# ---------------------------------------------------------------------------

_COST_INFLATION_ANNUAL = 0.03  # 3% annual cost inflation for construction
_RISK_ESCALATION_PER_YEAR = 0.05  # risk level escalation probability per year
_GRADE_DEGRADATION_YEARS = 3  # years before grade starts to degrade without action

# Typical cost multipliers by scenario type
_SCENARIO_COST_MULTIPLIER: dict[str, float] = {
    "do_nothing": 0.0,  # no cost, but risk increases
    "postpone": 1.0,  # same cost + inflation
    "phase": 1.15,  # phased is ~15% more expensive (mobilisation costs)
    "widen_scope": 1.30,
    "reduce_scope": 0.70,
    "sell_before_works": 0.0,  # no remediation cost, but lower sale price
    "sell_after_works": 1.0,  # full remediation cost
    "insure_before": 0.0,
    "insure_after": 1.0,
    "different_sequence": 1.05,
    "funding_timing": 0.85,  # subsidy reduces net cost
    "alternative_approach": 0.90,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def create_scenario(
    db: AsyncSession,
    building_id: UUID,
    scenario_type: str,
    title: str,
    assumptions: dict | None,
    created_by_id: UUID,
    org_id: UUID,
    *,
    case_id: UUID | None = None,
    description: str | None = None,
) -> CounterfactualScenario:
    """Create a scenario with assumptions. Status = draft."""
    # Validate building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        raise ValueError(f"Building {building_id} not found")

    if scenario_type not in SCENARIO_TYPES:
        raise ValueError(f"Unknown scenario_type '{scenario_type}'. Must be one of: {', '.join(SCENARIO_TYPES)}")

    scenario = CounterfactualScenario(
        building_id=building_id,
        case_id=case_id,
        organization_id=org_id,
        created_by_id=created_by_id,
        scenario_type=scenario_type,
        title=title,
        description=description,
        assumptions=assumptions or {},
        status="draft",
    )
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)
    return scenario


async def evaluate_scenario(
    db: AsyncSession,
    scenario_id: UUID,
) -> tuple[CounterfactualScenario, str]:
    """Evaluate a scenario by projecting outcomes.

    1. Get current building state (passport, completeness, readiness, trust)
    2. Apply assumptions to project future state
    3. Estimate cost implications
    4. Evaluate readiness implications
    5. Identify trade-offs and risks

    Returns (scenario, evaluation_summary).
    """
    result = await db.execute(select(CounterfactualScenario).where(CounterfactualScenario.id == scenario_id))
    scenario = result.scalar_one_or_none()
    if scenario is None:
        raise ValueError(f"Scenario {scenario_id} not found")

    # 1. Get current building state
    passport = await get_passport_summary(db, scenario.building_id)

    if passport is not None:
        current_trust = passport["knowledge_state"]["overall_trust"]
        current_completeness = passport["completeness"]["overall_score"]
        current_grade = passport["passport_grade"]
        current_readiness = passport["readiness"]
        current_blockers = sum(r["blockers_count"] for r in current_readiness.values() if isinstance(r, dict))
        current_contradictions = passport["contradictions"]["unresolved"]
    else:
        current_trust = 0.0
        current_completeness = 0.0
        current_grade = "F"
        current_readiness = {}
        current_blockers = 0
        current_contradictions = 0

    # Snapshot baseline
    scenario.baseline_grade = current_grade

    assumptions = scenario.assumptions or {}

    # 2. Apply assumptions to project future state
    projected = _project_state(
        scenario_type=scenario.scenario_type,
        assumptions=assumptions,
        current_trust=current_trust,
        current_completeness=current_completeness,
        current_grade=current_grade,
        current_blockers=current_blockers,
        current_contradictions=current_contradictions,
        current_readiness=current_readiness,
    )

    scenario.projected_grade = projected["grade"]
    scenario.projected_completeness = projected["completeness"]
    scenario.projected_readiness = projected["readiness"]
    scenario.projected_cost_chf = projected["cost_chf"]
    scenario.projected_risk_level = projected["risk_level"]
    scenario.projected_timeline_months = projected["timeline_months"]

    # 3. Estimate cost (baseline = proceed now)
    scenario.baseline_cost_chf = projected.get("baseline_cost_chf")

    # 4. Trade-offs
    scenario.advantages = projected["advantages"]
    scenario.disadvantages = projected["disadvantages"]
    scenario.risk_tradeoffs = projected["risk_tradeoffs"]

    # 5. Opportunity windows
    scenario.optimal_window_start = projected.get("optimal_window_start")
    scenario.optimal_window_end = projected.get("optimal_window_end")
    scenario.window_reason = projected.get("window_reason")

    scenario.status = "evaluated"

    await db.commit()
    await db.refresh(scenario)

    summary = _build_evaluation_summary(scenario)
    return scenario, summary


async def compare_scenarios(
    db: AsyncSession,
    building_id: UUID,
    scenario_ids: list[UUID],
) -> dict[str, Any]:
    """Compare multiple scenarios side by side.

    Returns comparison matrix with all projections aligned.
    """
    if len(scenario_ids) < 2:
        raise ValueError("At least 2 scenarios required for comparison")
    if len(scenario_ids) > 10:
        raise ValueError("Maximum 10 scenarios for comparison")

    result = await db.execute(
        select(CounterfactualScenario).where(
            CounterfactualScenario.id.in_(scenario_ids),
            CounterfactualScenario.building_id == building_id,
        )
    )
    scenarios = list(result.scalars().all())

    if len(scenarios) != len(scenario_ids):
        found_ids = {s.id for s in scenarios}
        missing = [str(sid) for sid in scenario_ids if sid not in found_ids]
        raise ValueError(f"Scenario(s) not found: {', '.join(missing)}")

    # Update status to compared for evaluated ones
    for s in scenarios:
        if s.status == "evaluated":
            s.status = "compared"
    await db.commit()

    # Build baseline from first evaluated scenario (they share the same building)
    baseline_grade = None
    baseline_cost = None
    for s in scenarios:
        if s.baseline_grade:
            baseline_grade = s.baseline_grade
            baseline_cost = s.baseline_cost_chf
            break

    # Recommendation heuristic: pick the best projected grade + lowest cost
    recommendation = _generate_comparison_recommendation(scenarios)

    return {
        "building_id": str(building_id),
        "baseline_grade": baseline_grade,
        "baseline_cost_chf": baseline_cost,
        "scenarios": scenarios,
        "recommendation": recommendation,
    }


async def generate_standard_scenarios(
    db: AsyncSession,
    building_id: UUID,
    created_by_id: UUID,
    org_id: UUID,
    *,
    case_id: UUID | None = None,
) -> list[CounterfactualScenario]:
    """Auto-generate standard scenarios for common what-ifs.

    Generates 6 standard scenarios:
    - Ne rien faire pendant 1 an
    - Ne rien faire pendant 3 ans
    - Proceder maintenant
    - Phasage sur 2 ans
    - Vendre avant travaux
    - Vendre apres travaux
    """
    # Verify building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        raise ValueError(f"Building {building_id} not found")

    standard_defs = [
        {
            "scenario_type": "do_nothing",
            "title": "Ne rien faire pendant 1 an",
            "description": "Projection de l'etat du batiment apres 1 an sans intervention.",
            "assumptions": {"delay_months": 12, "action": "none"},
        },
        {
            "scenario_type": "do_nothing",
            "title": "Ne rien faire pendant 3 ans",
            "description": "Projection de l'etat du batiment apres 3 ans sans intervention.",
            "assumptions": {"delay_months": 36, "action": "none"},
        },
        {
            "scenario_type": "alternative_approach",
            "title": "Proceder maintenant",
            "description": "Demarrer les travaux immediatement avec le perimetre actuel.",
            "assumptions": {"delay_months": 0, "action": "proceed_now"},
        },
        {
            "scenario_type": "phase",
            "title": "Phasage sur 2 ans",
            "description": "Repartir les travaux en phases sur 24 mois.",
            "assumptions": {"delay_months": 0, "phase_count": 3, "total_months": 24},
        },
        {
            "scenario_type": "sell_before_works",
            "title": "Vendre avant travaux",
            "description": "Vendre le batiment en l'etat, sans remediation prealable.",
            "assumptions": {"action": "sell", "timing": "before_works"},
        },
        {
            "scenario_type": "sell_after_works",
            "title": "Vendre apres travaux",
            "description": "Remedier puis vendre avec un dossier complet.",
            "assumptions": {"action": "sell", "timing": "after_works"},
        },
    ]

    scenarios: list[CounterfactualScenario] = []
    for defn in standard_defs:
        scenario = CounterfactualScenario(
            building_id=building_id,
            case_id=case_id,
            organization_id=org_id,
            created_by_id=created_by_id,
            scenario_type=defn["scenario_type"],
            title=defn["title"],
            description=defn["description"],
            assumptions=defn["assumptions"],
            status="draft",
        )
        db.add(scenario)
        scenarios.append(scenario)

    await db.commit()
    for s in scenarios:
        await db.refresh(s)

    return scenarios


async def get_building_scenarios(
    db: AsyncSession,
    building_id: UUID,
    *,
    status: str | None = None,
) -> list[CounterfactualScenario]:
    """List all scenarios for a building."""
    query = (
        select(CounterfactualScenario)
        .where(CounterfactualScenario.building_id == building_id)
        .order_by(CounterfactualScenario.created_at.desc())
    )
    if status:
        query = query.where(CounterfactualScenario.status == status)
    result = await db.execute(query)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Projection logic
# ---------------------------------------------------------------------------


def _project_state(
    *,
    scenario_type: str,
    assumptions: dict,
    current_trust: float,
    current_completeness: float,
    current_grade: str,
    current_blockers: int,
    current_contradictions: int,
    current_readiness: dict,
) -> dict[str, Any]:
    """Project future state based on scenario type and assumptions.

    Returns a dict with projected metrics, trade-offs, and windows.
    """
    delay_months = assumptions.get("delay_months", 0)
    delay_years = delay_months / 12.0

    # Baseline cost estimate (heuristic: 50k CHF base for a typical building)
    baseline_cost = 50_000.0

    # Start with current values
    proj_trust = current_trust
    proj_completeness = current_completeness
    proj_blockers = current_blockers
    proj_contradictions = current_contradictions
    proj_cost = baseline_cost
    proj_timeline = 0
    advantages: list[str] = []
    disadvantages: list[str] = []
    risk_tradeoffs: list[dict] = []

    if scenario_type == "do_nothing":
        proj_cost = 0.0
        proj_timeline = delay_months or 12

        # Trust and completeness degrade over time
        degradation = min(0.15, delay_years * 0.05)
        proj_trust = max(0.0, proj_trust - degradation)
        proj_completeness = max(0.0, proj_completeness - degradation * 0.5)
        proj_blockers = current_blockers + max(0, int(delay_years))

        advantages = ["Aucun cout immediat", "Pas de perturbation des occupants"]
        disadvantages = [
            "Degradation de la note du batiment",
            "Risque reglementaire croissant",
            "Cout futur potentiellement plus eleve",
        ]
        risk_tradeoffs = [
            {
                "risk": "Degradation reglementaire",
                "probability": min(0.9, 0.3 + delay_years * 0.2),
                "impact": "high",
            },
            {
                "risk": "Augmentation des couts",
                "probability": min(0.8, delay_years * _COST_INFLATION_ANNUAL * 10),
                "impact": "medium",
            },
        ]

    elif scenario_type == "postpone":
        inflation_factor = (1 + _COST_INFLATION_ANNUAL) ** delay_years
        proj_cost = baseline_cost * inflation_factor
        proj_timeline = delay_months + 6  # delay + works

        # Slight degradation during wait
        degradation = min(0.10, delay_years * 0.03)
        proj_trust = max(0.0, proj_trust - degradation)
        proj_completeness = max(0.0, proj_completeness - degradation * 0.3)

        # After works, trust improves
        proj_trust = min(1.0, proj_trust + 0.10)
        proj_completeness = min(1.0, proj_completeness + 0.15)
        proj_blockers = max(0, proj_blockers - 2)

        advantages = [
            "Report des depenses",
            "Temps pour preparer le financement",
        ]
        disadvantages = [
            f"Surcout d'inflation: ~{(inflation_factor - 1) * 100:.0f}%",
            "Risque reglementaire pendant la periode d'attente",
        ]
        risk_tradeoffs = [
            {
                "risk": "Inflation des couts de construction",
                "probability": 0.8,
                "impact": "medium",
            },
        ]

    elif scenario_type == "phase":
        phase_count = assumptions.get("phase_count", 3)
        total_months = assumptions.get("total_months", 24)
        multiplier = _SCENARIO_COST_MULTIPLIER["phase"]
        proj_cost = baseline_cost * multiplier
        proj_timeline = total_months

        proj_trust = min(1.0, proj_trust + 0.08)
        proj_completeness = min(1.0, proj_completeness + 0.12)
        proj_blockers = max(0, proj_blockers - 1)

        advantages = [
            f"Repartition des couts sur {phase_count} phases",
            "Moins de perturbation par phase",
            "Possibilite d'ajuster entre les phases",
        ]
        disadvantages = [
            f"Surcout de mobilisation: ~{(multiplier - 1) * 100:.0f}%",
            f"Duree totale plus longue: {total_months} mois",
        ]
        risk_tradeoffs = [
            {
                "risk": "Cout de mobilisation supplementaire",
                "probability": 0.95,
                "impact": "low",
            },
        ]

    elif scenario_type == "widen_scope":
        multiplier = _SCENARIO_COST_MULTIPLIER["widen_scope"]
        proj_cost = baseline_cost * multiplier
        proj_timeline = 9

        proj_trust = min(1.0, proj_trust + 0.15)
        proj_completeness = min(1.0, proj_completeness + 0.20)
        proj_blockers = max(0, proj_blockers - 3)

        advantages = [
            "Traitement plus complet",
            "Meilleure note projetee",
            "Reduction significative des risques",
        ]
        disadvantages = [
            f"Cout plus eleve: +{(multiplier - 1) * 100:.0f}%",
            "Perturbation plus importante",
        ]

    elif scenario_type == "reduce_scope":
        multiplier = _SCENARIO_COST_MULTIPLIER["reduce_scope"]
        proj_cost = baseline_cost * multiplier
        proj_timeline = 4

        proj_trust = min(1.0, proj_trust + 0.05)
        proj_completeness = min(1.0, proj_completeness + 0.08)
        proj_blockers = max(0, proj_blockers - 1)

        advantages = [
            f"Cout reduit: -{(1 - multiplier) * 100:.0f}%",
            "Delai plus court",
        ]
        disadvantages = [
            "Traitement partiel — risques residuels",
            "Note du batiment moins amelioree",
        ]
        risk_tradeoffs = [
            {
                "risk": "Risques residuels non traites",
                "probability": 0.6,
                "impact": "medium",
            },
        ]

    elif scenario_type == "sell_before_works":
        proj_cost = 0.0
        proj_timeline = 3

        # No improvement — current state is what buyer gets
        advantages = [
            "Aucun cout de remediation",
            "Delai court",
            "Transfert du risque a l'acheteur",
        ]
        disadvantages = [
            "Prix de vente reduit (decote polluants)",
            "Dossier incomplet peut bloquer la vente",
            "Responsabilite residuelle possible",
        ]
        risk_tradeoffs = [
            {
                "risk": "Decote sur prix de vente",
                "probability": 0.9,
                "impact": "high",
            },
            {
                "risk": "Responsabilite residuelle",
                "probability": 0.4,
                "impact": "high",
            },
        ]

    elif scenario_type == "sell_after_works":
        proj_cost = baseline_cost
        proj_timeline = 9

        proj_trust = min(1.0, proj_trust + 0.15)
        proj_completeness = min(1.0, proj_completeness + 0.20)
        proj_blockers = max(0, proj_blockers - 3)

        advantages = [
            "Prix de vente maximal",
            "Dossier complet pour l'acheteur",
            "Pas de responsabilite residuelle",
        ]
        disadvantages = [
            "Investissement initial important",
            "Delai avant mise en vente",
        ]

    elif scenario_type == "insure_before":
        proj_cost = 0.0
        proj_timeline = 1

        advantages = [
            "Protection immediate",
            "Pas de travaux requis",
        ]
        disadvantages = [
            "Primes d'assurance elevees (risque non traite)",
            "Couverture potentiellement limitee",
            "Exclusions possibles pour polluants connus",
        ]
        risk_tradeoffs = [
            {
                "risk": "Primes excessives ou refus",
                "probability": 0.7 if current_grade in ("D", "F") else 0.3,
                "impact": "high",
            },
        ]

    elif scenario_type == "insure_after":
        proj_cost = baseline_cost
        proj_timeline = 8

        proj_trust = min(1.0, proj_trust + 0.15)
        proj_completeness = min(1.0, proj_completeness + 0.18)
        proj_blockers = max(0, proj_blockers - 3)

        advantages = [
            "Primes d'assurance reduites",
            "Couverture complete",
            "Note amelioree",
        ]
        disadvantages = [
            "Investissement initial requis",
            "Delai avant assurabilite optimale",
        ]

    elif scenario_type == "different_sequence":
        multiplier = _SCENARIO_COST_MULTIPLIER["different_sequence"]
        proj_cost = baseline_cost * multiplier
        proj_timeline = 7

        proj_trust = min(1.0, proj_trust + 0.12)
        proj_completeness = min(1.0, proj_completeness + 0.15)
        proj_blockers = max(0, proj_blockers - 2)

        advantages = [
            "Sequencage optimise",
            "Synergies entre interventions",
        ]
        disadvantages = [
            "Leger surcout de coordination",
        ]

    elif scenario_type == "funding_timing":
        multiplier = _SCENARIO_COST_MULTIPLIER["funding_timing"]
        funding_scenario = assumptions.get("funding_scenario", "with_subsidy")
        proj_cost = baseline_cost * multiplier
        proj_timeline = 8

        proj_trust = min(1.0, proj_trust + 0.12)
        proj_completeness = min(1.0, proj_completeness + 0.15)
        proj_blockers = max(0, proj_blockers - 2)

        advantages = [
            f"Cout net reduit: -{(1 - multiplier) * 100:.0f}% ({funding_scenario})",
            "Meilleur retour sur investissement",
        ]
        disadvantages = [
            "Delai pour obtenir le financement",
            "Conditions d'octroi a respecter",
        ]

    elif scenario_type == "alternative_approach":
        if assumptions.get("action") == "proceed_now":
            proj_cost = baseline_cost
            proj_timeline = 6
            proj_trust = min(1.0, proj_trust + 0.15)
            proj_completeness = min(1.0, proj_completeness + 0.20)
            proj_blockers = max(0, proj_blockers - 3)

            advantages = [
                "Resultats les plus rapides",
                "Meilleure amelioration de la note",
            ]
            disadvantages = [
                "Investissement immediat",
                "Perturbation a court terme",
            ]
        else:
            multiplier = _SCENARIO_COST_MULTIPLIER["alternative_approach"]
            proj_cost = baseline_cost * multiplier
            proj_timeline = 7
            proj_trust = min(1.0, proj_trust + 0.10)
            proj_completeness = min(1.0, proj_completeness + 0.12)
            proj_blockers = max(0, proj_blockers - 2)

            advantages = ["Approche differente potentiellement moins couteuse"]
            disadvantages = ["Resultats incertains"]
    else:
        # Fallback for unknown types (shouldn't happen given validation)
        proj_timeline = 6
        proj_cost = baseline_cost

    # Compute projected grade
    proj_grade = _compute_passport_grade(
        trust=proj_trust,
        completeness=proj_completeness,
        blockers=proj_blockers,
        unresolved_contradictions=proj_contradictions,
    )

    # Determine projected risk level
    proj_risk = _estimate_risk_level(proj_trust, proj_completeness, proj_blockers, scenario_type, delay_months)

    # Project readiness
    proj_readiness = _project_readiness(current_readiness, scenario_type, proj_blockers)

    # Opportunity window
    window_start, window_end, window_reason = _compute_window(scenario_type, assumptions)

    return {
        "grade": proj_grade,
        "completeness": round(proj_completeness, 4),
        "readiness": proj_readiness,
        "cost_chf": round(proj_cost, 2) if proj_cost is not None else None,
        "risk_level": proj_risk,
        "timeline_months": proj_timeline,
        "baseline_cost_chf": round(baseline_cost, 2),
        "advantages": advantages,
        "disadvantages": disadvantages,
        "risk_tradeoffs": risk_tradeoffs,
        "optimal_window_start": window_start,
        "optimal_window_end": window_end,
        "window_reason": window_reason,
    }


def _estimate_risk_level(
    trust: float,
    completeness: float,
    blockers: int,
    scenario_type: str,
    delay_months: int,
) -> str:
    """Estimate risk level from projected metrics."""
    # Do-nothing scenarios with long delays are high risk
    if scenario_type == "do_nothing" and delay_months >= 24:
        return "high"
    if scenario_type == "do_nothing" and delay_months >= 12:
        return "medium"

    # Risk based on combined metrics
    score = trust * 0.4 + completeness * 0.4 + (1.0 if blockers == 0 else 0.0) * 0.2
    if score >= 0.8:
        return "low"
    if score >= 0.5:
        return "medium"
    if score >= 0.3:
        return "high"
    return "critical"


def _project_readiness(
    current_readiness: dict,
    scenario_type: str,
    projected_blockers: int,
) -> dict:
    """Project readiness based on scenario type."""
    proj = {}
    for rtype, rdata in current_readiness.items():
        if not isinstance(rdata, dict):
            proj[rtype] = rdata
            continue

        current_status = rdata.get("status", "not_evaluated")

        if scenario_type == "do_nothing":
            # Do nothing degrades readiness
            if current_status == "ready":
                proj[rtype] = "conditional"
            elif current_status == "conditional":
                proj[rtype] = "blocked"
            else:
                proj[rtype] = current_status
        elif scenario_type in ("sell_before_works", "insure_before"):
            # No change
            proj[rtype] = current_status
        else:
            # Most action scenarios improve readiness
            if projected_blockers == 0:
                proj[rtype] = "ready"
            elif current_status == "blocked" and projected_blockers < rdata.get("blockers_count", 0):
                proj[rtype] = "conditional"
            else:
                proj[rtype] = current_status

    return proj


def _compute_window(
    scenario_type: str,
    assumptions: dict,
) -> tuple[date | None, date | None, str | None]:
    """Compute optimal execution window for a scenario."""
    today = datetime.now(UTC).date()

    if scenario_type == "do_nothing":
        return None, None, None

    if scenario_type in ("sell_before_works", "sell_after_works"):
        # Real estate market windows: spring and autumn
        # Next good window
        if today.month <= 3:
            start = date(today.year, 3, 1)
            end = date(today.year, 6, 30)
            reason = "Fenetre immobiliere printaniere"
        elif today.month <= 9:
            start = date(today.year, 9, 1)
            end = date(today.year, 11, 30)
            reason = "Fenetre immobiliere automnale"
        else:
            start = date(today.year + 1, 3, 1)
            end = date(today.year + 1, 6, 30)
            reason = "Fenetre immobiliere printaniere (annee suivante)"
        return start, end, reason

    if scenario_type in ("funding_timing",):
        # Subsidy windows typically have annual deadlines
        next_deadline = date(today.year + 1, 1, 31)
        start = today
        return start, next_deadline, "Delai de depot des demandes de subvention"

    if scenario_type == "postpone":
        delay_months = assumptions.get("delay_months", 6)
        start = today + timedelta(days=delay_months * 30)
        end = start + timedelta(days=90)
        return start, end, f"Debut prevu apres report de {delay_months} mois"

    # Default: start within 3 months
    start = today
    end = today + timedelta(days=90)
    return start, end, "Fenetre optimale: demarrage dans les 3 prochains mois"


def _build_evaluation_summary(scenario: CounterfactualScenario) -> str:
    """Build a human-readable evaluation summary."""
    parts = [f"Scenario '{scenario.title}' evalue."]

    if scenario.baseline_grade and scenario.projected_grade:
        if scenario.projected_grade != scenario.baseline_grade:
            parts.append(f"Note projetee: {scenario.baseline_grade} -> {scenario.projected_grade}.")
        else:
            parts.append(f"Note projetee: {scenario.projected_grade} (inchangee).")

    if scenario.projected_cost_chf is not None:
        parts.append(f"Cout projete: CHF {scenario.projected_cost_chf:,.0f}.")

    if scenario.projected_timeline_months:
        parts.append(f"Delai: {scenario.projected_timeline_months} mois.")

    if scenario.projected_risk_level:
        parts.append(f"Niveau de risque projete: {scenario.projected_risk_level}.")

    advantages = scenario.advantages or []
    disadvantages = scenario.disadvantages or []
    parts.append(f"Avantages: {len(advantages)}. Inconvenients: {len(disadvantages)}.")

    return " ".join(parts)


def _generate_comparison_recommendation(scenarios: list[CounterfactualScenario]) -> str | None:
    """Generate a simple recommendation from compared scenarios."""
    evaluated = [s for s in scenarios if s.status in ("evaluated", "compared")]
    if not evaluated:
        return None

    # Rank by grade (A best), then by cost (lower better)
    grade_rank = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1, None: 0}

    def score(s: CounterfactualScenario) -> tuple[int, float]:
        g = grade_rank.get(s.projected_grade, 0)
        c = s.projected_cost_chf if s.projected_cost_chf is not None else 999_999
        return (g, -c)

    best = max(evaluated, key=score)
    return (
        f"Scenario recommande: '{best.title}' "
        f"(note projetee: {best.projected_grade or '?'}, "
        f"cout: CHF {best.projected_cost_chf:,.0f} "
        f"si applicable)."
        if best.projected_cost_chf is not None
        else f"Scenario recommande: '{best.title}' (note projetee: {best.projected_grade or '?'})."
    )
