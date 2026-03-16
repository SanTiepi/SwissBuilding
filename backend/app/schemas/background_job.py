"""Pydantic schemas for background job tracking."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BackgroundJobCreate(BaseModel):
    job_type: str
    building_id: UUID | None = None
    organization_id: UUID | None = None
    params_json: dict[str, Any] | None = None


class BackgroundJobRead(BaseModel):
    id: UUID
    job_type: str
    status: str
    building_id: UUID | None
    organization_id: UUID | None
    created_by: UUID | None
    params_json: dict[str, Any] | None
    result_json: dict[str, Any] | None
    error_message: str | None
    progress_pct: int | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class BackgroundJobList(BaseModel):
    items: list[BackgroundJobRead]
    total: int
