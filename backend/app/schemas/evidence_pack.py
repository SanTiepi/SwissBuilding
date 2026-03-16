"""Pydantic schemas for EvidencePack CRUD."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class EvidencePackCreate(BaseModel):
    pack_type: str
    title: str
    description: str | None = None
    status: str = "draft"
    required_sections_json: list[dict[str, Any]] | None = None
    included_artefacts_json: list[dict[str, Any]] | None = None
    included_documents_json: list[dict[str, Any]] | None = None
    recipient_name: str | None = None
    recipient_type: str | None = None
    recipient_organization_id: uuid.UUID | None = None
    export_job_id: uuid.UUID | None = None
    expires_at: datetime | None = None
    notes: str | None = None


class EvidencePackUpdate(BaseModel):
    pack_type: str | None = None
    title: str | None = None
    description: str | None = None
    status: str | None = None
    required_sections_json: list[dict[str, Any]] | None = None
    included_artefacts_json: list[dict[str, Any]] | None = None
    included_documents_json: list[dict[str, Any]] | None = None
    recipient_name: str | None = None
    recipient_type: str | None = None
    recipient_organization_id: uuid.UUID | None = None
    export_job_id: uuid.UUID | None = None
    assembled_at: datetime | None = None
    submitted_at: datetime | None = None
    expires_at: datetime | None = None
    notes: str | None = None


class EvidencePackRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    pack_type: str
    title: str
    description: str | None
    status: str
    required_sections_json: list[dict[str, Any]] | None
    included_artefacts_json: list[dict[str, Any]] | None
    included_documents_json: list[dict[str, Any]] | None
    recipient_name: str | None
    recipient_type: str | None
    recipient_organization_id: uuid.UUID | None
    export_job_id: uuid.UUID | None
    assembled_at: datetime | None
    submitted_at: datetime | None
    expires_at: datetime | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    notes: str | None

    model_config = ConfigDict(from_attributes=True)
