"""BatiConnect — BuildingCase service.

CRUD + lifecycle management for building cases (operating episodes).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building_case import (
    CASE_STATE_TRANSITIONS,
    CASE_STATES,
    CASE_TYPES,
    BuildingCase,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def create_case(
    db: AsyncSession,
    building_id: UUID,
    organization_id: UUID,
    created_by_id: UUID,
    case_type: str,
    title: str,
    *,
    description: str | None = None,
    spatial_scope_ids: list[str] | None = None,
    pollutant_scope: list[str] | None = None,
    planned_start: datetime | None = None,
    planned_end: datetime | None = None,
    intervention_id: UUID | None = None,
    tender_id: UUID | None = None,
    steps: list[dict] | None = None,
    canton: str | None = None,
    authority: str | None = None,
    priority: str = "medium",
) -> BuildingCase:
    """Create a new building case."""
    if case_type not in CASE_TYPES:
        raise ValueError(f"Invalid case_type '{case_type}'. Must be one of {CASE_TYPES}")

    case = BuildingCase(
        building_id=building_id,
        organization_id=organization_id,
        created_by_id=created_by_id,
        case_type=case_type,
        title=title,
        description=description,
        state="draft",
        spatial_scope_ids=spatial_scope_ids,
        pollutant_scope=pollutant_scope,
        planned_start=planned_start,
        planned_end=planned_end,
        intervention_id=intervention_id,
        tender_id=tender_id,
        steps=steps,
        canton=canton,
        authority=authority,
        priority=priority,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    logger.info("Created BuildingCase %s (type=%s) for building %s", case.id, case_type, building_id)
    return case


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


async def get_case(db: AsyncSession, case_id: UUID) -> BuildingCase | None:
    """Get a single case by ID."""
    result = await db.execute(select(BuildingCase).where(BuildingCase.id == case_id))
    return result.scalar_one_or_none()


async def list_cases(
    db: AsyncSession,
    *,
    building_id: UUID | None = None,
    organization_id: UUID | None = None,
    state: str | None = None,
    case_type: str | None = None,
) -> list[BuildingCase]:
    """List cases with optional filters."""
    stmt = select(BuildingCase)
    if building_id:
        stmt = stmt.where(BuildingCase.building_id == building_id)
    if organization_id:
        stmt = stmt.where(BuildingCase.organization_id == organization_id)
    if state:
        stmt = stmt.where(BuildingCase.state == state)
    if case_type:
        stmt = stmt.where(BuildingCase.case_type == case_type)
    stmt = stmt.order_by(BuildingCase.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def update_case(
    db: AsyncSession,
    case_id: UUID,
    **kwargs,
) -> BuildingCase | None:
    """Update mutable fields on a case."""
    case = await get_case(db, case_id)
    if case is None:
        return None

    allowed_fields = {
        "title",
        "description",
        "spatial_scope_ids",
        "pollutant_scope",
        "planned_start",
        "planned_end",
        "actual_start",
        "actual_end",
        "steps",
        "canton",
        "authority",
        "priority",
    }
    for key, value in kwargs.items():
        if key in allowed_fields and value is not None:
            setattr(case, key, value)

    await db.commit()
    await db.refresh(case)
    return case


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


async def advance_case(
    db: AsyncSession,
    case_id: UUID,
    new_state: str,
) -> BuildingCase:
    """Advance case state with validated transitions."""
    if new_state not in CASE_STATES:
        raise ValueError(f"Invalid state '{new_state}'. Must be one of {CASE_STATES}")

    case = await get_case(db, case_id)
    if case is None:
        raise ValueError(f"BuildingCase {case_id} not found")

    allowed = CASE_STATE_TRANSITIONS.get(case.state, ())
    if new_state not in allowed:
        raise ValueError(f"Cannot transition from '{case.state}' to '{new_state}'. Allowed transitions: {allowed}")

    old_state = case.state
    case.state = new_state

    # Auto-set actual dates on key transitions
    now = datetime.now(UTC)
    if new_state == "in_progress" and case.actual_start is None:
        case.actual_start = now
    if new_state in ("completed", "closed") and case.actual_end is None:
        case.actual_end = now

    await db.commit()
    await db.refresh(case)
    logger.info("BuildingCase %s: %s -> %s", case_id, old_state, new_state)
    return case


# ---------------------------------------------------------------------------
# Step management
# ---------------------------------------------------------------------------


async def complete_step(
    db: AsyncSession,
    case_id: UUID,
    step_name: str,
    status: str = "completed",
) -> BuildingCase:
    """Mark a case step as completed (or another status)."""
    case = await get_case(db, case_id)
    if case is None:
        raise ValueError(f"BuildingCase {case_id} not found")

    steps = list(case.steps or [])
    found = False
    for step in steps:
        if step.get("name") == step_name:
            step["status"] = status
            found = True
            break

    if not found:
        raise ValueError(f"Step '{step_name}' not found in case {case_id}")

    case.steps = steps
    await db.commit()
    await db.refresh(case)
    return case


# ---------------------------------------------------------------------------
# Linking
# ---------------------------------------------------------------------------


async def link_intervention(
    db: AsyncSession,
    case_id: UUID,
    intervention_id: UUID,
) -> BuildingCase:
    """Link an existing intervention to this case."""
    case = await get_case(db, case_id)
    if case is None:
        raise ValueError(f"BuildingCase {case_id} not found")

    case.intervention_id = intervention_id
    await db.commit()
    await db.refresh(case)
    logger.info("Linked intervention %s to case %s", intervention_id, case_id)
    return case


async def link_tender(
    db: AsyncSession,
    case_id: UUID,
    tender_id: UUID,
) -> BuildingCase:
    """Link an existing tender request to this case."""
    case = await get_case(db, case_id)
    if case is None:
        raise ValueError(f"BuildingCase {case_id} not found")

    case.tender_id = tender_id
    await db.commit()
    await db.refresh(case)
    logger.info("Linked tender %s to case %s", tender_id, case_id)
    return case


# ---------------------------------------------------------------------------
# Context & timeline
# ---------------------------------------------------------------------------


async def get_case_context(db: AsyncSession, case_id: UUID) -> dict:
    """Get full case context: case data + linked entity summaries."""
    case = await get_case(db, case_id)
    if case is None:
        raise ValueError(f"BuildingCase {case_id} not found")

    context: dict = {
        "case_id": str(case.id),
        "building_id": str(case.building_id),
        "case_type": case.case_type,
        "title": case.title,
        "state": case.state,
        "priority": case.priority,
        "spatial_scope_ids": case.spatial_scope_ids,
        "pollutant_scope": case.pollutant_scope,
        "planned_start": case.planned_start.isoformat() if case.planned_start else None,
        "planned_end": case.planned_end.isoformat() if case.planned_end else None,
        "actual_start": case.actual_start.isoformat() if case.actual_start else None,
        "actual_end": case.actual_end.isoformat() if case.actual_end else None,
        "steps": case.steps,
        "intervention_id": str(case.intervention_id) if case.intervention_id else None,
        "tender_id": str(case.tender_id) if case.tender_id else None,
    }
    return context


async def get_case_timeline(db: AsyncSession, case_id: UUID) -> list[dict]:
    """Get chronological events for this case.

    Returns key timestamps: creation, state changes (from steps),
    planned/actual dates, and linked entity info.
    """
    case = await get_case(db, case_id)
    if case is None:
        raise ValueError(f"BuildingCase {case_id} not found")

    events: list[dict] = []

    # Creation event
    if case.created_at:
        events.append(
            {
                "timestamp": case.created_at.isoformat(),
                "event_type": "created",
                "label": f"Case created: {case.title}",
            }
        )

    # Planned dates
    if case.planned_start:
        events.append(
            {
                "timestamp": case.planned_start.isoformat(),
                "event_type": "planned_start",
                "label": "Planned start",
            }
        )
    if case.planned_end:
        events.append(
            {
                "timestamp": case.planned_end.isoformat(),
                "event_type": "planned_end",
                "label": "Planned end",
            }
        )

    # Actual dates
    if case.actual_start:
        events.append(
            {
                "timestamp": case.actual_start.isoformat(),
                "event_type": "actual_start",
                "label": "Actual start",
            }
        )
    if case.actual_end:
        events.append(
            {
                "timestamp": case.actual_end.isoformat(),
                "event_type": "actual_end",
                "label": "Actual end",
            }
        )

    # Step events
    for step in case.steps or []:
        events.append(
            {
                "timestamp": case.updated_at.isoformat() if case.updated_at else case.created_at.isoformat(),
                "event_type": "step",
                "label": f"Step '{step.get('name', '?')}': {step.get('status', '?')}",
            }
        )

    # Sort chronologically
    events.sort(key=lambda e: e["timestamp"])
    return events
