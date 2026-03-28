"""BatiConnect -- Pilot Scorecard Service.

Two layers:
  1. Legacy `compute_pilot_scorecard` (used by demo_path.py) -- preserved
  2. New G2 scorecard functions for pilot conversion:
     - get_pilot_scorecard(org)
     - get_building_scorecard(building)
     - get_weekly_summary(org)

Derives pilot conversion metrics from existing data -- NO new database tables.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from datetime import date as date_type
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_pack import EvidencePack
from app.schemas.pilot_scorecard import PilotMetricResult, PilotScorecardResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_THREE_YEARS = timedelta(days=3 * 365)


# ---------------------------------------------------------------------------
# Grade helpers (legacy)
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
# Shared helpers
# ---------------------------------------------------------------------------


def _is_diagnostic_valid(diag_report_date: date_type | None, reference_date: date_type | None = None) -> bool:
    """Check if a diagnostic is still valid (< 3 years old)."""
    if diag_report_date is None:
        return False
    ref = reference_date or datetime.now(UTC).date()
    expiry = diag_report_date + _THREE_YEARS
    if isinstance(expiry, datetime):
        expiry = expiry.date()
    return expiry >= ref


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is UTC-aware (handles naive datetimes from SQLite)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _compute_trend(completed: int, created: int) -> str:
    net = completed - created
    if net > 2:
        return "improving"
    if net < -2:
        return "degrading"
    return "stable"


def _compute_pilot_health(
    resolution_rate: float,
    completion_rate: float,
    buildings_ready: int,
    total_buildings: int,
) -> str:
    if total_buildings == 0:
        return "on_track"
    ready_pct = (buildings_ready / total_buildings) * 100 if total_buildings > 0 else 0
    if resolution_rate >= 50 and completion_rate >= 40 and ready_pct >= 20:
        return "on_track"
    if resolution_rate < 20 or completion_rate < 15:
        return "behind"
    return "at_risk"


def _stage_label(stage: str) -> str:
    labels = {
        "not_assessed": "Non evalue",
        "partially_ready": "Partiellement pret",
        "ready": "Pret",
        "pack_generated": "Pack genere",
        "submitted": "Soumis",
        "complement_requested": "Complement demande",
        "acknowledged": "Accuse de reception",
    }
    return labels.get(stage, stage)


# ---------------------------------------------------------------------------
# Legacy: compute_pilot_scorecard (used by demo_path.py)
# ---------------------------------------------------------------------------


async def _completeness_improvement(db: AsyncSession, org_id: UUID) -> PilotMetricResult:
    stmt = select(func.count()).select_from(Building).where(Building.organization_id == org_id)
    total_result = await db.execute(stmt)
    total = total_result.scalar() or 0

    # Count buildings with at least one completed diagnostic + document
    diag_sub = (
        select(Diagnostic.building_id)
        .join(Building, Diagnostic.building_id == Building.id)
        .where(
            Building.organization_id == org_id,
            Diagnostic.status.in_(["completed", "validated"]),
        )
        .distinct()
    )
    diag_result = await db.execute(select(func.count()).select_from(diag_sub.subquery()))
    with_diag = diag_result.scalar() or 0

    avg_score = round((with_diag / max(total, 1)) * 100, 1)
    return PilotMetricResult(
        key="completeness_improvement",
        label="Amelioration completude",
        current_value=avg_score,
        target_value=80.0,
        unit="%",
        description="Score moyen de completude des dossiers batiment.",
    )


async def _buildings_enriched(db: AsyncSession, org_id: UUID) -> PilotMetricResult:
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
    doc_sub = (
        select(Document.building_id)
        .join(Building, Document.building_id == Building.id)
        .where(Building.organization_id == org_id)
        .distinct()
    )
    result = await db.execute(select(func.count()).select_from(doc_sub.subquery()))
    with_docs = result.scalar() or 0

    total_stmt = select(func.count()).select_from(
        select(Building.id).where(Building.organization_id == org_id).subquery()
    )
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 1

    pct = round((with_docs / max(total, 1)) * 100, 1)
    return PilotMetricResult(
        key="proof_coverage_delta",
        label="Couverture preuves",
        current_value=pct,
        target_value=80.0,
        unit="%",
        description="Pourcentage de batiments avec au moins une preuve documentaire.",
    )


async def _documents_uploaded(db: AsyncSession, org_id: UUID) -> PilotMetricResult:
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
    stmt = (
        select(func.count())
        .select_from(ActionItem)
        .join(Building, ActionItem.building_id == Building.id)
        .where(
            Building.organization_id == org_id,
            ActionItem.status == "done",
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


async def compute_pilot_scorecard(
    db: AsyncSession,
    org_id: UUID,
) -> PilotScorecardResult:
    """Legacy: aggregate all pilot metrics for an organization and compute overall score."""
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


# ===========================================================================
# G2: New pilot conversion scorecard functions
# ===========================================================================


async def get_pilot_scorecard(
    db: AsyncSession,
    org_id: UUID,
    baseline_date: date_type | None = None,
) -> dict:
    """Generate pilot scorecard for an organization.

    Aggregates across all buildings in the org to produce conversion-ready
    metrics proving BatiConnect value.
    """
    now = datetime.now(UTC)
    today = now.date()
    start = baseline_date or (today - timedelta(days=30))

    # 1. Buildings
    bld_q = select(Building).where(Building.organization_id == org_id)
    bld_result = await db.execute(bld_q)
    buildings = list(bld_result.scalars().all())
    building_ids = [b.id for b in buildings]
    total_buildings = len(buildings)

    if total_buildings == 0:
        return _empty_scorecard(org_id, start, today)

    # 2. Diagnostics
    diag_q = select(Diagnostic).where(Diagnostic.building_id.in_(building_ids))
    diag_result = await db.execute(diag_q)
    diagnostics = list(diag_result.scalars().all())

    total_diagnostics = len(diagnostics)
    valid_diagnostics = sum(
        1 for d in diagnostics if d.status in ("completed", "validated") and _is_diagnostic_valid(d.date_report, today)
    )
    expired_diagnostics = sum(
        1
        for d in diagnostics
        if d.status in ("completed", "validated") and not _is_diagnostic_valid(d.date_report, today)
    )

    buildings_with_diag: set[UUID] = set()
    for d in diagnostics:
        if d.status in ("completed", "validated"):
            buildings_with_diag.add(d.building_id)
    assessed_count = len(buildings_with_diag)
    missing_coverage = total_buildings - assessed_count

    # 3. Actions
    all_actions_q = select(ActionItem).where(ActionItem.building_id.in_(building_ids))
    all_actions_result = await db.execute(all_actions_q)
    all_actions = list(all_actions_result.scalars().all())

    total_created = len(all_actions)
    completed_actions = [a for a in all_actions if a.status == "done"]
    total_completed = len(completed_actions)
    open_actions = [a for a in all_actions if a.status in ("open", "in_progress", "blocked")]

    completion_rate = round((total_completed / total_created) * 100, 1) if total_created > 0 else 0.0

    resolution_days: list[float] = []
    for a in completed_actions:
        if a.completed_at and a.created_at:
            completed_ts = (
                a.completed_at
                if isinstance(a.completed_at, datetime)
                else datetime.combine(a.completed_at, datetime.min.time(), tzinfo=UTC)
            )
            created_ts = (
                a.created_at
                if isinstance(a.created_at, datetime)
                else datetime.combine(a.created_at, datetime.min.time(), tzinfo=UTC)
            )
            if completed_ts.tzinfo is None:
                completed_ts = completed_ts.replace(tzinfo=UTC)
            if created_ts.tzinfo is None:
                created_ts = created_ts.replace(tzinfo=UTC)
            delta = (completed_ts - created_ts).total_seconds() / 86400
            if delta >= 0:
                resolution_days.append(delta)
    avg_resolution = round(sum(resolution_days) / len(resolution_days), 1) if resolution_days else None

    blockers = [a for a in open_actions if a.priority in ("critical", "high")]
    total_blockers = len(blockers) + len([a for a in completed_actions if a.priority in ("critical", "high")])
    blockers_resolved = len([a for a in completed_actions if a.priority in ("critical", "high")])
    resolution_rate = round((blockers_resolved / total_blockers) * 100, 1) if total_blockers > 0 else 0.0

    buildings_with_blockers: set[UUID] = set()
    for a in open_actions:
        if a.priority in ("critical", "high"):
            buildings_with_blockers.add(a.building_id)

    # 4. Completeness proxy
    doc_q = select(Document).where(Document.building_id.in_(building_ids))
    doc_result = await db.execute(doc_q)
    documents = list(doc_result.scalars().all())

    buildings_with_docs: set[UUID] = set()
    for d in documents:
        buildings_with_docs.add(d.building_id)

    buildings_with_basic = buildings_with_diag & buildings_with_docs
    avg_completeness = (
        round(
            (len(buildings_with_basic) / total_buildings) * 100,
            1,
        )
        if total_buildings > 0
        else 0.0
    )

    # 5. Packs / dossiers
    pack_q = select(EvidencePack).where(
        and_(
            EvidencePack.building_id.in_(building_ids),
            EvidencePack.pack_type == "authority_pack",
        )
    )
    pack_result = await db.execute(pack_q)
    packs = list(pack_result.scalars().all())

    packs_generated = len(packs)
    packs_submitted = sum(1 for p in packs if p.submitted_at is not None)
    complements_received = sum(1 for p in packs if p.notes and "complement_requested" in (p.notes or ""))
    acknowledged = sum(1 for p in packs if p.status == "acknowledged")

    # 6. Ready buildings
    buildings_valid_diags: set[UUID] = set()
    for d in diagnostics:
        if d.status in ("completed", "validated") and _is_diagnostic_valid(d.date_report, today):
            buildings_valid_diags.add(d.building_id)

    ready_buildings = buildings_valid_diags - buildings_with_blockers
    ready_count = len(ready_buildings & buildings_with_docs)

    # 7. Time to safe_to_start
    time_to_sts: list[float] = []
    for p in packs:
        if p.submitted_at and p.building_id:
            building_actions = [a for a in all_actions if a.building_id == p.building_id and a.created_at]
            if building_actions:
                earliest = min(a.created_at for a in building_actions)
                sub_ts = p.submitted_at
                if isinstance(earliest, datetime) and isinstance(sub_ts, datetime):
                    if earliest.tzinfo is None:
                        earliest = earliest.replace(tzinfo=UTC)
                    if sub_ts.tzinfo is None:
                        sub_ts = sub_ts.replace(tzinfo=UTC)
                    days = (sub_ts - earliest).total_seconds() / 86400
                    if days >= 0:
                        time_to_sts.append(days)

    fastest = round(min(time_to_sts), 0) if time_to_sts else None
    avg_sts = round(sum(time_to_sts) / len(time_to_sts), 1) if len(time_to_sts) >= 2 else None

    # 8. Trend + health
    week_ago = now - timedelta(days=7)
    recent_completed = sum(1 for a in completed_actions if a.completed_at and _ensure_utc(a.completed_at) >= week_ago)
    recent_created = sum(1 for a in all_actions if a.created_at and _ensure_utc(a.created_at) >= week_ago)
    trend = _compute_trend(recent_completed, recent_created)
    pilot_health = _compute_pilot_health(resolution_rate, completion_rate, ready_count, total_buildings)

    return {
        "org_id": str(org_id),
        "period": {"start": start.isoformat(), "end": today.isoformat()},
        "buildings": {
            "total": total_buildings,
            "assessed": assessed_count,
            "ready": ready_count,
            "submitted": packs_submitted,
            "acknowledged": acknowledged,
        },
        "readiness": {
            "avg_completeness_pct": avg_completeness,
            "buildings_with_blockers": len(buildings_with_blockers),
            "total_blockers": total_blockers,
            "blockers_resolved": blockers_resolved,
            "resolution_rate_pct": resolution_rate,
        },
        "actions": {
            "total_created": total_created,
            "total_completed": total_completed,
            "completion_rate_pct": completion_rate,
            "avg_resolution_days": avg_resolution,
        },
        "dossiers": {
            "packs_generated": packs_generated,
            "packs_submitted": packs_submitted,
            "complements_received": complements_received,
            "acknowledged": acknowledged,
        },
        "time_to_safe_to_start": {
            "fastest_days": fastest,
            "avg_days": avg_sts,
            "buildings_achieved": len(time_to_sts),
        },
        "diagnostics": {
            "total": total_diagnostics,
            "valid": valid_diagnostics,
            "expired": expired_diagnostics,
            "missing_coverage": missing_coverage,
        },
        "trend": trend,
        "pilot_health": pilot_health,
    }


async def get_building_scorecard(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Per-building scorecard showing before/after metrics."""
    today = datetime.now(UTC).date()

    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    if building is None:
        return {"error": "building_not_found", "building_id": str(building_id)}

    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())
    total_diags = len(diagnostics)
    valid_diags = sum(
        1 for d in diagnostics if d.status in ("completed", "validated") and _is_diagnostic_valid(d.date_report, today)
    )
    expired_diags = sum(
        1
        for d in diagnostics
        if d.status in ("completed", "validated") and not _is_diagnostic_valid(d.date_report, today)
    )

    action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = list(action_result.scalars().all())
    total_actions = len(actions)
    done_actions = sum(1 for a in actions if a.status == "done")
    open_count = sum(1 for a in actions if a.status in ("open", "in_progress", "blocked"))
    blockers_open = sum(
        1 for a in actions if a.status in ("open", "in_progress", "blocked") and a.priority in ("critical", "high")
    )

    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = list(doc_result.scalars().all())
    doc_count = len(documents)

    pack_result = await db.execute(
        select(EvidencePack).where(
            and_(
                EvidencePack.building_id == building_id,
                EvidencePack.pack_type == "authority_pack",
            )
        )
    )
    packs = list(pack_result.scalars().all())
    latest_pack = max(packs, key=lambda p: p.created_at or datetime.min, default=None)

    dossier_stage = "not_assessed"
    if latest_pack:
        notes = latest_pack.notes or ""
        if "complement_requested" in notes:
            dossier_stage = "complement_requested"
        elif latest_pack.submitted_at:
            dossier_stage = "submitted"
        elif latest_pack.status in ("complete", "assembling", "draft"):
            dossier_stage = "pack_generated"
    elif valid_diags > 0 and blockers_open == 0:
        dossier_stage = "ready"
    elif total_diags > 0:
        dossier_stage = "partially_ready"

    has_diag = total_diags > 0
    has_valid_diag = valid_diags > 0
    has_docs = doc_count > 0
    completeness_score = sum([has_diag, has_valid_diag, has_docs, blockers_open == 0]) / 4 * 100

    return {
        "building_id": str(building_id),
        "building_name": building.address or "---",
        "completeness_pct": round(completeness_score, 1),
        "blockers_open": blockers_open,
        "blockers_total": sum(1 for a in actions if a.priority in ("critical", "high")),
        "blockers_resolved": sum(1 for a in actions if a.status == "done" and a.priority in ("critical", "high")),
        "actions_total": total_actions,
        "actions_completed": done_actions,
        "actions_open": open_count,
        "diagnostics_total": total_diags,
        "diagnostics_valid": valid_diags,
        "diagnostics_expired": expired_diags,
        "documents_count": doc_count,
        "dossier_stage": dossier_stage,
        "dossier_stage_label": _stage_label(dossier_stage),
    }


