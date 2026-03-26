"""Flywheel event hooks — Lot D: Execution → Flywheel graph.

Lightweight hooks that fire on domain events to:
1. Refresh building instant card data
2. Create a DomainEvent for audit
3. Update source_metadata_json with latest computed values
4. Propagate learning to similar buildings when applicable

Registered into the domain event projector.
"""

from __future__ import annotations

import logging
import uuid as _uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.domain_event import DomainEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: emit a flywheel domain event
# ---------------------------------------------------------------------------


async def _emit_flywheel_event(
    db: AsyncSession,
    event_type: str,
    building_id: _uuid.UUID,
    payload: dict,
) -> DomainEvent:
    """Create and persist a flywheel domain event."""
    event = DomainEvent(
        id=_uuid.uuid4(),
        event_type=event_type,
        aggregate_type="building",
        aggregate_id=building_id,
        payload=payload,
        occurred_at=datetime.now(UTC),
    )
    db.add(event)
    await db.flush()
    return event


async def _refresh_building_metadata(
    db: AsyncSession,
    building_id: _uuid.UUID,
    computed_values: dict,
) -> None:
    """Update building.source_metadata_json with latest computed values."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return

    meta = building.source_metadata_json or {}
    flywheel_meta = meta.get("flywheel", {})
    flywheel_meta.update(computed_values)
    flywheel_meta["last_refreshed_at"] = datetime.now(UTC).isoformat()
    meta["flywheel"] = flywheel_meta

    await db.execute(update(Building).where(Building.id == building_id).values(source_metadata_json=meta))
    await db.flush()


async def _propagate_to_similar(
    db: AsyncSession,
    building_id: _uuid.UUID,
    signal_type: str,
    signal_data: dict,
) -> int:
    """Propagate learning to similar buildings (same postal_code + similar year).

    Returns count of buildings updated.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return 0

    # Find similar buildings: same postal code, similar construction year
    similar_result = await db.execute(
        select(Building).where(
            Building.postal_code == building.postal_code,
            Building.id != building_id,
        )
    )
    count = 0
    for similar in similar_result.scalars().all():
        # Only propagate to buildings with similar construction year (within 10 years)
        if (
            building.construction_year
            and similar.construction_year
            and abs(building.construction_year - similar.construction_year) <= 10
        ):
            meta = similar.source_metadata_json or {}
            peer_signals = meta.get("peer_signals", [])
            peer_signals.append(
                {
                    "source_building_id": str(building_id),
                    "signal_type": signal_type,
                    "signal_data": signal_data,
                    "propagated_at": datetime.now(UTC).isoformat(),
                }
            )
            # Keep only last 10 peer signals
            meta["peer_signals"] = peer_signals[-10:]
            await db.execute(update(Building).where(Building.id == similar.id).values(source_metadata_json=meta))
            count += 1

    if count > 0:
        await db.flush()
    return count


# ---------------------------------------------------------------------------
# Hook 1: on_diagnostic_received
# ---------------------------------------------------------------------------


async def on_diagnostic_received(
    db: AsyncSession,
    event: DomainEvent,
) -> None:
    """Recalculate risk + refresh triage when a diagnostic publication is received."""
    payload = event.payload or {}
    building_id = payload.get("building_id") or event.aggregate_id
    if not building_id:
        return

    if isinstance(building_id, str):
        building_id = _uuid.UUID(building_id)

    # Refresh passport grade
    passport_grade = "F"
    overall_trust = 0.0
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
        if passport:
            passport_grade = passport.get("passport_grade", "F")
            overall_trust = passport.get("knowledge_state", {}).get("overall_trust", 0.0)
    except Exception:
        logger.debug("Passport refresh failed in flywheel", exc_info=True)

    computed = {
        "passport_grade": passport_grade,
        "overall_trust": overall_trust,
        "trigger": "diagnostic_received",
    }
    await _refresh_building_metadata(db, building_id, computed)

    await _emit_flywheel_event(
        db,
        "flywheel_diagnostic_refreshed",
        building_id,
        {
            "source_event_id": str(event.id),
            "passport_grade": passport_grade,
            "overall_trust": overall_trust,
        },
    )

    logger.info(
        "Flywheel: diagnostic received for building %s — grade=%s, trust=%.2f",
        building_id,
        passport_grade,
        overall_trust,
    )


# ---------------------------------------------------------------------------
# Hook 2: on_remediation_completed
# ---------------------------------------------------------------------------


