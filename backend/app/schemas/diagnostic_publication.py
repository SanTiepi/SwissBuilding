from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DiagnosticPublicationPackage(BaseModel):
    """Payload received from Batiscan when publishing a validated report."""

    source_system: str = "batiscan"
    source_mission_id: str
    mission_type: str
    building_identifiers: dict  # {egid, egrid, official_id, address}
    report_pdf_url: str | None = None
    structured_summary: dict  # {pollutants_found, fach_urgency, zones, recommendations}
    annexes: list[dict] = []
    payload_hash: str  # SHA-256
    published_at: datetime
    version: int = 1


class DiagnosticReportPublicationRead(BaseModel):
    """Read model for frontend."""

    id: UUID
    building_id: UUID | None
    source_system: str
    source_mission_id: str
    current_version: int
    match_state: str
    match_key: str | None
    match_key_type: str | None
    mission_type: str
    report_pdf_url: str | None
    structured_summary: dict | None
    annexes: list[dict]
    payload_hash: str
    published_at: datetime
    is_immutable: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiagnosticPublicationVersionRead(BaseModel):
    id: UUID
    publication_id: UUID
    version: int
    published_at: datetime
    payload_hash: str
    report_pdf_url: str | None
    structured_summary: dict | None

    model_config = ConfigDict(from_attributes=True)


class DiagnosticMissionOrderCreate(BaseModel):
    building_id: UUID
    requester_org_id: UUID | None = None
    mission_type: str
    context_notes: str | None = None
    attachments: list[dict] = []


class DiagnosticMissionOrderRead(BaseModel):
    id: UUID
    building_id: UUID
    requester_org_id: UUID | None
    mission_type: str
    status: str
    context_notes: str | None
    attachments: list[dict]
    building_identifiers: dict | None
    external_mission_id: str | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ContractValidationResult(BaseModel):
    """Result of validating a diagnostic package against the expected contract."""

    valid: bool
    errors: list[str] = []


class ConsumerFetchResult(BaseModel):
    """Result of fetch_and_ingest operation."""

    consumer_state: str
    publication_id: str | None = None
    error: str | None = None
    errors: list[str] | None = None


class ConsumerStateRead(BaseModel):
    """Consumer state for a publication."""

    consumer_state: str | None
    contract_version: str | None
    fetch_error: str | None
    fetched_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class PublicationMatchRequest(BaseModel):
    building_id: UUID
