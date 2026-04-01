"""BatiConnect — Mise en concurrence encadree: RFQ API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.rfq import (
    TenderAttributeRequest,
    TenderComparisonRead,
    TenderInvitationCreate,
    TenderInvitationRead,
    TenderQuoteCreate,
    TenderQuoteRead,
    TenderRequestCreate,
    TenderRequestRead,
    TenderRequestUpdate,
)
from app.services.rfq_service import (
    attribute_tender,
    extract_quote_data,
    generate_comparison,
    generate_rfq_draft,
    get_tender,
    list_quotes_for_tender,
    list_tenders_for_building,
    send_tender,
    submit_quote,
    update_tender,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Generate draft RFQ from building dossier
# ---------------------------------------------------------------------------


@router.post(
    "/rfq/generate",
    response_model=TenderRequestRead,
    status_code=201,
    tags=["RFQ"],
)
async def generate_rfq_endpoint(
    payload: TenderRequestCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a pre-filled RFQ from building dossier data."""
    try:
        tender = await generate_rfq_draft(
            db,
            building_id=payload.building_id,
            work_type=payload.work_type,
            created_by_id=current_user.id,
            org_id=current_user.organization_id if hasattr(current_user, "organization_id") else None,
            title=payload.title,
            description=payload.description,
            deadline_submission=payload.deadline_submission,
            planned_start_date=payload.planned_start_date,
            planned_end_date=payload.planned_end_date,
            attachments_manual=payload.attachments_manual,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return tender


# ---------------------------------------------------------------------------
# Get / Update tender
# ---------------------------------------------------------------------------


@router.get(
    "/rfq/{tender_id}",
    response_model=TenderRequestRead,
    tags=["RFQ"],
)
async def get_tender_endpoint(
    tender_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get tender details."""
    tender = await get_tender(db, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender


@router.put(
    "/rfq/{tender_id}",
    response_model=TenderRequestRead,
    tags=["RFQ"],
)
async def update_tender_endpoint(
    tender_id: UUID,
    payload: TenderRequestUpdate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a tender (draft status only)."""
    try:
        tender = await update_tender(db, tender_id, payload.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return tender


# ---------------------------------------------------------------------------
# Send to contractors
# ---------------------------------------------------------------------------


@router.post(
    "/rfq/{tender_id}/send",
    response_model=list[TenderInvitationRead],
    status_code=201,
    tags=["RFQ"],
)
async def send_tender_endpoint(
    tender_id: UUID,
    payload: TenderInvitationCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Send tender invitations to selected contractors."""
    try:
        invitations = await send_tender(db, tender_id, payload.contractor_org_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return invitations


# ---------------------------------------------------------------------------
# Submit quote
# ---------------------------------------------------------------------------


@router.post(
    "/rfq/{tender_id}/quotes",
    response_model=TenderQuoteRead,
    status_code=201,
    tags=["RFQ"],
)
async def submit_quote_endpoint(
    tender_id: UUID,
    payload: TenderQuoteCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Submit a quote for a tender."""
    try:
        quote = await submit_quote(
            db,
            tender_id=tender_id,
            quote_data=payload.model_dump(),
            document_id=payload.document_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return quote


# ---------------------------------------------------------------------------
# Extract data from quote PDF
# ---------------------------------------------------------------------------


@router.post(
    "/rfq/{tender_id}/quotes/{quote_id}/extract",
    response_model=TenderQuoteRead,
    tags=["RFQ"],
)
async def extract_quote_data_endpoint(
    tender_id: UUID,
    quote_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Extract structured data from a quote PDF (placeholder)."""
    try:
        quote = await extract_quote_data(db, quote_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return quote


# ---------------------------------------------------------------------------
# Generate comparison
# ---------------------------------------------------------------------------


@router.post(
    "/rfq/{tender_id}/compare",
    response_model=TenderComparisonRead,
    tags=["RFQ"],
)
async def generate_comparison_endpoint(
    tender_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a neutral comparison of all quotes for a tender."""
    try:
        comparison = await generate_comparison(db, tender_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return comparison


# ---------------------------------------------------------------------------
# Attribute tender
# ---------------------------------------------------------------------------


@router.post(
    "/rfq/{tender_id}/attribute",
    response_model=TenderComparisonRead,
    tags=["RFQ"],
)
async def attribute_tender_endpoint(
    tender_id: UUID,
    payload: TenderAttributeRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record the client's choice of quote."""
    try:
        comparison = await attribute_tender(db, tender_id, payload.quote_id, payload.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return comparison


# ---------------------------------------------------------------------------
# List quotes for a tender
# ---------------------------------------------------------------------------


@router.get(
    "/rfq/{tender_id}/quotes",
    response_model=list[TenderQuoteRead],
    tags=["RFQ"],
)
async def list_quotes_for_tender_endpoint(
    tender_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all quotes for a tender."""
    return await list_quotes_for_tender(db, tender_id)


# ---------------------------------------------------------------------------
# List tenders for a building
# ---------------------------------------------------------------------------


@router.get(
    "/rfq/building/{building_id}",
    response_model=list[TenderRequestRead],
    tags=["RFQ"],
)
async def list_tenders_for_building_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all tenders for a building."""
    return await list_tenders_for_building(db, building_id)
