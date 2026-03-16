from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_permission
from app.models.organization import Organization
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.organization import OrganizationCreate, OrganizationRead, OrganizationUpdate
from app.schemas.user import UserRead
from app.services.audit_service import log_action

router = APIRouter()


def _org_to_read(org: Organization) -> OrganizationRead:
    """Convert an Organization ORM object to OrganizationRead with member_count."""
    data = OrganizationRead.model_validate(org)
    data.member_count = len(org.members) if org.members else 0
    return data


@router.get("", response_model=PaginatedResponse[OrganizationRead])
async def list_organizations(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    type: str | None = Query(None, description="Filter by organization type"),
    current_user: User = Depends(require_permission("organizations", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List all organizations with pagination and optional type filter."""
    base = select(Organization)
    if type is not None:
        base = base.where(Organization.type == type)

    # Count total
    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar() or 0

    # Fetch page with members eager-loaded
    offset = (page - 1) * size
    result = await db.execute(
        base.options(selectinload(Organization.members))
        .order_by(Organization.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    orgs = result.scalars().all()
    pages = (total + size - 1) // size

    return {
        "items": [_org_to_read(org) for org in orgs],
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.post("", response_model=OrganizationRead, status_code=201)
async def create_organization(
    data: OrganizationCreate,
    current_user: User = Depends(require_permission("organizations", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new organization (admin only)."""
    org = Organization(**data.model_dump())
    db.add(org)
    await db.commit()
    await db.refresh(org, attribute_names=["members"])
    await log_action(db, current_user.id, "create", "organization", org.id)
    return _org_to_read(org)


@router.get("/{org_id}", response_model=OrganizationRead)
async def get_organization(
    org_id: UUID,
    current_user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single organization by ID."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id).options(selectinload(Organization.members))
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _org_to_read(org)


@router.put("/{org_id}", response_model=OrganizationRead)
async def update_organization(
    org_id: UUID,
    data: OrganizationUpdate,
    current_user: User = Depends(require_permission("organizations", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an organization (admin only)."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id).options(selectinload(Organization.members))
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)

    await db.commit()
    await db.refresh(org, attribute_names=["members"])
    await log_action(db, current_user.id, "update", "organization", org_id)
    return _org_to_read(org)


@router.delete("/{org_id}", status_code=204)
async def delete_organization(
    org_id: UUID,
    current_user: User = Depends(require_permission("organizations", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete an organization (admin only). Fails if the organization has members."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id).options(selectinload(Organization.members))
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if org.members:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete organization with existing members. Remove all members first.",
        )

    await db.delete(org)
    await db.commit()
    await log_action(db, current_user.id, "delete", "organization", org_id)


@router.get("/{org_id}/members", response_model=list[UserRead])
async def list_organization_members(
    org_id: UUID,
    current_user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all members of an organization."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    members_result = await db.execute(
        select(User).where(User.organization_id == org_id).order_by(User.last_name, User.first_name)
    )
    members = members_result.scalars().all()
    return [UserRead.model_validate(m) for m in members]
