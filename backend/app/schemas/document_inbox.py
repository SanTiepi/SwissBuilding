"""GED Inbox — Pydantic schemas for document inbox."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentInboxItemCreate(BaseModel):
    filename: str
    file_url: str
    file_size: int | None = None
    content_type: str | None = None
    source: str = "upload"
    notes: str | None = None
    suggested_building_id: UUID | None = None


class DocumentInboxItemRead(BaseModel):
    id: UUID
    filename: str
    file_url: str
    file_size: int | None
    content_type: str | None
    status: str
    suggested_building_id: UUID | None
    linked_building_id: UUID | None
    linked_document_id: UUID | None
    classification: dict | None
    source: str
    uploaded_by_user_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class DocumentInboxItemListRead(BaseModel):
    id: UUID
    filename: str
    file_size: int | None
    content_type: str | None
    status: str
    source: str
    suggested_building_id: UUID | None
    linked_building_id: UUID | None
    classification: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentInboxClassifyRequest(BaseModel):
    document_type: str
    confidence: float | None = None
    tags: list[str] | None = None


class DocumentInboxLinkRequest(BaseModel):
    building_id: UUID
    document_type: str | None = None


class DocumentInboxRejectRequest(BaseModel):
    reason: str | None = None
