"""Artifact Versioning + Chain-of-Custody — Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------- ArtifactVersion ----------


class ArtifactVersionCreate(BaseModel):
    artifact_type: str
    artifact_id: UUID
    content_hash: str | None = None


class ArtifactVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    artifact_type: str
    artifact_id: UUID
    version_number: int
    content_hash: str | None = None
    status: str
    superseded_by_id: UUID | None = None
    created_by_user_id: UUID | None = None
    created_at: datetime
    archived_at: datetime | None = None
    archive_reason: str | None = None


# ---------- CustodyEvent ----------


class CustodyEventCreate(BaseModel):
    artifact_version_id: UUID
    event_type: str
    actor_type: str = "system"
    actor_id: UUID | None = None
    actor_name: str | None = None
    recipient_org_id: UUID | None = None
    details: dict | None = None
    occurred_at: datetime | None = None


class CustodyEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    artifact_version_id: UUID
    event_type: str
    actor_type: str
    actor_id: UUID | None = None
    actor_name: str | None = None
    recipient_org_id: UUID | None = None
    details: dict | None = None
    occurred_at: datetime
    created_at: datetime


# ---------- Composite views ----------


class CustodyChainRead(BaseModel):
    artifact_type: str
    artifact_id: UUID
    current_version: ArtifactVersionRead | None = None
    versions: list[ArtifactVersionRead] = []
    events: list[CustodyEventRead] = []


class ArchivePostureRead(BaseModel):
    building_id: UUID
    total_artifacts: int = 0
    total_versions: int = 0
    superseded_count: int = 0
    archived_count: int = 0
    withdrawn_count: int = 0
    current_count: int = 0
    last_custody_event: CustodyEventRead | None = None


class ArchiveRequest(BaseModel):
    reason: str
