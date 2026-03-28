"""
BatiConnect - Change Tracker Service

Orchestrates the change grammar: recording observations, events, computing deltas,
detecting signals, and querying a unified change timeline.

Integrates with the existing change_signal_generator for backward-compatible
signal detection while adding new grammar-native signal creation.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building_change import (
    BuildingDelta,
    BuildingEvent,
    BuildingObservation,
    BuildingSignal,
)
from app.models.building_snapshot import BuildingSnapshot
from app.schemas.building_change import ChangeTimelineEntry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Record observation
# ---------------------------------------------------------------------------


async def record_observation(
    db: AsyncSession,
    building_id: UUID,
    observer_id: UUID,
    *,
    observation_type: str,
    observer_role: str,
    target_type: str,
    subject: str,
    value: str,
    observed_at: datetime | None = None,
    case_id: UUID | None = None,
    target_id: UUID | None = None,
    unit: str | None = None,
    confidence: float | None = None,
    method: str = "visual",
    source_document_id: UUID | None = None,
    source_extraction_id: UUID | None = None,
    notes: str | None = None,
) -> BuildingObservation:
    """Record a new observation about a building."""
    obs = BuildingObservation(
        building_id=building_id,
        observer_id=observer_id,
        observation_type=observation_type,
        observer_role=observer_role,
        observed_at=observed_at or datetime.now(UTC),
        case_id=case_id,
        target_type=target_type,
        target_id=target_id,
        subject=subject,
        value=value,
        unit=unit,
        confidence=confidence,
        method=method,
        source_document_id=source_document_id,
        source_extraction_id=source_extraction_id,
        notes=notes,
    )
    db.add(obs)
    await db.flush()
    logger.info("Recorded observation %s for building %s: %s", obs.id, building_id, subject)

    # Run consequence chain after truth change
    try:
        from app.services.consequence_engine import ConsequenceEngine

        engine = ConsequenceEngine()
        await engine.run_consequences(
            db, building_id, "observation_recorded", trigger_id=str(obs.id), triggered_by_id=observer_id
        )
    except Exception:
        logger.exception("consequence_engine failed after observation %s", obs.id)

    return obs


# ---------------------------------------------------------------------------
# Record event
# ---------------------------------------------------------------------------


async def record_event(
    db: AsyncSession,
    building_id: UUID,
    event_type: str,
    title: str,
    *,
    actor_id: UUID | None = None,
    occurred_at: datetime | None = None,
    description: str | None = None,
    case_id: UUID | None = None,
    impact_scope: str | None = None,
    impact_target_id: UUID | None = None,
    impact_description: str | None = None,
    severity: str = "info",
    source_type: str | None = None,
    source_id: UUID | None = None,
) -> BuildingEvent:
    """Record a building event."""
    evt = BuildingEvent(
        building_id=building_id,
        event_type=event_type,
        title=title,
        actor_id=actor_id,
        occurred_at=occurred_at or datetime.now(UTC),
        description=description,
        case_id=case_id,
        impact_scope=impact_scope,
        impact_target_id=impact_target_id,
        impact_description=impact_description,
        severity=severity,
        source_type=source_type,
        source_id=source_id,
    )
    db.add(evt)
    await db.flush()
    logger.info("Recorded event %s for building %s: %s", evt.id, building_id, title)
    return evt


# ---------------------------------------------------------------------------
# Compute delta
# ---------------------------------------------------------------------------


async def compute_delta(
    db: AsyncSession,
    building_id: UUID,
    delta_type: str,
    period_start: datetime,
    period_end: datetime,
) -> BuildingDelta:
    """Compute a delta between two points in time.

    Looks for the closest snapshots to period_start and period_end to extract
    before/after values based on delta_type.
    """
    # Find nearest snapshots
    before_snap = await _find_nearest_snapshot(db, building_id, period_start, direction="before")
    after_snap = await _find_nearest_snapshot(db, building_id, period_end, direction="after")

    before_value, after_value = _extract_delta_values(delta_type, before_snap, after_snap)
    direction = _compute_direction(delta_type, before_value, after_value)
    magnitude = _compute_magnitude(delta_type, before_value, after_value)

    delta = BuildingDelta(
        building_id=building_id,
        delta_type=delta_type,
        computed_at=datetime.now(UTC),
        period_start=period_start,
        period_end=period_end,
        before_value=before_value,
        after_value=after_value,
        before_snapshot_id=before_snap.id if before_snap else None,
        after_snapshot_id=after_snap.id if after_snap else None,
        direction=direction,
        magnitude=magnitude,
        explanation=f"{delta_type}: {before_value} -> {after_value}",
    )
    db.add(delta)
    await db.flush()
    logger.info("Computed delta %s for building %s: %s -> %s", delta.id, building_id, before_value, after_value)
    return delta


async def _find_nearest_snapshot(
    db: AsyncSession,
    building_id: UUID,
    target_dt: datetime,
    direction: str = "before",
) -> BuildingSnapshot | None:
    """Find the nearest snapshot to target_dt."""
    if direction == "before":
        result = await db.execute(
            select(BuildingSnapshot)
            .where(
                BuildingSnapshot.building_id == building_id,
                BuildingSnapshot.captured_at <= target_dt,
            )
            .order_by(BuildingSnapshot.captured_at.desc())
            .limit(1)
        )
    else:
        result = await db.execute(
            select(BuildingSnapshot)
            .where(
                BuildingSnapshot.building_id == building_id,
                BuildingSnapshot.captured_at <= target_dt,
            )
            .order_by(BuildingSnapshot.captured_at.desc())
            .limit(1)
        )
    return result.scalar_one_or_none()


def _extract_delta_values(
    delta_type: str,
    before_snap: BuildingSnapshot | None,
    after_snap: BuildingSnapshot | None,
) -> tuple[str, str]:
    """Extract before/after values from snapshots based on delta_type."""
    if delta_type == "grade_change":
        return (
            (before_snap.passport_grade or "N/A") if before_snap else "N/A",
            (after_snap.passport_grade or "N/A") if after_snap else "N/A",
        )
    if delta_type == "trust_change":
        return (
            str(round(before_snap.overall_trust, 4)) if before_snap and before_snap.overall_trust else "0",
            str(round(after_snap.overall_trust, 4)) if after_snap and after_snap.overall_trust else "0",
        )
    if delta_type == "completeness_change":
        return (
            str(round(before_snap.completeness_score, 4)) if before_snap and before_snap.completeness_score else "0",
            str(round(after_snap.completeness_score, 4)) if after_snap and after_snap.completeness_score else "0",
        )
    # Fallback: generic state comparison
    return ("unknown", "unknown")


def _compute_direction(delta_type: str, before_value: str, after_value: str) -> str:
    """Determine if the change is an improvement, degradation, or unchanged."""
    if before_value == after_value:
        return "unchanged"

    # Numeric comparison for score-like deltas
    if delta_type in ("trust_change", "completeness_change"):
        try:
            b = float(before_value)
            a = float(after_value)
            if a > b:
                return "improved"
            if a < b:
                return "degraded"
            return "unchanged"
        except ValueError:
            return "mixed"

    # Grade comparison (A > B > C > D > E > F)
    if delta_type == "grade_change":
        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}
        b_rank = grade_order.get(before_value, 99)
        a_rank = grade_order.get(after_value, 99)
        if a_rank < b_rank:
            return "improved"
        if a_rank > b_rank:
            return "degraded"
        return "unchanged"

    return "mixed"


def _compute_magnitude(delta_type: str, before_value: str, after_value: str) -> str:
    """Determine the magnitude of the change."""
    if before_value == after_value:
        return "minor"

    if delta_type in ("trust_change", "completeness_change"):
        try:
            diff = abs(float(after_value) - float(before_value))
            if diff >= 0.3:
                return "major"
            if diff >= 0.1:
                return "moderate"
            return "minor"
        except ValueError:
            return "minor"

    if delta_type == "grade_change":
        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}
        diff = abs(grade_order.get(after_value, 0) - grade_order.get(before_value, 0))
        if diff >= 3:
            return "major"
        if diff >= 2:
            return "moderate"
        return "minor"

    return "minor"


# ---------------------------------------------------------------------------
# Detect signals (integrates with existing change_signal_generator)
# ---------------------------------------------------------------------------


async def detect_signals(
    db: AsyncSession,
    building_id: UUID,
) -> list[BuildingSignal]:
    """Scan recent observations, events, and deltas to detect signals.

    Also delegates to the existing change_signal_generator for backward
    compatibility with the legacy ChangeSignal model.
    """
    from app.services.change_signal_generator import generate_signals_for_building

    # Run legacy signal detection (populates ChangeSignal table)
    legacy_signals = await generate_signals_for_building(db, building_id)

    # Convert legacy signals into BuildingSignal records for the new grammar
    new_signals: list[BuildingSignal] = []
    for legacy in legacy_signals:
        signal = BuildingSignal(
            building_id=building_id,
            signal_type=legacy.signal_type,
            detected_at=legacy.detected_at or datetime.now(UTC),
            severity=legacy.severity,
            confidence=None,
            title=legacy.title,
            description=legacy.description or "",
            recommended_action=None,
            based_on_type="event",
            based_on_ids=[str(legacy.entity_id)] if legacy.entity_id else [],
            status="active",
        )
        db.add(signal)
        new_signals.append(signal)

    if new_signals:
        await db.flush()

    logger.info(
        "Detected %d signals for building %s (%d from legacy)",
        len(new_signals),
        building_id,
        len(legacy_signals),
    )
    return new_signals


# ---------------------------------------------------------------------------
# Unified change timeline
# ---------------------------------------------------------------------------


async def get_change_timeline(
    db: AsyncSession,
    building_id: UUID,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ChangeTimelineEntry]:
    """Get unified change timeline: observations + events + deltas + signals."""
    entries: list[ChangeTimelineEntry] = []

    # Observations
    obs_query = select(BuildingObservation).where(BuildingObservation.building_id == building_id)
    if since:
        obs_query = obs_query.where(BuildingObservation.observed_at >= since)
    if until:
        obs_query = obs_query.where(BuildingObservation.observed_at <= until)
    result = await db.execute(obs_query)
    for obs in result.scalars().all():
        entries.append(
            ChangeTimelineEntry(
                id=obs.id,
                change_type="observation",
                occurred_at=obs.observed_at,
                title=obs.subject,
                description=f"{obs.observation_type}: {obs.value}" + (f" {obs.unit}" if obs.unit else ""),
                severity=None,
                metadata={"method": obs.method, "target_type": obs.target_type, "confidence": obs.confidence},
            )
        )

    # Events
    evt_query = select(BuildingEvent).where(BuildingEvent.building_id == building_id)
    if since:
        evt_query = evt_query.where(BuildingEvent.occurred_at >= since)
    if until:
        evt_query = evt_query.where(BuildingEvent.occurred_at <= until)
    result = await db.execute(evt_query)
    for evt in result.scalars().all():
        entries.append(
            ChangeTimelineEntry(
                id=evt.id,
                change_type="event",
                occurred_at=evt.occurred_at,
                title=evt.title,
                description=evt.description,
                severity=evt.severity,
                metadata={"event_type": evt.event_type, "impact_scope": evt.impact_scope},
            )
        )

    # Deltas
    delta_query = select(BuildingDelta).where(BuildingDelta.building_id == building_id)
    if since:
        delta_query = delta_query.where(BuildingDelta.computed_at >= since)
    if until:
        delta_query = delta_query.where(BuildingDelta.computed_at <= until)
    result = await db.execute(delta_query)
    for delta in result.scalars().all():
        entries.append(
            ChangeTimelineEntry(
                id=delta.id,
                change_type="delta",
                occurred_at=delta.computed_at,
                title=f"{delta.delta_type}: {delta.before_value} -> {delta.after_value}",
                description=delta.explanation,
                severity=None,
                metadata={
                    "delta_type": delta.delta_type,
                    "direction": delta.direction,
                    "magnitude": delta.magnitude,
                },
            )
        )

    # Signals
    sig_query = select(BuildingSignal).where(BuildingSignal.building_id == building_id)
    if since:
        sig_query = sig_query.where(BuildingSignal.detected_at >= since)
    if until:
        sig_query = sig_query.where(BuildingSignal.detected_at <= until)
    result = await db.execute(sig_query)
    for sig in result.scalars().all():
        entries.append(
            ChangeTimelineEntry(
                id=sig.id,
                change_type="signal",
                occurred_at=sig.detected_at,
                title=sig.title,
                description=sig.description,
                severity=sig.severity,
                metadata={
                    "signal_type": sig.signal_type,
                    "status": sig.status,
                    "confidence": sig.confidence,
                },
            )
        )

    # Sort by occurred_at descending
    entries.sort(key=lambda e: e.occurred_at, reverse=True)

    # Apply pagination
    return entries[offset : offset + limit]


# ---------------------------------------------------------------------------
# Signal lifecycle
# ---------------------------------------------------------------------------


async def acknowledge_signal(
    db: AsyncSession,
    signal_id: UUID,
    acknowledged_by_id: UUID,
) -> BuildingSignal:
    """Acknowledge a signal without resolving it."""
    result = await db.execute(select(BuildingSignal).where(BuildingSignal.id == signal_id))
    signal = result.scalar_one()
    signal.status = "acknowledged"
    await db.flush()
    logger.info("Signal %s acknowledged by %s", signal_id, acknowledged_by_id)
    return signal


async def resolve_signal(
    db: AsyncSession,
    signal_id: UUID,
    resolved_by_id: UUID,
    resolution_note: str | None = None,
) -> BuildingSignal:
    """Resolve a signal."""
    result = await db.execute(select(BuildingSignal).where(BuildingSignal.id == signal_id))
    signal = result.scalar_one()
    signal.status = "resolved"
    signal.resolved_at = datetime.now(UTC)
    signal.resolved_by_id = resolved_by_id
    signal.resolution_note = resolution_note
    await db.flush()
    logger.info("Signal %s resolved by %s", signal_id, resolved_by_id)
    return signal


async def get_active_signals(
    db: AsyncSession,
    building_id: UUID,
) -> list[BuildingSignal]:
    """Get active signals for a building."""
    result = await db.execute(
        select(BuildingSignal).where(
            BuildingSignal.building_id == building_id,
            BuildingSignal.status.in_(["active", "acknowledged"]),
        )
    )
    return list(result.scalars().all())


async def get_portfolio_signals(
    db: AsyncSession,
    severity: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[BuildingSignal]:
    """Get recent signals across all buildings (portfolio-level)."""
    query = select(BuildingSignal).order_by(BuildingSignal.detected_at.desc())
    if severity:
        query = query.where(BuildingSignal.severity == severity)
    if status:
        query = query.where(BuildingSignal.status == status)
    query = query.limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
