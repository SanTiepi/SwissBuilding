"""
SwissBuildingOS - Evidence Score Service

Computes a simplified 0-100 "Evidence Score" per building that answers:
"How well do I know this building?"

Aggregates four dimensions:
  - Trust score (weight 0.35)
  - Completeness score (weight 0.30)
  - Evidence freshness (weight 0.20)
  - Gap penalty (weight 0.15)
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.sample import Sample
from app.models.unknown_issue import UnknownIssue
from app.services.completeness_engine import evaluate_completeness

# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------

WEIGHT_TRUST = 0.35
WEIGHT_COMPLETENESS = 0.30
WEIGHT_FRESHNESS = 0.20
WEIGHT_GAP_PENALTY = 0.15

# ---------------------------------------------------------------------------
# Grade thresholds
# ---------------------------------------------------------------------------

_GRADE_MAP = [
    (85, "A"),
    (70, "B"),
    (55, "C"),
    (40, "D"),
]


def _score_to_grade(score: int) -> str:
    for threshold, grade in _GRADE_MAP:
        if score >= threshold:
            return grade
    return "F"


# ---------------------------------------------------------------------------
# Freshness calculation
# ---------------------------------------------------------------------------


def _compute_freshness(latest_date: datetime | None) -> float:
    """Compute freshness factor based on age of most recent evidence.

    Returns:
        1.0 if < 1 year
        0.5 if 1-3 years
        0.2 if 3-5 years
        0.0 if > 5 years or no evidence
    """
    if latest_date is None:
        return 0.0

    now = datetime.now(UTC)
    # Ensure latest_date is timezone-aware
    if latest_date.tzinfo is None:
        latest_date = latest_date.replace(tzinfo=UTC)

    age = now - latest_date
    years = age.total_seconds() / (365.25 * 86400)

    if years < 1:
        return 1.0
    if years < 3:
        return 0.5
    if years < 5:
        return 0.2
    return 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def compute_evidence_score(
    db: AsyncSession,
    building_id: UUID,
) -> dict | None:
    """Compute a unified evidence score (0-100) for a building.

    Returns None if the building does not exist.
    """
    # ── 0. Verify building exists ──────────────────────────────────
    building_result = await db.execute(select(Building).where(Building.id == building_id))
    building = building_result.scalar_one_or_none()
    if building is None:
        return None

    # ── 1. Trust score (0.0 - 1.0) ────────────────────────────────
    trust_result = await db.execute(
        select(BuildingTrustScore)
        .where(BuildingTrustScore.building_id == building_id)
        .order_by(BuildingTrustScore.assessed_at.desc())
        .limit(1)
    )
    trust_record = trust_result.scalar_one_or_none()
    trust_value = trust_record.overall_score if trust_record else 0.0

    # ── 2. Completeness score (0.0 - 1.0) ─────────────────────────
    completeness_result = await evaluate_completeness(db, building_id)
    completeness_value = completeness_result.overall_score

    # ── 3. Evidence freshness (0.0 - 1.0) ─────────────────────────
    # Find the most recent date across diagnostics, documents, and samples
    latest_diag_result = await db.execute(
        select(func.max(Diagnostic.date_inspection)).where(Diagnostic.building_id == building_id)
    )
    latest_diag_date = latest_diag_result.scalar()

    latest_doc_result = await db.execute(
        select(func.max(Document.created_at)).where(Document.building_id == building_id)
    )
    latest_doc_date = latest_doc_result.scalar()

    # Samples via diagnostics
    latest_sample_result = await db.execute(
        select(func.max(Sample.created_at))
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    latest_sample_date = latest_sample_result.scalar()

    dates = [d for d in [latest_diag_date, latest_doc_date, latest_sample_date] if d is not None]
    # Convert date objects to datetime for comparison
    normalized_dates: list[datetime] = []
    for d in dates:
        if isinstance(d, datetime):
            # Ensure timezone-aware
            if d.tzinfo is None:
                d = d.replace(tzinfo=UTC)
            normalized_dates.append(d)
        else:
            normalized_dates.append(datetime(d.year, d.month, d.day, tzinfo=UTC))

    latest_evidence_date = max(normalized_dates) if normalized_dates else None
    freshness_value = _compute_freshness(latest_evidence_date)

    # ── 4. Gap penalty (0.0 - 1.0) ────────────────────────────────
    # Count open unknowns that block readiness
    blocking_result = await db.execute(
        select(func.count())
        .select_from(UnknownIssue)
        .where(
            and_(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
                UnknownIssue.blocks_readiness.is_(True),
            )
        )
    )
    open_unknowns_blocking = blocking_result.scalar() or 0

    # Total applicable checks from completeness
    total_applicable = len([c for c in completeness_result.checks if c.status != "not_applicable"])
    total_applicable = max(total_applicable, 1)

    gap_penalty_value = 1.0 - (open_unknowns_blocking / total_applicable)
    gap_penalty_value = max(0.0, min(1.0, gap_penalty_value))

    # ── 5. Compute weighted score ──────────────────────────────────
    raw_score = (
        trust_value * WEIGHT_TRUST
        + completeness_value * WEIGHT_COMPLETENESS
        + freshness_value * WEIGHT_FRESHNESS
        + gap_penalty_value * WEIGHT_GAP_PENALTY
    )
    score = round(raw_score * 100)
    score = max(0, min(100, score))

    grade = _score_to_grade(score)
    computed_at = datetime.now(UTC)

    return {
        "building_id": str(building_id),
        "score": score,
        "grade": grade,
        "trust": round(trust_value, 4),
        "completeness": round(completeness_value, 4),
        "freshness": round(freshness_value, 4),
        "gap_penalty": round(gap_penalty_value, 4),
        "breakdown": {
            "trust_weighted": round(trust_value * WEIGHT_TRUST, 4),
            "completeness_weighted": round(completeness_value * WEIGHT_COMPLETENESS, 4),
            "freshness_weighted": round(freshness_value * WEIGHT_FRESHNESS, 4),
            "gap_penalty_weighted": round(gap_penalty_value * WEIGHT_GAP_PENALTY, 4),
        },
        "computed_at": computed_at.isoformat(),
    }
