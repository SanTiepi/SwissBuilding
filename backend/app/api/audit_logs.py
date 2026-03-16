"""Audit logs API — read-only endpoints for governance."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogRead])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user_id: str | None = None,
    entity_type: str | None = None,
    action: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    current_user: User = Depends(require_permission("audit_logs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List audit log entries with filters and pagination (admin/authority only)."""
    base = select(AuditLog)
    count_base = select(func.count()).select_from(AuditLog)

    if user_id is not None:
        uid = UUID(user_id)
        base = base.where(AuditLog.user_id == uid)
        count_base = count_base.where(AuditLog.user_id == uid)

    if entity_type is not None:
        base = base.where(AuditLog.entity_type == entity_type)
        count_base = count_base.where(AuditLog.entity_type == entity_type)

    if action is not None:
        base = base.where(AuditLog.action == action)
        count_base = count_base.where(AuditLog.action == action)

    if date_from is not None:
        base = base.where(AuditLog.timestamp >= date_from)
        count_base = count_base.where(AuditLog.timestamp >= date_from)

    if date_to is not None:
        base = base.where(AuditLog.timestamp <= date_to)
        count_base = count_base.where(AuditLog.timestamp <= date_to)

    # Total count
    total_result = await db.execute(count_base)
    total = total_result.scalar() or 0
    pages = (total + size - 1) // size if total > 0 else 0

    # Paginated, newest first
    offset = (page - 1) * size
    data_stmt = base.order_by(AuditLog.timestamp.desc()).offset(offset).limit(size)
    result = await db.execute(data_stmt)
    logs = list(result.scalars().all())

    # Enrich with user info
    user_ids = {log.user_id for log in logs if log.user_id is not None}
    user_map: dict[UUID, User] = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in users_result.scalars().all():
            user_map[u.id] = u

    items = []
    for log in logs:
        u = user_map.get(log.user_id) if log.user_id else None
        items.append(
            AuditLogRead(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                details=log.details,
                ip_address=log.ip_address,
                timestamp=log.timestamp,
                user_email=u.email if u else None,
                user_name=f"{u.first_name} {u.last_name}" if u else None,
            )
        )

    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}
