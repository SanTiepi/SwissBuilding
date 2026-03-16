"""
SwissBuildingOS - Audit Service

Provides audit logging for all significant user actions.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_action(
    db: AsyncSession,
    user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """
    Create an audit log entry recording a user action.

    Args:
        db: Async database session.
        user_id: The user who performed the action (None for system actions).
        action: Action name (e.g. 'create', 'update', 'delete', 'login').
        entity_type: Type of entity affected (e.g. 'building', 'diagnostic').
        entity_id: ID of the affected entity (None for non-entity actions).
        details: Optional JSON-serializable dict with extra context.
        ip_address: Optional IP address of the request origin.

    Returns:
        The created AuditLog entry.
    """
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(audit_log)
    await db.commit()
    await db.refresh(audit_log)

    return audit_log


async def list_audit_logs(
    db: AsyncSession,
    page: int,
    size: int,
    entity_type: str | None = None,
    user_id: UUID | None = None,
) -> tuple[list[AuditLog], int]:
    """
    List audit log entries with pagination and optional filters.

    Returns:
        A tuple of (audit_logs_list, total_count).
    """
    base = select(AuditLog)

    if entity_type is not None:
        base = base.where(AuditLog.entity_type == entity_type)
    if user_id is not None:
        base = base.where(AuditLog.user_id == user_id)

    # Total count
    count_stmt = select(func.count()).select_from(base.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginated results, newest first
    offset = (page - 1) * size
    data_stmt = base.order_by(AuditLog.timestamp.desc()).offset(offset).limit(size)
    result = await db.execute(data_stmt)
    logs = list(result.scalars().all())

    return logs, total
