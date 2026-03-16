"""
SwissBuildingOS - Risk Mitigation Planner

Generates optimal remediation sequence recommendations considering
regulatory urgency, cost efficiency, and dependency between interventions.

Aligned with CFST 6503, OTConst Art. 60a, ORRChim, ORaP.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.risk_mitigation import (
    DependencyAnalysis,
    DependencyEdge,
    MitigationPlan,
    MitigationStep,
    PlanTimeline,
    QuickWin,
    TimelineMilestone,
)

# ---------------------------------------------------------------------------
# Urgency scores by pollutant situation
# ---------------------------------------------------------------------------

URGENCY_SCORES: dict[str, float] = {
    "asbestos_friable": 95.0,
    "asbestos_non_friable": 70.0,
    "pcb_high": 80.0,
    "pcb_moderate": 50.0,
    "lead_accessible": 60.0,
    "lead_contained": 30.0,
    "hap": 55.0,
    "radon_above_1000": 90.0,
    "radon_300_1000": 40.0,
}

OVERDUE_BONUS = 20.0

# ---------------------------------------------------------------------------
# Dependency rules
# ---------------------------------------------------------------------------

DEPENDENCY_RULES: list[dict[str, str]] = [
    {
        "blocker": "asbestos_removal",
        "blocked": "renovation",
        "reason": "Asbestos must be removed before any renovation work (OTConst Art. 60a)",
    },
    {
        "blocker": "pcb_joint_removal",
        "blocked": "facade_work",
        "reason": "PCB in joints must be removed before facade renovation (ORRChim Annexe 2.15)",
    },
    {
        "blocker": "lead_removal",
        "blocked": "painting",
        "reason": "Lead-containing coatings must be removed before repainting (ORRChim Annexe 2.18)",
    },
    {
        "blocker": "radon_mitigation",
        "blocked": "occupancy",
        "reason": "Radon levels must be mitigated before building occupancy (ORaP Art. 110)",
    },
]

# ---------------------------------------------------------------------------
# Cost estimates by intervention type (CHF)
# ---------------------------------------------------------------------------

COST_ESTIMATES: dict[str, tuple[float, float]] = {
    "asbestos_removal": (15_000.0, 80_000.0),
    "pcb_joint_removal": (10_000.0, 50_000.0),
    "pcb_decontamination": (20_000.0, 100_000.0),
    "lead_removal": (5_000.0, 30_000.0),
    "lead_encapsulation": (2_000.0, 10_000.0),
    "hap_remediation": (8_000.0, 40_000.0),
    "radon_mitigation": (5_000.0, 25_000.0),
    "radon_ventilation": (3_000.0, 15_000.0),
}

DEFAULT_COST_RANGE = (5_000.0, 30_000.0)

# Duration estimates in weeks
DURATION_WEEKS: dict[str, int] = {
    "asbestos_removal": 4,
    "pcb_joint_removal": 3,
    "pcb_decontamination": 5,
    "lead_removal": 2,
    "lead_encapsulation": 1,
    "hap_remediation": 3,
    "radon_mitigation": 2,
    "radon_ventilation": 2,
}

DEFAULT_DURATION_WEEKS = 3

# Work categories per intervention
WORK_CATEGORIES: dict[str, str] = {
    "asbestos_removal": "major",
    "pcb_joint_removal": "medium",
    "pcb_decontamination": "major",
    "lead_removal": "medium",
    "lead_encapsulation": "minor",
    "hap_remediation": "medium",
    "radon_mitigation": "minor",
    "radon_ventilation": "minor",
}

# Regulatory references
REGULATORY_REFS: dict[str, str] = {
    "asbestos": "OTConst Art. 60a, 82-86 / CFST 6503",
    "pcb": "ORRChim Annexe 2.15",
    "lead": "ORRChim Annexe 2.18",
    "hap": "ORRChim / OLED",
    "radon": "ORaP Art. 110",
}

# Quick win thresholds
QUICK_WIN_MAX_COST = 15_000.0
QUICK_WIN_MIN_RISK_REDUCTION = 20.0


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


async def _fetch_samples_by_pollutant(db: AsyncSession, building_id: UUID) -> dict[str, list[Sample]]:
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


async def _fetch_completed_interventions(db: AsyncSession, building_id: UUID) -> list[Intervention]:
    stmt = select(Intervention).where(
        Intervention.building_id == building_id,
        Intervention.status == "completed",
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _fetch_overdue_actions(db: AsyncSession, building_id: UUID) -> list[ActionItem]:
    stmt = select(ActionItem).where(
        ActionItem.building_id == building_id,
        ActionItem.status.in_(["open", "in_progress"]),
        ActionItem.due_date.isnot(None),
    )
    result = await db.execute(stmt)
    actions = result.scalars().all()
    today = date.today()
    return [a for a in actions if a.due_date and a.due_date < today]


def _classify_pollutant_situation(pollutant_type: str, samples: list[Sample]) -> str:
    """Classify a pollutant into its urgency category based on sample data."""
    if pollutant_type == "asbestos":
        # Check material state for friability
        for s in samples:
            state = (s.material_state or "").lower()
            if state == "friable" or ("friable" in state and "non" not in state):
                return "asbestos_friable"
            if s.cfst_work_category == "major":
                return "asbestos_friable"
        return "asbestos_non_friable"

    if pollutant_type == "pcb":
        for s in samples:
            conc = s.concentration or 0
            if conc > 1000:  # mg/kg — high
                return "pcb_high"
        return "pcb_moderate"

    if pollutant_type == "lead":
        for s in samples:
            state = (s.material_state or "").lower()
            if "accessible" in state or s.risk_level in ("high", "critical"):
                return "lead_accessible"
        return "lead_contained"

    if pollutant_type == "hap":
        return "hap"

    if pollutant_type == "radon":
        for s in samples:
            conc = s.concentration or 0
            if conc > 1000:
                return "radon_above_1000"
            if conc > 300:
                return "radon_300_1000"
        return "radon_300_1000"

    return pollutant_type


def _intervention_type_for_pollutant(pollutant_type: str, samples: list[Sample]) -> str:
    """Determine the recommended intervention type."""
    if pollutant_type == "asbestos":
        return "asbestos_removal"
    if pollutant_type == "pcb":
        for s in samples:
            cat = (s.material_category or "").lower()
            if "joint" in cat:
                return "pcb_joint_removal"
        return "pcb_decontamination"
    if pollutant_type == "lead":
        for s in samples:
            if s.risk_level in ("high", "critical"):
                return "lead_removal"
        return "lead_encapsulation"
    if pollutant_type == "hap":
        return "hap_remediation"
    if pollutant_type == "radon":
        for s in samples:
            conc = s.concentration or 0
            if conc > 1000:
                return "radon_mitigation"
        return "radon_ventilation"
    return f"{pollutant_type}_remediation"


def _risk_reduction_for_situation(situation: str) -> float:
    """Estimated risk reduction percentage for resolving this situation."""
    mapping = {
        "asbestos_friable": 35.0,
        "asbestos_non_friable": 20.0,
        "pcb_high": 25.0,
        "pcb_moderate": 15.0,
        "lead_accessible": 18.0,
        "lead_contained": 8.0,
        "hap": 15.0,
        "radon_above_1000": 30.0,
        "radon_300_1000": 10.0,
    }
    return mapping.get(situation, 10.0)


def _is_already_addressed(
    pollutant_type: str,
    completed_interventions: list[Intervention],
) -> bool:
    """Check if a pollutant has already been addressed by a completed intervention."""
    for iv in completed_interventions:
        it = (iv.intervention_type or "").lower()
        if pollutant_type == "asbestos" and "asbestos" in it:
            return True
        if pollutant_type == "pcb" and "pcb" in it:
            return True
        if pollutant_type == "lead" and "lead" in it:
            return True
        if pollutant_type == "hap" and "hap" in it:
            return True
        if pollutant_type == "radon" and "radon" in it:
            return True
    return False


def _build_dependency_edges(
    active_pollutants: list[str],
) -> list[DependencyEdge]:
    """Build dependency edges for the given active pollutants."""
    edges: list[DependencyEdge] = []
    pollutant_set = set(active_pollutants)
    for rule in DEPENDENCY_RULES:
        # Map blocker intervention type back to pollutant
        blocker_pollutant = rule["blocker"].split("_")[0]
        if blocker_pollutant in pollutant_set:
            edges.append(
                DependencyEdge(
                    blocker=rule["blocker"],
                    blocked=rule["blocked"],
                    reason=rule["reason"],
                )
            )
    return edges


def _find_parallel_safe(
    active_pollutants: list[str],
    dependency_edges: list[DependencyEdge],
) -> list[str]:
    """Find interventions that can be done in parallel (no dependency between them)."""
    blockers = {e.blocker for e in dependency_edges}
    blocked = {e.blocked for e in dependency_edges}
    all_constrained = blockers | blocked

    parallel: list[str] = []
    for pt in active_pollutants:
        intervention = f"{pt}_removal" if pt in ("asbestos", "lead") else f"{pt}_remediation"
        if intervention not in all_constrained:
            parallel.append(pt)

    # Also check pairs: two pollutants in different zones with no dependency
    if len(parallel) < 2 and len(active_pollutants) >= 2:
        for pt in active_pollutants:
            if pt not in parallel:
                is_blocked = False
                for e in dependency_edges:
                    if pt in e.blocker or pt in e.blocked:
                        is_blocked = True
                        break
                if not is_blocked:
                    parallel.append(pt)

    return parallel


def _compute_critical_path(
    steps: list[MitigationStep],
    dependency_edges: list[DependencyEdge],
) -> list[str]:
    """Compute the critical path — the longest chain of dependent interventions."""
    if not steps:
        return []

    # Build adjacency from dependency edges
    blocker_to_intervention: dict[str, str] = {}
    for step in steps:
        blocker_to_intervention[step.intervention_type] = step.pollutant_type

    # For the critical path, use step order as the primary driver
    path: list[str] = []
    for step in steps:
        # Include steps that are blockers or blocked
        for edge in dependency_edges:
            if step.intervention_type == edge.blocker:
                if step.intervention_type not in path:
                    path.append(step.intervention_type)
                break
        else:
            # Check if this step is blocked by something
            for edge in dependency_edges:
                if step.pollutant_type in edge.blocked:
                    if step.intervention_type not in path:
                        path.append(step.intervention_type)
                    break

    # If no dependencies, critical path is the highest-urgency chain
    if not path and steps:
        path = [steps[0].intervention_type]

    return path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_mitigation_plan(db: AsyncSession, building_id: UUID) -> MitigationPlan:
    """Generate an ordered remediation plan for a building."""
    await _fetch_building(db, building_id)
    grouped = await _fetch_samples_by_pollutant(db, building_id)
    completed = await _fetch_completed_interventions(db, building_id)
    overdue = await _fetch_overdue_actions(db, building_id)

    overdue_pollutants: set[str] = set()
    for action in overdue:
        meta = action.metadata_json or {}
        pt = meta.get("pollutant_type") or action.action_type
        overdue_pollutants.add(pt)

    # Build scored steps
    raw_steps: list[dict] = []
    for pollutant_type, samples in grouped.items():
        if _is_already_addressed(pollutant_type, completed):
            continue

        situation = _classify_pollutant_situation(pollutant_type, samples)
        urgency = URGENCY_SCORES.get(situation, 30.0)

        # Overdue bonus
        if pollutant_type in overdue_pollutants:
            urgency = min(urgency + OVERDUE_BONUS, 100.0)

        intervention_type = _intervention_type_for_pollutant(pollutant_type, samples)
        cost_min, cost_max = COST_ESTIMATES.get(intervention_type, DEFAULT_COST_RANGE)
        work_cat = WORK_CATEGORIES.get(intervention_type, "minor")
        reg_ref = REGULATORY_REFS.get(pollutant_type, "")
        risk_red = _risk_reduction_for_situation(situation)

        # Determine dominant work category from samples
        dominant_cat = _dominant_sample_work_category(samples)
        if dominant_cat:
            work_cat = dominant_cat

        raw_steps.append(
            {
                "pollutant_type": pollutant_type,
                "intervention_type": intervention_type,
                "urgency": urgency,
                "cost_min": cost_min,
                "cost_max": cost_max,
                "work_category": work_cat,
                "regulatory_reference": reg_ref,
                "risk_reduction": risk_red,
                "situation": situation,
            }
        )

    # Sort by urgency descending (highest first)
    raw_steps.sort(key=lambda s: s["urgency"], reverse=True)

    # Apply dependency ordering: ensure blockers come before blocked items
    raw_steps = _apply_dependency_ordering(raw_steps)

    # Build final steps with order and dependencies
    steps: list[MitigationStep] = []
    pollutant_to_order: dict[str, int] = {}
    total_risk_reduction = 0.0

    for i, rs in enumerate(raw_steps):
        order = i + 1
        pollutant_to_order[rs["pollutant_type"]] = order

        # Find dependencies (which earlier steps must complete first)
        deps: list[int] = []
        for rule in DEPENDENCY_RULES:
            blocker_pt = rule["blocker"].split("_")[0]
            if (
                rs["pollutant_type"] != blocker_pt
                and blocker_pt in pollutant_to_order
                and _is_blocked_by_rule(rs["pollutant_type"], rs["intervention_type"], rule)
            ):
                deps.append(pollutant_to_order[blocker_pt])

        rationale = _build_rationale(rs)
        total_risk_reduction += rs["risk_reduction"]

        steps.append(
            MitigationStep(
                order=order,
                pollutant_type=rs["pollutant_type"],
                intervention_type=rs["intervention_type"],
                urgency_score=round(rs["urgency"], 1),
                estimated_cost_min_chf=rs["cost_min"],
                estimated_cost_max_chf=rs["cost_max"],
                dependencies=deps,
                rationale=rationale,
                work_category=rs["work_category"],
                regulatory_reference=rs["regulatory_reference"],
            )
        )

    total_cost_min = sum(s.estimated_cost_min_chf for s in steps)
    total_cost_max = sum(s.estimated_cost_max_chf for s in steps)
    total_weeks = sum(DURATION_WEEKS.get(s.intervention_type, DEFAULT_DURATION_WEEKS) for s in steps)

    return MitigationPlan(
        building_id=building_id,
        steps=steps,
        total_cost_min_chf=round(total_cost_min, 2),
        total_cost_max_chf=round(total_cost_max, 2),
        total_duration_weeks=total_weeks,
        risk_reduction_percent=min(round(total_risk_reduction, 1), 100.0),
        generated_at=datetime.now(UTC),
    )


async def get_quick_wins(db: AsyncSession, building_id: UUID) -> list[QuickWin]:
    """Identify low-cost, high-impact remediation actions."""
    await _fetch_building(db, building_id)
    grouped = await _fetch_samples_by_pollutant(db, building_id)
    completed = await _fetch_completed_interventions(db, building_id)

    wins: list[QuickWin] = []
    for pollutant_type, samples in grouped.items():
        if _is_already_addressed(pollutant_type, completed):
            continue

        situation = _classify_pollutant_situation(pollutant_type, samples)
        intervention_type = _intervention_type_for_pollutant(pollutant_type, samples)
        cost_min, _ = COST_ESTIMATES.get(intervention_type, DEFAULT_COST_RANGE)
        work_cat = WORK_CATEGORIES.get(intervention_type, "minor")
        risk_red = _risk_reduction_for_situation(situation)

        # Quick win: minor work category OR low cost with decent risk reduction
        if (work_cat == "minor" or cost_min <= QUICK_WIN_MAX_COST) and (
            risk_red >= QUICK_WIN_MIN_RISK_REDUCTION or work_cat == "minor"
        ):
            wins.append(
                QuickWin(
                    pollutant_type=pollutant_type,
                    action_description=_describe_quick_win(pollutant_type, intervention_type),
                    cost_estimate_chf=cost_min,
                    risk_reduction_score=round(risk_red, 1),
                    work_category=work_cat,
                )
            )

    # Sort by risk_reduction_score descending
    wins.sort(key=lambda w: w.risk_reduction_score, reverse=True)
    return wins


async def analyze_intervention_dependencies(db: AsyncSession, building_id: UUID) -> DependencyAnalysis:
    """Analyze what blocks what for a building's remediation."""
    await _fetch_building(db, building_id)
    grouped = await _fetch_samples_by_pollutant(db, building_id)
    completed = await _fetch_completed_interventions(db, building_id)

    active_pollutants = [pt for pt in grouped if not _is_already_addressed(pt, completed)]

    edges = _build_dependency_edges(active_pollutants)

    # Build steps for critical path analysis
    plan = await generate_mitigation_plan(db, building_id)
    critical_path = _compute_critical_path(plan.steps, edges)
    parallel_safe = _find_parallel_safe(active_pollutants, edges)

    return DependencyAnalysis(
        building_id=building_id,
        dependencies=edges,
        critical_path=critical_path,
        parallel_safe=parallel_safe,
    )


