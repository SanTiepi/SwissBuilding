"""Portfolio summary aggregate service.

Builds a unified portfolio-level read model combining risk distribution,
compliance status, readiness overview, and activity metrics using efficient
COUNT/GROUP BY queries — never per-building service calls.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ALL_POLLUTANTS
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_change import BuildingSignal
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_snapshot import BuildingSnapshot
from app.models.campaign import Campaign
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.unknown_issue import UnknownIssue
from app.models.user import User
from app.schemas.portfolio_summary import (
    PortfolioActionSummary,
    PortfolioAlertSummary,
    PortfolioComplianceOverview,
    PortfolioGradeDistribution,
    PortfolioOverview,
    PortfolioPollutantExposure,
    PortfolioReadinessOverview,
    PortfolioRiskDistribution,
    PortfolioSummary,
)


def _active_buildings_filter(organization_id: UUID | None = None):
    """Return a base WHERE clause for active buildings, optionally filtered by org."""
    conditions = [Building.status == "active"]
    if organization_id is not None:
        conditions.append(Building.created_by.in_(select(User.id).where(User.organization_id == organization_id)))
    return conditions


async def _build_overview(db: AsyncSession, org_id: UUID | None) -> PortfolioOverview:
    filters = _active_buildings_filter(org_id)

    # Total buildings
    total_buildings_q = await db.execute(select(func.count()).select_from(Building).where(*filters))
    total_buildings = total_buildings_q.scalar() or 0

    # Total diagnostics
    diag_q = await db.execute(
        select(func.count())
        .select_from(Diagnostic)
        .join(Building, Building.id == Diagnostic.building_id)
        .where(*filters)
    )
    total_diagnostics = diag_q.scalar() or 0

    # Total interventions
    interv_q = await db.execute(
        select(func.count())
        .select_from(Intervention)
        .join(Building, Building.id == Intervention.building_id)
        .where(*filters)
    )
    total_interventions = interv_q.scalar() or 0

    # Total documents
    doc_q = await db.execute(
        select(func.count()).select_from(Document).join(Building, Building.id == Document.building_id).where(*filters)
    )
    total_documents = doc_q.scalar() or 0

    # Active campaigns
    campaign_filters = [Campaign.status == "active"]
    if org_id is not None:
        campaign_filters.append(Campaign.organization_id == org_id)
    camp_q = await db.execute(select(func.count()).select_from(Campaign).where(*campaign_filters))
    active_campaigns = camp_q.scalar() or 0

    # Avg completeness and trust from latest snapshots (one per building)
    latest_snap = (
        select(
            BuildingSnapshot.building_id,
            func.max(BuildingSnapshot.captured_at).label("max_captured"),
        )
        .group_by(BuildingSnapshot.building_id)
        .subquery()
    )
    snap_q = await db.execute(
        select(
            func.avg(BuildingSnapshot.completeness_score),
            func.avg(BuildingSnapshot.overall_trust),
        )
        .join(
            latest_snap,
            (BuildingSnapshot.building_id == latest_snap.c.building_id)
            & (BuildingSnapshot.captured_at == latest_snap.c.max_captured),
        )
        .join(Building, Building.id == BuildingSnapshot.building_id)
        .where(*filters)
    )
    row = snap_q.one()
    avg_completeness = round(float(row[0]), 3) if row[0] is not None else None
    avg_trust = round(float(row[1]), 3) if row[1] is not None else None

    return PortfolioOverview(
        total_buildings=total_buildings,
        total_diagnostics=total_diagnostics,
        total_interventions=total_interventions,
        total_documents=total_documents,
        active_campaigns=active_campaigns,
        avg_completeness=avg_completeness,
        avg_trust=avg_trust,
    )


async def _build_risk(db: AsyncSession, org_id: UUID | None) -> PortfolioRiskDistribution:
    filters = _active_buildings_filter(org_id)

    # Group by risk level
    risk_q = await db.execute(
        select(BuildingRiskScore.overall_risk_level, func.count())
        .join(Building, Building.id == BuildingRiskScore.building_id)
        .where(*filters)
        .group_by(BuildingRiskScore.overall_risk_level)
    )
    by_level = {"low": 0, "medium": 0, "high": 0, "critical": 0, "unknown": 0}
    for level, count in risk_q.all():
        key = level if level in by_level else "unknown"
        by_level[key] += count

    # Avg risk score (using confidence as proxy)
    avg_q = await db.execute(
        select(func.avg(BuildingRiskScore.confidence))
        .join(Building, Building.id == BuildingRiskScore.building_id)
        .where(*filters)
    )
    avg_val = avg_q.scalar()
    avg_risk_score = round(float(avg_val), 3) if avg_val is not None else None

    # Buildings above threshold (confidence > 0.7)
    threshold_q = await db.execute(
        select(func.count())
        .select_from(BuildingRiskScore)
        .join(Building, Building.id == BuildingRiskScore.building_id)
        .where(*filters, BuildingRiskScore.confidence > 0.7)
    )
    buildings_above_threshold = threshold_q.scalar() or 0

    return PortfolioRiskDistribution(
        by_level=by_level,
        avg_risk_score=avg_risk_score,
        buildings_above_threshold=buildings_above_threshold,
    )


async def _build_compliance(db: AsyncSession, org_id: UUID | None) -> PortfolioComplianceOverview:
    """Compliance based on latest diagnostic age per building.

    - compliant: latest diagnostic < 3 years old and status == 'validated'
    - non_compliant: latest diagnostic > 3 years old
    - partially_compliant: has diagnostic but not validated
    - unknown: no diagnostic at all
    """
    filters = _active_buildings_filter(org_id)
    three_years_ago = datetime.now(UTC) - timedelta(days=3 * 365)

    # Count buildings with no diagnostics at all
    has_diag_subq = select(distinct(Diagnostic.building_id)).subquery()
    unknown_q = await db.execute(
        select(func.count()).select_from(Building).where(*filters, Building.id.notin_(select(has_diag_subq)))
    )
    unknown_count = unknown_q.scalar() or 0

    # For buildings with diagnostics, get latest diagnostic per building
    latest_diag = (
        select(
            Diagnostic.building_id,
            func.max(Diagnostic.created_at).label("max_created"),
        )
        .group_by(Diagnostic.building_id)
        .subquery()
    )

    # Join to get status and date of latest diagnostic
    compliance_q = await db.execute(
        select(
            func.count(
                case(
                    (
                        (Diagnostic.status == "validated") & (Diagnostic.created_at >= three_years_ago),
                        Diagnostic.building_id,
                    ),
                )
            ),
            func.count(
                case(
                    (
                        Diagnostic.created_at < three_years_ago,
                        Diagnostic.building_id,
                    ),
                )
            ),
            func.count(
                case(
                    (
                        (Diagnostic.status != "validated") & (Diagnostic.created_at >= three_years_ago),
                        Diagnostic.building_id,
                    ),
                )
            ),
        )
        .join(
            latest_diag,
            (Diagnostic.building_id == latest_diag.c.building_id)
            & (Diagnostic.created_at == latest_diag.c.max_created),
        )
        .join(Building, Building.id == Diagnostic.building_id)
        .where(*filters)
    )
    row = compliance_q.one()
    compliant_count = row[0] or 0
    non_compliant_count = row[1] or 0
    partially_compliant_count = row[2] or 0

    # Overdue actions
    overdue_q = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .join(Building, Building.id == ActionItem.building_id)
        .where(
            *filters,
            ActionItem.status.in_(["open", "in_progress"]),
            ActionItem.due_date.isnot(None),
            ActionItem.due_date < datetime.now(UTC).date(),
        )
    )
    total_overdue = overdue_q.scalar() or 0

    return PortfolioComplianceOverview(
        compliant_count=compliant_count,
        non_compliant_count=non_compliant_count,
        partially_compliant_count=partially_compliant_count,
        unknown_count=unknown_count,
        total_overdue_deadlines=total_overdue,
    )


async def _build_readiness(db: AsyncSession, org_id: UUID | None) -> PortfolioReadinessOverview:
    """Classify buildings by completeness from latest snapshots.

    - ready: completeness_score > 0.8
    - partially_ready: 0.5 <= completeness_score <= 0.8
    - not_ready: completeness_score < 0.5
    - unknown: no snapshot
    """
    filters = _active_buildings_filter(org_id)

    # Latest snapshot per building
    latest_snap = (
        select(
            BuildingSnapshot.building_id,
            func.max(BuildingSnapshot.captured_at).label("max_captured"),
        )
        .group_by(BuildingSnapshot.building_id)
        .subquery()
    )

    readiness_q = await db.execute(
        select(
            func.count(case((BuildingSnapshot.completeness_score > 0.8, BuildingSnapshot.building_id))),
            func.count(
                case(
                    (
                        (BuildingSnapshot.completeness_score >= 0.5) & (BuildingSnapshot.completeness_score <= 0.8),
                        BuildingSnapshot.building_id,
                    )
                )
            ),
            func.count(case((BuildingSnapshot.completeness_score < 0.5, BuildingSnapshot.building_id))),
        )
        .join(
            latest_snap,
            (BuildingSnapshot.building_id == latest_snap.c.building_id)
            & (BuildingSnapshot.captured_at == latest_snap.c.max_captured),
        )
        .join(Building, Building.id == BuildingSnapshot.building_id)
        .where(*filters)
    )
    row = readiness_q.one()
    ready_count = row[0] or 0
    partially_ready_count = row[1] or 0
    not_ready_count = row[2] or 0

    # Buildings without snapshots
    has_snap_subq = select(distinct(BuildingSnapshot.building_id)).subquery()
    unknown_q = await db.execute(
        select(func.count()).select_from(Building).where(*filters, Building.id.notin_(select(has_snap_subq)))
    )
    unknown_count = unknown_q.scalar() or 0

    return PortfolioReadinessOverview(
        ready_count=ready_count,
        partially_ready_count=partially_ready_count,
        not_ready_count=not_ready_count,
        unknown_count=unknown_count,
    )


async def _build_grades(db: AsyncSession, org_id: UUID | None) -> PortfolioGradeDistribution:
    filters = _active_buildings_filter(org_id)

    latest_snap = (
        select(
            BuildingSnapshot.building_id,
            func.max(BuildingSnapshot.captured_at).label("max_captured"),
        )
        .group_by(BuildingSnapshot.building_id)
        .subquery()
    )

    grade_q = await db.execute(
        select(BuildingSnapshot.passport_grade, func.count())
        .join(
            latest_snap,
            (BuildingSnapshot.building_id == latest_snap.c.building_id)
            & (BuildingSnapshot.captured_at == latest_snap.c.max_captured),
        )
        .join(Building, Building.id == BuildingSnapshot.building_id)
        .where(*filters)
        .group_by(BuildingSnapshot.passport_grade)
    )
    by_grade: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "None": 0}
    for grade, count in grade_q.all():
        key = grade if grade in ("A", "B", "C", "D", "E") else "None"
        by_grade[key] += count

    return PortfolioGradeDistribution(by_grade=by_grade)


async def _build_actions(db: AsyncSession, org_id: UUID | None) -> PortfolioActionSummary:
    filters = _active_buildings_filter(org_id)

    # By status
    status_q = await db.execute(
        select(ActionItem.status, func.count())
        .join(Building, Building.id == ActionItem.building_id)
        .where(*filters)
        .group_by(ActionItem.status)
    )
    status_map: dict[str, int] = {}
    for s, c in status_q.all():
        status_map[s] = c

    # By priority (only open/in_progress)
    priority_q = await db.execute(
        select(ActionItem.priority, func.count())
        .join(Building, Building.id == ActionItem.building_id)
        .where(*filters, ActionItem.status.in_(["open", "in_progress"]))
        .group_by(ActionItem.priority)
    )
    by_priority: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for p, c in priority_q.all():
        if p in by_priority:
            by_priority[p] += c

    # Overdue count
    overdue_q = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .join(Building, Building.id == ActionItem.building_id)
        .where(
            *filters,
            ActionItem.status.in_(["open", "in_progress"]),
            ActionItem.due_date.isnot(None),
            ActionItem.due_date < datetime.now(UTC).date(),
        )
    )
    overdue_count = overdue_q.scalar() or 0

    return PortfolioActionSummary(
        total_open=status_map.get("open", 0),
        total_in_progress=status_map.get("in_progress", 0),
        total_completed=status_map.get("completed", 0),
        by_priority=by_priority,
        overdue_count=overdue_count,
    )


async def _build_alerts(db: AsyncSession, org_id: UUID | None) -> PortfolioAlertSummary:
    filters = _active_buildings_filter(org_id)

    # Weak signals (active building signals)
    signals_q = await db.execute(
        select(func.count())
        .select_from(BuildingSignal)
        .join(Building, Building.id == BuildingSignal.building_id)
        .where(*filters, BuildingSignal.status == "active")
    )
    total_weak_signals = signals_q.scalar() or 0

    # Buildings on critical path (risk_level high or critical)
    critical_q = await db.execute(
        select(func.count())
        .select_from(BuildingRiskScore)
        .join(Building, Building.id == BuildingRiskScore.building_id)
        .where(*filters, BuildingRiskScore.overall_risk_level.in_(["high", "critical"]))
    )
    buildings_on_critical_path = critical_q.scalar() or 0

    # Constraint blockers (open unknowns that block readiness)
    blockers_q = await db.execute(
        select(func.count())
        .select_from(UnknownIssue)
        .join(Building, Building.id == UnknownIssue.building_id)
        .where(*filters, UnknownIssue.status == "open", UnknownIssue.blocks_readiness.is_(True))
    )
    total_constraint_blockers = blockers_q.scalar() or 0

    # Buildings with stale diagnostics (> 3 open unknowns)
    stale_subq = (
        select(UnknownIssue.building_id)
        .join(Building, Building.id == UnknownIssue.building_id)
        .where(*filters, UnknownIssue.status == "open")
        .group_by(UnknownIssue.building_id)
        .having(func.count() > 3)
        .subquery()
    )
    stale_q = await db.execute(select(func.count()).select_from(stale_subq))
    buildings_with_stale_diagnostics = stale_q.scalar() or 0

    return PortfolioAlertSummary(
        total_weak_signals=total_weak_signals,
        buildings_on_critical_path=buildings_on_critical_path,
        total_constraint_blockers=total_constraint_blockers,
        buildings_with_stale_diagnostics=buildings_with_stale_diagnostics,
    )


async def _build_pollutant_exposure(db: AsyncSession, org_id: UUID | None) -> list[PortfolioPollutantExposure]:
    """Build per-pollutant exposure summaries across the portfolio.

    For each pollutant in ALL_POLLUTANTS:
    - Count distinct buildings with at least one diagnostic of that type
    - Count buildings missing that diagnostic type
    - Count open unknown issues that block readiness and mention the pollutant
    """
    filters = _active_buildings_filter(org_id)

    # Total active buildings
    total_q = await db.execute(select(func.count()).select_from(Building).where(*filters))
    total_buildings = total_q.scalar() or 0

    if total_buildings == 0:
        return [PortfolioPollutantExposure(pollutant=p, total_buildings=0) for p in ALL_POLLUTANTS]

    # Count distinct buildings per pollutant diagnostic type (single query)
    assessed_q = await db.execute(
        select(Diagnostic.diagnostic_type, func.count(distinct(Diagnostic.building_id)))
        .join(Building, Building.id == Diagnostic.building_id)
        .where(*filters, Diagnostic.diagnostic_type.in_(ALL_POLLUTANTS))
        .group_by(Diagnostic.diagnostic_type)
    )
    assessed_map: dict[str, int] = {}
    for dtype, cnt in assessed_q.all():
        assessed_map[dtype] = cnt

    # Count readiness-blocking unknowns that reference each pollutant in title/description
    # Use a single query grouping by pollutant keyword match
    blocker_map: dict[str, int] = {}
    for pollutant in ALL_POLLUTANTS:
        pattern = f"%{pollutant}%"
        blocker_q = await db.execute(
            select(func.count())
            .select_from(UnknownIssue)
            .join(Building, Building.id == UnknownIssue.building_id)
            .where(
                *filters,
                UnknownIssue.status == "open",
                UnknownIssue.blocks_readiness.is_(True),
                (UnknownIssue.title.ilike(pattern) | UnknownIssue.unknown_type.ilike(pattern)),
            )
        )
        count = blocker_q.scalar() or 0
        if count > 0:
            blocker_map[pollutant] = count

    results = []
    for pollutant in ALL_POLLUTANTS:
        assessed = assessed_map.get(pollutant, 0)
        missing = total_buildings - assessed
        coverage = round(assessed / total_buildings, 4) if total_buildings > 0 else 0.0
        results.append(
            PortfolioPollutantExposure(
                pollutant=pollutant,
                buildings_assessed=assessed,
                buildings_missing=missing,
                total_buildings=total_buildings,
                coverage_ratio=coverage,
                readiness_blockers=blocker_map.get(pollutant, 0),
            )
        )
    return results


async def get_portfolio_summary(
    db: AsyncSession,
    organization_id: UUID | None = None,
) -> PortfolioSummary:
    """Full portfolio summary combining all dimensions."""
    overview = await _build_overview(db, organization_id)
    risk = await _build_risk(db, organization_id)
    compliance = await _build_compliance(db, organization_id)
    readiness = await _build_readiness(db, organization_id)
    grades = await _build_grades(db, organization_id)
    actions = await _build_actions(db, organization_id)
    alerts = await _build_alerts(db, organization_id)
    pollutant_exposure = await _build_pollutant_exposure(db, organization_id)

    return PortfolioSummary(
        overview=overview,
        risk=risk,
        compliance=compliance,
        readiness=readiness,
        grades=grades,
        actions=actions,
        alerts=alerts,
        pollutant_exposure=pollutant_exposure,
        generated_at=datetime.now(UTC),
        organization_id=organization_id,
    )


async def get_portfolio_comparison(
    db: AsyncSession,
    org_ids: list[UUID],
) -> list[PortfolioSummary]:
    """Compare portfolio summaries across organizations."""
    results = []
    for org_id in org_ids:
        summary = await get_portfolio_summary(db, organization_id=org_id)
        results.append(summary)
    return results


async def get_portfolio_health_score(
    db: AsyncSession,
    organization_id: UUID | None = None,
) -> dict:
    """Single 0-100 health score combining risk, compliance, readiness, and completeness.

    Weights:
    - Risk: 30% (inverse of high/critical ratio)
    - Compliance: 25% (compliant ratio)
    - Readiness: 25% (ready ratio)
    - Completeness: 20% (avg completeness from snapshots)
    """
    summary = await get_portfolio_summary(db, organization_id)
    total = summary.overview.total_buildings

    if total == 0:
        return {
            "score": 0,
            "breakdown": {
                "risk": {"score": 0, "weight": 0.30},
                "compliance": {"score": 0, "weight": 0.25},
                "readiness": {"score": 0, "weight": 0.25},
                "completeness": {"score": 0, "weight": 0.20},
            },
            "total_buildings": 0,
            "organization_id": str(organization_id) if organization_id else None,
        }

    # Risk score (inverse: fewer high/critical = better)
    high_critical = summary.risk.by_level.get("high", 0) + summary.risk.by_level.get("critical", 0)
    risk_score = max(0, 100 - (high_critical / total * 100))

    # Compliance score
    compliant_total = (
        summary.compliance.compliant_count
        + summary.compliance.non_compliant_count
        + summary.compliance.partially_compliant_count
        + summary.compliance.unknown_count
    )
    if compliant_total > 0:
        compliance_score = summary.compliance.compliant_count / compliant_total * 100
    else:
        compliance_score = 0

    # Readiness score
    readiness_total = (
        summary.readiness.ready_count
        + summary.readiness.partially_ready_count
        + summary.readiness.not_ready_count
        + summary.readiness.unknown_count
    )
    if readiness_total > 0:
        readiness_score = summary.readiness.ready_count / readiness_total * 100
    else:
        readiness_score = 0

    # Completeness score
    completeness_score = (summary.overview.avg_completeness or 0) * 100

    # Weighted total
    overall = risk_score * 0.30 + compliance_score * 0.25 + readiness_score * 0.25 + completeness_score * 0.20

    return {
        "score": round(overall, 1),
        "breakdown": {
            "risk": {"score": round(risk_score, 1), "weight": 0.30},
            "compliance": {"score": round(compliance_score, 1), "weight": 0.25},
            "readiness": {"score": round(readiness_score, 1), "weight": 0.25},
            "completeness": {"score": round(completeness_score, 1), "weight": 0.20},
        },
        "total_buildings": total,
        "organization_id": str(organization_id) if organization_id else None,
    }