async def get_weekly_summary(
    db: AsyncSession,
    org_id: UUID,
) -> dict:
    """Weekly summary for the operator ritual:
    - Actions completed this week
    - Actions due next week
    - Readiness changes
    - Dossier status changes
    """
    now = datetime.now(UTC)
    today = now.date()
    week_ago = now - timedelta(days=7)
    next_week = today + timedelta(days=7)

    bld_q = select(Building).where(Building.organization_id == org_id)
    bld_result = await db.execute(bld_q)
    buildings = list(bld_result.scalars().all())
    building_ids = [b.id for b in buildings]
    building_map = {b.id: b for b in buildings}

    if not building_ids:
        return _empty_weekly(org_id, week_ago, now)

    action_q = select(ActionItem).where(ActionItem.building_id.in_(building_ids))
    action_result = await db.execute(action_q)
    actions = list(action_result.scalars().all())

    completed_this_week = [
        a for a in actions if a.status == "done" and a.completed_at and _ensure_utc(a.completed_at) >= week_ago
    ]
    created_this_week = [a for a in actions if a.created_at and _ensure_utc(a.created_at) >= week_ago]
    due_next_week = [
        a for a in actions if a.status in ("open", "in_progress") and a.due_date and a.due_date <= next_week
    ]
    open_total = sum(1 for a in actions if a.status in ("open", "in_progress", "blocked"))

    net = len(completed_this_week) - len(created_this_week)
    trend = "improving" if net > 0 else ("degrading" if net < 0 else "stable")

    pack_q = select(EvidencePack).where(
        and_(
            EvidencePack.building_id.in_(building_ids),
            EvidencePack.pack_type == "authority_pack",
        )
    )
    pack_result = await db.execute(pack_q)
    packs = list(pack_result.scalars().all())
    packs_submitted_this_week = sum(1 for p in packs if p.submitted_at and _ensure_utc(p.submitted_at) >= week_ago)

    def _action_summary(a: ActionItem) -> dict:
        bld = building_map.get(a.building_id)
        return {
            "action_id": str(a.id),
            "title": a.title,
            "priority": a.priority,
            "building_name": bld.address if bld else "---",
            "building_id": str(a.building_id),
        }

    return {
        "org_id": str(org_id),
        "period": {"start": week_ago.isoformat(), "end": now.isoformat()},
        "completed_this_week": {
            "count": len(completed_this_week),
            "items": [_action_summary(a) for a in completed_this_week[:10]],
        },
        "created_this_week": {
            "count": len(created_this_week),
            "items": [_action_summary(a) for a in created_this_week[:10]],
        },
        "due_next_week": {
            "count": len(due_next_week),
            "items": [_action_summary(a) for a in due_next_week[:10]],
        },
        "open_actions_total": open_total,
        "readiness_trend": trend,
        "dossiers": {"packs_submitted_this_week": packs_submitted_this_week},
        "pilot_progress": (f"{len(completed_this_week)} actions completees, {open_total} restantes"),
    }