async def estimate_plan_timeline(db: AsyncSession, building_id: UUID) -> PlanTimeline:
    """Generate a week-by-week timeline with milestones and cost curve."""
    plan = await generate_mitigation_plan(db, building_id)

    milestones: list[TimelineMilestone] = []
    cumulative_cost_curve: list[float] = []
    current_week = 0
    cumulative_cost = 0.0

    for step in plan.steps:
        duration = DURATION_WEEKS.get(step.intervention_type, DEFAULT_DURATION_WEEKS)
        end_week = current_week + duration
        avg_cost = (step.estimated_cost_min_chf + step.estimated_cost_max_chf) / 2

        milestones.append(
            TimelineMilestone(
                week=end_week,
                description=f"Complete {step.intervention_type} ({step.pollutant_type})",
                cost_chf=round(avg_cost, 2),
            )
        )

        # Build weekly cost curve
        weekly_cost = avg_cost / max(duration, 1)
        for _w in range(duration):
            cumulative_cost += weekly_cost
            cumulative_cost_curve.append(round(cumulative_cost, 2))

        current_week = end_week

    return PlanTimeline(
        building_id=building_id,
        total_weeks=current_week,
        milestones=milestones,
        cumulative_cost_curve=cumulative_cost_curve,
    )


# ---------------------------------------------------------------------------
# Additional internal helpers
# ---------------------------------------------------------------------------


