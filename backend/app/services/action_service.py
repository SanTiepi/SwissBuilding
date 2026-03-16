"""
SwissBuildingOS - Action Item Service

CRUD operations and system-action synchronisation for ActionItem.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import (
    ACTION_PRIORITY_CRITICAL,
    ACTION_PRIORITY_HIGH,
    ACTION_PRIORITY_MEDIUM,
    ACTION_SOURCE_MANUAL,
    ACTION_SOURCE_SYSTEM,
    ACTION_STATUS_DONE,
    ACTION_STATUS_OPEN,
    ACTION_TYPE_ADD_SAMPLES,
    ACTION_TYPE_COMPLETE_DOSSIER,
    ACTION_TYPE_CREATE_DIAGNOSTIC,
    ACTION_TYPE_NOTIFY_CANTON,
    ACTION_TYPE_NOTIFY_SUVA,
    ACTION_TYPE_UPLOAD_REPORT,
)
from app.models.action_item import ActionItem
from app.schemas.action_item import ActionItemCreate, ActionItemUpdate

# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def list_actions(
    db: AsyncSession,
    *,
    building_id: UUID | None = None,
    status: str | None = None,
    priority: str | None = None,
    assigned_to: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ActionItem]:
    """List action items with optional filters."""
    stmt = select(ActionItem).order_by(ActionItem.created_at.desc())
    if building_id is not None:
        stmt = stmt.where(ActionItem.building_id == building_id)
    if status is not None:
        stmt = stmt.where(ActionItem.status == status)
    if priority is not None:
        stmt = stmt.where(ActionItem.priority == priority)
    if assigned_to is not None:
        stmt = stmt.where(ActionItem.assigned_to == assigned_to)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_building_actions(db: AsyncSession, building_id: UUID) -> list[ActionItem]:
    """List all action items for a specific building."""
    return await list_actions(db, building_id=building_id)


async def get_action(db: AsyncSession, action_id: UUID) -> ActionItem | None:
    """Get a single action item by ID."""
    stmt = select(ActionItem).where(ActionItem.id == action_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_action(
    db: AsyncSession,
    building_id: UUID,
    data: ActionItemCreate,
    created_by: UUID | None = None,
) -> ActionItem:
    """Create a new action item."""
    action = ActionItem(
        building_id=building_id,
        diagnostic_id=data.diagnostic_id,
        sample_id=data.sample_id,
        source_type=data.source_type or ACTION_SOURCE_MANUAL,
        action_type=data.action_type,
        title=data.title,
        description=data.description,
        priority=data.priority,
        due_date=data.due_date,
        assigned_to=data.assigned_to,
        metadata_json=data.metadata_json,
        created_by=created_by,
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action


async def update_action(
    db: AsyncSession,
    action_id: UUID,
    data: ActionItemUpdate,
) -> ActionItem | None:
    """Update an existing action item. Returns None if not found."""
    stmt = select(ActionItem).where(ActionItem.id == action_id)
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()
    if action is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(action, field, value)

    # Set completed_at when transitioning to done
    if data.status == ACTION_STATUS_DONE and action.completed_at is None:
        action.completed_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(action)
    return action


# ---------------------------------------------------------------------------
# System-action sync
# ---------------------------------------------------------------------------


async def sync_building_system_actions(db: AsyncSession, building_id: UUID) -> list[ActionItem]:
    """
    Synchronise system-generated action items for a building.

    1. Load building with diagnostics, documents, samples.
    2. Determine which system actions *should* exist based on current state.
    3. Upsert: create missing ones, mark resolved ones as done.
    """
    from app.models.building import Building
    from app.models.diagnostic import Diagnostic

    # Load building — expire first to ensure fresh data from DB
    await db.flush()
    stmt = (
        select(Building)
        .options(
            selectinload(Building.diagnostics).selectinload(Diagnostic.samples),
            selectinload(Building.documents),
            selectinload(Building.risk_scores),
        )
        .where(Building.id == building_id)
        .execution_options(populate_existing=True)
    )
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        return []

    # Load existing system actions for this building
    existing_stmt = (
        select(ActionItem)
        .where(ActionItem.building_id == building_id)
        .where(ActionItem.source_type == ACTION_SOURCE_SYSTEM)
    )
    existing_result = await db.execute(existing_stmt)
    existing_actions = list(existing_result.scalars().all())
    existing_keys: dict[str, ActionItem] = {}
    for a in existing_actions:
        meta = a.metadata_json or {}
        key = meta.get("system_key")
        if key:
            existing_keys[key] = a

    # Determine desired system actions
    desired: dict[str, dict] = {}

    # Rule 1: high/critical risk + no diagnostic → create_diagnostic
    risk_level = None
    if building.risk_scores:
        risk_level = building.risk_scores.overall_risk_level
    active_statuses = {"draft", "in_progress", "completed", "validated"}
    has_active_diagnostic = any(d.status in active_statuses for d in building.diagnostics)
    if risk_level in ("high", "critical") and not has_active_diagnostic:
        priority = ACTION_PRIORITY_CRITICAL if risk_level == "critical" else ACTION_PRIORITY_HIGH
        desired["create_diagnostic"] = {
            "action_type": ACTION_TYPE_CREATE_DIAGNOSTIC,
            "title": "Create a diagnostic for this high-risk building",
            "priority": priority,
        }

    for diag in building.diagnostics:
        diag_id = str(diag.id)

        # Rule 2: draft diagnostic with 0 samples → add_samples
        if diag.status == "draft" and len(diag.samples) == 0:
            key = f"add_samples_{diag_id}"
            desired[key] = {
                "action_type": ACTION_TYPE_ADD_SAMPLES,
                "title": f"Add samples to diagnostic {diag.diagnostic_type}",
                "priority": ACTION_PRIORITY_HIGH,
                "diagnostic_id": diag.id,
            }

        # Rule 3: completed diagnostic without report_file_path → upload_report
        if diag.status == "completed" and not diag.report_file_path:
            key = f"upload_report_{diag_id}"
            desired[key] = {
                "action_type": ACTION_TYPE_UPLOAD_REPORT,
                "title": f"Upload report for diagnostic {diag.diagnostic_type}",
                "priority": ACTION_PRIORITY_MEDIUM,
                "diagnostic_id": diag.id,
            }

        # Rule 4: suva required + no suva date → notify_suva
        if diag.suva_notification_required and not diag.suva_notification_date:
            key = f"notify_suva_{diag_id}"
            desired[key] = {
                "action_type": ACTION_TYPE_NOTIFY_SUVA,
                "title": f"Notify SUVA for diagnostic {diag.diagnostic_type}",
                "priority": ACTION_PRIORITY_CRITICAL,
                "diagnostic_id": diag.id,
            }

        # Rule 5: suva required + no canton date → notify_canton
        if diag.suva_notification_required and not diag.canton_notification_date:
            key = f"notify_canton_{diag_id}"
            desired[key] = {
                "action_type": ACTION_TYPE_NOTIFY_CANTON,
                "title": f"Notify canton for diagnostic {diag.diagnostic_type}",
                "priority": ACTION_PRIORITY_HIGH,
                "diagnostic_id": diag.id,
            }

        # Rule 6: validated diagnostic + no diagnostic_report document → complete_dossier
        if diag.status == "validated":
            has_report_doc = any(d.document_type == "diagnostic_report" for d in building.documents)
            if not has_report_doc:
                key = f"complete_dossier_{diag_id}"
                desired[key] = {
                    "action_type": ACTION_TYPE_COMPLETE_DOSSIER,
                    "title": f"Complete dossier for diagnostic {diag.diagnostic_type}",
                    "priority": ACTION_PRIORITY_MEDIUM,
                    "diagnostic_id": diag.id,
                }

    created: list[ActionItem] = []

    # Create missing actions
    for key, spec in desired.items():
        if key not in existing_keys:
            action = ActionItem(
                building_id=building_id,
                diagnostic_id=spec.get("diagnostic_id"),
                source_type=ACTION_SOURCE_SYSTEM,
                action_type=spec["action_type"],
                title=spec["title"],
                priority=spec["priority"],
                status=ACTION_STATUS_OPEN,
                metadata_json={"system_key": key},
            )
            db.add(action)
            created.append(action)

    # Mark resolved actions as done
    for key, action in existing_keys.items():
        if key not in desired and action.status not in (ACTION_STATUS_DONE, "dismissed"):
            action.status = ACTION_STATUS_DONE
            action.completed_at = datetime.now(UTC)

    if created or any(key not in desired for key in existing_keys):
        await db.commit()
        for a in created:
            await db.refresh(a)

    return created