# ---------------------------------------------------------------------------
# Empty response factories
# ---------------------------------------------------------------------------


def _empty_scorecard(org_id: UUID, start: date_type, end: date_type) -> dict:
    return {
        "org_id": str(org_id),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "buildings": {"total": 0, "assessed": 0, "ready": 0, "submitted": 0, "acknowledged": 0},
        "readiness": {
            "avg_completeness_pct": 0.0,
            "buildings_with_blockers": 0,
            "total_blockers": 0,
            "blockers_resolved": 0,
            "resolution_rate_pct": 0.0,
        },
        "actions": {
            "total_created": 0,
            "total_completed": 0,
            "completion_rate_pct": 0.0,
            "avg_resolution_days": None,
        },
        "dossiers": {
            "packs_generated": 0,
            "packs_submitted": 0,
            "complements_received": 0,
            "acknowledged": 0,
        },
        "time_to_safe_to_start": {"fastest_days": None, "avg_days": None, "buildings_achieved": 0},
        "diagnostics": {"total": 0, "valid": 0, "expired": 0, "missing_coverage": 0},
        "trend": "stable",
        "pilot_health": "on_track",
    }


def _empty_weekly(org_id: UUID, start: datetime, end: datetime) -> dict:
    return {
        "org_id": str(org_id),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "completed_this_week": {"count": 0, "items": []},
        "created_this_week": {"count": 0, "items": []},
        "due_next_week": {"count": 0, "items": []},
        "open_actions_total": 0,
        "readiness_trend": "stable",
        "dossiers": {"packs_submitted_this_week": 0},
        "pilot_progress": "0 actions completees, 0 restantes",
    }
