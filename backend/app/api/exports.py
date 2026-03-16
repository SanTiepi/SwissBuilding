from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.export_job import ExportJob
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.export_job import ExportJobCreate, ExportJobRead
from app.services.audit_service import log_action

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ExportJobRead])
async def list_exports(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    current_user: User = Depends(require_permission("exports", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List export jobs for the current user."""
    query = select(ExportJob)

    # Non-admin users only see their own exports
    if current_user.role != "admin":
        query = query.where(ExportJob.requested_by == current_user.id)

    if status:
        query = query.where(ExportJob.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(ExportJob.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    pages = (total + size - 1) // size if total > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.post("", response_model=ExportJobRead, status_code=201)
async def create_export(
    data: ExportJobCreate,
    current_user: User = Depends(require_permission("exports", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new export job (status=queued)."""
    export_job = ExportJob(
        type=data.type,
        building_id=data.building_id,
        organization_id=data.organization_id,
        status="queued",
        requested_by=current_user.id,
    )
    db.add(export_job)
    await db.commit()
    await db.refresh(export_job)
    await log_action(db, current_user.id, "create_export", "export_job", export_job.id)
    return ExportJobRead.model_validate(export_job)


@router.get("/{export_id}", response_model=ExportJobRead)
async def get_export(
    export_id: UUID,
    current_user: User = Depends(require_permission("exports", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single export job. Only own exports unless admin."""
    result = await db.execute(select(ExportJob).where(ExportJob.id == export_id))
    export_job = result.scalar_one_or_none()
    if not export_job:
        raise HTTPException(status_code=404, detail="Export job not found")

    # Non-admin users can only see their own exports
    if current_user.role != "admin" and export_job.requested_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return ExportJobRead.model_validate(export_job)


@router.delete("/{export_id}", status_code=204)
async def cancel_export(
    export_id: UUID,
    current_user: User = Depends(require_permission("exports", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an export job (only if status=queued). Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.execute(select(ExportJob).where(ExportJob.id == export_id))
    export_job = result.scalar_one_or_none()
    if not export_job:
        raise HTTPException(status_code=404, detail="Export job not found")

    if export_job.status != "queued":
        raise HTTPException(status_code=400, detail="Only queued exports can be cancelled")

    await db.delete(export_job)
    await db.commit()
    await log_action(db, current_user.id, "cancel_export", "export_job", export_id)
