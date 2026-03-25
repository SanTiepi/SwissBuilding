"""Adoption Loops — Rollout API: access grants, privileged events, embed tokens."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.package_preset import EmbedPublicView, EmbedTokenCreate, EmbedTokenRead
from app.schemas.rollout import GrantCreate, GrantRead, PrivilegedAccessEventRead
from app.services.package_preset_service import (
    create_embed_token,
    get_viewer_profile,
    record_embed_view,
    validate_embed_token,
)
from app.services.rollout_service import (
    create_grant,
    get_grant,
    list_grants,
    list_privileged_events,
    revoke_grant,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.post(
    "/buildings/{building_id}/access-grants",
    response_model=GrantRead,
    status_code=201,
)
async def create_grant_endpoint(
    building_id: UUID,
    payload: GrantCreate,
    request: Request,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    data = payload.model_dump(exclude_unset=True)
    ip = request.client.host if request.client else None
    grant = await create_grant(db, building_id, data, granted_by_user_id=current_user.id, ip_address=ip)
    await db.commit()
    return grant


@router.get(
    "/buildings/{building_id}/access-grants",
    response_model=list[GrantRead],
)
async def list_grants_endpoint(
    building_id: UUID,
    active_only: bool = Query(True),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await list_grants(db, building_id, active_only=active_only)


@router.delete(
    "/access-grants/{grant_id}",
    response_model=GrantRead,
)
async def revoke_grant_endpoint(
    grant_id: UUID,
    request: Request,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    grant = await get_grant(db, grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    ip = request.client.host if request.client else None
    revoked = await revoke_grant(db, grant, revoked_by_user_id=current_user.id, ip_address=ip)
    await db.commit()
    return revoked


@router.get(
    "/privileged-access-events",
    response_model=PaginatedResponse[PrivilegedAccessEventRead],
)
async def list_events_endpoint(
    building_id: UUID | None = None,
    user_id: UUID | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_permission("audit_logs", "list")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await list_privileged_events(db, building_id=building_id, user_id=user_id, page=page, size=size)
    pages = (total + size - 1) // size if total > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


@router.post(
    "/buildings/{building_id}/embed-tokens",
    response_model=EmbedTokenRead,
    status_code=201,
)
async def create_embed_token_endpoint(
    building_id: UUID,
    payload: EmbedTokenCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    embed = await create_embed_token(
        db,
        building_id,
        created_by_user_id=current_user.id,
        viewer_profile_id=payload.viewer_profile_id,
        scope=payload.scope,
    )
    await db.commit()
    return embed


@router.get(
    "/embed/{token}",
    response_model=EmbedPublicView,
)
async def access_embed_endpoint(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — no auth required. Validates token and returns bounded view."""
    embed = await validate_embed_token(db, token)
    if not embed:
        raise HTTPException(status_code=404, detail="Token invalid or expired")

    await record_embed_view(db, embed)
    await db.commit()

    scope = embed.scope or {}
    sections = scope.get("sections", [])

    viewer_type = None
    requires_ack = False
    if embed.viewer_profile_id:
        profile = await get_viewer_profile(db, embed.viewer_profile_id)
        if profile:
            viewer_type = profile.viewer_type
            requires_ack = profile.requires_acknowledgement

    return EmbedPublicView(
        building_id=embed.building_id,
        sections=sections,
        viewer_type=viewer_type,
        requires_acknowledgement=requires_ack,
    )
