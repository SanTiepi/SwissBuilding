"""Service for exporting audit trail data in CSV, JSON, and XLSX formats."""

import base64
import csv
import io
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_export import AuditExportFilter, AuditExportFormat, AuditExportResult


def _apply_filters(stmt, filters: AuditExportFilter):
    """Apply export filters to a SQLAlchemy statement."""
    if filters.user_id is not None:
        stmt = stmt.where(AuditLog.user_id == filters.user_id)
    if filters.action_type is not None:
        stmt = stmt.where(AuditLog.action == filters.action_type)
    if filters.resource_type is not None:
        stmt = stmt.where(AuditLog.entity_type == filters.resource_type)
    if filters.date_from is not None:
        stmt = stmt.where(AuditLog.timestamp >= filters.date_from)
    if filters.date_to is not None:
        stmt = stmt.where(AuditLog.timestamp <= filters.date_to)
    # building_id: AuditLog has no direct building_id column,
    # but details JSON may contain it. We filter via entity_type + entity_id pattern
    # or check details->building_id if present.
    # For simplicity and performance, we filter on entity_type='building' + entity_id
    if filters.building_id is not None:
        stmt = stmt.where(AuditLog.entity_type == "building").where(AuditLog.entity_id == filters.building_id)
    return stmt


async def count_audit_records(db: AsyncSession, filters: AuditExportFilter) -> int:
    """Count audit log records matching the given filters."""
    stmt = select(func.count()).select_from(AuditLog)
    stmt = _apply_filters(stmt, filters)
    result = await db.execute(stmt)
    return result.scalar() or 0


async def export_audit_trail(
    db: AsyncSession,
    filters: AuditExportFilter,
    format: AuditExportFormat,
    include_details: bool = True,
) -> AuditExportResult:
    """Export audit trail data in the requested format."""
    # Query logs
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())
    stmt = _apply_filters(stmt, filters)
    result = await db.execute(stmt)
    logs = list(result.scalars().all())

    # Enrich with user emails
    user_ids = {log.user_id for log in logs if log.user_id is not None}
    user_map: dict[UUID, str] = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in users_result.scalars().all():
            user_map[u.id] = u.email

    # Build rows
    rows = []
    for log in logs:
        row = {
            "timestamp": log.timestamp.isoformat() if log.timestamp else "",
            "user_email": user_map.get(log.user_id, str(log.user_id) if log.user_id else ""),
            "action_type": log.action or "",
            "resource_type": log.entity_type or "",
            "resource_id": str(log.entity_id) if log.entity_id else "",
            "building_id": "",
        }
        if include_details:
            row["details"] = json.dumps(log.details) if log.details else ""
        # If entity_type is building, populate building_id
        if log.entity_type == "building" and log.entity_id:
            row["building_id"] = str(log.entity_id)
        rows.append(row)

    # Generate filename
    building_part = str(filters.building_id) if filters.building_id else "all"
    date_str = datetime.now(UTC).strftime("%Y%m%d")

    if format == AuditExportFormat.csv:
        content = _to_csv(rows, include_details)
        filename = f"audit-export-{date_str}-{building_part}.csv"
    elif format == AuditExportFormat.json:
        content = json.dumps(rows, ensure_ascii=False, indent=2)
        filename = f"audit-export-{date_str}-{building_part}.json"
    elif format == AuditExportFormat.xlsx:
        content, is_real_xlsx = _to_xlsx(rows, include_details)
        ext = "xlsx" if is_real_xlsx else "csv"
        filename = f"audit-export-{date_str}-{building_part}.{ext}"
    else:
        content = _to_csv(rows, include_details)
        filename = f"audit-export-{date_str}-{building_part}.csv"

    return AuditExportResult(
        total_records=len(logs),
        format=format.value,
        filename=filename,
        content=content,
        generated_at=datetime.now(UTC),
    )


def _to_csv(rows: list[dict], include_details: bool) -> str:
    """Convert rows to CSV string."""
    if not rows:
        headers = ["timestamp", "user_email", "action_type", "resource_type", "resource_id", "building_id"]
        if include_details:
            headers.append("details")
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        return output.getvalue()

    headers = list(rows[0].keys())
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _to_xlsx(rows: list[dict], include_details: bool) -> tuple[str, bool]:
    """Convert rows to XLSX (base64-encoded) or fall back to CSV.

    Returns (content, is_real_xlsx).
    """
    try:
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Audit Export"

        headers = ["timestamp", "user_email", "action_type", "resource_type", "resource_id", "building_id"]
        if include_details:
            headers.append("details")

        ws.append(headers)
        for row in rows:
            ws.append([row.get(h, "") for h in headers])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("ascii"), True
    except ImportError:
        # openpyxl not available — fall back to CSV
        return _to_csv(rows, include_details), False
