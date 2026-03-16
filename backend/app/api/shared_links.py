"""Audience-bounded sharing link API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building import Building
from app.models.organization import Organization
from app.models.user import User
from app.schemas.shared_link import (
    SharedLinkCreate,
    SharedLinkList,
    SharedLinkRead,
    SharedLinkValidation,
    SharedPassportResponse,
)
from app.services import shared_link_service as svc
from app.services.passport_service import get_passport_summary

router = APIRouter()


@router.post(
    "/shared-links",
    response_model=SharedLinkRead,
    status_code=201,
)
async def create_shared_link_endpoint(
    data: SharedLinkCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new audience-bounded sharing link."""
    link = await svc.create_shared_link(
        db,
        resource_type=data.resource_type,
        resource_id=data.resource_id,
        audience_type=data.audience_type,
        created_by=current_user.id,
        organization_id=current_user.organization_id,
        audience_email=data.audience_email,
        expires_in_days=data.expires_in_days,
        max_views=data.max_views,
        allowed_sections=data.allowed_sections,
    )
    await db.commit()
    await db.refresh(link)
    return link


@router.get(
    "/shared-links",
    response_model=SharedLinkList,
)
async def list_shared_links_endpoint(
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List sharing links created by the current user."""
    items = await svc.list_shared_links(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
        created_by=current_user.id,
    )
    return {"items": items, "count": len(items)}


@router.get(
    "/shared-links/{link_id}",
    response_model=SharedLinkRead,
)
async def get_shared_link_endpoint(
    link_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific sharing link."""
    link = await svc.get_shared_link(db, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Shared link not found")
    return link


@router.delete(
    "/shared-links/{link_id}",
    response_model=SharedLinkRead,
)
async def revoke_shared_link_endpoint(
    link_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a sharing link."""
    try:
        link = await svc.revoke_shared_link(db, link_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from None
    if not link:
        raise HTTPException(status_code=404, detail="Shared link not found")
    await db.commit()
    await db.refresh(link)
    return link


@router.get(
    "/shared/{token}",
    response_model=SharedLinkValidation,
)
async def access_shared_link_endpoint(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Validate and access a shared link (public, no auth required)."""
    link = await svc.record_access(db, token)
    if not link:
        return SharedLinkValidation(is_valid=False)
    await db.commit()
    return SharedLinkValidation(
        is_valid=True,
        resource_type=link.resource_type,
        resource_id=link.resource_id,
        allowed_sections=link.allowed_sections,
        audience_type=link.audience_type,
    )


@router.get(
    "/shared/{token}/passport",
    response_model=SharedPassportResponse,
)
async def shared_passport_endpoint(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint: get building passport via a valid shared link."""
    link = await svc.validate_shared_link(db, token)
    if not link:
        raise HTTPException(status_code=404, detail="Link invalid or expired")

    if link.resource_type not in ("building", "passport"):
        raise HTTPException(status_code=400, detail="Link does not share a building passport")

    # Fetch building info
    result = await db.execute(select(Building).where(Building.id == link.resource_id))
    building = result.scalar_one_or_none()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    # Fetch passport summary
    passport = await get_passport_summary(db, link.resource_id)
    if passport is None:
        raise HTTPException(status_code=404, detail="Passport data not available")

    # Fetch organization name
    org_name: str | None = None
    if link.organization_id:
        org_result = await db.execute(select(Organization.name).where(Organization.id == link.organization_id))
        org_name = org_result.scalar_one_or_none()

    return SharedPassportResponse(
        building_address=building.address,
        building_city=building.city,
        building_canton=building.canton,
        building_postal_code=building.postal_code,
        passport=passport,
        shared_by_org=org_name,
        expires_at=link.expires_at,
        audience_type=link.audience_type,
    )