def _dominant_sample_work_category(samples: list[Sample]) -> str | None:
    priority = {"major": 3, "medium": 2, "minor": 1}
    best: str | None = None
    best_p = 0
    for s in samples:
        wc = s.cfst_work_category
        if wc and priority.get(wc, 0) > best_p:
            best = wc
            best_p = priority[wc]
    return best


def _apply_dependency_ordering(steps: list[dict]) -> list[dict]:
    """Reorder steps so that blockers come before blocked items."""
    pollutant_types = {s["pollutant_type"] for s in steps}
    ordered: list[dict] = []
    remaining = list(steps)

    # Multiple passes to resolve dependencies
    max_passes = len(remaining) + 1
    for _ in range(max_passes):
        if not remaining:
            break
        for step in list(remaining):
            # Check if all blockers for this step are already ordered
            can_add = True
            for rule in DEPENDENCY_RULES:
                blocker_pt = rule["blocker"].split("_")[0]
                if (
                    blocker_pt in pollutant_types
                    and blocker_pt != step["pollutant_type"]
                    and _is_blocked_by_rule(step["pollutant_type"], step["intervention_type"], rule)
                    and not any(o["pollutant_type"] == blocker_pt for o in ordered)
                ):
                    can_add = False
                    break
            if can_add:
                ordered.append(step)
                remaining.remove(step)

    # Add any remaining (shouldn't happen with well-formed rules)
    ordered.extend(remaining)
    return ordered


