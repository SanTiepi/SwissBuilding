"""
BatiConnect - Action Queue Service

Operator daily/weekly ritual surface: prioritized action queue per building.
Groups actions by urgency (overdue, this week, this month, backlog) and provides
completion with re-evaluation, snooze, and weekly summary.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    ACTION_STATUS_DONE,
    ACTION_STATUS_OPEN,
)
from app.models.action_item import ActionItem

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Effort estimation heuristic
# ---------------------------------------------------------------------------

_EFFORT_BY_TYPE: dict[str, str] = {
    "create_diagnostic": "heavy",
    "add_samples": "medium",
    "upload_report": "quick",
    "notify_suva": "quick",
    "notify_canton": "quick",
    "complete_dossier": "medium",
    "validate_diagnostic": "quick",
    "remediation": "heavy",
    "investigation": "medium",
    "notification": "quick",
    "procurement": "heavy",
    "documentation": "medium",
}


def _estimate_effort(action: ActionItem) -> str:
    return _EFFORT_BY_TYPE.get(action.action_type, "medium")


# ---------------------------------------------------------------------------
# Suggested resolution mapping
# ---------------------------------------------------------------------------

_RESOLUTION_BY_SOURCE: dict[str, str] = {
    "readiness": "Consultez l'onglet Readiness et resolez les blocages identifies.",
    "unknown": "Consultez les inconnues du dossier et completez les informations manquantes.",
    "contradiction": "Verifiez les contradictions detectees dans le dossier.",
    "risk": "Consultez l'onglet diagnostics et evaluez les risques.",
    "diagnostic": "Ouvrez le diagnostic associe et completez les etapes requises.",
    "document": "Telechargez ou completez les documents manquants.",
    "compliance": "Verifiez la conformite reglementaire dans l'onglet procedures.",
    "system": "Action generee automatiquement par le systeme.",
    "manual": "Action creee manuellement. Consultez la description pour les details.",
    "simulation": "Resultats de simulation necessitant une action.",
}


def _suggested_resolution(action: ActionItem) -> str:
    return _RESOLUTION_BY_SOURCE.get(action.source_type, "Consultez la description de l'action.")


# ---------------------------------------------------------------------------
# Linked entity helper
# ---------------------------------------------------------------------------


def _linked_entity(action: ActionItem) -> dict | None:
    if action.diagnostic_id:
        return {"type": "diagnostic", "id": str(action.diagnostic_id)}
    if action.sample_id:
        return {"type": "sample", "id": str(action.sample_id)}
    meta = action.metadata_json or {}
    if meta.get("zone_id"):
        return {"type": "zone", "id": str(meta["zone_id"])}
    if meta.get("intervention_id"):
        return {"type": "intervention", "id": str(meta["intervention_id"])}
    return None


# ---------------------------------------------------------------------------
# Serialise a single action for the queue
# ---------------------------------------------------------------------------


def _serialize_action(action: ActionItem) -> dict:
    return {
        "id": str(action.id),
        "title": action.title,
        "description": action.description,
        "priority": action.priority,
        "status": action.status,
        "source_type": action.source_type,
        "action_type": action.action_type,
        "deadline": action.due_date.isoformat() if action.due_date else None,
        "linked_entity": _linked_entity(action),
        "suggested_resolution": _suggested_resolution(action),
        "estimated_effort": _estimate_effort(action),
        "created_at": action.created_at.isoformat() if action.created_at else None,
        "completed_at": action.completed_at.isoformat() if action.completed_at else None,
        "snoozed_until": (action.metadata_json or {}).get("snoozed_until"),
        "metadata_json": action.metadata_json,
    }


# ---------------------------------------------------------------------------
# Priority sort key
# ---------------------------------------------------------------------------

_PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _sort_key(action: ActionItem) -> tuple:
    return (
        _PRIORITY_ORDER.get(action.priority, 9),
        action.due_date or date(9999, 12, 31),
        action.created_at or datetime.min,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_building_queue(
    db: AsyncSession,
    building_id: UUID,
    filter_status: str = "open",
) -> dict:
    """Get the prioritized action queue for a building grouped by urgency."""
    stmt = select(ActionItem).where(ActionItem.building_id == building_id)

    if filter_status == "open":
        stmt = stmt.where(ActionItem.status.in_([ACTION_STATUS_OPEN, "in_progress", "blocked"]))
    elif filter_status != "all":
        stmt = stmt.where(ActionItem.status == filter_status)

    result = await db.execute(stmt)
    actions = list(result.scalars().all())

    # Filter out snoozed actions (snoozed_until in the future)
    today = date.today()
    active_actions: list[ActionItem] = []
    snoozed_actions: list[ActionItem] = []

    for action in actions:
        meta = action.metadata_json or {}
        snoozed_until = meta.get("snoozed_until")
        if snoozed_until:
            try:
                snooze_date = date.fromisoformat(snoozed_until)
                if snooze_date > today:
                    snoozed_actions.append(action)
                    continue
            except (ValueError, TypeError):
                pass
        active_actions.append(action)

    # Group by urgency
    overdue: list[ActionItem] = []
    this_week: list[ActionItem] = []
    this_month: list[ActionItem] = []
    backlog: list[ActionItem] = []

    week_end = today + timedelta(days=7)
    month_end = today + timedelta(days=30)

    for action in active_actions:
        if action.due_date and action.due_date < today:
            overdue.append(action)
        elif action.due_date and action.due_date <= week_end:
            this_week.append(action)
        elif action.due_date and action.due_date <= month_end:
            this_month.append(action)
        else:
            backlog.append(action)

    # Sort each group by priority then deadline
    overdue.sort(key=_sort_key)
    this_week.sort(key=_sort_key)
    this_month.sort(key=_sort_key)
    backlog.sort(key=_sort_key)

    return {
        "building_id": str(building_id),
        "summary": {
            "overdue": len(overdue),
            "this_week": len(this_week),
            "this_month": len(this_month),
            "backlog": len(backlog),
            "snoozed": len(snoozed_actions),
            "total": len(active_actions),
        },
        "overdue": [_serialize_action(a) for a in overdue],
        "this_week": [_serialize_action(a) for a in this_week],
        "this_month": [_serialize_action(a) for a in this_month],
        "backlog": [_serialize_action(a) for a in backlog],
        "snoozed": [_serialize_action(a) for a in snoozed_actions],
    }


async def complete_action(
    db: AsyncSession,
    action_id: UUID,
    completed_by_id: UUID,
    resolution_note: str | None = None,
) -> ActionItem | None:
    """Mark an action as completed and trigger re-evaluation generators."""
    stmt = select(ActionItem).where(ActionItem.id == action_id)
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()
    if action is None:
        return None

    action.status = ACTION_STATUS_DONE
    action.completed_at = datetime.now(UTC)

    # Store resolution metadata
    meta = dict(action.metadata_json or {})
    meta["completed_by"] = str(completed_by_id)
    if resolution_note:
        meta["resolution_note"] = resolution_note
    action.metadata_json = meta

    await db.flush()

    # Re-run generators to detect new actions or auto-resolve existing ones
    building_id = action.building_id
    try:
        from app.services.readiness_action_generator import generate_readiness_actions

        await generate_readiness_actions(db, building_id)
    except Exception:
        logger.warning("Readiness action re-generation failed for building %s", building_id)

    try:
        from app.services.unknown_generator import generate_unknowns

        await generate_unknowns(db, building_id)
    except Exception:
        logger.warning("Unknown re-generation failed for building %s", building_id)

    await db.commit()
    await db.refresh(action)
    return action


async def snooze_action(
    db: AsyncSession,
    action_id: UUID,
    snooze_until: date,
    snoozed_by_id: UUID,
) -> ActionItem | None:
    """Snooze an action to a future date."""
    stmt = select(ActionItem).where(ActionItem.id == action_id)
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()
    if action is None:
        return None

    meta = dict(action.metadata_json or {})
    meta["snoozed_until"] = snooze_until.isoformat()
    meta["snoozed_by"] = str(snoozed_by_id)
    action.metadata_json = meta

    await db.commit()
    await db.refresh(action)
    return action


async def get_weekly_summary(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Generate a weekly summary of action activity."""
    now = datetime.now(UTC)
    week_ago = now - timedelta(days=7)

    # Actions completed this week
    completed_stmt = select(ActionItem).where(
        and_(
            ActionItem.building_id == building_id,
            ActionItem.status == ACTION_STATUS_DONE,
            ActionItem.completed_at >= week_ago,
        )
    )
    completed_result = await db.execute(completed_stmt)
    completed = list(completed_result.scalars().all())

    # Actions created this week
    created_stmt = select(ActionItem).where(
        and_(
            ActionItem.building_id == building_id,
            ActionItem.created_at >= week_ago,
        )
    )
    created_result = await db.execute(created_stmt)
    created = list(created_result.scalars().all())

    # Current open actions for next week priorities
    open_stmt = (
        select(ActionItem)
        .where(
            and_(
                ActionItem.building_id == building_id,
                ActionItem.status.in_([ACTION_STATUS_OPEN, "in_progress", "blocked"]),
            )
        )
        .order_by(ActionItem.due_date.asc().nulls_last())
    )
    open_result = await db.execute(open_stmt)
    open_actions = list(open_result.scalars().all())

    # Determine readiness trend
    net_change = len(completed) - len(created)
    if net_change > 0:
        trend = "improved"
    elif net_change < 0:
        trend = "degraded"
    else:
        trend = "stable"

    # Next week priorities: top 5 open actions by priority then deadline
    open_actions.sort(key=_sort_key)
    next_priorities = [_serialize_action(a) for a in open_actions[:5]]

    return {
        "building_id": str(building_id),
        "period_start": week_ago.isoformat(),
        "period_end": now.isoformat(),
        "completed_count": len(completed),
        "created_count": len(created),
        "completed": [_serialize_action(a) for a in completed],
        "created": [_serialize_action(a) for a in created],
        "readiness_trend": trend,
        "open_count": len(open_actions),
        "next_priorities": next_priorities,
    }
