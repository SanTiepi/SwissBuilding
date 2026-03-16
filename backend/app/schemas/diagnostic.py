from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DiagnosticCreate(BaseModel):
    diagnostic_type: str  # asbestos, pcb, lead, hap, radon, full
    diagnostic_context: str = "AvT"
    diagnostician_id: UUID | None = None  # Set from current_user if not provided
    laboratory: str | None = None
    date_inspection: date
    methodology: str | None = None
    summary: str | None = None


class DiagnosticUpdate(BaseModel):
    status: str | None = None
    laboratory: str | None = None
    laboratory_report_number: str | None = None
    date_report: date | None = None
    summary: str | None = None
    conclusion: str | None = None
    methodology: str | None = None
    suva_notification_date: date | None = None
    canton_notification_date: date | None = None


class DiagnosticRead(BaseModel):
    id: UUID
    building_id: UUID
    diagnostic_type: str
    diagnostic_context: str
    status: str
    diagnostician_id: UUID | None
    laboratory: str | None
    laboratory_report_number: str | None
    date_inspection: date
    date_report: date | None
    report_file_path: str | None
    summary: str | None
    conclusion: str | None
    methodology: str | None
    suva_notification_required: bool
    suva_notification_date: date | None
    canton_notification_date: date | None
    created_at: datetime
    updated_at: datetime
    samples: list[SampleRead] = []
    generated_actions_count: int | None = None

    model_config = ConfigDict(from_attributes=True)


# Resolve forward reference
from app.schemas.sample import SampleRead  # noqa: E402

DiagnosticRead.model_rebuild()


class ParsedSampleData(BaseModel):
    """A single sample extracted from a PDF report, before persistence."""

    sample_number: str | None = None
    location: str | None = None
    material: str | None = None
    pollutant_type: str | None = None
    pollutant_subtype: str | None = None
    concentration: float | None = None
    unit: str | None = None


class ParseReportResponse(BaseModel):
    """Response from parse-report endpoint. Data extracted but NOT yet persisted."""

    diagnostic_id: UUID
    metadata: dict[str, Any] = {}
    samples: list[ParsedSampleData] = []
    warnings: list[str] = []
    text_length: int = 0


class ApplyReportRequest(BaseModel):
    """Payload to apply reviewed/corrected report data."""

    samples: list[ParsedSampleData] = []
    laboratory: str | None = None
    laboratory_report_number: str | None = None
    date_report: date | None = None
    summary: str | None = None
    conclusion: str | None = None
