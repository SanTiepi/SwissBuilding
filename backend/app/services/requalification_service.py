"""
SwissBuildingOS - Requalification Replay Timeline Service

Aggregates change signals, snapshots, and interventions into a chronological
state-change timeline that shows exactly why a building's state changed over time.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building_change import BuildingSignal
from app.models.building_snapshot import BuildingSnapshot
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.schemas.requalification import (
    RequalificationEntry,
    RequalificationRecommendation,
    RequalificationTimeline,
    RequalificationTrigger,
    RequalificationTriggerReport,
    TriggerType,
    TriggerUrgency,
)

logger = logging.getLogger(__name__)


async def get_requalification_timeline(
    db: AsyncSession,
    building_id: UUID,
    limit: int = 50,
) -> RequalificationTimeline:
    """Build a chronological requalification timeline for a building.

    Merges change signals, snapshots, and completed interventions into a single
    ordered stream, detects grade transitions between consecutive snapshots,
    and extracts a compact grade history.
    """
    # ── 1. Fetch change signals ───────────────────────────────────
    sig_result = await db.execute(
        select(BuildingSignal)
        .where(BuildingSignal.building_id == building_id)
        .order_by(BuildingSignal.detected_at.desc())
    )
    signals = list(sig_result.scalars().all())

    # ── 2. Fetch snapshots ────────────────────────────────────────
    snap_result = await db.execute(
        select(BuildingSnapshot)
        .where(BuildingSnapshot.building_id == building_id)
        .order_by(BuildingSnapshot.captured_at.desc())
    )
    snapshots = list(snap_result.scalars().all())

    # ── 3. Fetch completed interventions ──────────────────────────
    interv_result = await db.execute(
        select(Intervention).where(
            and_(
                Intervention.building_id == building_id,
                Intervention.status == "completed",
            )
        )
    )
    interventions = list(interv_result.scalars().all())

    # ── 4. Build entries ──────────────────────────────────────────
    entries: list[RequalificationEntry] = []

    for sig in signals:
        entries.append(
            RequalificationEntry(
                timestamp=sig.detected_at,
                entry_type="signal",
                title=sig.title,
                description=sig.description,
                severity=sig.severity,
                signal_type=sig.signal_type,
                metadata={
                    "confidence": sig.confidence,
                    "based_on_type": sig.based_on_type,
                    "status": sig.status,
                },
            )
        )

    for snap in snapshots:
        entries.append(
            RequalificationEntry(
                timestamp=snap.captured_at,
                entry_type="snapshot",
                title=f"Snapshot ({snap.snapshot_type})",
                description=snap.notes or snap.trigger_event,
                metadata={
                    "passport_grade": snap.passport_grade,
                    "overall_trust": snap.overall_trust,
                    "completeness_score": snap.completeness_score,
                },
            )
        )

    for interv in interventions:
        ts = interv.updated_at or interv.created_at
        if ts is not None:
            entries.append(
                RequalificationEntry(
                    timestamp=ts,
                    entry_type="intervention",
                    title=f"Intervention terminée: {interv.title}",
                    description=interv.description,
                    metadata={
                        "intervention_type": interv.intervention_type,
                        "contractor_name": interv.contractor_name,
                    },
                )
            )

    # ── 5. Detect grade transitions from snapshots ────────────────
    # Snapshots are newest-first; iterate oldest-first for transitions.
    sorted_snaps = sorted(
        [s for s in snapshots if s.passport_grade is not None],
        key=lambda s: s.captured_at,
    )
    for i in range(1, len(sorted_snaps)):
        prev = sorted_snaps[i - 1]
        curr = sorted_snaps[i]
        if prev.passport_grade != curr.passport_grade:
            entries.append(
                RequalificationEntry(
                    timestamp=curr.captured_at,
                    entry_type="grade_change",
                    title=f"Grade {prev.passport_grade} → {curr.passport_grade}",
                    description=curr.trigger_event,
                    grade_before=prev.passport_grade,
                    grade_after=curr.passport_grade,
                )
            )

    # ── 6. Sort chronologically (newest first) & limit ────────────
    # Normalize timestamps to aware (UTC) for consistent sorting
    # (SQLite may return naive datetimes from func.now())
    def _aware_ts(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt

    entries.sort(key=lambda e: _aware_ts(e.timestamp), reverse=True)
    entries = entries[:limit]

    # ── 7. Grade history ──────────────────────────────────────────
    grade_history: list[dict] = []
    for snap in sorted_snaps:
        grade_history.append(
            {
                "grade": snap.passport_grade,
                "date": snap.captured_at.isoformat() if snap.captured_at else None,
                "trigger": snap.trigger_event,
            }
        )

    # Current grade = most recent snapshot with a grade
    current_grade = sorted_snaps[-1].passport_grade if sorted_snaps else None

    return RequalificationTimeline(
        building_id=building_id,
        entries=entries,
        current_grade=current_grade,
        grade_history=grade_history,
    )


async def get_state_change_summary(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Return a compact summary of state-change activity for a building."""
    sig_result = await db.execute(
        select(BuildingSignal)
        .where(BuildingSignal.building_id == building_id)
        .order_by(BuildingSignal.detected_at.desc())
    )
    signals = list(sig_result.scalars().all())

    snap_result = await db.execute(
        select(BuildingSnapshot)
        .where(BuildingSnapshot.building_id == building_id)
        .order_by(BuildingSnapshot.captured_at.desc())
    )
    snapshots = list(snap_result.scalars().all())

    # Count grade changes
    sorted_snaps = sorted(
        [s for s in snapshots if s.passport_grade is not None],
        key=lambda s: s.captured_at,
    )
    grade_changes_count = 0
    for i in range(1, len(sorted_snaps)):
        if sorted_snaps[i - 1].passport_grade != sorted_snaps[i].passport_grade:
            grade_changes_count += 1

    current_grade = sorted_snaps[-1].passport_grade if sorted_snaps else None

    return {
        "total_signals": len(signals),
        "total_snapshots": len(snapshots),
        "grade_changes_count": grade_changes_count,
        "last_signal_date": (signals[0].detected_at.isoformat() if signals else None),
        "last_snapshot_date": (snapshots[0].captured_at.isoformat() if snapshots else None),
        "current_grade": current_grade,
    }


