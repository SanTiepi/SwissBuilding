"""Audit trail export API — download filtered audit logs."""

from datetime import datetime
from io import BytesIO, StringIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.audit_export import (
    AuditExportFilter,
    AuditExportFormat,
    AuditExportRequest,
    AuditExportResult,
)
from app.services.audit_export_service import count_audit_records, export_audit_trail

router = APIRouter()


def _require_admin_or_authority(
    current_user: User = Depends(require_permission("audit_logs", "read")),
) -> User:
    """Ensure the user is admin or authority."""
    if current_user.role not in ("admin", "authority"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or authority roles can export audit logs.",
        )
    return current_user


@router.post("/audit-logs/export", response_model=AuditExportResult)
async def export_audit_logs(
    request: AuditExportRequest,
    current_user: User = Depends(_require_admin_or_authority),
    db: AsyncSession = Depends(get_db),
):
    """Export audit logs with filters in the requested format."""
    return await export_audit_trail(
        db,
        filters=request.filters,
        format=request.format,
        include_details=request.include_details,
    )


@router.post("/audit-logs/export/count")
async def count_export_records(
    filters: AuditExportFilter,
    current_user: User = Depends(_require_admin_or_authority),
    db: AsyncSession = Depends(get_db),
):
    """Count audit log records matching the given filters (preview before export)."""
    count = await count_audit_records(db, filters)
    return {"count": count}


@router.get("/audit-logs/export/download")
async def download_audit_logs(
    format: AuditExportFormat = Query(AuditExportFormat.csv),
    building_id: UUID | None = Query(None),
    user_id: UUID | None = Query(None),
    action_type: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    resource_type: str | None = Query(None),
    include_details: bool = Query(True),
    current_user: User = Depends(_require_admin_or_authority),
    db: AsyncSession = Depends(get_db),
):
    """Download audit logs as a file with proper Content-Type and Content-Disposition."""
    filters = AuditExportFilter(
        building_id=building_id,
        user_id=user_id,
        action_type=action_type,
        date_from=date_from,
        date_to=date_to,
        resource_type=resource_type,
    )

    result = await export_audit_trail(
        db,
        filters=filters,
        format=format,
        include_details=include_details,
    )

    content_type_map = {
        "csv": "text/csv; charset=utf-8",
        "json": "application/json; charset=utf-8",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    content_type = content_type_map.get(result.format, "application/octet-stream")

    # For XLSX (binary), decode base64; for text formats, use raw content
    if result.format == "xlsx" and result.filename.endswith(".xlsx"):
        import base64

        binary_content = base64.b64decode(result.content)
        stream = BytesIO(binary_content)
    else:
        stream = StringIO(result.content)

    return StreamingResponse(
        stream,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )
