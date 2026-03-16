"""
SwissBuildingOS - Building Passport Service

Aggregates the building's knowledge state into a unified passport summary.
The passport represents what the system knows, what it doesn't know,
what is contradictory, and what is actionable about a building.

This is NOT a physical document — it's a living state object that evolves
as evidence accumulates.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.readiness_assessment import ReadinessAssessment
from app.models.sample import Sample
from app.models.unknown_issue import UnknownIssue

# ---------------------------------------------------------------------------
# Grade thresholds
# ---------------------------------------------------------------------------

_GRADE_THRESHOLDS = [
    # (grade, min_trust, min_completeness, max_blockers, max_contradictions)
    ("A", 0.8, 0.9, 0, 0),
    ("B", 0.6, 0.7, 0, None),  # None = no limit
    ("C", 0.4, 0.5, None, None),
    ("D", 0.2, 0.3, None, None),
]


def _compute_passport_grade(
    trust: float,
    completeness: float,
    blockers: int,
    unresolved_contradictions: int,
) -> str:
    """Compute passport grade from A to F based on combined metrics.

    - A: trust >= 0.8, completeness >= 0.9, no blockers, no unresolved contradictions
    - B: trust >= 0.6, completeness >= 0.7, no critical blockers
    - C: trust >= 0.4, completeness >= 0.5
    - D: trust >= 0.2 or completeness >= 0.3
    - F: below all thresholds
    """
    for grade, min_trust, min_comp, max_block, max_contra in _GRADE_THRESHOLDS:
        if trust < min_trust or completeness < min_comp:
            continue
        if max_block is not None and blockers > max_block:
            continue
        if max_contra is not None and unresolved_contradictions > max_contra:
            continue
        return grade
    return "F"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_passport_summary(
    db: AsyncSession,
    building_id: UUID,
) -> dict | None:
    """Aggregate the building's passport state.

    Returns None if the building does not exist.

    Returns a dict with:
      - building_id
      - knowledge_state (trust score breakdown)
      - completeness (overall + category scores)
      - readiness (4 readiness types with status/score/blockers_count)
      - blind_spots (open unknown issues)
      - contradictions (data quality issues of type contradiction)
      - evidence_coverage (entity counts and latest dates)
      - passport_grade (A-F)
      - assessed_at (ISO timestamp)
    """
    # ── 0. Verify building exists ──────────────────────────────────
    building_result = await db.execute(select(Building).where(Building.id == building_id))
    building = building_result.scalar_one_or_none()
    if building is None:
        return None

    # ── 1. Load latest BuildingTrustScore ──────────────────────────
    trust_result = await db.execute(
        select(BuildingTrustScore)
        .where(BuildingTrustScore.building_id == building_id)
        .order_by(BuildingTrustScore.assessed_at.desc())
        .limit(1)
    )
    trust_score = trust_result.scalar_one_or_none()

    if trust_score is not None:
        knowledge_state = {
            "proven_pct": trust_score.percent_proven or 0.0,
            "inferred_pct": trust_score.percent_inferred or 0.0,
            "declared_pct": trust_score.percent_declared or 0.0,
            "obsolete_pct": trust_score.percent_obsolete or 0.0,
            "contradictory_pct": trust_score.percent_contradictory or 0.0,
            "overall_trust": trust_score.overall_score or 0.0,
            "total_data_points": trust_score.total_data_points or 0,
            "trend": trust_score.trend,
        }
    else:
        knowledge_state = {
            "proven_pct": 0.0,
            "inferred_pct": 0.0,
            "declared_pct": 0.0,
            "obsolete_pct": 0.0,
            "contradictory_pct": 0.0,
            "overall_trust": 0.0,
            "total_data_points": 0,
            "trend": None,
        }

    overall_trust = knowledge_state["overall_trust"]

    # ── 2. Load ReadinessAssessment records ────────────────────────
    readiness_result = await db.execute(
        select(ReadinessAssessment).where(ReadinessAssessment.building_id == building_id)
    )
    readiness_records = list(readiness_result.scalars().all())

    readiness_map: dict[str, dict] = {}
    total_blockers = 0
    for ra in readiness_records:
        blockers_count = len(ra.blockers_json) if ra.blockers_json else 0
        total_blockers += blockers_count
        readiness_map[ra.readiness_type] = {
            "status": ra.status,
            "score": ra.score or 0.0,
            "blockers_count": blockers_count,
        }

    readiness_default = {"status": "not_evaluated", "score": 0.0, "blockers_count": 0}
    readiness = {
        "safe_to_start": readiness_map.get("safe_to_start", readiness_default),
        "safe_to_tender": readiness_map.get("safe_to_tender", readiness_default),
        "safe_to_reopen": readiness_map.get("safe_to_reopen", readiness_default),
        "safe_to_requalify": readiness_map.get("safe_to_requalify", readiness_default),
    }

    # ── 3. Load open UnknownIssue records ──────────────────────────
    unknown_result = await db.execute(
        select(UnknownIssue).where(
            and_(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
            )
        )
    )
    open_unknowns = list(unknown_result.scalars().all())

    by_unknown_type: dict[str, int] = defaultdict(int)
    blocking_count = 0
    for u in open_unknowns:
        by_unknown_type[u.unknown_type] += 1
        if u.blocks_readiness:
            blocking_count += 1

    blind_spots = {
        "total_open": len(open_unknowns),
        "blocking": blocking_count,
        "by_type": dict(by_unknown_type),
    }

    # ── 4. Load DataQualityIssue (contradiction type) ──────────────
    contradiction_result = await db.execute(
        select(DataQualityIssue).where(
            and_(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.issue_type == "contradiction",
            )
        )
    )
    contradictions_list = list(contradiction_result.scalars().all())

    by_contradiction_type: dict[str, int] = defaultdict(int)
    unresolved_contradictions = 0
    for c in contradictions_list:
        field = c.field_name or "unknown"
        by_contradiction_type[field] += 1
        if c.status != "resolved":
            unresolved_contradictions += 1

    contradictions = {
        "total": len(contradictions_list),
        "unresolved": unresolved_contradictions,
        "by_type": dict(by_contradiction_type),
    }

    # ── 5. Evidence coverage counts ────────────────────────────────
    diag_count_result = await db.execute(
        select(func.count()).select_from(Diagnostic).where(Diagnostic.building_id == building_id)
    )
    diagnostics_count = diag_count_result.scalar() or 0

    # Samples count (via diagnostics)
    samples_count = 0
    if diagnostics_count > 0:
        sample_count_result = await db.execute(
            select(func.count())
            .select_from(Sample)
            .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
            .where(Diagnostic.building_id == building_id)
        )
        samples_count = sample_count_result.scalar() or 0

    doc_count_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.building_id == building_id)
    )
    documents_count = doc_count_result.scalar() or 0

    intervention_count_result = await db.execute(
        select(func.count()).select_from(Intervention).where(Intervention.building_id == building_id)
    )
    interventions_count = intervention_count_result.scalar() or 0

    # Latest dates
    latest_diag_result = await db.execute(
        select(func.max(Diagnostic.date_inspection)).where(Diagnostic.building_id == building_id)
    )
    latest_diag_date = latest_diag_result.scalar()

    latest_doc_result = await db.execute(
        select(func.max(Document.created_at)).where(Document.building_id == building_id)
    )
    latest_doc_date = latest_doc_result.scalar()

    evidence_coverage = {
        "diagnostics_count": diagnostics_count,
        "samples_count": samples_count,
        "documents_count": documents_count,
        "interventions_count": interventions_count,
        "latest_diagnostic_date": (latest_diag_date.isoformat() if latest_diag_date else None),
        "latest_document_date": (latest_doc_date.isoformat() if latest_doc_date else None),
    }

    # ── 6. Completeness (from readiness scores as proxy) ───────────
    # Use the average of readiness scores as completeness proxy,
    # or 0.0 if no readiness assessments exist.
    scored_assessments = [ra for ra in readiness_records if ra.score is not None]
    if scored_assessments:
        overall_completeness = round(sum(ra.score for ra in scored_assessments) / len(scored_assessments), 4)
    else:
        overall_completeness = 0.0

    category_scores: dict[str, float] = {}
    for ra in readiness_records:
        category_scores[ra.readiness_type] = ra.score or 0.0

    completeness = {
        "overall_score": overall_completeness,
        "category_scores": category_scores,
    }

    # ── 7. Compute passport grade ──────────────────────────────────
    passport_grade = _compute_passport_grade(
        trust=overall_trust,
        completeness=overall_completeness,
        blockers=total_blockers,
        unresolved_contradictions=unresolved_contradictions,
    )

    assessed_at = datetime.now(UTC)

    return {
        "building_id": str(building_id),
        "knowledge_state": knowledge_state,
        "completeness": completeness,
        "readiness": readiness,
        "blind_spots": blind_spots,
        "contradictions": contradictions,
        "evidence_coverage": evidence_coverage,
        "passport_grade": passport_grade,
        "assessed_at": assessed_at.isoformat(),
    }
