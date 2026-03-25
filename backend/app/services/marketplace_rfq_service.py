"""BatiConnect — Marketplace RFQ service (ClientRequest, Invitation, Quote)."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client_request import ClientRequest
from app.models.company_profile import CompanyProfile
from app.models.company_subscription import CompanySubscription
from app.models.company_verification import CompanyVerification
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.quote import Quote
from app.models.request_document import RequestDocument
from app.models.request_invitation import RequestInvitation

# ---------------------------------------------------------------------------
# ClientRequest CRUD
# ---------------------------------------------------------------------------


async def create_request(db: AsyncSession, data: dict, requester_user_id: UUID) -> ClientRequest:
    """Create a draft RFQ."""
    req = ClientRequest(requester_user_id=requester_user_id, **data)
    db.add(req)
    await db.flush()
    await db.refresh(req)
    return req


async def publish_request(db: AsyncSession, request_id: UUID) -> ClientRequest:
    """Publish an RFQ. ENFORCES: diagnostic_publication_id must be set and matched to building."""
    result = await db.execute(select(ClientRequest).where(ClientRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise ValueError("Request not found")
    if req.status != "draft":
        raise ValueError(f"Cannot publish request in status '{req.status}'")

    # ENFORCE: diagnostic publication must be set
    if not req.diagnostic_publication_id:
        raise ValueError("No valid diagnostic publication for this building. Request a Batiscan assessment first.")

    # ENFORCE: publication must be matched to the building
    pub_result = await db.execute(
        select(DiagnosticReportPublication).where(DiagnosticReportPublication.id == req.diagnostic_publication_id)
    )
    pub = pub_result.scalar_one_or_none()
    if not pub or pub.building_id != req.building_id:
        raise ValueError("No valid diagnostic publication for this building. Request a Batiscan assessment first.")

    req.status = "published"
    req.published_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(req)
    return req


async def close_request(db: AsyncSession, request_id: UUID) -> ClientRequest:
    result = await db.execute(select(ClientRequest).where(ClientRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise ValueError("Request not found")
    if req.status not in ("published", "awarded"):
        raise ValueError(f"Cannot close request in status '{req.status}'")
    req.status = "closed"
    req.closed_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(req)
    return req


async def cancel_request(db: AsyncSession, request_id: UUID) -> ClientRequest:
    result = await db.execute(select(ClientRequest).where(ClientRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise ValueError("Request not found")
    if req.status in ("closed", "cancelled"):
        raise ValueError(f"Cannot cancel request in status '{req.status}'")
    req.status = "cancelled"
    req.closed_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(req)
    return req


# ---------------------------------------------------------------------------
# Request Documents
# ---------------------------------------------------------------------------


async def add_document(
    db: AsyncSession, request_id: UUID, doc_data: dict, uploaded_by_user_id: UUID | None = None
) -> RequestDocument:
    doc = RequestDocument(client_request_id=request_id, uploaded_by_user_id=uploaded_by_user_id, **doc_data)
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


async def _is_company_eligible(db: AsyncSession, company_profile_id: UUID) -> bool:
    """Check if company has approved verification + active subscription."""
    verif = await db.execute(
        select(CompanyVerification)
        .where(CompanyVerification.company_profile_id == company_profile_id)
        .where(CompanyVerification.status == "approved")
        .limit(1)
    )
    if not verif.scalar_one_or_none():
        return False

    sub = await db.execute(
        select(CompanySubscription)
        .where(CompanySubscription.company_profile_id == company_profile_id)
        .where(CompanySubscription.status == "active")
        .limit(1)
    )
    return sub.scalar_one_or_none() is not None


async def send_invitations(
    db: AsyncSession, request_id: UUID, company_profile_ids: list[UUID]
) -> list[RequestInvitation]:
    """Send invitations. ENFORCES: each company must be network-eligible."""
    invitations = []
    for cpid in company_profile_ids:
        eligible = await _is_company_eligible(db, cpid)
        if not eligible:
            raise ValueError(f"Company {cpid} is not network-eligible (requires verified + active subscription)")
        inv = RequestInvitation(
            client_request_id=request_id,
            company_profile_id=cpid,
            status="pending",
            sent_at=datetime.now(UTC),
        )
        db.add(inv)
        invitations.append(inv)
    await db.flush()
    for inv in invitations:
        await db.refresh(inv)
    return invitations


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------


def _compute_content_hash(quote: Quote) -> str:
    """SHA-256 of quote content fields at submission time."""
    content = {
        "client_request_id": str(quote.client_request_id),
        "company_profile_id": str(quote.company_profile_id),
        "amount_chf": str(quote.amount_chf),
        "currency": quote.currency,
        "validity_days": quote.validity_days,
        "description": quote.description,
        "work_plan": quote.work_plan,
        "timeline_weeks": quote.timeline_weeks,
        "includes": quote.includes,
        "excludes": quote.excludes,
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


async def create_quote(db: AsyncSession, data: dict) -> Quote:
    """Create a draft quote."""
    quote = Quote(**data)
    db.add(quote)
    await db.flush()
    await db.refresh(quote)
    return quote


async def submit_quote(db: AsyncSession, quote_id: UUID) -> Quote:
    """Submit a quote — computes content_hash and sets submitted_at."""
    result = await db.execute(select(Quote).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()
    if not quote:
        raise ValueError("Quote not found")
    if quote.status != "draft":
        raise ValueError(f"Cannot submit quote in status '{quote.status}'")
    quote.status = "submitted"
    quote.submitted_at = datetime.now(UTC)
    quote.content_hash = _compute_content_hash(quote)
    await db.flush()
    await db.refresh(quote)
    return quote


async def withdraw_quote(db: AsyncSession, quote_id: UUID) -> Quote:
    result = await db.execute(select(Quote).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()
    if not quote:
        raise ValueError("Quote not found")
    if quote.status not in ("draft", "submitted"):
        raise ValueError(f"Cannot withdraw quote in status '{quote.status}'")
    quote.status = "withdrawn"
    await db.flush()
    await db.refresh(quote)
    return quote


async def get_quote_comparison(db: AsyncSession, request_id: UUID) -> dict:
    """Neutral comparison: sorted by submitted_at. NO ranking, NO scoring."""
    result = await db.execute(
        select(Quote, CompanyProfile.company_name)
        .join(CompanyProfile, Quote.company_profile_id == CompanyProfile.id)
        .where(Quote.client_request_id == request_id)
        .where(Quote.status == "submitted")
        .order_by(Quote.submitted_at)
    )
    rows = result.all()
    entries = []
    for quote, company_name in rows:
        entries.append(
            {
                "quote_id": quote.id,
                "company_name": company_name,
                "amount_chf": quote.amount_chf,
                "timeline_weeks": quote.timeline_weeks,
                "includes": quote.includes,
                "excludes": quote.excludes,
                "submitted_at": quote.submitted_at,
            }
        )
    return {"client_request_id": request_id, "quotes": entries}


# ---------------------------------------------------------------------------
# Listing / Detail
# ---------------------------------------------------------------------------


async def list_requests(
    db: AsyncSession,
    *,
    building_id: UUID | None = None,
    requester_org_id: UUID | None = None,
    status: str | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[ClientRequest], int]:
    from sqlalchemy import func

    query = select(ClientRequest)
    count_query = select(func.count()).select_from(ClientRequest)

    if building_id:
        query = query.where(ClientRequest.building_id == building_id)
        count_query = count_query.where(ClientRequest.building_id == building_id)
    if requester_org_id:
        query = query.where(ClientRequest.requester_org_id == requester_org_id)
        count_query = count_query.where(ClientRequest.requester_org_id == requester_org_id)
    if status:
        query = query.where(ClientRequest.status == status)
        count_query = count_query.where(ClientRequest.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(ClientRequest.created_at.desc()).offset((page - 1) * size).limit(size)
    items = (await db.execute(query)).scalars().all()
    return list(items), total


async def get_request_detail(db: AsyncSession, request_id: UUID) -> ClientRequest | None:
    result = await db.execute(select(ClientRequest).where(ClientRequest.id == request_id))
    return result.scalar_one_or_none()


async def list_quotes_for_request(db: AsyncSession, request_id: UUID) -> list[Quote]:
    result = await db.execute(select(Quote).where(Quote.client_request_id == request_id).order_by(Quote.created_at))
    return list(result.scalars().all())


async def list_documents_for_request(db: AsyncSession, request_id: UUID) -> list[RequestDocument]:
    result = await db.execute(
        select(RequestDocument)
        .where(RequestDocument.client_request_id == request_id)
        .order_by(RequestDocument.created_at)
    )
    return list(result.scalars().all())


async def list_invitations_for_request(db: AsyncSession, request_id: UUID) -> list[RequestInvitation]:
    result = await db.execute(
        select(RequestInvitation)
        .where(RequestInvitation.client_request_id == request_id)
        .order_by(RequestInvitation.created_at)
    )
    return list(result.scalars().all())
