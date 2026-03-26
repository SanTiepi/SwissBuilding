"""Pilot Scorecard service — compute pilot success metrics from live data.

Aggregates real platform usage for an organization to measure pilot outcomes:
completeness improvement, enrichment velocity, proof coverage, etc.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.schemas.pilot_scorecard import PilotMetricResult, PilotScorecardResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Grade helpers
# ---------------------------------------------------------------------------

_GRADE_MAP = [
    (90, "A"),
    (75, "B"),
    (60, "C"),
    (45, "D"),
    (30, "E"),
    (0, "F"),
]


def _score_to_grade(score: float) -> str:
    for threshold, grade in _GRADE_MAP:
        if score >= threshold:
            return grade
    return "F"


# ---------------------------------------------------------------------------
# Internal metric computers
# ---------------------------------------------------------------------------


async def _completeness_improvement(db: AsyncSession, org_id: UUID) -> PilotMetricResult:
    """Measure average completeness score across org buildings."""
    stmt = select(func.avg(Building.completeness_score)).where(Building.organization_id == org_id)
    result = await db.execute(stmt)
    avg_score = result.scalar() or 0.0
    return PilotMetricResult(
        key="completeness_improvement",
        label="Amelioration completude",
        current_value=round(float(avg_score), 1),
        target_value=80.0,
        unit="%",
        description="Score moyen de completude des dossiers batiment.",
    )


async def _buildings_enriched(db: AsyncSession, org_id: UUID) -> PilotMetricResult:
    """Count buildings with at least one enrichment (diagnostic or document)."""
    # Buildings with at least one diagnostic
    diag_sub = (
        select(Diagnostic.building_id)
        .join(Building, Diagnostic.building_id == Building.id)
        .where(Building.organization_id == org_id)
        .distinct()
    )
    result = await db.execute(select(func.count()).select_from(diag_sub.subquery()))
    enriched = result.scalar() or 0

    total_stmt = select(func.count()).select_from(
        select(Building.id).where(Building.organization_id == org_id).subquery()
    )
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 1

    return PilotMetricResult(
        key="buildings_enriched_count",
        label="Batiments enrichis",
        current_value=float(enriched),
        target_value=float(total),
        unit="batiments",
        description="Nombre de batiments avec au moins un diagnostic ou enrichissement.",
    )


async def _diagnostics_integrated(db: AsyncSession, org_id: UUID) -> PilotMetricResult:
    """Count integrated diagnostics (completed or validated)."""
    stmt = (
        select(func.count())
        .select_from(Diagnostic)
        .join(Building, Diagnostic.building_id == Building.id)
        .where(
            Building.organization_id == org_id,
            Diagnostic.status.in_(["completed", "validated"]),
        )
    )
    result = await db.execute(stmt)
    count = result.scalar() or 0
    return PilotMetricResult(
        key="diagnostics_integrated_count",
        label="Diagnostics integres",
        current_value=float(count),
        target_value=10.0,
        unit="diagnostics",
        description="Nombre de diagnostics au statut complete ou valide.",
    )


async def _proof_coverage(db: AsyncSession, org_id: UUID) -> PilotMetricResult:
    """Measure proof coverage = buildings with evidence links / total buildings."""
    evidence_sub = (
        select(EvidenceLink.building_id)
        .join(Building, EvidenceLink.building_id == Building.id)
        .where(Building.organization_id == org_id)
        .distinct()
    )
    result = await db.execute(select(func.count()).select_from(evidence_sub.subquery()))
    with_evidence = result.scalar() or 0

    total_stmt = select(func.count()).select_from(
        select(Building.id).where(Building.organization_id == org_id).subquery()
    )
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 1

    pct = round((with_evidence / max(total, 1)) * 100, 1)
    return PilotMetricResult(
        key="proof_coverage_delta",
        label="Couverture preuves",
        current_value=pct,
        target_value=80.0,
        unit="%",
        description="Pourcentage de batiments avec au moins une preuve documentaire.",
    )


async def _documents_uploaded(db: AsyncSession, org_id: UUID) -> PilotMetricResult:
    """Count documents uploaded in the last 30 days."""
    cutoff = datetime.now(UTC) - timedelta(days=30)
    stmt = (
        select(func.count())
        .select_from(Document)
        .join(Building, Document.building_id == Building.id)
        .where(
            Building.organization_id == org_id,
            Document.created_at >= cutoff,
        )
    )
    result = await db.execute(stmt)
    count = result.scalar() or 0
    return PilotMetricResult(
        key="documents_uploaded_30d",
        label="Documents (30j)",
        current_value=float(count),
        target_value=20.0,
        unit="documents",
        description="Nombre de documents uploades dans les 30 derniers jours.",
    )


async def _blockers_resolved(db: AsyncSession, org_id: UUID) -> PilotMetricResult:
    """Estimate blockers resolved by counting completed action items."""
    from app.models.action_item import ActionItem

    stmt = (
        select(func.count())
        .select_from(ActionItem)
        .join(Building, ActionItem.building_id == Building.id)
        .where(
            Building.organization_id == org_id,
            ActionItem.status == "completed",
        )
    )
    result = await db.execute(stmt)
    count = result.scalar() or 0
    return PilotMetricResult(
        key="blockers_resolved",
        label="Blocages resolus",
        current_value=float(count),
        target_value=15.0,
        unit="actions",
        description="Nombre d'actions correctives completees.",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def compute_pilot_scorecard(
    db: AsyncSession,
    org_id: UUID,
) -> PilotScorecardResult:
    """Aggregate all pilot metrics for an organization and compute an overall score."""
    metrics: list[PilotMetricResult] = []

    for computer in [
        _completeness_improvement,
        _buildings_enriched,
        _diagnostics_integrated,
        _proof_coverage,
        _documents_uploaded,
        _blockers_resolved,
    ]:
        try:
            m = await computer(db, org_id)
            metrics.append(m)
        except Exception:
            logger.debug("Metric %s failed for org %s", computer.__name__, org_id, exc_info=True)

    # Overall score = average of (current/target) capped at 100, across all metrics
    if metrics:
        ratios = []
        for m in metrics:
            if m.target_value and m.target_value > 0:
                ratios.append(min(m.current_value / m.target_value, 1.0))
            else:
                ratios.append(0.0)
        pilot_score = round((sum(ratios) / len(ratios)) * 100, 1)
    else:
        pilot_score = 0.0

    return PilotScorecardResult(
        org_id=org_id,
        pilot_score=pilot_score,
        grade=_score_to_grade(pilot_score),
        metrics=metrics,
        computed_at=datetime.now(UTC).isoformat(),
    )
