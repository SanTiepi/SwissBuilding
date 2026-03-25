"""Adoption Loops — Rollout service: delegated access grants + privileged access audit."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delegated_access import DelegatedAccessGrant, PrivilegedAccessEvent


async def create_grant(
    db: AsyncSession,
    building_id: UUID,
    data: dict,
    granted_by_user_id: UUID,
    ip_address: str | None = None,
) -> DelegatedAccessGrant:
    """Create a delegated access grant and log the event."""
    grant = DelegatedAccessGrant(
        building_id=building_id,
        granted_by_user_id=granted_by_user_id,
        **data,
    )
    db.add(grant)
    await db.flush()
    await db.refresh(grant)

    # Auto-log the privileged access event
    await log_privileged_event(
        db,
        user_id=granted_by_user_id,
        action_type="grant_created",
        building_id=building_id,
        target_entity_type="delegated_access_grant",
        target_entity_id=grant.id,
        details={"grant_type": grant.grant_type, "scope": grant.scope},
        ip_address=ip_address,
    )
    return grant


async def revoke_grant(
    db: AsyncSession,
    grant: DelegatedAccessGrant,
    revoked_by_user_id: UUID,
    ip_address: str | None = None,
) -> DelegatedAccessGrant:
    """Revoke a delegated access grant and log the event."""
    from datetime import UTC, datetime

    grant.is_active = False
    grant.revoked_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(grant)

    await log_privileged_event(
        db,
        user_id=revoked_by_user_id,
        action_type="grant_revoked",
        building_id=grant.building_id,
        target_entity_type="delegated_access_grant",
        target_entity_id=grant.id,
        details={"grant_type": grant.grant_type},
        ip_address=ip_address,
    )
    return grant


async def list_grants(
    db: AsyncSession,
    building_id: UUID,
    *,
    active_only: bool = True,
) -> list[DelegatedAccessGrant]:
    """List access grants for a building."""
    query = select(DelegatedAccessGrant).where(DelegatedAccessGrant.building_id == building_id)
    if active_only:
        query = query.where(DelegatedAccessGrant.is_active.is_(True))
    query = query.order_by(DelegatedAccessGrant.granted_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_grant(db: AsyncSession, grant_id: UUID) -> DelegatedAccessGrant | None:
    """Fetch a single grant by ID."""
    result = await db.execute(select(DelegatedAccessGrant).where(DelegatedAccessGrant.id == grant_id))
    return result.scalar_one_or_none()


async def check_delegated_access(
    db: AsyncSession,
    building_id: UUID,
    *,
    org_id: UUID | None = None,
    email: str | None = None,
) -> DelegatedAccessGrant | None:
    """Check whether an org or email has an active grant on a building."""
    query = (
        select(DelegatedAccessGrant)
        .where(DelegatedAccessGrant.building_id == building_id)
        .where(DelegatedAccessGrant.is_active.is_(True))
    )
    if org_id:
        query = query.where(DelegatedAccessGrant.granted_to_org_id == org_id)
    elif email:
        query = query.where(DelegatedAccessGrant.granted_to_email == email)
    else:
        return None
    result = await db.execute(query.limit(1))
    return result.scalar_one_or_none()


async def log_privileged_event(
    db: AsyncSession,
    user_id: UUID,
    action_type: str,
    building_id: UUID | None = None,
    target_entity_type: str | None = None,
    target_entity_id: UUID | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> PrivilegedAccessEvent:
    """Record a privileged access event."""
    event = PrivilegedAccessEvent(
        user_id=user_id,
        building_id=building_id,
        action_type=action_type,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


async def list_privileged_events(
    db: AsyncSession,
    *,
    building_id: UUID | None = None,
    user_id: UUID | None = None,
    page: int = 1,
    size: int = 50,
) -> tuple[list[PrivilegedAccessEvent], int]:
    """List privileged access events with optional filters."""
    query = select(PrivilegedAccessEvent)
    count_query = select(func.count()).select_from(PrivilegedAccessEvent)

    if building_id:
        query = query.where(PrivilegedAccessEvent.building_id == building_id)
        count_query = count_query.where(PrivilegedAccessEvent.building_id == building_id)
    if user_id:
        query = query.where(PrivilegedAccessEvent.user_id == user_id)
        count_query = count_query.where(PrivilegedAccessEvent.user_id == user_id)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(PrivilegedAccessEvent.created_at.desc()).offset((page - 1) * size).limit(size)
    items = (await db.execute(query)).scalars().all()
    return list(items), total
