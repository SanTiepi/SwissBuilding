"""
Prework Trigger Service — persistent lifecycle for pre-work diagnostic requirements.

Core contract:
  1. sync_triggers(building_id, assessment) — idempotent sync from readiness evaluation
     - creates new triggers for newly-failing checks
     - auto-resolves triggers whose checks now pass
     - updates reason/urgency if the source changed
  2. escalate_triggers(building_id) — deterministic escalation based on age x urgency
  3. CRUD: list, acknowledge, resolve/dismiss
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prework_trigger import PreworkTrigger
from app.schemas.readiness import _derive_prework_triggers

# ---------------------------------------------------------------------------
# Escalation rules (deterministic)
# ---------------------------------------------------------------------------

# After N days at a given urgency, bump escalation_level
_ESCALATION_THRESHOLDS = {
    "high": [
        (7, 0.5),  # 7 days → escalation 0.5
        (14, 1.0),  # 14 days → 1.0
        (30, 2.0),  # 30 days → 2.0 (critical)
    ],
    "medium": [
        (14, 0.3),
        (30, 0.7),
        (60, 1.5),
    ],
    "low": [
        (30, 0.2),
        (60, 0.5),
        (90, 1.0),
    ],
}

# Legal basis mapping for triggers (enrichment)
_TRIGGER_LEGAL_BASIS: dict[str, str] = {
    "amiante_check": "OTConst Art. 60a / CFST 6503",
    "pcb_check": "ORRChim Annexe 2.15",
    "lead_check": "ORRChim Annexe 2.18",
    "hap_check": "OLED / directive cantonale HAP",
    "radon_check": "ORaP Art. 110",
}


# ---------------------------------------------------------------------------
# Sync: readiness evaluation → persistent triggers (idempotent)
# ---------------------------------------------------------------------------


async def sync_triggers(
    db: AsyncSession,
    building_id: UUID,
    assessment_id: UUID | None,
    checks_json: list[dict[str, Any]] | None,
) -> dict[str, list[PreworkTrigger]]:
    """
    Sync persistent triggers from a readiness evaluation.

    Returns dict with keys: created, updated, resolved.
    """
    # 1. Derive ephemeral triggers from checks
    derived = _derive_prework_triggers(checks_json)
    derived_by_type = {t["trigger_type"]: t for t in derived}

    # 2. Load existing active triggers for this building
    result = await db.execute(
        select(PreworkTrigger).where(
            PreworkTrigger.building_id == building_id,
            PreworkTrigger.status.in_(("pending", "acknowledged")),
        )
    )
    existing = {t.trigger_type: t for t in result.scalars().all()}

    created: list[PreworkTrigger] = []
    updated: list[PreworkTrigger] = []
    resolved: list[PreworkTrigger] = []

    # 3. Create new / update existing triggers
    for ttype, derived_t in derived_by_type.items():
        if ttype in existing:
            # Update if reason or urgency changed
            trigger = existing[ttype]
            changed = False
            if trigger.reason != derived_t["reason"]:
                trigger.reason = derived_t["reason"]
                changed = True
            if trigger.urgency != derived_t["urgency"]:
                trigger.urgency = derived_t["urgency"]
                changed = True
            if trigger.source_check != derived_t["source_check"]:
                trigger.source_check = derived_t["source_check"]
                changed = True
            if assessment_id and trigger.assessment_id != assessment_id:
                trigger.assessment_id = assessment_id
                changed = True
            if changed:
                updated.append(trigger)
        else:
            # New trigger
            trigger = PreworkTrigger(
                building_id=building_id,
                trigger_type=ttype,
                reason=derived_t["reason"],
                source_check=derived_t["source_check"],
                urgency=derived_t["urgency"],
                legal_basis=_TRIGGER_LEGAL_BASIS.get(ttype),
                status="pending",
                assessment_id=assessment_id,
            )
            db.add(trigger)
            created.append(trigger)

    # 4. Auto-resolve triggers that are no longer derived (check passed)
    for ttype, trigger in existing.items():
        if ttype not in derived_by_type:
            trigger.status = "resolved"
            trigger.resolved_at = datetime.now(UTC)
            trigger.resolved_reason = "Source check now passes"
            resolved.append(trigger)

    await db.flush()
    return {"created": created, "updated": updated, "resolved": resolved}


# ---------------------------------------------------------------------------
# Escalation: deterministic priority bump based on age x urgency
# ---------------------------------------------------------------------------


async def escalate_triggers(
    db: AsyncSession,
    building_id: UUID | None = None,
) -> list[PreworkTrigger]:
    """
    Compute and update escalation_level for all active triggers.

    If building_id is provided, only escalate that building's triggers.
    Otherwise, escalate all active triggers (for scheduled jobs).

    Returns list of triggers whose escalation_level changed.
    """
    query = select(PreworkTrigger).where(
        PreworkTrigger.status.in_(("pending", "acknowledged")),
    )
    if building_id:
        query = query.where(PreworkTrigger.building_id == building_id)

    result = await db.execute(query)
    triggers = list(result.scalars().all())

    now = datetime.now(UTC)
    escalated: list[PreworkTrigger] = []

    for trigger in triggers:
        created = trigger.created_at
        if created and created.tzinfo is None:
            # Assume UTC if naive
            created = created.replace(tzinfo=UTC)
        if not created:
            continue

        age_days = (now - created).days
        thresholds = _ESCALATION_THRESHOLDS.get(trigger.urgency, _ESCALATION_THRESHOLDS["medium"])

        new_level = 0.0
        for days, level in thresholds:
            if age_days >= days:
                new_level = level

        if new_level != trigger.escalation_level:
            trigger.escalation_level = new_level
            escalated.append(trigger)

    if escalated:
        await db.flush()

    return escalated


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def list_triggers(
    db: AsyncSession,
    building_id: UUID,
    *,
    status: str | None = None,
    include_resolved: bool = False,
) -> list[PreworkTrigger]:
    """List triggers for a building."""
    query = select(PreworkTrigger).where(PreworkTrigger.building_id == building_id)

    if status:
        query = query.where(PreworkTrigger.status == status)
    elif not include_resolved:
        query = query.where(PreworkTrigger.status.in_(("pending", "acknowledged")))

    query = query.order_by(PreworkTrigger.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def acknowledge_trigger(
    db: AsyncSession,
    trigger_id: UUID,
    user_id: UUID,
) -> PreworkTrigger | None:
    """Mark a trigger as acknowledged (user has seen it)."""
    result = await db.execute(
        select(PreworkTrigger).where(
            PreworkTrigger.id == trigger_id,
            PreworkTrigger.status == "pending",
        )
    )
    trigger = result.scalar_one_or_none()
    if not trigger:
        return None

    trigger.status = "acknowledged"
    trigger.acknowledged_by = user_id
    trigger.acknowledged_at = datetime.now(UTC)
    await db.flush()
    return trigger


async def resolve_trigger(
    db: AsyncSession,
    trigger_id: UUID,
    *,
    status: str = "resolved",
    reason: str | None = None,
) -> PreworkTrigger | None:
    """Resolve or dismiss a trigger."""
    if status not in ("resolved", "dismissed"):
        raise ValueError(f"Invalid resolution status: {status}")

    result = await db.execute(
        select(PreworkTrigger).where(
            PreworkTrigger.id == trigger_id,
            PreworkTrigger.status.in_(("pending", "acknowledged")),
        )
    )
    trigger = result.scalar_one_or_none()
    if not trigger:
        return None

    trigger.status = status
    trigger.resolved_at = datetime.now(UTC)
    trigger.resolved_reason = reason
    await db.flush()
    return trigger


async def get_portfolio_trigger_summary(
    db: AsyncSession,
    building_ids: list[UUID],
) -> dict[str, Any]:
    """
    Aggregate prework trigger summary across multiple buildings.

    Returns:
        {
            "total_active": N,
            "by_type": {"amiante_check": N, ...},
            "by_urgency": {"high": N, ...},
            "critical_escalations": N,  # escalation_level >= 2.0
            "buildings_affected": N,
        }
    """
    if not building_ids:
        return {
            "total_active": 0,
            "by_type": {},
            "by_urgency": {},
            "critical_escalations": 0,
            "buildings_affected": 0,
        }

    result = await db.execute(
        select(PreworkTrigger).where(
            PreworkTrigger.building_id.in_(building_ids),
            PreworkTrigger.status.in_(("pending", "acknowledged")),
        )
    )
    triggers = list(result.scalars().all())

    by_type: dict[str, int] = {}
    by_urgency: dict[str, int] = {}
    buildings: set[str] = set()
    critical = 0

    for t in triggers:
        by_type[t.trigger_type] = by_type.get(t.trigger_type, 0) + 1
        by_urgency[t.urgency] = by_urgency.get(t.urgency, 0) + 1
        buildings.add(str(t.building_id))
        if t.escalation_level >= 2.0:
            critical += 1

    return {
        "total_active": len(triggers),
        "by_type": by_type,
        "by_urgency": by_urgency,
        "critical_escalations": critical,
        "buildings_affected": len(buildings),
    }
