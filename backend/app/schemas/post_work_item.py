"""Schemas for post-work item tracking and completion certificates."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PostWorkItemCreate(BaseModel):
    work_item_id: uuid.UUID | None = None
    building_element_id: uuid.UUID | None = None
    completion_status: str = "pending"
    notes: str | None = None
    photo_uris: list[str] | None = None
    before_after_pairs: list[dict] | None = None


class PostWorkItemUpdate(BaseModel):
    completion_status: str | None = None
    completion_date: datetime | None = None
    notes: str | None = None
    photo_uris: list[str] | None = None
    before_after_pairs: list[dict] | None = None
    verification_score: float | None = Field(None, ge=0, le=100)
    flagged_for_review: bool | None = None


class PostWorkItemComplete(BaseModel):
    """Contractor submits completion of a work item."""

    photo_uris: list[str] = Field(..., min_length=1)
    before_after_pairs: list[dict] | None = None
    notes: str | None = None
    contractor_signature_uri: str | None = None


class PostWorkItemRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    work_item_id: uuid.UUID | None
    building_element_id: uuid.UUID | None
    completion_status: str
    completion_date: datetime | None
    contractor_id: uuid.UUID
    photo_uris: list | None
    before_after_pairs: list | None
    notes: str | None
    verification_score: float
    flagged_for_review: bool
    ai_generated: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompletionStatusRead(BaseModel):
    building_id: uuid.UUID
    total_items: int
    completed_items: int
    verified_items: int
    completion_percentage: float
    items_by_status: dict[str, int]
    last_updated: datetime | None


class WorksCompletionCertificateRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    pdf_uri: str
    total_items: int
    verified_items: int
    completion_percentage: float
    issued_date: datetime
    contractor_signature_uri: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
