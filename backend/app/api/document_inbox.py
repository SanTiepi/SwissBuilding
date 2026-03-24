"""GED Inbox — API routes for document inbox."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.document_inbox import DocumentInboxItem
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.document_inbox import (
    DocumentInboxClassifyRequest,
    DocumentInboxItemCreate,
    DocumentInboxItemListRead,
    DocumentInboxItemRead,
    DocumentInboxLinkRequest,
    DocumentInboxRejectRequest,
)
from app.services.document_inbox_service import (
    classify_item,
    create_inbox_item,
    get_inbox_item,
    link_to_building,
    list_inbox,
    reject_item,
)

router = APIRouter()


async def _get_item_or_404(db: AsyncSession, item_id: UUID) -> DocumentInboxItem:
    item = await get_inbox_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    return item


@router.get(
    "/document-inbox",
    response_model=PaginatedResponse[DocumentInboxItemListRead],
)
async def list_inbox_endpoint(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    source: str | None = None,
    current_user: User = Depends(require_permission("documents", "list")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await list_inbox(db, page=page, size=size, status_filter=status, source_filter=source)
    pages = (total + size - 1) // size if total > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


@router.get(
    "/document-inbox/{item_id}",
    response_model=DocumentInboxItemRead,
)
async def get_inbox_item_endpoint(
    item_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await _get_item_or_404(db, item_id)


@router.post(
    "/document-inbox",
    response_model=DocumentInboxItemRead,
    status_code=201,
)
async def create_inbox_item_endpoint(
    payload: DocumentInboxItemCreate,
    current_user: User = Depends(require_permission("documents", "create")),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    item = await create_inbox_item(db, data, uploaded_by=current_user.id)
    await db.commit()
    return item


@router.post(
    "/document-inbox/{item_id}/classify",
    response_model=DocumentInboxItemRead,
)
async def classify_inbox_item_endpoint(
    item_id: UUID,
    payload: DocumentInboxClassifyRequest,
    current_user: User = Depends(require_permission("documents", "create")),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_item_or_404(db, item_id)
    if item.status == "linked":
        raise HTTPException(status_code=400, detail="Cannot classify a linked item")
    classification = {
        "document_type": payload.document_type,
        "confidence": payload.confidence,
        "tags": payload.tags,
    }
    result = await classify_item(db, item, classification)
    await db.commit()
    return result


@router.post(
    "/document-inbox/{item_id}/link",
    response_model=DocumentInboxItemRead,
)
async def link_inbox_item_endpoint(
    item_id: UUID,
    payload: DocumentInboxLinkRequest,
    current_user: User = Depends(require_permission("documents", "create")),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_item_or_404(db, item_id)
    if item.status == "linked":
        raise HTTPException(status_code=400, detail="Item already linked")
    if item.status == "rejected":
        raise HTTPException(status_code=400, detail="Cannot link a rejected item")

    # Verify building exists
    from app.services.building_service import get_building

    building = await get_building(db, payload.building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    result = await link_to_building(db, item, payload.building_id, payload.document_type)
    await db.commit()
    return result


@router.post(
    "/document-inbox/{item_id}/reject",
    response_model=DocumentInboxItemRead,
)
async def reject_inbox_item_endpoint(
    item_id: UUID,
    payload: DocumentInboxRejectRequest,
    current_user: User = Depends(require_permission("documents", "create")),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_item_or_404(db, item_id)
    if item.status == "linked":
        raise HTTPException(status_code=400, detail="Cannot reject a linked item")
    result = await reject_item(db, item, payload.reason)
    await db.commit()
    return result
