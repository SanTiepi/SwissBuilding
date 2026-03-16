"""
SwissBuildingOS - Compliance Domain Facade

Read-only composition point for compliance-related queries: completeness,
compliance artefacts, and readiness assessments for a building. Thin wrapper
over existing models and services -- no new business logic.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.readiness_assessment import ReadinessAssessment
from app.services.completeness_engine import evaluate_completeness

# Readiness gate types
_READINESS_TYPES = ("safe_to_start", "safe_to_tender", "safe_to_reopen", "safe_to_requalify")

_READINESS_DEFAULT = {"status": "not_evaluated", "score": 0.0, "blockers_count": 0}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_compliance_summary(
    db: AsyncSession,
    building_id: UUID,
) -> dict | None:
    """Aggregate compliance state for a building.

    Returns None if the building does not exist.

    Returns a dict with:
      - building_id
      - completeness_score (from completeness engine)
      - completeness_ready (bool)
      - artefacts (total, by_status, pending_submissions)
      - readiness (4 gates with status/score/blockers_count)
      - regulatory_checks (count of completeness checks by category)
    """
    # ── 0. Verify building exists ─────────────────────────────────
    result = await db.execute(select(Building).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        return None

    # ── 1. Completeness (reuse existing engine) ───────────────────
    completeness_result = await evaluate_completeness(db, building_id)

    completeness_score = completeness_result.overall_score
    completeness_ready = completeness_result.ready_to_proceed
    missing_items = completeness_result.missing_items

    # Aggregate checks by category
    checks_by_category: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "complete": 0, "missing": 0})
    for check in completeness_result.checks:
        cat = check.category
        checks_by_category[cat]["total"] += 1
        if check.status == "complete":
            checks_by_category[cat]["complete"] += 1
        elif check.status == "missing":
            checks_by_category[cat]["missing"] += 1

    # ── 2. Compliance artefacts ───────────────────────────────────
    artefact_result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id))
    artefacts = list(artefact_result.scalars().all())

    artefacts_total = len(artefacts)
    by_status: dict[str, int] = defaultdict(int)
    pending_submissions = 0

    for a in artefacts:
        by_status[a.status or "draft"] += 1
        if a.status == "draft":
            pending_submissions += 1

    # ── 3. Readiness assessments (read existing, no mutation) ─────
    readiness_result = await db.execute(
        select(ReadinessAssessment).where(ReadinessAssessment.building_id == building_id)
    )
    readiness_records = list(readiness_result.scalars().all())

    readiness_map: dict[str, dict] = {}
    for ra in readiness_records:
        blockers_count = len(ra.blockers_json) if ra.blockers_json else 0
        readiness_map[ra.readiness_type] = {
            "status": ra.status,
            "score": ra.score or 0.0,
            "blockers_count": blockers_count,
        }

    readiness = {rt: readiness_map.get(rt, dict(_READINESS_DEFAULT)) for rt in _READINESS_TYPES}

    return {
        "building_id": str(building_id),
        "completeness_score": completeness_score,
        "completeness_ready": completeness_ready,
        "missing_items": missing_items,
        "artefacts": {
            "total": artefacts_total,
            "by_status": dict(by_status),
            "pending_submissions": pending_submissions,
        },
        "readiness": readiness,
        "regulatory_checks": {k: dict(v) for k, v in checks_by_category.items()},
    }
