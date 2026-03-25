"""BatiConnect — Marketplace RFQ API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.marketplace_rfq import (
    ClientRequestCreate,
    ClientRequestPublish,
    ClientRequestRead,
    QuoteComparisonView,
    QuoteCreate,
    QuoteRead,
    RequestDocumentCreate,
    RequestDocumentRead,
    RequestInvitationCreate,
    RequestInvitationRead,
)
from app.services.marketplace_rfq_service import (
    add_document,
    cancel_request,
    close_request,
    create_quote,
    create_request,
    get_quote_comparison,
    get_request_detail,
    list_quotes_for_request,
    list_requests,
    publish_request,
    send_invitations,
    submit_quote,
    withdraw_quote,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Client Requests
# ---------------------------------------------------------------------------


@router.post(
    "/marketplace/requests",
    response_model=ClientRequestRead,
    status_code=201,
)
async def create_request_endpoint(
    payload: ClientRequestCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump()
    req = await create_request(db, data, requester_user_id=current_user.id)
    await db.commit()
    return req


@router.get(
    "/marketplace/requests",
    response_model=PaginatedResponse[ClientRequestRead],
)
async def list_requests_endpoint(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    building_id: UUID | None = None,
    status: str | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await list_requests(db, building_id=building_id, status=status, page=page, size=size)
    pages = (total + size - 1) // size if total > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


@router.get(
    "/marketplace/requests/{request_id}",
    response_model=ClientRequestRead,
)
async def get_request_endpoint(
    request_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    req = await get_request_detail(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


# ---------------------------------------------------------------------------
# Publish / Close / Cancel
# ---------------------------------------------------------------------------


@router.post(
    "/marketplace/requests/{request_id}/publish",
    response_model=ClientRequestRead,
)
async def publish_request_endpoint(
    request_id: UUID,
    payload: ClientRequestPublish | None = None,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    # Optionally set diagnostic_publication_id before publish
    if payload and payload.diagnostic_publication_id:
        req = await get_request_detail(db, request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        req.diagnostic_publication_id = payload.diagnostic_publication_id
        await db.flush()

    try:
        result = await publish_request(db, request_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return result


@router.post(
    "/marketplace/requests/{request_id}/close",
    response_model=ClientRequestRead,
)
async def close_request_endpoint(
    request_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await close_request(db, request_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return result


@router.post(
    "/marketplace/requests/{request_id}/cancel",
    response_model=ClientRequestRead,
)
async def cancel_request_endpoint(
    request_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await cancel_request(db, request_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return result


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


@router.post(
    "/marketplace/requests/{request_id}/documents",
    response_model=RequestDocumentRead,
    status_code=201,
)
async def add_document_endpoint(
    request_id: UUID,
    payload: RequestDocumentCreate,
    current_user: User = Depends(require_permission("documents", "create")),
    db: AsyncSession = Depends(get_db),
):
    req = await get_request_detail(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    data = payload.model_dump()
    doc = await add_document(db, request_id, data, uploaded_by_user_id=current_user.id)
    await db.commit()
    return doc


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


@router.post(
    "/marketplace/requests/{request_id}/invitations",
    response_model=list[RequestInvitationRead],
    status_code=201,
)
async def send_invitations_endpoint(
    request_id: UUID,
    payload: RequestInvitationCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    req = await get_request_detail(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    try:
        invitations = await send_invitations(db, request_id, payload.company_profile_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return invitations


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------


@router.post(
    "/marketplace/quotes",
    response_model=QuoteRead,
    status_code=201,
)
async def create_quote_endpoint(
    payload: QuoteCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump()
    quote = await create_quote(db, data)
    await db.commit()
    return quote


@router.get(
    "/marketplace/requests/{request_id}/quotes",
    response_model=list[QuoteRead],
)
async def list_quotes_endpoint(
    request_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await list_quotes_for_request(db, request_id)


@router.post(
    "/marketplace/quotes/{quote_id}/submit",
    response_model=QuoteRead,
)
async def submit_quote_endpoint(
    quote_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await submit_quote(db, quote_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return result


@router.post(
    "/marketplace/quotes/{quote_id}/withdraw",
    response_model=QuoteRead,
)
async def withdraw_quote_endpoint(
    quote_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await withdraw_quote(db, quote_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return result


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


@router.get(
    "/marketplace/requests/{request_id}/comparison",
    response_model=QuoteComparisonView,
)
async def quote_comparison_endpoint(
    request_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    req = await get_request_detail(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return await get_quote_comparison(db, request_id)
