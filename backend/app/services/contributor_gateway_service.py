"""BatiConnect — Contributor Gateway service.

Bounded contributor access, submission management, acceptance workflow.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contributor_gateway import (
    ContributorGatewayRequest,
    ContributorReceipt,
    ContributorSubmission,
)


async def create_request(
    db: AsyncSession,
    building_id: UUID,
    contributor_type: str,
    created_by_user_id: UUID,
    *,
    scope_description: str | None = None,
    expires_in_hours: int = 72,
    linked_procedure_id: UUID | None = None,
    linked_remediation_id: UUID | None = None,
) -> ContributorGatewayRequest:
    """Generate access token and create contributor request."""
    access_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(hours=expires_in_hours)

    req = ContributorGatewayRequest(
        building_id=building_id,
        contributor_type=contributor_type,
        scope_description=scope_description,
        access_token=access_token,
        expires_at=expires_at,
        status="open",
        created_by_user_id=created_by_user_id,
        linked_procedure_id=linked_procedure_id,
        linked_remediation_id=linked_remediation_id,
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)
    return req


async def validate_token(db: AsyncSession, token: str) -> ContributorGatewayRequest | None:
    """Check active + not expired."""
    result = await db.execute(
        select(ContributorGatewayRequest).where(
            ContributorGatewayRequest.access_token == token,
            ContributorGatewayRequest.status == "open",
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        return None

    if req.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        req.status = "expired"
        await db.flush()
        return None

    return req


async def submit(
    db: AsyncSession,
    token: str,
    submission_data: dict,
) -> ContributorSubmission:
    """Create ContributorSubmission in pending_review."""
    req = await validate_token(db, token)
    if not req:
        raise ValueError("Invalid or expired contributor token")

    sub = ContributorSubmission(
        request_id=req.id,
        status="pending_review",
        **submission_data,
    )
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    return sub


async def accept_submission(
    db: AsyncSession,
    submission_id: UUID,
    user_id: UUID,
) -> ContributorReceipt:
    """Accept submission: create receipt with hash."""
    sub = await db.get(ContributorSubmission, submission_id)
    if not sub:
        raise ValueError("Submission not found")
    if sub.status != "pending_review":
        raise ValueError("Submission is not pending review")

    sub.status = "accepted"
    sub.reviewed_by_user_id = user_id
    sub.reviewed_at = datetime.now(UTC)

    # Compute receipt hash from submission content
    hash_input = f"{sub.id}-{sub.submission_type}-{sub.created_at}"
    receipt_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    receipt = ContributorReceipt(
        submission_id=submission_id,
        receipt_hash=receipt_hash,
        accepted_at=datetime.now(UTC),
    )
    db.add(receipt)
    await db.flush()
    await db.refresh(receipt)
    return receipt


async def reject_submission(
    db: AsyncSession,
    submission_id: UUID,
    user_id: UUID,
    notes: str | None = None,
) -> ContributorSubmission:
    """Reject submission with optional notes."""
    sub = await db.get(ContributorSubmission, submission_id)
    if not sub:
        raise ValueError("Submission not found")
    if sub.status != "pending_review":
        raise ValueError("Submission is not pending review")

    sub.status = "rejected"
    sub.reviewed_by_user_id = user_id
    sub.reviewed_at = datetime.now(UTC)
    sub.review_notes = notes

    await db.flush()
    await db.refresh(sub)
    return sub


async def list_pending_submissions(db: AsyncSession) -> list[ContributorSubmission]:
    """Admin queue: all pending_review submissions."""
    result = await db.execute(
        select(ContributorSubmission)
        .where(ContributorSubmission.status == "pending_review")
        .order_by(ContributorSubmission.created_at.asc())
    )
    return list(result.scalars().all())


async def list_requests(db: AsyncSession, building_id: UUID | None = None) -> list[ContributorGatewayRequest]:
    """List contributor requests, optionally filtered by building."""
    query = select(ContributorGatewayRequest).order_by(ContributorGatewayRequest.created_at.desc())
    if building_id:
        query = query.where(ContributorGatewayRequest.building_id == building_id)
    result = await db.execute(query)
    return list(result.scalars().all())
