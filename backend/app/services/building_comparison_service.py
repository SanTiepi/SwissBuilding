"""
SwissBuildingOS - Building Comparison Service

Compares 2-10 buildings side by side across passport, trust, readiness,
and completeness dimensions. Aggregates per-building metrics and computes
cross-building statistics (best/worst passport, averages).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.readiness_assessment import ReadinessAssessment
from app.models.unknown_issue import UnknownIssue
from app.schemas.building_comparison import (
    BuildingComparison,
    BuildingComparisonEntry,
)
from app.services.completeness_engine import evaluate_completeness
from app.services.passport_service import get_passport_summary

# Grade ordering for comparison (lower index = better grade)
_GRADE_ORDER = ["A", "B", "C", "D", "F"]

COMPARISON_DIMENSIONS = [
    "passport",
    "trust",
    "completeness",
    "readiness",
    "actions",
    "unknowns",
    "contradictions",
    "diagnostics",
]


def _grade_rank(grade: str | None) -> int:
    """Return numeric rank for a grade. Lower = better. None = worst."""
    if grade is None:
        return len(_GRADE_ORDER)
    try:
        return _GRADE_ORDER.index(grade)
    except ValueError:
        return len(_GRADE_ORDER)


async def _build_entry(
    db: AsyncSession,
    building: Building,
) -> BuildingComparisonEntry:
    """Build a comparison entry for a single building."""
    building_id = building.id

    # -- Passport --
    passport = await get_passport_summary(db, building_id)
    passport_grade: str | None = None
    passport_score: float | None = None
    if passport is not None:
        passport_grade = passport.get("passport_grade")
        # Use completeness overall_score as passport_score proxy
        completeness_data = passport.get("completeness", {})
        passport_score = completeness_data.get("overall_score")

    # -- Trust score (latest) --
    trust_result = await db.execute(
        select(BuildingTrustScore)
        .where(BuildingTrustScore.building_id == building_id)
        .order_by(BuildingTrustScore.assessed_at.desc())
        .limit(1)
    )
    trust_record = trust_result.scalar_one_or_none()
    trust_score = trust_record.overall_score if trust_record else None

    # -- Completeness --
    completeness_result = await evaluate_completeness(db, building_id)
    completeness_score = completeness_result.overall_score

    # -- Readiness summary --
    readiness_result = await db.execute(
        select(ReadinessAssessment).where(ReadinessAssessment.building_id == building_id)
    )
    readiness_records = list(readiness_result.scalars().all())
    readiness_summary: dict[str, bool] = {}
    for ra in readiness_records:
        readiness_summary[ra.readiness_type] = ra.status == "ready"

    # Fill defaults for missing readiness types
    for rtype in ("safe_to_start", "safe_to_tender", "safe_to_reopen", "safe_to_requalify"):
        if rtype not in readiness_summary:
            readiness_summary[rtype] = False

    # -- Open actions count --
    open_actions_result = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .where(
            and_(
                ActionItem.building_id == building_id,
                ActionItem.status == "open",
            )
        )
    )
    open_actions_count = open_actions_result.scalar() or 0

    # -- Open unknowns count --
    open_unknowns_result = await db.execute(
        select(func.count())
        .select_from(UnknownIssue)
        .where(
            and_(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
            )
        )
    )
    open_unknowns_count = open_unknowns_result.scalar() or 0

    # -- Contradictions count --
    contradictions_result = await db.execute(
        select(func.count())
        .select_from(DataQualityIssue)
        .where(
            and_(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.issue_type == "contradiction",
                DataQualityIssue.status != "resolved",
            )
        )
    )
    contradictions_count = contradictions_result.scalar() or 0

    # -- Diagnostic count and latest date --
    diag_count_result = await db.execute(
        select(func.count()).select_from(Diagnostic).where(Diagnostic.building_id == building_id)
    )
    diagnostic_count = diag_count_result.scalar() or 0

    latest_diag_result = await db.execute(
        select(func.max(Diagnostic.date_inspection)).where(Diagnostic.building_id == building_id)
    )
    last_diagnostic_date = latest_diag_result.scalar()

    # Build display name
    building_name = f"{building.address}, {building.postal_code} {building.city}"

    return BuildingComparisonEntry(
        building_id=str(building_id),
        building_name=building_name,
        address=building.address,
        passport_grade=passport_grade,
        passport_score=passport_score,
        trust_score=trust_score,
        completeness_score=completeness_score,
        readiness_summary=readiness_summary,
        open_actions_count=open_actions_count,
        open_unknowns_count=open_unknowns_count,
        contradictions_count=contradictions_count,
        diagnostic_count=diagnostic_count,
        last_diagnostic_date=last_diagnostic_date,
    )


async def compare_buildings(
    db: AsyncSession,
    building_ids: list[str],
) -> BuildingComparison:
    """Compare 2-10 buildings side by side.

    Args:
        db: Async database session.
        building_ids: List of building UUID strings (2-10).

    Returns:
        BuildingComparison with per-building entries and aggregate stats.

    Raises:
        ValueError: If fewer than 2 or more than 10 building IDs, or if any building not found.
    """
    if len(building_ids) < 2:
        raise ValueError("At least 2 building IDs are required for comparison")
    if len(building_ids) > 10:
        raise ValueError("At most 10 building IDs can be compared at once")

    # Validate all buildings exist
    uuid_ids = [UUID(bid) for bid in building_ids]
    buildings_result = await db.execute(select(Building).where(Building.id.in_(uuid_ids)))
    buildings = {b.id: b for b in buildings_result.scalars().all()}

    missing = [bid for bid in building_ids if UUID(bid) not in buildings]
    if missing:
        raise ValueError(f"Buildings not found: {', '.join(missing)}")

    # Build entries preserving requested order
    entries: list[BuildingComparisonEntry] = []
    for bid in building_ids:
        building = buildings[UUID(bid)]
        entry = await _build_entry(db, building)
        entries.append(entry)

    # Compute aggregates
    # Best/worst passport
    graded = [e for e in entries if e.passport_grade is not None]
    best_passport: str | None = None
    worst_passport: str | None = None
    if graded:
        best = min(graded, key=lambda e: _grade_rank(e.passport_grade))
        worst = max(graded, key=lambda e: _grade_rank(e.passport_grade))
        best_passport = best.building_id
        worst_passport = worst.building_id

    # Average trust
    trust_values = [e.trust_score for e in entries if e.trust_score is not None]
    average_trust = round(sum(trust_values) / len(trust_values), 4) if trust_values else 0.0

    # Average completeness
    comp_values = [e.completeness_score for e in entries if e.completeness_score is not None]
    average_completeness = round(sum(comp_values) / len(comp_values), 4) if comp_values else 0.0

    return BuildingComparison(
        buildings=entries,
        comparison_dimensions=COMPARISON_DIMENSIONS,
        best_passport=best_passport,
        worst_passport=worst_passport,
        average_trust=average_trust,
        average_completeness=average_completeness,
    )
