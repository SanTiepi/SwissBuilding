from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.event import Event
from app.schemas.activity import ActivityItemRead


async def get_building_activity(
    db: AsyncSession,
    building_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[ActivityItemRead]:
    """Return an aggregated activity timeline for a building.

    Merges diagnostics, documents, events, and (optionally) action items,
    sorted by occurred_at descending, with limit/offset applied.
    """
    items: list[ActivityItemRead] = []

    # --- Diagnostics ---
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    for diag in diag_result.scalars().all():
        occurred_at = diag.created_at
        if diag.date_inspection is not None:
            occurred_at = datetime.combine(diag.date_inspection, time.min)
        items.append(
            ActivityItemRead(
                id=diag.id,
                kind="diagnostic",
                source_id=diag.id,
                building_id=diag.building_id,
                occurred_at=occurred_at,
                title=f"Diagnostic {diag.diagnostic_type}",
                description=diag.summary,
                status=diag.status,
                actor_id=diag.diagnostician_id,
            )
        )

    # --- Documents ---
    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    for doc in doc_result.scalars().all():
        items.append(
            ActivityItemRead(
                id=doc.id,
                kind="document",
                source_id=doc.id,
                building_id=doc.building_id,
                occurred_at=doc.created_at,
                title=doc.file_name or doc.description or "Document",
                description=doc.description,
                actor_id=doc.uploaded_by,
            )
        )

    # --- Events ---
    evt_result = await db.execute(select(Event).where(Event.building_id == building_id))
    for evt in evt_result.scalars().all():
        occurred_at = datetime.combine(evt.date, time.min) if evt.date else evt.created_at
        items.append(
            ActivityItemRead(
                id=evt.id,
                kind="event",
                source_id=evt.id,
                building_id=evt.building_id,
                occurred_at=occurred_at,
                title=evt.title,
                description=evt.description,
                actor_id=evt.created_by,
                metadata_json=evt.metadata_json,
            )
        )

    # --- Action items (optional - model may not exist yet) ---
    try:
        from app.models.action_item import ActionItem

        action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
        for action in action_result.scalars().all():
            items.append(
                ActivityItemRead(
                    id=action.id,
                    kind="action",
                    source_id=action.id,
                    building_id=action.building_id,
                    occurred_at=action.created_at,
                    title=action.title,
                    status=getattr(action, "status", None),
                    actor_id=getattr(action, "created_by", None),
                )
            )
    except (ImportError, Exception):
        pass

    # Sort descending by occurred_at, then apply limit/offset
    items.sort(key=lambda x: x.occurred_at, reverse=True)
    return items[offset : offset + limit]