# Grade ordering: A is best, E is worst
_GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}

# Stale diagnostic threshold in years
_STALE_DIAGNOSTIC_YEARS = 5

# High-severity signal accumulation threshold
_HIGH_SEVERITY_SIGNAL_THRESHOLD = 3

# Trust score threshold
_TRUST_SCORE_THRESHOLD = 0.5


async def detect_requalification_triggers(
    db: AsyncSession,
    building_id: UUID,
) -> RequalificationTriggerReport:
    """Analyze a building's state and identify conditions that should trigger requalification."""
    now = datetime.now(UTC)
    triggers: list[RequalificationTrigger] = []

    # ── Fetch data ─────────────────────────────────────────────────
    snap_result = await db.execute(
        select(BuildingSnapshot)
        .where(BuildingSnapshot.building_id == building_id)
        .order_by(BuildingSnapshot.captured_at.asc())
    )
    snapshots = list(snap_result.scalars().all())

    sig_result = await db.execute(
        select(BuildingSignal)
        .where(BuildingSignal.building_id == building_id)
        .order_by(BuildingSignal.detected_at.desc())
    )
    signals = list(sig_result.scalars().all())

    interv_result = await db.execute(
        select(Intervention).where(
            and_(
                Intervention.building_id == building_id,
                Intervention.status == "completed",
            )
        )
    )
    interventions = list(interv_result.scalars().all())

    diag_result = await db.execute(
        select(Diagnostic).where(
            and_(
                Diagnostic.building_id == building_id,
                Diagnostic.status == "completed",
            )
        )
    )
    diagnostics = list(diag_result.scalars().all())

    # ── 1. Grade degradation ───────────────────────────────────────
    graded_snaps = [s for s in snapshots if s.passport_grade is not None]
    if len(graded_snaps) >= 2:
        prev = graded_snaps[-2]
        curr = graded_snaps[-1]
        prev_order = _GRADE_ORDER.get(prev.passport_grade, -1)
        curr_order = _GRADE_ORDER.get(curr.passport_grade, -1)
        if curr_order > prev_order:
            triggers.append(
                RequalificationTrigger(
                    trigger_type=TriggerType.grade_degradation,
                    severity=TriggerUrgency.high,
                    title=f"Grade dégradé: {prev.passport_grade} → {curr.passport_grade}",
                    description=(
                        f"Le grade du bâtiment est passé de {prev.passport_grade} "
                        f"à {curr.passport_grade}. Une requalification est recommandée."
                    ),
                    detected_at=curr.captured_at if curr.captured_at else now,
                    metadata={
                        "grade_before": prev.passport_grade,
                        "grade_after": curr.passport_grade,
                    },
                )
            )

    # ── 2. Stale diagnostic ────────────────────────────────────────
    if diagnostics:
        sorted_diags = sorted(
            diagnostics,
            key=lambda d: d.date_report or d.created_at or now,
        )
        latest_diag = sorted_diags[-1]
        latest_date = latest_diag.date_report or (latest_diag.created_at.date() if latest_diag.created_at else None)
        if latest_date is not None:
            from datetime import date as date_type

            if isinstance(latest_date, datetime):
                latest_date = latest_date.date()
            age_days = (date_type.today() - latest_date).days
            if age_days > _STALE_DIAGNOSTIC_YEARS * 365:
                triggers.append(
                    RequalificationTrigger(
                        trigger_type=TriggerType.stale_diagnostic,
                        severity=TriggerUrgency.medium,
                        title="Diagnostic obsolète",
                        description=(
                            f"Le dernier diagnostic complété date de plus de "
                            f"{_STALE_DIAGNOSTIC_YEARS} ans ({age_days} jours). "
                            f"Une requalification est nécessaire."
                        ),
                        detected_at=now,
                        metadata={"age_days": age_days, "diagnostic_id": str(latest_diag.id)},
                    )
                )

    # ── 3. High-severity signal accumulation ───────────────────────
    last_snapshot_at = snapshots[-1].captured_at if snapshots else None
    high_sev_signals = []
    for sig in signals:
        if sig.severity in ("high", "critical") and (last_snapshot_at is None or sig.detected_at > last_snapshot_at):
            high_sev_signals.append(sig)

    if len(high_sev_signals) >= _HIGH_SEVERITY_SIGNAL_THRESHOLD:
        triggers.append(
            RequalificationTrigger(
                trigger_type=TriggerType.high_severity_accumulation,
                severity=TriggerUrgency.high,
                title="Accumulation de signaux critiques",
                description=(
                    f"{len(high_sev_signals)} signaux de sévérité haute/critique "
                    f"détectés depuis le dernier snapshot. Requalification recommandée."
                ),
                detected_at=high_sev_signals[0].detected_at if high_sev_signals else now,
                metadata={"signal_count": len(high_sev_signals)},
            )
        )

    # ── 4. Post-intervention requalification ───────────────────────
    for interv in interventions:
        interv_ts = interv.updated_at or interv.created_at
        if interv_ts is None:
            continue
        has_subsequent_snapshot = any(s.captured_at is not None and s.captured_at > interv_ts for s in snapshots)
        if not has_subsequent_snapshot:
            triggers.append(
                RequalificationTrigger(
                    trigger_type=TriggerType.post_intervention,
                    severity=TriggerUrgency.medium,
                    title=f"Snapshot post-intervention manquant: {interv.title}",
                    description=(
                        f"L'intervention «{interv.title}» est terminée mais aucun "
                        f"snapshot n'a été pris après. Un snapshot post-travaux est recommandé."
                    ),
                    detected_at=interv_ts,
                    metadata={
                        "intervention_id": str(interv.id),
                        "intervention_type": interv.intervention_type,
                    },
                )
            )

    # ── 5. Trust score drop ────────────────────────────────────────
    trust_snaps = [s for s in snapshots if s.overall_trust is not None]
    if trust_snaps:
        latest_trust = trust_snaps[-1]
        if latest_trust.overall_trust < _TRUST_SCORE_THRESHOLD:
            triggers.append(
                RequalificationTrigger(
                    trigger_type=TriggerType.trust_score_drop,
                    severity=TriggerUrgency.critical,
                    title="Score de confiance bas",
                    description=(
                        f"Le score de confiance du bâtiment est de "
                        f"{latest_trust.overall_trust:.2f}, en dessous du seuil de "
                        f"{_TRUST_SCORE_THRESHOLD}. Requalification recommandée."
                    ),
                    detected_at=latest_trust.captured_at if latest_trust.captured_at else now,
                    metadata={"trust_score": latest_trust.overall_trust},
                )
            )

    # ── Compute overall urgency ────────────────────────────────────
    urgency = TriggerUrgency.low
    if triggers:
        urgency_order = {
            TriggerUrgency.low: 0,
            TriggerUrgency.medium: 1,
            TriggerUrgency.high: 2,
            TriggerUrgency.critical: 3,
        }
        urgency = max(triggers, key=lambda t: urgency_order[t.severity]).severity

    # ── Build recommendations ──────────────────────────────────────
    recommendations = _build_recommendations(triggers)

    return RequalificationTriggerReport(
        building_id=building_id,
        triggers=triggers,
        needs_requalification=len(triggers) > 0,
        urgency=urgency,
        recommendations=recommendations,
    )