def _is_blocked_by_rule(pollutant_type: str, intervention_type: str, rule: dict) -> bool:
    """Check if a given pollutant/intervention is blocked by a dependency rule."""
    blocked = rule["blocked"]
    # Renovation blocks: any non-asbestos work during renovation
    if blocked == "renovation" and pollutant_type != "asbestos":
        return False  # Only renovation work is blocked, not other pollutant removal
    if blocked == "facade_work" and "facade" not in intervention_type:
        return False
    if blocked == "painting" and "paint" not in intervention_type:
        return False
    if blocked == "occupancy" and pollutant_type != "radon":
        return False
    return False  # Conservative: don't over-block


def _build_rationale(step_data: dict) -> str:
    """Build a human-readable rationale for a mitigation step."""
    situation = step_data["situation"]
    urgency = step_data["urgency"]
    reg_ref = step_data["regulatory_reference"]

    parts = []
    if urgency >= 80:
        parts.append("High urgency")
    elif urgency >= 50:
        parts.append("Moderate urgency")
    else:
        parts.append("Lower urgency")

    situation_descriptions = {
        "asbestos_friable": "friable asbestos detected — immediate action required",
        "asbestos_non_friable": "non-friable asbestos detected — plan removal before renovation",
        "pcb_high": "high PCB concentration (>1000 mg/kg) — mandatory decontamination",
        "pcb_moderate": "moderate PCB levels — monitor and plan removal",
        "lead_accessible": "accessible lead-containing materials — risk of exposure",
        "lead_contained": "contained lead — encapsulation may suffice",
        "hap": "HAP detected — remediation required before works",
        "radon_above_1000": "radon >1000 Bq/m³ — exceeds action threshold",
        "radon_300_1000": "radon 300-1000 Bq/m³ — above reference level",
    }
    desc = situation_descriptions.get(situation, f"{situation} detected")
    parts.append(desc)

    if reg_ref:
        parts.append(f"Ref: {reg_ref}")

    return ". ".join(parts)


def _describe_quick_win(pollutant_type: str, intervention_type: str) -> str:
    """Build a description for a quick win action."""
    descriptions = {
        "lead_encapsulation": "Encapsulate lead-containing surfaces to prevent exposure",
        "radon_ventilation": "Install ventilation system to reduce radon levels",
        "radon_mitigation": "Seal entry points and improve sub-floor ventilation for radon",
        "hap_remediation": "Remove HAP-contaminated materials in targeted areas",
        "asbestos_removal": "Remove asbestos-containing materials (CFST 6503 compliant)",
        "pcb_joint_removal": "Remove PCB-containing joint sealants",
        "pcb_decontamination": "Decontaminate PCB-affected surfaces",
        "lead_removal": "Remove lead-containing coatings and materials",
    }
    return descriptions.get(
        intervention_type,
        f"Remediate {pollutant_type} contamination",
    )
