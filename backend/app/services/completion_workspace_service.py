"""
SwissBuildingOS - Completion Workspace Service

Transforms a DossierCompletionReport into an ordered, dependency-aware
set of actionable steps that a human operator can follow to complete
a building's dossier.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.completion_workspace import (
    CompletionStep,
    CompletionWorkspace,
    StepStatusUpdate,
)
from app.schemas.dossier_completion import (
    CompletionBlocker,
    CompletionRecommendation,
    DossierCompletionReport,
)
from app.services.dossier_completion_agent import run_dossier_completion

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Category ordering: evidence first, then diagnostic, documentation,
# verification, administrative — mirrors the natural workflow.
_CATEGORY_ORDER = {
    "evidence": 0,
    "diagnostic": 1,
    "documentation": 2,
    "verification": 3,
    "administrative": 4,
}

# Map recommendation categories to workspace categories.
_RECOMMENDATION_CATEGORY_MAP: dict[str, str] = {
    "evidence": "evidence",
    "diagnostic": "diagnostic",
    "document": "documentation",
    "regulatory": "administrative",
    "intervention": "administrative",
}

# Estimated effort (minutes) by category or action keyword.
_EFFORT_BY_CATEGORY: dict[str, int] = {
    "evidence": 15,
    "diagnostic": 120,
    "documentation": 5,
    "verification": 15,
    "administrative": 10,
}

_EFFORT_KEYWORDS: dict[str, int] = {
    "upload": 5,
    "commission": 120,
    "verify": 15,
    "inspect": 60,
    "sample": 30,
    "document": 5,
    "plan": 10,
}

# Categories that must complete before verification steps can start.
_VERIFICATION_PREREQUISITES = {"evidence", "diagnostic", "documentation"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _estimate_effort(category: str, description: str) -> int:
    """Estimate effort in minutes based on category and description keywords."""
    desc_lower = description.lower()
    for keyword, minutes in _EFFORT_KEYWORDS.items():
        if keyword in desc_lower:
            return minutes
    return _EFFORT_BY_CATEGORY.get(category, 10)


def _map_blocker_to_step(blocker: CompletionBlocker) -> CompletionStep:
    """Convert a top blocker into a critical completion step."""
    category = "evidence"
    if blocker.source == "readiness":
        category = "administrative"
    elif blocker.entity_type:
        category = _RECOMMENDATION_CATEGORY_MAP.get(blocker.entity_type, "evidence")

    return CompletionStep(
        id=uuid4(),
        step_number=0,  # assigned later
        category=category,
        title=f"[BLOCKER] {blocker.description}",
        description=f"Resolve blocker: {blocker.description}",
        priority="critical",
        status="pending",
        estimated_effort_minutes=_estimate_effort(category, blocker.description),
        entity_type=blocker.entity_type,
        entity_id=blocker.entity_id,
        depends_on=[],
    )


def _map_recommendation_to_step(rec: CompletionRecommendation) -> CompletionStep:
    """Convert a recommendation into a completion step."""
    category = _RECOMMENDATION_CATEGORY_MAP.get(rec.category, "evidence")
    return CompletionStep(
        id=uuid4(),
        step_number=0,
        category=category,
        title=rec.description,
        description=f"Recommended action: {rec.description}",
        priority=rec.priority,
        status="pending",
        estimated_effort_minutes=_estimate_effort(category, rec.description),
        entity_type=rec.entity_type,
        entity_id=rec.entity_id,
        depends_on=[],
    )


def _map_gap_to_step(gap_type: str, count: int) -> CompletionStep:
    """Convert a gap category into a completion step."""
    category = _RECOMMENDATION_CATEGORY_MAP.get(
        {
            "missing_diagnostic": "diagnostic",
            "uninspected_zone": "evidence",
            "missing_document": "document",
            "missing_sample": "diagnostic",
            "regulatory_gap": "regulatory",
            "missing_intervention": "intervention",
        }.get(gap_type, "evidence"),
        "evidence",
    )
    return CompletionStep(
        id=uuid4(),
        step_number=0,
        category=category,
        title=f"Resolve {count} {gap_type.replace('_', ' ')} gap(s)",
        description=f"There are {count} open {gap_type.replace('_', ' ')} issue(s) to address.",
        priority="high" if count >= 3 else "medium",
        status="pending",
        estimated_effort_minutes=_estimate_effort(category, gap_type) * count,
        depends_on=[],
    )


def _map_warning_to_step(warning: str) -> CompletionStep:
    """Convert a data quality warning into a low-priority verification step."""
    return CompletionStep(
        id=uuid4(),
        step_number=0,
        category="verification",
        title=f"Verify: {warning}",
        description=f"Data quality issue detected: {warning}. Review and correct affected records.",
        priority="low",
        status="pending",
        estimated_effort_minutes=15,
        depends_on=[],
    )


def _deduplicate_steps(steps: list[CompletionStep]) -> list[CompletionStep]:
    """Remove steps with duplicate titles, keeping the higher-priority one."""
    seen: dict[str, CompletionStep] = {}
    for step in steps:
        if step.title in seen:
            existing = seen[step.title]
            if _PRIORITY_ORDER.get(step.priority, 3) < _PRIORITY_ORDER.get(existing.priority, 3):
                seen[step.title] = step
        else:
            seen[step.title] = step
    return list(seen.values())


def _sort_steps(steps: list[CompletionStep]) -> list[CompletionStep]:
    """Sort steps by category order, then by priority within each category."""
    return sorted(
        steps,
        key=lambda s: (
            _CATEGORY_ORDER.get(s.category, 99),
            _PRIORITY_ORDER.get(s.priority, 99),
        ),
    )


def _assign_dependencies(steps: list[CompletionStep]) -> None:
    """Assign dependency edges: verification steps depend on prerequisite categories."""
    prerequisite_ids: list[UUID] = []
    for step in steps:
        if step.category in _VERIFICATION_PREREQUISITES:
            prerequisite_ids.append(step.id)

    for step in steps:
        if step.category == "verification" and prerequisite_ids:
            step.depends_on = list(prerequisite_ids)


def _compute_overall_priority(steps: list[CompletionStep]) -> str:
    """Return the highest priority across all steps."""
    if not steps:
        return "low"
    best = min(_PRIORITY_ORDER.get(s.priority, 3) for s in steps)
    for label, rank in _PRIORITY_ORDER.items():
        if rank == best:
            return label
    return "low"


def _find_next_recommended(steps: list[CompletionStep]) -> UUID | None:
    """Return the id of the highest-priority pending, non-blocked step."""
    candidates = [s for s in steps if s.status == "pending" and not _is_blocked_by_deps(s, steps)]
    if not candidates:
        return None
    candidates.sort(key=lambda s: _PRIORITY_ORDER.get(s.priority, 3))
    return candidates[0].id


def _is_blocked_by_deps(step: CompletionStep, all_steps: list[CompletionStep]) -> bool:
    """Check if a step is blocked because a dependency is not yet completed/skipped."""
    if not step.depends_on:
        return False
    completed_ids = {s.id for s in all_steps if s.status in ("completed", "skipped")}
    return not all(dep_id in completed_ids for dep_id in step.depends_on)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_workspace(
    db: AsyncSession,
    building_id: UUID,
) -> CompletionWorkspace | None:
    """Generate a completion workspace from the dossier completion report.

    Returns None if the building does not exist.
    """
    report = await run_dossier_completion(db, building_id)
    if report is None:
        return None

    return build_workspace_from_report(report)


def build_workspace_from_report(report: DossierCompletionReport) -> CompletionWorkspace:
    """Transform a DossierCompletionReport into a CompletionWorkspace.

    Pure function — useful for testing without DB.
    """
    steps: list[CompletionStep] = []

    # 1. Top blockers → critical steps
    for blocker in report.top_blockers:
        steps.append(_map_blocker_to_step(blocker))

    # 2. Recommended actions → steps
    for rec in report.recommended_actions:
        steps.append(_map_recommendation_to_step(rec))

    # 3. Gap categories → steps (only if not already covered by recommendations)
    existing_titles = {s.title for s in steps}
    for gap_type, count in report.gap_categories.items():
        gap_step = _map_gap_to_step(gap_type, count)
        if gap_step.title not in existing_titles:
            steps.append(gap_step)

    # 4. Data quality warnings → verification steps
    for warning in report.data_quality_warnings:
        steps.append(_map_warning_to_step(warning))

    # Deduplicate, sort, assign numbers and dependencies
    steps = _deduplicate_steps(steps)
    steps = _sort_steps(steps)
    _assign_dependencies(steps)

    for i, step in enumerate(steps, start=1):
        step.step_number = i

    # Compute aggregates
    completed = sum(1 for s in steps if s.status == "completed")
    total = len(steps)
    progress = (completed / total * 100.0) if total > 0 else 100.0
    total_effort = sum(s.estimated_effort_minutes or 0 for s in steps)

    return CompletionWorkspace(
        building_id=report.building_id,
        total_steps=total,
        completed_steps=completed,
        progress_percent=round(progress, 1),
        steps=steps,
        overall_priority=_compute_overall_priority(steps),
        estimated_total_effort_minutes=total_effort if total_effort > 0 else None,
        next_recommended_step=_find_next_recommended(steps),
    )


def update_step_status(
    workspace: CompletionWorkspace,
    step_id: UUID,
    update: StepStatusUpdate,
) -> CompletionWorkspace:
    """Update a step's status and recalculate workspace progress.

    Raises ValueError if the step_id is not found.
    """
    target = None
    for step in workspace.steps:
        if step.id == step_id:
            target = step
            break

    if target is None:
        raise ValueError(f"Step {step_id} not found in workspace")

    target.status = update.status
    target.blocker_reason = update.blocker_reason

    # If a step is completed, check if dependent steps can be unblocked
    if update.status in ("completed", "skipped"):
        _try_unblock_dependents(workspace.steps, step_id)

    # Recalculate aggregates
    completed = sum(1 for s in workspace.steps if s.status == "completed")
    total = workspace.total_steps
    workspace.completed_steps = completed
    workspace.progress_percent = round((completed / total * 100.0) if total > 0 else 100.0, 1)
    workspace.next_recommended_step = _find_next_recommended(workspace.steps)

    return workspace


def _try_unblock_dependents(steps: list[CompletionStep], completed_id: UUID) -> None:
    """Unblock steps that were blocked solely because of the now-completed step."""
    completed_ids = {s.id for s in steps if s.status in ("completed", "skipped")}
    for step in steps:
        if (
            step.status == "blocked"
            and completed_id in step.depends_on
            and all(dep_id in completed_ids for dep_id in step.depends_on)
        ):
            step.status = "pending"
            step.blocker_reason = None


def get_next_steps(
    workspace: CompletionWorkspace,
    count: int = 3,
) -> list[CompletionStep]:
    """Return the top N actionable steps (pending, not blocked by dependencies)."""
    actionable: list[CompletionStep] = []
    for step in workspace.steps:
        if step.status != "pending":
            continue
        if _is_blocked_by_deps(step, workspace.steps):
            continue
        actionable.append(step)

    actionable.sort(key=lambda s: _PRIORITY_ORDER.get(s.priority, 3))
    return actionable[:count]
