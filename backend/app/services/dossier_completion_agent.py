"""
SwissBuildingOS - Dossier Completion Agent

Orchestrates existing engines to produce a unified dossier completion
analysis for a building. This is the first "invisible agent" — it runs
all sub-services, aggregates their output, and returns a single report
describing what is done, what is missing, and what to do next.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.schemas.dossier_completion import (
    CompletionBlocker,
    CompletionRecommendation,
    DossierCompletionReport,
)
from app.services import (
    action_generator,
    completeness_engine,
    readiness_reasoner,
    trust_score_calculator,
    unknown_generator,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

READINESS_TYPES = (
    "safe_to_start",
    "safe_to_tender",
    "safe_to_reopen",
    "safe_to_requalify",
)

_SEVERITY_PRIORITY = {"critical": 0, "high": 1, "medium": 2, "low": 3}

_UNKNOWN_TYPE_TO_CATEGORY: dict[str, str] = {
    "missing_diagnostic": "diagnostic",
    "uninspected_zone": "evidence",
    "missing_document": "document",
    "missing_sample": "diagnostic",
    "regulatory_gap": "regulatory",
    "missing_intervention": "intervention",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _severity_to_priority(severity: str) -> str:
    """Map severity to priority label."""
    if severity in ("critical", "high"):
        return "high"
    if severity == "medium":
        return "medium"
    return "low"


def _blocker_sort_key(b: CompletionBlocker) -> int:
    """Sort key for blockers — high priority first."""
    return {"high": 0, "medium": 1, "low": 2}.get(b.priority, 3)


def _determine_overall_status(
    completeness_score: float,
    trust_score: float,
    readiness_statuses: dict[str, str],
) -> str:
    """Determine the overall dossier status.

    - "complete": completeness >= 0.95 AND all readiness ready AND trust >= 0.7
    - "near_complete": completeness >= 0.80 AND no readiness type blocked
    - "critical_gaps": any readiness type blocked
    - "incomplete": everything else
    """
    all_ready = all(s == "ready" for s in readiness_statuses.values())
    any_blocked = any(s == "blocked" for s in readiness_statuses.values())

    if completeness_score >= 0.95 and all_ready and trust_score >= 0.7:
        return "complete"
    if any_blocked:
        return "critical_gaps"
    if completeness_score >= 0.80 and not any_blocked:
        return "near_complete"
    return "incomplete"


def _build_trust_warnings(trust_score_obj: object) -> list[str]:
    """Generate data quality warnings from trust score dimensions."""
    warnings: list[str] = []
    declared_pct = getattr(trust_score_obj, "percent_declared", None) or 0.0
    obsolete_pct = getattr(trust_score_obj, "percent_obsolete", None) or 0.0
    contradictory_pct = getattr(trust_score_obj, "percent_contradictory", None) or 0.0

    if declared_pct >= 0.3:
        warnings.append(f"{int(declared_pct * 100)}% of data is declared-only")
    if obsolete_pct >= 0.1:
        warnings.append(f"{int(obsolete_pct * 100)}% of data is obsolete")
    if contradictory_pct >= 0.05:
        warnings.append(f"{int(contradictory_pct * 100)}% of data has contradictions")
    return warnings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_dossier_completion(
    db: AsyncSession,
    building_id: UUID,
    *,
    force_refresh: bool = False,
) -> DossierCompletionReport | None:
    """Run the full dossier completion agent for a building.

    Returns None if the building does not exist.
    When *force_refresh* is True, all generators run before evaluation.
    """
    # 0. Verify building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    # 1. Refresh unknowns
    unknowns = await unknown_generator.generate_unknowns(db, building_id)

    # 2. Calculate trust
    trust_obj = await trust_score_calculator.calculate_trust_score(db, building_id)
    trust_value = trust_obj.overall_score if trust_obj else 0.0

    # 3. Evaluate completeness
    completeness_result = await completeness_engine.evaluate_completeness(db, building_id)
    completeness_score = completeness_result.overall_score

    # 4. Evaluate all readiness types
    readiness_map: dict[str, str] = {}
    readiness_blockers: list[CompletionBlocker] = []

    for rtype in READINESS_TYPES:
        assessment = await readiness_reasoner.evaluate_readiness(db, building_id, rtype)
        readiness_map[rtype] = assessment.status

        # Extract blockers from readiness
        if assessment.blockers_json:
            for blocker_data in assessment.blockers_json:
                desc = (
                    blocker_data
                    if isinstance(blocker_data, str)
                    else blocker_data.get("description", str(blocker_data))
                )
                readiness_blockers.append(
                    CompletionBlocker(
                        priority="high",
                        description=desc,
                        source="readiness",
                        readiness_type=rtype,
                    )
                )

    # 5. Refresh actions (idempotent, per-diagnostic)
    diag_result = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
    diagnostic_ids = list(diag_result.scalars().all())
    for diag_id in diagnostic_ids:
        await action_generator.generate_actions_from_diagnostic(db, building_id, diag_id)

    # 6. Build blockers from unknowns that block readiness
    unknown_blockers: list[CompletionBlocker] = []
    for u in unknowns:
        if u.blocks_readiness and u.status == "open":
            unknown_blockers.append(
                CompletionBlocker(
                    priority=_severity_to_priority(u.severity),
                    description=u.title,
                    source="unknown",
                    entity_type=u.entity_type,
                    entity_id=u.entity_id,
                )
            )

    # Merge and sort blockers, take top 10
    all_blockers = readiness_blockers + unknown_blockers
    all_blockers.sort(key=_blocker_sort_key)
    top_blockers = all_blockers[:10]

    # 7. Build recommendations from open unknowns
    recommendations: list[CompletionRecommendation] = []
    for u in unknowns:
        if u.status == "open":
            category = _UNKNOWN_TYPE_TO_CATEGORY.get(u.unknown_type, "evidence")
            recommendations.append(
                CompletionRecommendation(
                    priority=_severity_to_priority(u.severity),
                    description=u.title,
                    category=category,
                    entity_type=u.entity_type,
                    entity_id=u.entity_id,
                )
            )
    recommendations.sort(key=lambda r: {"high": 0, "medium": 1, "low": 2}.get(r.priority, 3))
    recommended_actions = recommendations[:10]

    # 8. Gap categories
    gap_categories: dict[str, int] = defaultdict(int)
    for u in unknowns:
        if u.status == "open":
            gap_categories[u.unknown_type] += 1

    # 9. Trust warnings
    data_quality_warnings = _build_trust_warnings(trust_obj)

    # 10. Overall status
    overall_status = _determine_overall_status(completeness_score, trust_value, readiness_map)

    return DossierCompletionReport(
        building_id=building_id,
        overall_status=overall_status,
        completeness_score=completeness_score,
        trust_score=trust_value,
        readiness_summary=readiness_map,
        top_blockers=top_blockers,
        recommended_actions=recommended_actions,
        gap_categories=dict(gap_categories),
        data_quality_warnings=data_quality_warnings,
        assessed_at=datetime.utcnow(),
    )
