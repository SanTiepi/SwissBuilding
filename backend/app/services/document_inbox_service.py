"""GED Inbox — Document inbox service."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_inbox import DocumentInboxItem


async def create_inbox_item(
    db: AsyncSession,
    data: dict,
    uploaded_by: UUID | None = None,
) -> DocumentInboxItem:
    """Create a new inbox item in pending state."""
    item = DocumentInboxItem(
        uploaded_by_user_id=uploaded_by,
        status="pending",
        **data,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def list_inbox(
    db: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
    status_filter: str | None = None,
    source_filter: str | None = None,
) -> tuple[list[DocumentInboxItem], int]:
    """List inbox items with optional filters, paginated."""
    query = select(DocumentInboxItem)
    count_query = select(func.count()).select_from(DocumentInboxItem)

    if status_filter:
        query = query.where(DocumentInboxItem.status == status_filter)
        count_query = count_query.where(DocumentInboxItem.status == status_filter)
    if source_filter:
        query = query.where(DocumentInboxItem.source == source_filter)
        count_query = count_query.where(DocumentInboxItem.source == source_filter)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(DocumentInboxItem.created_at.desc()).offset((page - 1) * size).limit(size)
    items = (await db.execute(query)).scalars().all()
    return list(items), total


async def get_inbox_item(db: AsyncSession, item_id: UUID) -> DocumentInboxItem | None:
    """Get a single inbox item by ID."""
    result = await db.execute(select(DocumentInboxItem).where(DocumentInboxItem.id == item_id))
    return result.scalar_one_or_none()


async def classify_item(
    db: AsyncSession,
    item: DocumentInboxItem,
    classification: dict,
) -> DocumentInboxItem:
    """Update classification on an inbox item and set status to classified."""
    item.classification = classification
    if item.status == "pending":
        item.status = "classified"
    await db.flush()
    await db.refresh(item)
    return item


async def link_to_building(
    db: AsyncSession,
    item: DocumentInboxItem,
    building_id: UUID,
    document_type: str | None = None,
) -> DocumentInboxItem:
    """Create a Document record from the inbox item and mark as linked."""
    doc = Document(
        building_id=building_id,
        file_path=item.file_url,
        file_name=item.filename,
        file_size_bytes=item.file_size,
        mime_type=item.content_type,
        document_type=document_type,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    item.linked_building_id = building_id
    item.linked_document_id = doc.id
    item.status = "linked"
    await db.flush()
    await db.refresh(item)
    return item


async def reject_item(
    db: AsyncSession,
    item: DocumentInboxItem,
    reason: str | None = None,
) -> DocumentInboxItem:
    """Mark inbox item as rejected."""
    item.status = "rejected"
    if reason:
        item.notes = reason
    await db.flush()
    await db.refresh(item)
    return item