def _build_recommendations(triggers: list[RequalificationTrigger]) -> list[RequalificationRecommendation]:
    """Generate actionable recommendations from detected triggers."""
    recs: list[RequalificationRecommendation] = []
    seen_types: set[TriggerType] = set()

    for trigger in triggers:
        if trigger.trigger_type in seen_types:
            continue
        seen_types.add(trigger.trigger_type)

        if trigger.trigger_type == TriggerType.grade_degradation:
            recs.append(
                RequalificationRecommendation(
                    priority=1,
                    action="Planifier un diagnostic complet pour identifier les causes de la dégradation du grade.",
                    reason=trigger.description,
                    trigger_type=trigger.trigger_type,
                )
            )
        elif trigger.trigger_type == TriggerType.stale_diagnostic:
            recs.append(
                RequalificationRecommendation(
                    priority=2,
                    action="Commander un nouveau diagnostic pour mettre à jour l'état du bâtiment.",
                    reason=trigger.description,
                    trigger_type=trigger.trigger_type,
                )
            )
        elif trigger.trigger_type == TriggerType.high_severity_accumulation:
            recs.append(
                RequalificationRecommendation(
                    priority=1,
                    action="Analyser les signaux critiques et prendre un nouveau snapshot après résolution.",
                    reason=trigger.description,
                    trigger_type=trigger.trigger_type,
                )
            )
        elif trigger.trigger_type == TriggerType.post_intervention:
            recs.append(
                RequalificationRecommendation(
                    priority=3,
                    action="Prendre un snapshot post-travaux pour documenter l'état après intervention.",
                    reason=trigger.description,
                    trigger_type=trigger.trigger_type,
                )
            )
        elif trigger.trigger_type == TriggerType.trust_score_drop:
            recs.append(
                RequalificationRecommendation(
                    priority=1,
                    action="Requalifier le bâtiment en urgence — le score de confiance est insuffisant.",
                    reason=trigger.description,
                    trigger_type=trigger.trigger_type,
                )
            )

    recs.sort(key=lambda r: r.priority)
    return recs


async def get_requalification_recommendations(
    db: AsyncSession,
    building_id: UUID,
) -> list[RequalificationRecommendation]:
    """Return actionable recommendations based on detected triggers."""
    report = await detect_requalification_triggers(db, building_id)
    return report.recommendations
