"""Pydantic schemas for audit trail export."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditExportFormat(StrEnum):
    csv = "csv"
    json = "json"
    xlsx = "xlsx"


class AuditExportFilter(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID | None = None
    user_id: UUID | None = None
    action_type: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    resource_type: str | None = None


class AuditExportRequest(BaseModel):
    filters: AuditExportFilter = Field(default_factory=AuditExportFilter)
    format: AuditExportFormat = AuditExportFormat.csv
    include_details: bool = True


class AuditExportResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_records: int
    format: str
    filename: str
    content: str
    generated_at: datetime
