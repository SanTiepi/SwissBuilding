"""Building Dashboard aggregate service.

Provides a single-call read model that combines all key metrics
a building detail page needs, replacing 10+ separate API calls.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_snapshot import BuildingSnapshot
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.unknown_issue import UnknownIssue
from app.models.zone import Zone
from app.schemas.building_dashboard import (
    BuildingDashboard,
    DashboardActivitySummary,
    DashboardAlertsSummary,
    DashboardCompletenessSummary,
    DashboardComplianceSummary,
    DashboardReadinessSummary,
    DashboardRiskSummary,
    DashboardTrustSummary,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _trust_level(score: float | None) -> str | None:
    """Map a numeric trust score to a categorical level."""
    if score is None:
        return None
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _risk_level_from_score(risk_score: float | None) -> str | None:
    """Map a numeric risk score to a categorical level."""
    if risk_score is None:
        return None
    if risk_score >= 0.75:
        return "critical"
    if risk_score >= 0.5:
        return "high"
    if risk_score >= 0.25:
        return "medium"
    return "low"


async def _get_activity_counts(db: AsyncSession, building_id: UUID) -> DashboardActivitySummary:
    """Fetch all activity counts in efficient queries."""
    # Diagnostics
    diag_result = await db.execute(
        select(
            func.count().label("total"),
            func.count().filter(Diagnostic.status.in_(("completed", "validated"))).label("completed"),
        )
        .select_from(Diagnostic)
        .where(Diagnostic.building_id == building_id)
    )
    diag_row = diag_result.one()

    # Interventions
    interv_result = await db.execute(
        select(
            func.count().label("total"),
            func.count().filter(Intervention.status.in_(("planned", "in_progress"))).label("active"),
        )
        .select_from(Intervention)
        .where(Intervention.building_id == building_id)
    )
    interv_row = interv_result.one()

    # Open actions
    actions_result = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .where(
            ActionItem.building_id == building_id,
            ActionItem.status == "open",
        )
    )
    open_actions = actions_result.scalar() or 0

    # Documents
    docs_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.building_id == building_id)
    )
    total_documents = docs_result.scalar() or 0

    # Zones
    zones_result = await db.execute(select(func.count()).select_from(Zone).where(Zone.building_id == building_id))
    total_zones = zones_result.scalar() or 0

    # Samples (via diagnostics)
    diag_ids_result = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
    diag_ids = [row[0] for row in diag_ids_result.all()]
    total_samples = 0
    if diag_ids:
        samples_result = await db.execute(
            select(func.count()).select_from(Sample).where(Sample.diagnostic_id.in_(diag_ids))
        )
        total_samples = samples_result.scalar() or 0

    return DashboardActivitySummary(
        total_diagnostics=diag_row.total,
        completed_diagnostics=diag_row.completed,
        total_interventions=interv_row.total,
        active_interventions=interv_row.active,
        open_actions=open_actions,
        total_documents=total_documents,
        total_zones=total_zones,
        total_samples=total_samples,
    )


async def _get_latest_snapshot(db: AsyncSession, building_id: UUID) -> BuildingSnapshot | None:
    """Get the most recent snapshot for a building."""
    result = await db.execute(
        select(BuildingSnapshot)
        .where(BuildingSnapshot.building_id == building_id)
        .order_by(BuildingSnapshot.captured_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_trust_summary(db: AsyncSession, building_id: UUID) -> DashboardTrustSummary:
    """Build trust summary from latest snapshot."""
    snapshot = await _get_latest_snapshot(db, building_id)
    if not snapshot or snapshot.overall_trust is None:
        return DashboardTrustSummary()

    # Determine trend from trust_state_json if available
    trend = None
    if snapshot.trust_state_json and isinstance(snapshot.trust_state_json, dict):
        trend = snapshot.trust_state_json.get("trend")

    return DashboardTrustSummary(
        score=snapshot.overall_trust,
        level=_trust_level(snapshot.overall_trust),
        trend=trend,
    )


async def _get_readiness_summary(db: AsyncSession, building_id: UUID) -> DashboardReadinessSummary:
    """Build readiness summary from readiness assessments."""
    try:
        from app.models.readiness_assessment import ReadinessAssessment

        result = await db.execute(select(ReadinessAssessment).where(ReadinessAssessment.building_id == building_id))
        assessments = list(result.scalars().all())

        if not assessments:
            return DashboardReadinessSummary(overall_status="unknown")

        gate_count = len(assessments)
        blocked_count = sum(1 for a in assessments if a.status == "blocked")
        ready_count = sum(1 for a in assessments if a.status in ("ready", "passed"))

        if ready_count == gate_count:
            overall_status = "ready"
        elif blocked_count == gate_count:
            overall_status = "not_ready"
        elif ready_count > 0:
            overall_status = "partially_ready"
        else:
            overall_status = "not_ready"

        return DashboardReadinessSummary(
            overall_status=overall_status,
            blocked_count=blocked_count,
            gate_count=gate_count,
        )
    except Exception:
        logger.exception("Error computing readiness summary for building %s", building_id)
        return DashboardReadinessSummary(overall_status="unknown")


async def _get_completeness_summary(db: AsyncSession, building_id: UUID) -> DashboardCompletenessSummary:
    """Build completeness summary from completeness engine."""
    try:
        from app.services.completeness_engine import evaluate_completeness

        result = await evaluate_completeness(db, building_id)
        category_scores: dict[str, float] = {}
        for check in result.checks:
            cat = check.category
            if cat not in category_scores:
                category_scores[cat] = 0.0
            if check.status == "complete":
                category_scores[cat] = category_scores.get(cat, 0.0) + check.weight

        missing_count = len(result.missing_items)
        return DashboardCompletenessSummary(
            overall_score=result.overall_score,
            category_scores=category_scores if category_scores else None,
            missing_count=missing_count,
        )
    except Exception:
        logger.exception("Error computing completeness for building %s", building_id)
        return DashboardCompletenessSummary()


async def _get_risk_summary(db: AsyncSession, building_id: UUID) -> DashboardRiskSummary:
    """Build risk summary from building risk score."""
    result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk = result.scalar_one_or_none()
    if not risk:
        return DashboardRiskSummary()

    # Build pollutant risks from individual probabilities
    pollutant_risks: dict[str, str] = {}
    for pollutant in ("asbestos", "pcb", "lead", "hap", "radon"):
        prob = getattr(risk, f"{pollutant}_probability", None)
        if prob is not None:
            if prob >= 0.75:
                pollutant_risks[pollutant] = "critical"
            elif prob >= 0.5:
                pollutant_risks[pollutant] = "high"
            elif prob >= 0.25:
                pollutant_risks[pollutant] = "medium"
            else:
                pollutant_risks[pollutant] = "low"

    # Compute an aggregate risk score from max probability
    probs = [getattr(risk, f"{p}_probability", 0.0) or 0.0 for p in ("asbestos", "pcb", "lead", "hap", "radon")]
    max_prob = max(probs) if probs else None

    return DashboardRiskSummary(
        risk_level=risk.overall_risk_level,
        risk_score=max_prob,
        pollutant_risks=pollutant_risks if pollutant_risks else None,
    )


async def _get_compliance_summary(db: AsyncSession, building_id: UUID) -> DashboardComplianceSummary:
    """Build compliance summary from compliance timeline service."""
    try:
        from app.services.compliance_timeline_service import (
            analyze_compliance_gaps,
            get_compliance_deadlines,
            get_pollutant_compliance_states,
        )

        states = await get_pollutant_compliance_states(db, building_id)
        deadlines = await get_compliance_deadlines(db, building_id)
        gaps = await analyze_compliance_gaps(db, building_id)

        # Determine overall status
        if not states:
            status = "unknown"
        elif all(ps.compliant for ps in states):
            status = "compliant"
        elif any(not ps.compliant for ps in states):
            any_compliant = any(ps.compliant for ps in states)
            status = "partially_compliant" if any_compliant else "non_compliant"
        else:
            status = "unknown"

        overdue_count = sum(1 for d in deadlines if d.status == "overdue")
        upcoming_count = sum(1 for d in deadlines if d.status == "upcoming")

        return DashboardComplianceSummary(
            status=status,
            overdue_count=overdue_count,
            upcoming_deadlines=upcoming_count,
            gap_count=gaps.total_gaps,
        )
    except Exception:
        logger.exception("Error computing compliance for building %s", building_id)
        return DashboardComplianceSummary(status="unknown")


async def _get_alerts_summary(db: AsyncSession, building_id: UUID) -> DashboardAlertsSummary:
    """Build alerts summary from weak signals, constraints, quality, and unknowns."""
    # Weak signals count
    weak_signals = 0
    try:
        from app.services.weak_signal_watchtower import scan_building_weak_signals

        ws_report = await scan_building_weak_signals(db, building_id)
        weak_signals = ws_report.total_signals
    except Exception:
        logger.exception("Error scanning weak signals for building %s", building_id)

    # Constraint blockers count
    constraint_blockers = 0
    try:
        from app.services.constraint_graph_service import build_constraint_graph

        graph = await build_constraint_graph(db, building_id)
        constraint_blockers = graph.blocked_count
    except Exception:
        logger.exception("Error computing constraint graph for building %s", building_id)

    # Quality issues count
    quality_issues = 0
    try:
        from app.models.data_quality_issue import DataQualityIssue

        qi_result = await db.execute(
            select(func.count())
            .select_from(DataQualityIssue)
            .where(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.status == "open",
            )
        )
        quality_issues = qi_result.scalar() or 0
    except Exception:
        logger.exception("Error counting quality issues for building %s", building_id)

    # Open unknowns count
    open_unknowns = 0
    try:
        unknowns_result = await db.execute(
            select(func.count())
            .select_from(UnknownIssue)
            .where(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
            )
        )
        open_unknowns = unknowns_result.scalar() or 0
    except Exception:
        logger.exception("Error counting unknowns for building %s", building_id)

    return DashboardAlertsSummary(
        weak_signals=weak_signals,
        constraint_blockers=constraint_blockers,
        quality_issues=quality_issues,
        open_unknowns=open_unknowns,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_building_dashboard(
    db: AsyncSession,
    building_id: UUID,
) -> BuildingDashboard | None:
    """Single call that aggregates all key metrics for a building dashboard.

    Queries building + counts diagnostics/interventions/actions/documents/zones/samples.
    Gets latest snapshot for grade/trust. Computes compliance, alerts summaries.
    Returns a complete dashboard object, or None if building not found.
    """
    # Load building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    # Latest snapshot for grade
    snapshot = await _get_latest_snapshot(db, building_id)
    passport_grade = snapshot.passport_grade if snapshot else None

    # Gather all summaries (each handles its own errors gracefully)
    trust = await _get_trust_summary(db, building_id)
    readiness = await _get_readiness_summary(db, building_id)
    completeness = await _get_completeness_summary(db, building_id)
    risk = await _get_risk_summary(db, building_id)
    compliance = await _get_compliance_summary(db, building_id)
    activity = await _get_activity_counts(db, building_id)
    alerts = await _get_alerts_summary(db, building_id)

    last_updated = snapshot.captured_at if snapshot else building.updated_at

    return BuildingDashboard(
        building_id=building.id,
        address=building.address,
        city=building.city,
        canton=building.canton,
        passport_grade=passport_grade,
        trust=trust,
        readiness=readiness,
        completeness=completeness,
        risk=risk,
        compliance=compliance,
        activity=activity,
        alerts=alerts,
        last_updated=last_updated,
    )


async def get_buildings_dashboard_list(
    db: AsyncSession,
    building_ids: list[UUID],
) -> list[BuildingDashboard]:
    """Batch version for portfolio views.

    Returns dashboards for multiple buildings. Uses efficient batch queries
    where possible.
    """
    dashboards: list[BuildingDashboard] = []
    for bid in building_ids:
        dashboard = await get_building_dashboard(db, bid)
        if dashboard is not None:
            dashboards.append(dashboard)
    return dashboards


async def get_dashboard_quick(
    db: AsyncSession,
    building_id: UUID,
) -> dict | None:
    """Lightweight version with only counts and current grade/risk.

    No service calls, just DB counts. For list views.
    Returns None if building not found.
    """
    # Load building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    # Latest snapshot for grade and trust
    snapshot = await _get_latest_snapshot(db, building_id)

    # Activity counts (DB only)
    activity = await _get_activity_counts(db, building_id)

    # Risk score (DB only)
    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk = risk_result.scalar_one_or_none()

    risk_level = None
    risk_score = None
    if risk:
        risk_level = risk.overall_risk_level
        probs = [getattr(risk, f"{p}_probability", 0.0) or 0.0 for p in ("asbestos", "pcb", "lead", "hap", "radon")]
        risk_score = max(probs) if probs else None

    return {
        "building_id": str(building.id),
        "address": building.address,
        "city": building.city,
        "canton": building.canton,
        "passport_grade": snapshot.passport_grade if snapshot else None,
        "trust_score": snapshot.overall_trust if snapshot else None,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "activity": activity.model_dump(),
        "last_updated": (snapshot.captured_at if snapshot else building.updated_at),
    }
