"""Audience-bounded sharing link service."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shared_link import SharedLink


async def create_shared_link(
    db: AsyncSession,
    resource_type: str,
    resource_id: UUID,
    audience_type: str,
    created_by: UUID,
    *,
    organization_id: UUID | None = None,
    audience_email: str | None = None,
    expires_in_days: int = 30,
    max_views: int | None = None,
    allowed_sections: list[str] | None = None,
) -> SharedLink:
    """Create a new time-limited sharing link."""
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

    link = SharedLink(
        token=token,
        resource_type=resource_type,
        resource_id=resource_id,
        created_by=created_by,
        organization_id=organization_id,
        audience_type=audience_type,
        audience_email=audience_email,
        expires_at=expires_at,
        max_views=max_views,
        allowed_sections=allowed_sections,
    )
    db.add(link)
    return link


async def validate_shared_link(db: AsyncSession, token: str) -> SharedLink | None:
    """Validate a shared link token. Returns the link if valid, None otherwise."""
    result = await db.execute(select(SharedLink).where(SharedLink.token == token))
    link = result.scalar_one_or_none()
    if not link:
        return None
    if not link.is_active:
        return None
    now = datetime.now(UTC)
    expires = link.expires_at if link.expires_at.tzinfo else link.expires_at.replace(tzinfo=UTC)
    if expires < now:
        return None
    if link.max_views is not None and link.view_count >= link.max_views:
        return None
    return link


async def record_access(db: AsyncSession, token: str) -> SharedLink | None:
    """Record an access: increment view_count and update last_accessed_at.

    Returns the link if valid, None otherwise.
    """
    link = await validate_shared_link(db, token)
    if not link:
        return None
    link.view_count = (link.view_count or 0) + 1
    link.last_accessed_at = datetime.now(UTC)
    return link


async def revoke_shared_link(db: AsyncSession, link_id: UUID, user_id: UUID) -> SharedLink | None:
    """Revoke a shared link. Only the creator can revoke."""
    result = await db.execute(select(SharedLink).where(SharedLink.id == link_id))
    link = result.scalar_one_or_none()
    if not link:
        return None
    if link.created_by != user_id:
        raise ValueError("Only the link creator can revoke it")
    link.is_active = False
    return link


async def list_shared_links(
    db: AsyncSession,
    *,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    created_by: UUID | None = None,
    limit: int = 20,
) -> list[SharedLink]:
    """List shared links with optional filters."""
    query = select(SharedLink)
    if resource_type is not None:
        query = query.where(SharedLink.resource_type == resource_type)
    if resource_id is not None:
        query = query.where(SharedLink.resource_id == resource_id)
    if created_by is not None:
        query = query.where(SharedLink.created_by == created_by)
    query = query.order_by(SharedLink.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_shared_link(db: AsyncSession, link_id: UUID) -> SharedLink | None:
    """Get a single shared link by ID."""
    result = await db.execute(select(SharedLink).where(SharedLink.id == link_id))
    return result.scalar_one_or_none()
