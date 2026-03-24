"""BatiConnect — Workspace membership service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User
from app.models.workspace_membership import DEFAULT_SCOPE_BY_ROLE, WORKSPACE_ROLES, WorkspaceMembership


async def add_member(
    db: AsyncSession,
    building_id: UUID,
    data: dict,
    granted_by: UUID,
) -> WorkspaceMembership:
    """Add a workspace member to a building."""
    role = data.get("role", "viewer")
    if role not in WORKSPACE_ROLES:
        msg = f"Invalid workspace role: {role}"
        raise ValueError(msg)

    # Apply default scope if none provided
    access_scope = data.get("access_scope")
    if access_scope is None:
        access_scope = DEFAULT_SCOPE_BY_ROLE.get(role, DEFAULT_SCOPE_BY_ROLE["viewer"])
    elif hasattr(access_scope, "model_dump"):
        access_scope = access_scope.model_dump()

    membership = WorkspaceMembership(
        building_id=building_id,
        organization_id=data.get("organization_id"),
        user_id=data.get("user_id"),
        role=role,
        access_scope=access_scope,
        granted_by_user_id=granted_by,
        expires_at=data.get("expires_at"),
        notes=data.get("notes"),
    )
    db.add(membership)
    await db.flush()
    await db.refresh(membership)
    return membership


async def remove_member(db: AsyncSession, membership_id: UUID) -> WorkspaceMembership | None:
    """Soft-delete a workspace membership (set is_active=False)."""
    result = await db.execute(select(WorkspaceMembership).where(WorkspaceMembership.id == membership_id))
    membership = result.scalar_one_or_none()
    if membership is None:
        return None
    membership.is_active = False
    await db.flush()
    await db.refresh(membership)
    return membership


async def update_member_scope(db: AsyncSession, membership_id: UUID, data: dict) -> WorkspaceMembership | None:
    """Update a workspace membership's role, scope, or other fields."""
    result = await db.execute(select(WorkspaceMembership).where(WorkspaceMembership.id == membership_id))
    membership = result.scalar_one_or_none()
    if membership is None:
        return None

    for key, value in data.items():
        if key == "access_scope" and hasattr(value, "model_dump"):
            value = value.model_dump()
        setattr(membership, key, value)

    await db.flush()
    await db.refresh(membership)
    return membership


async def get_member(db: AsyncSession, membership_id: UUID) -> WorkspaceMembership | None:
    """Get a single workspace membership by ID."""
    result = await db.execute(select(WorkspaceMembership).where(WorkspaceMembership.id == membership_id))
    return result.scalar_one_or_none()


async def get_members(db: AsyncSession, building_id: UUID, *, active_only: bool = True) -> list[WorkspaceMembership]:
    """List workspace memberships for a building."""
    query = select(WorkspaceMembership).where(WorkspaceMembership.building_id == building_id)
    if active_only:
        query = query.where(WorkspaceMembership.is_active.is_(True))
    query = query.order_by(WorkspaceMembership.granted_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def check_access(db: AsyncSession, user_id: UUID, building_id: UUID, resource: str) -> bool:
    """Check whether a user has access to a specific resource on a building.

    Checks both direct user memberships and memberships through their organization.
    The resource parameter maps to an access_scope key (e.g. 'documents', 'financial').
    """
    now = datetime.now(UTC)

    # Find the user's organization_id
    user_result = await db.execute(select(User.organization_id).where(User.id == user_id))
    user_org_id = user_result.scalar_one_or_none()

    # Build query: active memberships for this building matching user or org
    query = select(WorkspaceMembership).where(
        WorkspaceMembership.building_id == building_id,
        WorkspaceMembership.is_active.is_(True),
    )

    # Match by user_id OR organization_id
    from sqlalchemy import or_

    conditions = [WorkspaceMembership.user_id == user_id]
    if user_org_id is not None:
        conditions.append(WorkspaceMembership.organization_id == user_org_id)
    query = query.where(or_(*conditions))

    result = await db.execute(query)
    memberships = result.scalars().all()

    for m in memberships:
        # Skip expired memberships (handle both tz-aware and naive datetimes)
        if m.expires_at is not None:
            expires = m.expires_at if m.expires_at.tzinfo else m.expires_at.replace(tzinfo=UTC)
            if expires < now:
                continue

        # Check scope
        scope = m.access_scope or {}
        if scope.get(resource, False):
            return True

    return False


async def get_member_count(db: AsyncSession, building_id: UUID) -> int:
    """Count active workspace members for a building."""
    query = (
        select(func.count())
        .select_from(WorkspaceMembership)
        .where(
            WorkspaceMembership.building_id == building_id,
            WorkspaceMembership.is_active.is_(True),
        )
    )
    result = await db.execute(query)
    return result.scalar() or 0


async def enrich_membership(db: AsyncSession, membership: WorkspaceMembership) -> dict:
    """Convert a WorkspaceMembership ORM instance to a dict with display fields."""
    data = {c.key: getattr(membership, c.key) for c in membership.__table__.columns}

    # Resolve organization name
    if membership.organization_id:
        result = await db.execute(select(Organization.name).where(Organization.id == membership.organization_id))
        data["organization_name"] = result.scalar_one_or_none()
    else:
        data["organization_name"] = None

    # Resolve user display name
    if membership.user_id:
        result = await db.execute(select(User.first_name, User.last_name).where(User.id == membership.user_id))
        row = result.one_or_none()
        data["user_display_name"] = f"{row[0]} {row[1]}" if row else None
    else:
        data["user_display_name"] = None

    # Resolve granted_by display name
    result = await db.execute(select(User.first_name, User.last_name).where(User.id == membership.granted_by_user_id))
    row = result.one_or_none()
    data["granted_by_display_name"] = f"{row[0]} {row[1]}" if row else None

    return data


async def enrich_memberships(db: AsyncSession, memberships: list[WorkspaceMembership]) -> list[dict]:
    """Enrich a list of memberships with display fields."""
    return [await enrich_membership(db, m) for m in memberships]