async def on_remediation_completed(
    db: AsyncSession,
    event: DomainEvent,
) -> None:
    """Update risk + passport + valuation when a remediation is completed."""
    payload = event.payload or {}
    building_id = payload.get("building_id") or event.aggregate_id
    if not building_id:
        return

    if isinstance(building_id, str):
        building_id = _uuid.UUID(building_id)

    # Refresh passport
    passport_grade = "F"
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
        if passport:
            passport_grade = passport.get("passport_grade", "F")
    except Exception:
        logger.debug("Passport refresh failed in flywheel", exc_info=True)

    computed = {
        "passport_grade": passport_grade,
        "trigger": "remediation_completed",
        "completion_id": str(payload.get("completion_id", "")),
    }
    await _refresh_building_metadata(db, building_id, computed)

    await _emit_flywheel_event(
        db,
        "flywheel_remediation_refreshed",
        building_id,
        {
            "source_event_id": str(event.id),
            "passport_grade": passport_grade,
        },
    )

    # Propagate pollutant risk baseline to similar buildings
    pollutant = payload.get("pollutant_type")
    if pollutant:
        propagated = await _propagate_to_similar(
            db,
            building_id,
            "remediation_completed",
            {"pollutant": pollutant, "new_grade": passport_grade},
        )
        logger.info("Flywheel: propagated remediation signal to %d similar buildings", propagated)

    logger.info(
        "Flywheel: remediation completed for building %s — grade=%s",
        building_id,
        passport_grade,
    )


# ---------------------------------------------------------------------------
# Hook 3: on_proof_delivered
# ---------------------------------------------------------------------------


async def on_proof_delivered(
    db: AsyncSession,
    event: DomainEvent,
) -> None:
    """Update exchange history + trust when proof is delivered."""
    payload = event.payload or {}
    building_id = payload.get("building_id") or event.aggregate_id
    if not building_id:
        return

    if isinstance(building_id, str):
        building_id = _uuid.UUID(building_id)

    computed = {
        "trigger": "proof_delivered",
        "delivery_id": str(payload.get("delivery_id", "")),
        "audience": payload.get("audience", "unknown"),
    }
    await _refresh_building_metadata(db, building_id, computed)

    await _emit_flywheel_event(
        db,
        "flywheel_proof_delivered_refreshed",
        building_id,
        {
            "source_event_id": str(event.id),
            "audience": payload.get("audience"),
        },
    )

    logger.info(
        "Flywheel: proof delivered for building %s — audience=%s",
        building_id,
        payload.get("audience"),
    )


# ---------------------------------------------------------------------------
# Hook 4: on_post_works_finalized
# ---------------------------------------------------------------------------


async def on_post_works_finalized(
    db: AsyncSession,
    event: DomainEvent,
) -> None:
    """Update passport + building narrative + peer benchmarks on post-works finalization."""
    payload = event.payload or {}
    building_id = event.aggregate_id
    if not building_id:
        return

    if isinstance(building_id, str):
        building_id = _uuid.UUID(building_id)

    # Refresh passport
    passport_grade = "F"
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
        if passport:
            passport_grade = passport.get("passport_grade", "F")
    except Exception:
        logger.debug("Passport refresh failed in flywheel", exc_info=True)

    computed = {
        "passport_grade": passport_grade,
        "trigger": "post_works_finalized",
        "intervention_id": str(payload.get("intervention_id", "")),
        "verification_rate": payload.get("verification_rate"),
    }
    await _refresh_building_metadata(db, building_id, computed)

    await _emit_flywheel_event(
        db,
        "flywheel_post_works_refreshed",
        building_id,
        {
            "source_event_id": str(event.id),
            "passport_grade": passport_grade,
            "verification_rate": payload.get("verification_rate"),
        },
    )

    # Propagate post-works benchmarks to peer buildings
    propagated = await _propagate_to_similar(
        db,
        building_id,
        "post_works_finalized",
        {
            "verification_rate": payload.get("verification_rate"),
            "grade_after": passport_grade,
        },
    )

    logger.info(
        "Flywheel: post-works finalized for building %s — grade=%s, propagated to %d peers",
        building_id,
        passport_grade,
        propagated,
    )


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------


def register_flywheel_hooks() -> None:
    """Register all flywheel hooks into the domain event projector."""
    from app.services.domain_event_projector import register_handler

    register_handler("diagnostic_publication_received", on_diagnostic_received)
    register_handler("remediation_completion_fully_confirmed", on_remediation_completed)
    register_handler("proof_delivery_acknowledged", on_proof_delivered)
    register_handler("remediation_post_works_finalized", on_post_works_finalized)

    logger.info("Flywheel hooks registered in domain event projector")
