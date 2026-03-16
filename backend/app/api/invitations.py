import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.invitation import Invitation
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.invitation import InvitationAccept, InvitationCreate, InvitationRead
from app.services.audit_service import log_action

router = APIRouter()


def _utcnow() -> datetime:
    """Return naive UTC datetime for DB compatibility (SQLite stores naive)."""
    return datetime.now(UTC).replace(tzinfo=None)


@router.get("", response_model=PaginatedResponse[InvitationRead])
async def list_invitations(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permission("invitations", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List all invitations (admin only) with pagination."""
    count_result = await db.execute(select(func.count()).select_from(Invitation))
    total = count_result.scalar() or 0

    offset = (page - 1) * size
    result = await db.execute(select(Invitation).order_by(Invitation.created_at.desc()).offset(offset).limit(size))
    invitations = result.scalars().all()
    pages = (total + size - 1) // size

    return {
        "items": [InvitationRead.model_validate(inv) for inv in invitations],
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.post("", response_model=InvitationRead, status_code=201)
async def create_invitation(
    data: InvitationCreate,
    current_user: User = Depends(require_permission("invitations", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new invitation (admin only)."""
    # Check if a pending invitation already exists for this email
    existing = await db.execute(
        select(Invitation).where(Invitation.email == data.email, Invitation.status == "pending")
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A pending invitation already exists for this email")

    invitation = Invitation(
        email=data.email,
        role=data.role,
        organization_id=data.organization_id,
        status="pending",
        token=secrets.token_urlsafe(32),
        invited_by=current_user.id,
        expires_at=_utcnow() + timedelta(days=7),
    )

    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    await log_action(db, current_user.id, "create", "invitation", invitation.id)
    return InvitationRead.model_validate(invitation)


@router.get("/{invitation_id}", response_model=InvitationRead)
async def get_invitation(
    invitation_id: UUID,
    current_user: User = Depends(require_permission("invitations", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single invitation (admin only)."""
    result = await db.execute(select(Invitation).where(Invitation.id == invitation_id))
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return InvitationRead.model_validate(invitation)


@router.delete("/{invitation_id}", status_code=204)
async def revoke_invitation(
    invitation_id: UUID,
    current_user: User = Depends(require_permission("invitations", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an invitation (admin only). Sets status to 'revoked'."""
    result = await db.execute(select(Invitation).where(Invitation.id == invitation_id))
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot revoke invitation with status '{invitation.status}'")

    invitation.status = "revoked"
    await db.commit()
    await log_action(db, current_user.id, "revoke", "invitation", invitation_id)


@router.post("/accept", status_code=201)
async def accept_invitation(
    data: InvitationAccept,
    db: AsyncSession = Depends(get_db),
):
    """Accept an invitation and create a user account. No authentication required."""
    result = await db.execute(select(Invitation).where(Invitation.token == data.token))
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid invitation token")

    if invitation.status == "revoked":
        raise HTTPException(status_code=400, detail="This invitation has been revoked")

    if invitation.status == "accepted":
        raise HTTPException(status_code=400, detail="This invitation has already been accepted")

    if invitation.expires_at < _utcnow():
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="This invitation has expired")

    if invitation.status != "pending":
        raise HTTPException(status_code=400, detail=f"Invalid invitation status: {invitation.status}")

    # Create user via auth service
    from app.services.auth_service import register_user

    try:
        user = await register_user(
            db,
            invitation.email,
            data.password,
            data.first_name,
            data.last_name,
            invitation.role,
            data.language,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    invitation.status = "accepted"
    invitation.accepted_at = _utcnow()
    await db.commit()

    await log_action(db, user.id, "accept", "invitation", invitation.id)

    return {"message": "Invitation accepted", "user_id": str(user.id)}
