"""BatiConnect -- Freshness Watch Service.

Update intelligence layer: records, assesses, and executes reactions
to external changes (legal, procedural, portal, form, dataset,
local-override, provider).

Integrates with invalidation_engine for pack/safe_to_x invalidation.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.freshness_watch import FreshnessWatchEntry

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Record
# ------------------------------------------------------------------


async def record_change(
    db: AsyncSession,
    *,
    delta_type: str,
    title: str,
    description: str | None = None,
    canton: str | None = None,
    jurisdiction_id: UUID | None = None,
    affected_work_families: list[str] | None = None,
    affected_procedure_types: list[str] | None = None,
    severity: str = "info",
    reactions: list[dict] | None = None,
    source_registry_id: UUID | None = None,
    source_url: str | None = None,
    effective_date=None,
) -> FreshnessWatchEntry:
    """Record an external change that may affect system truth."""
    entry = FreshnessWatchEntry(
        delta_type=delta_type,
        title=title,
        description=description,
        canton=canton,
        jurisdiction_id=jurisdiction_id,
        affected_work_families=affected_work_families,
        affected_procedure_types=affected_procedure_types,
        severity=severity,
        reactions=reactions,
        source_registry_id=source_registry_id,
        source_url=source_url,
        effective_date=effective_date,
        status="detected",
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    logger.info(
        "freshness_watch: recorded change '%s' (delta_type=%s, severity=%s)",
        title,
        delta_type,
        severity,
    )
    return entry


# ------------------------------------------------------------------
# Impact Assessment
# ------------------------------------------------------------------


async def assess_impact(
    db: AsyncSession,
    entry_id: UUID,
) -> dict:
    """Assess the impact of a change: how many buildings, which procedures,
    which packs are affected.

    Uses source_registry + building canton + work_families to compute impact.
    """
    result = await db.execute(select(FreshnessWatchEntry).where(FreshnessWatchEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        return {"error": "Entry not found"}

    affected_buildings = 0
    affected_procedures: list[str] = []
    affected_packs: list[str] = []

    # 1. Estimate affected buildings by canton
    if entry.canton:
        try:
            from app.models.building import Building

            count_q = select(func.count(Building.id)).where(Building.canton == entry.canton)
            count_result = await db.execute(count_q)
            affected_buildings = count_result.scalar() or 0
        except Exception:
            logger.exception("freshness_watch: building count failed for canton %s", entry.canton)
    else:
        # If no canton scope, count all buildings
        try:
            from app.models.building import Building

            count_q = select(func.count(Building.id))
            count_result = await db.execute(count_q)
            affected_buildings = count_result.scalar() or 0
        except Exception:
            logger.exception("freshness_watch: building count failed (all buildings)")

    # 2. Identify affected procedure templates
    if entry.affected_procedure_types:
        try:
            from app.models.procedure import ProcedureTemplate

            proc_q = select(ProcedureTemplate.procedure_type).where(
                ProcedureTemplate.procedure_type.in_(entry.affected_procedure_types)
            )
            proc_result = await db.execute(proc_q)
            affected_procedures = [str(r) for r in proc_result.scalars().all()]
        except Exception:
            logger.exception("freshness_watch: procedure template lookup failed")

    # 3. Identify packs that may be invalidated (published packs in affected canton)
    if entry.canton:
        try:
            from app.models.building import Building
            from app.models.evidence_pack import EvidencePack

            pack_q = (
                select(EvidencePack.id)
                .join(Building, Building.id == EvidencePack.building_id)
                .where(
                    Building.canton == entry.canton,
                    EvidencePack.status.in_(["complete", "submitted"]),
                )
            )
            pack_result = await db.execute(pack_q)
            affected_packs = [str(pid) for pid in pack_result.scalars().all()]
        except Exception:
            logger.exception("freshness_watch: pack lookup failed for canton %s", entry.canton)

    # Update the entry with the estimate
    entry.affected_buildings_estimate = affected_buildings
    if entry.status == "detected":
        entry.status = "under_review"
    await db.flush()

    reactions_summary = []
    for r in entry.reactions or []:
        reactions_summary.append(
            {
                "type": r.get("type", "unknown"),
                "target": r.get("target"),
                "scope": r.get("scope"),
                "estimated_impact": affected_buildings,
            }
        )

    return {
        "entry_id": str(entry.id),
        "affected_buildings_estimate": affected_buildings,
        "affected_procedures": affected_procedures,
        "affected_packs": affected_packs,
        "reactions_summary": reactions_summary,
    }


# ------------------------------------------------------------------
# Apply Reactions
# ------------------------------------------------------------------


async def apply_reactions(
    db: AsyncSession,
    entry_id: UUID,
    applied_by_id: UUID,
) -> dict:
    """Execute the required reactions for a change.

    Supported reaction types:
    - template_invalidation: mark affected procedure/form templates for review
    - safe_to_x_refresh: trigger re-evaluation on affected buildings
    - pack_invalidation: create invalidation events for affected packs
    - blocker_refresh: update procedure blockers
    - notification: notify affected users
    """
    result = await db.execute(select(FreshnessWatchEntry).where(FreshnessWatchEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        return {"error": "Entry not found", "reactions_executed": 0}

    reactions = entry.reactions or []
    executed: list[dict] = []

    for reaction in reactions:
        r_type = reaction.get("type", "unknown")
        r_result: dict = {"type": r_type, "success": False, "detail": ""}

        try:
            if r_type == "template_invalidation":
                r_result = await _react_template_invalidation(db, entry, reaction)

            elif r_type == "safe_to_x_refresh":
                r_result = await _react_safe_to_x_refresh(db, entry, reaction)

            elif r_type == "pack_invalidation":
                r_result = await _react_pack_invalidation(db, entry, reaction)

            elif r_type == "blocker_refresh":
                r_result = await _react_blocker_refresh(db, entry, reaction)

            elif r_type == "notification":
                r_result = await _react_notification(db, entry, reaction)

            else:
                r_result = {"type": r_type, "success": False, "detail": "Type de reaction inconnu"}

        except Exception:
            logger.exception("freshness_watch: reaction '%s' failed for entry %s", r_type, entry_id)
            r_result = {"type": r_type, "success": False, "detail": "Erreur lors de l'execution"}

        executed.append(r_result)

    # Mark entry as applied
    now = datetime.now(UTC)
    entry.status = "applied"
    entry.applied_at = now
    entry.reviewed_by_id = applied_by_id
    entry.reviewed_at = now
    await db.flush()

    success_count = sum(1 for e in executed if e.get("success"))
    logger.info(
        "freshness_watch: applied %d/%d reactions for entry %s",
        success_count,
        len(executed),
        entry_id,
    )

    return {
        "entry_id": str(entry_id),
        "reactions_executed": len(executed),
        "reactions_succeeded": success_count,
        "details": executed,
    }


# ------------------------------------------------------------------
# Reaction handlers
# ------------------------------------------------------------------


async def _react_template_invalidation(
    db: AsyncSession,
    entry: FreshnessWatchEntry,
    reaction: dict,
) -> dict:
    """Mark affected procedure/form templates for review."""
    target = reaction.get("target")
    invalidated = 0

    try:
        from app.models.procedure import ProcedureTemplate

        query = select(ProcedureTemplate).where(ProcedureTemplate.status == "active")
        if target:
            query = query.where(ProcedureTemplate.procedure_type == target)
        if entry.canton:
            query = query.where(ProcedureTemplate.canton == entry.canton)

        result = await db.execute(query)
        templates = list(result.scalars().all())

        for tmpl in templates:
            tmpl.status = "needs_review"
            invalidated += 1
    except Exception:
        logger.exception("freshness_watch: template_invalidation lookup failed")

    return {
        "type": "template_invalidation",
        "success": True,
        "detail": f"{invalidated} template(s) marque(s) pour revue",
        "count": invalidated,
    }


async def _react_safe_to_x_refresh(
    db: AsyncSession,
    entry: FreshnessWatchEntry,
    reaction: dict,
) -> dict:
    """Trigger re-evaluation of SafeToX states via invalidation engine."""
    scope = reaction.get("scope", "")
    refreshed = 0

    try:
        from app.models.building import Building
        from app.services.invalidation_engine import InvalidationEngine

        inv_engine = InvalidationEngine()

        # Find affected buildings
        bld_q = select(Building.id)
        if entry.canton:
            bld_q = bld_q.where(Building.canton == entry.canton)

        bld_result = await db.execute(bld_q)
        building_ids = [bid for bid in bld_result.scalars().all()]

        for bid in building_ids:
            invalidations = await inv_engine.scan_for_invalidations(db, bid, trigger_type="rule_change")
            refreshed += len(invalidations)

    except Exception:
        logger.exception("freshness_watch: safe_to_x_refresh failed (scope=%s)", scope)

    return {
        "type": "safe_to_x_refresh",
        "success": True,
        "detail": f"{refreshed} invalidation(s) detectee(s) sur les etats SafeToX",
        "count": refreshed,
    }


async def _react_pack_invalidation(
    db: AsyncSession,
    entry: FreshnessWatchEntry,
    reaction: dict,
) -> dict:
    """Create invalidation events for affected packs."""
    scope = reaction.get("scope", "")
    invalidated = 0

    try:
        from app.models.building import Building
        from app.models.evidence_pack import EvidencePack
        from app.services.invalidation_engine import InvalidationEngine

        inv_engine = InvalidationEngine()

        pack_q = select(EvidencePack).where(EvidencePack.status.in_(["complete", "submitted"]))
        if entry.canton:
            pack_q = pack_q.join(Building, Building.id == EvidencePack.building_id).where(
                Building.canton == entry.canton
            )

        pack_result = await db.execute(pack_q)
        packs = list(pack_result.scalars().all())

        for pack in packs:
            invalidations = await inv_engine.scan_for_invalidations(db, pack.building_id, trigger_type="rule_change")
            invalidated += len(invalidations)

    except Exception:
        logger.exception("freshness_watch: pack_invalidation failed (scope=%s)", scope)

    return {
        "type": "pack_invalidation",
        "success": True,
        "detail": f"{invalidated} invalidation(s) creee(s) sur les packs",
        "count": invalidated,
    }


async def _react_blocker_refresh(
    db: AsyncSession,
    entry: FreshnessWatchEntry,
    reaction: dict,
) -> dict:
    """Update procedure blockers for affected procedures."""
    refreshed = 0

    try:
        from app.models.permit_procedure import PermitProcedure
        from app.models.permit_step import PermitStep

        step_q = (
            select(PermitStep)
            .join(PermitProcedure, PermitProcedure.id == PermitStep.procedure_id)
            .where(PermitStep.status.in_(["pending", "active"]))
        )

        if entry.canton:
            from app.models.building import Building

            step_q = step_q.join(Building, Building.id == PermitProcedure.building_id).where(
                Building.canton == entry.canton
            )

        result = await db.execute(step_q)
        steps = list(result.scalars().all())

        for step in steps:
            # Flag step as needs re-evaluation
            if hasattr(step, "status") and step.status == "active":
                step.status = "pending"
                refreshed += 1

    except Exception:
        logger.exception("freshness_watch: blocker_refresh failed")

    return {
        "type": "blocker_refresh",
        "success": True,
        "detail": f"{refreshed} blocker(s) mis a jour",
        "count": refreshed,
    }


async def _react_notification(
    db: AsyncSession,
    entry: FreshnessWatchEntry,
    reaction: dict,
) -> dict:
    """Notify affected users about the change."""
    notified = 0

    try:
        from app.models.notification import Notification

        # Notify all admin users
        from app.models.user import User

        admin_q = select(User).where(User.role == "admin")
        admin_result = await db.execute(admin_q)
        admins = list(admin_result.scalars().all())

        for admin in admins:
            notification = Notification(
                user_id=admin.id,
                type="system",
                title=f"Veille fraicheur: {entry.title}",
                message=entry.description or f"Changement detecte: {entry.delta_type} ({entry.severity})",
                status="unread",
            )
            db.add(notification)
            notified += 1

        await db.flush()

    except Exception:
        logger.exception("freshness_watch: notification failed")

    return {
        "type": "notification",
        "success": True,
        "detail": f"{notified} notification(s) envoyee(s)",
        "count": notified,
    }


# ------------------------------------------------------------------
# Query helpers
# ------------------------------------------------------------------


async def get_pending_watches(
    db: AsyncSession,
    *,
    status: str = "detected",
    severity: str | None = None,
    canton: str | None = None,
    delta_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[FreshnessWatchEntry], int]:
    """Get watch entries with optional filters."""
    query = select(FreshnessWatchEntry)
    count_filters = []

    if status:
        query = query.where(FreshnessWatchEntry.status == status)
        count_filters.append(FreshnessWatchEntry.status == status)
    if severity:
        query = query.where(FreshnessWatchEntry.severity == severity)
        count_filters.append(FreshnessWatchEntry.severity == severity)
    if canton:
        query = query.where(FreshnessWatchEntry.canton == canton)
        count_filters.append(FreshnessWatchEntry.canton == canton)
    if delta_type:
        query = query.where(FreshnessWatchEntry.delta_type == delta_type)
        count_filters.append(FreshnessWatchEntry.delta_type == delta_type)

    # Count
    count_q = (
        select(func.count(FreshnessWatchEntry.id)).where(*count_filters)
        if count_filters
        else select(func.count(FreshnessWatchEntry.id))
    )
    count_result = await db.execute(count_q)
    total = count_result.scalar() or 0

    query = (
        query.order_by(
            FreshnessWatchEntry.severity.desc(),
            FreshnessWatchEntry.detected_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_watch_dashboard(db: AsyncSession) -> dict:
    """Dashboard: total changes, by severity, by delta_type, by canton, by status."""

    # Total
    total_q = select(func.count(FreshnessWatchEntry.id))
    total_result = await db.execute(total_q)
    total = total_result.scalar() or 0

    # By severity
    sev_q = select(
        FreshnessWatchEntry.severity,
        func.count(FreshnessWatchEntry.id),
    ).group_by(FreshnessWatchEntry.severity)
    sev_result = await db.execute(sev_q)
    by_severity = {row[0]: row[1] for row in sev_result.all()}

    # By delta_type
    dt_q = select(
        FreshnessWatchEntry.delta_type,
        func.count(FreshnessWatchEntry.id),
    ).group_by(FreshnessWatchEntry.delta_type)
    dt_result = await db.execute(dt_q)
    by_delta_type = {row[0]: row[1] for row in dt_result.all()}

    # By canton
    canton_q = (
        select(
            FreshnessWatchEntry.canton,
            func.count(FreshnessWatchEntry.id),
        )
        .where(FreshnessWatchEntry.canton.isnot(None))
        .group_by(FreshnessWatchEntry.canton)
    )
    canton_result = await db.execute(canton_q)
    by_canton = {row[0]: row[1] for row in canton_result.all()}

    # By status
    status_q = select(
        FreshnessWatchEntry.status,
        func.count(FreshnessWatchEntry.id),
    ).group_by(FreshnessWatchEntry.status)
    status_result = await db.execute(status_q)
    by_status = {row[0]: row[1] for row in status_result.all()}

    # Critical pending (detected + critical)
    crit_q = select(func.count(FreshnessWatchEntry.id)).where(
        and_(
            FreshnessWatchEntry.severity == "critical",
            FreshnessWatchEntry.status.in_(["detected", "under_review"]),
        )
    )
    crit_result = await db.execute(crit_q)
    critical_pending = crit_result.scalar() or 0

    return {
        "total": total,
        "by_severity": by_severity,
        "by_delta_type": by_delta_type,
        "by_canton": by_canton,
        "by_status": by_status,
        "critical_pending": critical_pending,
    }


async def dismiss_watch(
    db: AsyncSession,
    entry_id: UUID,
    dismissed_by_id: UUID,
    reason: str,
) -> FreshnessWatchEntry | None:
    """Dismiss a watch entry as not impactful."""
    result = await db.execute(select(FreshnessWatchEntry).where(FreshnessWatchEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        return None

    now = datetime.now(UTC)
    entry.status = "dismissed"
    entry.reviewed_by_id = dismissed_by_id
    entry.reviewed_at = now
    entry.dismiss_reason = reason
    await db.flush()
    await db.refresh(entry)

    logger.info("freshness_watch: dismissed entry %s (reason: %s)", entry_id, reason)
    return entry


# ------------------------------------------------------------------
# Integration: source health -> freshness watch
# ------------------------------------------------------------------


async def from_source_health_event(
    db: AsyncSession,
    source_id: UUID,
    event_type: str,
    description: str | None = None,
) -> FreshnessWatchEntry | None:
    """Create a freshness watch entry from a SourceHealthEvent.

    Maps source health event_types to freshness delta_types:
    - schema_drift -> schema_change
    - unavailable -> provider_breakage
    - degraded -> provider_breakage (severity=warning)
    """
    delta_map = {
        "schema_drift": ("schema_change", "warning"),
        "unavailable": ("provider_breakage", "critical"),
        "degraded": ("provider_breakage", "warning"),
        "error": ("provider_breakage", "warning"),
        "timeout": ("provider_breakage", "info"),
    }

    mapped = delta_map.get(event_type)
    if not mapped:
        return None

    delta_type, severity = mapped

    # Look up source for context
    from app.models.source_registry import SourceRegistryEntry

    source_result = await db.execute(select(SourceRegistryEntry).where(SourceRegistryEntry.id == source_id))
    source = source_result.scalar_one_or_none()
    source_name = source.display_name if source else "Source inconnue"

    return await record_change(
        db,
        delta_type=delta_type,
        title=f"{source_name}: {event_type}",
        description=description or f"Evenement de sante source: {event_type}",
        severity=severity,
        source_registry_id=source_id,
        reactions=[
            {"type": "notification", "scope": "admins"},
        ],
    )


# ------------------------------------------------------------------
# Integration: critical watches for Today feed
# ------------------------------------------------------------------


async def get_critical_for_today(db: AsyncSession) -> list[dict]:
    """Return critical freshness watch entries for the Today feed."""
    query = (
        select(FreshnessWatchEntry)
        .where(
            FreshnessWatchEntry.severity == "critical",
            FreshnessWatchEntry.status.in_(["detected", "under_review"]),
        )
        .order_by(FreshnessWatchEntry.detected_at.desc())
        .limit(10)
    )
    result = await db.execute(query)
    entries = list(result.scalars().all())

    return [
        {
            "id": str(e.id),
            "type": "freshness_watch",
            "delta_type": e.delta_type,
            "title": e.title,
            "description": e.description,
            "severity": e.severity,
            "canton": e.canton,
            "status": e.status,
            "detected_at": e.detected_at.isoformat() if e.detected_at else None,
            "priority": "critical",
        }
        for e in entries
    ]
