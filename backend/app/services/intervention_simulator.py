"""
SwissBuildingOS - Intervention Simulator

Predicts how planned interventions would affect a building's readiness,
trust, and compliance state. This is a read-only simulation — no data
is persisted.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ACTION_STATUS_OPEN
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.schemas.simulation import (
    SimulationImpactSummary,
    SimulationInput,
    SimulationResult,
    SimulationStateSnapshot,
)
from app.services.passport_service import _compute_passport_grade, get_passport_summary

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intervention-type to pollutant resolution mapping
# ---------------------------------------------------------------------------
# Some intervention types imply a specific pollutant even when not explicit.
_TYPE_IMPLIED_POLLUTANT: dict[str, str] = {
    "asbestos_removal": "asbestos",
    "decontamination": "asbestos",
}

# Intervention types that are considered high-impact for remediation
_REMEDIATION_TYPES = {
    "asbestos_removal",
    "decontamination",
    "demolition",
    "renovation",
}

# Intervention types that are evidence/monitoring (lower impact on risk)
_MONITORING_TYPES = {
    "inspection",
    "diagnostic",
    "maintenance",
}

# Trust improvement per intervention (heuristic)
_TRUST_BOOST_REMEDIATION = 0.05
_TRUST_BOOST_MONITORING = 0.02
_TRUST_BOOST_OTHER = 0.03

# Completeness improvement per intervention (heuristic)
_COMPLETENESS_BOOST_REMEDIATION = 0.04
_COMPLETENESS_BOOST_MONITORING = 0.02
_COMPLETENESS_BOOST_OTHER = 0.02


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def simulate_interventions(
    db: AsyncSession,
    building_id: UUID,
    planned_interventions: list[SimulationInput],
) -> SimulationResult:
    """Simulate the effect of planned interventions on a building.

    Returns current state, projected state, impact summary, and recommendations.
    Raises ValueError if the building does not exist.
    """
    # 0. Verify building exists
    building_result = await db.execute(select(Building).where(Building.id == building_id))
    building = building_result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    # 1. Get current passport summary
    passport = await get_passport_summary(db, building_id)

    if passport is not None:
        current_trust = passport["knowledge_state"]["overall_trust"]
        current_completeness = passport["completeness"]["overall_score"]
        current_grade = passport["passport_grade"]
        current_blockers = sum(r["blockers_count"] for r in passport["readiness"].values() if isinstance(r, dict))
    else:
        current_trust = 0.0
        current_completeness = 0.0
        current_grade = "F"
        current_blockers = 0

    # 2. Count current open actions
    open_actions_result = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .where(
            and_(
                ActionItem.building_id == building_id,
                ActionItem.status == ACTION_STATUS_OPEN,
            )
        )
    )
    open_actions_count = open_actions_result.scalar() or 0

    current_state = SimulationStateSnapshot(
        passport_grade=current_grade,
        trust_score=round(current_trust, 4),
        completeness_score=round(current_completeness, 4),
        blocker_count=current_blockers,
        open_actions_count=open_actions_count,
    )

    # 3. If no interventions planned, return unchanged state
    if not planned_interventions:
        return SimulationResult(
            current_state=current_state,
            projected_state=current_state.model_copy(),
            impact_summary=SimulationImpactSummary(
                actions_resolved=0,
                readiness_improvement="no change",
                trust_delta=0.0,
                completeness_delta=0.0,
                grade_change=None,
                risk_reduction={},
                estimated_total_cost=None,
            ),
            recommendations=_generate_recommendations(current_grade, current_trust, current_completeness, []),
        )

    # 4. Load open actions and positive samples for matching
    open_actions = await _load_open_actions(db, building_id)
    positive_samples = await _load_positive_samples(db, building_id)

    # 5. Estimate impact of each planned intervention
    actions_resolved = 0
    blockers_removed = 0
    trust_boost = 0.0
    completeness_boost = 0.0
    total_cost = 0.0
    has_cost = False
    risk_changes: dict[str, list[str]] = defaultdict(list)
    resolved_action_ids: set[UUID] = set()

    for intervention in planned_interventions:
        itype = intervention.intervention_type
        pollutant = intervention.target_pollutant or _TYPE_IMPLIED_POLLUTANT.get(itype)

        # Cost aggregation
        if intervention.estimated_cost is not None:
            total_cost += intervention.estimated_cost
            has_cost = True

        # Trust boost
        if itype in _REMEDIATION_TYPES:
            trust_boost += _TRUST_BOOST_REMEDIATION
        elif itype in _MONITORING_TYPES:
            trust_boost += _TRUST_BOOST_MONITORING
        else:
            trust_boost += _TRUST_BOOST_OTHER

        # Completeness boost
        if itype in _REMEDIATION_TYPES:
            completeness_boost += _COMPLETENESS_BOOST_REMEDIATION
        elif itype in _MONITORING_TYPES:
            completeness_boost += _COMPLETENESS_BOOST_MONITORING
        else:
            completeness_boost += _COMPLETENESS_BOOST_OTHER

        # Match open actions that this intervention would resolve
        matched = _match_actions(open_actions, itype, pollutant, intervention.target_zone_id, resolved_action_ids)
        actions_resolved += matched
        # Remediation-type interventions also reduce blockers
        if itype in _REMEDIATION_TYPES and matched > 0:
            blockers_removed += min(matched, max(current_blockers - blockers_removed, 0))

        # Risk reduction per pollutant
        if pollutant and itype in _REMEDIATION_TYPES:
            affected_risks = _estimate_risk_reduction(positive_samples, pollutant)
            if affected_risks:
                risk_changes[pollutant].append(affected_risks)

    # 6. Project new state
    projected_trust = min(1.0, current_trust + trust_boost)
    projected_completeness = min(1.0, current_completeness + completeness_boost)
    projected_blockers = max(0, current_blockers - blockers_removed)
    projected_open_actions = max(0, open_actions_count - actions_resolved)

    # Compute projected grade
    projected_grade = _compute_passport_grade(
        trust=projected_trust,
        completeness=projected_completeness,
        blockers=projected_blockers,
        unresolved_contradictions=0,  # We don't simulate contradiction resolution
    )

    projected_state = SimulationStateSnapshot(
        passport_grade=projected_grade,
        trust_score=round(projected_trust, 4),
        completeness_score=round(projected_completeness, 4),
        blocker_count=projected_blockers,
        open_actions_count=projected_open_actions,
    )

    # 7. Build impact summary
    grade_change = f"{current_grade} → {projected_grade}" if projected_grade != current_grade else None

    if blockers_removed > 0 and projected_blockers == 0 and current_blockers > 0:
        readiness_improvement = "blocked → ready"
    elif blockers_removed > 0:
        readiness_improvement = f"{blockers_removed} blockers removed"
    else:
        readiness_improvement = "no change"

    risk_reduction_summary: dict[str, str] = {}
    for pollutant, changes in risk_changes.items():
        # Take the most impactful change
        risk_reduction_summary[pollutant] = changes[0] if changes else "no change"

    impact_summary = SimulationImpactSummary(
        actions_resolved=actions_resolved,
        readiness_improvement=readiness_improvement,
        trust_delta=round(projected_trust - current_trust, 4),
        completeness_delta=round(projected_completeness - current_completeness, 4),
        grade_change=grade_change,
        risk_reduction=risk_reduction_summary,
        estimated_total_cost=round(total_cost, 2) if has_cost else None,
    )

    # 8. Generate recommendations
    simulated_pollutants = {
        pi.target_pollutant or _TYPE_IMPLIED_POLLUTANT.get(pi.intervention_type) for pi in planned_interventions
    } - {None}
    recommendations = _generate_recommendations(
        projected_grade,
        projected_trust,
        projected_completeness,
        list(simulated_pollutants),
    )

    return SimulationResult(
        current_state=current_state,
        projected_state=projected_state,
        impact_summary=impact_summary,
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _load_open_actions(db: AsyncSession, building_id: UUID) -> list[ActionItem]:
    """Load all open action items for a building."""
    result = await db.execute(
        select(ActionItem).where(
            and_(
                ActionItem.building_id == building_id,
                ActionItem.status == ACTION_STATUS_OPEN,
            )
        )
    )
    return list(result.scalars().all())


async def _load_positive_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    """Load positive samples from all building diagnostics."""
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            and_(
                Diagnostic.building_id == building_id,
                Sample.threshold_exceeded.is_(True),
            )
        )
    )
    return list(result.scalars().all())


def _match_actions(
    actions: list[ActionItem],
    intervention_type: str,
    pollutant: str | None,
    zone_id: UUID | None,
    already_resolved: set[UUID],
) -> int:
    """Count how many open actions would be resolved by this intervention.

    Matching logic:
    - Remediation-type interventions resolve remediation/investigation actions
    - If pollutant is specified, match actions whose title/metadata mention it
    - If zone_id is specified, match actions with matching zone in metadata
    - Each action can only be resolved once across all interventions
    """
    count = 0
    for action in actions:
        if action.id in already_resolved:
            continue

        # Check action type compatibility
        if intervention_type in _REMEDIATION_TYPES:
            if action.action_type not in ("remediation", "investigation", "procurement"):
                continue
        elif intervention_type in _MONITORING_TYPES:
            if action.action_type not in ("investigation", "documentation"):
                continue
        else:
            continue

        # Pollutant matching (if specified)
        if pollutant:
            title_lower = (action.title or "").lower()
            meta = action.metadata_json or {}
            meta_pollutant = meta.get("pollutant", "")
            if pollutant.lower() not in title_lower and pollutant.lower() != (meta_pollutant or "").lower():
                continue

        # Zone matching (if specified)
        if zone_id:
            meta = action.metadata_json or {}
            action_zone = meta.get("zone_id")
            if action_zone and str(action_zone) != str(zone_id):
                continue

        already_resolved.add(action.id)
        count += 1

    return count


def _estimate_risk_reduction(samples: list[Sample], pollutant: str) -> str:
    """Estimate risk level change for a pollutant after remediation."""
    matching = [s for s in samples if (s.pollutant_type or "").lower() == pollutant.lower()]
    if not matching:
        return ""

    # Find highest current risk
    risk_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
    max_risk = max((risk_order.get(s.risk_level or "unknown", 0) for s in matching), default=0)
    risk_names = {v: k for k, v in risk_order.items()}
    current_risk = risk_names.get(max_risk, "unknown")

    # After remediation, risk drops by ~2 levels
    projected_risk_val = max(0, max_risk - 2)
    projected_risk = risk_names.get(projected_risk_val, "unknown")

    if current_risk == projected_risk:
        return "no change"
    return f"{current_risk} → {projected_risk}"


def _generate_recommendations(
    current_grade: str,
    trust: float,
    completeness: float,
    already_targeted_pollutants: list[str],
) -> list[str]:
    """Generate improvement recommendations based on projected state."""
    recs: list[str] = []

    all_pollutants = {"asbestos", "pcb", "lead", "hap", "radon"}
    untargeted = all_pollutants - set(p.lower() for p in already_targeted_pollutants)

    if current_grade in ("C", "D", "F"):
        if trust < 0.6:
            recs.append("Consider adding diagnostic inspections to improve trust score above 0.6")
        if completeness < 0.7:
            recs.append("Complete missing documentation to improve completeness above 0.7")

    if current_grade in ("B", "C") and untargeted:
        # Suggest targeting untargeted pollutants
        for p in sorted(untargeted):
            recs.append(f"Consider adding {p} remediation to improve grade to {_next_grade(current_grade)}")
            if len(recs) >= 3:
                break

    if current_grade == "A":
        recs.append("Building is at highest grade — maintain with regular inspections")

    if not recs:
        recs.append("No additional recommendations at this time")

    return recs


def _next_grade(grade: str) -> str:
    """Return the next better grade."""
    order = {"F": "D", "D": "C", "C": "B", "B": "A", "A": "A"}
    return order.get(grade, "A")
